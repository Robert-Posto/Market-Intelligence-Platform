/**
 * Logica vederii „Comparație cu Libra”, fără marcaj: din valorile din
 * comparatie_libra (/api/comparatie_libra) în ce se afișează. Portată din
 * aplicația Next.js (lib/produse.js), care o luase din app/index.html (funcțiile pl*),
 * cu aceleași reguli; textele trec acum prin dicționar.
 */
import type { ScenariuLibra, ValoareLibra } from '@mcc/shared'
import type { DictKey, LangState } from '../../i18n'
import { unitTxt } from '../../components/valori'
import { num } from '../../util/format'

type Tr = LangState['t']
type Tn = LangState['tn']

/** Filtrele din adresă: `amb`, `low`, `ref`, `toate` sunt „1” sau lipsesc. */
export type Stare = Record<string, string>

export const CATEGORII = ['CONT_CURENT', 'CONT_OPERATIUNI', 'CARDURI_ACQUIRING', 'CREDIT_CAPITAL_LUCRU',
  'CREDIT_INVESTITII', 'DEPOZITE', 'FX_HEDGING', 'TRADE_FINANCE'] as const

export const numeCategorie = (c: string | null, t: Tr) =>
  c && (CATEGORII as readonly string[]).includes(c) ? t(`pl.categorie.${c}` as DictKey) : t('pl.categorie_altele')

/** Numele scurt din capul coloanelor; sigla și numele oficial rămân în `meta`. */
export const SCURT: Record<string, string> = {
  libra: 'Libra', bcr: 'BCR', raiffeisen: 'Raiffeisen', brd: 'BRD', ing: 'ING', 'banca-transilvania': 'BT',
}

const MOTIVE = ['produs_inexistent', 'nepublicat', 'nu_am_gasit', 'potrivire_slaba', 'blocat_de_robots']
export const motiv = (m: string | undefined, t: Tr) =>
  m && MOTIVE.includes(m) ? t(`pl.motiv.${m}` as DictKey) : t('pl.motiv_implicit')

// etichetele de scenariu fără spațiu și fără diacritice sunt de regulă bucăți din codul
// scenariului („od”, „cl”, „0”); doar acestea câteva sunt lizibile
const ETICHETE_LIZIBILE = new Set(['standard', 'Premium', 'gold', 'extra', 'plus', 'optim', 'start-up', 'lunar', 'Max'])

type Potrivire = NonNullable<ScenariuLibra['referinta']>['potrivire']
// potrivirea cu scenariul de referință (referinte_libra.json); „nespecificat” nu primește etichetă
const REF: Partial<Record<Potrivire, { k: DictKey; cls: string }>> = {
  exact: { k: 'pl.et.referinta', cls: 'ref' },
  aproximativ: { k: 'pl.et.aproximativ', cls: 'ref ap' },
  alt: { k: 'pl.et.alt', cls: 'alt' },
}
const RANG: Record<Potrivire, number> = { exact: 0, aproximativ: 1, nespecificat: 3, alt: 4 }
// întâi valorile pe scenariul de referință, apoi cele fără scenariu, la urmă alte exemple
export const rang = (v: ValoareLibra) => {
  const r = v.scenariu?.referinta
  return r ? RANG[r.potrivire] : 2
}

const VALUTA_IC: Record<string, string> = { EUR: 'euro', USD: 'dolar', GBP: 'lira', RON: 'bancnota' }
function iconitaEticheta(x: string): string {
  if (/asigur/i.test(x)) return 'scut'
  if (/salariu/i.test(x)) return 'servieta'
  if (/venit/i.test(x)) return 'portofel'
  if (/perioad|luni|\ban\b/i.test(x)) return 'calendar'
  if (/străin/i.test(x)) return 'glob'
  if (/client nou/i.test(x)) return 'clientNou'
  if (/premium|gold|max/i.test(x)) return 'coroana'
  return 'eticheta'
}

const UNITATI: Record<string, DictKey | ''> = {
  '%': 'unitate.procent', pp: 'pl.u.pp', lei: 'unitate.lei', eur: 'unitate.eur', usd: 'unitate.usd',
  luni: 'pl.u.luni', ani: 'pl.u.ani', zile: 'pl.u.zile', numar: '',
}

export function valoare(v: ValoareLibra, t: Tr, locale: string): string {
  if (v.valoare === null) return v.valoare_text || '—'
  const k = v.unitate ? UNITATI[v.unitate] : ''
  const u = k === undefined ? unitTxt(v.unitate, t) : k ? t(k) : ''
  return num(v.valoare, locale) + u
}

