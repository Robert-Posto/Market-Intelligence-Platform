import type { ReactNode } from 'react'
import { Tooltip } from 'antd'
import type { Meta } from '../api/meta'
import { useLang } from '../i18n'

/**
 * Banda din capul secțiunilor 2.4 (revamp 30.09 în aplicația veche): câteva
 * cifre mari, apoi băncile ca „chips” — clic pe o bancă = filtrul pe ea, încă
 * un clic = toate. Folosită de toate secțiunile 2.4, deci stă aici o singură dată.
 */

/** Numele scurt al băncii pe chip; numele oficial rămâne la hover și în tabele. */
const SCURT: Record<string, string> = {
  brci: 'BRCI', creditcoop: 'Creditcoop', bid: 'BID', cetelem: 'Cetelem', banorient: 'Banorient',
  citibank: 'Citibank', revolut: 'Revolut', 'bcr-locuinte': 'BCR Locuințe', bankofchina: 'Bank of China',
}
export const numeScurt = (b: string, m: Meta) =>
  SCURT[b] ?? (m.nume[b] ?? b).replace(/ — .*| – .*| N\.V\..*| S\.A\..*| EAD .*| \(.*\)$| România$/, '')

export interface Cifra {
  n: ReactNode
  eticheta: ReactNode
  titlu?: string
}

export function Banda({ cifre, chipuri, eticheta }: { cifre: Cifra[]; chipuri?: ReactNode; eticheta?: ReactNode }) {
  const { t } = useLang()
  return (
    <div className="cm-banda">
      <div className="cm-cifre">
        {cifre.map((c, i) => {
          const corp = (
            <div key={i}>
              <b>{c.n}</b>
              <span>{c.eticheta}</span>
            </div>
          )
          return c.titlu ? <Tooltip key={i} title={c.titlu}>{corp}</Tooltip> : corp
        })}
      </div>
      {chipuri && (
        <div className="cm-chipuri">
          <span className="cm-et">{eticheta ?? t('campanii.banda_eticheta_implicita')}</span>
          {chipuri}
        </div>
      )}
    </div>
  )
}

/** Un chip de bancă: Libra marcată, zero estompat, cel ales aprins; fără `onClick` e doar informativ. */
export function Chip({ slug, m, n, titlu, activ, onClick }: {
  slug: string; m: Meta; n: string; titlu: string; activ?: boolean; onClick?: () => void
}) {
  const cls = ['cm-chip', slug === 'libra' ? 'ref' : '', n === '0' ? 'zero' : '', activ ? 'activ' : ''].join(' ').trim()
  return (
    <Tooltip title={`${m.nume[slug] ?? slug} — ${titlu}`}>
      <button type="button" className={cls} onClick={onClick} disabled={!onClick}>
        {numeScurt(slug, m)}
        <b>{n}</b>
      </button>
    </Tooltip>
  )
}

/** Bara fixă a unei secțiuni 2.4: comutatorul (desenat de pagină), informația din dreapta, filtrele dedesubt. */
export function BaraSectiune({ taburi, info, filtre }: { taburi: ReactNode; info?: ReactNode; filtre?: ReactNode }) {
  return (
    <div className="bara-fixa cm-bara">
      <div className="filtre">
        {taburi}
        {info && <span className="cm-info">{info}</span>}
      </div>
      {filtre && <div className="filtre">{filtre}</div>}
    </div>
  )
}
