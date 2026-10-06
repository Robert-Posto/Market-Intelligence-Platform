import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode, type RefObject } from 'react'
import { Checkbox, Input, Segmented, Tooltip } from 'antd'
import { useSearchParams } from 'react-router-dom'
import type { ComparatieLibraDisponibila, ProdusLibra, ValoareLibra } from '@mcc/shared'
import { useComparatieLibra, useComparatieProdus } from '../../api/comparatie_libra'
import { useMeta, type Meta } from '../../api/meta'
import { Despre, Eroare, SeIncarca } from '../../components/comune'
import { etNume } from '../../components/valori'
import { T, useLang, type DictKey } from '../../i18n'
import { faraDiacritice, num } from '../../util/format'
import Celula from './Celula'
import Iconita from './Iconita'
import ModalDovada from './ModalDovada'
import PeTermene from './PeTermene'
import { eligibil } from './termene'
import { CATEGORII, SCURT, motiv, numeCategorie, vizibila, type Stare } from './logica'
import '../../styles/produse_libra.css'

const SEGMENTE: [string, DictKey][] = [['toate', 'pl.segment_toate'], ['PF', 'pl.segment_pf'], ['PJ', 'pl.segment_pj']]

type Lista = ComparatieLibraDisponibila
type Negasit = Lista['negasite'][number]

/* Tabelul se derulează în interiorul lui, nu pagina: capul cu băncile rămâne mereu
   vizibil. Înălțimea = spațiul rămas pe ecran sub carduri, plus 20% (restul se vede
   derulând puțin pagina). */
function potriveste(w: HTMLDivElement | null) {
  const main = document.getElementById('principal')
  if (!w || !main) return
  const ingust = window.innerWidth < 860
  const sus = w.getBoundingClientRect().top - main.getBoundingClientRect().top + main.scrollTop
  w.style.maxHeight = Math.round(1.2 * (ingust ? window.innerHeight - 70 : Math.max(380, main.clientHeight - sus - 24))) + 'px'
}

/**
 * 2.1, vederea „Comparație cu Libra”: fiecare produs Libra față de produsul
 * echivalent de la concurență, din comparatie_libra. Portată din aplicația
 * Next.js (components/produse/ProduseLibra.jsx), cu aceleași reguli.
 */
export default function ComparatieLibra({ comutator }: { comutator: ReactNode }) {
  const { t } = useLang()
  const lista = useComparatieLibra()
  const meta = useMeta()
  if (lista.error) return <Eroare e={lista.error} />
  if (meta.error) return <Eroare e={meta.error} />
  if (!lista.data || !meta.data) return <SeIncarca />
  if (!lista.data.disponibil) {
    return (
      <>
        <div className="pl-filtre">{comutator}</div>
        <section><p className="note"><T k="pl.nedisponibil" /></p></section>
      </>
    )
  }
  return <Vedere lista={lista.data} m={meta.data} comutator={comutator} t={t} />
}

