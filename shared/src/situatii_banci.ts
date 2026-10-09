/**
 * /api/situatii_banci: situațiile financiare anuale ale instituțiilor de credit, din datele
 * deschise ale Ministerului Finanțelor (data.gov.ro), normalizate de
 * ingest/situatii_financiare_mf.py pe indicatori comuni tuturor anilor. Sumele sunt în lei;
 * `null` = indicator neraportat în acel an.
 */
import { z } from 'zod'

const suma = z.number().nullable().optional()

export const IndicatoriSituatie = z
  .object({
    active: suma,
    credite: suma,
    datorii: suma,
    numerar: suma,
    capital_social: suma,
    profit_brut: suma,
    profit_net: suma,
  })
  .passthrough()
export type IndicatoriSituatie = z.infer<typeof IndicatoriSituatie>

export const BancaSituatie = z
  .object({
    cui: z.number(),
    /** denumirea de la ANAF, cum e în registru (majuscule, fără prescurtări) */
    nume: z.string(),
    /** banca monitorizată din tabela `banci`; null = bancă care nu e (sau nu mai e) urmărită */
    slug: z.string().nullable(),
    tip: z.enum(['banca', 'sucursala', 'cooperativa']),
    primul_an: z.number(),
    ultimul_an: z.number(),
    valori: z.record(z.string(), IndicatoriSituatie),
  })
  .passthrough()
export type BancaSituatie = z.infer<typeof BancaSituatie>

export const SituatiiBanci = z.discriminatedUnion('disponibil', [
  z.object({ disponibil: z.literal(false), motiv: z.string() }),
  z
    .object({
      disponibil: z.literal(true),
      sursa: z.string(),
      generat_la: z.string(),
      ani: z.array(z.number()),
      /** forma fișierului pe an (A–D): coloanele MF s-au schimbat de trei ori din 2012 */
      forme: z.record(z.string(), z.string()),
      /** suma tuturor entităților din fișierul anului: numitorul cotelor de piață */
      total: z.record(z.string(), IndicatoriSituatie),
      /** bănci lipsă dintr-un an în care ar fi trebuit să fie (BRD în 2021): cotele acelui an ies umflate */
      goluri: z.record(z.string(), z.array(z.object({ cui: z.number(), nume: z.string(), cota_estimata: z.number() }).passthrough())).optional(),
      banci: z.array(BancaSituatie),
    })
    .passthrough(),
])
export type SituatiiBanci = z.infer<typeof SituatiiBanci>
