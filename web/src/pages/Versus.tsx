import { useCallback, useRef, useState, type CSSProperties } from 'react'
import { Segmented } from 'antd'
import { useSearchParams } from 'react-router-dom'
import { useMeta } from '../api/meta'
import { useRate } from '../api/rate_mobil'
import { useVersusExtra, useVersusMatrice } from '../api/versus'
import { Despre, Eroare, Pill, SeIncarca } from '../components/comune'
import Sertar, { type CerereSertar } from '../components/Sertar'
import { T, useLang, type DictKey } from '../i18n'
import { num } from '../util/format'
import { AlegeBanci } from './versus/AlegeBanci'
import { CardBanca } from './versus/CardBanca'
import {
  dinMatrice, dinRate, GRUPURI, IMPLICIT, REFERINTA, scurt, sectiunePret, sectiuniExtra,
  type Bilant, type SectiuneExtra, type SectiunePret,
} from './versus/model'
import { SectiuneExtraVs, SectiunePretVs } from './versus/Sectiune'
import '../styles/versus.css'

const TABURI: [string, DictKey][] = [
  ['toate', 'versus.tab_toate'],
  ['pierde', 'versus.tab_pierde'],
  ['castiga', 'versus.tab_castiga'],
]

/**
 * Capul secțiunilor stă fix sub bara de filtre, oricât de înaltă e ea (bara se
 * rupe pe două rânduri la ferestre înguste sau cu nume lungi de bănci). Cei 26 px
 * sunt marginea de sus a lui <main>, pe care bara fixă o acoperă (`top: -26px`).
 */
function useSubBara(): [(el: HTMLDivElement | null) => void, number] {
  const [h, setH] = useState(0)
  const obs = useRef<ResizeObserver | null>(null)
  const ref = useCallback((el: HTMLDivElement | null) => {
    obs.current?.disconnect()
    obs.current = null
    if (!el) return
    const masoara = () => setH(Math.max(el.offsetHeight - 26, 0))
    masoara()
    obs.current = new ResizeObserver(masoara)
    obs.current.observe(el)
  }, [])
  return [ref, h]
}

/**
 * Versus Libra. Revamp 25.09: rezumat sus („unde câștigă / pierde Libra”), filtru
 * pe rânduri, capul fiecărei secțiuni fix la derulare, selector de bănci cu căutare.
 * Libra e comparată cu până la trei bănci, alese în adresă (`?banci=bcr,brd`).
 */
