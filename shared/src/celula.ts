/**
 * Rândurile din spatele unei celule (/api/celula), folosite de Sertar și de Vox.
 * Separat de index.ts ca alte fișiere din shared să le poată importa fără import circular.
 */
import { z } from 'zod'

/** O valoare din sertarul cu dovezi (/api/celula). */
export const ValoareDovada = z
  .object({
    valoare: z.number().nullable(),
    valoare_text: z.string().nullable(),
    unitate: z.string().nullable(),
    cod_scenariu: z.string().nullable(),
    /** pf / pfa / imm / pj din `cod_scenariu`; null = sursa nu-l spune; lipsește în răspunsurile Vox
     * salvate înainte de 07.10.2026 */
    segment: z.string().nullable().optional(),
    citat: z.string().nullable(),
    confidence: z.number().nullable(),
    ambiguu: z.boolean(),
    motiv_ambiguu: z.string().nullable(),
    metoda_extractie: z.string().nullable(),
    serviciu: z.string().nullable(),
    sectiune: z.string().nullable(),
    conditie: z.string().nullable(),
    frecventa: z.string().nullable(),
    detaliu: z.string().nullable(),
    pagina: z.number().nullable(),
    nr_aparitii: z.number().nullable(),
    sursa: z.string().nullable(),
    tip_sursa: z.string().nullable(),
    link: z.string().nullable(),
    link_pagina: z.string().nullable(),
    pagina_documente_motiv: z.string().nullable(),
    fisier: z.string().nullable(),
    ancora: z.string().nullable(),
    /** data intrării în vigoare (ISO), când sursa o are; o arată doar fișa din Vox */
    data_vigoare: z.string().nullable().optional(),
    /** tipul rândului când nu e prețul serviciului („limita”, „nota” …): îl pune Vox, nu /api/celula */
    tip_alt: z.string().nullable().optional(),
    /** sursa „referinta” (2.1 / 2.2): datele valorii, din citat, a documentului și a extragerii */
    data_citat: z.string().nullable().optional(),
    data_document: z.string().nullable().optional(),
    data_document_sursa: z.string().nullable().optional(),
    data_extragere: z.string().nullable().optional(),
  })
  .passthrough()
export type ValoareDovada = z.infer<typeof ValoareDovada>
export const Celula = z.array(ValoareDovada)
