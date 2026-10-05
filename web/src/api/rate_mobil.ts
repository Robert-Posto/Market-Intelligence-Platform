import { useQuery } from '@tanstack/react-query'
import { Mobil, Rate } from '@mcc/shared'
import { api } from './client'

export const useRate = (categorie: string, termen: string, produs: string) =>
  useQuery({
    queryKey: ['rate', categorie, termen, produs],
    queryFn: () => api('/api/rate', Rate, { categorie, termen, produs }),
    placeholderData: (p) => p,
  })
export const useMobil = () => useQuery({ queryKey: ['mobil'], queryFn: () => api('/api/mobil', Mobil) })
