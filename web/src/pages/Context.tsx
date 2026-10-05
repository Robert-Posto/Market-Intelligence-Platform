import type { ReactNode } from 'react'
import { Segmented } from 'antd'
import { useSearchParams } from 'react-router-dom'
import type { Indici } from '@mcc/shared'
import { useIndici } from '../api/rate_mobil'
import { Despre, Eroare, Pill, SeIncarca } from '../components/comune'
import { Tabel, type Coloana } from '../components/Tabel'
import { T, useLang } from '../i18n'
import { formatZi, num } from '../util/format'
import '../styles/context_istoric.css'

type Indice = Indici[number]

/** scadențele în ordinea lor economică, nu alfabetică (12M, 1M, 1W… nu spunea nimic) */
const ORD_SCADENTA = ['O/N', 'T/N', '1W', '1M', '3M', '6M', '9M', '12M']
const ordScad = (s: string | null) => {
  const i = ORD_SCADENTA.indexOf(s ?? '')
  return i < 0 ? 99 : i
}

/** ROBOR, ROBID și IRCC sunt nume proprii: aceeași etichetă în ambele limbi */
const INDICI = [
  { value: 'robor', label: 'ROBOR' },
  { value: 'robid', label: 'ROBID' },
  { value: 'ircc', label: 'IRCC' },
]

const zi = (x: string | null | undefined) => String(x ?? '').slice(0, 10)
/** `valoare` vine din coloana `numeric` a bazei, deci ca text („5.6400”) */
const nr = (v: Indice['valoare']) => (v === null ? null : Number(v))

/** Un rând sub o cifră: scumpirea portocalie, ieftinirea verde, cu săgeata. */
function Sageata({ d, children }: { d: number; children?: ReactNode }) {
  return <span className={d > 0 ? 'ci-sus' : 'ci-jos'}>{d > 0 ? '↑' : '↓'}{children}</span>
}

/**
 * 2.6 Context de piață: indicii de referință BNR. Sus, ce se folosește în
 * credite azi (IRCC în vigoare, ROBOR 3M / 6M / 12M față de ziua precedentă);
 * dedesubt, seria fiecărui indice.
 */
