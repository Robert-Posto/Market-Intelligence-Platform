import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Button, Segmented, Tooltip } from 'antd'
import { useSearchParams } from 'react-router-dom'
import { useMeta, type Meta } from '../api/meta'
import { useMobil, useSentiment } from '../api/rate_mobil'
import { BareStele } from '../components/BareStele'
import { Despre, Eroare, SeIncarca } from '../components/comune'
import { T, useLang } from '../i18n'
import { num } from '../util/format'
import Android from './rate_mobil/android/Android'
import { CeENou, Galerie, RezumatAi, Stele } from './rate_mobil/Piese'
import ComparaLibra, { type RandAplicatie } from './rate_mobil/ComparaLibra'
import { BaraRecenzii, ListaRecenzii, type FiltruRecenzii } from './rate_mobil/Recenzii'
import '../styles/rate_mobil.css'

type Rand = RandAplicatie

/** Parametrii goi nu intră în adresă: `#/mobil?platforma=ios`, nu `…&banca=&nota=`. */
const curat = (o: Record<string, string>) => Object.fromEntries(Object.entries(o).filter(([, v]) => v))

/**
 * 2.3 Aplicații mobile și recenzii. Pagina 2.7 (Sentiment) s-a mutat aici, la
 * cererea lui Robert (25.09): și aplicația, și recenziile vin din același loc
 * (pagina publică din store), iar întrebările merg împreună („ce notă are
 * aplicația și de ce se plâng oamenii”). Un comutator iOS / Android; Android vine
 * din analiza statică a APK-urilor (05.10.2026), nu din Google Play: fără note și recenzii.
 */
export default function Mobil() {
  const [sp, setSp] = useSearchParams()
  const plat = sp.get('platforma') === 'android' ? 'android' : 'ios'
  return (
    <>
      <div className="filtre mb-comutator">
        {/* App Store și Google Play sunt nume proprii: aceeași etichetă în ambele limbi */}
        <Segmented value={plat} onChange={(v) => setSp({ platforma: v })}
          options={[{ value: 'ios', label: 'iOS · App Store' }, { value: 'android', label: 'Android · Google Play' }]} />
      </div>
      {plat === 'android' ? <Android /> : <Ios />}
    </>
  )
}

/**
 * `?la=recenzii` derulează la bara recenziilor: la intrarea în pagină mereu
 * (ruta veche #/sentiment duce aici), pe aceeași pagină doar dacă bara e sub
 * ecran — după un clic pe o bancă din tabel, recenziile ei sunt mai jos.
 */
function useLa(la: string | null, gata: boolean, adresa: string) {
  const prima = useRef(true)
  useEffect(() => {
    if (!gata) return
    const intai = prima.current
    prima.current = false
    const tinta = la && document.getElementById(la)
    if (!tinta) return
    const principal = document.getElementById('principal')
    if (intai || (principal && tinta.getBoundingClientRect().top > principal.clientHeight)) tinta.scrollIntoView()
  }, [la, gata, adresa])
}

function Ios() {
  const { t } = useLang()
  const [sp, setSp] = useSearchParams()
  const f: FiltruRecenzii = { banca: sp.get('banca') || '', nota: sp.get('nota') || '', storefront: sp.get('storefront') || '' }
  const meta = useMeta()
  const mob = useMobil()
  const s = useSentiment(f.banca, f.nota, f.storefront)
  // banca aleasă stă în adresă (`?vs=ing`), ca o comparație să se poată trimite: cu `vs` în adresă, modalul e deschis
  const [compara, setCompara] = useState(false)
  useLa(sp.get('la'), !!(meta.data && mob.data && s.data), sp.toString())

  const err = meta.error ?? mob.error ?? s.error
  if (err) return <Eroare e={err} />
  if (!meta.data || !mob.data || !s.data) return <SeIncarca />
  const m = meta.data
  const d = mob.data
  const sent = s.data

  const ordine: Ordine = ORDINI.includes(sp.get('ordine') as Ordine) ? (sp.get('ordine') as Ordine) : 'volum'
  // ordinea implicită nu intră în adresă, ca filtrele goale
  const vs = sp.get('vs') || ''
  const baza = { platforma: 'ios', ...f, ordine: ordine === 'volum' ? '' : ordine, vs }
  const mergi = (o: Partial<FiltruRecenzii> & { la?: string; ordine?: string; vs?: string }) => setSp(curat({ ...baza, ...o }))
  const capturiPe: Record<string, string[]> = {}
  for (const x of d.screenshoturi) (capturiPe[x.banca] ??= []).push(x.url)
  const rec = Object.fromEntries(sent.sumar.map((x) => [x.banca, x]))
  const v = ordoneaza(d.versiuni.map((r) => ({ ...r, rec: rec[r.banca] ?? null })), ordine, m)

  return (
    <div style={{ opacity: s.isPlaceholderData ? 0.45 : 1 }}>
      <section className="apl-tabel">
        <div className="mb-lista-cap">
          <h2>{t('mobil.aplicatiile')}</h2>
          <Segmented size="small" value={ordine} onChange={(o) => mergi({ ordine: o === 'volum' ? '' : String(o) })}
            options={ORDINI.map((o) => ({ value: o, label: t(`mobil.ordine_${o}`) }))} />
          <Button type="primary" className="mb-btn-compara" onClick={() => setCompara(true)}>{t('mobil.compara_buton')}</Button>
        </div>
        <p className="note" style={{ margin: '0 0 12px' }}>
          <T k="mobil.nota_identificate" params={{ n: d.versiuni.length }} />{' '}<T k="mobil.nota_clic" />
        </p>
        <div className="mb-carduri">
          {v.map((r) => (
            <CardAplicatie key={`${r.banca}|${r.platforma}`} r={r} m={m} urls={capturiPe[r.banca] ?? []} ales={r.banca === f.banca}
              onRecenzii={() => mergi({ banca: r.banca === f.banca ? '' : r.banca, la: 'recenzii' })} />
          ))}
        </div>
        <Despre>
          <div className="callout warn" style={{ marginBottom: 14 }}><T k="comun.doua_note" /></div>
          <T k="mobil.despre_reale" />
          <T k="mobil.despre_data_actualizare" />
        </Despre>
      </section>
      <BaraRecenzii s={sent} f={f} schimba={(o) => mergi(o)} sterge={() => setSp({ platforma: 'ios', la: 'recenzii' })} />
      <ListaRecenzii key={`${f.banca}|${f.nota}|${f.storefront}`} s={sent} f={f} m={m} />
      <ComparaLibra deschis={compara || !!vs} vs={vs} aplicatii={v} capturiPe={capturiPe} m={m}
        alege={(b) => mergi({ vs: b })} onClose={() => { setCompara(false); mergi({ vs: '' }) }} />
    </div>
  )
}

