/**
 * Utilizatorii aplicației (/api/utilizatori, doar admin): rolul se dă în aplicație, nu în AD
 * (tabela `utilizatori`, migrarea 040, scrisă de app/utilizatori.py). Un cont apare aici la prima
 * logare reușită în AD, fără rol. Pe o bază fără tabelă serverul trimite `{disponibil: false}`.
 */
import { z } from 'zod'

const txt = z.string().nullable()

export const RolCont = z.enum(['admin', 'analist'])
export type RolCont = z.infer<typeof RolCont>

export const ContAplicatie = z
  .object({
    utilizator: z.string(),
    nume: z.string(),
    /** null = cont neaprobat: parola e bună, dar aplicația nu-l lasă să intre */
    rol: RolCont.nullable(),
    activ: z.boolean(),
    creat: z.string(),
    ultima_logare: txt,
    modificat: txt,
    modificat_de: txt,
  })
  .passthrough()
export type ContAplicatie = z.infer<typeof ContAplicatie>

export const ConturiAplicatie = z.discriminatedUnion('disponibil', [
  z.object({ disponibil: z.literal(false) }),
  z.object({ disponibil: z.literal(true), utilizatori: z.array(ContAplicatie) }),
])
export type ConturiAplicatie = z.infer<typeof ConturiAplicatie>
