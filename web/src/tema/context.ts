import { createContext } from 'react'

/**
 * Tema: luminoasă, întunecată sau ca sistemul (implicit). Contextul stă separat de
 * provider din același motiv ca la limbă (i18n/context.ts): la reîncărcarea în
 * dezvoltare, paginile trebuie să găsească același context ca providerul montat.
 */
export type Tema = 'luminos' | 'intunecat' | 'sistem'

/** Aceeași cheie și aceeași validare ca în public/tema-init.js. */
export const CHEIE_TEMA = 'mcc-tema'
const TEME: readonly string[] = ['luminos', 'intunecat', 'sistem']

/** Orice altă valoare (lipsă, veche, străină) înseamnă „ca sistemul”: nu ajunge niciodată în pagină ca text. */
export function valideazaTema(v: unknown): Tema {
  return typeof v === 'string' && TEME.includes(v) ? (v as Tema) : 'sistem'
}

export interface TemaState {
  tema: Tema
  /** tema efectivă, după alegere și după sistem */
  intunecat: boolean
  setTema: (t: Tema) => void
}

export const TemaContext = createContext<TemaState>(null as never)
