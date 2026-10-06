import type {
  Android,
  AplicatieAndroid,
  FunctionalitateAndroid,
  PortofelAndroid,
  ProfilTehnicAndroid,
  SchimbareAndroid,
  TextEcranAndroid,
  TrackerAndroid,
  VersiuneAndroid,
} from '@mcc/shared'
import type { Meta } from '../../../api/meta'
import { areCheie, type DictKey, type Params } from '../../../i18n'
import { faraDiacritice } from '../../../util/format'

export type Tr = (k: DictKey, p?: Params) => string

export type Sectiune = 'magazin' | 'aplicatii' | 'functionalitati' | 'trackere' | 'portofele' | 'schimbari'

/** Ce primește fiecare secțiune de la pagina Android: aplicațiile rămase după filtre și deschiderea detaliului. */
export interface PropsSectiune {
  ix: Index
  apps: AplicatieAndroid[]
  m: Meta
  deschide: (pachet: string) => void
}

/**
 * Ordinea din definiția funcționalităților (`functionalitati.yaml` din pachet): de
 * la contul deschis la distanță la plăți și siguranță. Serverul le trimite
 * alfabetic, iar „anti_fraud” ajungea prima. O cheie nouă din bază apare la coadă.
 */
const FUNCTII: string[] = [
  'identity_verification', 'nfc_id_chip', 'video_call', 'in_app_chat', 'wallet_provisioning', 'hce_contactless',
  'ropay', 'scan_pay', 'voice', 'strong_auth', 'marketing', 'anti_fraud', 'huawei',
]

export interface Index {
  /** toate aplicațiile, în ordinea serverului (Libra prima); filtrele din bară nu le ating */
  toate: AplicatieAndroid[]
  incarcat_la: string | null
  app: Record<string, AplicatieAndroid>
  versiuni: Record<string, VersiuneAndroid[]>
  /** versiunea pe care stau permisiunile și trackerele afișate: cea mai nouă */
  ultima: Record<string, string | null>
  /** permisiunile versiunii celei mai noi */
  perm: Record<string, string[]>
  /** trackerele versiunii celei mai noi */
  trackere: Record<string, TrackerAndroid[]>
  functii: Record<string, Record<string, FunctionalitateAndroid>>
  /** coloanele matricei, cu titlul românesc din bază */
  coloaneFunctii: { functie: string; titlu: string }[]
  portofel: Record<string, PortofelAndroid>
  profil: Record<string, ProfilTehnicAndroid[]>
  schimbari: Record<string, SchimbareAndroid[]>
  texte: Record<string, TextEcranAndroid[]>
  note: Record<string, string[]>
}

function grupeaza<T>(randuri: T[], cheie: (r: T) => string): Record<string, T[]> {
  const o: Record<string, T[]> = {}
  for (const r of randuri) (o[cheie(r)] ??= []).push(r)
  return o
}

export function indexeaza(d: Android): Index {
  const versiuni = grupeaza(d.versiuni, (v) => v.package)
  // serverul ordonează versiunile după version_code: fără versiune_cea_mai_noua, ultima din listă
  const ultima: Record<string, string | null> = {}
  for (const a of d.aplicatii) ultima[a.package] = a.versiune_cea_mai_noua ?? versiuni[a.package]?.at(-1)?.version_name ?? null
  const peUltima = (pachet: string, versiune: string) => {
    const u = ultima[pachet]
    return !u || u === versiune
  }

  const perm: Record<string, string[]> = {}
  for (const [pachet, rs] of Object.entries(grupeaza(d.permisiuni.filter((p) => peUltima(p.package, p.version_name)), (p) => p.package))) {
    perm[pachet] = [...new Set(rs.map((p) => p.permisiune))].sort()
  }

  const functii: Record<string, Record<string, FunctionalitateAndroid>> = {}
  const titluri = new Map<string, string>()
  for (const f of d.functionalitati) {
    (functii[f.package] ??= {})[f.functie] = f
    if (!titluri.has(f.functie)) titluri.set(f.functie, f.titlu || f.functie)
  }
  const chei = [...FUNCTII.filter((k) => titluri.has(k)), ...[...titluri.keys()].filter((k) => !FUNCTII.includes(k))]

  const note: Record<string, string[]> = {}
  for (const n of d.note) (note[n.package] ??= []).push(n.nota)

  return {
    toate: d.aplicatii,
    incarcat_la: d.incarcat_la,
    app: Object.fromEntries(d.aplicatii.map((a) => [a.package, a])),
    versiuni,
    ultima,
    perm,
    trackere: grupeaza(d.trackere.filter((x) => peUltima(x.package, x.version_name)), (x) => x.package),
    functii,
    coloaneFunctii: chei.map((functie) => ({ functie, titlu: titluri.get(functie) ?? functie })),
    portofel: Object.fromEntries(d.portofele.map((p) => [p.package, p])),
    profil: grupeaza(d.profil_tehnic, (p) => p.package),
    schimbari: grupeaza(d.schimbari, (s) => s.package),
    texte: grupeaza(d.texte_ecran, (x) => x.package),
    note,
  }
}

