import { Fragment, useEffect, useState, type ReactNode } from 'react'
import { Checkbox, Collapse, Input, Select, Table, Tooltip } from 'antd'
import type { ColumnType, SortOrder } from 'antd/es/table/interface'
import { useSearchParams } from 'react-router-dom'
import type { BancaGoogle, ReclamaGoogle, ReclameGoogle } from '@mcc/shared'
import { SERVER_OPRIT } from '../../api/client'
import type { Meta } from '../../api/meta'
import { useGoogle } from '../../api/reclame'
import { Banda, BaraSectiune, Chip } from '../../components/Banda'
import { Despre, EtichetaBanca, Eroare, Pill, SeIncarca } from '../../components/comune'
import { Paginare } from '../../components/Paginare'
import { Tabel, type Coloana } from '../../components/Tabel'
import { T, useLang, type DictKey } from '../../i18n'
import { formatZi, num } from '../../util/format'
import type { PropsSectiune } from './tipuri'
import '../../styles/campanii_reclame.css'

/*
 * 2.4: reclamele Google (Ads Transparency Center). Sunt 16.765 în fotografia din
 * 30.09, prea multe pentru un tabel întreg: filtrul, sortarea și paginarea le face
 * serverul, iar aici se desenează doar rezultatul. Filtrele stau în adresă, deci
 * cererea se schimbă odată cu ea.
 */

/** Platformele sunt nume proprii; doar cele două stări fără platformă au text de tradus. */
const NUME_PLATFORMA: Record<string, string> = { SEARCH: 'Search', YOUTUBE: 'YouTube', MAPS: 'Maps', PLAY: 'Play', SHOPPING: 'Shopping' }
const CHEIE_PLATFORMA: Record<string, DictKey> = {
  sub_1000: 'campanii.google.platforma_sub_1000',
  fara_date: 'campanii.google.platforma_fara_date',
}
/** ordinea din lista de filtre: cele cunoscute întâi, în ordinea asta, apoi ce mai trimite serverul */
const ORDINE_PLATFORME = ['SEARCH', 'YOUTUBE', 'MAPS', 'PLAY', 'SHOPPING', 'sub_1000', 'fara_date']
const CHEIE_FORMAT: Record<string, DictKey> = {
  TEXT: 'campanii.google.format_text',
  IMAGE: 'campanii.google.format_imagine',
  VIDEO: 'campanii.google.format_video',
}
const PERIOADE: [string, DictKey][] = [
  ['', 'campanii.google.perioada_tot_anul'],
  ['activ7', 'campanii.google.perioada_activ7'],
  ['activ30', 'campanii.google.perioada_activ30'],
  ['activ90', 'campanii.google.perioada_activ90'],
  ['noi30', 'campanii.google.perioada_noi30'],
]
/** coloanele după care sortează serverul (GOOGLE_ORDINE din app/server.py) */
const COLOANE = ['banca', 'advertiser', 'format', 'platforma', 'prima', 'ultima', 'afisari']
const ORDINE_IMPLICITA = 'ultima'

/** linkul public al reclamei, refăcut din coduri (ca în galeria colegului); se deschide doar la clic */
const linkAtc = (r: ReclamaGoogle) =>
  `https://adstransparency.google.com/advertiser/${encodeURIComponent(r.advertiser_id)}/creative/${encodeURIComponent(r.creative_id)}?region=RO`

interface Filtre {
  banca: string
  format: string
  platforma: string
  perioada: string
  q: string
  doar_ro: boolean
  filiale: boolean
  ordine: string
  sens: 'asc' | 'desc'
  offset: number
}

function citesteFiltre(sp: URLSearchParams): Filtre {
  const ordine = sp.get('ordine') ?? ''
  return {
    banca: sp.get('banca') ?? '',
    format: sp.get('format') ?? '',
    platforma: sp.get('platforma') ?? '',
    perioada: sp.get('perioada') ?? '',
    q: sp.get('q') ?? '',
    doar_ro: sp.get('doar_ro') === '1',
    filiale: sp.get('filiale') === '1',
    ordine: COLOANE.includes(ordine) ? ordine : ORDINE_IMPLICITA,
    sens: sp.get('sens') === 'asc' ? 'asc' : 'desc',
    offset: Math.max(0, Number.parseInt(sp.get('offset') ?? '', 10) || 0),
  }
}

