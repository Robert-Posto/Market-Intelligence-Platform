import { useEffect, useState } from 'react'
import { Checkbox, Input, Select, Tooltip } from 'antd'
import { useSearchParams } from 'react-router-dom'
import type { ReclamaBing } from '@mcc/shared'
import { useBing } from '../../api/reclame'
import { Banda, BaraSectiune, Chip } from '../../components/Banda'
import { Despre, EtichetaBanca, Eroare, Pill, SeIncarca } from '../../components/comune'
import { Tabel } from '../../components/Tabel'
import { T, useLang } from '../../i18n'
import { faraDiacritice, formatZi, num } from '../../util/format'
import type { PropsSectiune } from './tipuri'
import '../../styles/campanii_reclame.css'

/*
 * 2.4: reclamele de pe Bing (Microsoft Ad Library). Vin toate deodată, dintr-un
 * fișier local, deci filtrele lucrează în browser, fără cerere nouă; stau în
 * adresă, ca filtrul să se păstreze la reîncărcare.
 */

/** „țintite pe România”: cel puțin jumătate din afișări în România; restul sunt ale grupului, în alte țări */
const peRomania = (r: ReclamaBing) => r.pondere_ro !== null && r.pondere_ro >= 50

/** Microsoft dă afișările ca interval scris („1K-5K”): pentru sortare contează capătul de jos. */
const MULTIPLU: Record<string, number> = { K: 1e3, M: 1e6 }
function afisariBing(v: unknown): number {
  const x = String(v || '').match(/([\d.,]+)\s*([KM]?)/i)
  return x ? Number.parseFloat(x[1]!.replace(',', '.')) * (MULTIPLU[(x[2] ?? '').toUpperCase()] ?? 1) : Number.NaN
}

