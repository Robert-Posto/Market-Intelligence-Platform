import { useQuery } from '@tanstack/react-query'
import { VoxStare, RaspunsIntrebare, type Interpretare } from '@mcc/shared'
import { api, apiPostValidat } from './client'

/** Starea funcției (activă doar local, cu MIP_PERMITE_VOX=1 și cheia reală) și tokenul POST-ului. */
export function useStareVox() {
  return useQuery({ queryKey: ['vox'], queryFn: () => api('/api/vox', VoxStare) })
}

/** O întrebare = un apel plătit la model: doar la clic, niciodată la randare (deci nu prin useQuery). */
export function trimiteIntrebarea(intrebare: string, anterior: Interpretare | null, token: string) {
  return apiPostValidat('/api/vox', { intrebare, anterior }, token, RaspunsIntrebare)
}
