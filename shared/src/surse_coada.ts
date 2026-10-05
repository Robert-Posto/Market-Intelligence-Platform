/**
 * Surse (/api/surse) și Coada de verificare (/api/coada). Scrise după
 * răspunsurile serverului Python din 05.10.2026 (6.332 de surse, 5.396 de
 * valori în coadă); `passthrough()`: un câmp nou de la server nu strică interfața.
 *
 * Numele sunt lungi intenționat: `shared/src/index.ts` le reexportă pe toate
 * într-un singur spațiu, iar „Surse” sau „Coada” s-ar putea ciocni cu alte zone.
 */
import { z } from 'zod'

const text = z.string().nullable()

/** O sursă (document sau pagină) cu câte valori a dat și, dacă n-a dat, de ce. */
export const SursaInventar = z
  .object({
    banca: z.string(),
    banca_nume: text,
    sursa: text,
    tip_sursa: text,
    format: text,
    rol: text,
    status: text,
    metoda_extractie: text,
    nota_extractie: text,
    url_public: text,
    observatii: z.number(),
    fisier: text,
  })
  .passthrough()
export type SursaInventar = z.infer<typeof SursaInventar>

/** Rândul din tabelul „Pe bancă”: toate cele 30 de bănci, și cele fără nicio sursă. */
export const SurseInventarBanca = z
  .object({
    slug: z.string(),
    nume: z.string(),
    total: z.number(),
    cu_date: z.number(),
    incercate: z.number(),
    neatinse: z.number(),
    blocate: z.number(),
  })
  .passthrough()
export type SurseInventarBanca = z.infer<typeof SurseInventarBanca>

export const SurseInventar = z
  .object({
    total: z.number(),
    limit: z.number(),
    offset: z.number(),
    randuri: z.array(SursaInventar),
    /** lista de bănci din filtru (doar cele cu surse), ordonată după nume pe server */
    banci: z.array(z.object({ slug: z.string(), nume: z.string(), surse: z.number() }).passthrough()),
    pe_banca: z.array(SurseInventarBanca),
    bilant: z.object({ total: z.number(), cu_date: z.number(), incercate: z.number(), neatinse: z.number() }).passthrough(),
    /** prima bucată din `nota_extractie` (până la „:”), cu câte surse o au */
    motive: z.array(z.object({ motiv: z.string(), n: z.number() }).passthrough()),
  })
  .passthrough()
export type SurseInventar = z.infer<typeof SurseInventar>

/** O valoare din coadă, cu tot ce cere o decizie umană (citat, pagină, legătura spre document). */
export const ValoareCoada = z
  .object({
    id: z.number(),
    banca: z.string(),
    banca_nume: text,
    produs: text,
    camp: z.string(),
    serviciu: text,
    valoare_num: z.number().nullable(),
    unitate: text,
    confidence: z.number().nullable(),
    ambiguu: z.boolean().nullable(),
    /** motivul din vederea coada_verificare: valoare din bază, în română, și cheie de filtru */
    motiv: z.string(),
    motiv_ambiguu: text,
    citat: text,
    pagina: z.number().nullable(),
    sursa: text,
    tip_sursa: text,
    url_public: text,
    metoda_extractie: text,
    link: text,
    link_pagina: text,
    fisier: text,
    ancora: text,
  })
  .passthrough()
export type ValoareCoada = z.infer<typeof ValoareCoada>

export const CoadaVerificare = z
  .object({
    pe_motiv: z.array(z.object({ motiv: z.string(), n: z.number() }).passthrough()),
    pe_banca: z.array(z.object({ banca: z.string(), banca_nume: text, n: z.number() }).passthrough()),
    pe_produs: z.array(z.object({ produs: text, n: z.number() }).passthrough()),
    matrice: z.array(z.object({ banca: z.string(), banca_nume: text, motiv: z.string(), n: z.number() }).passthrough()),
    context: z.object({ observatii_total: z.number(), in_coada: z.number(), in_coada_cu_link: z.number() }).passthrough(),
    total: z.number(),
    offset: z.number(),
    limit: z.number(),
    randuri: z.array(ValoareCoada),
    /** `banca|camp|serviciu` → toate valorile băncii la acel serviciu (primele 14 distincte) și câte sunt */
    fratii: z.record(z.string(), z.object({ valori: z.array(z.number()), n: z.number() }).passthrough()),
  })
  .passthrough()
export type CoadaVerificare = z.infer<typeof CoadaVerificare>