/** „4.22.0 → 4.23.0”, din prima și ultima versiune extrasă (serverul le ordonează după version_code). */
export function intervalVersiuni(ix: Index, a: AplicatieAndroid): string {
  const v = ix.versiuni[a.package] ?? []
  return v.length > 1 ? `${v[0]!.version_name} → ${v[v.length - 1]!.version_name}` : (v[0]?.version_name ?? '')
}

/** Căutarea din bară: banca, aplicația sau pachetul, fără diacritice. */
export function sePotriveste(a: AplicatieAndroid, m: Meta, q: string): boolean {
  if (!q) return true
  return faraDiacritice([m.nume[a.banca] ?? a.banca, a.banca, a.aplicatie, a.package].join(' ')).includes(q)
}

/**
 * Eticheta unei valori închise din bază (rol, captură, verdict, tip…): din dicționar
 * dacă are cheie (`mobil.android_<prefix>.<valoare>`), altfel cum vine. Numele proprii
 * (Capacitor/Angular, Getik, Asseco) n-au cheie și rămân la fel în ambele limbi.
 */
export function eticheta(t: Tr, prefix: string, v: string | null | undefined): string {
  if (!v) return '—'
  const k = `mobil.android_${prefix}.${v.trim().replace(/[^a-zA-Z0-9]+/g, '_')}`
  return areCheie(k) ? t(k) : v
}

/** Cheia unei etichete, dacă există; altfel null (descrierile fără pereche nu se afișează). */
export function cheie(prefix: string, v: string | null | undefined): DictKey | null {
  if (!v) return null
  const k = `mobil.android_${prefix}.${v.trim().replace(/[^a-zA-Z0-9]+/g, '_')}`
  return areCheie(k) ? k : null
}

/** Listele din bază sunt separate prin | (`surse`, `adaugat`, `eliminat`). */
export const bucati = (s: string | null | undefined): string[] =>
  (s ?? '').split('|').map((x) => x.trim()).filter(Boolean)

/**
 * Textele citite de pe ecran păstrează entitățile din XML-ul de accesibilitate
 * (21 de `&#10;` în texte_ecran.csv, plus `&amp;` și `&gt;`): fără decodare,
 * apăreau ca atare în pagină. Rezultatul se afișează ca text, nu ca HTML.
 */
const ENTITATI: Record<string, string> = {
  amp: '&', lt: '<', gt: '>', quot: String.fromCharCode(34), apos: String.fromCharCode(39), nbsp: String.fromCharCode(160),
}
export function decodeaza(s: string): string {
  return s.replace(/&(#x[0-9a-f]+|#[0-9]+|[a-z]+);/gi, (orig, e: string) => {
    if (!e.startsWith('#')) return ENTITATI[e.toLowerCase()] ?? orig
    const cod = e[1] === 'x' || e[1] === 'X' ? parseInt(e.slice(2), 16) : Number(e.slice(1))
    return Number.isInteger(cod) && cod > 0 && cod <= 0x10ffff ? String.fromCodePoint(cod) : orig
  })
}

/** Rangul pentru sortarea unei coloane din matrice; „neconcludent” e gol, deci rămâne jos în ambele sensuri. */
export function rangVerdict(v: string | undefined): number | null {
  return v === 'sigur' ? 2 : v === 'probabil' ? 1 : v === 'absent' ? 0 : null
}

export const VERDICTE = ['sigur', 'probabil', 'absent', 'neconcludent']

/** Categoriile Exodus ale unui tracker, traduse; unul fără categorie (AltBeacon) rămâne fără. */
export const categorii = (x: TrackerAndroid, t: Tr) => bucati(x.categorii).map((c) => eticheta(t, 'cat', c)).join(', ')

/* ---- permisiunile sensibile ---- */

const A = 'android.permission.'
const cu = (...nume: string[]) => nume.map((n) => A + n)

export interface GrupPermisiuni {
  k: string
  perm: string[]
  /** datele de sănătate au câte o permisiune pe tip (pași, distanță, exerciții…) */
  prefix?: string
}

/**
 * Grupurile afișate în matricea de permisiuni. Pe 05.10.2026, cele 27 de versiuni
 * cereau 143 de permisiuni distincte, multe banale (internet, vibrație, iconițe de
 * notificare pe lansatoarele producătorilor); aici stau doar cele care ating date
 * sau senzori ai omului. SMS nu cere nicio aplicație, iar coloana rămâne tocmai
 * ca să se vadă asta. Lista completă e în detaliul aplicației.
 */
