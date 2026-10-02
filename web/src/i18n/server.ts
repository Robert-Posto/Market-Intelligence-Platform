import { DICT } from './dict'
import type { Lang } from '.'

/**
 * Textele pe care le trimite serverul gata scrise în română (numele comenzilor
 * de rulare, domeniile din „Detalii tehnice”, motivele din coadă). Serverul
 * Python nu știe de limbă, iar unele dintre ele sunt și chei de căutare
 * („bănci” din /api/sumar, motivele din ?motiv=): traduse pe server, paginile
 * n-ar mai găsi nimic. De aceea se traduc aici, la afișare, după textul exact.
 * Un text pe care nu-l cunoaștem rămâne cum a venit.
 */
const PREFIXE = ['server.', 'rulari_server.', 'db.']

const INVERS: Map<string, string> = new Map(
  Object.entries(DICT)
    .filter(([k]) => PREFIXE.some((p) => k.startsWith(p)))
    .map(([, v]) => [(v as readonly [string, string])[0], (v as readonly [string, string])[1]]),
)

export function deLaServer(text: string | null | undefined, lang: Lang): string {
  if (!text) return text ?? ''
  if (lang === 'ro') return text
  return INVERS.get(text) ?? text
}
