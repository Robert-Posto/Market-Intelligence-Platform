import type { DictKey } from './i18n'

/**
 * Meniul și paginile, în aceeași ordine ca în aplicația veche. `mutata`: pagina
 * are deja varianta React; celelalte se deschid încă în aplicația veche.
 */
export interface Pagina {
  id: string
  pdf: string
  mutata: boolean
}
export interface Grup {
  grup: DictKey
  chei: Pagina[]
}

export const PAGINI: Grup[] = [
  {
    grup: 'pagini.grup.colectare',
    chei: [
      { id: 'overview', pdf: '', mutata: true },
      { id: 'produse', pdf: '2.1', mutata: true },
      { id: 'rate', pdf: '2.2', mutata: true },
      { id: 'mobil', pdf: '2.3', mutata: true },
      { id: 'campanii', pdf: '2.4', mutata: true },
      { id: 'retea', pdf: '2.5', mutata: true },
      { id: 'context', pdf: '2.6', mutata: true },
    ],
  },
  {
    grup: 'pagini.grup.analiza',
    chei: [
      { id: 'versus', pdf: '', mutata: true },
      { id: 'banca', pdf: '', mutata: true },
      { id: 'concurenta', pdf: '', mutata: true },
      { id: 'istoric', pdf: '', mutata: true },
    ],
  },
  {
    grup: 'pagini.grup.date_guvernanta',
    chei: [
      { id: 'surse', pdf: '', mutata: true },
      { id: 'coada', pdf: '', mutata: true },
    ],
  },
  {
    // joburile fluxului de comparație (discovery, extragere, produse noi): durata, costul, erorile;
    // „Rulare manuală” le pornește de mână (până pe 06.10.2026 rulările manuale stăteau în Overview)
    grup: 'pagini.grup.logging',
    chei: [
      { id: 'logging', pdf: '', mutata: true },
      { id: 'rulare', pdf: '', mutata: true },
    ],
  },
]

export const TOATE = PAGINI.flatMap((g) => g.chei)
export const cheie = (id: string, parte: 'nume_meniu' | 'titlu' | 'descriere') => `pagini.${id}.${parte}` as DictKey
