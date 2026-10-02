import { createContext, Fragment, useContext, useMemo, useState, type ReactNode } from 'react'
import { DICT } from './dict'

/**
 * Română și engleză, cu dicționar propriu, ca în SCC: fiecare cheie are
 * [ro, en]. Limba se ține minte în browser; implicit e română.
 *
 * Datele băncilor (denumirile serviciilor din PDF-uri, titlurile campaniilor,
 * recenziile, citatele) NU trec pe aici și rămân în română: sunt dovezi, iar un
 * citat tradus nu mai e cel din document.
 */
export type Lang = 'ro' | 'en'
export type DictKey = keyof typeof DICT
export type Params = Record<string, string | number>

const CHEIE_LIMBA = 'mcc-lang'

function citesteLimba(): Lang {
  try {
    return localStorage.getItem(CHEIE_LIMBA) === 'en' ? 'en' : 'ro'
  } catch {
    return 'ro'
  }
}

function inlocuieste(text: string, params?: Params): string {
  if (!params) return text
  return text.replace(/\{([a-zA-Z0-9_]+)\}/g, (m, k: string) => (k in params ? String(params[k]) : m))
}

interface LangState {
  lang: Lang
  setLang: (l: Lang) => void
  /** textul simplu, cu parametrii puși în locul lui {nume} */
  t: (key: DictKey, params?: Params) => string
  /** singular sau plural, după n: cheia `<baza>_1` sau `<baza>_n` */
  tn: (baza: string, n: number, params?: Params) => string
  /** locale-ul pentru Intl: numere, date, sortare */
  locale: string
}

const LangContext = createContext<LangState>(null as never)

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(citesteLimba)
  const value = useMemo<LangState>(() => {
    const i = lang === 'en' ? 1 : 0
    const t = (key: DictKey, params?: Params) => {
      const intrare = DICT[key] as readonly [string, string] | undefined
      if (!intrare) {
        if (import.meta.env.DEV) console.warn(`[i18n] cheie lipsă: ${key}`)
        return key
      }
      return inlocuieste(intrare[i], params)
    }
    return {
      lang,
      locale: lang === 'en' ? 'en-GB' : 'ro-RO',
      setLang: (l) => {
        try {
          localStorage.setItem(CHEIE_LIMBA, l)
        } catch {
          /* fără stocare: limba rămâne doar pe sesiune */
        }
        document.documentElement.lang = l
        setLangState(l)
      },
      t,
      tn: (baza, n, params) => t(`${baza}_${n === 1 ? '1' : 'n'}` as DictKey, { n, ...params }),
    }
  }, [lang])
  return <LangContext.Provider value={value}>{children}</LangContext.Provider>
}

export function useLang(): LangState {
  return useContext(LangContext)
}

/**
 * Text cu marcaj simplu (<b>, <i>, <br>, <a href>, <span class>, <mark>, <small>, <code>),
 * transformat în elemente React. Parametrii intră ca text, deci nu pot aduce
 * marcaj: un nume de bancă sau un citat nu se interpretează niciodată ca HTML.
 */
const RE_TAG = /<(\/?)(b|i|br|a|span|mark|small|code)((?:\s+[a-z-]+="[^"]*")*)\s*\/?>/g

export function T({ k, params }: { k: DictKey; params?: Record<string, ReactNode> }) {
  const { lang } = useLang()
  const intrare = DICT[k] as readonly [string, string] | undefined
  const text = intrare ? intrare[lang === 'en' ? 1 : 0] : k
  return <>{randeaza(text, params)}</>
}

function atribute(s: string): Record<string, string> {
  const out: Record<string, string> = {}
  for (const m of s.matchAll(/([a-z-]+)="([^"]*)"/g)) out[m[1]!] = m[2]!
  return out
}

function cuParametri(text: string, params: Record<string, ReactNode> | undefined, cheie: string): ReactNode[] {
  const out: ReactNode[] = []
  let ultim = 0
  for (const m of text.matchAll(/\{([a-zA-Z0-9_]+)\}/g)) {
    out.push(text.slice(ultim, m.index))
    const v = params?.[m[1]!]
    out.push(<Fragment key={`${cheie}-${m.index}`}>{v ?? m[0]}</Fragment>)
    ultim = m.index! + m[0].length
  }
  out.push(text.slice(ultim))
  return out
}

interface Nod {
  tag: string
  attrs: Record<string, string>
  copii: ReactNode[]
}

function randeaza(text: string, params?: Record<string, ReactNode>): ReactNode[] {
  const radacina: Nod = { tag: '', attrs: {}, copii: [] }
  const stiva: Nod[] = [radacina]
  let ultim = 0
  let n = 0
  for (const m of text.matchAll(RE_TAG)) {
    stiva[stiva.length - 1]!.copii.push(...cuParametri(text.slice(ultim, m.index), params, `t${n++}`))
    ultim = m.index! + m[0].length
    const [, inchide, tag] = m
    if (tag === 'br') {
      stiva[stiva.length - 1]!.copii.push(<br key={`br${n++}`} />)
    } else if (inchide) {
      const nod = stiva.length > 1 ? stiva.pop()! : null
      if (nod) stiva[stiva.length - 1]!.copii.push(element(nod, `e${n++}`))
    } else {
      stiva.push({ tag: tag!, attrs: atribute(m[3] ?? ''), copii: [] })
    }
  }
  stiva[stiva.length - 1]!.copii.push(...cuParametri(text.slice(ultim), params, `t${n++}`))
  while (stiva.length > 1) {
    const nod = stiva.pop()!
    stiva[stiva.length - 1]!.copii.push(element(nod, `e${n++}`))
  }
  return radacina.copii
}

function element(nod: Nod, key: string): ReactNode {
  const { tag, attrs, copii } = nod
  if (tag === 'a') return <a key={key} href={attrs.href}>{copii}</a>
  if (tag === 'span') return <span key={key} className={attrs.class}>{copii}</span>
  if (tag === 'b') return <b key={key}>{copii}</b>
  if (tag === 'i') return <i key={key}>{copii}</i>
  if (tag === 'small') return <small key={key}>{copii}</small>
  if (tag === 'code') return <code key={key}>{copii}</code>
  return <mark key={key}>{copii}</mark>
}
