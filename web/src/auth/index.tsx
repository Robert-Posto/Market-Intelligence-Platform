import { useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { EVENIMENT_SESIUNE_EXPIRATA } from '../api/client'
import { SesiuneContext, type CodLogare, type Rol, type SesiuneState, type Stare, type Utilizator } from './context'
import PaginaLogare from './PaginaLogare'

export type { CodLogare, Rol, SesiuneState, Utilizator } from './context'

const CODURI: readonly string[] = ['date_invalide', 'fara_rol', 'prea_multe_incercari', 'ad_indisponibil']

function citeste(corp: unknown): Utilizator | null {
  if (!corp || typeof corp !== 'object') return null
  const c = corp as Record<string, unknown>
  if (typeof c.utilizator !== 'string' || (c.rol !== 'admin' && c.rol !== 'analist')) return null
  return { utilizator: c.utilizator, nume: typeof c.nume === 'string' && c.nume ? c.nume : c.utilizator, rol: c.rol, local: c.local === true }
}

/**
 * După logare ne întoarcem doar la o rută internă a aplicației (`#/...`). Un hash
 * străin (`#//evil`, `#javascript:...`) nu poate duce în altă parte, dar îl aducem
 * la o adresă cunoscută ca să nu rămână o rută fără sens.
 */
function rutaInterna(): void {
  if (!/^#\/(?![/\\])/.test(window.location.hash)) window.location.hash = '#/overview'
}

/**
 * Întreabă serverul cine e utilizatorul. În dezvoltare, un API fără rutele de
 * autentificare (404 sau răspuns care nu e JSON) înseamnă „autentificarea nu e încă
 * pusă pe server”, deci se lucrează ca admin local, ca până acum. În producție 404
 * NU are voie să însemne asta: un server fără rute de autentificare ar deschide
 * aplicația oricui, așa că acolo orice răspuns diferit de 200 valid = neautentificat.
 */
async function intrebaSesiunea(): Promise<Utilizator | null> {
  try {
    const r = await fetch('/api/sesiune')
    const corp = (await r.json().catch(() => undefined)) as unknown
    if (r.ok) {
      const u = citeste(corp)
      if (u) return u
    }
    if (import.meta.env.DEV && (r.status === 404 || corp === undefined)) {
      return { utilizator: 'local', nume: 'local', rol: 'admin', local: true }
    }
  } catch {
    /* serverul nu răspunde: la logare se vede mesajul */
  }
  return null
}

export function SesiuneProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient()
  const [stare, setStare] = useState<Stare>('se_incarca')
  const [utilizator, setUtilizator] = useState<Utilizator | null>(null)
  const [expirata, setExpirata] = useState(false)

  useEffect(() => {
    let activ = true
    void intrebaSesiunea().then((u) => {
      if (!activ) return
      setUtilizator(u)
      setStare(u ? 'autentificat' : 'neautentificat')
    })
    return () => { activ = false }
  }, [])

  // Un 401 de la orice cerere de date: sesiunea a expirat. Golim cache-ul, ca datele
  // utilizatorului dinainte să nu se vadă (sau să nu rămână) pentru cel care se loghează apoi.
  useEffect(() => {
    const laExpirare = () => {
      qc.clear()
      setUtilizator(null)
      setStare('neautentificat')
      setExpirata(true)
    }
    window.addEventListener(EVENIMENT_SESIUNE_EXPIRATA, laExpirare)
    return () => window.removeEventListener(EVENIMENT_SESIUNE_EXPIRATA, laExpirare)
  }, [qc])

  const logare = useCallback(async (nume: string, parola: string): Promise<CodLogare | null> => {
    let r: Response
    try {
      r = await fetch('/api/autentificare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ utilizator: nume, parola }),
      })
    } catch {
      return 'retea'
    }
    const corp = (await r.json().catch(() => null)) as unknown
    const u = r.ok ? citeste(corp) : null
    if (u) {
      qc.clear()
      rutaInterna()
      setUtilizator(u)
      setExpirata(false)
      setStare('autentificat')
      return null
    }
    const cod = corp && typeof corp === 'object' ? String((corp as { eroare?: unknown }).eroare ?? '') : ''
    return CODURI.includes(cod) ? (cod as CodLogare) : 'generic'
  }, [qc])

  const delogare = useCallback(async () => {
    try {
      await fetch('/api/delogare', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
    } catch {
      /* oricum închidem sesiunea în interfață; cookie-ul expiră pe server */
    }
    qc.clear()
    setUtilizator(null)
    setExpirata(false)
    setStare('neautentificat')
  }, [qc])

  const value = useMemo<SesiuneState>(() => ({ stare, utilizator, expirata, logare, delogare }), [stare, utilizator, expirata, logare, delogare])

  if (stare === 'se_incarca') return <div className="logare-asteapta" aria-busy="true" />
  return (
    <SesiuneContext.Provider value={value}>
      {stare === 'autentificat' ? children : <PaginaLogare />}
    </SesiuneContext.Provider>
  )
}

export function useSesiune(): SesiuneState {
  return useContext(SesiuneContext)
}

/** Rolul curent; în afara unei sesiuni (nu se întâmplă: paginile sunt montate doar autentificat) — `analist`, cel mai restrâns. */
export function useRol(): Rol {
  return useSesiune().utilizator?.rol ?? 'analist'
}
