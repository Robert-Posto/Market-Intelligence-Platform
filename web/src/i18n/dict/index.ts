// Dicționarele pe secțiuni; cheile au prefixul secțiunii, deci nu se suprapun.
import { comun } from './comun'
import { overview } from './overview'
import { banca_produse } from './banca_produse'
import { rate_mobil } from './rate_mobil'
import { retea_campanii1 } from './retea_campanii1'
import { campanii2_context } from './campanii2_context'
import { versus_coada } from './versus_coada'
import { harta_pdf } from './harta_pdf'
import { server_db } from './server_db'

export const DICT = {
  ...comun,
  ...overview,
  ...banca_produse,
  ...rate_mobil,
  ...retea_campanii1,
  ...campanii2_context,
  ...versus_coada,
  ...harta_pdf,
  ...server_db,
} as const
