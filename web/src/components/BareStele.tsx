import { Tooltip } from 'antd'
import { useLang } from '../i18n'
import { num } from '../util/format'

/** Distribuția pe stele [5★, 4★, 3★, 2★, 1★] ca bară stivuită, cu cifrele la hover. Folosită în 2.3 și în fișa băncii. */
const CULORI = ['var(--ok)', '#7fb893', 'var(--muted)', '#d9a441', 'var(--warn)']

export function BareStele({ dist, latime = 140 }: { dist: number[] | null | undefined; latime?: number }) {
  const { locale } = useLang()
  const d = (dist ?? []).map(Number)
  const tot = d.reduce((s, x) => s + x, 0)
  if (!tot) return <span className="gri">—</span>
  const titlu = d.map((x, i) => `${5 - i}★: ${num(x, locale, 0)} (${Math.round((100 * x) / tot)}%)`).join(' · ')
  return (
    <Tooltip title={titlu}>
      <span className="stele-bar" style={{ width: latime }}>
        {d.map((x, i) => (
          <span key={i} style={{ width: `${(100 * x) / tot}%`, background: CULORI[i] }} />
        ))}
      </span>
    </Tooltip>
  )
}
