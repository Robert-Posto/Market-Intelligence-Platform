import { useEffect, useRef, useState, type PointerEvent } from 'react'
import { Segmented, type SegmentedProps } from 'antd'
import { ALUNECARE_COMUTATOR_MS } from '../theme'

type Valoare = string | number

/**
 * `Segmented` din AntD, cu două diferențe, ca alunecarea să pornească din clipa apăsării:
 * - opțiunea se schimbă la apăsare (`pointerdown`), nu la ridicarea butonului: cu o apăsare de 100 ms,
 *   AntD pornea alunecarea la ~150 ms (măsurat 06.10.2026). Pe ecran tactil rămâne la ridicare,
 *   altfel un deget pus pe comutator ca să derulezi pagina ar schimba opțiunea;
 * - opțiunea aleasă se ține și local, până o confirmă părintele. Valoarea vine des din adresă, pe care
 *   React Router 7 o schimbă într-o tranziție: pe o pagină grea, butonul aștepta desenarea ei
 *   (2.4, Reclame Google: ~290 ms).
 * Tastatura merge ca înainte, prin `onChange`.
 *
 * `dupaAlunecare`: părintele află abia după alunecare. Pentru comutatoarele care desenează o pagină grea:
 * la 2.4, desenarea secțiunii noi oprea alunecarea pe loc (Reclame Bing: 14 cadre din 18, un blocaj de
 * 67–83 ms). Prețul: pagina nouă vine cu ~170 ms mai târziu.
 */
export function Comutator<T extends Valoare>({ dupaAlunecare, ...props }: SegmentedProps<T> & { dupaAlunecare?: boolean }) {
  const { value, onChange, options, disabled } = props
  const [ales, setAles] = useState(value)
  useEffect(() => setAles(value), [value])
  // două apăsări rapide: părintele primește doar ultima alegere, nu și pe cea dintre ele
  const ultima = useRef(value)
  const anunta = (v: T) => { if (ultima.current === v) onChange?.(v) }

  const alege = (v: T) => {
    if (v === ales) return
    setAles(v)
    ultima.current = v
    if (dupaAlunecare) {
      // ~40 ms până pornește alunecarea (două cadre), plus alunecarea însăși
      setTimeout(() => anunta(v), ALUNECARE_COMUTATOR_MS + 40)
    } else {
      // Cu părintele anunțat imediat, desenarea lui pornea înaintea alunecării: la 2.4, alunecarea pornea la
      // 130 ms. Două cadre de răgaz (~33 ms) lasă alunecarea să pornească prima.
      requestAnimationFrame(() => requestAnimationFrame(() => anunta(v)))
    }
  }

  const laApasare = (e: PointerEvent<HTMLDivElement>) => {
    if (disabled || e.pointerType === 'touch' || e.button !== 0) return
    const item = (e.target as HTMLElement).closest('.ant-segmented-item')
    if (!item?.parentElement) return
    const iteme = [...item.parentElement.children].filter((c) => c.classList.contains('ant-segmented-item'))
    const optiune = options[iteme.indexOf(item)]
    if (optiune === undefined) return
    if (typeof optiune === 'object') {
      if (!optiune.disabled) alege(optiune.value)
    } else alege(optiune)
  }

  return <Segmented<T> {...props} value={ales} onChange={alege} onPointerDown={laApasare} />
}