/**
 * Doar ce diferă de implicit: fără niciun filtru, cererea e aceeași cu cea a
 * comutatorului (aceeași cheie de cache), deci secțiunea nu cere fișierul de două ori.
 */
function parametri(f: Filtre): Record<string, string | number> {
  const p: Record<string, string | number> = {}
  if (f.banca) p.banca = f.banca
  if (f.format) p.format = f.format
  if (f.platforma) p.platforma = f.platforma
  if (f.perioada) p.perioada = f.perioada
  if (f.q.trim()) p.q = f.q.trim()
  if (f.doar_ro) p.doar_ro = '1'
  if (f.filiale) p.filiale = '1'
  if (f.ordine !== ORDINE_IMPLICITA) p.ordine = f.ordine
  if (f.sens !== 'desc') p.sens = f.sens
  if (f.offset) p.offset = f.offset
  return p
}

/** Etichetele și cifrele folosite deopotrivă în bandă, în tabele și în rezumat. */
function useEtichete() {
  const { t, locale } = useLang()
  const platforma = (p: string) => NUME_PLATFORMA[p] ?? (CHEIE_PLATFORMA[p] ? t(CHEIE_PLATFORMA[p]) : p || '—')
  const format = (x: string | null) => (x ? (CHEIE_FORMAT[x] ? t(CHEIE_FORMAT[x]) : x) : '—')
  const nr = (v: number) => (v >= 1e6 ? t('campanii.google.milioane', { valoare: num(v / 1e6, locale, 1) }) : num(v, locale, 0))
  const mil = (v: number) => num(v / 1e6, locale, 1)
  // suma pe bancă e un ordin de mărime: „≥” când măcar o reclamă e în treapta deschisă
  const afisariBanca = (b: BancaGoogle) =>
    b.af_deschis ? t('campanii.google.afisari_minim_mil', { jos: mil(b.af_jos) })
      : b.af_sus >= 1e6 ? t('campanii.google.afisari_interval_mil', { jos: mil(b.af_jos), sus: mil(b.af_sus) })
        : `${nr(b.af_jos)}–${nr(b.af_sus)}`
  const zi = (s: string | null | undefined) => (s ? formatZi(s, locale) : '—')
  return { platforma, format, nr, afisariBanca, zi }
}

