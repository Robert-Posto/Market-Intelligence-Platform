import { useQuery } from '@tanstack/react-query'
import { ReteaLocatii } from '@mcc/shared'
import { api } from './client'

/**
 * Toate locațiile (683 pe 05.10.2026): 2.5 și harta citesc același răspuns, deci se cere o dată.
 * Cheia are prefixul zonei: fișa băncii cere și ea /api/locatii, cu schema ei.
 */
export const useLocatii = () =>
  useQuery({ queryKey: ['retea', 'locatii'], queryFn: () => api('/api/locatii', ReteaLocatii) })