// „ofertă specială” (Blitz la Libra) e tot o promoție: pe 05.10.2026, 6 valori o spuneau așa, fără „promo”
export const ePromo = (s: ScenariuLibra | null, v: ValoareLibra) =>
  s?.oferta === 'promotie' || /promo|ofert[aă] special/i.test([s?.cod ?? '', (s?.etichete ?? []).join(' '), v.conditie ?? ''].join(' '))

export interface Eticheta {
  t: string
  ic: string
  cls?: string
}

/**
 * Etichetele de scenariu, oferta prima, ca să sară în ochi. Varianta, valuta și
 * etichetele libere vin din document și nu se traduc. `implicit`: valoarea e chiar pe
 * scenariul de referință, deci „referință” și valuta lui nu mai spun nimic și nu se afișează.
 */
export function etichete(s: ScenariuLibra | null, v: ValoareLibra, t: Tr, tn: Tn, locale: string,
  implicit = false): Eticheta[] {
  const e: Eticheta[] = []
  if (ePromo(s, v)) e.push({ t: t('pl.et.oferta'), ic: 'oferta', cls: 'of' })
  if (!s) return e
  const ref = s.referinta && REF[s.referinta.potrivire]
  if (ref && !implicit) e.push({ t: t(ref.k), ic: 'tinta', cls: ref.cls })
  if (s.varianta) e.push({ t: s.varianta, ic: 'straturi', cls: 'var' })
  const bani = (n: number, m?: string) => `${num(n, locale, 0)} ${m === 'EUR' ? 'EUR' : m === 'USD' ? 'USD' : 'lei'}`
  if (s.valuta && !implicit) {
    const c = s.valuta === 'LEI' ? 'RON' : s.valuta
    e.push({ t: c, ic: VALUTA_IC[c] ?? 'monede', cls: 'val' })
  }
  if (s.suma != null || (s.banda && s.suma_max != null)) {
    // la o treaptă de sold (`banda`) un singur capăt e „≥” / „<”, nu o sumă exactă
    const lo = s.suma, hi = s.suma_max
    e.push({
      t: lo != null && hi != null ? `${bani(lo, s.moneda)} – ${bani(hi, s.moneda)}`
        : lo != null ? `${s.banda ? '≥ ' : ''}${bani(lo, s.moneda)}`
        : `${s.suma_max_exclusiv ? '<' : '≤'} ${bani(hi!, s.moneda)}`,
      ic: 'monede',
    })
  }
  if (s.perioada_luni != null) e.push({ t: tn('pl.et.luni', s.perioada_luni), ic: 'calendar' })
  if (s.perioada_zile != null) e.push({ t: tn('pl.et.zile', s.perioada_zile), ic: 'calendar' })
  if (s.fix_ani != null) e.push({ t: tn('pl.et.fix_ani', s.fix_ani), ic: 'lacat' })
  if (s.venit_min != null) e.push({ t: t('pl.et.venit', { suma: num(s.venit_min, locale, 0) }), ic: 'portofel' })
  ;(s.etichete ?? [])
    .filter((x) => x !== s.varianta && !/promo/i.test(x) && (/ /.test(x) || /[^ -~]/.test(x) || ETICHETE_LIZIBILE.has(x)))
    .slice(0, 3)
    .forEach((x) => e.push({ t: x, ic: iconitaEticheta(x) }))
  if (s.derivat) e.push({ t: t('pl.et.calculat'), ic: 'calculator', cls: 'der' })
  return e
}

/** Condițiile citite din document, fără codul de scenariu și fără valuta (afișate separat). */
export function conditie(v: ValoareLibra): string {
  let c = v.conditie ?? ''
  const cod = v.scenariu?.cod
  if (cod && c.startsWith(cod)) c = c.slice(cod.length).replace(/^;\s*/, '')
  return c.replace(/^valuta [A-Z]{3};?\s*/, '')
}

export function vizibila(v: ValoareLibra, stare: Stare): boolean {
  if (stare.amb === '1' && v.ambiguu) return false
  if (stare.low === '1' && v.incredere != null && v.incredere < 0.85) return false
  const ref = v.scenariu?.referinta
  if (stare.ref === '1' && ref && (ref.potrivire === 'alt' || ref.potrivire === 'nespecificat')) return false
  return true
}
