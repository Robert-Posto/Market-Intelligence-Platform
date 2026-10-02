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
      { id: 'rate', pdf: '2.2', mutata: false },
      { id: 'mobil', pdf: '2.3', mutata: false },
      { id: 'campanii', pdf: '2.4', mutata: false },
      { id: 'retea', pdf: '2.5', mutata: false },
      { id: 'context', pdf: '2.6', mutata: false },
    ],
  },
  {
    grup: 'pagini.grup.analiza',
    chei: [
      { id: 'versus', pdf: '', mutata: false },
      { id: 'banca', pdf: '', mutata: false },
      { id: 'istoric', pdf: '', mutata: false },
    ],
  },
  {
    grup: 'pagini.grup.date_guvernanta',
    chei: [
      { id: 'surse', pdf: '', mutata: false },
      { id: 'coada', pdf: '', mutata: false },
    ],
  },
]

export const TOATE = PAGINI.flatMap((g) => g.chei)
export const cheie = (id: string, parte: 'nume_meniu' | 'titlu' | 'descriere') => `pagini.${id}.${parte}` as DictKey
