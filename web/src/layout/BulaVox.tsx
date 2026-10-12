import { FloatButton, Tooltip } from 'antd'
import { useLocation } from 'react-router-dom'
import { useLang } from '../i18n'
import { VOX } from '../pagini'
import { VoxBula } from '../components/LogoVox'

/**
 * Intrarea în Vox de pe orice pagină (decizia lui Nicolae, 09.10.2026): o bulă în dreapta jos, ca widgetul de chat de
 * pe reginamaria.ro, în locul butonului din bara laterală. Doar duce pe `#/vox`; acolo nu apare, ar trimite pe pagina
 * pe care ești deja. Textul se vede doar la hover sau la focus: mereu vizibil, ar acoperi mai mult din pagini.
 * Tooltip-ul e al nostru, nu proprietatea `tooltip` a lui FloatButton: antd 5.29 îl pune în jurul `div`-ului interior,
 * nu al linkului care primește focusul, iar textul nu apărea la Tab (verificarea Playwright, 09.10.2026).
 * `zIndex` explicit: sub un Tooltip, antd urcă bula la 1200, deasupra sertarelor (Drawer, 1000); bula trebuie să stea sub
 * ele și sub ferestrele modale.
 */
export default function BulaVox() {
  const { t } = useLang()
  const { pathname } = useLocation()
  if (pathname === `/${VOX.id}`) return null
  const text = t('vox.nav.buton')
  return (
    <Tooltip title={text} placement="left" trigger={['hover', 'focus']}>
      <FloatButton
        className="vox-lansator"
        type="primary"
        shape="circle"
        href={`#/${VOX.id}`}
        icon={<VoxBula size={28} />}
        aria-label={text}
        style={{ zIndex: 900 }}
      />
    </Tooltip>
  )
}