export default function Versus() {
  const { t, locale } = useLang()
  const [sp, setSp] = useSearchParams()
  const arata = sp.get('arata') || 'toate'
  const banciAdresa = sp.get('banci')
  const [sertar, setSertar] = useState<CerereSertar | null>(null)
  const [refBara, subBara] = useSubBara()

  const meta = useMeta()
  const contCurent = useVersusMatrice('cont_curent')
  const carduri = useVersusMatrice('carduri')
  const transferuri = useVersusMatrice('transferuri')
  const depozite = useRate('depozite', '', '')
  const credite = useRate('credite', '', '')
  const extra = useVersusExtra()

  const err = meta.error ?? contCurent.error ?? carduri.error ?? transferuri.error ?? depozite.error ?? credite.error ?? extra.error
  if (err) return <Eroare e={err} />
  if (!meta.data || !contCurent.data || !carduri.data || !transferuri.data || !depozite.data || !credite.data || !extra.data) return <SeIncarca />
  const m = meta.data
  const date = [dinMatrice(contCurent.data), dinMatrice(carduri.data), dinMatrice(transferuri.data), dinRate(depozite.data), dinRate(credite.data)]
  const x = extra.data

  const toateBanci = [...new Set(date.flatMap((d) => d.celule.map((c) => c.banca)))]
    .sort((a, b) => (m.nume[a] ?? a).localeCompare(m.nume[b] ?? b, locale))
  const implicit = IMPLICIT.filter((b) => toateBanci.includes(b))
  // `?banci=` gol (Aplică fără nicio bifă) înseamnă tot alegerea implicită, ca în aplicația veche
  const alese = (banciAdresa ? banciAdresa.split(',') : implicit).filter((b) => toateBanci.includes(b) && b !== REFERINTA)
  const coloane = [REFERINTA, ...alese]
  const nume = Object.fromEntries(coloane.map((b) => [b, scurt(b, m.nume)]))

  const bilant: Bilant = { castiga: 0, pierde: 0, mijloc: 0, fara: 0, singura: 0 }
  const sectiuni: (SectiunePret | SectiuneExtra)[] = [
    ...GRUPURI.map((g, i) => sectiunePret(g, date[i]!, coloane, bilant, arata)).filter((s): s is SectiunePret => s !== null),
    ...sectiuniExtra(x, coloane, bilant, arata, { t, locale }),
  ]
  const comparabile = bilant.castiga + bilant.pierde + bilant.mijloc

  const pe = <X extends { banca: string }>(lista: X[]) => Object.fromEntries(lista.map((r) => [r.banca, r])) as Record<string, X>
  const appPe = pe(x.mobil)
  const locPe = pe(x.retea)
  const acopPe = pe(x.acoperire)
  // tabul scrie în adresă și băncile afișate, ca legătura copiată să arate același lucru
  const mergi = (o: { banci?: string; arata?: string }) => setSp({ banci: alese.join(','), arata, ...o })
  const stil = {
    '--vsc': `minmax(200px,1.3fr) repeat(${coloane.length},minmax(130px,1fr))`,
    '--sub-bara': `${subBara}px`,
  } as CSSProperties

  return (
    <>
      <div className="bara-fixa" ref={refBara}>
        <div className="filtre">
          <div className="vs-alege">
            <span className="gri" style={{ fontSize: 11.5 }}>{t('versus.comparata_cu')}</span>
            {alese.length ? alese.map((b) => <Pill key={b}>{scurt(b, m.nume)}</Pill>) : <span className="gri">{t('versus.nicio_banca')}</span>}
            <AlegeBanci key={alese.join(',')} toate={toateBanci} alese={alese} m={m} onAplica={(sel) => mergi({ banci: sel.join(',') })} />
          </div>
          <Segmented style={{ marginLeft: 'auto' }} value={arata} onChange={(v) => mergi({ arata: v })}
            options={TABURI.map(([v, k]) => ({ value: v, label: t(k) }))} />
        </div>
      </div>
      <div className="kpi vs-kpi">
        <div>
          <div className="e">{t('versus.kpi_castiga')}</div>
          <div className="n" style={{ color: 'var(--ok)' }}>{num(bilant.castiga, locale, 0)}<span className="gri" style={{ fontSize: 15 }}> / {num(comparabile, locale, 0)}</span></div>
          <div className="l">{t('versus.kpi_castiga_desc')}</div>
        </div>
        <div>
          <div className="e">{t('versus.kpi_mijloc')}</div>
          <div className="n">{num(bilant.mijloc, locale, 0)}</div>
          <div className="l">{t('versus.kpi_mijloc_desc')}</div>
        </div>
        <div>
          <div className="e">{t('versus.kpi_pierde')}</div>
          <div className="n" style={{ color: 'var(--warn)' }}>{num(bilant.pierde, locale, 0)}</div>
          <div className="l">{t('versus.kpi_pierde_desc')}</div>
        </div>
        <div className="inactiv">
          <div className="e">{t('versus.kpi_fara')}</div>
          <div className="n gri">{num(bilant.fara, locale, 0)}</div>
          <div className="l">{t('versus.kpi_fara_desc')}</div>
        </div>
      </div>
      {sectiuni.length ? (
        <section className="vs" style={stil}>
          <div className="vs-bara">
            <div className="vs-cap0">{t('versus.caracteristica')}</div>
            {coloane.map((b) => <CardBanca key={b} b={b} m={m} app={appPe[b]} loc={locPe[b]} acop={acopPe[b]} />)}
          </div>
          {sectiuni.map((s) =>
            s.tip === 'pret'
              ? <SectiunePretVs key={s.cheie} s={s} coloane={coloane} nume={nume} deschide={setSertar} />
              : <SectiuneExtraVs key={s.cheie} s={s} coloane={coloane} nume={nume} />,
          )}
          <Despre><T k="versus.despre" /></Despre>
        </section>
      ) : (
        <section>
          <p className="note">{t(arata === 'toate' ? 'versus.gol_toate' : 'versus.gol_filtru')}</p>
        </section>
      )}
      <Sertar cerere={sertar} onClose={() => setSertar(null)} />
    </>
  )
}
