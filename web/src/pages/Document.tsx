import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Button, ConfigProvider, type ThemeConfig } from 'antd'
import { useSearchParams } from 'react-router-dom'
import type { PDFDocumentProxy } from 'pdfjs-dist'
import { T, useLang } from '../i18n'
import { incarcaDocument, randeazaPagina } from './document/pdf'
import '../styles/document.css'

/*
 * Vizualizator propriu de PDF: dovada din spatele unei cifre, documentul
 * băncii deschis la pagina exactă, cu citatul evidențiat.
 *
 * De ce există: parametrii de deschidere ai Adobe (`#page=`, `search=`) sunt
 * implementați de plugin-ul clasic Acrobat, care nu mai există în Chrome.
 * Extensia Adobe pentru Chrome își încarcă PDF-ul în pagina ei și pierde
 * fragmentul din URL, deci nici nu sare la pagină, nici nu evidențiază.
 * Chrome cu vizualizatorul propriu sare la pagină dar ignoră `search=`.
 * Singurul mod în care ruta la locul exact funcționează la toată lumea e să
 * randăm noi documentul — atunci pagina și evidențierea nu mai depind de ce
 * are instalat cititorul.
 *
 * Adresa e cea din `linkDocument` (components/Dovezi.tsx), ca `/pdf.html?u=&p=&q=`
 * din aplicația veche: `#/document?u=<url>&p=<pagina>&q=<citat>`.
 */
export default function Document() {
  const [sp] = useSearchParams()
  const url = sp.get('u') || ''
  const pagina = Math.max(1, parseInt(sp.get('p') || '1', 10) || 1)
  const citat = (sp.get('q') || '').trim()
  // altă adresă = alt document: totul se ia de la capăt, ca la o încărcare de pagină
  return <Vizualizator key={`${url}\n${pagina}\n${citat}`} url={url} pagina={pagina} citat={citat} />
}

/* Butoanele din antet stau pe vișiniul barei laterale: transparente, cu text
   deschis, ca în pdf.html. */
const NAV_INK = '#f6ece6'
const TEMA_ANTET: ThemeConfig = {
  components: {
    Button: {
      defaultBg: 'transparent',
      defaultColor: NAV_INK,
      defaultBorderColor: 'rgba(246, 236, 230, .28)',
      defaultHoverBg: 'rgba(246, 236, 230, .10)',
      defaultHoverColor: NAV_INK,
      defaultHoverBorderColor: 'rgba(246, 236, 230, .45)',
      defaultActiveBg: 'rgba(246, 236, 230, .16)',
      defaultActiveColor: NAV_INK,
      defaultActiveBorderColor: 'rgba(246, 236, 230, .45)',
      defaultShadow: 'none',
      colorBgContainerDisabled: 'transparent',
      colorTextDisabled: 'rgba(246, 236, 230, .45)',
      borderColorDisabled: 'rgba(246, 236, 230, .18)',
    },
  },
}

/** Ce s-a randat ultima dată; etichetele din bară se schimbă abia după randare, ca în pdf.html. */
type Rezultat = { fel: 'pagina'; nr: number; gasite: number } | { fel: 'toate'; cu: number[] }

