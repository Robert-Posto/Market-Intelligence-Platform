import { useEffect, useState, type ReactNode } from 'react'
import { Table, type TableProps } from 'antd'

/** Marginea de sus a lui <main> (global.css: `main { padding: 26px … }`); bara de filtre o acoperă cu `top: -26px`. */
const SUS_MAIN = 26

/**
 * Cât de jos se lipește capul unui tabel la derularea paginii: sub ultima bară de filtre
 * (`.bara-fixa`) de dinaintea tabelului, oricât de înaltă e (se rupe pe rânduri la ferestre
 * înguste, deci se măsoară); fără bară, sus de tot. Valoarea e față de marginea conținutului
 * lui <main>, deci fără bară e -26.
 */
export function useSusCap(el: HTMLElement | null): number {
  const [sus, setSus] = useState(-SUS_MAIN)
  useEffect(() => {
    if (!el) return
    const bare = [...document.querySelectorAll<HTMLElement>('#principal .bara-fixa')]
      .filter((b) => b.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING)
    const bara = bare[bare.length - 1]
    if (!bara) {
      setSus(-SUS_MAIN)
      return
    }
    const masoara = () => setSus(bara.offsetHeight - SUS_MAIN)
    masoara()
    const obs = new ResizeObserver(masoara)
    obs.observe(bara)
    return () => obs.disconnect()
  }, [el])
  return sus
}

/**
 * Capul lipit pe pagină (varianta aleasă prin proba din 06.10.2026): `sticky` desparte capul
 * de corp în două tabele; `scroll.x: '100%'` cu `tableLayout: 'auto'` păstrează lățimea de azi
 * (textul se rupe pe rânduri în loc să împingă tabelul în lateral); tabelul capului ia exact
 * lățimile măsurate în corp (global.css, `.ant-table-header > table`).
 */
export function propsLipit<R>(sus: number): Pick<TableProps<R>, 'sticky' | 'scroll' | 'tableLayout'> {
  return {
    sticky: { offsetHeader: sus, getContainer: () => document.getElementById('principal') ?? window },
    scroll: { x: '100%' },
    tableLayout: 'auto',
  }
}

/**
 * Rândul fantomă: AntD dă capului lipit lățimile măsurate în corp, iar un cap lung peste
 * cifre scurte („Administrare cont”, cu descrierea, peste „0 lei”) s-ar înghesui. Rândul
 * acesta pune textul capului și în corp, invizibil și de înălțime zero, deci coloanele ies
 * cel puțin cât capul; locul săgeților de sortare e rezervat alături (`.fantoma-sort`).
 */
export function RandFantoma({ capuri }: { capuri: { cheie: string; cap: ReactNode; sortabil: boolean }[] }) {
  return (
    <Table.Summary.Row className="cap-fantoma">
      {capuri.map((c, i) => (
        <Table.Summary.Cell key={c.cheie} index={i}>
          <div className="fantoma" aria-hidden="true">
            <span>{c.cap}</span>
            {c.sortabil && <span className="fantoma-sort" />}
          </div>
        </Table.Summary.Cell>
      ))}
    </Table.Summary.Row>
  )
}
