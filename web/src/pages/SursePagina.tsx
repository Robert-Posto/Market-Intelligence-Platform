import { useEffect, useState } from 'react'
import { Button, Input, Select, Tooltip } from 'antd'
import type { SursaInventar, SurseInventarBanca } from '@mcc/shared'
import { useMeta } from '../api/meta'
import { useSurseInventar } from '../api/surse_coada'
import { EtichetaBanca, Eroare, Pill, Pliat, SeIncarca } from '../components/comune'
import { linkDocument } from '../components/Dovezi'
import { Paginare } from '../components/Paginare'
import { Tabel, type Coloana } from '../components/Tabel'
import { useLang, type DictKey } from '../i18n'
import { num } from '../util/format'
import { useFiltreAdresa } from './surse_coada/adresa'
import '../styles/surse_coada.css'

const CHEI = ['banca', 'stare', 'rol', 'q', 'motiv'] as const
const LIM = 50

/** Rolurile sunt coduri din bază (surse.rol): rămân coduri în adresă și în filtru, la afișare au eticheta lor. */
const ROLURI: [string, DictKey][] = [
  ['', 'surse.rol_toate'],
  ['produs', 'surse.rol_produs'],
  ['conditii', 'surse.rol_conditii'],
  ['hub', 'surse.rol_hub'],
  ['locator', 'surse.rol_locator'],
  ['context', 'surse.rol_context'],
]
const ET_ROL = Object.fromEntries(ROLURI.filter(([v]) => v)) as Record<string, DictKey>

/** Același text ca la Istoric („Bancă”, „toate băncile”…): extragerea din 02.10 a păstrat o singură cheie pe text. */
const K_BANCA: DictKey = 'istoric.banca'
const K_TOATE_BANCILE: DictKey = 'istoric.toate_bancile'
const K_STERGE: DictKey = 'istoric.sterge_filtrele'
const K_TIP: DictKey = 'istoric.tip'

/** Un rând de tabel are nevoie de cheie unică: aceeași adresă apare de două ori la aceeași bancă (600 de perechi pe 05.10.2026, ca produs și ca document de tarife). */
interface RandSursa {
  r: SursaInventar
  i: number
}

/*
 * Surse: guvernanță. Revamp 25.09 în aplicația veche: tabel pe bancă (acoperire
 * dintr-o privire), căutare după fișier, numele fișierului în loc de începutul
 * adresei, paginare reală, motivul eșecului vizibil pe fiecare rând.
 */
