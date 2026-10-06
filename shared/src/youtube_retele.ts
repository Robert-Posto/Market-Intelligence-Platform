/**
 * 2.4: canalele YouTube (/api/youtube, din output/youtube/, nu din bază) și
 * conturile sociale (/api/retele, din date/retele_sociale.csv). Câmpurile de
 * aici sunt cele cerute de Overview, de comutator și de cele două secțiuni.
 */
import { z } from 'zod'

const txt = z.string().nullable().optional()
const nr = z.number().nullable().optional()

/** Un rând din date/retele_sociale.csv: `url` e „NEGASIT” când rețeaua n-a apărut nici pe site, nici în căutare. */
export const ContSocial = z
  .object({
    slug: z.string(),
    retea: z.string(),
    url: z.string().nullable(),
    // „grup” = contul grupului internațional; „RO” = al băncii din România
    nivel: txt,
    // „site banca” sau „cautare web”
    sursa: txt,
    incredere: txt,
    nota: txt,
  })
  .passthrough()
export type ContSocial = z.infer<typeof ContSocial>
export const Retele = z.array(ContSocial)
export type Retele = z.infer<typeof Retele>

/** Cifrele canalului, cum le dă YouTube Data API (abonații vin rotunjiți chiar de YouTube). */
export const CanalYoutube = z
  .object({
    id: txt,
    titlu: txt,
    custom_url: txt,
    link: txt,
    creat_la: txt,
    abonati: nr,
    abonati_ascunsi: z.boolean().nullable().optional(),
    vizualizari: nr,
    videoclipuri: nr,
  })
  .passthrough()
export type CanalYoutube = z.infer<typeof CanalYoutube>

export const VideoclipYoutube = z
  .object({
    id: z.string(),
    titlu: txt,
    link: txt,
    publicat_la: txt,
    durata_sec: nr,
    vizualizari: nr,
    likeuri: nr,
    comentarii: nr,
    nou: z.boolean().optional(),
  })
  .passthrough()
export type VideoclipYoutube = z.infer<typeof VideoclipYoutube>

export const BancaYoutube = z
  .object({
    canal: CanalYoutube,
    // pagina băncii pe care s-a găsit linkul canalului
    dovada: txt,
    videoclipuri: z.array(VideoclipYoutube).nullable().optional(),
    // „data” sau „id-uri”: cum s-a stabilit eticheta „nou” pe canalul acesta
    metoda_nou: txt,
  })
  .passthrough()
export type BancaYoutube = z.infer<typeof BancaYoutube>

export const Youtube = z
  .object({
    data_extragerii: z.string().nullable(),
    sterge_la: z.string().nullable(),
    motiv: z.string().nullable().optional(),
    luni: nr,
    de_la: txt,
    nou_fata_de: txt,
    metoda_nou: txt,
    banci: z.record(z.string(), BancaYoutube),
  })
  .passthrough()
export type Youtube = z.infer<typeof Youtube>
