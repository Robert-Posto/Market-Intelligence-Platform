/** Texte adăugate la mutarea paginii în React (în afara extragerii din 02.10.2026). */
export const extra_banca = {
  // singularele care lipseau: pe 05.10.2026, UniCredit, CEC și Garanti aveau o sucursală, Patria și Garanti un ATM propriu,
  // iar 7 bănci din 15 aveau o singură recenzie negativă („1 negative” în aplicația veche)
  "banca.kpi_note_app_store_1": ["{n} notă în App Store", "{n} rating on the App Store"],
  "banca.kpi_retea_sucursale_1": ["{n} sucursală", "{n} branch"],
  "banca.kpi_retea_sucursale_n": ["{n} sucursale", "{n} branches"],
  "banca.kpi_retea_atm_1": ["{n} ATM", "{n} ATM"],
  "banca.kpi_retea_atm_n": ["{n} ATM-uri", "{n} ATMs"],
  "banca.kpi_retea_parteneri_1": ["+{n} partener", "+{n} partner ATM"],
  "banca.kpi_retea_parteneri_n": ["+{n} partenere", "+{n} partner ATMs"],
  "banca.recenzii_sumar_o_negativa": ["Nota recenziilor scrise <b>{medie_text} ★</b> din {n_recenzii} citite · {negative} negativă · nota App Store <b>{medie_store} ★</b>.", "Written-review rating <b>{medie_text} ★</b> from {n_recenzii} read · {negative} negative · App Store rating <b>{medie_store} ★</b>."],
} as const
