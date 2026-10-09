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
  tip: z.enum(['cautare', 'clasament', 'aplicatii', 'neclar', 'in_afara']),
  banci: z.array(z.string()),
  concept: z.string().nullable(),
  categorie: z.string().nullable(),
  termen: z.string().nullable(),
  produs_credit: z.string().nullable(),
  text_cautat: z.string().nullable(),
  clarificare: z.string().nullable(),
  /** lipsesc în conversațiile salvate înainte de clasamente (07.10.2026) */
  segment: z.string().nullable().optional(),
  metrica: z.enum(['mediana', 'cea_mai_buna']).nullable().optional(),
  /** lipsesc în conversațiile salvate înainte de aplicații (08.10.2026) */
  functie: z.string().nullable().optional(),
  aspect: z.enum(['functii', 'note', 'recenzii']).nullable().optional(),
  prag_note: z.number().nullable().optional(),
})
export type Interpretare = z.infer<typeof Interpretare>

/** O frecvență dintr-o grupă de comision (lunar, anual …; null = sursa n-o spune). */
export const FrecventaGrupa = z.object({ frecventa: z.string().nullable(), n: z.number(), minim: z.number(), maxim: z.number() })
export type FrecventaGrupa = z.infer<typeof FrecventaGrupa>

/** Butoanele de sub un răspuns, care continuă fără model (app/vox.py, `BUTOANE`). */
export const Buton = z.enum(['firme', 'pf', 'libra', 'toate', 'prag_100', 'prag_1000', 'fara_prag'])
export type Buton = z.infer<typeof Buton>

