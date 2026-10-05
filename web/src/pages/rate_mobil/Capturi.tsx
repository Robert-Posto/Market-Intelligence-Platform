import { Button, Drawer } from 'antd'
import type { Meta } from '../../api/meta'
import { useLang } from '../../i18n'

/**
 * Capturile din App Store ale unei bănci, în același sertar ca dovezile din 2.1
 * și 2.2 (`deschideSertarHtml` din aplicația veche). Imaginile sunt ale băncii,
 * de pe serverul Apple: ce alege să arate primul spune ce consideră diferențiator.
 */
export default function Capturi({ banca, urls, m, onClose }: {
  banca: string | null
  urls: string[]
  m: Meta
  onClose: () => void
}) {
  const { t } = useLang()
  const titlu = banca ? t('mobil.capturi_titlu', { banca: m.nume[banca] ?? banca }) : ''
  return (
    <Drawer open={!!banca} onClose={onClose} width="min(880px, 94vw)" title={<span className="sertar-titlu">{titlu}</span>} closeIcon={null}
      extra={<Button onClick={onClose}>{t('sertar.inchide')}</Button>} destroyOnClose>
      <p className="note" style={{ margin: '0 0 14px' }}>{t('mobil.capturi_sub')}</p>
      <div className="mb-capturi">
        {urls.map((u, i) => (
          <a key={u} href={u} target="_blank" rel="noopener" title={t('mobil.deschide_marit')}>
            <img src={u} alt={t('mobil.captura_alt', { i: i + 1 })} />
          </a>
        ))}
      </div>
    </Drawer>
  )
}
