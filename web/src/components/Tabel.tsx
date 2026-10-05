import { useMemo, useState, type ReactNode } from 'react'
import { Table, Tooltip } from 'antd'
import type { ColumnType } from 'antd/es/table'
import { useLang } from '../i18n'
import { compara } from '../util/format'

/**
 * Tabelul comun al aplicației vechi, pe Table din AntD, cu aceleași reguli:
 *  - primul clic pe un antet sortează descrescător (cifrele mari sus), al doilea crescător;
 *  - golurile rămân jos în ambele sensuri;
 *  - rândul Libra rămâne primul, oricum s-ar sorta.
 * AntD singur nu le are pe ultimele două, deci sortarea se face aici, iar
 * tabelul primește lista deja ordonată.
 */
export interface Coloana<R> {
  cheie: string
  cap: ReactNode
  /** explicația din antet, la hover (`titlu` din tabelul vechi) */
  titlu?: string
  /** valoarea după care se sortează; fără ea, coloana nu e sortabilă */
  s?: (r: R) => unknown
  val: (r: R) => ReactNode
  num?: boolean
  /** clasă și clic pe celulă (matricea 2.1) */
  td?: (r: R) => { className?: string; onClick?: () => void; title?: string } | undefined
}

export function Tabel<R>({
  randuri,
  coloane,
  cheieRand,
  libra,
  implicit,
  gol,
  clasaRand,
  onRand,
}: {
  randuri: R[]
  coloane: Coloana<R>[]
  cheieRand: (r: R) => string
  libra?: (r: R) => string
  implicit?: [string, 'ascend' | 'descend']
  gol?: ReactNode
  clasaRand?: (r: R) => string
  /** clic pe tot rândul (deschide sertarul, filtrează); un clic pe un link din rând nu ajunge aici */
  onRand?: (r: R) => void
}) {
  const { t, locale } = useLang()
  const [sort, setSort] = useState<[string, 'ascend' | 'descend'] | null>(implicit ?? null)

  const lista = useMemo(() => {
    const l = randuri.slice()
    const c = sort && coloane.find((x) => x.cheie === sort[0])
    if (c?.s) {
      const sens = sort![1] === 'ascend' ? 1 : -1
      l.sort((a, b) => {
        const va = c.s!(a)
        const vb = c.s!(b)
        const gol = (x: unknown) => x === null || x === undefined || x === '' || (typeof x === 'number' && Number.isNaN(x))
        if (gol(va) || gol(vb)) return compara(va, vb, locale)
        return compara(va, vb, locale) * sens
      })
    }
    if (libra) l.sort((a, b) => Number(libra(b) === 'libra') - Number(libra(a) === 'libra'))
    return l
  }, [randuri, coloane, sort, libra, locale])

  const cols: ColumnType<R>[] = coloane.map((c) => ({
    key: c.cheie,
    title: c.titlu ? <Tooltip title={c.titlu}>{c.cap}</Tooltip> : c.cap,
    // fără `align` pe celelalte: AntD îl pune inline și ar bate alinierea din CSS (celulele matricei, la dreapta)
    align: c.num ? 'right' : undefined,
    className: c.num ? 'num' : undefined,
    render: (_: unknown, r: R) => c.val(r),
    onCell: c.td ? (r: R) => c.td!(r) ?? {} : undefined,
    sorter: c.s ? true : undefined,
    sortDirections: ['descend', 'ascend', 'descend'],
    sortOrder: sort && sort[0] === c.cheie ? sort[1] : null,
    showSorterTooltip: false,
  }))

  if (!randuri.length) return <p className="note">{gol ?? t('comun.nimic_de_afisat')}</p>
  return (
    <Table<R>
      className="t"
      size="small"
      columns={cols}
      dataSource={lista}
      rowKey={cheieRand}
      pagination={false}
      rowClassName={(r) => [libra && libra(r) === 'libra' ? 'libra' : '', onRand ? 'clic' : '', clasaRand?.(r) ?? ''].join(' ').trim()}
      onRow={onRand ? (r) => ({ onClick: (e) => { if (!(e.target as HTMLElement).closest('a, button')) onRand(r) } }) : undefined}
      onChange={(_p, _f, s) => {
        const x = Array.isArray(s) ? s[0] : s
        setSort(x?.order ? [String(x.columnKey), x.order] : null)
      }}
    />
  )
}
