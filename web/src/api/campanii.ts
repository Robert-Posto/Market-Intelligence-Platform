import { useQuery } from '@tanstack/react-query'
import { Campanii, Comunicate } from '@mcc/shared'
import { api } from './client'

/**
 * Aceleași chei de cache în comutatorul de secțiuni și în secțiuni: o singură cerere.
 * Vin toate rândurile deodată (742 de campanii și 989 de comunicate pe 30.09.2026,
 * ~0,5 MB), iar filtrele se combină în pagină. Ținute 5 minute, ca în aplicația
 * veche: schimbarea secțiunii nu le mai cere din nou.
 */
const CINCI_MINUTE = 5 * 60_000

export const useCampanii = () =>
  useQuery({ queryKey: ['campanii'], queryFn: () => api('/api/campanii', Campanii), staleTime: CINCI_MINUTE })
export const useComunicate = () =>
  useQuery({ queryKey: ['comunicate'], queryFn: () => api('/api/comunicate', Comunicate), staleTime: CINCI_MINUTE })