export default function Google({ m, taburi, subsol }: PropsSectiune) {
  const { t, locale } = useLang()
  const et = useEtichete()
  const [sp, setSp] = useSearchParams()
  const f = citesteFiltre(sp)
  const baza = useGoogle()
  const rez = useGoogle(parametri(f))

  /** orice filtru nou duce la prima pagină, ca în aplicația veche; doar paginarea păstrează `offset` */
  const schimba = (o: Record<string, string>, opt: { pagina?: boolean; inlocuieste?: boolean } = {}) =>
    setSp((p) => {
      const n = new URLSearchParams(p)
      for (const [k, v] of Object.entries(o)) {
        if (v) n.set(k, v)
        else n.delete(k)
      }
      if (!opt.pagina) n.delete('offset')
      return n
    }, { replace: opt.inlocuieste })
  // clic pe chip (sau pe rândul din „Pe bănci”) = filtrul pe bancă; încă un clic = toate
  const comutaBanca = (slug: string) => schimba({ banca: f.banca === slug ? '' : slug })
  const sorteaza = (col: string) => {
    const sens = col === f.ordine && f.sens === 'desc' ? 'asc' : 'desc'
    schimba({ ordine: col === ORDINE_IMPLICITA ? '' : col, sens: sens === 'desc' ? '' : sens })
  }

  // căutarea pornește la 250 ms după ultima tastă, ca în aplicația veche: altfel fiecare literă e o cerere pe server
  const [cauta, setCauta] = useState(f.q)
  useEffect(() => setCauta(f.q), [f.q])
  useEffect(() => {
    if (cauta === f.q) return
    const id = setTimeout(() => schimba({ q: cauta }, { inlocuieste: true }), 250)
    return () => clearTimeout(id)
  }, [cauta])

  const d = baza.data
  if (!d) {
    return (
      <>
        <BaraSectiune taburi={taburi} />
        {baza.error ? <Eroare e={baza.error} /> : <SeIncarca />}
      </>
    )
  }
  const info = (
    <Pill tip="amb" title={t('campanii.google.info_titlu')}>{t('campanii.google.info', { fotografie: d.fotografie || '—' })}</Pill>
  )
  if (!d.fotografie) {
    return (
      <>
        <BaraSectiune taburi={taburi} info={info} />
        <section className="cm-sec">
          <p className="note">{t('campanii.google.fara_fotografie')}</p>
          {subsol}
        </section>
      </>
    )
  }

  const banci = d.banci
  const fil = d.filiale.reduce((s, b) => s + b.n, 0)
  const lasate = d.lasate_deoparte ?? {}
  // Libra prima, ca reper; restul în ordinea serverului (după numărul de reclame)
  const ordonate = banci.slice().sort((a, b) => Number(b.banca === 'libra') - Number(a.banca === 'libra'))
  const chipuri = (
    <>
      {!banci.some((b) => b.banca === 'libra') && <Chip slug="libra" m={m} n="0" titlu={t('campanii.google.chip_libra_zero')} />}
      {ordonate.map((b) => (
        <Chip
          key={b.banca}
          slug={b.banca}
          m={m}
          n={num(b.n, locale, 0)}
          titlu={t('campanii.google.chip_titlu', { active7: num(b.active7, locale, 0), noi30: num(b.noi30, locale, 0), afisari: et.afisariBanca(b) })}
          activ={f.banca === b.banca}
          onClick={() => comutaBanca(b.banca)}
        />
      ))}
    </>
  )
  const platforme = [...ORDINE_PLATFORME.filter((k) => d.platforme.includes(k)), ...d.platforme.filter((k) => !ORDINE_PLATFORME.includes(k))]
  const numeBanca = (b: string) => m.nume[b] ?? b

  const filtre = (
    <>
      <label className="f">
        {t('campanii.comun.banca')}
        <Select className="rc-sel" popupMatchSelectWidth={false} value={f.banca} onChange={(v: string) => schimba({ banca: v })}
          options={[
            { value: '', label: t('campanii.toate_bancile') },
            ...banci.map((b) => b.banca).sort((a, b) => numeBanca(a).localeCompare(numeBanca(b), locale)).map((b) => ({ value: b, label: numeBanca(b) })),
          ]} />
      </label>
      <label className="f">
        {t('campanii.format')}
        <Select className="rc-sel" popupMatchSelectWidth={false} value={f.format} onChange={(v: string) => schimba({ format: v })}
          options={[{ value: '', label: t('campanii.toate') }, ...d.formate.map((x) => ({ value: x, label: et.format(x) }))]} />
      </label>
      <label className="f">
        {t('campanii.google.suprafata_principala')}
        <Select className="rc-sel" popupMatchSelectWidth={false} value={f.platforma} onChange={(v: string) => schimba({ platforma: v })}
          options={[{ value: '', label: t('campanii.toate') }, ...platforme.map((x) => ({ value: x, label: et.platforma(x) }))]} />
      </label>
      <label className="f">
        {t('campanii.google.perioada_activa')}
        <Select className="rc-sel" popupMatchSelectWidth={false} value={f.perioada} onChange={(v: string) => schimba({ perioada: v })}
          options={PERIOADE.map(([v, k]) => ({ value: v, label: t(k) }))} />
      </label>
      <label className="f">
        {t('campanii.cauta')}
        <Input className="cauta rc-cauta" allowClear placeholder={t('campanii.google.cauta_placeholder')} value={cauta}
          onChange={(e) => setCauta(e.target.value)} />
      </label>
      <Tooltip title={t('campanii.google.doar_ro_titlu')}>
        <Checkbox className="rc-bifa" checked={f.doar_ro} onChange={(e) => schimba({ doar_ro: e.target.checked ? '1' : '' })}>
          {t('campanii.google.doar_ro')}
        </Checkbox>
      </Tooltip>
      {fil > 0 && (
        <Tooltip title={d.filiale.map((b) => `${numeBanca(b.banca)}: ${num(b.n, locale, 0)}`).join(' · ')}>
          <Checkbox className="rc-bifa" checked={f.filiale} onChange={(e) => schimba({ filiale: e.target.checked ? '1' : '' })}>
            {t('campanii.google.filiale', { n: num(fil, locale, 0) })}
          </Checkbox>
        </Tooltip>
      )}
    </>
  )

  // „Pe bănci”: clic pe rând = același filtru ca pe chip (Tabel are clic doar pe celulă, deci pe fiecare)
  const colBanciFaraClic: Coloana<BancaGoogle>[] = [
    { cheie: 'banca', cap: t('campanii.comun.banca'), s: (b) => numeBanca(b.banca), val: (b) => <EtichetaBanca slug={b.banca} m={m} tag /> },
    { cheie: 'n', cap: t('campanii.google.col_reclame'), num: true, s: (b) => b.n, val: (b) => num(b.n, locale, 0) },
    { cheie: 'active7', cap: t('campanii.google.col_active7'), num: true, s: (b) => b.active7, val: (b) => num(b.active7, locale, 0) },
    { cheie: 'noi30', cap: t('campanii.google.col_noi30'), num: true, s: (b) => b.noi30, val: (b) => num(b.noi30, locale, 0) },
    { cheie: 'af', cap: t('campanii.google.col_afisari_ordin'), num: true, s: (b) => b.af_jos, val: (b) => et.afisariBanca(b) },
  ]
  const colBanci = colBanciFaraClic.map((c) => ({ ...c, td: (b: BancaGoogle) => ({ onClick: () => comutaBanca(b.banca) }) }))

  let rezultat: ReactNode
  if (rez.error) {
    const mesaj = rez.error instanceof Error ? rez.error.message : String(rez.error)
    rezultat = (
      <p className="note" style={{ color: 'var(--warn)' }}>
        {mesaj === SERVER_OPRIT ? t('comun.server_oprit') : t('campanii.google.eroare', { mesaj })}
      </p>
    )
  } else if (!rez.data) {
    rezultat = <p className="note">{t('comun.se_incarca')}</p>
  } else {
    rezultat = (
      <Rezultat d={rez.data} m={m} f={f} onSorteaza={sorteaza}
        onPagina={(o) => schimba({ offset: o ? String(o) : '' }, { pagina: true })} />
    )
  }

  return (
    <>
      <BaraSectiune taburi={taburi} info={info} filtre={filtre} />
      <Banda
        cifre={[
          { n: num(d.total, locale, 0), eticheta: t('campanii.google.reclame_banci'), titlu: t('campanii.google.reclame_banci_titlu') },
          { n: <T k="campanii.google.banci_din_30" params={{ n: banci.length }} />, eticheta: t('campanii.google.banci_gasite') },
          { n: et.zi(d.ultima_zi), eticheta: t('campanii.google.ultima_zi'), titlu: t('campanii.google.ultima_zi_titlu', { data: et.zi(d.afisari_pana_la) }) },
        ]}
        chipuri={chipuri}
      />
      <section className="cm-sec rc-sec">
        {/* rezultatul vechi rămâne, estompat, până vine cel nou (ca la filtrele din aplicația veche) */}
        <div style={{ opacity: rez.isPlaceholderData ? 0.45 : 1 }}>{rezultat}</div>
        <Collapse
          ghost
          className="despre"
          items={[{
            key: 'b',
            label: <span className="despre-cap">ⓘ {t('campanii.google.pe_banci_rezumat')}</span>,
            children: (
              <Tabel<BancaGoogle>
                randuri={banci}
                cheieRand={(b) => b.banca}
                libra={(b) => b.banca}
                implicit={['n', 'descend']}
                clasaRand={() => 'rc-clic'}
                coloane={colBanci}
              />
            ),
          }]}
        />
        <Despre>
          <T
            k="campanii.google.despre"
            params={{
              fisier: d.fisier ?? '',
              afisari_pana_la: et.zi(d.afisari_pana_la),
              banci_gasite: banci.length,
              agentie_fara_platitor: num(lasate.agentie_fara_platitor ?? 0, locale, 0),
              exclus: num(lasate.exclus ?? 0, locale, 0),
            }}
          />
        </Despre>
        {subsol}
      </section>
    </>
  )
}

