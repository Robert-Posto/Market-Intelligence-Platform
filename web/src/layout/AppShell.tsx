import { MoonOutlined, SunOutlined } from '@ant-design/icons'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useSesiune } from '../auth'
import { useLang, type Lang } from '../i18n'
import { PAGINI, TOATE, VOX, cheie } from '../pagini'
import { useTema, type Tema } from '../tema'
import { Comutator } from '../components/Comutator'
import { VoxInsigna } from '../components/LogoVox'
import BulaVox from './BulaVox'

/** Bara laterală, titlul paginii, comutatoarele de limbă și de temă. */
export default function AppShell() {
  const { t, lang, setLang } = useLang()
  const { intunecat, setTema } = useTema()
  const { utilizator, delogare } = useSesiune()
  const { pathname } = useLocation()
  const id = pathname.replace(/^\//, '').split('/')[0] || 'overview'
  const pagina = TOATE.find((p) => p.id === id) ?? TOATE[0]!

  // Paginile de admin nu apar în meniul analistului (serverul le refuză oricum cu 403); un grup rămas gol dispare
  const meniu = PAGINI.map((gr) => ({ ...gr, chei: gr.chei.filter((p) => !p.admin || utilizator?.rol === 'admin') })).filter((gr) => gr.chei.length)

  return (
    <div className="aplicatie">
      <nav>
        <div className="marca">
          <span className="t">
            Marketing <i>Command</i> Center
          </span>
        </div>
        <div className="meniu">
          {meniu.map((gr) => (
            <div key={gr.grup ?? gr.chei[0]!.id} className={gr.grup ? undefined : 'fara-titlu'}>
              {gr.grup && <h3>{t(gr.grup)}</h3>}
              {gr.chei.map((p) => (
                <NavLink key={p.id} to={`/${p.id}`} className={({ isActive }) => (isActive ? 'activ' : '')}>
                  {t(cheie(p.id, 'nume_meniu'))}
                  {p.pdf && <span className="pdf">{p.pdf}</span>}
                </NavLink>
              ))}
            </div>
          ))}
        </div>
        <div className="jos">
          <div className="picior">
            {/* o singură linie pentru utilizator, iar „Ieșire” / „local” pe rândul comutatoarelor: meniul trebuie să încapă fără derulare la 720 px */}
            {utilizator && !utilizator.local && (
              <div className="utilizator">
                <b>{utilizator.nume}</b> · {t(`auth.rol.${utilizator.rol}`)}
              </div>
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
              {utilizator?.local && <span className="local" title={t('auth.local_titlu')}>{t('auth.local')}</span>}
              {utilizator && !utilizator.local && (
                <button type="button" className="iesire" onClick={() => void delogare()}>{t('auth.iesire')}</button>
              )}
            </div>
          </div>
        </div>
      </nav>
      <main id="principal">
        <div className="cap">
          <h1>
            {pagina.id === VOX.id && <VoxInsigna className="titlu-logo" size={30} />}
            {t(cheie(pagina.id, 'titlu'))}
          </h1>
          <p className="lede">{t(cheie(pagina.id, 'descriere'))}</p>
        </div>
        <Outlet />
      </main>
      <BulaVox />
    </div>
  )
}
