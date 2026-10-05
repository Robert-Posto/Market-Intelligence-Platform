/**
 * Schemele fișei unei bănci (#/banca?b=<slug>). Scrise după răspunsurile
 * serverului Python din 05.10.2026; `passthrough()`: un câmp nou de la server
 * nu strică interfața.
 *
 * Fișa citește și răspunsuri pe care alte pagini le descriu complet (acoperirea,
 * matricea, locațiile). Aici stă doar ce folosește fișa, cu nume proprii
 * (`…Fisa`): schemele comune din index.ts nu se pot extinde de aici (index.ts
 * reexportă fișierul acesta, deci importul ar fi circular), iar /api/locatii îl
 * descrie zona Rețea.
 */
import { z } from 'zod'

export const _banca = z.object({})

/** /api/acoperire, rândul unei bănci: cifrele din casete și din butoanele barei. */
export const AcoperireFisaBanca = z
  .object({
    slug: z.string(),
    nume: z.string(),
    comisioane: z.number(),
    dobanzi: z.number(),
    rating: z.number().nullable(),
    /** câte note are aplicația în App Store (volum_rating) */
    note: z.number().nullable(),
    surse: z.number(),
    blocate: z.number(),
    schimbari: z.number(),
    in_coada: z.number(),
  })
  .passthrough()
export const AcoperireFisa = z.object({ pe_banca: z.array(AcoperireFisaBanca) }).passthrough()
export type AcoperireFisa = z.infer<typeof AcoperireFisa>

/** /api/matrice: fișa arată și valoarea tipică (`valoare`), pe care matricea 2.1 n-o folosește. */
export const CelulaMatriceFisa = z
  .object({
    banca: z.string(),
    camp: z.string(),
    n: z.number(),
    minim: z.number(),
    maxim: z.number(),
    gratuite: z.number(),
    valoare: z.number().nullable(),
  })
  .passthrough()
export const MatriceFisa = z.object({ celule: z.array(CelulaMatriceFisa) }).passthrough()
export type MatriceFisa = z.infer<typeof MatriceFisa>

/** /api/locatii: din tot răspunsul (și cele 683 de puncte), fișa folosește doar totalurile pe bancă. */
export const LocatiiFisa = z
  .object({
    banci: z.array(
      z
        .object({
          slug: z.string(),
          sucursale: z.number(),
          atm: z.number(),
          atm_parteneri: z.number(),
        })
        .passthrough(),
    ),
  })
  .passthrough()
export type LocatiiFisa = z.infer<typeof LocatiiFisa>

/**
 * /api/catalog_libra: catalogul intern de produse Libra (migrarea 020), din
 * exportul Sales Command Center, nu de pe web. Sumele și vechimea vin ca
 * `float8` din server; `generat_la` e un TIMESTAMP trimis ca text.
 */
export const ProdusCatalogLibra = z
  .object({
    cod: z.string(),
    denumire: z.string(),
    categorie: z.string().nullable(),
    categorie_cod: z.string().nullable(),
    produs_prioritar: z.boolean(),
    adresabilitate: z.string().nullable(),
    segment: z.string().nullable(),
    caracteristici: z.string().nullable(),
    criterii_eligibilitate: z.string().nullable(),
    cand_recomand: z.string().nullable(),
    cifra_afaceri_min: z.number().nullable(),
    cifra_afaceri_max: z.number().nullable(),
    vechime_min_ani: z.number().nullable(),
    vechime_max_ani: z.number().nullable(),
    linii_business: z.string().nullable(),
    caen_prefixe: z.string().nullable(),
    fisier: z.string(),
    generat_la: z.string().nullable(),
  })
  .passthrough()
export type ProdusCatalogLibra = z.infer<typeof ProdusCatalogLibra>
export const CatalogLibra = z.array(ProdusCatalogLibra)