function Vedere({ lista, m, comutator, t }: { lista: Lista; m: Meta; comutator: ReactNode; t: ReturnType<typeof useLang>['t'] }) {
  const { tn, locale } = useLang()
  const [sp, setSp] = useSearchParams()
  const stare: Stare = useMemo(() => Object.fromEntries(sp.entries()), [sp])
  const [cauta, setCauta] = useState('')
  const [deschis, setDeschis] = useState<ValoareLibra | null>(null)
  const track = useRef<HTMLDivElement>(null)
  const tw = useRef<HTMLDivElement>(null)

  const mergi = useCallback((k: Record<string, string>) => setSp((p) => {
    const n = new URLSearchParams(p)
    for (const [c, v] of Object.entries(k)) {
      if (v) n.set(c, v)
      else n.delete(c)
    }
    return n
  }, { replace: true }), [setSp])

  // ce se vede, din răspunsul /api/comparatie_libra și filtrele din adresă
  const v = useMemo(() => {
    const seg = stare.segment || 'toate'
    const cat = stare.cat || ''
    const acop: Record<string, Record<string, Lista['acoperire'][number]>> = {}
    const cmp: Record<string, number> = {}
    const nf: Record<string, Record<string, Negasit>> = {}
    for (const a of lista.acoperire) (acop[a.cod] ??= {})[a.banca] = a
    for (const c of lista.comparabile) cmp[c.cod] = c.n
    for (const x of lista.negasite) (nf[x.cod] ??= {})[x.banca] = x
    const banci = lista.banci.map((b) => b.slug)
    const peSeg = lista.produse.filter((p) => seg === 'toate' || p.segment === seg || p.segment === 'PF+PJ')
    const produse = peSeg.filter((p) => !cat || p.categorie_cod === cat)
    // implicit: produsul cu cele mai multe câmpuri comparabile
    const ales = produse.find((p) => p.cod === stare.produs)
      ?? [...produse].sort((a, b) => (cmp[b.cod] ?? 0) - (cmp[a.cod] ?? 0))[0]
    const nrCat: Record<string, number> = {}
    for (const p of peSeg) nrCat[p.categorie_cod ?? ''] = (nrCat[p.categorie_cod ?? ''] ?? 0) + 1
    return { seg, cat, acop, cmp, nf, banci, peSeg, produse, ales, nrCat }
  }, [lista, stare])

  const codAles = v.ales?.cod ?? null
  const d = useComparatieProdus(codAles)
  const dd = d.data?.disponibil ? d.data : null
  // vederea pe termene, doar la produsele care au valori cu termen (termene.ts); implicită acolo
  const areTermene = !!v.ales && eligibil(v.ales, dd?.valori)
  const mod = areTermene && stare.mod !== 'campuri' ? 'termene' : 'campuri'

  // cardul ales stă la mijlocul sliderului — doar când se schimbă produsul, nu la fiecare
  // tastă din căutare; tabelul ocupă restul ecranului de fiecare dată când se redesenează
  const nrProduse = v.produse.length
  useLayoutEffect(() => {
    const tr = track.current
    const a = tr?.querySelector<HTMLElement>('.pl-card.activ')
    if (tr && a) tr.scrollLeft = a.offsetLeft - (tr.clientWidth - a.offsetWidth) / 2
  }, [codAles, nrProduse])
  useLayoutEffect(() => { potriveste(tw.current) }, [dd, stare])
  useEffect(() => {
    const f = () => potriveste(tw.current)
    window.addEventListener('resize', f)
    return () => window.removeEventListener('resize', f)
  }, [])
  /* Rotița verticală deasupra sliderului îl mută pe orizontală (altfel derula pagina).
     La capete o lasă să deruleze pagina, ca să nu „blocheze” mouse-ul. */
  useEffect(() => {
    const tr = track.current
    if (!tr) return
    const f = (e: WheelEvent) => {
      if (Math.abs(e.deltaY) <= Math.abs(e.deltaX)) return
      const max = tr.scrollWidth - tr.clientWidth
      if ((e.deltaY < 0 && tr.scrollLeft <= 0) || (e.deltaY > 0 && tr.scrollLeft >= max - 1)) return
      e.preventDefault()
      tr.scrollLeft += e.deltaY
    }
    tr.addEventListener('wheel', f, { passive: false })
    return () => tr.removeEventListener('wheel', f)
  }, [])

  const inchide = useCallback(() => setDeschis(null), [])
  const { seg, cat, acop, cmp, nf, banci, peSeg, produse, ales, nrCat } = v
  const nume = (b: string) => SCURT[b] ?? m.nume[b] ?? b
  const logo = (b: string, cls = '') => (m.logo[b] ? <img className={cls} src={m.logo[b]} alt={nume(b)} /> : null)
  const c = faraDiacritice(cauta.trim())
  const derula = (sens: number) => track.current?.scrollBy({ left: sens * track.current.clientWidth * 0.8, behavior: 'smooth' })
  // BT răspunde 403 pe site-ul principal: are foarte puține valori, iar nota spune de ce
  const blocate = lista.banci.filter((b) => b.acces_restricted || b.slug === 'banca-transilvania').map((b) => nume(b.slug))

  return (
    <>
      <div className="pl-filtre">
        <Segmented value={seg} onChange={(s) => mergi({ segment: s === 'toate' ? '' : s, produs: '' })}
          options={SEGMENTE.map(([s, k]) => ({ value: s, label: t(k) }))} />
        <Input className="cauta" allowClear placeholder={t('pl.cauta_placeholder')} value={cauta} onChange={(e) => setCauta(e.target.value)} />
        <span className="pl-vedere">{comutator}</span>
      </div>

      <div className="pl-chipuri">
        <button type="button" className={`pl-chip ${!cat ? 'activ' : ''}`} onClick={() => mergi({ cat: '', produs: '' })}>
          {t('pl.categorie_toate')}<span>{peSeg.length}</span>
        </button>
        {CATEGORII.filter((k) => nrCat[k]).map((k) => (
          <button type="button" key={k} className={`pl-chip ${k === cat ? 'activ' : ''}`} onClick={() => mergi({ cat: k, produs: '' })}>
            {numeCategorie(k, t)}<span>{nrCat[k]}</span>
          </button>
        ))}
      </div>

      <div className="pl-slider">
        <button type="button" className="pl-sag" aria-label={t('pl.sag_inapoi')} onClick={() => derula(-1)}>‹</button>
        <div className="pl-track" ref={track}>
          {produse.length ? produse.map((p) => (
            <button type="button" key={p.cod} className={`pl-card ${p.cod === ales?.cod ? 'activ' : ''}`}
              hidden={!!c && !faraDiacritice(`${p.denumire} ${p.cod}`).includes(c)}
              onClick={() => mergi({ produs: p.cod, termen: '', ind: '', moneda: '', canal: '', plata: '', oferta: '', variante: '' })}>
              <span className="cat">{p.segment ?? ''} · {numeCategorie(p.categorie_cod, t)}</span>
              <span className="n">{p.denumire}</span>
              <span className="lg">
                {banci.map((b) => {
                  const a = acop[p.cod]?.[b]
                  const n = nf[p.cod]?.[b]
                  const titlu = a ? tn('pl.card_valori', a.n, { banca: nume(b) })
                    : n ? t('pl.card_motiv', { banca: nume(b), motiv: motiv(n.motiv, t) })
                    : t('pl.card_fara_date', { banca: nume(b) })
                  return (
                    <Tooltip key={b} title={titlu}>
                      <span className={`pl-lg ${a ? 'da' : n ? 'nu' : ''}`}>{logo(b) ?? nume(b).slice(0, 3)}</span>
                    </Tooltip>
                  )
                })}
                {cmp[p.cod]
                  ? <Tooltip title={t('pl.comparabile_tooltip')}><span className="cmp">{t('pl.comparabile', { n: cmp[p.cod]! })}</span></Tooltip>
                  : <Tooltip title={t('pl.necomparabil_tooltip')}><span className="gri">—</span></Tooltip>}
              </span>
            </button>
          )) : <p className="note">{t('pl.niciun_produs')}</p>}
        </div>
        <button type="button" className="pl-sag" aria-label={t('pl.sag_inainte')} onClick={() => derula(1)}>›</button>
      </div>

      <section className="pl-sec">
        {ales && <CapProdus ales={ales} valori={dd?.valori} stare={stare} mergi={mergi} areTermene={areTermene} mod={mod} />}
        {d.error ? <Eroare e={d.error} />
          : !ales ? <p className="note">{t('pl.niciun_produs_filtre')}</p>
          : !dd ? <p className="note">{t('comun.se_incarca')}</p>
          : mod === 'termene'
            // bifele „neclare” și „încredere sub 0,85” se aplică și aici; „doar referința” nu: termenul ales e scenariul
            ? <PeTermene ales={ales} valori={(dd.valori ?? []).filter((x) => vizibila(x, { ...stare, ref: '' }))}
                banci={banci} stare={stare} mergi={mergi} m={m} deschide={setDeschis} />
          : <TabelProdus d={dd} ales={ales} banci={banci} nf={nf} stare={stare} nume={nume} logo={logo} deschide={setDeschis} tw={tw} />}
        <Despre>
          <T k="pl.despre_ce" />
          <T k="pl.despre_scenariu" />
          <T k="pl.despre_referinta" />
          <T k="pl.despre_corectii" />
          <T k="pl.despre_sigure" />
          <T k="pl.despre_surse" params={{ lista: lista.banci.map((b) => `${nume(b.slug)}: ${num(b.n, locale, 0)}`).join(' · ') }} />
          {blocate.length > 0 && <> <T k="pl.despre_blocate" params={{ banci: blocate.join(', ') }} /></>}
        </Despre>
      </section>

      <ModalDovada v={deschis} inchide={inchide} />
    </>
  )
}