export default function Context() {
  const { t, locale } = useLang()
  const [sp, setSp] = useSearchParams()
  const ind = sp.get('indice') || 'robor'
  const q = useIndici()

  if (q.error) return <Eroare e={q.error} />
  if (!q.data) return <SeIncarca />
  const indici = q.data

  // la mai multe rânduri pe aceeași cheie câștigă primul, ca `find` din aplicația veche
  const valori = new Map<string, number | null>()
  for (const x of indici) {
    const k = `${x.indice}|${x.scadenta}|${zi(x.valabil_din)}`
    if (!valori.has(k)) valori.set(k, nr(x.valoare))
  }
  const val = (i: string, sc: string | null, z: string | undefined) => valori.get(`${i}|${sc}|${z}`) ?? null

  const zileRobor = [...new Set(indici.filter((x) => x.indice === 'robor').map((x) => zi(x.valabil_din)))].sort().reverse()
  const [azi, ieri] = zileRobor
  const astazi = new Date().toISOString().slice(0, 10)
  const irccToate = indici.filter((x) => x.indice === 'ircc').sort((a, b) => zi(b.valabil_din).localeCompare(zi(a.valabil_din)))
  const irccAcum = irccToate.find((x) => zi(x.valabil_din) <= astazi && (!x.valabil_pana || zi(x.valabil_pana) >= astazi))
  const sursa = indici.find((x) => x.indice === ind && x.sursa)?.sursa

  const card = (sc: string) => {
    const a = val('robor', sc, azi)
    const b = val('robor', sc, ieri)
    const d = a !== null && b !== null ? a - b : null
    return (
      <div key={sc}>
        <div className="e">ROBOR {sc}</div>
        <div className="n">{a === null ? '—' : `${num(a, locale)}%`}</div>
        <div className="l">
          {d === null ? '' : Math.abs(d) < 0.005
            ? t('context.card.neschimbat', { zi: formatZi(ieri, locale) })
            : <T k="context.card.fata_de" params={{ schimbare: <Sageata d={d}> {num(Math.abs(d), locale)} pp</Sageata>, zi: formatZi(ieri, locale) }} />}
        </div>
      </div>
    )
  }

  let tabel: ReactNode
  if (ind === 'ircc') {
    const coloane: Coloana<Indice>[] = [
      { cheie: 'trimestru', cap: t('context.ircc.col_trimestru'), td: () => ({ className: 'mono' }), val: (r) => r.scadenta ?? '—' },
      { cheie: 'valoare', cap: t('context.ircc.col_valoare'), num: true, val: (r) => <b>{num(nr(r.valoare), locale)}%</b> },
      { cheie: 'de_la', cap: t('context.ircc.col_de_la'), td: () => ({ className: 'mono' }), val: (r) => formatZi(r.valabil_din, locale) },
      { cheie: 'pana_la', cap: t('context.ircc.col_pana_la'), td: () => ({ className: 'mono' }), val: (r) => (r.valabil_pana ? formatZi(r.valabil_pana, locale) : '—') },
      { cheie: 'acum', cap: '', val: (r) => (r === irccAcum ? <Pill tip="ok">{t('context.ircc.in_vigoare_azi')}</Pill> : '') },
    ]
    tabel = <Tabel randuri={irccToate} coloane={coloane} cheieRand={(r) => `${r.scadenta}|${r.valabil_din}`} />
  } else {
    // pivot: un rând pe zi, o coloană pe scadență — curba se citește pe rând
    const serie = indici.filter((x) => x.indice === ind)
    const zile = [...new Set(serie.map((x) => zi(x.valabil_din)))].sort().reverse()
    const scadente = [...new Set(serie.map((x) => x.scadenta))].sort((a, b) => ordScad(a) - ordScad(b))
    const coloane: Coloana<string>[] = [
      { cheie: 'zi', cap: t('context.col_zi'), td: () => ({ className: 'mono' }), val: (z) => formatZi(z, locale) },
      ...scadente.map((s): Coloana<string> => ({
        cheie: s ?? '',
        cap: s ?? '',
        num: true,
        val: (z) => {
          const a = val(ind, s, z)
          const i = zile.indexOf(z)
          const b = i + 1 < zile.length ? val(ind, s, zile[i + 1]) : null
          if (a === null) return '—'
          const d = b === null ? 0 : a - b
          return <>{num(a, locale)}{Math.abs(d) >= 0.005 && <span className="ci-sageata"><Sageata d={d} /></span>}</>
        },
      })),
    ]
    tabel = <Tabel randuri={zile} coloane={coloane} cheieRand={(z) => z} />
  }

  return (
    <>
      <div className="kpi">
        <div>
          <div className="e">{t('context.ircc_in_vigoare')}</div>
          <div className="n">{irccAcum ? `${num(nr(irccAcum.valoare), locale)}%` : '—'}</div>
          <div className="l">
            {irccAcum && t('context.ircc_detaliu', {
              trimestru: irccAcum.scadenta ?? '',
              de_la: formatZi(irccAcum.valabil_din, locale),
              pana_la: irccAcum.valabil_pana ? formatZi(irccAcum.valabil_pana, locale) : '',
            })}
            <br />
            {t('context.ircc_descriere')}
          </div>
        </div>
        {card('3M')}
        {card('6M')}
        {card('12M')}
      </div>
      <section>
        <div className="filtre ci-filtre">
          <Segmented value={ind} onChange={(v) => setSp({ indice: v })} options={INDICI} />
          <span className="note" style={{ marginLeft: 'auto' }}>
            <T k="context.sursa" params={{
              sursa: sursa ? <a className="sursa" href={sursa} target="_blank" rel="noopener">{t('context.sursa_link')}</a> : 'BNR',
            }} />
          </span>
        </div>
        <p className="note" style={{ margin: '0 0 10px' }}>
          {ind === 'ircc'
            ? t('context.nota_ircc')
            : t('context.nota_pivot', { explicatie: t(ind === 'robor' ? 'context.nota_robor' : 'context.nota_robid') })}
        </p>
        {tabel}
        <Despre titlu="context.lipsa.titlu">
          <T k="context.lipsa.p1" />
          <T k="context.lipsa.p2" />
        </Despre>
      </section>
    </>
  )
}
