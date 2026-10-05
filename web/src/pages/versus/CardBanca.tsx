import { Tooltip } from 'antd'
import { Link } from 'react-router-dom'
import type { VersusExtra } from '@mcc/shared'
import type { Meta } from '../../api/meta'
import { useLang } from '../../i18n'
import { num } from '../../util/format'
import { REFERINTA } from './model'

/** Cardul de sus: identitatea băncii + cifrele care există cu adevărat pentru ea. */
export function CardBanca({ b, m, app, loc, acop }: {
  b: string
  m: Meta
  app?: VersusExtra['mobil'][number]
  loc?: VersusExtra['retea'][number]
  acop?: VersusExtra['acoperire'][number]
}) {
  const { t, locale } = useLang()
  const nume = m.nume[b] ?? b
  const volum = app?.volum ?? null
  const cifre: [string, string][] = [
    app && app.rating
      ? [`${num(app.rating, locale, 2)} ★`, volum === 1 ? t('versus.card_app_store_1', { volum: num(volum, locale, 0) }) : t('versus.card_app_store', { volum: num(volum, locale, 0) })]
      : ['—', t('versus.card_fara_app_store')],
    loc ? [num((loc.sucursale || 0) + (loc.atm || 0), locale, 0), t('versus.card_locatii')] : ['—', t('versus.card_fara_locatii')],
    [num(acop ? acop.valori : 0, locale, 0), t('versus.card_valori_colectate')],
  ]
  return (
    <div className={b === REFERINTA ? 'vs-card ref' : 'vs-card'}>
      {b === REFERINTA && <span className="vs-tag">{t('versus.card_referinta')}</span>}
      <div className="vs-logo">
        {m.logo[b] ? <img src={m.logo[b]} alt={nume} /> : <span className="vs-init">{nume.slice(0, 2).toUpperCase()}</span>}
      </div>
      <div className="vs-nume">
        <Tooltip title={t('versus.card_fisa_title')}>
          <Link className="fisa" to={`/banca?b=${encodeURIComponent(b)}`}><span className="nm">{nume}</span></Link>
        </Tooltip>
      </div>
      <div className="vs-cifre">
        {cifre.map(([v, e], i) => <div key={i}><b>{v}</b><span>{e}</span></div>)}
      </div>
    </div>
  )
}
