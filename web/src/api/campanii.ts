import { useQuery } from '@tanstack/react-query'
import { Campanii, Comunicate } from '@mcc/shared'
import { api } from './client'

/** Aceleași chei de cache în comutatorul de secțiuni și în secțiuni: o singură cerere. */
export const useCampanii = () => useQuery({ queryKey: ['campanii'], queryFn: () => api('/api/campanii', Campanii) })
export const useComunicate = () => useQuery({ queryKey: ['comunicate'], queryFn: () => api('/api/comunicate', Comunicate) })
