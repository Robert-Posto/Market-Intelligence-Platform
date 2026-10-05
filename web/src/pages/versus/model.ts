import type { Rate, VersusExtra, VersusMatrice } from '@mcc/shared'
import type { DictKey, Params } from '../../i18n'
import { num } from '../../util/format'

/** Coloana fixă din stânga: Libra e referința, celelalte bănci se compară cu ea. */
export const REFERINTA = 'libra'
/** Alegerea veche, când adresa nu spune nimic (`#/versus` simplu). */
export const IMPLICIT = ['bcr', 'brd', 'raiffeisen']
export const MAXIM_ALESE = 3

export interface Grup {
  api: 'matrice' | 'rate'
  cheie: string
  unitate: 'lei' | 'procent'
}
export const GRUPURI: Grup[] = [
  { api: 'matrice', cheie: 'cont_curent', unitate: 'lei' },
  { api: 'matrice', cheie: 'carduri', unitate: 'lei' },
  { api: 'matrice', cheie: 'transferuri', unitate: 'lei' },
  { api: 'rate', cheie: 'depozite', unitate: 'procent' },
  { api: 'rate', cheie: 'credite', unitate: 'procent' },
]

/** Celula de preț sau de dobândă, aceeași formă pentru /api/matrice și /api/rate. */
export interface CelulaVs {
  banca: string
  camp: string
  n: number
  minim: number
  maxim: number
  valoare: number | null
  serviciu: string | null
  frecventa: string | null
  conditie: string | null
  gratuite: number
}

export interface DateGrup {
  titlu: string
  sens: string
  campuri: string[]
  celule: CelulaVs[]
}

export const dinMatrice = (d: VersusMatrice): DateGrup => ({ titlu: d.titlu, sens: d.sens, campuri: d.campuri, celule: d.celule })

/** /api/rate trimite și `gratuite` (o dobândă de 0%), dar schema 2.2 nu-l cere: se citește dacă vine. */
export const dinRate = (d: Rate): DateGrup => ({
  titlu: d.titlu,
  sens: d.sens,
  campuri: d.campuri,
  celule: d.celule.map((c) => ({ ...c, gratuite: typeof c['gratuite'] === 'number' ? c['gratuite'] : 0 })),
})

export type Stare = 'castiga' | 'pierde' | 'mijloc' | 'fara' | 'singura'
export type Bilant = Record<Stare, number>

/**
 * Starea Libra pe un rând: cea mai bună / la mijloc / cea mai slabă / fără date.
 * Doar pe rândurile unde cel puțin încă o bancă are valoare.
 */
export function stareLibra(vals: Record<string, number | null>, sens: string): Stare {
  const lib = vals[REFERINTA]
  const alte = Object.entries(vals)
    .filter(([b, v]) => b !== REFERINTA && v !== null && v !== undefined)
    .map(([, v]) => v as number)
  if (lib === null || lib === undefined) return 'fara'
  if (!alte.length) return 'singura'
  const bun = sens === 'mare_bun' ? lib >= Math.max(...alte) : lib <= Math.min(...alte)
  const slab = sens === 'mare_bun' ? lib < Math.min(...alte) : lib > Math.max(...alte)
  return bun ? 'castiga' : slab ? 'pierde' : 'mijloc'
}

/** „Unde Libra nu e cea mai bună” cuprinde și mijlocul: acolo se poate câștiga ceva. */
export const vizibil = (st: Stare | 'neutru', arata: string) =>
  arata === 'toate' || (arata === 'pierde' && (st === 'pierde' || st === 'mijloc')) || (arata === 'castiga' && st === 'castiga')

export interface RandPret {
  camp: string
  celule: Record<string, CelulaVs>
  /** câte dintre coloane au valoare: „cel mai bun” are sens doar de la două în sus */
  prezente: number
  celMaiBun: number | null
  stare: Stare
}
export interface SectiunePret {
  tip: 'pret'
  cheie: string
  grup: Grup
  titlu: string
  sens: string
  randuri: RandPret[]
}

/**
 * Un grup de comisioane sau de dobânzi. Bilanțul numără toate rândurile, nu doar
 * pe cele afișate: casetele de sus spun același lucru pe oricare tab.
 */
export function sectiunePret(g: Grup, d: DateGrup, coloane: string[], bilant: Bilant, arata: string): SectiunePret | null {
  const harta: Record<string, Record<string, CelulaVs>> = {}
  for (const c of d.celule) (harta[c.camp] ??= {})[c.banca] = c
  const randuri: RandPret[] = []
  for (const cp of d.campuri.filter((x) => coloane.some((b) => harta[x]?.[b]))) {
    const p = harta[cp] ?? {}
    const prezente = coloane.map((b) => p[b]).filter((x): x is CelulaVs => !!x)
    const vals = prezente.map((x) => x.valoare).filter((v): v is number => v !== null)
    const celMaiBun = vals.length ? (d.sens === 'mare_bun' ? Math.max(...vals) : Math.min(...vals)) : null
    const st = stareLibra(Object.fromEntries(coloane.map((b) => [b, p[b] ? p[b].valoare : null])), d.sens)
    bilant[st] += 1
    if (!vizibil(st, arata)) continue
    randuri.push({ camp: cp, celule: p, prezente: prezente.length, celMaiBun, stare: st })
  }
  return randuri.length ? { tip: 'pret', cheie: g.cheie, grup: g, titlu: d.titlu, sens: d.sens, randuri } : null
}

