/**
 * 2.3, ramura Android (/api/android): analiza statică a APK-urilor din pachetul
 * lui Nicolae din 05.10.2026 (migrarea 027, `ingest/load_android.py`). Scrise după
 * `android()` din app/server.py și după constrângerile din migrare: ce e NOT NULL
 * acolo e obligatoriu aici. Valorile închise (rol, captura, verdict, tip, sursa)
 * rămân `z.string()`, nu enum: o valoare nouă în bază apare cum vine, nu strică
 * toată pagina. `passthrough()`: un câmp nou de la server nu strică interfața.
 *
 * Cheia unei aplicații e `package`, nu banca: BRD (YOU BRD și MyBRD) și Nexent
 * (monet și Avantaj) au câte două.
 */
import { z } from 'zod'

const nr = z.number().nullable()
const txt = z.string().nullable()

/** Una din cele 24 de aplicații; trackerele, bibliotecile și data sunt ale versiunii celei mai noi. */
export const AplicatieAndroid = z
  .object({
    banca: z.string(),
    package: z.string(),
    aplicatie: z.string(),
    /** principal | secundar | reper (Libra) */
    rol: z.string(),
    versiune_analizata: txt,
    versiune_cea_mai_noua: txt,
    framework: txt,
    platforma_tehnica: txt,
    /** ok | negru_text | negru_nimic | blocat */
    captura: txt,
    min_sdk: nr,
    target_sdk: nr,
    nr_permisiuni: nr,
    nr_texte_in_apk: nr,
    nr_trackere: nr,
    nr_biblioteci: nr,
    nr_librarii_native: nr,
    data_extragere: txt,
    nr_versiuni: z.number(),
    provenienta: z.string(),
  })
  .passthrough()
export type AplicatieAndroid = z.infer<typeof AplicatieAndroid>

export const VersiuneAndroid = z
  .object({
    package: z.string(),
    version_name: z.string(),
    version_code: nr,
    min_sdk: nr,
    target_sdk: nr,
    framework: txt,
    nr_permisiuni: nr,
    nr_trackere: nr,
    nr_biblioteci: nr,
    nr_librarii_native: nr,
    data_extragere: txt,
  })
  .passthrough()
export type VersiuneAndroid = z.infer<typeof VersiuneAndroid>

/** O celulă din matricea aplicație × funcționalitate, calculată pe versiunea analizată. */
export const FunctionalitateAndroid = z
  .object({
    package: z.string(),
    functie: z.string(),
    titlu: txt,
    /** sigur | probabil | absent | neconcludent */
    verdict: z.string(),
    /** `cod|text|assets`, separate prin | */
    surse: txt,
    dovada_text: txt,
  })
  .passthrough()
export type FunctionalitateAndroid = z.infer<typeof FunctionalitateAndroid>

export const TrackerAndroid = z
  .object({
    package: z.string(),
    version_name: z.string(),
    tracker: z.string(),
    categorii: txt,
    dovada: txt,
  })
  .passthrough()
export type TrackerAndroid = z.infer<typeof TrackerAndroid>

export const PermisiuneAndroid = z
  .object({ package: z.string(), version_name: z.string(), permisiune: z.string() })
  .passthrough()
export type PermisiuneAndroid = z.infer<typeof PermisiuneAndroid>

/** Semnale din APK, NU acceptarea Google/Apple Pay (Capcane, punctul 1, în pachet). */
export const PortofelAndroid = z
  .object({
    package: z.string(),
    ropay_text: nr,
    googlepay_text: nr,
    applepay_text_ios: nr,
    wearable_text: nr,
    hce_servicii: nr,
    nfc_permisiune: nr,
    gpay_push_provisioning: nr,
    gpay_wallet_api: nr,
    cauta_google_wallet: nr,
  })
  .passthrough()
export type PortofelAndroid = z.infer<typeof PortofelAndroid>

/** tip: hardware | cauta_aplicatia | domeniu_pinned | domeniu_revendicat | schema_deep_link | mediu_retea | meta_data_terti */
export const ProfilTehnicAndroid = z
  .object({ package: z.string(), tip: z.string(), valoare: z.string() })
  .passthrough()
export type ProfilTehnicAndroid = z.infer<typeof ProfilTehnicAndroid>

/** O diferență între două versiuni consecutive; `adaugat` / `eliminat` sunt liste separate prin |. */
export const SchimbareAndroid = z
  .object({
    package: z.string(),
    de_la: z.string(),
    la: z.string(),
    camp: z.string(),
    adaugat: txt,
    eliminat: txt,
  })
  .passthrough()
export type SchimbareAndroid = z.infer<typeof SchimbareAndroid>

/** Un text citit de pe ecran prin accesibilitate; sursa: pornire | parcurgere. */
export const TextEcranAndroid = z
  .object({
    package: z.string(),
    sursa: z.string(),
    data: txt,
    pas: nr,
    text: z.string(),
  })
  .passthrough()
export type TextEcranAndroid = z.infer<typeof TextEcranAndroid>

export const NotaAndroid = z.object({ package: z.string(), nota: z.string() }).passthrough()
export type NotaAndroid = z.infer<typeof NotaAndroid>

export const Android = z
  .object({
    aplicatii: z.array(AplicatieAndroid),
    versiuni: z.array(VersiuneAndroid),
    functionalitati: z.array(FunctionalitateAndroid),
    trackere: z.array(TrackerAndroid),
    permisiuni: z.array(PermisiuneAndroid),
    portofele: z.array(PortofelAndroid),
    profil_tehnic: z.array(ProfilTehnicAndroid),
    schimbari: z.array(SchimbareAndroid),
    texte_ecran: z.array(TextEcranAndroid),
    note: z.array(NotaAndroid),
    /** max(incarcat_la): null când tabelele sunt goale */
    incarcat_la: txt,
  })
  .passthrough()
export type Android = z.infer<typeof Android>

/** /api/android?package=…: bibliotecile unei aplicații, pe toate versiunile ei (3.644 de rânduri în total). */
export const BiblioteciAndroid = z.array(
  z.object({ version_name: z.string(), biblioteca: z.string(), versiune: txt }).passthrough(),
)
export type BiblioteciAndroid = z.infer<typeof BiblioteciAndroid>
