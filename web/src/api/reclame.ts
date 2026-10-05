import { useQuery } from '@tanstack/react-query'
import { ReclameBing, ReclameGoogle } from '@mcc/shared'
import { api } from './client'

export const useBing = () => useQuery({ queryKey: ['bing'], queryFn: () => api('/api/reclame_bing', ReclameBing) })

/**
 * Google se filtrează și se paginează pe server (16.765 de reclame la 30.09.2026):
 * fiecare combinație de filtre e altă cerere. Fără parametri = numărătoarea de pe comutator.
 */
export const useGoogle = (params: Record<string, string | number> = {}) =>
  useQuery({
    queryKey: ['google', params],
    queryFn: () => api('/api/reclame_google', ReclameGoogle, params),
    placeholderData: (p) => p,
  })