function CapProdus({ ales, valori, stare, mergi, areTermene, mod }: {
  ales: ProdusLibra
  valori: ValoareLibra[] | undefined
  stare: Stare
  mergi: (k: Record<string, string>) => void
  areTermene: boolean
  mod: 'termene' | 'campuri'
}) {
  const { t } = useLang()
  const ref = (valori ?? []).map((x) => x.scenariu?.referinta).find(Boolean)
  const bifa = (k: string, eticheta: DictKey) => (
    <Checkbox checked={stare[k] === '1'} onChange={() => mergi({ [k]: stare[k] === '1' ? '' : '1' })}>{t(eticheta)}</Checkbox>
  )
  return (
    <div className="pl-cap">
      <h2>{ales.denumire}</h2>
      <span className="gri mono" style={{ fontSize: 11 }}>
        {ales.cod} · {ales.segment ?? ''}{ales.prioritar ? ` · ${t('pl.prioritar')}` : ''}
      </span>
      {ref && (
        <Tooltip title={t('pl.ref_tooltip')}>
          <span className="pl-ref"><Iconita n="tinta" /><T k="pl.ref_scenariu" params={{ nume: ref.nume }} /></span>
        </Tooltip>
      )}
      <span className="pl-bife">
        {areTermene && (
          <Segmented size="small" value={mod} onChange={(x) => mergi({ mod: x === 'campuri' ? 'campuri' : '' })}
            options={[{ value: 'termene', label: t('pt.mod_termene') }, { value: 'campuri', label: t('pt.mod_campuri') }]} />
        )}
        {mod === 'campuri' && ref && bifa('ref', 'pl.bifa_ref')}
        {mod === 'campuri' && bifa('toate', 'pl.bifa_toate')}
        {bifa('low', 'pl.bifa_low')}
        {bifa('amb', 'pl.bifa_amb')}
      </span>
    </div>
  )
}

