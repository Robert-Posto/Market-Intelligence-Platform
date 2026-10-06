/**
 * Vederea „pe termene” a unui produs Libra: clasamentul băncilor la o maturitate
 * aleasă (luni), pe un indicator (dobândă, DAE, marjă), într-o monedă.
 *
 * MODULAR: ce se compară și în ce sens stă în configurație, pe categoria produsului
 * (PE_CATEGORIE), cu excepții pe produs (PE_PRODUS). Un produs nou intră în vedere fără
 * cod nou, dacă are valori cu termen la cel puțin MIN_BANCI bănci. Măsurat pe
 * 05.10.2026: 8 produse trec pragul (3 depozite, 5 credite), restul n-au termen în date.
 */
import type { ProdusLibra, ValoareLibra } from '@mcc/shared'
import type { DictKey } from '../../i18n'
import { ePromo } from './logica'

export interface Indicator {
  id: string
  eticheta: DictKey
  campuri: string[]
}
export interface ConfigTermene {
  /** depozit: dobânda mare e mai bună; credit: DAE / dobânda / marja mică */
  sens: 'mare_bun' | 'mic_bun'
  /** „Maturitate” la depozite, „Perioadă” la credite */
  axa: DictKey
  indicatori: Indicator[]
}

/* Câmpuri lăsate deliberat pe dinafară, fiindcă nu sunt o ofertă comparabilă:
   dobanda_lunara (rată pe lună, nu pe an: 0,4% lângă 5,5% ar ieși ultima),
   dobanda_min / dobanda_max (capetele unui interval, nu dobânda clientului),
   dobanda_variabila_ulterioara (după perioada fixă, nu la acordare). */
const DEPOZIT: ConfigTermene = {
  sens: 'mare_bun',
  axa: 'pt.axa_maturitate',
  indicatori: [{ id: 'dobanda', eticheta: 'pt.ind.dobanda_anuala', campuri: ['dobanda_nominala', 'dobanda_la_scadenta', 'dobanda_fixa'] }],
}
const CREDIT: ConfigTermene = {
  sens: 'mic_bun',
  axa: 'pt.axa_perioada',
  indicatori: [
    { id: 'dae', eticheta: 'pt.ind.dae', campuri: ['dae'] },
    { id: 'dobanda', eticheta: 'pt.ind.dobanda', campuri: ['dobanda_fixa', 'dobanda_fixa_introductiva', 'dobanda_nominala', 'dobanda_variabila'] },
    { id: 'marja', eticheta: 'pt.ind.marja', campuri: ['marja_banca'] },
  ],
}

export const PE_CATEGORIE: Record<string, ConfigTermene> = {
  DEPOZITE: DEPOZIT,
  CREDIT_INVESTITII: CREDIT,
  CREDIT_CAPITAL_LUCRU: CREDIT,
}
/** Excepțiile unui produs față de categoria lui (gol la 05.10.2026). */
export const PE_PRODUS: Record<string, ConfigTermene> = {}

const MIN_BANCI = 2

export const config = (p: ProdusLibra): ConfigTermene | null =>
  PE_PRODUS[p.cod] ?? (p.categorie_cod ? PE_CATEGORIE[p.categorie_cod] ?? null : null)

/** Termenul valorii, în luni; zilele se trec în luni doar de la o lună în sus (150 de zile = 5 luni). */
export function luni(v: ValoareLibra): number | null {
  const s = v.scenariu
  if (s?.perioada_luni != null) return s.perioada_luni
  if (s?.perioada_zile != null && s.perioada_zile >= 28) return Math.round(s.perioada_zile / 30)
  return null
}

/** Moneda valorii: valuta scenariului, altfel moneda rândului; „LEI” e RON. Lipsa rămâne lipsă, nu se ghicește. */
export function moneda(v: ValoareLibra): string | null {
  const m = v.scenariu?.valuta ?? v.moneda
  if (!m) return null
  return m.toUpperCase() === 'LEI' ? 'RON' : m.toUpperCase()
}

/** Valorile care intră în vedere: un indicator al configurației, procent, cu termen. */
export function candidate(cfg: ConfigTermene, valori: ValoareLibra[]): ValoareLibra[] {
  const campuri = new Set(cfg.indicatori.flatMap((i) => i.campuri))
  return valori.filter((v) => campuri.has(v.camp) && v.unitate === '%' && v.valoare !== null && luni(v) !== null)
}

/** Produsul are vedere pe termene: configurație + valori cu termen la cel puțin MIN_BANCI bănci. */
export function eligibil(p: ProdusLibra, valori: ValoareLibra[] | undefined): boolean {
  const cfg = config(p)
  if (!cfg || !valori) return false
  return new Set(candidate(cfg, valori).map((v) => v.banca)).size >= MIN_BANCI
}

export interface Filtre {
  indicator: Indicator
  termen: number
  moneda: string // 'toate' sau codul
  oferta: 'toate' | 'standard' | 'promo'
  /** 'toate' sau online / ghiseu; o dobândă fără canal se aplică oricărui canal, deci intră la ambele */
  canal: string
  /** 'toate' sau la_scadenta / lunar / capitalizare; o dobândă fără plata precizată intră doar la 'toate' */
  plata: string
}

export interface Optiuni {
  indicatori: Indicator[]
  termene: { luni: number; banci: number }[]
  monede: { cod: string; n: number }[]
  faraMoneda: number
  /** canalele și plățile care apar în date; filtrul se arată doar dacă au ce despărți */
  canale: string[]
  plati: string[]
}

