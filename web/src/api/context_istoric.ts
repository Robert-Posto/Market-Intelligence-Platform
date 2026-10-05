import { useQuery } from '@tanstack/react-query'
import { IstoricPreturi } from '@mcc/shared'
import { api } from './client'

/**
 * Banca și direcția le filtrează serverul; perioada, tipul și ordinea le aplică
 * pagina, pe datele venite toate odată (ca în aplicația veche). La un filtru nou,
 * lista veche rămâne (estompată) până vine cea nouă.
 * Indicii BNR pentru 2.6 vin din `useIndici` (api/rate_mobil.ts).
 */
export const useIstoric = (banca: string, directie: string) =>
  useQuery({
    queryKey: ['istoric', banca, directie],
    queryFn: () => api('/api/istoric', IstoricPreturi, { banca: banca || undefined, directie: directie || undefined }),
    placeholderData: (p) => p,
  })
