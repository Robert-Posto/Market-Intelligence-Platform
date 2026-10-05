import { useQuery } from '@tanstack/react-query'
import { AcoperireFisa, CatalogLibra, LocatiiFisa, MatriceFisa } from '@mcc/shared'
import { api } from './client'

/** Cererile zonei „banca” (le scrie agentul care mută paginile ei). */
export const _banca = { useQuery, api }

/*
 * Cheile încep cu „fisa”: alte pagini cer aceleași adrese cu schemele lor, iar
 * o cheie comună ar da fișei datele validate de altă schemă (fără `note`,
 * `surse` sau `valoare` în tipuri).
 */

/** Acoperirea, matricea și locațiile sunt pe toate băncile: schimbarea băncii nu le cere din nou. */
export const useAcoperireFisa = () =>
  useQuery({ queryKey: ['fisa', 'acoperire'], queryFn: () => api('/api/acoperire', AcoperireFisa) })

/** Comisioanele fișei: cele trei grupuri din 2.1, pe toate segmentele, în lei (ca în aplicația veche). */
export const GRUPURI_FISA = ['cont_curent', 'carduri', 'transferuri'] as const

export const useMatriceFisa = () =>
  useQuery({
    queryKey: ['fisa', 'matrice'],
    queryFn: () =>
      Promise.all(GRUPURI_FISA.map((grup) => api('/api/matrice', MatriceFisa, { grup, segment: 'toate', unitate: 'lei' }))),
  })

export const useLocatiiFisa = () =>
  useQuery({ queryKey: ['fisa', 'locatii'], queryFn: () => api('/api/locatii', LocatiiFisa) })

/** Catalogul intern există doar pentru Libra (migrarea 020): pe celelalte bănci nu se cere. */
export const useCatalogLibra = (activ: boolean) =>
  useQuery({ queryKey: ['fisa', 'catalog_libra'], enabled: activ, queryFn: () => api('/api/catalog_libra', CatalogLibra) })
