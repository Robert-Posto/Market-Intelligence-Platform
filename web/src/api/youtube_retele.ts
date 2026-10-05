import { useQuery } from '@tanstack/react-query'
import { Retele, Youtube } from '@mcc/shared'
import { api } from './client'

export const useRetele = () => useQuery({ queryKey: ['retele'], queryFn: () => api('/api/retele', Retele) })
export const useYoutube = () => useQuery({ queryKey: ['youtube'], queryFn: () => api('/api/youtube', Youtube) })
