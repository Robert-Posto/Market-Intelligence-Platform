import { useSearchParams } from 'react-router-dom'

/**
 * Filtrele Surselor și ale Cozii stau în adresă, ca în aplicația veche
 * (`#/coada?banca=bcr` vine din Overview și din fișa băncii). Parametrii goi
 * nu intră în adresă: `#/surse?banca=bcr`, nu `…&stare=&rol=&q=&motiv=&offset=`;
 * adresele vechi, cu parametrii goi, se citesc la fel.
 */
export function useFiltreAdresa<K extends string>(chei: readonly K[]) {
  const [sp, setSp] = useSearchParams()
  const f = Object.fromEntries(chei.map((k) => [k, sp.get(k) ?? ''])) as Record<K, string>
  const offset = Math.max(0, Number.parseInt(sp.get('offset') ?? '', 10) || 0)
  /** orice filtru nou duce la prima pagină, ca în aplicația veche; doar paginarea păstrează `offset` */
  const mergi = (o: Partial<Record<K, string>>, pagina?: number) =>
    setSp(() => {
      const n = new URLSearchParams()
      for (const k of chei) {
        const v = k in o ? o[k] : f[k]
        if (v) n.set(k, v)
      }
      if (pagina) n.set('offset', String(pagina))
      return n
    })
  const pagina = (o: number) => mergi({}, o)
  const sterge = () => setSp(new URLSearchParams())
  const activ = chei.some((k) => f[k])
  /** parametrii cererii: doar cei completați, ca adresa */
  const parametri = (limit: number) => {
    const p: Record<string, string | number> = { limit }
    if (offset) p.offset = offset
    for (const k of chei) if (f[k]) p[k] = f[k]
    return p
  }
  return { f, offset, mergi, pagina, sterge, activ, parametri }
}
