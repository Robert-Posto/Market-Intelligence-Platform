import React, { useEffect } from 'react'
import ReactDOM from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { App as AntApp, ConfigProvider } from 'antd'
import roRO from 'antd/locale/ro_RO'
import enUS from 'antd/locale/en_US'
import dayjs from 'dayjs'
import 'dayjs/locale/ro'
/* Fonturile aplicației vechi, incluse local (fără Google Fonts). Subsetul
   latin-ext e obligatoriu: ș, ț, ă stau acolo, nu în latin — fără el, textul
   românesc ar cădea pe fontul de sistem la jumătate din litere. */
import '@fontsource/ibm-plex-sans/latin-400.css'
import '@fontsource/ibm-plex-sans/latin-ext-400.css'
import '@fontsource/ibm-plex-sans/latin-500.css'
import '@fontsource/ibm-plex-sans/latin-ext-500.css'
import '@fontsource/ibm-plex-sans/latin-600.css'
import '@fontsource/ibm-plex-sans/latin-ext-600.css'
import '@fontsource/ibm-plex-sans/latin-700.css'
import '@fontsource/ibm-plex-sans/latin-ext-700.css'
import '@fontsource/ibm-plex-mono/latin-400.css'
import '@fontsource/ibm-plex-mono/latin-ext-400.css'
import '@fontsource/ibm-plex-mono/latin-500.css'
import '@fontsource/ibm-plex-mono/latin-ext-500.css'
import '@fontsource/source-serif-4/latin-600.css'
import '@fontsource/source-serif-4/latin-ext-600.css'
import '@fontsource/source-serif-4/latin-700.css'
import '@fontsource/source-serif-4/latin-ext-700.css'
import './styles/global.css'
import './styles/auth.css'
import App from './App'
import { SesiuneProvider } from './auth'
import { LangProvider, useLang } from './i18n'
import { temaMip } from './theme'
import { TemaProvider, useTema } from './tema'

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 60_000, retry: 1, refetchOnWindowFocus: false } },
})

/** ConfigProvider stă sub LangProvider, ca limba să schimbe și textele AntD. */
function CuTema() {
  const { lang } = useLang()
  const { intunecat } = useTema()
  useEffect(() => {
    dayjs.locale(lang === 'en' ? 'en' : 'ro')
    document.documentElement.lang = lang
  }, [lang])
  return (
    <ConfigProvider locale={lang === 'en' ? enUS : roRO} theme={temaMip(intunecat)}>
      <AntApp>
        {/* fără sesiune, SesiuneProvider arată pagina de logare în loc de aplicație; hash-ul rămâne, deci după logare ne întoarcem la aceeași pagină */}
        {/* HashRouter: adresele rămân `#/produse?grup=…`, ca linkurile salvate din aplicația veche să meargă */}
        <SesiuneProvider>
          <HashRouter>
            <App />
          </HashRouter>
        </SesiuneProvider>
      </AntApp>
    </ConfigProvider>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <LangProvider>
        <TemaProvider>
          <CuTema />
        </TemaProvider>
      </LangProvider>
    </QueryClientProvider>
  </React.StrictMode>,
)