/** Pe segment (pf / pfa / imm / pj), unitate și categorie (primul segment din cod_scenariu), fără valorile ambigue. */
export const GrupaRezumat = z.object({
  /** null = fără segment în sursă; lipsește în conversațiile salvate înainte de 07.10.2026 */
  segment: z.string().nullable().optional(),
  unitate: z.string(),
  categorie: z.string(),
  /** doar la dobânzi: lei / eur / usd / gbp / chf, null = monedă nespusă; lipsește la comisioane și în conversațiile vechi */
  moneda: z.string().nullable().optional(),
  n: z.number(),
  minim: z.number(),
  maxim: z.number(),
  gratuite: z.number(),
  /** doar la comisioanele cu mai multe frecvențe (de pildă lunar și anual); lipsește altfel */
  frecvente: z.array(FrecventaGrupa).optional(),
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
    /** notele, limitele, cursurile găsite la serviciu, separat de preț; lipsește în conversațiile vechi */
    alte: z.array(GrupaRezumat).optional(),
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

/** Un rând de clasament (app/vox.py, `clasa`). */
export const RandClasament = z
  .object({
    loc: z.number(), loc_pana: z.number(), banca: z.string(), valoare: z.number(),
    minim: z.number(), maxim: z.number(), n: z.number(),
    serviciu: z.string().nullable(), frecventa: z.string().nullable(), conditie: z.string().nullable(),
    segment_necunoscut: z.boolean().nullable().optional(), evidentiata: z.boolean(),
    alte_monede: z.object({ n: z.number(), din: z.number() }).optional(),
  })
  .passthrough()
export type RandClasament = z.infer<typeof RandClasament>

export const BlocClasament = z
  .object({ tip: z.enum(['exact', 'nespecificat']), termen: z.string(), produs: z.string(), randuri: z.array(RandClasament) })
  .passthrough()
export type BlocClasament = z.infer<typeof BlocClasament>

/** Clasamentul unei întrebări; `neclasabil` = conceptul nu are o cifră comparabilă între bănci. */
export const Clasament = z
  .object({
    concept: z.string().nullable(),
    text: z.string().nullable().optional(),
    neclasabil: z.boolean().optional(),
    sursa: z.enum(['matrice', 'rate']).optional(),
    grup: z.string().optional(),
    unitate: z.string().optional(),
    sens: z.enum(['mic_bun', 'mare_bun']).optional(),
    metrica: z.enum(['mediana', 'cea_mai_buna']).optional(),
    segment: z.string().nullable().optional(),
    categorie: z.string().nullable().optional(),
    termen: z.string().nullable().optional(),
    produs: z.string().nullable().optional(),
    blocuri: z.array(BlocClasament).optional(),
    /** `bloc`: în ce bloc stă Libra (pe depozitul de 12 luni, doar în cel „nespecificat”) */
    libra: z.object({ loc: z.number(), loc_pana: z.number(), din: z.number(), bloc: z.enum(['exact', 'nespecificat']).optional() }).nullable().optional(),
    fara_date: z
      .array(z.object({
        banca: z.string(), stare: z.string().nullable().optional(), surse: z.number().optional(),
        robots: z.number().optional(), refuzate: z.number().optional(), pdf: z.number().optional(),
      }).passthrough())
      .optional(),
  })
  .passthrough()
export type Clasament = z.infer<typeof Clasament>

/** Aplicațiile băncilor (app/vox.py, `Vox._aplicatii_raspuns`): analiza APK, App Store, Google Play. */
const Verdict = z.enum(['sigur', 'probabil', 'absent', 'neconcludent'])

export const FunctieAplicatie = z.object({ verdict: Verdict, surse: z.array(z.string()), dovada_text: z.string().nullable() })
export type FunctieAplicatie = z.infer<typeof FunctieAplicatie>

/** Nota dintr-un magazin; `loc`…`sub_prag` doar în cardurile vederii `note`. */
export const NotaMagazin = z
  .object({
    nota: z.number().nullable(), evaluari: z.number(), distributie_stele: z.array(z.number()).nullable(),
    versiune: z.string().nullable(), url: z.string().nullable(),
    loc: z.number().nullable().optional(), loc_pana: z.number().nullable().optional(),
    din: z.number().nullable().optional(), sub_prag: z.boolean().optional(),
  })
  .passthrough()
export type NotaMagazin = z.infer<typeof NotaMagazin>

export const ColoanaAplicatie = z
  .object({
    banca: z.string(), fara_aplicatie: z.boolean(), aplicatie: z.string().nullable(),
    versiune_analizata: z.string().nullable(), data_analizei: z.string().nullable(), framework: z.string().nullable(),
    secundare: z.array(z.string()), functii: z.record(FunctieAplicatie),
    play: NotaMagazin.nullable(), app_store: NotaMagazin.nullable(),
  })
  .passthrough()
export type ColoanaAplicatie = z.infer<typeof ColoanaAplicatie>

export const Diferenta = z.object({
  functie: z.string(), nivel: z.enum(['sigur', 'probabil']), au: z.array(z.string()), n_au: z.array(z.string()),
})
export type Diferenta = z.infer<typeof Diferenta>

/** Un rând din clasamentul notelor (app/vox.py, `clasa_note`); fără `loc` sub prag sau fără notă. */
export const RandNota = z
  .object({
    banca: z.string(), aplicatie: z.string().nullable(), nota: z.number().nullable(),
    nota_afisata: z.number().nullable(), evaluari: z.number(), url: z.string().nullable(), evidentiata: z.boolean(),
    loc: z.number().optional(), loc_pana: z.number().optional(),
  })
  .passthrough()
export type RandNota = z.infer<typeof RandNota>

export const ClasamentNote = z.object({ randuri: z.array(RandNota), sub_prag: z.array(RandNota), fara_nota: z.array(RandNota) })
export type ClasamentNote = z.infer<typeof ClasamentNote>

export const CardNote = z
  .object({
    banca: z.string(), aplicatie: z.string().nullable(), fara_aplicatie: z.boolean(),
    play: NotaMagazin.nullable(), app_store: NotaMagazin.nullable(),
  })
  .passthrough()
export type CardNote = z.infer<typeof CardNote>

/** O recenzie, așa cum a scris-o clientul (App Store din bază, Google Play din date/google_play_recenzii.json). */
export const RecenzieVox = z
  .object({
    nota: z.number().nullable(), text: z.string().nullable(), data: z.string().nullable(), versiune: z.string().nullable(),
    raspuns_banca: z.string().nullable(), raspuns_data: z.string().nullable().optional(),
  })
  .passthrough()
export type RecenzieVox = z.infer<typeof RecenzieVox>

/** Recenziile unei bănci într-un magazin: cele potrivite și câte are eșantionul. */
export const MagazinRecenzii = z.object({ recenzii: z.array(RecenzieVox), din: z.number() })
export type MagazinRecenzii = z.infer<typeof MagazinRecenzii>

/** `play` = null: fișierul Google Play lipsește. */
export const BlocRecenzii = z
  .object({
    banca: z.string(), aplicatie: z.string().nullable(), fara_aplicatie: z.boolean(), evidentiata: z.boolean(),
    play: MagazinRecenzii.nullable(), app_store: MagazinRecenzii.nullable(),
  })
  .passthrough()
export type BlocRecenzii = z.infer<typeof BlocRecenzii>

const SchemaAplicatii = z
  .object({
    vedere: z.enum(['functie', 'aplicatii', 'note', 'neanalizata', 'recenzii']),
    blocuri: z.array(BlocRecenzii).optional(),
    cuvinte: z.array(z.string()).optional(),
    fara_potriviri: z.number().optional(),
    functie: z.string().nullable(),
    text_cautat: z.string().nullable(),
    analiza_la: z.string().nullable(),
    app_store_la: z.string().nullable(),
    play_la: z.string().nullable(),
    banci_fara_aplicatie: z.array(z.string()),
    grupuri: z.array(z.object({
      verdict: Verdict,
      aplicatii: z.array(z.object({
        banca: z.string(), aplicatie: z.string().nullable(), verdict: Verdict, surse: z.array(z.string()),
        dovada_text: z.string().nullable(), evidentiata: z.boolean(),
      }).passthrough()),
    })).optional(),
    coloane: z.array(ColoanaAplicatie).optional(),
    diferente: z.array(Diferenta).optional(),
    prag: z.number().nullable().optional(),
    clasamente: z.object({ play: ClasamentNote.nullable(), app_store: ClasamentNote.nullable() }).optional(),
    putine_note: z.object({
      app_store: z.number().optional(), play: z.number().optional(), prag: z.number(),
      primul: z.object({
        magazin: z.enum(['play', 'app_store']), banca: z.string(), loc: z.number(), loc_pana: z.number(), evaluari: z.number(),
      }),
    }).nullable().optional(),
    carduri: z.array(CardNote).optional(),
    functii: z.array(z.string()).optional(),
  })
  .passthrough()
export type Aplicatii = z.infer<typeof SchemaAplicatii>
/** Cu tipul inferat, structura se repeta în RaspunsIntrebare, RaspunsVox, Tura și Conversatie, iar tsc refuza
 * Conversatie (TS7056: tipul depășește lungimea maximă, 08.10.2026); tipul numit oprește repetarea. */
export const Aplicatii: z.ZodType<Aplicatii, z.ZodTypeDef, unknown> = SchemaAplicatii

export const RaspunsIntrebare = z
  .object({
    interpretare: Interpretare,
    ignorate: z.array(z.string()),
    raspunsuri: z.array(RaspunsBanca),
    /** lipsește în conversațiile salvate înainte de clasamente (07.10.2026) */
    clasament: Clasament.nullable().optional(),
    /** lipsește în conversațiile salvate înainte de aplicații (08.10.2026) */
    aplicatii: Aplicatii.nullable().optional(),
    /** null = tură dată de un buton, fără model */
    model: z.string().nullable(),
    tokeni: z.object({ intrare: z.number(), iesire: z.number(), citire_cache: z.number(), scriere_cache: z.number() }),
    cost_usd: z.number().nullable(),
    /** butoanele de sub răspuns; lipsesc în conversațiile salvate înainte de 08.10.2026 */
    butoane: z.array(Buton).optional(),
    /** butonul care a dat tura (fără model) */
    buton: Buton.optional(),
  })
  .passthrough()
export type RaspunsIntrebare = z.infer<typeof RaspunsIntrebare>

/** Răspunsul la POST /api/vox: ca cel salvat, plus conversația (null dacă n-a putut fi salvată). */
export const RaspunsVox = RaspunsIntrebare.extend({ conversatie: z.string().nullable() })
export type RaspunsVox = z.infer<typeof RaspunsVox>

/** O întrebare dintr-o conversație salvată (loguri/vox/conversatii/<id>.jsonl). */
const SchemaTura = z.object({ data: z.string(), intrebare: z.string(), raspuns: RaspunsIntrebare })
export type Tura = z.infer<typeof SchemaTura>
/** Tip numit, ca la `Aplicatii`: cu vederea recenziilor, `Conversatie` depășea din nou lungimea maximă (TS7056, 09.10.2026). */
export const Tura: z.ZodType<Tura, z.ZodTypeDef, unknown> = SchemaTura

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
