import { useQuery } from '@tanstack/react-query'
import { ContAplicatie, ConturiAplicatie, type RolCont } from '@mcc/shared'
import { api, apiPostValidat } from './client'

/** Conturile aplicației, cu rolul dat aici (doar admin; serverul răspunde 403 analistului). */
export const useConturi = () =>
  useQuery({ queryKey: ['utilizatori'], queryFn: () => api('/api/utilizatori', ConturiAplicatie) })

/** Rolul (`null` = fără acces) și/sau starea unui cont. Erorile vin ca cod (`ut.eroare.*`). */
export const modificaCont = (utilizator: string, schimbari: { rol?: RolCont | null; activ?: boolean }) =>
  apiPostValidat('/api/utilizatori/modifica', { utilizator, ...schimbari }, null, ContAplicatie)
