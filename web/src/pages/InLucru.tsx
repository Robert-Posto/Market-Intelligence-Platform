import { useLocation } from 'react-router-dom'
import { useLang } from '../i18n'

/**
 * Paginile care n-au trecut încă în React se deschid în aplicația veche
 * (serverul Python, :8765), cu aceeași adresă. Textul e scris aici în ambele
 * limbi, nu în dicționar: pagina dispare când se mută ultima pagină.
 */
export default function InLucru({ id }: { id: string }) {
  const { lang } = useLang()
  const { search } = useLocation()
  const veche = `http://localhost:8765/#/${id}${search}`
  return (
    <section>
      <p className="note" style={{ margin: 0 }}>
        {lang === 'en'
          ? 'This page has not been moved to the new interface yet. Until it is, it opens in the old application: '
          : 'Pagina nu e încă mutată în interfața nouă. Până atunci se deschide în aplicația veche: '}
        <a href={veche}>{veche}</a>
      </p>
    </section>
  )
}
