import { Button } from 'antd'
import { useLang } from '../i18n'
import { num } from '../util/format'

/**
 * Paginarea din aplicația veche: „1–100 din 16.765”, butoanele din jurul paginii
 * curente plus prima și ultima, „…” între ele. Schimbă doar `offset`; cererea
 * nouă o face pagina.
 */
export function Paginare({ total, offset, limit, onChange }: {
  total: number; offset: number; limit: number; onChange: (offset: number) => void
}) {
  const { t, locale } = useLang()
  const n = Math.ceil(total / limit)
  if (n <= 1) return null
  const cur = Math.floor(offset / limit)
  const idx = [...new Set([0, cur - 2, cur - 1, cur, cur + 1, cur + 2, n - 1])].filter((k) => k >= 0 && k < n).sort((a, b) => a - b)
  const out: JSX.Element[] = []
  let prev = -1
  for (const k of idx) {
    if (k - prev > 1) out.push(<span key={`g${k}`}>…</span>)
    out.push(
      <Button key={k} size="small" type={k === cur ? 'primary' : 'default'} onClick={() => onChange(k * limit)}>
        {k + 1}
      </Button>,
    )
    prev = k
  }
  return (
    <div className="pagini">
      <span>
        {t('comun.paginare.interval', {
          de_la: num(offset + 1, locale, 0),
          pana_la: num(Math.min(offset + limit, total), locale, 0),
          total: num(total, locale, 0),
        })}
      </span>
      {cur > 0 && <Button size="small" onClick={() => onChange((cur - 1) * limit)}>{t('comun.paginare.inapoi')}</Button>}
      {out}
      {cur < n - 1 && <Button size="small" onClick={() => onChange((cur + 1) * limit)}>{t('comun.paginare.inainte')}</Button>}
    </div>
  )
}
