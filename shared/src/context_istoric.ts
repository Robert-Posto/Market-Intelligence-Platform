/**
 * Istoric & schimbări (/api/istoric). Pagina 2.6 Context de piață citește
 * /api/indici cu schema `Indici` din rate_mobil.ts: e aceeași cerere ca reperul
 * din 2.2, deci o singură schemă.
 *
 * Scrise după răspunsul serverului Python din 05.10.2026 (883 de schimbări
 * afișate, 17 peste pragul de plauzibilitate); `passthrough()`: un câmp nou de
 * la server nu strică interfața.
 */
import { z } from 'zod'

/** O schimbare: același serviciu, la aceeași bancă, cu altă valoare la altă dată de vigoare (vederea schimbari_pret). */
export const SchimbarePret = z
  .object({
    banca: z.string(),
    camp: z.string(),
    serviciu: z.string().nullable(),
    unitate: z.string().nullable(),
    data_ant: z.string().nullable(),
    valoare_ant: z.number().nullable(),
    data_noua: z.string().nullable(),
    valoare_noua: z.number().nullable(),
    delta: z.number().nullable(),
    /** gol când valoarea veche era 0 (9 rânduri la 05.10.2026): procentul n-are sens */
    delta_pct: z.number().nullable(),
    citat: z.string().nullable(),
    pagina: z.number().nullable(),
    sursa: z.string().nullable(),
    url_public: z.string().nullable(),
  })
  .passthrough()
export type SchimbarePret = z.infer<typeof SchimbarePret>

export const IstoricPreturi = z
  .object({
    /** câte schimbări au valori peste prag (capitalul social citit ca comision); stau în coada de verificare */
    excluse_implauzibile: z.number(),
    randuri: z.array(SchimbarePret),
    /** pentru meniul de bănci: pe toate băncile, fără filtrul de bancă */
    pe_banca: z.array(z.object({ banca: z.string(), n: z.number() }).passthrough()),
    /** observațiile pe stare de datare; „fără datare” e cheia trimisă de server, nu un text de afișat */
    acoperire: z.array(z.object({ stare: z.string(), n: z.number() }).passthrough()),
  })
  .passthrough()
export type IstoricPreturi = z.infer<typeof IstoricPreturi>
