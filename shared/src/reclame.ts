/**
 * 2.4: reclamele Bing (/api/reclame_bing) și Google (/api/reclame_google), din
 * fișiere locale în output/reclame/, nu din bază (până la avizul juridic).
 * Comutatorul de secțiuni numără `reclame[].pondere_ro` la Bing și `total` la
 * Google; restul câmpurilor le folosesc secțiunile.
 */
import { z } from 'zod'

const text = z.string().nullable().optional()

/**
 * O reclamă din Microsoft Ad Library, cum o trimite serverul (app/server.py,
 * reclame_bing). Câmpurile vin din API-ul Microsoft aproape neatinse, deci sunt
 * îngăduitoare: pe 05.10.2026 nu exista niciun fișier microsoft_*.json pe care
 * să le verificăm forma.
 */
export const ReclamaBing = z
  .object({
    banca: z.string(),
    pondere_ro: z.number().nullable(),
    advertiser: text,
    titlu: text,
    text: text,
    start: text,
    sfarsit: text,
    // TotalImpressionsRange: un interval scris („1K-5K”), parsat la sortare
    afisari: z.union([z.string(), z.number()]).nullable().optional(),
    platitor: text,
    link_biblioteca: text,
  })
  .passthrough()
export type ReclamaBing = z.infer<typeof ReclamaBing>

export const ReclameBing = z
  .object({
    fotografie: z.string().nullable(),
    banci_verificate: z.number(),
    oprit: z.unknown().nullable().optional(),
    reclame: z.array(ReclamaBing),
  })
  .passthrough()
export type ReclameBing = z.infer<typeof ReclameBing>

/** O bancă în rezumatul Google (banda, „Pe bănci”, filialele). */
export const BancaGoogle = z
  .object({
    banca: z.string(),
    n: z.number(),
    active7: z.number(),
    noi30: z.number(),
    af_jos: z.number(),
    af_sus: z.number(),
    af_deschis: z.boolean(),
  })
  .passthrough()
export type BancaGoogle = z.infer<typeof BancaGoogle>

/** O reclamă din Google Ads Transparency Center (o variantă de creație, nu o campanie). */
export const ReclamaGoogle = z
  .object({
    banca: z.string(),
    filiala: z.boolean(),
    advertiser: z.string().nullable(),
    platitor: z.string().nullable(),
    format: z.string().nullable(),
    tema: z.string().nullable(),
    platforma: z.string(),
    platforme: z.string(),
    prima: z.string().nullable(),
    ultima: z.string().nullable(),
    af_jos: z.number().nullable(),
    af_sus: z.number().nullable(),
    af_deschis: z.boolean(),
    af_din: z.string().nullable(),
    advertiser_id: z.string(),
    creative_id: z.string(),
  })
  .passthrough()
export type ReclamaGoogle = z.infer<typeof ReclamaGoogle>

const numaratoare = z.record(z.string(), z.number())

/**
 * Răspunsul Google: agregatele pe tot setul (aceleași la orice filtru) plus
 * pagina curentă din filtru. Fără fotografie, serverul trimite doar golurile,
 * fără `fisier`, `ultima_zi`, `ordine` și celelalte, de aceea sunt opționale.
 */
export const ReclameGoogle = z
  .object({
    fotografie: z.string().nullable(),
    total: z.number(),
    fisier: z.string().optional(),
    ultima_zi: z.string().nullable().optional(),
    afisari_pana_la: z.string().nullable().optional(),
    lasate_deoparte: numaratoare.optional(),
    banci: z.array(BancaGoogle),
    filiale: z.array(BancaGoogle),
    formate: z.array(z.string()),
    platforme: z.array(z.string()),
    filtrat: z
      .object({ n: z.number(), pe_format: numaratoare, pe_platforma: numaratoare, banci: z.number() })
      .passthrough(),
    ordine: z.string().optional(),
    sens: z.string().optional(),
    offset: z.number(),
    limit: z.number(),
    randuri: z.array(ReclamaGoogle),
  })
  .passthrough()
export type ReclameGoogle = z.infer<typeof ReclameGoogle>