const ORDINI = ['volum', 'nota', 'nume'] as const
type Ordine = (typeof ORDINI)[number]

/** Ca `Tabel`: Libra prima, golurile (aplicație fără note) jos, apoi ordinea aleasă. */
function ordoneaza(v: Rand[], ordine: Ordine, m: Meta): Rand[] {
  const nume = (r: Rand) => m.nume[r.banca] ?? r.banca
  const cheie = (r: Rand) => (ordine === 'nota' ? (r.rating_agregat === null ? null : Number(r.rating_agregat)) : r.volum_rating)
  return [...v].sort((a, b) => {
    if ((a.banca === 'libra') !== (b.banca === 'libra')) return a.banca === 'libra' ? -1 : 1
    if (ordine === 'nume') return nume(a).localeCompare(nume(b))
    const ka = cheie(a)
    const kb = cheie(b)
    if (ka === null || kb === null) return ka === kb ? nume(a).localeCompare(nume(b)) : ka === null ? 1 : -1
    return kb - ka || nume(a).localeCompare(nume(b))
  })
}

/**
 * O aplicație pe un card: sus nota, numărul de note și capturile mereu la vedere; jos rezumatul
 * AI al recenziilor și raportul App Store vs. Google Play. În tabel, capturile stăteau după un
 * buton în ultima coloană (a zecea), deci nimeni nu le compara între bănci.
 */
function CardAplicatie({ r, m, urls, ales, onRecenzii }: {
  r: Rand
  m: Meta
  urls: string[]
  ales: boolean
  onRecenzii: () => void
}) {
  const { t, tn, locale } = useLang()
  return (
    <article className={['mb-card', ales ? 'ales' : ''].join(' ').trim()}>
      <div className="mb-card-sus">
        <div className="mb-card-info">
          <Sigla slug={r.banca} m={m} />
          <div className="mb-rating">
            <div className="mb-nota">
              <Stele nota={r.rating_agregat === null ? null : Number(r.rating_agregat)} marime={26} />
              {r.rating_agregat && <span className="mb-nota-cifra">{num(Number(r.rating_agregat), locale)}</span>}
            </div>
            <Cap titlu={t('mobil.nr_note_title')}>
              <div className="mb-volum">
                <b>{num(r.volum_rating, locale, 0)}</b>
                <span>{t('mobil.note_app_store')}</span>
              </div>
            </Cap>
          </div>
          <Cap titlu={t('mobil.distributia_title')}><span className="mb-stele"><BareStele dist={r.distributie_stele} latime={230} /></span></Cap>
          <div className="mb-versiune">
            <span className="gri">{t('mobil.versiune')}</span> <b className="mono">{r.versiune ?? '—'}</b>
          </div>
          <CeENou text={r.note_lansare} />
          {r.rec && (
            <Button size="small" type={ales ? 'primary' : 'default'} className="mb-btn-rec" onClick={onRecenzii}>
              {ales ? t('mobil.recenzii_toate_bancile') : t('mobil.recenziile_bancii')}
            </Button>
          )}
        </div>
        <div className="mb-card-capturi">
          {urls.length
            ? <>
                <Galerie urls={urls} inaltime={270} clasa="mb-banda" titlu={t('mobil.capturi_titlu', { banca: m.nume[r.banca] ?? r.banca })} />
                <span className="sub mb-banda-nota">{tn('mobil.n_capturi', urls.length)} · {t('mobil.clic_marire')}</span>
              </>
            : <div className="mb-fara-capturi gri">{t('mobil.fara_capturi')}</div>}
        </div>
      </div>
      <div className="mb-card-jos">
        <RezumatAi banca={r.banca} />
      </div>
    </article>
  )
}

/**
 * Doar sigla, fără nume: „ING Bank (Sucursala București)” se rupea pe două rânduri în coloana de
 * 270px și împingea cifrele în jos. Numele rămâne în `alt` și la hover; fără siglă, apare numele.
 */
function Sigla({ slug, m }: { slug: string; m: Meta }) {
  const nume = m.nume[slug] ?? slug
  const logo = m.logo[slug]
  return logo
    ? <Tooltip title={nume}><img className="mb-sigla" src={logo} alt={nume} /></Tooltip>
    : <span className="mb-sigla-txt">{nume}</span>
}

/** Eticheta cu explicație la hover (în aplicația veche, `title` pe <th>). */
function Cap({ titlu, children }: { titlu: string; children: ReactNode }) {
  return <Tooltip title={titlu}><span>{children}</span></Tooltip>
}
