import { createContext } from 'react'

/**
 * Sesiunea, ca în `GET /api/sesiune`. Contextul stă separat de provider din același
 * motiv ca la limbă (i18n/context.ts): la reîncărcarea în dezvoltare, paginile
 * trebuie să găsească același context ca providerul montat.
 */
export type Rol = 'admin' | 'analist'

export interface Utilizator {
  utilizator: string
  nume: string
  rol: Rol
  /** scurtătura de dezvoltare de pe laptop (MCC_AUTH_LOCAL): fără logare, fără „Ieșire” */
  local: boolean
}

export type Stare = 'se_incarca' | 'neautentificat' | 'autentificat'

/** Codurile de eroare ale serverului la logare, plus `retea` (fără răspuns) și `generic` (cod necunoscut). */
export type CodLogare = 'date_invalide' | 'fara_rol' | 'prea_multe_incercari' | 'ad_indisponibil' | 'retea' | 'generic'

export interface SesiuneState {
  stare: Stare
  /** doar când `stare === 'autentificat'` */
  utilizator: Utilizator | null
  /** sesiunea a expirat cu aplicația deschisă (nu e prima vizită): pagina de logare o spune */
  expirata: boolean
  /** întoarce `null` la succes, altfel codul erorii */
  logare: (utilizator: string, parola: string) => Promise<CodLogare | null>
  delogare: () => Promise<void>
}

export const SesiuneContext = createContext<SesiuneState>(null as never)