export default function SursePagina() {
  const { t, locale } = useLang()
  const a = useFiltreAdresa(CHEI)
  const { f } = a
  const meta = useMeta()
  const q = useSurseInventar(a.parametri(LIM))

  // căutarea pornește la Enter, ca în aplicația veche; golită, se aplică pe loc
  const [cauta, setCauta] = useState(f.q)
  useEffect(() => setCauta(f.q), [f.q])

  const err = q.error ?? meta.error
  if (err) return <Eroare e={err} />
  if (!q.data || !meta.data) return <SeIncarca />
  const d = q.data
  const m = meta.data
  const b = d.bilant

  const cutie = (cheie: string, n: number, et: DictKey, desc: DictKey) => (
    <button type="button" key={cheie || 'toate'} className={`sc-tile${f.stare === cheie ? ' activ' : ''}`} onClick={() => a.mergi({ stare: cheie })}>
      <span className="n">{num(n, locale, 0)}</span>
      <span className="e">{t(et)}</span>
      <span className="l">{t(desc)}</span>
    </button>
  )

  const procent = (r: SurseInventarBanca) => Math.round((100 * r.cu_date) / r.total)
  const coloaneBanca: Coloana<SurseInventarBanca>[] = [
    { cheie: 'banca', cap: t(K_BANCA), s: (r) => r.nume, val: (r) => <EtichetaBanca slug={r.slug} m={m} tag /> },
    { cheie: 'total', cap: t('surse.col_surse'), num: true, s: (r) => r.total, val: (r) => num(r.total, locale, 0) },
    { cheie: 'cu_date', cap: t('surse.col_cu_date'), num: true, s: (r) => r.cu_date,
      val: (r) => (r.cu_date ? <b>{num(r.cu_date, locale, 0)}</b> : <span className="gri">0</span>) },
    { cheie: 'incercate', cap: t('surse.col_incercate'), num: true, s: (r) => r.incercate, val: (r) => num(r.incercate, locale, 0) },
    { cheie: 'neatinse', cap: t('surse.col_neincercate'), num: true, s: (r) => r.neatinse, val: (r) => num(r.neatinse, locale, 0) },
    { cheie: 'acoperire', cap: t('surse.col_acoperire'), s: (r) => (r.total ? r.cu_date / r.total : -1),
      val: (r) => (r.total ? (
        <>
          <Tooltip title={t('surse.acoperire_title', { procent: procent(r) })}>
            <span className="stele-bar" style={{ width: 110 }}>
              <span className="sc-plin" style={{ width: `${(100 * r.cu_date) / r.total}%` }} />
            </span>
          </Tooltip>
          <span className="sc-procent">{procent(r)}%</span>
        </>
      ) : '') },
    { cheie: 'stare', cap: t('surse.stare'), s: (r) => (r.blocate ? 0 : r.cu_date ? 2 : 1),
      val: (r) => r.blocate ? <Pill tip="amb" title={t('surse.site_blocat_title')}>{t('surse.site_blocat')}</Pill>
        : !r.total ? <Pill>{t('surse.stare_nicio_sursa')}</Pill>
          : r.cu_date ? <Pill tip="ok">{t('surse.stare_colectata')}</Pill> : <Pill>{t('surse.stare_fara_date')}</Pill> },
  ]

  const coloane: Coloana<RandSursa>[] = [
    { cheie: 'banca', cap: t(K_BANCA), val: ({ r }) => <EtichetaBanca slug={r.banca} m={m} /> },
    { cheie: 'fisier', cap: t('surse.col_fisier'), td: () => ({ className: 'sc-fisier' }), val: ({ r }) => <Fisier r={r} /> },
    { cheie: 'tip', cap: t(K_TIP), td: () => ({ className: 'mono' }), val: ({ r }) => (r.format || r.tip_sursa || '').toUpperCase() },
    { cheie: 'rol', cap: t('surse.rol'), td: () => ({ className: 'mono sc-rol' }),
      val: ({ r }) => (r.rol ? (ET_ROL[r.rol] ? t(ET_ROL[r.rol]!) : r.rol) : '—') },
    { cheie: 'valori', cap: t('surse.col_valori'), num: true, val: ({ r }) => (r.observatii ? num(r.observatii, locale, 0) : '—') },
    { cheie: 'stare', cap: t('surse.stare'), val: ({ r }) => <StareSursa r={r} /> },
    // nota de extracție e text din bază (date), nu se traduce
    { cheie: 'de_ce', cap: t('surse.col_de_ce'),
      val: ({ r }) => (r.observatii ? '' : (r.nota_extractie || '').split(':').slice(-1)[0]!.trim().slice(0, 80) || '—') },
  ]

  return (
    <div className="sc" style={{ opacity: q.isPlaceholderData ? 0.45 : 1 }}>
      <section>
        <div className="sc-tiles">
          {cutie('cu_date', b.cu_date, 'surse.cutie_cu_date', 'surse.cutie_cu_date_desc')}
          {cutie('incercate', b.incercate, 'surse.cutie_incercate', 'surse.cutie_incercate_desc')}
          {cutie('neatinse', b.neatinse, 'surse.cutie_neincercate', 'surse.cutie_neincercate_desc')}
          {cutie('', b.total, 'surse.cutie_toate', 'surse.cutie_toate_desc')}
        </div>
        {d.motive.length > 0 && (
          <p className="note sc-motive">
            {t('surse.motive_intro')}{' '}
            {/* motivul e începutul notei de extracție, text din bază: rămâne cum vine, și în filtru, și pe ecran */}
            {d.motive.map((x) => {
              const comuta = () => a.mergi({ motiv: x.motiv === f.motiv ? '' : x.motiv })
              return (
                <span key={x.motiv} role="button" tabIndex={0} className={`sc-motiv${x.motiv === f.motiv ? ' activ' : ''}`}
                  onClick={comuta} onKeyDown={(e) => { if (e.key === 'Enter') comuta() }}>
                  <Pill tip="amb">{x.motiv}: {num(x.n, locale, 0)}</Pill>
                </span>
              )
            })}
          </p>
        )}
      </section>

      {/* banca aleasă pliază tabelul: sursele ei sunt dedesubt (cheia îl reface pliat sau deschis, ca în aplicația veche) */}
      <Pliat key={f.banca ? 'inchis' : 'deschis'} deschis={!f.banca}
        titlu={<>{t('surse.pe_banca')} <span className="note">{t('surse.pe_banca_nota')}</span></>}>
        <section>
          <Tabel randuri={d.pe_banca} coloane={coloaneBanca} cheieRand={(r) => r.slug} libra={(r) => r.slug}
            onRand={(r) => a.mergi({ banca: r.slug === f.banca ? '' : r.slug })}
            clasaRand={(r) => (r.slug === f.banca ? 'ales' : '')} />
        </section>
      </Pliat>

      <div className="bara-fixa">
        <div className="filtre">
          <label className="f">{t('surse.cauta')}
            <Input className="cauta" allowClear placeholder={t('surse.cauta_placeholder')} value={cauta}
              onChange={(e) => {
                setCauta(e.target.value)
                if (!e.target.value && f.q) a.mergi({ q: '' })
              }}
              onPressEnter={() => a.mergi({ q: cauta })} />
          </label>
          <label className="f">{t(K_BANCA)}
            <Select value={f.banca} onChange={(v: string) => a.mergi({ banca: v })} style={{ minWidth: 320 }} popupMatchSelectWidth={false}
              options={[
                { value: '', label: t(K_TOATE_BANCILE) },
                ...d.banci.map((x) => ({ value: x.slug, label: `${x.nume} (${num(x.surse, locale, 0)})` })),
              ]} />
          </label>
          <label className="f">{t('surse.rol')}
            <Select value={f.rol} onChange={(v: string) => a.mergi({ rol: v })} style={{ minWidth: 170 }} popupMatchSelectWidth={false}
              options={ROLURI.map(([v, k]) => ({ value: v, label: t(k) }))} />
          </label>
          {a.activ && <Button onClick={a.sterge}>{t(K_STERGE)}</Button>}
          <span className="note sc-n">
            {d.total === 1 ? t('surse.numar_filtru_1', { n: 1 }) : t('surse.numar_filtru', { n: num(d.total, locale, 0) })}
          </span>
        </div>
      </div>

      <section className="sc-surse">
        <Tabel randuri={d.randuri.map((r, i) => ({ r, i }))} coloane={coloane} cheieRand={({ i }) => String(d.offset + i)} />
        <Paginare total={d.total} offset={d.offset} limit={d.limit} onChange={a.pagina} />
      </section>
    </div>
  )
}

