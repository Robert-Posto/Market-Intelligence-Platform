/**
 * Jurnalul joburilor (/api/jobs): ce a rulat, cât a durat, câți tokeni și cât a
 * costat, ce erori a avut. Tabelele vin din db/migration_036_jobs.sql și le scrie
 * extragere_produse_bancare/jurnal_joburi.py; pe o bază fără ele serverul trimite
 * `{disponibil: false}`, nu 500.
 */
import { z } from 'zod'

const txt = z.string().nullable()

export const TipJob = z
  .object({ cod: z.string(), denumire: z.string(), descriere: txt, script: txt })
  .passthrough()
export type TipJob = z.infer<typeof TipJob>

/** `abandonat` = încă `in_curs`, dar fără semn de viață de peste o oră (procesul a murit). */
export const StareJob = z.enum(['in_curs', 'reusit', 'cu_erori', 'esuat', 'intrerupt', 'abandonat'])
export type StareJob = z.infer<typeof StareJob>

export const Job = z
  .object({
    id: z.number(),
    type: z.string(),
    tip: z.string(),
    banca: txt,
    nume_banca: txt,
    started_at: z.string(),
    ended_at: txt,
    durata_s: z.number(),
    stare: StareJob,
    errors: z.number(),
    model: txt,
    apeluri: z.number(),
    tokeni_intrare: z.number(),
    tokeni_iesire: z.number(),
    tokeni_cache_citire: z.number(),
    tokeni_cache_scriere: z.number(),
    cost_usd: z.number(),
    cost_complet: z.boolean(),
    parametri: z.record(z.string(), z.unknown()).nullable(),
    rezumat: txt,
    // pornit din pagina „Rulare manuală” (migrarea 037); lipsă pe o bază fără migrare = automat
    runed_manually: z.boolean().optional().default(false),
  })
  .passthrough()
export type Job = z.infer<typeof Job>

export const EroareJob = z
  .object({
    id: z.number(),
    id_job: z.number(),
    eroare: z.string(),
    context: txt,
    created_at: z.string(),
    type: z.string(),
    tip: z.string(),
    banca: txt,
    nume_banca: txt,
  })
  .passthrough()
export type EroareJob = z.infer<typeof EroareJob>

/** O zi din grafic: costul pe fiecare tip care a rulat în ziua aceea (tipurile lipsă = 0). */
export const CostZi = z
  .object({ zi: z.string(), total: z.number(), joburi: z.number(), costuri: z.record(z.string(), z.number()) })
  .passthrough()
export type CostZi = z.infer<typeof CostZi>

const JobsDisponibile = z.object({
  disponibil: z.literal(true),
  tipuri: z.array(TipJob),
  filtre: z.object({ zile: z.number(), tip: txt, job: z.number().nullable() }).passthrough(),
  totaluri: z
    .object({
      joburi: z.number(),
      in_curs: z.number(),
      cu_probleme: z.number(),
      errors: z.number(),
      cost_usd: z.number(),
      tokeni_intrare: z.number(),
      tokeni_iesire: z.number(),
      tokeni_cache_citire: z.number(),
      tokeni_cache_scriere: z.number(),
      apeluri: z.number(),
      durata_s: z.number().nullable(),
      cost_complet: z.boolean(),
    })
    .passthrough(),
  cost_pe_zi: z.array(CostZi),
  joburi: z.array(Job),
  erori: z.array(EroareJob),
  limita: z.number(),
})

export const Jobs = z.discriminatedUnion('disponibil', [z.object({ disponibil: z.literal(false) }), JobsDisponibile])
export type Jobs = z.infer<typeof Jobs>
export type JobsDisponibile = z.infer<typeof JobsDisponibile>