export default function Bing({ m, taburi, subsol }: PropsSectiune) {
  const { t, tn, locale } = useLang()
  const q = useBing()
  const [sp, setSp] = useSearchParams()
  const banca = sp.get('banca') ?? ''
  const toate = sp.get('toate') === '1'
  const cautaAdresa = sp.get('q') ?? ''

  const schimba = (k: string, v: string, inlocuieste = false) =>
    setSp((p) => {
      const n = new URLSearchParams(p)
      if (v) n.set(k, v)
      else n.delete(k)
      return n
    }, { replace: inlocuieste })
  // tabelul nu se filtrează pe ascuns: clic pe chip alege banca din select (încă un clic: toate)
  const comutaBanca = (slug: string) => schimba('banca', banca === slug ? '' : slug)

  // tabelul se filtrează la fiecare tastă; adresa se scrie după 250 ms, fără o intrare nouă în istoric la fiecare literă
  const [cauta, setCauta] = useState(cautaAdresa)
  useEffect(() => setCauta(cautaAdresa), [cautaAdresa])
  useEffect(() => {
    if (cauta === cautaAdresa) return
    const id = setTimeout(() => schimba('q', cauta, true), 250)
    return () => clearTimeout(id)
  }, [cauta])

  const d = q.data
  if (!d) {
    return (
      <>
        <BaraSectiune taburi={taburi} />
        {q.error ? <Eroare e={q.error} /> : <SeIncarca />}
      </>
    )
  }
  const info = (
    <Pill tip="amb" title={t('campanii.bing.info_titlu')}>{t('campanii.bing.info', { fotografie: d.fotografie || '—' })}</Pill>
  )
  const rec = d.reclame
  if (!rec.length) {
    return (
      <>
        <BaraSectiune taburi={taburi} info={info} />
        <section className="cm-sec">
          <p className="note">{t('campanii.bing.fara_fotografie')}</p>
          {subsol}
        </section>
      </>
    )
  }

  const pe: Record<string, { ro: number; alt: number }> = {}
  for (const r of rec) {
    const x = (pe[r.banca] ??= { ro: 0, alt: 0 })
    if (peRomania(r)) x.ro++
    else x.alt++
  }
  const numeBanca = (b: string) => m.nume[b] ?? b
  const slugs = Object.keys(pe).sort((a, b) => Number(b === 'libra') - Number(a === 'libra') || pe[b]!.ro - pe[a]!.ro
    || numeBanca(a).localeCompare(numeBanca(b), locale))
  const nRo = rec.filter(peRomania).length
  const chipuri = (
    <>
      {/* Libra rămâne reperul și când nu are nicio reclamă pe Bing */}
      {!pe.libra && <Chip slug="libra" m={m} n="0" titlu={t('campanii.bing.chip_libra_zero')} />}
      {slugs.map((b) => {
        const x = pe[b]!
        return (
          <Chip
            key={b}
            slug={b}
            m={m}
            n={String(x.ro)}
            titlu={x.alt ? t('campanii.bing.chip_titlu_cu_grup', { ro: x.ro, alt: x.alt }) : t('campanii.bing.chip_titlu', { ro: x.ro })}
            activ={banca === b}
            onClick={() => comutaBanca(b)}
          />
        )
      })}
    </>
  )

  const c = faraDiacritice(cauta.trim())
  const vizibile = rec.filter((r) => (toate || peRomania(r)) && (!banca || r.banca === banca)
    && (!c || faraDiacritice([r.titlu, r.text, r.advertiser, numeBanca(r.banca)].join(' ')).includes(c)))
  // fără un cod unic în răspuns: cheia rândului e poziția lui în fișier
  const pozitie = new Map(rec.map((r, i) => [r, i]))
  // datele vin din API-ul Microsoft; o dată ISO se scrie după limbă, altceva rămâne cum a venit
  const zi = (s: string | null | undefined) => (!s ? '?' : /^\d{4}-\d{2}-\d{2}/.test(s) ? formatZi(s, locale) : s)

  const filtre = (
    <>
      <label className="f">
        {t('campanii.comun.banca')}
        <Select className="rc-sel" popupMatchSelectWidth={false} value={banca} onChange={(v: string) => schimba('banca', v)}
          options={[{ value: '', label: t('campanii.toate_bancile') }, ...slugs.map((b) => ({ value: b, label: numeBanca(b) }))]} />
      </label>
      <label className="f">
        {t('campanii.cauta')}
        <Input className="cauta rc-cauta" allowClear placeholder={t('campanii.bing.cauta_placeholder')} value={cauta}
          onChange={(e) => setCauta(e.target.value)} />
      </label>
      <Tooltip title={t('campanii.bing.grup_titlu')}>
        <Checkbox className="rc-bifa" checked={toate} onChange={(e) => schimba('toate', e.target.checked ? '1' : '')}>
          {t('campanii.bing.grup_eticheta')}
        </Checkbox>
      </Tooltip>
      <span className="rc-n">{tn('campanii.bing.n_reclame', vizibile.length, { n: num(vizibile.length, locale, 0) })}</span>
    </>
  )

  return (
    <>
      <BaraSectiune taburi={taburi} info={info} filtre={filtre} />
      <Banda
        cifre={[
          { n: num(nRo, locale, 0), eticheta: t('campanii.bing.tintite_ro'), titlu: t('campanii.bing.tintite_ro_titlu') },
          { n: num(rec.length, locale, 0), eticheta: t('campanii.bing.gasite_total') },
          { n: num(d.banci_verificate || 0, locale, 0), eticheta: t('campanii.bing.banci_verificate') },
        ]}
        chipuri={chipuri}
      />
      <section className="cm-sec rc-sec">
        {!!d.oprit && (
          <div className="callout warn" style={{ marginBottom: 12 }}>
            <T k="campanii.bing.oprit" />
          </div>
        )}
        <Tabel<ReclamaBing>
          randuri={vizibile}
          cheieRand={(r) => String(pozitie.get(r))}
          implicit={['pondere', 'descend']}
          gol={t('campanii.nicio_reclama_filtre')}
          coloane={[
            { cheie: 'banca', cap: t('campanii.comun.banca'), s: (r) => numeBanca(r.banca), val: (r) => <EtichetaBanca slug={r.banca} m={m} /> },
            {
              cheie: 'reclama', cap: t('campanii.bing.col_reclama'), s: (r) => r.titlu ?? '',
              val: (r) => (
                <>
                  <b>{r.titlu || '—'}</b>
                  <div className="rc-text">{r.text ?? ''}</div>
                  {r.advertiser && (
                    <Tooltip title={r.platitor ? t('campanii.bing.advertiser_titlu_platitor', { platitor: r.platitor }) : t('campanii.bing.advertiser_titlu')}>
                      <div className="rc-adv">{r.advertiser}</div>
                    </Tooltip>
                  )}
                </>
              ),
            },
            {
              cheie: 'perioada', cap: t('campanii.bing.col_perioada'), s: (r) => r.start ?? '',
              td: () => ({ className: 'mono nw' }), val: (r) => `${zi(r.start)} → ${zi(r.sfarsit)}`,
            },
            { cheie: 'afisari', cap: t('campanii.afisari'), num: true, s: (r) => afisariBing(r.afisari), val: (r) => r.afisari || '—' },
            {
              cheie: 'pondere', cap: t('campanii.bing.col_pondere_ro'), num: true, s: (r) => r.pondere_ro,
              val: (r) => (r.pondere_ro === null ? '—' : <span className={peRomania(r) ? '' : 'gri'}>{num(r.pondere_ro, locale, 1)}%</span>),
            },
            {
              cheie: 'sursa', cap: t('campanii.sursa'), td: () => ({ className: 'nw' }),
              val: (r) => (r.link_biblioteca
                ? <a className="sursa" href={r.link_biblioteca} target="_blank" rel="noopener noreferrer">↗ Ad Library</a>
                : '—'),
            },
          ]}
        />
        <Despre>
          <T k="campanii.bing.despre" />
        </Despre>
        {subsol}
      </section>
    </>
  )
}
