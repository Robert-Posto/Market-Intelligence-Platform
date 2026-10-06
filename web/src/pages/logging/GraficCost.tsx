import { useEffect, useRef, useState } from 'react'
import type { CostZi, TipJob } from '@mcc/shared'
import { useLang } from '../../i18n'
import { numeTip, usd, ziLunga, ziScurta } from './format'

/**
 * Costul pe zi, stivuit pe tipul jobului. SVG desenat aici, nu o bibliotecă de
 * grafice: stack-ul SCC nu are una, iar o bară stivuită pe o singură axă nu o cere.
 *
 * Culoarea urmează tipul (ordinea din job_types), nu poziția lui în filtru: un
 * filtru nu recolorează graficul. Paleta e validată pe ambele suprafețe MIP
 * (validate_palette.js, 05.10.2026): CVD ΔE 9,2 pe luminos, 9,4 pe întunecat;
 * verdele are 2,77:1 pe fildeș, deci vederea de tabel rămâne la un clic.
 */
const INALTIME = 260
const M = { sus: 12, dreapta: 8, jos: 24, stanga: 56 }
const LATIME_MAX_BARA = 28
/** Fâșia de suprafață dintre două segmente: fără ea, două tipuri alăturate se citesc ca o singură bară. */
const SPATIU = 2

export const culoareTip = (tipuri: TipJob[], cod: string) => {
  const i = tipuri.findIndex((t) => t.cod === cod)
  return i >= 0 && i < 3 ? `var(--lg-${i + 1})` : 'var(--muted)'
}

/** Trepte rotunde pe axa Y (1 / 2 / 5 × 10ⁿ), de la zero: un cost nu are alt început firesc. */
function trepte(max: number): number[] {
  if (max <= 0) return [0, 1]
  const brut = max / 4
  const mag = Math.pow(10, Math.floor(Math.log10(brut)))
  const n = brut / mag
  const pas = (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * mag
  const out: number[] = []
  for (let v = 0; v <= Math.ceil(max / pas) * pas + pas / 1000; v += pas) out.push(Number(v.toFixed(6)))
  return out
}

/** Calea unui segment; doar cel de sus își rotunjește colțurile de sus. */
function segment(x: number, y: number, w: number, h: number, rotunjit: boolean): string {
  const r = rotunjit ? Math.min(4, w / 2, h) : 0
  if (!r) return `M${x},${y}h${w}v${h}h${-w}Z`
  return `M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h}Z`
}

function useLatime<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const [w, setW] = useState(0)
  useEffect(() => {
    if (!ref.current) return
    const o = new ResizeObserver(([e]) => setW(Math.floor(e!.contentRect.width)))
    o.observe(ref.current)
    return () => o.disconnect()
  }, [])
  return [ref, w] as const
}

/** `tipuri`: toate, în ordinea din job_types (dau culoarea); `afisate`: cele cu cost în perioadă (intră în stivă). */
export function GraficCost({ zile, tipuri, afisate }: { zile: CostZi[]; tipuri: TipJob[]; afisate: TipJob[] }) {
  const { t, tn, locale } = useLang()
  const [ref, latime] = useLatime<HTMLDivElement>()
  const [ales, setAles] = useState<number | null>(null)

  const total = zile.reduce((s, z) => s + z.total, 0)
  const ticks = trepte(Math.max(0, ...zile.map((z) => z.total)))
  const sus = ticks[ticks.length - 1]!
  const lp = Math.max(0, latime - M.stanga - M.dreapta)
  const hp = INALTIME - M.sus - M.jos
  const banda = zile.length ? lp / zile.length : 0
  const lb = Math.max(2, Math.min(LATIME_MAX_BARA, banda * 0.72))
  const y = (v: number) => M.sus + hp - (v / sus) * hp
  // o etichetă la ~48 px; ultima zi are mereu etichetă: e „azi”
  const fiecare = Math.max(1, Math.ceil(zile.length / Math.max(1, Math.floor(lp / 48))))
  const z = ales !== null ? zile[ales] : undefined
  // tooltip-ul stă lângă coloană, nu peste ea: centrat, acoperea chiar barele zilelor vecine
  const xc = ales !== null ? M.stanga + (ales + 0.5) * banda : 0
  const spreStanga = xc > latime / 2

  return (
    <div className="lg-grafic" ref={ref} onMouseLeave={() => setAles(null)}>
      {latime > 0 && (
        <svg width={latime} height={INALTIME} role="img" aria-label={t('lg.cost.aria', { total: usd(total, locale) })}>
          {ticks.map((v) => (
            <g key={v}>
              <line x1={M.stanga} x2={latime - M.dreapta} y1={y(v)} y2={y(v)} className="lg-grila" />
              <text x={M.stanga - 8} y={y(v)} dy="0.32em" textAnchor="end" className="lg-axa">
                {usd(v, locale, sus < 10 && v % 1 ? 2 : 0)}
              </text>
            </g>
          ))}
          {zile.map((zi, i) => {
            const x0 = M.stanga + i * banda
            const xb = x0 + (banda - lb) / 2
            const cu = afisate.filter((tp) => (zi.costuri[tp.cod] ?? 0) > 0)
            let baza = 0
            return (
              <g key={zi.zi}>
                {ales === i && <rect x={x0} y={M.sus} width={banda} height={hp} className="lg-coloana" />}
                {cu.map((tp, k) => {
                  const v = zi.costuri[tp.cod]!
                  const yt = y(baza + v)
                  const h = y(baza) - yt - (k > 0 ? SPATIU : 0)
                  baza += v
                  if (h <= 0) return null
                  return <path key={tp.cod} d={segment(xb, yt, lb, h, k === cu.length - 1)} fill={culoareTip(tipuri, tp.cod)} />
                })}
                {(zile.length - 1 - i) % fiecare === 0 && (
                  <text x={x0 + banda / 2} y={INALTIME - 6} textAnchor="middle" className="lg-axa">
                    {ziScurta(zi.zi)}
                  </text>
                )}
                {/* ținta de hover e toată coloana, nu bara: o zi ieftină are o bară de 2 px */}
                <rect x={x0} y={M.sus} width={banda} height={hp} fill="transparent" onMouseEnter={() => setAles(i)} />
              </g>
            )
          })}
          <line x1={M.stanga} x2={latime - M.dreapta} y1={y(0)} y2={y(0)} className="lg-baza" />
        </svg>
      )}
      {z && ales !== null && (
        <div
          className={`lg-tip${spreStanga ? ' stanga' : ''}`}
          style={{ left: spreStanga ? xc - banda / 2 - 8 : xc + banda / 2 + 8 }}
        >
          <div className="lg-tip-zi">
            {ziLunga(z.zi, locale)} · {tn('lg.cost.joburi', z.joburi)}
          </div>
          {/* doar tipurile care au rulat în ziua aceea, în ordinea stivei, de sus în jos */}
          {[...afisate].reverse().filter((tp) => (z.costuri[tp.cod] ?? 0) > 0).map((tp) => (
            <div key={tp.cod} className="lg-tip-rand">
              <span className="lg-cheie" style={{ background: culoareTip(tipuri, tp.cod) }} />
              <span className="v">{usd(z.costuri[tp.cod]!, locale)}</span>
              <span className="n">{numeTip(t, tp.cod, tp.denumire)}</span>
            </div>
          ))}
          {afisate.filter((tp) => (z.costuri[tp.cod] ?? 0) > 0).length > 1 && (
            <div className="lg-tip-rand lg-tip-total">
              <span />
              <span className="v">{usd(z.total, locale)}</span>
              <span className="n">{t('lg.cost.total')}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
