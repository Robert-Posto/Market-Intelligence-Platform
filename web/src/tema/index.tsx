import { useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { CHEIE_TEMA, TemaContext, valideazaTema, type TemaState } from './context'

export type { Tema, TemaState } from './context'

const SISTEM_INTUNECAT = '(prefers-color-scheme: dark)'

function citesteTema() {
  try {
    return valideazaTema(localStorage.getItem(CHEIE_TEMA))
  } catch {
    return 'sistem' as const
  }
}

/**
 * Alegerea se ține minte în browser. public/tema-init.js a pus deja tema pe <html>
 * înainte de primul cadru; de aici React o ține la zi: la comutare și, pe „Ca
 * sistemul”, la o schimbare din Windows făcută cu aplicația deschisă.
 */
export function TemaProvider({ children }: { children: ReactNode }) {
  const [tema, setTemaState] = useState(citesteTema)
  const [sistemIntunecat, setSistemIntunecat] = useState(() => window.matchMedia(SISTEM_INTUNECAT).matches)
  useEffect(() => {
    const mq = window.matchMedia(SISTEM_INTUNECAT)
    const f = (e: MediaQueryListEvent) => setSistemIntunecat(e.matches)
    mq.addEventListener('change', f)
    return () => mq.removeEventListener('change', f)
  }, [])
  const intunecat = tema === 'intunecat' || (tema === 'sistem' && sistemIntunecat)
  useEffect(() => {
    const html = document.documentElement
    html.dataset.theme = intunecat ? 'dark' : 'light'
    html.style.colorScheme = intunecat ? 'dark' : 'light'
  }, [intunecat])
  const value = useMemo<TemaState>(() => ({
    tema,
    intunecat,
    setTema: (t) => {
      try {
        localStorage.setItem(CHEIE_TEMA, t)
      } catch {
        /* fără stocare: alegerea ține până la reîncărcare */
      }
      setTemaState(t)
    },
  }), [tema, intunecat])
  return <TemaContext.Provider value={value}>{children}</TemaContext.Provider>
}

export function useTema(): TemaState {
  return useContext(TemaContext)
}
