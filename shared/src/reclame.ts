/**
 * 2.4: reclamele Bing (/api/reclame_bing) și Google (/api/reclame_google), din
 * fișiere locale în output/reclame/, nu din bază (până la avizul juridic).
 * Câmpurile de aici sunt cele cerute de numărătoarea de pe comutator; secțiunile
 * pot adăuga câmpuri.
 */
import { z } from 'zod'

export const ReclameBing = z
  .object({
    fotografie: z.string().nullable(),
    banci_verificate: z.number(),
    oprit: z.unknown().nullable().optional(),
    reclame: z.array(z.object({ banca: z.string(), pondere_ro: z.number().nullable() }).passthrough()),
  })
  .passthrough()
export type ReclameBing = z.infer<typeof ReclameBing>

export const ReclameGoogle = z
  .object({
    fotografie: z.string().nullable(),
    total: z.number(),
  })
  .passthrough()
export type ReclameGoogle = z.infer<typeof ReclameGoogle>
