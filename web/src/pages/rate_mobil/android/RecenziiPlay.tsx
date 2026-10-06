import { useState } from 'react'
import { Modal, Segmented } from 'antd'
import type { Meta } from '../../../api/meta'
import { useLang } from '../../../i18n'
import { recenziiPlay } from '../dateLocale'
import { CardRecenzie } from '../Recenzii'

type Filtru = 'toate' | 'negative' | 'pozitive'

/**
 * Recenziile din Google Play ale unei aplicații, în același card ca cele din App Store.
 * Sunt cele ~20 pe care Google le afișează pe pagină (cele mai relevante), acumulate între
 * rulări; nu toate recenziile aplicației (ING avea 29.738 scrise la 06.10.2026).
 */
export default function RecenziiPlay({ pachet, banca, m, onClose }: {
  pachet: string | null
  banca: string
  m: Meta
  onClose: () => void
}) {
  const { t, tn } = useLang()
  const [filtru, setFiltru] = useState<Filtru>('toate')
  const toate = pachet ? recenziiPlay(pachet) : []
  const lista = toate.filter((r) => filtru === 'toate' || (filtru === 'negative' ? r.nota <= 2 : r.nota >= 4))
  const negative = toate.filter((r) => r.nota <= 2).length
  const cuRaspuns = toate.filter((r) => r.raspuns_banca).length
  return (
    <Modal open={!!pachet} onCancel={() => { setFiltru('toate'); onClose() }} footer={null} centered width="min(980px, 94vw)" destroyOnHidden
      className="ap-grila-modal" title={<span className="sertar-titlu">{t('mobil.rec_play_titlu', { banca: m.nume[banca] ?? banca })}</span>}>
      <div className="rp-bara">
        <Segmented<Filtru> value={filtru} onChange={setFiltru} options={[
          { value: 'toate', label: `${t('mobil.toate')} (${toate.length})` },
          { value: 'negative', label: `1–2★ (${negative})` },
          { value: 'pozitive', label: `4–5★ (${toate.filter((r) => r.nota >= 4).length})` },
        ]} />
        <span className="note">{t('mobil.rec_play_raspuns', { n: cuRaspuns, total: toate.length })}</span>
      </div>
      <p className="note" style={{ margin: '0 0 12px' }}>{t('mobil.rec_play_nota')}</p>
      {lista.length
        ? lista.map((r) => (
            <CardRecenzie key={r.id} banca={banca} m={m} nota={r.nota} data={r.data} versiune={r.versiune} magazin="Google Play"
              text={r.text} raspuns={r.raspuns_banca} raspunsData={r.raspuns_data} utile={r.utile} />
          ))
        : <p className="note">{t('mobil.nicio_recenzie')}</p>}
      <span className="sub">{tn('mobil.n_recenzii_play', toate.length)}</span>
    </Modal>
  )
}
