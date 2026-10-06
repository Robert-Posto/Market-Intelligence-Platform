import { z } from 'zod'

/**
 * Fișierele din `date/` citite la build, nu prin API: `google_play.json` și
 * `google_play_recenzii.json` (ingest/google_play_app.mjs --salveaza) și `rezumate_recenzii.json` (rezumatele AI). Sunt în
 * .gitignore ca restul rezultatelor din date/, deci la un coleg care nu le are
 * `import.meta.glob` dă un obiect gol și pagina arată „necolectat”, fără eroare de build.
 */
const fisiere = import.meta.glob('../../../../date/{google_play,google_play_recenzii,rezumate_recenzii,rezumate_recenzii_play}.json', { eager: true, import: 'default' })
const fisier = (nume: string) => Object.entries(fisiere).find(([cale]) => cale.endsWith(`/${nume}`))?.[1]

const Text = z.object({ ro: z.string(), en: z.string() })
export type TextRoEn = z.infer<typeof Text>

const Rezumate = z.object({
  generat_la: z.string(),
  generat_de: z.string(),
  aplicatii: z.record(z.object({
    n_recenzii: z.number(),
    nota_medie: z.number().nullable(),
    rezumat: Text,
    pro: z.array(Text),
    contra: z.array(Text),
  })),
})
export type Rezumat = z.infer<typeof Rezumate>['aplicatii'][string]

const GooglePlay = z.object({
  colectat_la: z.string(),
  aplicatii: z.record(z.object({
    package: z.string(),
    url: z.string(),
    nume: z.string().nullable(),
    icon: z.string().nullable(),
    nota: z.number().nullable(),
    evaluari: z.number().nullable(),
    recenzii_scrise: z.number().nullable(),
    prag_descarcari: z.string().nullable(),
    descarcari: z.number().nullable(),
    // câmpurile de mai jos vin doar din colectorul Node (ingest/google_play_app.mjs --salveaza)
    distributie_stele: z.array(z.number()).nullable().optional(),
    versiune: z.string().nullable().optional(),
    actualizat_la: z.string().nullable().optional(),
    ce_e_nou: z.string().nullable().optional(),
    android_minim: z.string().nullable().optional(),
    capturi: z.array(z.string()).optional(),
    video: z.string().nullable().optional(),
  }).passthrough()),
})
export type AplicatiePlay = z.infer<typeof GooglePlay>['aplicatii'][string]

// un fișier stricat nu dărâmă pagina: se tratează ca lipsă
const rez = Rezumate.safeParse(fisier('rezumate_recenzii.json'))
const rezPlay = Rezumate.safeParse(fisier('rezumate_recenzii_play.json'))
const play = GooglePlay.safeParse(fisier('google_play.json'))

export const rezumate = rez.success ? rez.data : null
/** Rezumatele AI din recenziile Google Play (`date/rezumate_recenzii_play.json`), aceeași formă. */
export const rezumatePlay = rezPlay.success ? rezPlay.data : null
export const googlePlay = play.success ? play.data : null

/** Datele Google Play ale unei aplicații, după `package` (o bancă poate avea mai multe aplicații Android). */
export const playDupaPachet = (pachet: string): AplicatiePlay | undefined =>
  Object.values(googlePlay?.aplicatii ?? {}).find((x) => x.package === pachet)

const RecenziiPlay = z.object({
  colectat_la: z.string(),
  aplicatii: z.record(z.object({
    package: z.string(),
    recenzii: z.array(z.object({
      id: z.string(),
      nota: z.number(),
      text: z.string().nullable(),
      data: z.string().nullable(),
      utile: z.number().nullable(),
      raspuns_banca: z.string().nullable(),
      raspuns_data: z.string().nullable(),
      versiune: z.string().nullable(),
    }).passthrough()),
  })),
})
export type RecenziePlay = z.infer<typeof RecenziiPlay>['aplicatii'][string]['recenzii'][number]
const recPlay = RecenziiPlay.safeParse(fisier('google_play_recenzii.json'))

/** Recenziile din Google Play ale unei aplicații, după `package`; [] dacă fișierul lipsește. */
export const recenziiPlay = (pachet: string): RecenziePlay[] =>
  (recPlay.success ? Object.values(recPlay.data.aplicatii).find((x) => x.package === pachet)?.recenzii : undefined) ?? []