/** Valoarea afișată în rândurile care nu vin din prețuri; `n` e cifra comparabilă (null: doar informativ). */
export interface ValExtra {
  t: string
  n: number | null
  sub?: string
}
export interface RandExtra {
  eticheta: DictKey
  desc: DictKey
  valori: Record<string, ValExtra | null>
  best: number | null
  stare: Stare | 'neutru'
}
export interface SectiuneExtra {
  tip: 'extra'
  cheie: string
  titlu: DictKey
  sens: string
  randuri: RandExtra[]
}

interface Fmt {
  t: (k: DictKey, p?: Params) => string
  locale: string
}

type DefRand<X> = [DictKey, DictKey, Record<string, X>, (r: X | undefined) => ValExtra | null]

function sectiuneExtra<X>(cheie: string, titlu: DictKey, sens: string, defs: DefRand<X>[], coloane: string[], bilant: Bilant, arata: string): SectiuneExtra | null {
  const randuri: RandExtra[] = []
  for (const [eticheta, desc, surse, fmt] of defs) {
    const brute = coloane.map((b) => {
      const v = fmt(surse[b])
      return { b, v, n: v && typeof v.n === 'number' ? v.n : null }
    })
    const numere = brute.map((x) => x.n).filter((x): x is number => x !== null && !Number.isNaN(x))
    const best = numere.length > 1 ? (sens === 'mare_bun' ? Math.max(...numere) : Math.min(...numere)) : null
    // rânduri fără cifră comparabilă (versiunea aplicației): doar informative
    const st = numere.length ? stareLibra(Object.fromEntries(brute.map((x) => [x.b, x.n])), sens) : 'neutru'
    if (st !== 'neutru') bilant[st] += 1
    if (!vizibil(st, arata)) continue
    randuri.push({ eticheta, desc, valori: Object.fromEntries(brute.map((x) => [x.b, x.v])), best, stare: st })
  }
  return randuri.length ? { tip: 'extra', cheie, titlu, sens, randuri } : null
}

/** Aplicația, rețeaua și recenziile, în aceeași formă ca celulele de preț (din /api/versus_extra). */
export function sectiuniExtra(extra: VersusExtra, coloane: string[], bilant: Bilant, arata: string, { t, locale }: Fmt): SectiuneExtra[] {
  const pe = <X extends { banca: string }>(lista: X[]) => Object.fromEntries(lista.map((x) => [x.banca, x])) as Record<string, X>
  const appPe = pe(extra.mobil)
  const locPe = pe(extra.retea)
  const sentPe = pe(extra.sentiment)
  const numar = (v: number | null | undefined, sufix: string, sub?: string): ValExtra | null =>
    v === null || v === undefined ? null : { t: num(v, locale) + sufix, n: Number(v), sub }
  const note = (v: number | null) =>
    v === 1 ? t('versus.sub_note_1', { volum: num(v, locale, 0) }) : t('versus.sub_note', { volum: num(v, locale, 0) })
  const recenzii = (n: number) =>
    n === 1 ? t('versus.sub_recenzii_1', { n: num(n, locale, 0) }) : t('versus.sub_recenzii', { n: num(n, locale, 0) })

  type App = VersusExtra['mobil'][number]
  type Loc = VersusExtra['retea'][number]
  type Sent = VersusExtra['sentiment'][number]
  const app: DefRand<App>[] = [
    ['versus.nota_app_store', 'versus.nota_app_store_desc', appPe, (r) => (r && r.rating ? numar(r.rating, ' ★', note(r.volum)) : null)],
    ['versus.nr_note', 'versus.nr_note_desc', appPe, (r) => (r && r.volum ? numar(r.volum, '', t('versus.sub_note_in_store')) : null)],
    ['versus.versiune_publicata', 'versus.versiune_publicata_desc', appPe, (r) => (r && r.versiune ? { t: r.versiune, n: null } : null)],
  ]
  const retea: DefRand<Loc>[] = [
    ['versus.sucursale', 'versus.sucursale_desc', locPe, (r) => (r && r.sucursale ? numar(r.sucursale, '', t('versus.sub_in_romania')) : null)],
    ['versus.atm_proprii', 'versus.atm_proprii_desc', locPe, (r) => (r && r.atm ? numar(r.atm, '', t('versus.sub_in_romania')) : null)],
  ]
  const rec: DefRand<Sent>[] = [
    ['versus.nota_recenzii', 'versus.nota_recenzii_desc', sentPe,
      (r) => (r && r.medie_text ? numar(r.medie_text, ' ★', recenzii(r.review_uri)) : null)],
    // mai puține negative = mai bine: cifra comparabilă e cu minus, ca rândul să rămână „mai mare = mai bun”
    ['versus.recenzii_negative', 'versus.recenzii_negative_desc', sentPe,
      (r) => (r && r.pct_negative !== null && r.pct_negative !== undefined
        ? { t: num(r.pct_negative, locale, 0) + '%', n: -Number(r.pct_negative), sub: t('versus.sub_din_recenziile_citite') }
        : null)],
  ]
  return [
    sectiuneExtra('aplicatie', 'versus.sec_aplicatie_mobila', 'mare_bun', app, coloane, bilant, arata),
    sectiuneExtra('retea', 'versus.sec_retea', 'mare_bun', retea, coloane, bilant, arata),
    sectiuneExtra('recenzii', 'versus.sec_recenzii', 'mare_bun', rec, coloane, bilant, arata),
  ].filter((s): s is SectiuneExtra => s !== null)
}

/** Numele scurt din capul coloanelor: „BRD”, nu „BRD — Groupe Société Générale”. */
export const scurt = (b: string, nume: Record<string, string>) => (nume[b] ?? b).replace(/ — .*| N\.V\..*| S\.A\..*| EAD .*/, '')
