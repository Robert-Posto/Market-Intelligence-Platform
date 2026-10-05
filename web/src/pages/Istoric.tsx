import type { ReactNode } from 'react'
import { Button, Collapse, Select, Tooltip } from 'antd'
import { useSearchParams } from 'react-router-dom'
import type { SchimbarePret } from '@mcc/shared'
import { useIstoric } from '../api/context_istoric'
import { useMeta } from '../api/meta'
import { Despre, EtichetaBanca, Eroare, SeIncarca } from '../components/comune'
import { linkDocument } from '../components/Dovezi'
import { Tabel, type Coloana } from '../components/Tabel'
import { etNume, unitTxt } from '../components/valori'
import { T, useLang, type DictKey } from '../i18n'
import { formatZi, num } from '../util/format'
import '../styles/context_istoric.css'

const PERIOADE: [string, DictKey][] = [
  ['', 'istoric.perioada_oricand'],
  ['3', 'istoric.perioada_3_luni'],
  ['6', 'istoric.perioada_6_luni'],
  ['12', 'istoric.perioada_12_luni'],
]
const DIRECTII: [string, DictKey][] = [
  ['', 'istoric.directie_toate'],
  ['scumpire', 'istoric.directie_scumpire'],
  ['ieftinire', 'istoric.directie_ieftinire'],
]
const TIPURI: [string, DictKey][] = [
  ['', 'istoric.tip_toate'],
  ['comisioane', 'istoric.tip_comisioane'],
  ['dobanzi', 'istoric.tip_dobanzi'],
]
const ORDINI: [string, DictKey][] = [
  ['recente', 'istoric.ordine_recente'],
  ['mari', 'istoric.ordine_mari'],
]

interface Filtre {
  banca: string
  directie: string
  perioada: string
  tip: string
  ordine: string
}

/** cheia unică a rândului: același serviciu poate avea două schimbări identice în două documente */
type Rand = SchimbarePret & { id: number }

interface PeBanca {
  banca: string
  n: number
  sus: number
  jos: number
  rs: Rand[]
}

const zi = (x: string | null | undefined) => String(x ?? '').slice(0, 10)
const scumpire = (r: SchimbarePret) => (r.delta ?? 0) > 0

/** Scumpirea portocalie, ieftinirea verde, cu săgeata în față. */
function Sageata({ sus, children }: { sus: boolean; children?: ReactNode }) {
  return <span className={sus ? 'ci-sus' : 'ci-jos'}>{sus ? '↑' : '↓'}{children}</span>
}

/**
 * Istoric: ce s-a schimbat. Revamp 25.09 în aplicația veche: erau 986 de carduri
 * una sub alta (~58.000 px). Acum: filtre de perioadă, tip și ordine; rezumatul
 * pe bancă se recalculează din ce e filtrat; schimbările grupate pe bancă, în
 * tabel compact.
 */
