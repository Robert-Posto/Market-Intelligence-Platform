import { useQuery } from '@tanstack/react-query'
import { RulareManualaCatalog, RulareManualaEstimare } from '@mcc/shared'
import { api } from './client'

/** Tipurile de job, băncile fluxului de extragere și produsele Libra active (pentru modalul „Începe job”). */
export function useCatalogRulare() {
  return useQuery({ queryKey: ['rulare_manuala'], staleTime: 5 * 60_000,
    queryFn: () => api('/api/rulare_manuala', RulareManualaCatalog) })
}

/**
 * Estimarea de cost și durată, doar când tipul, băncile și (unde trebuie) produsul sunt alese.
 * O bancă: estimarea ei; mai multe: suma lor (`total`), pentru că rulează pe rând.
 */
export function useEstimareRulare(tip: string, banci: string[], produs: string, gata: boolean) {
  const params = banci.length === 1 ? { tip, banca: banci[0], produs } : { tip, banci: banci.join(','), produs }
  return useQuery({
    queryKey: ['rulare_manuala_estimare', tip, banci.join(','), produs],
    enabled: gata,
    placeholderData: (vechi) => vechi,
    queryFn: () => api('/api/rulare_manuala/estimare', RulareManualaEstimare, params),
  })
}
