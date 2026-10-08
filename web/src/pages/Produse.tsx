import ComparatieLibra from './produse/ComparatieLibra'

/**
 * 2.1 Produse & prețuri: doar vederea „Comparație cu Libra”. Matricea „Comisioane
 * pe bănci” (bancă × serviciu, /api/matrice) a fost scoasă din pagină pe 08.10.2026;
 * e în istoricul git dacă e nevoie din nou. Linkurile vechi `#/produse?grup=…`
 * deschid acum tot comparația.
 */
export default function Produse() {
  return <ComparatieLibra />
}
