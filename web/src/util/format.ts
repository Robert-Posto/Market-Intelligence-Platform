/** Numerele după limbă: 1.234,5 în română, 1,234.5 în engleză. Golul e „—”. */
export function num(v: number | null | undefined, locale: string, zecimale = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—'
  return Number(v).toLocaleString(locale, { maximumFractionDigits: zecimale })
}

/**
 * Comparația din tabelele vechi: numerele ca numere, textul alfabetic după
 * limbă, golurile la coadă indiferent de sens.
 */
export function compara(a: unknown, b: unknown, locale: string): number {
  const gol = (x: unknown) => x === null || x === undefined || x === ''
  if (gol(a) && gol(b)) return 0
  if (gol(a)) return 1
  if (gol(b)) return -1
  const na = Number(a)
  const nb = Number(b)
  if (!Number.isNaN(na) && !Number.isNaN(nb)) return na - nb
  return String(a).localeCompare(String(b), locale)
}

/** „Romana” găsește „Română”: căutarea ignoră diacriticele și majusculele. */
export const faraDiacritice = (t: string) =>
  String(t).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()

/** Câte zile au trecut de la o dată (0 = azi). */
export function zileDeLa(t: string): number {
  return Math.floor((Date.now() - new Date(t).getTime()) / 86400000)
}

/** Data scurtă după limbă: 30.09.2026 în română, 30/09/2026 în engleză; din ISO (AAAA-LL-ZZ…). */
export function formatZi(d: string | null | undefined, locale: string): string {
  if (!d) return '?'
  const s = String(d).slice(0, 10)
  const [a, l, z] = s.split('-')
  if (!a || !l || !z) return s
  return locale.startsWith('ro') ? `${z}.${l}.${a}` : `${z}/${l}/${a}`
}
