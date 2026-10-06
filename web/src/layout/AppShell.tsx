import { MoonOutlined, SunOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { Sumar } from '@mcc/shared'
import { api } from '../api/client'
import { T, useLang, type Lang } from '../i18n'
import { PAGINI, TOATE, cheie } from '../pagini'
import { useTema, type Tema } from '../tema'
import { num } from '../util/format'
import { Comutator } from '../components/Comutator'

/** Bara laterală, titlul paginii, comutatoarele de limbă și de temă. */
export default function AppShell() {
  const { t, lang, setLang, locale } = useLang()
  const { intunecat, setTema } = useTema()
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
          {/* limba și tema pe același rând: meniul trebuie să încapă fără derulare la 720 px */}
          <div className="comutatoare">
            <div className="limba">
              <Comutator<Lang>
                size="small"
                value={lang}
                onChange={setLang}
                options={[
                  { label: 'RO', value: 'ro' },
                  { label: 'EN', value: 'en' },
                ]}
              />
            </div>
            <div className="tema">
              {/* doar două alegeri; până la prima alegere tema urmează sistemul (src/tema), iar comutatorul arată tema efectivă */}
              <Comutator<Tema>
                size="small"
                value={intunecat ? 'intunecat' : 'luminos'}
                onChange={setTema}
                aria-label={t('comun.tema.eticheta')}
                options={[
                  { value: 'luminos', title: t('comun.tema.luminos'), label: <SunOutlined aria-label={t('comun.tema.luminos')} /> },
                  { value: 'intunecat', title: t('comun.tema.intunecat'), label: <MoonOutlined aria-label={t('comun.tema.intunecat')} /> },
                ]}
              />
            </div>
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
