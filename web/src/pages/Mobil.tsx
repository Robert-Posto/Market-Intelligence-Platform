import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Button, Collapse, Segmented, Tooltip } from 'antd'
import { useSearchParams } from 'react-router-dom'
import type { Mobil as MobilT, Sentiment } from '@mcc/shared'
import { useMeta } from '../api/meta'
import { useMobil, useSentiment } from '../api/rate_mobil'
import { BareStele } from '../components/BareStele'
import { Despre, EtichetaBanca, Eroare, SeIncarca } from '../components/comune'
import { Tabel, type Coloana } from '../components/Tabel'
import { T, useLang } from '../i18n'
import { num } from '../util/format'
import Capturi from './rate_mobil/Capturi'
import { BaraRecenzii, ListaRecenzii, type FiltruRecenzii } from './rate_mobil/Recenzii'
import '../styles/rate_mobil.css'

type Rand = MobilT['versiuni'][number] & { rec: Sentiment['sumar'][number] | null }

/** Parametrii goi nu intră în adresă: `#/mobil?platforma=ios`, nu `…&banca=&nota=`. */
const curat = (o: Record<string, string>) => Object.fromEntries(Object.entries(o).filter(([, v]) => v))

/**
 * 2.3 Aplicații mobile și recenzii. Pagina 2.7 (Sentiment) s-a mutat aici, la
 * cererea lui Robert (25.09): și aplicația, și recenziile vin din același loc
 * (pagina publică din store), iar întrebările merg împreună („ce notă are
 * aplicația și de ce se plâng oamenii”). Un comutator iOS / Android; Android nu
 * e încă colectat.
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

function Android() {
  const { t } = useLang()
  return (
    <section>
      <div className="gol-stare">
        <b>{t('mobil.android_titlu')}</b>
        {t('mobil.android_necolectat')}
      </div>
      <h4 className="mb-h4">{t('mobil.ce_va_contine')}</h4>
      <p className="note">{t('mobil.android_descriere')}</p>
    </section>
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
  const { t, tn, locale } = useLang()
  const [sp, setSp] = useSearchParams()
  const f: FiltruRecenzii = { banca: sp.get('banca') || '', nota: sp.get('nota') || '', storefront: sp.get('storefront') || '' }
  const meta = useMeta()
  const mob = useMobil()
  const s = useSentiment(f.banca, f.nota, f.storefront)
  const [capturi, setCapturi] = useState<string | null>(null)
  useLa(sp.get('la'), !!(meta.data && mob.data && s.data), sp.toString())

  const err = meta.error ?? mob.error ?? s.error
  if (err) return <Eroare e={err} />
  if (!meta.data || !mob.data || !s.data) return <SeIncarca />
  const m = meta.data
  const d = mob.data
  const sent = s.data

  const mergi = (o: Partial<FiltruRecenzii> & { la?: string }) => setSp(curat({ platforma: 'ios', ...f, ...o }))
  const capturiPe: Record<string, string[]> = {}
  for (const x of d.screenshoturi) (capturiPe[x.banca] ??= []).push(x.url)
  const rec = Object.fromEntries(sent.sumar.map((x) => [x.banca, x]))
  const v: Rand[] = d.versiuni.map((r) => ({ ...r, rec: rec[r.banca] ?? null }))
  const nota = (r: Rand) => (r.rating_agregat === null ? null : Number(r.rating_agregat))
  const dif = (r: Rand) => (r.rec && r.rec.medie_text && r.rating_agregat ? r.rec.medie_text - Number(r.rating_agregat) : null)

  // tot rândul duce la recenziile băncii (încă un clic: toate); numele, „ce e nou” și capturile își opresc clicul
  const rand = (r: Rand) => (r.rec ? { onClick: () => mergi({ banca: r.banca === f.banca ? '' : r.banca, la: 'recenzii' }) } : undefined)
  const coloane: Coloana<Rand>[] = [
    { cheie: 'banca', cap: t('rate.banca'), s: (r) => m.nume[r.banca] ?? r.banca, td: (r) => ({ className: 'mb-nowrap', ...rand(r) }),
      val: (r) => <EtichetaBanca slug={r.banca} m={m} tag /> },
    { cheie: 'nota', cap: t('mobil.nota_app_store'), num: true, s: nota, td: rand,
      val: (r) => (r.rating_agregat ? <><b>{num(Number(r.rating_agregat), locale)}</b> ★</> : '—') },
    { cheie: 'volum', cap: <Cap titlu={t('mobil.nr_note_title')}>{t('mobil.nr_note')}</Cap>, num: true, s: (r) => r.volum_rating, td: rand,
      val: (r) => num(r.volum_rating, locale, 0) },
    { cheie: 'distributie', cap: <Cap titlu={t('mobil.distributia_title')}>{t('mobil.distributia_notelor')}</Cap>, td: rand,
      val: (r) => <BareStele dist={r.distributie_stele} latime={120} /> },
    { cheie: 'scrise', cap: t('mobil.nota_recenziilor_scrise'), num: true, s: (r) => r.rec?.medie_text ?? null, td: rand,
      val: (r) => (r.rec
        ? <>{num(r.rec.medie_text, locale)} ★<span className="sub">{t('mobil.din_citite', { n: num(r.rec.review_uri, locale, 0) })}</span></>
        : '—') },
    { cheie: 'negative', cap: t('mobil.negative_cap'), num: true, s: (r) => (r.rec ? r.rec.negative / r.rec.review_uri : null), td: rand,
      val: (r) => (r.rec
        ? <>{t('mobil.negative_din', { negative: num(r.rec.negative, locale, 0), total: num(r.rec.review_uri, locale, 0) })}
            <span className="sub">{Math.round((100 * r.rec.negative) / r.rec.review_uri)}%</span></>
        : '—') },
    { cheie: 'diferenta', cap: <Cap titlu={t('mobil.diferenta_title')}>{t('mobil.diferenta_cap')}</Cap>, num: true, s: dif, td: rand,
      val: (r) => {
        const x = dif(r)
        if (x === null) return '—'
        if (Math.abs(x) < 0.005) return '0'
        return <b style={{ color: x < 0 ? 'var(--warn)' : 'var(--ok)' }}>{x > 0 ? '+' : '−'}{num(Math.abs(x), locale)}</b>
      } },
    { cheie: 'versiune', cap: t('mobil.versiune'), s: (r) => r.versiune, td: (r) => ({ className: 'mono', ...rand(r) }), val: (r) => r.versiune ?? '—' },
    { cheie: 'nou', cap: t('mobil.ce_e_nou'), td: rand, val: (r) => <CeENou text={r.note_lansare} /> },
    { cheie: 'capturi', cap: t('mobil.capturi'), s: (r) => (capturiPe[r.banca] ?? []).length, td: rand,
      val: (r) => {
        const n = (capturiPe[r.banca] ?? []).length
        return n ? <Button size="small" className="mb-nowrap" onClick={(e) => { e.stopPropagation(); setCapturi(r.banca) }}>{tn('mobil.n_capturi', n)}</Button> : '—'
      } },
  ]

  return (
    <div style={{ opacity: s.isPlaceholderData ? 0.45 : 1 }}>
      <section className="apl-tabel">
        <h2>{t('mobil.aplicatiile')}</h2>
        <p className="note" style={{ margin: '0 0 10px' }}>
          <T k="mobil.nota_identificate" params={{ n: d.versiuni.length }} />{' '}<T k="mobil.nota_clic" />
        </p>
        <Tabel randuri={v} coloane={coloane} cheieRand={(r) => `${r.banca}|${r.platforma}`} libra={(r) => r.banca} implicit={['volum', 'descend']}
          clasaRand={(r) => [r.rec ? 'clic' : '', r.banca === f.banca ? 'ales' : ''].join(' ').trim()} />
        <Despre>
          <div className="callout warn" style={{ marginBottom: 14 }}><T k="comun.doua_note" /></div>
          <T k="mobil.despre_reale" />
          <T k="mobil.despre_data_actualizare" />
        </Despre>
      </section>
      <BaraRecenzii s={sent} f={f} schimba={(o) => mergi(o)} sterge={() => setSp({ platforma: 'ios', la: 'recenzii' })} />
      <ListaRecenzii key={`${f.banca}|${f.nota}|${f.storefront}`} s={sent} f={f} m={m} />
      <Capturi banca={capturi} urls={capturi ? capturiPe[capturi] ?? [] : []} m={m} onClose={() => setCapturi(null)} />
    </div>
  )
}

/** Antetul cu explicație la hover (în aplicația veche, `title` pe <th>). */
function Cap({ titlu, children }: { titlu: string; children: ReactNode }) {
  return <Tooltip title={titlu}><span>{children}</span></Tooltip>
}

/** „Ce e nou” pliat: notele de lansare ajung la 401 caractere (BCR, 05.10.2026); deschise, ar lungi fiecare rând al tabelului. */
function CeENou({ text }: { text: string | null }) {
  if (!text) return <span className="gri">—</span>
  return (
    // clicul pe „ce e nou” deschide textul, nu filtrul pe bancă
    <div onClick={(e) => e.stopPropagation()}>
      <Collapse ghost className="despre mb-nou"
        items={[{ key: 'n', label: <span className="despre-cap">ⓘ {text.slice(0, 70).replace(/\s+\S*$/, '')}…</span>,
          children: <div className="note mb-nou-txt">{text}</div> }]} />
    </div>
  )
}
