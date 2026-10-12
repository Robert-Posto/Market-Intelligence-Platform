import { useQuery } from '@tanstack/react-query'
import { Indici, Mobil, Rate, Sentiment } from '@mcc/shared'
import { api } from './client'

/** `sursa`: 'referinta' la 2.2 (api/sursa.ts); gol la Versus și la fișa băncii (colectarea echipei). */
export const useRate = (categorie: string, termen: string, produs: string, sursa = '') =>
  useQuery({
    queryKey: ['rate', categorie, termen, produs, sursa],
    queryFn: () => api('/api/rate', Rate, { categorie, termen, produs, sursa: sursa || undefined }),
    placeholderData: (p) => p,
  })
export const useMobil = () => useQuery({ queryKey: ['mobil'], queryFn: () => api('/api/mobil', Mobil) })

/** Indicii BNR au o singură valoare pe zi: se cer o dată pe sesiune, nu la fiecare filtru. */
export const useIndici = () =>
  useQuery({ queryKey: ['indici'], staleTime: Infinity, queryFn: () => api('/api/indici', Indici) })

/** Alt filtru pe recenzii: lista veche rămâne (estompată) până vine cea nouă, ca în aplicația veche. */
export const useSentiment = (banca: string, nota: string, storefront: string) =>
  useQuery({
    queryKey: ['sentiment', banca, nota, storefront],
    queryFn: () => api('/api/sentiment', Sentiment, { banca, nota, storefront }),
    placeholderData: (p) => p,
  })