export const GRUPURI_PERMISIUNI: GrupPermisiuni[] = [
  { k: 'camera', perm: cu('CAMERA') },
  { k: 'microfon', perm: cu('RECORD_AUDIO') },
  { k: 'locatie', perm: cu('ACCESS_FINE_LOCATION', 'ACCESS_COARSE_LOCATION', 'ACCESS_BACKGROUND_LOCATION') },
  { k: 'contacte', perm: cu('READ_CONTACTS', 'WRITE_CONTACTS') },
  { k: 'sms', perm: cu('READ_SMS', 'RECEIVE_SMS', 'SEND_SMS', 'RECEIVE_MMS', 'RECEIVE_WAP_PUSH') },
  { k: 'telefon', perm: cu('READ_PHONE_STATE', 'READ_PHONE_NUMBERS', 'READ_PRIVILEGED_PHONE_STATE', 'CALL_PHONE', 'ANSWER_PHONE_CALLS', 'READ_CALL_LOG', 'WRITE_CALL_LOG') },
  { k: 'biometrie', perm: cu('USE_BIOMETRIC', 'USE_FINGERPRINT') },
  { k: 'stocare', perm: cu('READ_EXTERNAL_STORAGE', 'WRITE_EXTERNAL_STORAGE', 'MANAGE_EXTERNAL_STORAGE', 'READ_MEDIA_IMAGES', 'READ_MEDIA_VIDEO', 'READ_MEDIA_AUDIO', 'READ_MEDIA_VISUAL_USER_SELECTED', 'ACCESS_MEDIA_LOCATION') },
  { k: 'nfc', perm: cu('NFC') },
  { k: 'bluetooth', perm: cu('BLUETOOTH', 'BLUETOOTH_ADMIN', 'BLUETOOTH_CONNECT', 'BLUETOOTH_SCAN', 'BLUETOOTH_ADVERTISE') },
  { k: 'aplicatii', perm: cu('QUERY_ALL_PACKAGES') },
  { k: 'publicitate', perm: ['com.google.android.gms.permission.AD_ID', ...cu('ACCESS_ADSERVICES_AD_ID', 'ACCESS_ADSERVICES_ATTRIBUTION', 'ACCESS_ADSERVICES_CUSTOM_AUDIENCE', 'ACCESS_ADSERVICES_TOPICS')] },
  { k: 'suprapunere', perm: cu('SYSTEM_ALERT_WINDOW') },
  { k: 'activitate', perm: [...cu('ACTIVITY_RECOGNITION'), 'android.gms.permission.ACTIVITY_RECOGNITION', 'com.google.android.gms.permission.ACTIVITY_RECOGNITION'], prefix: A + 'health.' },
]

export const LOCATIE_FUNDAL = A + 'ACCESS_BACKGROUND_LOCATION'

export function grupPermisiune(p: string): GrupPermisiuni | undefined {
  return GRUPURI_PERMISIUNI.find((g) => g.perm.includes(p) || (!!g.prefix && p.startsWith(g.prefix)))
}

/** „android.permission.CAMERA” → „CAMERA”; ale Google, ale producătorilor și ale băncii rămân întregi. */
export const permScurt = (p: string) => (p.startsWith(A) ? p.slice(A.length) : p)

/* ---- portofelele ---- */

export type CampPortofel =
  | 'hce_servicii' | 'gpay_push_provisioning' | 'gpay_wallet_api' | 'cauta_google_wallet' | 'nfc_permisiune'
  | 'ropay_text' | 'googlepay_text' | 'wearable_text' | 'applepay_text_ios'

/**
 * Coloanele, de la semnalele sigure la cele slabe (Capcane, punctul 1, în pachet):
 * doar HCE și butonul „Adaugă în Google Wallet” spun ceva sigur; textele sunt un
 * minim, fiindcă la aplicațiile web textele stau pe server.
 */
export const SEMNALE_PORTOFEL: { k: CampPortofel; tip: 'sigur' | 'slab' | 'text' }[] = [
  { k: 'hce_servicii', tip: 'sigur' },
  { k: 'gpay_push_provisioning', tip: 'sigur' },
  { k: 'gpay_wallet_api', tip: 'slab' },
  { k: 'cauta_google_wallet', tip: 'slab' },
  { k: 'nfc_permisiune', tip: 'slab' },
  { k: 'ropay_text', tip: 'text' },
  { k: 'googlepay_text', tip: 'text' },
  { k: 'wearable_text', tip: 'text' },
  { k: 'applepay_text_ios', tip: 'text' },
]

/* ---- profilul tehnic ---- */

/** Ordinea în detaliu: ce cere de la telefon, apoi legăturile, apoi configurarea internă. */
export const TIPURI_PROFIL = ['hardware', 'cauta_aplicatia', 'schema_deep_link', 'domeniu_revendicat', 'domeniu_pinned', 'mediu_retea', 'meta_data_terti']