export default function Istoric() {
  const { t, locale } = useLang()
  const [sp, setSp] = useSearchParams()
  const f: Filtre = {
    banca: sp.get('banca') || '',
    directie: sp.get('directie') || '',
    perioada: sp.get('perioada') || '',
    tip: sp.get('tip') || '',
    ordine: sp.get('ordine') || 'recente',
  }
  const meta = useMeta()
  const q = useIstoric(f.banca, f.directie)

  if (q.error) return <Eroare e={q.error} />
  if (meta.error) return <Eroare e={meta.error} />
  if (!q.data || !meta.data) return <SeIncarca />
  const d = q.data
  const m = meta.data
  const nume = (b: string) => m.nume[b] ?? b

  // parametrii goi și ordinea implicită nu intră în adresă; adresele vechi (`…&banca=&ordine=recente`) se citesc la fel
  const mergi = (o: Partial<Filtre>) => {
    const n = { ...f, ...o }
    setSp(Object.fromEntries(Object.entries(n).filter(([k, v]) => v && !(k === 'ordine' && v === 'recente'))))
  }

  // filtrele de perioadă, tip și ordine se aplică aici: datele vin toate odată
  const prag = f.perioada ? new Date(Date.now() - Number(f.perioada) * 30.44 * 86400000).toISOString().slice(0, 10) : ''
  const randuri: Rand[] = d.randuri
    .map((r, id) => ({ ...r, id }))
    .filter((r) => (!prag || zi(r.data_noua) >= prag)
      && (!f.tip || (f.tip === 'comisioane' ? r.unitate !== 'procent' : r.unitate === 'procent')))
  const mare = (r: SchimbarePret) => Math.abs(r.delta_pct || 0)
  randuri.sort(f.ordine === 'mari'
    ? (a, b) => mare(b) - mare(a)
    : (a, b) => zi(b.data_noua).localeCompare(zi(a.data_noua)) || mare(b) - mare(a))

  // rezumatul pe bancă, din rândurile FILTRATE (înainte arăta totalul, orice filtru ai fi ales)
  const peBanca: Record<string, PeBanca> = {}
  for (const r of randuri) {
    const x = (peBanca[r.banca] ??= { banca: r.banca, n: 0, sus: 0, jos: 0, rs: [] })
    x.n++
    if (scumpire(r)) x.sus++
    else x.jos++
    x.rs.push(r)
  }
  const listaB = Object.values(peBanca).sort((a, b) => b.n - a.n)
  const datate = d.acoperire.filter((x) => x.stare !== 'fără datare').reduce((s, x) => s + x.n, 0)
  const total = d.acoperire.reduce((s, x) => s + x.n, 0)

  const optiuniBanci = d.pe_banca.slice().sort((a, b) => nume(a.banca).localeCompare(nume(b.banca), locale))
    .map((x) => ({ value: x.banca, label: `${nume(x.banca)} (${num(x.n, locale, 0)})` }))
  // o bancă fără nicio schimbare (ex. `?banca=libra`) apare aleasă cu numele ei, nu ca slug
  if (f.banca && !optiuniBanci.some((o) => o.value === f.banca)) optiuniBanci.push({ value: f.banca, label: `${nume(f.banca)} (0)` })
  const optiuni = (l: [string, DictKey][]) => l.map(([value, k]) => ({ value, label: t(k) }))
  const filtrat = !!(f.banca || f.directie || f.perioada || f.tip || f.ordine !== 'recente')

  return (
    <>
      <div className="bara-fixa">
        <div className="filtre">
          <label className="f">{t('istoric.banca')}
            <Select value={f.banca} onChange={(v) => mergi({ banca: v })} style={{ minWidth: 280 }} popupMatchSelectWidth={false}
              options={[{ value: '', label: t('istoric.toate_bancile') }, ...optiuniBanci]} />
          </label>
          <label className="f">{t('istoric.perioada')}
            <Select value={f.perioada} onChange={(v) => mergi({ perioada: v })} style={{ minWidth: 150 }} popupMatchSelectWidth={false}
              options={optiuni(PERIOADE)} />
          </label>
          <label className="f">{t('istoric.directie')}
            <Select value={f.directie} onChange={(v) => mergi({ directie: v })} style={{ minWidth: 170 }} popupMatchSelectWidth={false}
              options={optiuni(DIRECTII)} />
          </label>
          <label className="f">{t('istoric.tip')}
            <Select value={f.tip} onChange={(v) => mergi({ tip: v })} style={{ minWidth: 180 }} popupMatchSelectWidth={false}
              options={optiuni(TIPURI)} />
          </label>
          <label className="f">{t('istoric.ordine')}
            <Select value={f.ordine} onChange={(v) => mergi({ ordine: v })} style={{ minWidth: 190 }} popupMatchSelectWidth={false}
              options={optiuni(ORDINI)} />
          </label>
          {filtrat && <Button onClick={() => setSp({})}>{t('istoric.sterge_filtrele')}</Button>}
        </div>
      </div>
      <div style={{ opacity: q.isPlaceholderData ? 0.45 : 1 }}>
        <section>
          <h2>{randuri.length === 1
            ? t('istoric.titlu_numar_1', { n: 1 })
            : t('istoric.titlu_numar', { n: num(randuri.length, locale, 0) })}</h2>
          {listaB.length > 0 && (
            <div className="ci-tiles">
              {listaB.map((x) => (
                <Tooltip key={x.banca} title={t('istoric.tile_title', { banca: nume(x.banca) })}>
                  <button type="button" className={`ci-tile${x.banca === f.banca ? ' ales' : ''}`}
                    onClick={() => mergi({ banca: x.banca === f.banca ? '' : x.banca })}>
                    <span className="nm">{nume(x.banca)}</span>
                    <span className="n">{num(x.n, locale, 0)}</span>
                    <span className="l">
                      <span className="ci-sus">{t(x.sus === 1 ? 'istoric.tile_scumpiri_1' : 'istoric.tile_scumpiri', { n: num(x.sus, locale, 0) })}</span>
                      {' · '}
                      <span className="ci-jos">{t(x.jos === 1 ? 'istoric.tile_ieftiniri_1' : 'istoric.tile_ieftiniri', { n: num(x.jos, locale, 0) })}</span>
                    </span>
                  </button>
                </Tooltip>
              ))}
            </div>
          )}
          <Despre>
            <T k="istoric.despre" params={{
              datate: num(datate, locale, 0),
              total: num(total, locale, 0),
              procent: Math.round((100 * datate) / Math.max(total, 1)),
            }} />
            {d.excluse_implauzibile > 0 && <T k="istoric.despre_excluse" params={{ n: num(d.excluse_implauzibile, locale, 0) }} />}
          </Despre>
        </section>
        {listaB.length ? (
          // altă adresă sau date noi = alt Collapse: deschise rămân iar primul grup (sau toate, la cel mult 3), ca în aplicația veche
          <Collapse
            key={`${sp.toString()}|${q.isPlaceholderData ? 'p' : 'd'}`}
            ghost
            className="ci-grupuri"
            defaultActiveKey={listaB.filter((_, i) => listaB.length <= 3 || i === 0).map((x) => x.banca)}
            items={listaB.map((x) => ({
              key: x.banca,
              label: (
                <span className="ci-grup-cap">
                  <EtichetaBanca slug={x.banca} m={m} fisa />
                  <span className="mono gri">
                    {t(x.n === 1 ? 'istoric.grup_schimbari_1' : 'istoric.grup_schimbari', { n: num(x.n, locale, 0) })}
                    {' · '}<span className="ci-sus">↑ {num(x.sus, locale, 0)}</span>
                    {' · '}<span className="ci-jos">↓ {num(x.jos, locale, 0)}</span>
                  </span>
                </span>
              ),
              children: <section><TabelBanca rs={x.rs} /></section>,
            }))}
          />
        ) : (
          <section>
            <div className="gol-stare">
              <b>{t('istoric.gol_titlu')}</b>
              {t('istoric.gol_text')}
            </div>
          </section>
        )}
      </div>
    </>
  )
}

