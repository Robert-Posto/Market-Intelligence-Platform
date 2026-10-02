import type { z } from 'zod'

/**
 * Toate cererile trec pe aici. Răspunsul se validează cu schema din
 * @mcc/shared: dacă serverul schimbă forma unui câmp, eroarea apare aici, cu
 * numele câmpului, nu ca o pagină goală.
 *
 * Serverul Python trimite erorile ca `{eroare: "..."}` cu 200, deci câmpul se
 * verifică explicit, ca în aplicația veche.
 */
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
  }
}

export async function api<S extends z.ZodTypeAny>(cale: string, schema: S, params?: Record<string, unknown>): Promise<z.infer<S>> {
  const url = new URL(cale, window.location.origin)
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null) url.searchParams.set(k, String(v))
    }
  }
  const res = await fetch(url)
  const corp = (await res.json().catch(() => null)) as unknown
  if (corp && typeof corp === 'object' && 'eroare' in corp && (corp as { eroare: unknown }).eroare) {
    throw new ApiError(res.status, String((corp as { eroare: unknown }).eroare))
  }
  if (!res.ok) throw new ApiError(res.status, `HTTP ${res.status}`)
  const rez = schema.safeParse(corp)
  if (!rez.success) {
    const p = rez.error.issues[0]
    throw new ApiError(res.status, `${cale}: ${p?.path.join('.') ?? ''} ${p?.message ?? ''}`)
  }
  return rez.data
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
  let d: { eroare?: string } = {}
  try {
    d = (await r.json()) as { eroare?: string }
  } catch {
    /* corp gol */
  }
  if (!r.ok && !d.eroare) d.eroare = `HTTP ${r.status}`
  return d
}
