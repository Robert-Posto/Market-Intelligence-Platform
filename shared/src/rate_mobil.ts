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

/**
 * /api/indici: indicii BNR (ROBOR, ROBID, IRCC). 2.2 arată doar reperul (ROBOR 3M
 * din ultima zi, IRCC în vigoare); pagina lor e 2.6. `valoare` vine din coloana
 * `numeric` a bazei, deci ca text („5.6400”).
 */
export const Indici = z.array(
  z
    .object({
      indice: z.string(),
      scadenta: z.string().nullable(),
      valoare: z.union([z.string(), z.number()]).nullable(),
      valabil_din: z.string().nullable(),
      valabil_pana: z.string().nullable(),
      sursa: z.string().nullable(),
    })
    .passthrough(),
)
export type Indici = z.infer<typeof Indici>

/**
 * /api/sentiment: recenziile din App Store, filtrabile pe bancă, notă și magazin.
 * `sumar` și `storefronts` rămân pe toate băncile (serverul nu le filtrează), ca
 * să se vadă cu ce se compară banca aleasă; `recente` și `total_filtrat` urmează filtrul.
 */
export const Sentiment = z
  .object({
    sumar: z.array(
      z
        .object({
          banca: z.string(),
          nume: z.string(),
          review_uri: z.number(),
          medie_text: z.number().nullable(),
          medie_store: z.number().nullable(),
          volum_store: z.number().nullable(),
          negative: z.number(),
        })
        .passthrough(),
    ),
    storefronts: z.array(z.object({ storefront: z.string().nullable(), n: z.number() }).passthrough()),
    total_filtrat: z.number(),
    recente: z.array(
      z
        .object({
          banca: z.string(),
          banca_nume: z.string().nullable(),
          rating: z.number().nullable(),
          storefront: z.string().nullable(),
          versiune: z.string().nullable(),
          text: z.string().nullable(),
          autor: z.string().nullable(),
          postat_la: z.string().nullable(),
          raspuns_banca: z.string().nullable(),
        })
        .passthrough(),
    ),
  })
  .passthrough()
export type Sentiment = z.infer<typeof Sentiment>
