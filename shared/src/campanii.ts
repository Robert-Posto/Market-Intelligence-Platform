/**
 * 2.4: campaniile de pe site-uri (/api/campanii) și comunicatele (/api/comunicate).
 * Overview folosește `randuri[].banca/stare/in_comparatie` și `rulare.campanii`;
 * comutatorul de secțiuni numără `randuri` și lungimea comunicatelor; restul
 * câmpurilor le folosesc secțiunile „Campanii pe site-uri” și „Comunicate”.
 *
 * Coloanele vin din vederea `campanii_curente` și din tabela `comunicate`, toate
 * nullable în bază, de aceea aproape toate sunt `.nullable()`. Pe 05.10.2026
 * ambele erau goale în `mip_stack`: forma e scrisă după SELECT-ul din
 * app/server.py (campanii(), comunicate()), nu verificată pe rânduri reale.
 */
import { z } from 'zod'

const text = z.string().nullable()

/** Un document al campaniei (campanii_surse), fără hub-ul din care s-a citit eticheta. */
export const DocumentCampanie = z
  .object({
    url: z.string(),
    rol: z.string(),
    format: text,
    eticheta: text.optional(),
    fara_text: z.boolean().nullable().optional(),
    in_bronze: z.boolean().nullable().optional(),
  })
  .passthrough()
export type DocumentCampanie = z.infer<typeof DocumentCampanie>

export const Campanie = z
  .object({
    banca: z.string(),
    stare: z.string().nullable(),
    in_comparatie: z.boolean().nullable().optional(),
    id: z.number().optional(),
    titlu: text.optional(),
    titlu_din: text.optional(),
    beneficiu: text.optional(),
    segment: text.optional(),
    categorie_produs: text.optional(),
    tip_oferta: text.optional(),
    organizator: text.optional(),
    organizator_citat: text.optional(),
    fereastra_start: text.optional(),
    fereastra_sfarsit: text.optional(),
    fereastra_citat: text.optional(),
    sursa_ferestrei: text.optional(),
    act_aditional: z.boolean().nullable().optional(),
    motiv_verificare: text.optional(),
    incheiata_azi: z.boolean().nullable().optional(),
    url: text.optional(),
    documente: z.array(DocumentCampanie).nullable().optional(),
  })
  .passthrough()
export type Campanie = z.infer<typeof Campanie>

/** Starea colectării pe bancă: colectat, blocat, in_afara_scopului, fara_config; motivul e text românesc al serverului. */
export const BancaCampanii = z
  .object({
    banca: z.string(),
    stare: z.string().optional(),
    motiv: text.optional(),
    comunicate: z.number().optional(),
  })
  .passthrough()
export type BancaCampanii = z.infer<typeof BancaCampanii>

export const Campanii = z
  .object({
    randuri: z.array(Campanie),
    banci: z.array(BancaCampanii).optional(),
    rulare: z
      .object({ campanii: z.string().nullable(), comunicate: z.string().nullable() })
      .passthrough()
      .nullable()
      .optional(),
  })
  .passthrough()
export type Campanii = z.infer<typeof Campanii>

export const Comunicat = z
  .object({
    banca: z.string(),
    id: z.number().optional(),
    titlu: text.optional(),
    titlu_din: text.optional(),
    data_publicarii: text.optional(),
    data_din: text.optional(),
    e_campanie: z.boolean().nullable().optional(),
    e_campanie_potrivire: text.optional(),
    url: text.optional(),
  })
  .passthrough()
export type Comunicat = z.infer<typeof Comunicat>

export const Comunicate = z.array(Comunicat)
export type Comunicate = z.infer<typeof Comunicate>
