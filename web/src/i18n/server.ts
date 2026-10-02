import { DICT } from './dict'
import type { Lang } from '.'

/**
 * Textele pe care le trimite serverul gata scrise în română (numele comenzilor
 * de rulare, domeniile din „Detalii tehnice”, motivele din coadă). Serverul
 * Python nu știe de limbă, iar unele dintre ele sunt și chei de căutare
 * („bănci” din /api/sumar, motivele din ?motiv=): traduse pe server, paginile
 * n-ar mai găsi nimic. De aceea se traduc aici, la afișare.
 *
 * Textele cu parametri vin deja completate („rulează deja: Indicii BNR”), deci
 * nu se pot căuta după textul exact: se potrivesc după tipar, iar bucățile
 * prinse se traduc și ele, dacă sunt la rândul lor texte cunoscute.
 * Un text pe care nu-l cunoaștem rămâne cum a venit.
 */
const PREFIXE = ['server.', 'rulari_server.', 'db.']

const intrari = Object.entries(DICT)
  .filter(([k]) => PREFIXE.some((p) => k.startsWith(p)))
  .map(([, v]) => v as readonly [string, string])

const EXACT = new Map(intrari.filter(([ro]) => !ro.includes('{')).map(([ro, en]) => [ro, en]))

const escapa = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
const TIPARE = intrari
  .filter(([ro]) => ro.includes('{'))
  .map(([ro, en]) => {
    const nume: string[] = []
    const sursa = ro
      .split(/(\{[a-zA-Z0-9_]+\})/)
      .map((b) => {
        const m = /^\{([a-zA-Z0-9_]+)\}$/.exec(b)
        if (!m) return escapa(b)
        nume.push(m[1]!)
        return '(.*?)'
      })
      .join('')
    return { re: new RegExp(`^${sursa}$`, 's'), nume, en }
  })

export function deLaServer(text: string | null | undefined, lang: Lang): string {
  if (!text) return text ?? ''
  if (lang === 'ro') return text
  const exact = EXACT.get(text)
  if (exact !== undefined) return exact
  for (const t of TIPARE) {
    const m = t.re.exec(text)
    if (!m) continue
    return t.en.replace(/\{([a-zA-Z0-9_]+)\}/g, (orig, k: string) => {
      const i = t.nume.indexOf(k)
      return i < 0 ? orig : deLaServer(m[i + 1] ?? '', lang)
    })
  }
  return text
}
