import { areCheie, type DictKey, type Params } from '../i18n'

type Tr = (k: DictKey, p?: Params) => string

/**
 * Conceptele canonice din vocabular.py sunt slug-uri („retragere_numerar”):
 * bune pentru comparație, dar nu spun ce se plătește. Eticheta și descrierea
 * stau în dicționar (`camp.<slug>.*`). Variantele `_min` / `_max` (comisionul
 * minim sau maxim al unui procent: „0,1%, minim 5 lei”) iau eticheta conceptului
 * de bază plus sufixul. Un concept nou, fără intrare, apare ca slug cu spații,
 * nu dispare. Pe 05.10.2026, în `mip_stack`, 76 din cele 129 de concepte n-aveau
 * etichetă (nici în aplicația veche): 53 erau variante _min/_max, restul de 23 au
 * primit etichete atunci.
 */
function cuSufix(camp: string): [string, DictKey | null] {
  const m = /^(.+)_(min|max)$/.exec(camp)
  return m ? [m[1]!, `camp.sufix.${m[2]}` as DictKey] : [camp, null]
}

export function etNume(camp: string, t: Tr): string {
  const k = `camp.${camp}.eticheta`
  if (areCheie(k)) return t(k)
  const [baza, sufix] = cuSufix(camp)
  const kb = `camp.${baza}.eticheta`
  if (sufix && areCheie(kb)) return `${t(kb)} · ${t(sufix)}`
  return camp.replace(/_/g, ' ')
}

export function etDesc(camp: string, t: Tr): string {
  const k = `camp.${camp}.descriere`
  if (areCheie(k)) return t(k)
  const kb = `camp.${cuSufix(camp)[0]}.descriere`
  return areCheie(kb) ? t(kb) : ''
}

/** Unitatea lipită de cifră: „ lei”, „ EUR”, „%”; o unitate necunoscută apare cum vine. */
export function unitTxt(u: string | null | undefined, t: Tr): string {
  if (!u) return ''
  const k = `unitate.${u}`
  return areCheie(k) ? t(k) : ' ' + u
}
