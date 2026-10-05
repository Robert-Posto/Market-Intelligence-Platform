/**
 * 2.2 Rate & indicatori (/api/rate) și 2.3 Aplicații & recenzii (/api/mobil).
 * Scrise după răspunsurile serverului Python din 05.10.2026; `passthrough()`:
 * un câmp nou de la server nu strică interfața.
 */
import { z } from 'zod'

export const CelulaRata = z
  .object({
    banca: z.string(),
    camp: z.string(),
    n: z.number(),
    minim: z.number(),
    maxim: z.number(),
    valoare: z.number().nullable(),
    serviciu: z.string().nullable(),
    frecventa: z.string().nullable(),
    conditie: z.string().nullable(),
    luni: z.number().nullable(),
  })
  .passthrough()

const Optiune = z.object({ cheie: z.string(), eticheta: z.string(), n: z.number() }).passthrough()

export const Rate = z
  .object({
    categorie: z.string(),
    titlu: z.string(),
    sens: z.string(),
    campuri: z.array(z.string()),
    prag: z.number(),
    termen: z.string(),
    produs: z.string(),
    termene: z.array(Optiune),
    produse: z.array(Optiune),
    celule: z.array(CelulaRata),
    excluse_implauzibile: z.number(),
    provenienta: z.array(z.object({ metoda: z.string(), valori: z.number(), banci: z.number() }).passthrough()),
  })
  .passthrough()
export type Rate = z.infer<typeof Rate>

export const Mobil = z
  .object({
    versiuni: z.array(
      z
        .object({
          banca: z.string(),
          platforma: z.string(),
          app_id: z.string().nullable(),
          versiune: z.string().nullable(),
          note_lansare: z.string().nullable(),
          rating_agregat: z.string().nullable(),
          volum_rating: z.number().nullable(),
          distributie_stele: z.array(z.number()).nullable(),
        })
        .passthrough(),
    ),
    review_sumar: z.array(
      z
        .object({
          banca: z.string(),
          storefront: z.string().nullable(),
          review_uri: z.number(),
          rating_mediu_text: z.string().nullable(),
          rating_agregat_store: z.string().nullable(),
        })
        .passthrough(),
    ),
    review_recente: z.array(
      z
        .object({
          banca: z.string(),
          storefront: z.string().nullable(),
          rating: z.number().nullable(),
          versiune: z.string().nullable(),
          text: z.string().nullable(),
          autor: z.string().nullable(),
          postat_la: z.string().nullable(),
        })
        .passthrough(),
    ),
    screenshoturi: z.array(z.object({ banca: z.string(), url: z.string() }).passthrough()),
  })
  .passthrough()
export type Mobil = z.infer<typeof Mobil>
