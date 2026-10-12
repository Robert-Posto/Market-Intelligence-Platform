import { useQuery } from '@tanstack/react-query'
import { News } from '@mcc/shared'
import { api } from './client'

/** Brief-ul de știri (ultimul sau, cu `id`, unul mai vechi) și lista celor mai noi. */
export const useNews = (id?: number) =>
  useQuery({
    queryKey: ['news', id ?? 'ultimul'],
    queryFn: () => api('/api/news', News, id ? { id } : undefined),
    placeholderData: (p) => p,
  })
