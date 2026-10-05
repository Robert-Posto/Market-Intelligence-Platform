/**
 * 2.4: canalele YouTube (/api/youtube, din output/youtube/, nu din bază) și
 * conturile sociale (/api/retele, din date/retele_sociale.csv). Câmpurile de
 * aici sunt cele cerute de Overview și de comutator; secțiunile pot adăuga.
 */
import { z } from 'zod'

export const ContSocial = z
  .object({ slug: z.string(), retea: z.string(), url: z.string().nullable() })
  .passthrough()
export const Retele = z.array(ContSocial)
export type Retele = z.infer<typeof Retele>

export const Youtube = z
  .object({
    data_extragerii: z.string().nullable(),
    sterge_la: z.string().nullable(),
    motiv: z.string().nullable().optional(),
    banci: z.record(z.string(), z.unknown()),
  })
  .passthrough()
export type Youtube = z.infer<typeof Youtube>
