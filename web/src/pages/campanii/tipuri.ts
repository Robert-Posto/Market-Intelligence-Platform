import type { ReactNode } from 'react'
import type { Meta } from '../../api/meta'

/**
 * Ce primește fiecare secțiune 2.4 de la pagina Campanii: comutatorul de
 * secțiuni (îl pune în bara ei fixă, prin BaraSectiune) și tabelul surselor
 * (îl pune la finalul <section className="cm-sec">, ca în aplicația veche).
 * Filtrele și starea proprie le citește singură din adresă (useSearchParams).
 */
export interface PropsSectiune {
  m: Meta
  taburi: ReactNode
  subsol: ReactNode
}
