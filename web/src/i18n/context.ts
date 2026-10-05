import { createContext } from 'react'
import type { LangState } from '.'

/**
 * Contextul de limbă stă separat de dicționar. Când se modifică un fișier din
 * dict/ în dezvoltare, Vite reevaluează i18n/index.tsx; dacă și contextul s-ar
 * crea acolo, paginile reîncărcate ar căuta alt context decât cel al
 * providerului deja montat, iar useLang() ar întoarce null (pagina cădea).
 */
export const LangContext = createContext<LangState>(null as never)
