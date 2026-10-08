import { useQuery } from '@tanstack/react-query'
import { InventarProduse, TokenInventar, type ProdusDeSalvat } from '@mcc/shared'
import { api, apiPost } from './client'

/** Produsele din produse_libra.json, cu starea fiecăruia în bază. */
export function useInventarProduse() {
  return useQuery({ queryKey: ['inventar_produse'], queryFn: () => api('/api/inventar_produse', InventarProduse) })
}

/**
 * Tokenul de scriere. Prin proxy-ul Vite tokenul ar veni (proxy-ul rescrie Host),
 * dar salvarea e refuzată oricum (Origin :5173), deci în dezvoltare nici nu se cere:
 * pagina rămâne doar de citire, cu explicația, în loc de butoane care eșuează.
 */
export function useTokenInventar() {
  return useQuery({
    queryKey: ['inventar_produse_token'],
    enabled: !import.meta.env.DEV,
    queryFn: () => api('/api/inventar_produse/token', TokenInventar),
    retry: false,
    staleTime: Infinity,
  })
}

export type ActiuneInventar = 'adauga' | 'modifica' | 'sterge'

export function salveazaProdus(actiune: ActiuneInventar, produs: ProdusDeSalvat | { cod: string }, versiune: string, token: string) {
  return apiPost(`/api/inventar_produse/${actiune}`, { ...produs, versiune }, token)
}
