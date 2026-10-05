import { useQuery } from '@tanstack/react-query'
import { Retele, Youtube } from '@mcc/shared'
import { DICT } from '../i18n/dict'
import { api, ApiError } from './client'

export const useRetele = () => useQuery({ queryKey: ['retele'], queryFn: () => api('/api/retele', Retele) })

/**
 * Un server pornit înainte de ruta /api/youtube răspunde 404: secțiunea YouTube
 * spune asta, restul paginii 2.4 merge. Motivul rămâne textul românesc din
 * aplicația veche (îl afișează și tabelul surselor), iar `fara_ruta` îi spune
 * paginii să-l ia din dicționar, în limba aleasă.
 */
const FARA_RUTA: Youtube = {
  data_extragerii: null,
  sterge_la: null,
  motiv: DICT['campanii.youtube.motiv_fara_ruta'][0],
  banci: {},
  fara_ruta: true,
}

/** Obiectul de rezervă de mai sus, nu un răspuns al serverului. */
export const faraRutaYoutube = (d: Youtube) => d.fara_ruta === true

export const useYoutube = () =>
  useQuery({
    queryKey: ['youtube'],
    queryFn: async () => {
      try {
        return await api('/api/youtube', Youtube)
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) return FARA_RUTA
        throw e
      }
    },
  })
