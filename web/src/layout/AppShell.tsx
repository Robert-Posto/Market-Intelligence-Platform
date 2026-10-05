import { useQuery } from '@tanstack/react-query'
import { Segmented } from 'antd'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { Sumar } from '@mcc/shared'
import { api } from '../api/client'
import { T, useLang, type Lang } from '../i18n'
import { PAGINI, TOATE, cheie } from '../pagini'
import { num } from '../util/format'

/** Bara laterală, titlul paginii și comutatorul de limbă. */
export default function AppShell() {
  const { t, lang, setLang, locale } = useLang()
  const { pathname } = useLocation()
  const id = pathname.replace(/^\//, '').split('/')[0] || 'overview'
  const pagina = TOATE.find((p) => p.id === id) ?? TOATE[0]!

  // Piciorul barei spune cât e în bază, nu un slogan. Se cere o dată pe sesiune.
  const sumar = useQuery({ queryKey: ['sumar'], staleTime: Infinity, queryFn: () => api('/api/sumar', Sumar) })
  const g = (c: string) => sumar.data?.totaluri.find((x) => x.ce === c)?.n ?? 0

  return (
    <div className="aplicatie">
      <nav>
        <div className="marca">
          <span className="t">
            Marketing <i>Command</i> Center
          </span>
          <span className="s">{t('comun.nav.subtitlu')}</span>
        </div>
        <div className="meniu">
          {PAGINI.map((gr) => (
            <div key={gr.grup}>
              <h3>{t(gr.grup)}</h3>
              {gr.chei.map((p) => (
                <NavLink key={p.id} to={`/${p.id}`} className={({ isActive }) => (isActive ? 'activ' : '')}>
                  {t(cheie(p.id, 'nume_meniu'))}
                  {p.pdf && <span className="pdf">{p.pdf}</span>}
                </NavLink>
              ))}
            </div>
          ))}
        </div>
        <div className="picior">
          {sumar.data && (
            <T
              k="comun.picior.sumar"
              params={{ banci: num(g('bănci'), locale, 0), surse: num(g('surse'), locale, 0), valori: num(g('observații'), locale, 0) }}
            />
          )}
          <div className="limba">
            <Segmented<Lang>
              size="small"
              value={lang}
              onChange={setLang}
              options={[
                { label: 'RO', value: 'ro' },
                { label: 'EN', value: 'en' },
              ]}
            />
          </div>
        </div>
      </nav>
      <main id="principal">
        <div className="cap">
          <h1>{t(cheie(pagina.id, 'titlu'))}</h1>
          <p className="lede">{t(cheie(pagina.id, 'descriere'))}</p>
        </div>
        <Outlet />
      </main>
    </div>
  )
}
