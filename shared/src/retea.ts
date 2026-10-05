/**
 * Schemele zonei „retea”: 2.5 Rețea & operațional și harta (/api/locatii).
 *
 * Numele au prefixul `Retea`: fișa băncii citește și ea /api/locatii, cu
 * schemele ei, iar toate fișierele din shared/src se exportă din același index.
 */
import { z } from 'zod'

/** Rețeaua unei bănci, numărată pe server peste toate locațiile ei. */
export const ReteaBanca = z
  .object({
    slug: z.string(),
    nume: z.string(),
    sucursale: z.number(),
    /** doar ATM-urile din rețeaua proprie */
    atm: z.number(),
    /** ATM-uri din rețele comune (ex. Euronet), afișate de bancă pentru clienții ei */
    atm_parteneri: z.number(),
    total: z.number(),
  })
  .passthrough()
export type ReteaBanca = z.infer<typeof ReteaBanca>

/** Un punct de pe hartă: sucursală sau ATM. */
export const ReteaPunct = z
  .object({
    id: z.number(),
    banca: z.string(),
    banca_nume: z.string(),
    tip: z.string(),
    nume: z.string().nullable(),
    adresa: z.string().nullable(),
    sector: z.string().nullable(),
    lat: z.number(),
    lon: z.number(),
    program: z.string().nullable(),
    /** `overture`, `locator_banca`, `mock` (constrângerea din migrarea 014 mai permite `google_places`, `onrc`) */
    sursa: z.string().nullable(),
    rating: z.number().nullable(),
    nr_recenzii: z.number().nullable(),
    furnizori: z.string().nullable(),
    /** `proprie` sau `partener` */
    retea: z.string().nullable(),
  })
  .passthrough()
export type ReteaPunct = z.infer<typeof ReteaPunct>

export const ReteaLocatii = z
  .object({
    banci: z.array(ReteaBanca),
    total: z.number(),
    puncte: z.array(ReteaPunct),
  })
  .passthrough()
export type ReteaLocatii = z.infer<typeof ReteaLocatii>
