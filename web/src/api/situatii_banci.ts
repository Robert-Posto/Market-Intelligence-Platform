import { useQuery } from '@tanstack/react-query'
import { SituatiiBanci } from '@mcc/shared'
import { api } from './client'

/** Toate băncile și toți anii dintr-o cerere (~200 KB): filtrele și cotele se calculează în pagină. */
export const useSituatiiBanci = () =>
  useQuery({ queryKey: ['situatii_banci'], staleTime: Infinity, queryFn: () => api('/api/situatii_banci', SituatiiBanci) })