/** Rezumatul filtrului, tabelul sortat de server și paginarea. */
function Rezultat({ d, m, f, onSorteaza, onPagina }: {
  d: ReclameGoogle; m: Meta; f: Filtre; onSorteaza: (col: string) => void; onPagina: (offset: number) => void
}) {
  const { t, tn, locale } = useLang()
  const et = useEtichete()
  const x = d.filtrat
  const n = x.n

  // „activă” = afișată în ultimele 7 zile din date; „azi” e ultima zi din set, nu data rulării
  let prag7: string | null = null
  if (d.ultima_zi) {
    const z = new Date(`${d.ultima_zi}T00:00:00Z`)
    if (!Number.isNaN(z.getTime())) {
      z.setUTCDate(z.getUTCDate() - 6)
      prag7 = z.toISOString().slice(0, 10)
    }
  }

  const lista = (o: Record<string, number>, eticheta: (k: string) => string) =>
    Object.entries(o)
      .sort((a, b) => b[1] - a[1])
      .map(([k, v], i) => (
        <Fragment key={k}>
          {i > 0 && ' · '}
          {eticheta(k)} <b>{num(v, locale, 0)}</b>
        </Fragment>
      ))
  const reclame = <T k={n === 1 ? 'campanii.google.rezumat_reclame_1' : 'campanii.google.rezumat_reclame_n'} params={{ n: num(n, locale, 0) }} />
  const banciTxt = tn('campanii.n_banci', x.banci)
  const rezumat = (
    <p className="note" style={{ margin: '0 0 10px', maxWidth: 'none' }}>
      {n ? (
        <T k="campanii.google.rezumat_cu_detalii"
          params={{ reclame, banci: banciTxt, pe_format: lista(x.pe_format, (k) => et.format(k)), pe_platforma: lista(x.pe_platforma, et.platforma) }} />
      ) : (
        <T k="campanii.google.rezumat" params={{ reclame, banci: banciTxt }} />
      )}
    </p>
  )
  if (!n) return <>{rezumat}<p className="note">{t('campanii.nicio_reclama_filtre')}</p></>

  // sortarea o face serverul, pe tot filtrul; tabelul doar arată săgeata
  const ordine = (c: string): SortOrder => (f.ordine === c ? (f.sens === 'asc' ? 'ascend' : 'descend') : null)
  const sortabil = (c: string): Partial<ColumnType<ReclamaGoogle>> => ({
    sorter: true,
    sortOrder: ordine(c),
    sortDirections: ['descend', 'ascend', 'descend'],
    showSorterTooltip: false,
  })
  const cuTitlu = (cap: string, titlu: string) => <Tooltip title={titlu}><span>{cap}</span></Tooltip>
  const coloane: ColumnType<ReclamaGoogle>[] = [
    {
      key: 'banca', title: t('campanii.comun.banca'), className: 'nw', ...sortabil('banca'),
      render: (_, r) => (
        <>
          <EtichetaBanca slug={r.banca} m={m} fisa />
          {r.filiala && <Pill title={t('campanii.google.filiala_titlu')}>{t('campanii.filiala')}</Pill>}
        </>
      ),
    },
    {
      key: 'advertiser', title: t('campanii.google.col_advertiser'), ...sortabil('advertiser'),
      render: (_, r) => (
        <>
          {r.advertiser || '—'}
          {r.platitor && <div className="rc-mic">{t('campanii.google.platit_de', { platitor: r.platitor })}</div>}
        </>
      ),
    },
    {
      key: 'format', title: t('campanii.format'), ...sortabil('format'),
      render: (_, r) => (
        <>
          {et.format(r.format)}
          {r.tema && <Tooltip title={t('campanii.google.tema_titlu')}><div className="rc-mic">{r.tema}</div></Tooltip>}
        </>
      ),
    },
    {
      key: 'platforma',
      title: cuTitlu(t('campanii.google.suprafata_principala'), t('campanii.google.suprafata_principala_titlu')),
      ...sortabil('platforma'),
      // toate cele cinci platforme, cu treptele lor, la hover (textul vine gata scris de server)
      onCell: (r) => (r.platforme ? { title: r.platforme } : {}),
      render: (_, r) => {
        const txt = r.platforma.split('+').map(et.platforma).join(' + ')
        return r.platforma === 'fara_date' || r.platforma === 'sub_1000' ? <span className="gri">{txt}</span> : txt
      },
    },
    { key: 'prima', title: t('campanii.google.prima_afisare'), className: 'mono nw', ...sortabil('prima'), render: (_, r) => et.zi(r.prima) },
    {
      key: 'ultima', title: t('campanii.google.ultima_afisare'), className: 'mono nw', ...sortabil('ultima'),
      render: (_, r) => (
        <>
          {et.zi(r.ultima)}
          {prag7 && r.ultima && r.ultima >= prag7 && <> <Pill tip="ok" title={t('campanii.google.activa_titlu')}>{t('campanii.activa')}</Pill></>}
        </>
      ),
    },
    {
      key: 'afisari',
      title: cuTitlu(t('campanii.afisari'), t('campanii.google.afisari_titlu', { data: et.zi(d.afisari_pana_la) })),
      className: 'num nw', align: 'right', ...sortabil('afisari'),
      render: (_, r) =>
        r.af_deschis ? t('campanii.google.peste_10_mil')
          : r.af_jos !== null ? `${et.nr(r.af_jos)}–${r.af_sus === null ? '—' : et.nr(r.af_sus)}`
            : (
              <Tooltip title={t('campanii.google.afisari_intarziere_titlu')}>
                <span className="gri">{t('campanii.google.afisari_din', { data: et.zi(r.af_din) })}</span>
              </Tooltip>
            ),
    },
    {
      key: 'sursa', title: t('campanii.sursa'), className: 'nw',
      render: (_, r) => (
        <Tooltip title={r.creative_id}>
          <a className="sursa" href={linkAtc(r)} target="_blank" rel="noopener noreferrer">↗ ATC</a>
        </Tooltip>
      ),
    },
  ]

  return (
    <>
      {rezumat}
      {/* Table direct, nu Tabel: Tabel sortează în browser, iar aici sortează serverul pe toate cele 16.765 */}
      <Table<ReclamaGoogle>
        className="t"
        size="small"
        columns={coloane}
        dataSource={d.randuri}
        rowKey={(r) => `${r.advertiser_id}/${r.creative_id}`}
        pagination={false}
        rowClassName={(r) => (r.banca === 'libra' ? 'libra' : '')}
        onChange={(_p, _f, s, extra) => {
          if (extra.action !== 'sort') return
          const c = Array.isArray(s) ? s[0] : s
          const col = String(c?.columnKey ?? '')
          if (COLOANE.includes(col)) onSorteaza(col)
        }}
      />
      <Paginare total={n} offset={d.offset} limit={d.limit} onChange={onPagina} />
    </>
  )
}
