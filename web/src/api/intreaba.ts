import { useQuery } from '@tanstack/react-query'
import { IntrebariStare, RaspunsIntrebare, type Interpretare } from '@mcc/shared'
import { api, apiPostValidat } from './client'

/** Starea funcției (activă doar local, cu MIP_PERMITE_INTREBARI=1 și cheia reală) și tokenul POST-ului. */
export function useStareIntrebari() {
  return useQuery({ queryKey: ['intreaba'], queryFn: () => api('/api/intreaba', IntrebariStare) })
}

/** O întrebare = un apel plătit la model: doar la clic, niciodată la randare (deci nu prin useQuery). */
export function trimiteIntrebarea(intrebare: string, anterior: Interpretare | null, token: string) {
  return apiPostValidat('/api/intreaba', { intrebare, anterior }, token, RaspunsIntrebare)
}
