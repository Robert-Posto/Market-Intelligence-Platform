import type { DictKey, Params } from '../i18n'

type Tr = (k: DictKey, p?: Params) => string

/**
 * Conceptele canonice din vocabular.py sunt slug-uri („retragere_numerar”):
 * bune pentru comparație, dar nu spun ce se plătește. Eticheta și descrierea
 * stau în dicționar (`camp.<slug>.*`); un concept nou, fără intrare, apare ca
 * slug cu spații, nu dispare.
 */
export function etNume(camp: string, t: Tr): string {
  const k = `camp.${camp}.eticheta` as DictKey
  const v = t(k)
  return v === k ? camp.replace(/_/g, ' ') : v
}

export function etDesc(camp: string, t: Tr): string {
  const k = `camp.${camp}.descriere` as DictKey
  const v = t(k)
  return v === k ? '' : v
}

/** Unitatea lipită de cifră: „ lei”, „ EUR”, „%”; o unitate necunoscută apare cum vine. */
export function unitTxt(u: string | null | undefined, t: Tr): string {
  if (!u) return ''
  const k = `unitate.${u}` as DictKey
  const v = t(k)
  return v === k ? ' ' + u : v
}
