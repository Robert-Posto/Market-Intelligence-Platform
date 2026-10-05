import { useMemo, useState, type ReactNode } from 'react'
import { Input } from 'antd'
import type { ContSocial } from '@mcc/shared'
import { useRetele } from '../../api/youtube_retele'
import { Banda, BaraSectiune } from '../../components/Banda'
import { Despre, EtichetaBanca, Eroare, Pill, SeIncarca } from '../../components/comune'
import { Tabel } from '../../components/Tabel'
import { T, useLang, type DictKey, type Params } from '../../i18n'
import { faraDiacritice, num } from '../../util/format'
import type { PropsSectiune } from './tipuri'
import '../../styles/campanii_youtube.css'

type Tr = (k: DictKey, p?: Params) => string

/**
 * Numele contului din adresă: fără domeniu, fără `company/` sau `pages/`,
 * fără id-ul numeric pe care Facebook îl lipește la paginile vechi.
 */
function contSocial(url: string, retea: string, t: Tr): string {
  let p = url.replace(/^https?:\/\/[^/]+\/?/, '').replace(/[?#].*$/, '').replace(/\/+$/, '')
  try {
    p = decodeURIComponent(p)
  } catch {
    /* adresă cu % nevalid: rămâne cum e */
  }
  const seg = p.replace(/^(company|pages|p)\//, '').split('/').filter(Boolean)
  const nume = seg.find((s) => !/^\d+$/.test(s))
  if (!nume) return t('campanii.retele.pagina_fara_nume', { segment: seg[0] ?? '' })
  const h = nume.replace(/-\d{9,}$/, '')
  return (retea === 'instagram' || retea === 'tiktok') && !h.startsWith('@') ? '@' + h : h
}

/*
 * Siglele rețelelor, ca SVG inline (fără fișiere sau biblioteci): căile pentru
 * Facebook, LinkedIn și TikTok vin din Simple Icons (CC0); Instagram e desenat
 * din forme simple. Folosite doar ca trimitere la contul oficial al băncii.
 */
const SIGLA: Record<string, ReactNode> = {
  facebook: (
    <svg viewBox="0 0 24 24" aria-label="Facebook"><path fill="currentColor" d="M9.101 23.691v-7.98H6.627v-3.667h2.474v-1.58c0-4.085 1.848-5.978 5.858-5.978.401 0 .955.042 1.468.103a8.68 8.68 0 0 1 1.141.195v3.325a8.623 8.623 0 0 0-.653-.036 26.805 26.805 0 0 0-.733-.009c-.707 0-1.259.096-1.675.309a1.686 1.686 0 0 0-.679.622c-.258.42-.374.995-.374 1.752v1.297h3.919l-.386 2.103-.287 1.564h-3.246v8.245C19.396 23.238 24 18.179 24 12.044c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.628 3.874 10.35 9.101 11.647Z" /></svg>
  ),
  linkedin: (
    <svg viewBox="0 0 24 24" aria-label="LinkedIn"><path fill="currentColor" d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" /></svg>
  ),
  instagram: (
    <svg viewBox="0 0 24 24" aria-label="Instagram">
      <rect x="2.2" y="2.2" width="19.6" height="19.6" rx="5.6" fill="none" stroke="currentColor" strokeWidth="2.2" />
      <circle cx="12" cy="12" r="4.6" fill="none" stroke="currentColor" strokeWidth="2.2" />
      <circle cx="17.6" cy="6.4" r="1.4" fill="currentColor" />
    </svg>
  ),
  tiktok: (
    <svg viewBox="0 0 24 24" aria-label="TikTok"><path fill="currentColor" d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z" /></svg>
  ),
}

/** Ordinea coloanelor din aplicația veche: Facebook, Instagram, LinkedIn, TikTok. */
const RETELE: { k: string; nume: string }[] = [
  { k: 'facebook', nume: 'Facebook' },
  { k: 'instagram', nume: 'Instagram' },
  { k: 'linkedin', nume: 'LinkedIn' },
  { k: 'tiktok', nume: 'TikTok' },
]

/** 2.4: conturile oficiale pe rețelele sociale, un tabel bancă × rețea (înainte, 30 de carduri). */
export default function Retele({ m, taburi, subsol }: PropsSectiune) {
  const { t, tn, locale } = useLang()
  const q = useRetele()
  const [cauta, setCauta] = useState('')
  const rs = q.data

  // conturile pe bancă și rețea; „NEGASIT” (sau fără adresă) = rețeaua lipsește
  const pe = useMemo(() => {
    const o: Record<string, Record<string, ContSocial>> = {}
    for (const r of rs ?? []) {
      if (r.url && r.url !== 'NEGASIT') (o[r.slug] ??= {})[r.retea] = r
    }
    return o
  }, [rs])

  if (q.error) return <><BaraSectiune taburi={taburi} /><Eroare e={q.error} /></>
  if (!rs) return <><BaraSectiune taburi={taburi} /><SeIncarca /></>

  const cont = (b: string, k: string) => pe[b]?.[k] ?? null
  const banci = Object.keys(m.nume).sort(
    (a, b) => Number(b === 'libra') - Number(a === 'libra') || (m.nume[a] ?? a).localeCompare(m.nume[b] ?? b, locale),
  )
  const are = (b: string) => RETELE.filter((x) => cont(b, x.k)).length
  const nume = (b: string, k: string) => {
    const r = cont(b, k)
    return r ? contSocial(r.url!, k, t) : ''
  }
  const titlu = (r: ContSocial) =>
    [t(r.sursa === 'site banca' ? 'campanii.social.tooltip_sursa.site' : 'campanii.social.tooltip_sursa.cautare'), r.nota]
      .filter(Boolean)
      .join(' · ')
  const c = faraDiacritice(cauta.trim())
  const vizibile = c
    ? banci.filter((b) => faraDiacritice([b, m.nume[b] ?? '', ...RETELE.map((x) => nume(b, x.k))].join(' ')).includes(c))
    : banci
  const gasite = Object.values(pe).flatMap((x) => Object.values(x))

  const filtre = (
    <>
      <label className="f">
        {t('campanii.comun.cauta')}
        <Input className="cauta" allowClear placeholder={t('campanii.social.cauta_placeholder')}
          value={cauta} onChange={(e) => setCauta(e.target.value)} />
      </label>
      <span className="gri rs-n">{c ? tn('comun.cauta_carduri.n_banci', vizibile.length) : ''}</span>
      <span className="rs-leg">
        <span><Pill>{t('campanii.social.international')}</Pill> {t('campanii.social.legenda_international')}</span>
        <span>{t('campanii.social.legenda_hover')}</span>
      </span>
    </>
  )

  return (
    <>
      <BaraSectiune taburi={taburi} filtre={filtre}
        info={<span className="gri" style={{ fontSize: 12 }}>{t('campanii.social.info')}</span>} />
      <Banda
        cifre={[
          { n: num(gasite.length, locale, 0), eticheta: t('campanii.social.banda.gasite') },
          { n: <T k="campanii.social.banda.banci_valoare" params={{ n: num(banci.filter(are).length, locale, 0), total: num(banci.length, locale, 0) }} />,
            eticheta: t('campanii.social.banda.banci') },
          { n: num(gasite.filter((r) => r.nivel === 'grup').length, locale, 0), eticheta: t('campanii.social.banda.grup') },
        ]}
      />
      <section className="cm-sec">
        <div className="rs-tabel">
          <Tabel
            randuri={vizibile}
            cheieRand={(b) => b}
            libra={(b) => b}
            gol={t('campanii.social.gol')}
            coloane={[
              { cheie: 'banca', cap: t('campanii.comun.banca'), s: (b) => m.nume[b] ?? b, val: (b) => <EtichetaBanca slug={b} m={m} fisa tag /> },
              ...RETELE.map((x) => ({
                cheie: x.k,
                cap: <><span className={`rs-ic ${x.k}`}>{SIGLA[x.k]}</span>{x.nume}</>,
                s: (b: string) => nume(b, x.k).toLowerCase(),
                td: (b: string) => {
                  const r = cont(b, x.k)
                  return { className: 'rs-c', title: r ? titlu(r) : undefined }
                },
                val: (b: string) => {
                  const r = cont(b, x.k)
                  if (!r) return <span className="gri">—</span>
                  return (
                    <>
                      <a href={r.url!} target="_blank" rel="noopener noreferrer">{contSocial(r.url!, x.k, t)} ↗</a>
                      {r.nivel === 'grup' && <Pill title={t('campanii.social.international_tooltip')}>{t('campanii.social.international')}</Pill>}
                    </>
                  )
                },
              })),
              { cheie: 'conturi', cap: t('campanii.social.col_conturi'), num: true, s: are,
                val: (b) => <span className="rs-nr">{t('campanii.social.conturi_din', { n: are(b), total: RETELE.length })}</span> },
            ]}
          />
        </div>
        <Despre>
          <T k="campanii.social.despre.p1" />
          <T k="campanii.social.despre.p2" />
          <T k="campanii.social.despre.p3" />
        </Despre>
        {subsol}
      </section>
    </>
  )
}
