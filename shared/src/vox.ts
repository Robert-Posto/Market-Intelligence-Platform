/**
 * Vox (/api/vox): starea funcției și răspunsul la o întrebare, scrise după
 * app/vox.py din 06.10.2026. Interpretarea vine de la model, dar trece prin validarea
 * serverului; valorile (`randuri`) au forma rândurilor din /api/celula.
 */
import { z } from 'zod'
import { ValoareDovada } from './celula'

export const VoxStare = z
  .object({ activ: z.boolean(), model: z.string(), token: z.string().optional() })
  .passthrough()
export type VoxStare = z.infer<typeof VoxStare>

export const Interpretare = z.object({
  tip: z.enum(['cautare', 'neclar', 'in_afara']),
  banci: z.array(z.string()),
  concept: z.string().nullable(),
  categorie: z.string().nullable(),
  termen: z.string().nullable(),
  produs_credit: z.string().nullable(),
  text_cautat: z.string().nullable(),
  clarificare: z.string().nullable(),
})
export type Interpretare = z.infer<typeof Interpretare>

/** Pe segment (pf / pfa / imm / pj), unitate și categorie (primul segment din cod_scenariu), fără valorile ambigue. */
export const GrupaRezumat = z.object({
  /** null = fără segment în sursă; lipsește în conversațiile salvate înainte de 07.10.2026 */
  segment: z.string().nullable().optional(),
  unitate: z.string(),
  categorie: z.string(),
  n: z.number(),
  minim: z.number(),
  maxim: z.number(),
  gratuite: z.number(),
})
export type GrupaRezumat = z.infer<typeof GrupaRezumat>

export const RaspunsBanca = z
  .object({
    banca: z.string(),
    mod: z.enum(['concept', 'text']),
    total: z.number(),
    limitat: z.boolean(),
    ambigue: z.number(),
    /** neambigue, fără cifră (doar `valoare_text`): nu intră în rezumat, dar sunt în `total` */
    fara_cifra: z.number(),
    rezumat: z.array(GrupaRezumat),
    randuri: z.array(ValoareDovada),
    stare_banca: z.enum(['blocata', 'fara_surse']).nullable(),
    /** câte surse ale băncii sunt blocate și de ce, doar la 0 valori; lipsește în conversațiile vechi */
    blocaje: z.object({ surse: z.number(), robots: z.number(), refuzate: z.number(), pdf: z.number() }).nullable().optional(),
    /** filtrele căzute pe „nespecificat în sursă” ca răspunsul să nu iasă gol; lipsește în conversațiile vechi */
    filtre_relaxate: z.array(z.enum(['termen', 'produs'])).optional(),
    /** zero valori din cauza termenului / tipului de credit: câte sunt fără ele */
    fara_filtre: z.number().nullable(),
  })
  .passthrough()
export type RaspunsBanca = z.infer<typeof RaspunsBanca>

export const RaspunsIntrebare = z
  .object({
    interpretare: Interpretare,
    ignorate: z.array(z.string()),
    raspunsuri: z.array(RaspunsBanca),
    model: z.string(),
    tokeni: z.object({ intrare: z.number(), iesire: z.number(), citire_cache: z.number(), scriere_cache: z.number() }),
    cost_usd: z.number().nullable(),
  })
  .passthrough()
export type RaspunsIntrebare = z.infer<typeof RaspunsIntrebare>

/** Răspunsul la POST /api/vox: ca cel salvat, plus conversația (null dacă n-a putut fi salvată). */
export const RaspunsVox = RaspunsIntrebare.extend({ conversatie: z.string().nullable() })
export type RaspunsVox = z.infer<typeof RaspunsVox>

/** O întrebare dintr-o conversație salvată (loguri/vox/conversatii/<id>.jsonl). */
export const Tura = z.object({ data: z.string(), intrebare: z.string(), raspuns: RaspunsIntrebare })
export type Tura = z.infer<typeof Tura>

export const Conversatie = z
  .object({ id: z.string(), titlu: z.string(), redenumita: z.boolean(), ture: z.array(Tura) })
  .passthrough()
export type Conversatie = z.infer<typeof Conversatie>

/** Un rând din coloana „Conversații”; `texte` = toate întrebările, pentru căutare. */
export const ConversatieRezumat = z
  .object({
    id: z.string(),
    titlu: z.string(),
    redenumita: z.boolean(),
    intrebari: z.number(),
    texte: z.array(z.string()),
    inceputa: z.string(),
    ultima: z.string(),
    cost_usd: z.number(),
  })
  .passthrough()
export type ConversatieRezumat = z.infer<typeof ConversatieRezumat>

export const Redenumire = z.object({ titlu: z.string(), redenumita: z.boolean() })
export const Stergere = z.object({ sters: z.literal(true) })