function Vizualizator({ url, pagina: paginaCeruta, citat }: { url: string; pagina: number; citat: string }) {
  const { t, tn } = useLang()
  const [doc, setDoc] = useState<PDFDocumentProxy | null>(null)
  const [eroare, setEroare] = useState<string | null>(null)
  const [pagina, setPagina] = useState(paginaCeruta)
  const [toate, setToate] = useState(false)
  const [rezultat, setRezultat] = useState<Rezultat | null>(null)
  const [copiat, setCopiat] = useState(false)
  const zona = useRef<HTMLDivElement>(null)
  const foi = useRef<HTMLDivElement>(null)
  const ceas = useRef<number>()

  const total = doc?.numPages ?? 0
  /* Doar http(s): `u` vine din adresă, iar un `javascript:` pus acolo ar rula
     în aplicație la clic pe „Deschide originalul”. */
  const original = /^https?:\/\//i.test(url) ? url : undefined

  useEffect(() => {
    const vechi = document.title
    document.title = t('pdf.titlu_pagina')
    return () => {
      document.title = vechi
    }
  }, [t])

  useEffect(() => () => window.clearTimeout(ceas.current), [])

  useEffect(() => {
    if (!url) return
    let anulat = false
    const sarcina = incarcaDocument(url)
    sarcina.promise.then(
      (d) => {
        if (anulat) return
        // o pagină peste numărul de pagini (documentul s-a scurtat) se oprește la ultima
        setPagina((p) => Math.min(Math.max(1, p), d.numPages))
        setDoc(d)
      },
      (e: unknown) => {
        if (!anulat) setEroare(mesajEroare(e))
      },
    )
    return () => {
      anulat = true
      void sarcina.destroy()
    }
  }, [url])

  useEffect(() => {
    const cutie = foi.current
    if (!doc || !cutie) return
    let viu = true
    const eViu = () => viu
    cutie.replaceChildren()
    const latime = Math.min((zona.current?.clientWidth ?? 1020) - 40, 980)
    const ruleaza = async () => {
      if (!toate) {
        const n = await randeazaPagina(doc, pagina, cutie, citat, latime, eViu)
        if (n === null || !viu) return
        setRezultat({ fel: 'pagina', nr: pagina, gasite: n })
        /* La 1440×900 se văd 803 px dintr-o pagină A4 de 1.386 px: în pdf.html,
           „Lunar: 20 Lei, în echivalent” (BCR, cont în valută) începe la 760 px în
           foaie și ieșea tăiat de marginea de jos; un citat mai jos nu se vedea deloc. */
        cutie.querySelector('.doc-marcaj')?.scrollIntoView({ block: 'center' })
        return
      }
      const cu: number[] = []
      for (let i = 1; i <= doc.numPages; i++) {
        const n = await randeazaPagina(doc, i, cutie, citat, latime, eViu)
        if (n === null || !viu) return
        if (n) cu.push(i)
      }
      setRezultat({ fel: 'toate', cu })
    }
    ruleaza().catch((e: unknown) => {
      if (viu) setEroare(mesajEroare(e))
    })
    return () => {
      viu = false
    }
  }, [doc, pagina, toate, citat])

  const mergiLa = (nr: number) => {
    if (!doc) return
    setToate(false)
    setPagina(Math.min(Math.max(1, nr), doc.numPages))
  }

  useEffect(() => {
    if (!doc || toate) return
    const f = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') mergiLa(pagina - 1)
      if (e.key === 'ArrowRight') mergiLa(pagina + 1)
    }
    window.addEventListener('keydown', f)
    return () => window.removeEventListener('keydown', f)
  })

  const copiaza = () => {
    navigator.clipboard.writeText(citat).then(
      () => {
        setCopiat(true)
        window.clearTimeout(ceas.current)
        ceas.current = window.setTimeout(() => setCopiat(false), 1600)
      },
      () => {},
    )
  }

  const b = <b>{citat}</b>
  let mesaj: ReactNode
  if (rezultat?.fel === 'toate') {
    if (!citat) mesaj = total === 1 ? t('pdf.citat.total_pagini_1') : t('pdf.citat.total_pagini', { total })
    else if (rezultat.cu.length) mesaj = tn('pdf.citat.apare_pe', rezultat.cu.length, { pagini: rezultat.cu.join(', ') })
    else mesaj = <T k={total === 1 ? 'pdf.citat.negasit_in_document_1' : 'pdf.citat.negasit_in_document'} params={{ citat: b, total }} />
  } else if (!citat) {
    mesaj = t('pdf.citat.fara_citat')
  } else if (rezultat) {
    mesaj = rezultat.gasite ? (
      <T k="pdf.citat.evidentiat" params={{ pagina: rezultat.nr, citat: b }} />
    ) : (
      <T k="pdf.citat.negasit_pe_pagina" params={{ pagina: rezultat.nr, citat: b }} />
    )
  } else {
    mesaj = <T k="pdf.citat.se_cauta" params={{ citat: b }} />
  }

  const eticheta = !rezultat
    ? '—'
    : rezultat.fel === 'toate'
      ? total === 1
        ? t('pdf.nav.singura_pagina')
        : t('pdf.nav.toate_n_paginile', { total })
      : t('pdf.nav.pagina_din', { pagina: rezultat.nr, total })

  let stare: ReactNode = null
  if (!url) {
    stare = <T k="pdf.stare.lipseste_documentul" />
  } else if (eroare !== null) {
    const link = (
      <a href={original} target="_blank" rel="noopener">
        {t('pdf.stare.eroare_link_original')}
      </a>
    )
    stare = (
      <>
        <b>{t('pdf.stare.eroare_titlu')}</b>
        {eroare}
        <br />
        <br />
        {citat ? (
          <T k="pdf.stare.eroare_manual" params={{ link, citat: b, pagina: paginaCeruta }} />
        ) : (
          <T k="pdf.stare.eroare_manual_fara_citat" params={{ link, pagina: paginaCeruta }} />
        )}
      </>
    )
  } else if (!doc) {
    stare = t('pdf.stare.se_incarca_documentul')
  }

  return (
    <div className="doc-pagina">
      <header className="doc-antet">
        <h1>
          Marketing <i>Command</i> Center
        </h1>
        <div className="sp" />
        <ConfigProvider theme={TEMA_ANTET}>
          <Button href={original} target="_blank" rel="noopener" disabled={!original}>
            {t('pdf.antet.deschide_original')}
          </Button>
          <Button onClick={copiaza} disabled={!citat}>
            {copiat ? t('pdf.antet.copiat') : t('pdf.antet.copiaza_citatul')}
          </Button>
        </ConfigProvider>
      </header>
      <div className="doc-bara">
        <div className="cit">{mesaj}</div>
        <div className="nav">
          <Button size="small" onClick={() => mergiLa(pagina - 1)} disabled={!doc || pagina <= 1}>
            {t('pdf.nav.anterioara')}
          </Button>
          <span className="pg">{eticheta}</span>
          <Button size="small" onClick={() => mergiLa(pagina + 1)} disabled={!doc || pagina >= total}>
            {t('pdf.nav.urmatoarea')}
          </Button>
          <Button size="small" onClick={() => setToate(true)} disabled={!doc}>
            {t('pdf.nav.toate_paginile')}
          </Button>
        </div>
      </div>
      <div className="doc-zona" ref={zona}>
        {stare !== null && <div className="doc-stare">{stare}</div>}
        {/* foile le pune PDF.js (pânză + strat de text); React nu randează nimic aici */}
        <div className="doc-foi" ref={foi} hidden={stare !== null} />
      </div>
    </div>
  )
}

function mesajEroare(e: unknown): string {
  return e instanceof Error ? e.message : String(e)
}
