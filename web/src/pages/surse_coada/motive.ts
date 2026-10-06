import { MOTIV_CHEIE } from '../../components/Dovezi'
import { useLang, type DictKey } from '../../i18n'
import { DICT } from '../../i18n/dict'
import { deLaServer } from '../../i18n/server'

/**
 * Motivele din coadă sunt cele reale din date (vederea coada_verificare), în
 * română, și rămân așa în adresă (`?motiv=…`) și ca valori de filtru. La afișare:
 * eticheta scurtă și explicația din dicționar. Cele două mari sunt pierderi de
 * STRUCTURĂ la citirea tabelului din PDF, nu greșeli de citire a cifrei — de-aia
 * valoarea se păstrează și așteaptă un om.
 *
 * Doar o parte din motive au etichetă scurtă (ca MOTIV_SCURT din aplicația
 * veche): celelalte apar cu numele întreg, tradus de `deLaServer` dacă îl știe.
 */
export interface Motive {
  /** numele întreg, tradus la afișare */
  nume: (mo: string) => string
  /** eticheta scurtă (antetul matricei, pastila de pe rând, lista din filtru) */
  scurt: (mo: string) => string
  /** explicația; gol pentru un motiv necunoscut */
  explicatie: (mo: string) => string
}

export function useMotive(): Motive {
  const { t, lang } = useLang()
  const cheie = (parte: 'motiv_scurt' | 'motiv_explicatie', mo: string): DictKey | null => {
    const k = MOTIV_CHEIE[mo]
    const c = k ? `coada.${parte}.${k}` : ''
    return c && c in DICT ? (c as DictKey) : null
  }
  const nume = (mo: string) => deLaServer(mo, lang)
  return {
    nume,
    scurt: (mo) => {
      const k = cheie('motiv_scurt', mo)
      return k ? t(k) : nume(mo)
    },
    explicatie: (mo) => {
      const k = cheie('motiv_explicatie', mo)
      return k ? t(k) : ''
    },
  }
}
