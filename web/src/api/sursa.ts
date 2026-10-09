/**
 * De unde citesc 2.1 (Produse & prețuri) și 2.2 (Rate & indicatori) prețurile și dobânzile.
 *
 * 'libra': fluxul comparației cu Libra (extragere_produse_bancare: comparatie_libra +
 * surse_libra), prin aceleași rute (/api/matrice, /api/rate, /api/celula) cu `sursa=libra`;
 * serverul mapează câmpurile fluxului pe serviciile paginilor (app/server.py, _CTE_LIBRA).
 * '' (gol): colectarea generală a echipei (observatii_curente), ca înainte.
 * Versus și Fișa băncii citesc mai departe din colectarea generală.
 */
export const SURSA_PRETURI = 'libra'
