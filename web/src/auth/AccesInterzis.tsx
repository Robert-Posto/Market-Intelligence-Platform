import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useLang } from '../i18n'
import { useRol } from '.'

/** Paginile de administrare: analistul vede „Acces interzis”; serverul răspunde oricum 403 pe rutele lor. */
export function DoarAdmin({ children }: { children: ReactNode }) {
  return useRol() === 'admin' ? <>{children}</> : <AccesInterzis />
}

export default function AccesInterzis() {
  const { t } = useLang()
  return (
    <section className="acces-interzis" role="alert">
      <h2>{t('auth.interzis_titlu')}</h2>
      <p className="note">{t('auth.interzis_text')}</p>
      <Link className="sursa" to="/overview">{t('auth.interzis_inapoi')}</Link>
    </section>
  )
}
