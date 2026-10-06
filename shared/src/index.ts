/**
 * Contractul dintre API și interfață: forma răspunsurilor, ca scheme Zod.
 *
 * Scrise după răspunsurile reale ale serverului Python (app/server.py), pe
 * baza din 02.10.2026. Când serverul trece pe Fastify, aceleași scheme
 * validează ce trimite el, deci cele două nu se pot despărți pe tăcute.
 * `passthrough()`: un câmp nou de la server nu strică interfața.
 */
import { z } from 'zod'

const data = z.string().nullable()

export const Banca = z
  .object({
    slug: z.string(),
    nume: z.string(),
    tier: z.number().nullable(),
    surse: z.number(),
    observatii: z.number(),
    versiuni_app: z.number(),
  })
  .passthrough()
export type Banca = z.infer<typeof Banca>

export const Logos = z.record(z.string(), z.string())

export const AcoperireBanca = z
  .object({
    slug: z.string(),
    nume: z.string(),
    comisioane: z.number(),
    dobanzi: z.number(),
    rating: z.number().nullable(),
    locatii: z.number(),
    recenzii: z.number(),
    blocate: z.number(),
    schimbari: z.number(),
    in_coada: z.number(),
  })
  .passthrough()

export const Acoperire = z.object({
  pe_banca: z.array(AcoperireBanca),
  categorii: z
    .object({
      comisioane: z.number(),
      comisioane_la: data,
      dobanzi: z.number(),
      dobanzi_la: data,
      aplicatii: z.number(),
      aplicatii_la: data,
      locatii: z.number(),
      locatii_la: data,
      indici: z.number(),
      indici_la: data,
      recenzii: z.number(),
      schimbari: z.number(),
    })
    .passthrough(),
})
export type Acoperire = z.infer<typeof Acoperire>

export const StareTabel = z.object({
  domeniu: z.string(),
  randuri: z.number(),
  ultima: data,
  provenienta: z.string().nullable(),
})
export const Stare = z.array(StareTabel)

export const Sumar = z
  .object({ totaluri: z.array(z.object({ ce: z.string(), n: z.number() })) })
  .passthrough()

export const ComandaRulare = z
  .object({
    id: z.string(),
    nume: z.string(),
    ce: z.string(),
    internet: z.boolean(),
    banca: z.string().nullable(),
    // joburile fluxului de comparație (pagina „Rulare manuală”): cer un produs, costă, au grupul „joburi”
    produs: z.string().nullable().optional(),
    grup: z.string().nullable().optional(),
    platit: z.boolean().optional(),
    estimare_s: z.number().optional(),
    estimare_sursa: z.string().optional(),
    estimare_banca_s: z.number().optional(),
    estimare_banca_sursa: z.string().optional(),
    estimari_banca: z.record(z.string(), z.number()).optional(),
    ultima: z
      .object({
        sfarsit: data,
        durata_s: z.number().nullable(),
        banca: z.string().nullable().optional(),
        cod: z.number().nullable(),
        oprit: z.boolean().optional(),
        ultimele: z.array(z.string()).optional(),
      })
      .passthrough()
      .nullable(),
  })
  .passthrough()
export type ComandaRulare = z.infer<typeof ComandaRulare>

export const RulareCurenta = z
  .object({
    nume: z.string(),
    banca: z.string().nullable().optional(),
    produs: z.string().nullable().optional(),
    inceput: data,
    scurs_s: z.number(),
    estimare_s: z.number().nullable().optional(),
    oprit: z.boolean().optional(),
    dupa_repornire: z.boolean().optional(),
    log: z.string(),
    jurnal: z.array(z.string()).optional(),
  })
  .passthrough()
export type RulareCurenta = z.infer<typeof RulareCurenta>

export const Rulari = z
  .object({
    activ: z.boolean(),
    comenzi: z.array(ComandaRulare),
    banci: z.array(z.string()),
    banci_joburi: z.array(z.string()).optional(),
    curenta: RulareCurenta.nullable(),
    token: z.string().optional(),
  })
  .passthrough()
export type Rulari = z.infer<typeof Rulari>

/** Ce se poate alege în modalul „Începe job” (/api/rulare_manuala). */
export const RulareManualaCatalog = z
  .object({
    tipuri: z.array(z.object({
      id: z.string(),
      denumire: z.string(),
      descriere: z.string(),
      ce: z.string(),
      produs: z.string().nullable(),
    }).passthrough()),
    banci: z.array(z.string()),
    produse: z.array(z.object({
      cod: z.string(),
      denumire: z.string(),
      segment: z.string().nullable(),
      categorie_cod: z.string().nullable(),
      prioritar: z.boolean(),
    }).passthrough()),
  })
  .passthrough()
export type RulareManualaCatalog = z.infer<typeof RulareManualaCatalog>

/** Costul și durata unui job înainte de pornire, din joburile încheiate (/api/rulare_manuala/estimare). */
export const RulareManualaEstimare = z
  .object({
    tip: z.string(),
    estimare: z.object({
      nivel: z.enum(['banca_produs', 'produs', 'banca', 'tip']),
      n: z.number(),
      cost_med: z.number(),
      cost_min: z.number(),
      cost_max: z.number(),
      durata_med: z.number().nullable(),
      durata_max: z.number().nullable(),
    }).nullable(),
    surse: z.object({ gasite: z.number(), negasite: z.number(), ultima: z.string().nullable() }).nullable(),
  })
  .passthrough()
export type RulareManualaEstimare = z.infer<typeof RulareManualaEstimare>

export const CelulaMatrice = z
  .object({
    banca: z.string(),
    camp: z.string(),
    n: z.number(),
    minim: z.number(),
    maxim: z.number(),
    gratuite: z.number(),
  })
  .passthrough()

export const Matrice = z
  .object({
    grup: z.string(),
    campuri: z.array(z.string()),
    segmente: z.array(z.object({ seg: z.string(), n: z.number() })),
    celule: z.array(CelulaMatrice),
    excluse_ambigue: z.number(),
    excluse_implauzibile: z.number(),
    prag_plauzibil: z.number(),
  })
  .passthrough()
export type Matrice = z.infer<typeof Matrice>

/** O valoare din sertarul cu dovezi (/api/celula). */
export const ValoareDovada = z
  .object({
    valoare: z.number().nullable(),
    valoare_text: z.string().nullable(),
    unitate: z.string().nullable(),
    cod_scenariu: z.string().nullable(),
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
  })
  .passthrough()
export type ValoareDovada = z.infer<typeof ValoareDovada>
export const Celula = z.array(ValoareDovada)

export * from './rate_mobil'
export * from './campanii'
export * from './reclame'
export * from './youtube_retele'
export * from './retea'
export * from './context_istoric'
export * from './versus'
export * from './banca'
export * from './surse_coada'
export * from './comparatie_libra'
export * from './jobs'
export * from './android'