/**
 * Numele fișierului, nu începutul adresei (la BCR toate încep cu același CDN);
 * adresa întreagă la hover, domeniul dedesubt. Un PDF se deschide în
 * vizualizatorul propriu, ca orice document din aplicație.
 */
function Fisier({ r }: { r: SursaInventar }) {
  const sursa = r.sursa ?? ''
  const link = r.url_public || (sursa.startsWith('http') ? sursa : null)
  const fis = r.fisier ?? ''
  const et = fis.length > 70 ? fis.slice(0, 69) + '…' : fis
  const dom = sursa.replace(/^https?:\/\/(www\.)?/, '').split('/')[0]
  const href = link && r.format === 'pdf' ? linkDocument(link, 1, '') : link
  return (
    <>
      <Tooltip title={sursa}>
        {href ? (
          <a className="sursa" href={href} target="_blank" rel="noopener">↗ {et}</a>
        ) : (
          <span className="mono" style={{ fontSize: 11 }}>{et}</span>
        )}
      </Tooltip>
      <span className="sub">{dom}</span>
    </>
  )
}

/** Trei stări, nu două: „neîncercată” cere o rulare, „site blocat” nu se forțează; nota spune de ce. */
function StareSursa({ r }: { r: SursaInventar }) {
  const { t } = useLang()
  if (r.observatii) return <Pill tip="ok">{t('surse.pill_are_date')}</Pill>
  if (r.status === 'blocat') return <Pill tip="amb" title={r.nota_extractie || undefined}>{t('surse.site_blocat')}</Pill>
  if (r.nota_extractie) return <Pill tip="amb" title={r.nota_extractie}>{r.nota_extractie.split(':')[0]!.slice(0, 40)}</Pill>
  return <Pill>{t('surse.pill_neincercata')}</Pill>
}
