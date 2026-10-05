import { useQuery } from '@tanstack/react-query'
import { CoadaVerificare, SurseInventar } from '@mcc/shared'
import { api } from './client'

/**
 * Surse și coada se filtrează și se paginează pe server (6.332 de surse și
 * 5.396 de valori în coadă pe 05.10.2026): fiecare combinație de filtre e altă
 * cerere. Rezultatul vechi rămâne pe ecran, estompat, până vine cel nou, ca în
 * aplicația veche (o pagină care sărea goală la fiecare filtru te arunca sus).
 */
export const useSurseInventar = (params: Record<string, string | number>) =>
  useQuery({
    queryKey: ['surse', params],
    queryFn: () => api('/api/surse', SurseInventar, params),
    placeholderData: (p) => p,
  })

export const useCoadaVerificare = (params: Record<string, string | number>) =>
  useQuery({
    queryKey: ['coada', params],
    queryFn: () => api('/api/coada', CoadaVerificare, params),
    placeholderData: (p) => p,
  })
