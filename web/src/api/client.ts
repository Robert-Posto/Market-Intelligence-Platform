import type { z } from 'zod'

/**
 * Toate cererile trec pe aici. Răspunsul se validează cu schema din
 * @mcc/shared: dacă serverul schimbă forma unui câmp, eroarea apare aici, cu
 * numele câmpului, nu ca o pagină goală.
 *
 * Serverul Python trimite erorile ca `{eroare: "..."}` cu 200, deci câmpul se
 * verifică explicit, ca în aplicația veche.
 */
/** Mesajul-semnal pentru „serverul de date nu răspunde”; îl traduce componenta Eroare. */
export const SERVER_OPRIT = 'SERVER_OPRIT'

/**
 * Eveniment pe `window` la orice 401 de la o rută de date: sesiunea a expirat. Îl ascultă
 * providerul de sesiune (src/auth), care arată pagina de logare; clientul nu știe de React.
 */
export const EVENIMENT_SESIUNE_EXPIRATA = 'mcc:sesiune-expirata'
const sesiuneExpirata = () => window.dispatchEvent(new Event(EVENIMENT_SESIUNE_EXPIRATA))

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
  }
}

/** Răspunsul, validat cu schema; aceleași reguli de eroare pentru GET și POST. */
async function dinRaspuns<S extends z.ZodTypeAny>(res: Response, cale: string, schema: S): Promise<z.infer<S>> {
  if (res.status === 401) sesiuneExpirata()
  const corp = (await res.json().catch(() => null)) as unknown
  if (corp && typeof corp === 'object' && 'eroare' in corp && (corp as { eroare: unknown }).eroare) {
    throw new ApiError(res.status, String((corp as { eroare: unknown }).eroare))
  }
  // Fără corp JSON și cu eroare: serverul de date nu răspunde (în dezvoltare, proxy-ul Vite
  // întoarce 500 gol când app/server.py e oprit). Pagina arată atunci un mesaj clar, nu „HTTP 500”.
  if (!res.ok && corp === null) throw new ApiError(res.status, SERVER_OPRIT)
  if (!res.ok) throw new ApiError(res.status, `HTTP ${res.status}`)
  const rez = schema.safeParse(corp)
  if (!rez.success) {
    const p = rez.error.issues[0]
    throw new ApiError(res.status, `${cale}: ${p?.path.join('.') ?? ''} ${p?.message ?? ''}`)
  }
  return rez.data
}

export async function api<S extends z.ZodTypeAny>(cale: string, schema: S, params?: Record<string, unknown>): Promise<z.infer<S>> {
  const url = new URL(cale, window.location.origin)
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null) url.searchParams.set(k, String(v))
    }
  }
  return dinRaspuns(await fetch(url), cale, schema)
}

/**
 * POST pentru rulările manuale. Serverul cere Content-Type JSON, tokenul
 * primit la GET /api/rulari și aceeași origine; din dev (Vite, alt port)
 * refuză, intenționat — verificarea nu se slăbește pentru dezvoltare.
 */
export async function apiPost(cale: string, corp: unknown, token: string): Promise<{ eroare?: string }> {
  const r = await fetch(cale, {
    method: 'POST',
    body: JSON.stringify(corp),
    headers: { 'Content-Type': 'application/json', 'X-MIP-Token': token },
  })
  if (r.status === 401) sesiuneExpirata()
  let d: { eroare?: string } = {}
  try {
    d = (await r.json()) as { eroare?: string }
  } catch {
    /* corp gol */
  }
  if (!r.ok && !d.eroare) d.eroare = `HTTP ${r.status}`
  return d
}

/**
 * POST cu răspuns validat (Vox): aceleași antete ca apiPost (JSON + token), dar
 * erorile se aruncă, ca la `api`, iar răspunsul trece prin schemă. Ruta permite și Vite (:5173).
 * `token: null` pentru rutele fără token (utilizatorii): acolo serverul cere doar JSON și aceeași origine.
 */
export async function apiPostValidat<S extends z.ZodTypeAny>(cale: string, corp: unknown, token: string | null, schema: S): Promise<z.infer<S>> {
  const res = await fetch(cale, {
    method: 'POST',
    body: JSON.stringify(corp),
    headers: { 'Content-Type': 'application/json', ...(token ? { 'X-MIP-Token': token } : {}) },
  })
  return dinRaspuns(res, cale, schema)
}
