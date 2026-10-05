/**
 * 2.4: campaniile de pe site-uri (/api/campanii) și comunicatele (/api/comunicate).
 * Câmpurile de aici sunt cele folosite de Overview și de numărătoarea de pe
 * comutatorul de secțiuni; secțiunile pot adăuga câmpuri (`passthrough()` lasă
 * restul să treacă).
 */
import { z } from 'zod'

export const Campanii = z
  .object({
    randuri: z.array(
      z
        .object({
          banca: z.string(),
          stare: z.string().nullable(),
          in_comparatie: z.boolean().nullable().optional(),
        })
        .passthrough(),
    ),
    banci: z.array(z.object({ banca: z.string() }).passthrough()).optional(),
    rulare: z
      .object({ campanii: z.string().nullable(), comunicate: z.string().nullable() })
      .passthrough()
      .nullable()
      .optional(),
  })
  .passthrough()
export type Campanii = z.infer<typeof Campanii>

export const Comunicate = z.array(z.object({ banca: z.string() }).passthrough())
export type Comunicate = z.infer<typeof Comunicate>