/** Tabelul produsului ales: un rând per câmp, o coloană per bancă. */
function TabelProdus({ d, ales, banci, nf, stare, nume, logo, deschide, tw }: {
  d: Lista
  ales: ProdusLibra
  banci: string[]
  nf: Record<string, Record<string, Negasit>>
  stare: Stare
  nume: (b: string) => string
  logo: (b: string, cls?: string) => ReactNode
  deschide: (v: ValoareLibra) => void
  tw: RefObject<HTMLDivElement>
}) {
  const { t, tn, locale } = useLang()
  const pc: Record<string, Record<string, ValoareLibra[]>> = {}
  for (const x of d.valori ?? []) ((pc[x.camp] ??= {})[x.banca] ??= []).push(x)
  const vede = (l: ValoareLibra[] | undefined) => (l ?? []).some((x) => vizibila(x, stare))
  let campuri = Object.keys(pc)
  // în modul „doar referința” rândul rămâne și când Libra n-are cifra pe referință:
  // tocmai asta e informația (Libra publică alt exemplu), nu un motiv să dispară rândul
  if (stare.toate !== '1') {
    campuri = campuri.filter((c) => (stare.ref === '1'
      ? banci.some((b) => vede(pc[c]![b])) && (pc[c]!.libra ?? []).length > 0
      : vede(pc[c]!.libra) && banci.some((b) => b !== 'libra' && vede(pc[c]![b]))))
  }
  campuri.sort((a, b) => Number(a === 'altele') - Number(b === 'altele') || etNume(a, t).localeCompare(etNume(b, t), locale))
  if (!campuri.length) {
    return <p className="note">{t(stare.toate === '1' ? 'pl.nicio_valoare_filtre' : 'pl.niciun_camp_comparabil')}</p>
  }
  const ech: Record<string, NonNullable<Lista['echivalente']>[number]> = {}
  for (const e of d.echivalente ?? []) ech[e.banca] = e
  const nfp = nf[ales.cod] ?? {}
  return (
    <div className="pl-tw" ref={tw}>
      <table className="pl" style={{ minWidth: 170 + 148 * banci.length }}>
        <thead>
          <tr>
            <th className="camp colt">{t('pl.col_ce')}<small>{tn('pl.n_campuri', campuri.length)}</small></th>
            {banci.map((b) => (
              <th key={b} className={b === 'libra' ? 'libra' : ''}>
                {/* doar sigla, mărită; numele la hover, iar fără siglă rămâne numele */}
                <span className="bk" title={nume(b)}>{logo(b, 'lg') ?? <b>{nume(b)}</b>}</span>
                {/* denumirea produsului la bancă e dată, nu text de interfață */}
                {ech[b] ? <span className="eq" title={ech[b]!.denumire_la_banca ?? ''}>{ech[b]!.denumire_la_banca ?? ''}</span>
                  : nfp[b] ? <span className="eq sus">{motiv(nfp[b]!.motiv, t)}</span>
                  : <span className="eq">{t('pl.fara_date')}</span>}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {campuri.map((c) => (
            <tr key={c}>
              <th className="camp" scope="row">{etNume(c, t)}<small>{c}</small></th>
              {banci.map((b) => (
                <td key={b} className={b === 'libra' ? 'libra' : ''}>
                  <Celula key={`${ales.cod}-${c}-${b}`} lista={pc[c]![b]} stare={stare} deschide={deschide} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
