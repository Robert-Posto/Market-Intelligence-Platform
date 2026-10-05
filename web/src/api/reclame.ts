import { useQuery } from '@tanstack/react-query'
import { ReclameBing, ReclameGoogle } from '@mcc/shared'
import { api } from './client'

/**
 * Ținute 5 minute, ca în aplicația veche (cmia): schimbarea secțiunii 2.4 nu
 * mai cere fișierele din nou (pagina întreagă însemna 1,6 MB pe 30.09.2026).
 */
const CINCI_MINUTE = 5 * 60_000

export const useBing = () =>
  useQuery({ queryKey: ['bing'], queryFn: () => api('/api/reclame_bing', ReclameBing), staleTime: CINCI_MINUTE })

/**
 * Google se filtrează și se paginează pe server (16.765 de reclame la 30.09.2026):
 * fiecare combinație de filtre e altă cerere. Fără parametri = numărătoarea de pe
 * comutator și agregatele secțiunii; secțiunea nu trimite parametrii goi sau impliciți,
 * ca fără filtre aceeași cerere să servească pe amândouă.
 */
export const useGoogle = (params: Record<string, string | number> = {}) =>
  useQuery({
    queryKey: ['google', params],
    queryFn: () => api('/api/reclame_google', ReclameGoogle, params),
    placeholderData: (p) => p,
    staleTime: CINCI_MINUTE,
  })