/** Schimbările unei bănci, în ordinea aleasă sus; antetul sortează doar tabelul ăsta. */
function TabelBanca({ rs }: { rs: Rand[] }) {
  const { t, locale } = useLang()
  const u = (r: SchimbarePret) => unitTxt(r.unitate, t)
  const coloane: Coloana<Rand>[] = [
    {
      cheie: 'serviciu', cap: t('istoric.col_serviciu'), s: (r) => etNume(r.camp, t),
      val: (r) => {
        // denumirea serviciului e textul băncii și nu se traduce; conceptul de deasupra, da
        const s = r.serviciu || ''
        return <><b className="serv">{etNume(r.camp, t)}</b><span className="sub">{s.slice(0, 90)}{s.length > 90 ? '…' : ''}</span></>
      },
    },
    { cheie: 'inainte', cap: t('istoric.col_inainte'), num: true, s: (r) => r.valoare_ant, val: (r) => `${num(r.valoare_ant, locale)}${u(r)}` },
    { cheie: 'acum', cap: t('istoric.col_acum'), num: true, s: (r) => r.valoare_noua, val: (r) => <b>{num(r.valoare_noua, locale)}{u(r)}</b> },
    {
      cheie: 'schimbare', cap: t('istoric.col_schimbare'), num: true, s: (r) => r.delta_pct,
      // de la 0 lei procentul n-are sens: rămâne doar săgeata
      val: (r) => <Sageata sus={scumpire(r)}>{r.delta_pct === null ? '' : ` ${num(Math.abs(r.delta_pct), locale, 0)}%`}</Sageata>,
    },
    {
      cheie: 'perioada', cap: t('istoric.col_de_la_la'), s: (r) => zi(r.data_noua), td: () => ({ className: 'mono' }),
      val: (r) => `${formatZi(r.data_ant, locale)} → ${formatZi(r.data_noua, locale)}`,
    },
    { cheie: 'sursa', cap: t('istoric.col_sursa'), val: (r) => <LinkSchimbare r={r} /> },
  ]
  return (
    <div className="ci-tabel">
      <Tabel randuri={rs} coloane={coloane} cheieRand={(r) => String(r.id)} />
    </div>
  )
}

/**
 * Legătura spre documentul din care s-a citit valoarea nouă. La PDF se deschide
 * vizualizatorul propriu, la pagina și cu citatul căutat (Chrome ignoră `search=`,
 * iar extensia Adobe pierde `#page=`); o pagină web se deschide direct. Pagina
 * există doar la documente: la 05.10.2026 toate cele 883 de schimbări vin din PDF.
 */
function LinkSchimbare({ r }: { r: SchimbarePret }) {
  const { t } = useLang()
  const l = r.url_public || (String(r.sursa || '').startsWith('http') ? r.sursa : null)
  if (!l) return null
  const pdf = r.pagina !== null || /\.pdf(?:[?#]|$)/i.test(l)
  const a = (
    <a className="sursa" href={pdf ? linkDocument(l, r.pagina || 1, r.citat || '') : l} target="_blank" rel="noopener">
      {r.pagina ? t('istoric.link_sursa_pagina', { pagina: r.pagina }) : t('istoric.link_sursa')}
    </a>
  )
  // citatul e textul documentului: la hover, netradus
  return r.citat ? <Tooltip title={r.citat}>{a}</Tooltip> : a
}
