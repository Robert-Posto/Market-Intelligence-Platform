/**
 * Fluxul de comparație cu Libra (extragere_produse_bancare/): /api/comparatie_libra
 * și /api/products_discovery. Tabelele fluxului vin din migrările lui (027–034),
 * deci pe o bază fără ele serverul trimite `{disponibil: false}`, nu 500.
 */
import { z } from 'zod'

const txt = z.string().nullable()
const nr = z.number().nullable()

/**
 * Scenariul unei valori, descompus determinist din codul pus de model
 * (scenariu_libra.py). Toate cheile sunt opționale: o valoare are doar
 * dimensiunile pe care documentul le spune. Măsurat pe 05.10.2026, pe cele
 * 1.346 de valori cu scenariu.
 */
export const ScenariuLibra = z
  .object({
    cod: z.string().optional(),
    suma: nr.optional(),
    suma_max: nr.optional(),
    moneda: z.string().optional(),
    valuta: z.string().optional(),
    perioada_luni: z.number().optional(),
    perioada_zile: z.number().optional(),
    fix_ani: z.number().optional(),
    venit_min: z.number().optional(),
    etichete: z.array(z.string()).optional(),
    varianta: z.string().optional(),
    // grila de depozit (extrage_comparatie_libra.grila): dimensiunile ofertei, din valori fixe
    canal: z.string().optional(),
    plata_dobanzii: z.string().optional(),
    oferta: z.string().optional(),
    reguli: z.array(z.string()).optional(),
    derivat: z.boolean().optional(),
    din_trepte: z.boolean().optional(),
    // treaptă de sold (contul de economii): suma/suma_max sunt capetele unei benzi, nu o sumă exactă;
    // fără capete și cu `banda`, dobânda e valabilă la orice sold
    banda: z.boolean().optional(),
    suma_max_exclusiv: z.boolean().optional(),
    axa: z.string().optional(),
    // ofertă care cere ceva în plus (program de beneficii, plăți programate, promoție)
    conditionat: z.array(z.string()).optional(),
    referinta: z
      .object({
        id: z.string().optional(),
        nume: z.string(),
        potrivire: z.enum(['exact', 'aproximativ', 'alt', 'nespecificat']),
        motiv: z.string().optional(),
      })
      .passthrough()
      .optional(),
  })
  .passthrough()
export type ScenariuLibra = z.infer<typeof ScenariuLibra>

export const ProdusLibra = z
  .object({ cod: z.string(), denumire: z.string(), segment: txt, categorie_cod: txt, prioritar: z.boolean() })
  .passthrough()
export type ProdusLibra = z.infer<typeof ProdusLibra>

export const ValoareLibra = z
  .object({
    banca: z.string(),
    camp: z.string(),
    valoare: nr,
    valoare_text: txt,
    unitate: txt,
    moneda: txt,
    conditie: txt,
    citat: txt,
    link: txt,
    url: txt,
    tip: txt,
    incredere: nr,
    ambiguu: z.boolean(),
    motiv_ambiguu: txt,
    denumire_banca: txt,
    scenariu: ScenariuLibra.nullable(),
    stare: z.string(),
    data_colectare: txt,
  })
  .passthrough()
export type ValoareLibra = z.infer<typeof ValoareLibra>

const ComparatieDisponibila = z.object({
  disponibil: z.literal(true),
  produse: z.array(ProdusLibra),
  acoperire: z.array(z.object({ cod: z.string(), banca: z.string(), n: z.number(), campuri: z.number() }).passthrough()),
  comparabile: z.array(z.object({ cod: z.string(), n: z.number() }).passthrough()),
  negasite: z.array(z.object({ cod: z.string(), banca: z.string(), motiv: z.string(), nota: txt }).passthrough()),
  banci: z.array(z.object({ slug: z.string(), nume: z.string(), acces_restricted: z.boolean(), n: z.number() }).passthrough()),
  // doar cu ?produs=COD
  valori: z.array(ValoareLibra).optional(),
  echivalente: z
    .array(z.object({ banca: z.string(), denumire_la_banca: txt, url: txt, incredere: nr }).passthrough())
    .optional(),
})

export const ComparatieLibra = z.discriminatedUnion('disponibil', [
  z.object({ disponibil: z.literal(false) }),
  ComparatieDisponibila,
])
export type ComparatieLibra = z.infer<typeof ComparatieLibra>
export type ComparatieLibraDisponibila = z.infer<typeof ComparatieDisponibila>

export const ProdusConcurenta = z
  .object({
    id: z.number(),
    banca: z.string(),
    nume_banca: z.string(),
    denumire_produs: z.string(),
    descriere_produs: txt,
    link: z.string(),
    segment: txt,
    categorie: txt,
    created_at: z.string(),
    vazut_la: z.string(),
    nou: z.boolean(),
    retras: z.boolean(),
  })
  .passthrough()
export type ProdusConcurenta = z.infer<typeof ProdusConcurenta>

export const ProduseConcurenta = z.discriminatedUnion('disponibil', [
  z.object({ disponibil: z.literal(false) }),
  z.object({ disponibil: z.literal(true), produse: z.array(ProdusConcurenta) }),
])
export type ProduseConcurenta = z.infer<typeof ProduseConcurenta>
