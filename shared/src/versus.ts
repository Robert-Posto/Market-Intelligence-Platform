/**
 * Schemele zonei „versus”: Versus Libra.
 *
 * Numele au prefixul `Versus`: toate fișierele din shared/src se exportă din
 * același index, iar 2.1 și fișa băncii citesc și ele /api/matrice, cu schemele lor.
 * Scrise după răspunsurile serverului Python din 05.10.2026; `passthrough()`:
 * un câmp nou de la server nu strică interfața.
 */
import { z } from 'zod'

export const _versus = z.object({})

/**
 * O celulă din /api/matrice cu valoarea reprezentativă: Versus arată mediana
 * (rândul de la mijloc, cu serviciul și frecvența lui), nu doar intervalul ca 2.1.
 */
export const VersusCelulaMatrice = z
  .object({
    banca: z.string(),
    camp: z.string(),
    n: z.number(),
    minim: z.number(),
    maxim: z.number(),
    gratuite: z.number(),
    valoare: z.number().nullable(),
    unitate: z.string().nullable(),
    serviciu: z.string().nullable(),
    frecventa: z.string().nullable(),
    conditie: z.string().nullable(),
  })
  .passthrough()
export type VersusCelulaMatrice = z.infer<typeof VersusCelulaMatrice>

/** /api/matrice cu titlul grupului (în română, de la server) și sensul comparației. */
export const VersusMatrice = z
  .object({
    grup: z.string(),
    titlu: z.string(),
    sens: z.string(),
    campuri: z.array(z.string()),
    celule: z.array(VersusCelulaMatrice),
  })
  .passthrough()
export type VersusMatrice = z.infer<typeof VersusMatrice>

/**
 * /api/versus_extra: rândurile de comparație care nu vin din prețuri — aplicația
 * (2.3), rețeaua (2.5), recenziile — și câte valori avem pe fiecare bancă.
 */
export const VersusExtra = z
  .object({
    mobil: z.array(
      z
        .object({
          banca: z.string(),
          platforma: z.string().nullable(),
          versiune: z.string().nullable(),
          rating: z.number().nullable(),
          volum: z.number().nullable(),
          capturi: z.number(),
        })
        .passthrough(),
    ),
    retea: z.array(
      z
        .object({
          banca: z.string(),
          sucursale: z.number(),
          atm: z.number(),
          rating_sucursale: z.number().nullable(),
        })
        .passthrough(),
    ),
    sentiment: z.array(
      z
        .object({
          banca: z.string(),
          review_uri: z.number(),
          medie_text: z.number().nullable(),
          pct_negative: z.number().nullable(),
        })
        .passthrough(),
    ),
    acoperire: z.array(
      z
        .object({
          banca: z.string(),
          servicii_cunoscute: z.number(),
          valori: z.number(),
        })
        .passthrough(),
    ),
  })
  .passthrough()
export type VersusExtra = z.infer<typeof VersusExtra>
