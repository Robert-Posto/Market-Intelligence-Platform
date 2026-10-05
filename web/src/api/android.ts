import { useQuery } from '@tanstack/react-query'
import { Android, BiblioteciAndroid } from '@mcc/shared'
import { api } from './client'

/**
 * 2.3, Android. Totul vine dintr-o cerere (~2.700 de rânduri pe 05.10.2026), iar
 * filtrele și secțiunile se combină în pagină; datele se schimbă doar la o nouă
 * încărcare a pachetului, deci schimbarea secțiunii nu le cere din nou.
 */
const CINCI_MINUTE = 5 * 60_000

export const useAndroid = () =>
  useQuery({ queryKey: ['android'], queryFn: () => api('/api/android', Android), staleTime: CINCI_MINUTE })

/** Bibliotecile (3.644 de rânduri în total, ~200 pe aplicație) se cer doar când se deschide detaliul aplicației. */
export const useBiblioteciAndroid = (pachet: string | null) =>
  useQuery({
    queryKey: ['android', 'biblioteci', pachet],
    enabled: !!pachet,
    queryFn: () => api('/api/android', BiblioteciAndroid, { package: pachet }),
    staleTime: CINCI_MINUTE,
  })
