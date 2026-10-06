import { useQuery } from '@tanstack/react-query'
import { RulareManualaCatalog, RulareManualaEstimare } from '@mcc/shared'
import { api } from './client'

/** Tipurile de job, băncile fluxului de extragere și produsele Libra active (pentru modalul „Începe job”). */
export function useCatalogRulare() {
  return useQuery({ queryKey: ['rulare_manuala'], staleTime: 5 * 60_000,
    queryFn: () => api('/api/rulare_manuala', RulareManualaCatalog) })
}

/** Estimarea de cost și durată, doar când tipul, banca și (unde trebuie) produsul sunt alese. */
export function useEstimareRulare(tip: string, banca: string, produs: string, gata: boolean) {
  return useQuery({
    queryKey: ['rulare_manuala_estimare', tip, banca, produs],
    enabled: gata,
    queryFn: () => api('/api/rulare_manuala/estimare', RulareManualaEstimare, { tip, banca, produs }),
  })
}
