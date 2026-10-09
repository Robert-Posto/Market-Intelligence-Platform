import { useQuery } from '@tanstack/react-query'
import { VersusExtra, VersusLibra, VersusMatrice } from '@mcc/shared'
import { api } from './client'

/**
 * Comisioanele din Versus: persoane fizice, în lei, ca în aplicația veche. Cheia e
 * alta decât la 2.1: aceeași adresă, dar altă schemă (aici și mediana, titlul, sensul).
 */
/** Versus compară prețurile pentru persoane fizice; sertarul celulei cere același segment. */
export const SEGMENT_VERSUS = 'pf'

export const useVersusMatrice = (grup: string) =>
  useQuery({
    queryKey: ['versus_matrice', grup],
    queryFn: () => api('/api/matrice', VersusMatrice, { grup, segment: SEGMENT_VERSUS, unitate: 'lei' }),
  })

export const useVersusExtra = () => useQuery({ queryKey: ['versus_extra'], queryFn: () => api('/api/versus_extra', VersusExtra) })

/** Produsele Libra față de echivalentele lor, din fluxul comparației (o singură cerere pentru toate). */
export const useVersusLibra = () => useQuery({ queryKey: ['versus_libra'], queryFn: () => api('/api/versus_libra', VersusLibra) })
