import { useQuery } from '@tanstack/react-query'
import { z } from 'zod'
import { Conversatie, ConversatieRezumat, RaspunsVox, Redenumire, Stergere, VoxStare, type Interpretare } from '@mcc/shared'
import { api, apiPostValidat } from './client'

/** Starea funcției (activă doar local, cu MIP_PERMITE_VOX=1 și cheia reală) și tokenul POST-ului. */
export function useStareVox() {
  return useQuery({ queryKey: ['vox'], queryFn: () => api('/api/vox', VoxStare) })
}

/** Lista se reîncarcă după o întrebare, o redenumire sau o ștergere. */
export const CHEIE_CONVERSATII = ['vox-conversatii']

/** Conversațiile salvate pe laptop: doar citește fișiere, nu cheamă modelul. */
export function useConversatii() {
  return useQuery({ queryKey: CHEIE_CONVERSATII, queryFn: () => api('/api/vox/conversatii', z.array(ConversatieRezumat)) })
}

export function citesteConversatia(id: string) {
  return api(`/api/vox/conversatii/${encodeURIComponent(id)}`, Conversatie)
}

/** O întrebare = un apel plătit la model: doar la clic, niciodată la randare; `conversatie` null începe una. */
export function trimiteIntrebarea(intrebare: string, anterior: Interpretare | null, conversatie: string | null, token: string) {
  return apiPostValidat('/api/vox', { intrebare, anterior, conversatie }, token, RaspunsVox)
}

export function redenumesteConversatia(id: string, titlu: string, token: string) {
  return apiPostValidat(`/api/vox/conversatii/${encodeURIComponent(id)}/redenumeste`, { titlu }, token, Redenumire)
}

export function stergeConversatia(id: string, token: string) {
  return apiPostValidat(`/api/vox/conversatii/${encodeURIComponent(id)}/sterge`, {}, token, Stergere)
}
