/**
 * Formatele paginii Logging. Costul e în dolari (prețurile de listă Anthropic sunt
 * în USD), deci simbolul rămâne $ în ambele limbi; separatorul zecimal urmează limba.
 */
import type { DictKey } from '../../i18n'
import { areCheie } from '../../i18n'

const FUS = 'Europe/Bucharest'

/** Numele tipului în limba paginii; un tip nou din job_types, fără cheie în dicționar, rămâne cu denumirea lui. */
export const numeTip = (t: (k: DictKey) => string, cod: string, denumire: string) => {
  const k = `lg.tip.${cod}`
  return areCheie(k) ? t(k) : denumire
}

export function usd(v: number, locale: string, zecimale = 2): string {
  if (v > 0 && v < 0.01) return '< $' + (0.01).toLocaleString(locale, { minimumFractionDigits: 2 })
  return '$' + Number(v || 0).toLocaleString(locale, { minimumFractionDigits: zecimale, maximumFractionDigits: zecimale })
}

/**
 * Tot ce a intrat în model, cu cache cu tot. Discovery-ul trimite aproape tot prin cache
 * (la ING, 05.10.2026: 6 tokeni fără cache, 92.841 din cache): fără ei, „6 / 797” lângă $0,14
 * arăta ca o eroare de calcul.
 */
export const intrare = (x: { tokeni_intrare: number; tokeni_cache_citire: number; tokeni_cache_scriere: number }) =>
  x.tokeni_intrare + x.tokeni_cache_citire + x.tokeni_cache_scriere

/** 46,8 mil. / 46.8M: un total de tokeni nu se citește cu opt cifre. */
export const tokeni = (v: number, locale: string) =>
  new Intl.NumberFormat(locale, { notation: 'compact', maximumFractionDigits: 1 }).format(Number(v || 0))

/** Momentul în ora României, oricare ar fi fusul browserului: joburile rulează aici. */
export const moment = (iso: string, locale: string) =>
  new Date(iso).toLocaleString(locale, { timeZone: FUS, day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })

export const ziScurta = (zi: string) => {
  const [, l, z] = zi.split('-')
  return `${z}.${l}`
}

export const ziLunga = (zi: string, locale: string) =>
  new Date(`${zi}T12:00:00Z`).toLocaleDateString(locale, { timeZone: FUS, weekday: 'short', day: 'numeric', month: 'long' })

/** Durata în părțile ei; textul îl pune pagina, prin dicționar. */
export function partiDurata(s: number | null | undefined): { cheie: 's' | 'min' | 'h'; p: Record<string, string | number> } | null {
  if (s === null || s === undefined) return null
  const x = Math.round(s)
  if (x < 60) return { cheie: 's', p: { s: x } }
  if (x < 3600) return { cheie: 'min', p: { m: Math.floor(x / 60), s: String(x % 60).padStart(2, '0') } }
  return { cheie: 'h', p: { h: Math.floor(x / 3600), m: String(Math.floor((x % 3600) / 60)).padStart(2, '0') } }
}
