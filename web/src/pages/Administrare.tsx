import { Tabs } from 'antd'
import { useSearchParams } from 'react-router-dom'
import { useLang } from '../i18n'
import Utilizatori from './administrare/Utilizatori'

/**
 * Administrare: setările aplicației, câte una pe tab (doar admin; serverul răspunde 403 analistului).
 * Tab-ul ales stă în adresă (`?tab=`), ca o vedere să se poată trimite; un tab nou = o intrare în TABURI.
 */
const TABURI = ['utilizatori'] as const
type Tab = (typeof TABURI)[number]

export default function Administrare() {
  const { t } = useLang()
  const [sp, setSp] = useSearchParams()
  const tab: Tab = TABURI.find((x) => x === sp.get('tab')) ?? 'utilizatori'

  return (
    <Tabs
      activeKey={tab}
      // la schimbarea tab-ului filtrele celui vechi nu au sens în cel nou: rămâne doar `tab`
      onChange={(k) => setSp(new URLSearchParams({ tab: k }), { replace: true })}
      items={[{ key: 'utilizatori', label: t('adm.tab.utilizatori'), children: <Utilizatori /> }]}
    />
  )
}