/**
 * Ce se poate alege, din date: doar indicatorii, termenele și monedele care există.
 * Băncile pe termen se numără în moneda aleasă: la Depozit la termen, 12 luni avea
 * două bănci pe toate monedele, dar una singură în lei.
 */
export function optiuni(cfg: ConfigTermene, valori: ValoareLibra[], indicator: Indicator, monedaFiltru = 'toate'): Optiuni {
  const toate = candidate(cfg, valori)
  const ale = toate.filter((v) => indicator.campuri.includes(v.camp))
  const peTermen = new Map<number, Set<string>>()
  for (const v of ale.filter((x) => monedaFiltru === 'toate' || moneda(x) === monedaFiltru)) {
    const l = luni(v)!
    if (!peTermen.has(l)) peTermen.set(l, new Set())
    peTermen.get(l)!.add(v.banca)
  }
  const monede = new Map<string, number>()
  let faraMoneda = 0
  for (const v of ale) {
    const m = moneda(v)
    if (m) monede.set(m, (monede.get(m) ?? 0) + 1)
    else faraMoneda++
  }
  return {
    indicatori: cfg.indicatori.filter((i) => toate.some((v) => i.campuri.includes(v.camp))),
    termene: [...peTermen].map(([l, b]) => ({ luni: l, banci: b.size })).sort((a, b) => a.luni - b.luni),
    monede: [...monede].map(([cod, n]) => ({ cod, n })).sort((a, b) => b.n - a.n),
    faraMoneda,
    canale: [...new Set(ale.map((v) => v.scenariu?.canal).filter((x): x is string => !!x))].sort(),
    plati: [...new Set(ale.map((v) => v.scenariu?.plata_dobanzii).filter((x): x is string => !!x))].sort(),
  }
}

/**
 * Termenul implicit: cel al scenariului de referință (la depozite, 12 luni în lei),
 * dacă la el au valoare cel puțin MIN_BANCI bănci; altfel termenul cu cele mai multe
 * bănci, iar la egalitate cel mai aproape de 12 luni. Pe 05.10.2026, la Depozit la
 * termen, 12 luni avea o singură bancă (Libra publică 13, BCR 5, ING 7): un clasament
 * cu un rând nu compară nimic.
 */
export function termenImplicit(valori: ValoareLibra[], opt: Optiuni): number | null {
  if (!opt.termene.length) return null
  const ref = valori.filter((v) => v.scenariu?.referinta?.potrivire === 'exact').map(luni).filter((l): l is number => l !== null)
  const disponibile = new Set(opt.termene.map((t) => t.luni))
  const frecv = new Map<number, number>()
  const banci = new Map(opt.termene.map((t) => [t.luni, t.banci]))
  for (const l of ref) if (disponibile.has(l) && banci.get(l)! >= MIN_BANCI) frecv.set(l, (frecv.get(l) ?? 0) + 1)
  if (frecv.size) return [...frecv].sort((a, b) => b[1] - a[1])[0]![0]
  return [...opt.termene].sort((a, b) => b.banci - a.banci || Math.abs(a.luni - 12) - Math.abs(b.luni - 12))[0]!.luni
}

export interface Rand {
  cheie: string
  pozitie: number
  banca: string
  v: ValoareLibra
  /** față de lider, în puncte procentuale (negativ = mai slab la depozit, pozitiv = mai scump la credit) */
  diferenta: number
  /** câte valori are banca la filtrele alese; rândul arată cea mai bună */
  variante: number
}

/**
 * Clasamentul: valorile de la filtrele alese, cea mai bună pe bancă (sau toate, cu
 * `toateVariantele`), ordonate după sens. Poziția are egalități, ca în clasamentele
 * publicate: două bănci cu 6,25% sunt amândouă pe 4, următoarea e pe 6.
 */
export function clasament(cfg: ConfigTermene, valori: ValoareLibra[], f: Filtre, toateVariantele: boolean): Rand[] {
  const mai_bun = (a: number, b: number) => (cfg.sens === 'mare_bun' ? b - a : a - b)
  const ale = candidate(cfg, valori).filter((v) => f.indicator.campuri.includes(v.camp)
    && luni(v) === f.termen
    && (f.moneda === 'toate' || moneda(v) === f.moneda)
    && (f.oferta === 'toate' || (f.oferta === 'promo') === ePromo(v.scenariu, v))
    && (f.canal === 'toate' || !v.scenariu?.canal || v.scenariu.canal === f.canal)
    && (f.plata === 'toate' || v.scenariu?.plata_dobanzii === f.plata))
  const peBanca = new Map<string, ValoareLibra[]>()
  for (const v of ale) {
    if (!peBanca.has(v.banca)) peBanca.set(v.banca, [])
    peBanca.get(v.banca)!.push(v)
  }
  const randuri: Omit<Rand, 'pozitie' | 'diferenta'>[] = []
  for (const [banca, l] of peBanca) {
    l.sort((a, b) => mai_bun(a.valoare!, b.valoare!))
    if (toateVariantele) l.forEach((v, i) => randuri.push({ cheie: `${banca}-${i}`, banca, v, variante: l.length }))
    else randuri.push({ cheie: banca, banca, v: l[0]!, variante: l.length })
  }
  randuri.sort((a, b) => mai_bun(a.v.valoare!, b.v.valoare!) || a.banca.localeCompare(b.banca))
  const lider = randuri[0]?.v.valoare ?? 0
  let pozitie = 0
  let anterior: number | null = null
  return randuri.map((r, i) => {
    if (r.v.valoare !== anterior) pozitie = i + 1
    anterior = r.v.valoare
    return { ...r, pozitie, diferenta: Math.round((r.v.valoare! - lider) * 100) / 100 }
  })
}
