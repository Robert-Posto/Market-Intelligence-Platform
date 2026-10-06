import { useQuery } from '@tanstack/react-query'
import { ComparatieLibra, ProduseConcurenta } from '@mcc/shared'
import { api } from './client'

/** Lista produselor Libra, cu acoperirea pe bănci; aceeași pentru orice produs ales. */
export const useComparatieLibra = () =>
  useQuery({ queryKey: ['comparatie_libra'], queryFn: () => api('/api/comparatie_libra', ComparatieLibra) })

/** Valorile unui produs: cererea pornește doar după ce s-a ales produsul. */
export const useComparatieProdus = (cod: string | null) =>
  useQuery({
    queryKey: ['comparatie_libra', cod],
    queryFn: () => api('/api/comparatie_libra', ComparatieLibra, { produs: cod }),
    enabled: !!cod,
  })

export const useProduseConcurenta = () =>
  useQuery({ queryKey: ['products_discovery'], queryFn: () => api('/api/products_discovery', ProduseConcurenta) })
