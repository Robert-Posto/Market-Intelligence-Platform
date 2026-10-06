import { useQuery } from '@tanstack/react-query'
import { z } from 'zod'
import { Banca, Logos } from '@mcc/shared'
import { api } from './client'

export interface Meta {
  nume: Record<string, string>
  logo: Record<string, string>
}

/** Numele și sigla băncilor apar pe aproape fiecare pagină: se cer o dată pe sesiune. */
export function useMeta() {
  return useQuery({
    queryKey: ['meta'],
    staleTime: Infinity,
    queryFn: async (): Promise<Meta> => {
      const [b, l] = await Promise.all([api('/api/banci', z.array(Banca)), api('/api/logos', Logos)])
      return { nume: Object.fromEntries(b.map((x) => [x.slug, x.nume])), logo: l }
    },
  })
}
