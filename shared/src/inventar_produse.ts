/**
 * Inventarul produselor Libra (/api/inventar_produse): conținutul fișierului
 * extragere_produse_bancare/produse_libra.json, fiecare produs cu starea lui în
 * tabela `produse_libra`. Pagina modifică fișierul; baza se actualizează abia la
 * `incarca_baza.py`, de aici `baza` și `doar_in_baza`.
 */
import { z } from 'zod'

export const SEGMENTE_LIBRA = ['PF', 'PJ', 'PF+PJ'] as const
export const SegmentLibra = z.enum(SEGMENTE_LIBRA)
export type SegmentLibra = z.infer<typeof SegmentLibra>

/** Codul produsului și al categoriei: CREDIT_SIMPLU_IMM, ca toate cele 57 din catalog. */
export const COD_PRODUS = /^[A-Z0-9]+(_[A-Z0-9]+)*$/

/** `null` = baza nu răspunde; `inactiv` = produsul e în bază, dar dezactivat. */
export const StareInBaza = z.enum(['identic', 'diferit', 'lipsa', 'inactiv'])
export type StareInBaza = z.infer<typeof StareInBaza>

export const ProdusInventar = z
  .object({
    cod: z.string(),
    denumire: z.string(),
    descriere: z.string().nullable().optional(),
    segment: SegmentLibra.nullable(),
    categorie_cod: z.string().nullable(),
    prioritar: z.boolean(),
    /** tipul din produse_bancare_v2.json: dă câmpurile căutate la extragere; fără el, produsul e sărit */
    tip_v2: z.string().nullable().optional(),
    baza: StareInBaza.nullable(),
    diferente: z.array(z.string()),
  })
  .passthrough()
export type ProdusInventar = z.infer<typeof ProdusInventar>

export const TipV2 = z.object({ id: z.string(), nume: z.string(), segment: z.string().nullable().optional() }).passthrough()
export type TipV2 = z.infer<typeof TipV2>

export const InventarProduse = z
  .object({
    fisier: z.string(),
    /** amprenta fișierului: o salvare cu altă versiune e refuzată (409), ca să nu se piardă o modificare făcută între timp */
    versiune: z.string(),
    modificat: z.string(),
    generat: z.string().nullable(),
    produse: z.array(ProdusInventar),
    tipuri_v2: z.array(TipV2),
    baza_disponibila: z.boolean(),
    doar_in_baza: z.array(z.string()),
  })
  .passthrough()
export type InventarProduse = z.infer<typeof InventarProduse>

export const TokenInventar = z.object({ token: z.string() })

/** Ce trimite formularul; `cod` nu se schimbă după adăugare. */
export interface ProdusDeSalvat {
  cod: string
  denumire: string
  descriere: string | null
  segment: SegmentLibra
  categorie_cod: string | null
  prioritar: boolean
  tip_v2: string
}
