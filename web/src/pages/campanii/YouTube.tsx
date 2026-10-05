import { useState, type ReactNode } from 'react'
import { Checkbox, Input, Select, Tooltip } from 'antd'
import { useSearchParams } from 'react-router-dom'
import type { VideoclipYoutube } from '@mcc/shared'
import { faraRutaYoutube, useYoutube } from '../../api/youtube_retele'
import { BaraSectiune, numeScurt } from '../../components/Banda'
import { Despre, EtichetaBanca, Eroare, Pill, SeIncarca } from '../../components/comune'
import { Tabel } from '../../components/Tabel'
import { T, useLang } from '../../i18n'
import { deLaServer } from '../../i18n/server'
import { faraDiacritice, formatZi, num } from '../../util/format'
import type { PropsSectiune } from './tipuri'
import '../../styles/campanii_youtube.css'

/*
 * 2.4: canalele YouTube ale băncilor (YouTube Data API v3, fișierul output/youtube/youtube_<data>.json).
 * Regula politicii YouTube (Developer Policies III.E.2.a): datele API NU se agregă între canalele unor
 * proprietari diferiți. De-aia aici nu există niciun total, medie, clasament sau grafic între bănci:
 * se alege O bancă și se văd doar cifrele canalului ei, cum le dă YouTube. Băncile stau în ordine
 * alfabetică, cu Libra prima, niciodată după cifre; chips-urile n-au numere. Sortarea din tabel
 * lucrează doar în interiorul canalului ales.
 */

// linkul de pe site există, dar nu se extrage: pagini aduse după blocaj, respectiv canalul grupului
const BLOCATE = ['banca-transilvania', 'intesa', 'unicredit', 'cetelem']
const GRUP = ['pko', 'revolut', 'bnpparibas']

const PERIOADE = ['30', '90']
const DURATE = ['scurt', 'lung']

function durataTxt(s: number | null | undefined): string {
  if (s === null || s === undefined) return '—'
  const h = Math.floor(s / 3600)
  const mi = Math.floor((s % 3600) / 60)
  const se = String(s % 60).padStart(2, '0')
  return h ? `${h}:${String(mi).padStart(2, '0')}:${se}` : `${mi}:${se}`
}

export default function YouTube({ m, taburi, subsol }: PropsSectiune) {
  const { t, tn, lang, locale } = useLang()
  const [sp, setSp] = useSearchParams()
  const [cauta, setCauta] = useState('')
  const q = useYoutube()

  if (q.error) return <><BaraSectiune taburi={taburi} /><Eroare e={q.error} /></>
  if (!q.data) return <><BaraSectiune taburi={taburi} /><SeIncarca /></>
  const d = q.data

  const zi = (x: string | null | undefined) => formatZi(x, locale)
  // banca și filtrele rămân în adresă (link de trimis); `replace`, ca în aplicația veche, fără pași noi în istoric
  const schimba = (k: string, v: string | null) =>
    setSp((p) => {
      const n = new URLSearchParams(p)
      if (v) n.set(k, v)
      else n.delete(k)
      return n
    }, { replace: true })

  const eticheta = <Pill title={t('campanii.youtube.eticheta_tooltip')}>{t('campanii.youtube.eticheta')}</Pill>
  const info = (
    <>
      {eticheta}
      {d.data_extragerii && (
        <Tooltip title={t('campanii.youtube.info_retentie_tooltip')}>
          <span className="gri" style={{ fontSize: 12 }}>
            {t('campanii.youtube.info_retentie', { data_extragerii: zi(d.data_extragerii), sterge_la: zi(d.sterge_la) })}
          </span>
        </Tooltip>
      )}
    </>
  )

  const scurt = (b: string) => numeScurt(b, m)
  const lista = (l: string[]) => l.map(scurt).join(', ')
  const fara = Object.keys(m.nume)
    .filter((b) => !d.banci[b] && !BLOCATE.includes(b) && !GRUP.includes(b))
    .sort((a, b) => scurt(a).localeCompare(scurt(b), locale))
  const despre = (
    <Despre>
      <T k="campanii.youtube.despre.p1_sursa" params={{ luni: d.luni || 12 }} />
      <T k="campanii.youtube.despre.p2_canale" params={{ blocate: lista(BLOCATE), grup: lista(GRUP), fara_canal: lista(fara) || '—' }} />
      <T k="campanii.youtube.despre.p3_agregare" />
      <T k="campanii.youtube.despre.p4_retentie" params={{ data_extragerii: zi(d.data_extragerii), sterge_la: zi(d.sterge_la) }} />
      <T k="campanii.youtube.despre.p5_eticheta" />
      <T k="campanii.youtube.despre.p6_nou" params={{
        acum: d.nou_fata_de
          ? t('campanii.youtube.despre.acum_fata_de', { data: zi(d.nou_fata_de) })
          : t('campanii.youtube.despre.acum_prima'),
      }} />
    </Despre>
  )

  const ordine = Object.keys(d.banci).sort(
    (a, b) => Number(b === 'libra') - Number(a === 'libra') || scurt(a).localeCompare(scurt(b), locale),
  )
  if (!ordine.length) {
    const motiv = faraRutaYoutube(d)
      ? t('campanii.youtube.motiv_fara_ruta')
      : deLaServer(d.motiv, lang) || t('campanii.youtube.fara_date_motiv_implicit')
    return (
      <>
        <BaraSectiune taburi={taburi} info={info} />
        <section className="cm-sec">
          <div className="callout warn yt-fara-date"><T k="campanii.youtube.fara_date" params={{ motiv }} /></div>
          {despre}
          {subsol}
        </section>
      </>
    )
  }

  const ales = sp.get('b')
  const banca = ales && d.banci[ales] ? ales : ordine[0]!
  const b = d.banci[banca]!
  const c = b.canal
  const vs = b.videoclipuri ?? []
  /* eticheta „nou” (ingest/youtube_api.py): videoclipul nu era în extragerea anterioară (metoda „id-uri”)
     sau, fără fișierul anterior, e publicat după ziua rulării anterioare (metoda „data”). Doar pe canalul ales. */
  const nouTitlu = b.metoda_nou === 'data'
    ? t('campanii.youtube.nou_tooltip_data', { data: zi(d.nou_fata_de) })
    : t('campanii.youtube.nou_tooltip_iduri', { data: zi(d.nou_fata_de) })
  const numar = (n: number, tot: number) =>
    tot ? tn('campanii.youtube.numar', tot, { n: num(n, locale, 0), total: num(tot, locale, 0) }) : ''

  // filtrele lucrează pe videoclipurile canalului ales, fără cerere nouă
  const perioada = PERIOADE.includes(sp.get('perioada') ?? '') ? sp.get('perioada')! : 'tot'
  const durata = DURATE.includes(sp.get('durata') ?? '') ? sp.get('durata')! : 'toate'
  // prima extragere: nimic nu e „nou”, bifa e oprită, deci nici adresa nu o poate aprinde
  const doarNoi = sp.get('noi') === '1' && !!d.nou_fata_de
  let prag = ''
  if (perioada !== 'tot' && d.data_extragerii) {
    const z = new Date(d.data_extragerii + 'T00:00:00Z')
    z.setUTCDate(z.getUTCDate() - Number(perioada))
    prag = z.toISOString().slice(0, 10)
  }
  const ct = faraDiacritice(cauta.trim())
  const vizibile = vs.filter((v) => {
    const sec = v.durata_sec ?? NaN
    return (!ct || faraDiacritice(v.titlu ?? '').includes(ct))
      && (!prag || String(v.publicat_la ?? '').slice(0, 10) >= prag)
      && (durata === 'toate' || (durata === 'scurt' ? sec <= 60 : sec > 60))
      && (!doarNoi || !!v.nou)
  })

  const filtre = (
    <>
      <label className="f">
        {t('campanii.comun.banca')}
        <Select value={banca} onChange={(v) => schimba('b', v)} style={{ minWidth: 220 }} popupMatchSelectWidth={false}
          options={ordine.map((x) => ({ value: x, label: m.nume[x] ?? x }))} />
      </label>
      <label className="f">
        {t('campanii.comun.cauta')}
        <Input className="cauta" allowClear placeholder={t('campanii.comun.cauta_in_titlu')} value={cauta}
          onChange={(e) => setCauta(e.target.value)} />
      </label>
      <label className="f">
        {t('campanii.youtube.filtru.perioada')}
        <Select value={perioada} onChange={(v) => schimba('perioada', v === 'tot' ? null : v)} style={{ minWidth: 170 }}
          popupMatchSelectWidth={false}
          options={[
            { value: '30', label: t('campanii.youtube.filtru.ultimele_30') },
            { value: '90', label: t('campanii.youtube.filtru.ultimele_90') },
            { value: 'tot', label: t('campanii.youtube.filtru.ultimele_luni', { luni: d.luni || 12 }) },
          ]} />
      </label>
      <label className="f">
        {t('campanii.youtube.durata')}
        <Select value={durata} onChange={(v) => schimba('durata', v === 'toate' ? null : v)} style={{ minWidth: 170 }}
          popupMatchSelectWidth={false}
          options={[
            { value: 'toate', label: t('campanii.comun.toate_mic') },
            { value: 'scurt', label: t('campanii.youtube.filtru.scurte') },
            { value: 'lung', label: t('campanii.youtube.filtru.lungi') },
          ]} />
      </label>
      <Tooltip title={d.nou_fata_de
        ? t('campanii.youtube.filtru.doar_noi_tooltip', { data: zi(d.nou_fata_de) })
        : t('campanii.youtube.filtru.doar_noi_tooltip_prima')}>
        <span className="yt-bifa">
          <Checkbox checked={doarNoi} disabled={!d.nou_fata_de} onChange={(e) => schimba('noi', e.target.checked ? '1' : null)}>
            {t('campanii.youtube.filtru.doar_noi')}
          </Checkbox>
        </span>
      </Tooltip>
      <span className="gri yt-n">{numar(vizibile.length, vs.length)}</span>
    </>
  )

  // fișa canalului ales: doar cifrele lui, cum le dă YouTube
  const cifre: { n: ReactNode; et: string; titlu?: string }[] = [
    {
      n: c.abonati_ascunsi ? t('campanii.youtube.cifre.abonati_ascunsi') : num(c.abonati, locale, 0),
      et: t('campanii.youtube.cifre.abonati'),
      titlu: c.abonati_ascunsi ? t('campanii.youtube.cifre.abonati_ascunsi_tooltip') : t('campanii.youtube.cifre.abonati_tooltip'),
    },
    { n: num(c.vizualizari, locale, 0), et: t('campanii.youtube.cifre.vizualizari'), titlu: t('campanii.youtube.cifre.vizualizari_tooltip') },
    { n: num(c.videoclipuri, locale, 0), et: t('campanii.youtube.cifre.videoclipuri') },
    { n: zi(c.creat_la), et: t('campanii.youtube.cifre.creat_la') },
  ]
  if (d.nou_fata_de) {
    cifre.push({
      n: num(vs.filter((v) => v.nou).length, locale, 0),
      et: t('campanii.youtube.cifre.noi', { data: zi(d.nou_fata_de) }),
      titlu: t('campanii.youtube.cifre.noi_tooltip', { explicatie: nouTitlu }),
    })
  }
  const banda = (
    <div className="cm-banda yt-banda">
      <div className="yt-canal">
        <Tooltip title={t('campanii.youtube.canal_link_tooltip')}>
          <a href={c.link ?? undefined} target="_blank" rel="noopener noreferrer"><b>{c.titlu || banca}</b> ↗</a>
        </Tooltip>
        <span className="gri mono yt-id">{c.custom_url || c.id || ''}</span>
        {eticheta}
      </div>
      <div className="cm-cifre">
        {cifre.map((x, i) => {
          const corp = <div key={i}><b>{x.n}</b><span>{x.et}</span></div>
          return x.titlu ? <Tooltip key={i} title={x.titlu}>{corp}</Tooltip> : corp
        })}
      </div>
      {!d.nou_fata_de && <div className="yt-nou">{t('campanii.youtube.prima_extragere')}</div>}
      <div className="cm-chipuri">
        <span className="cm-et">{t('campanii.youtube.eticheta_chipuri')}</span>
        {ordine.map((x) => (
          <Tooltip key={x} title={t('campanii.youtube.chip_tooltip', { banca: m.nume[x] ?? x })}>
            <button type="button" onClick={() => schimba('b', x)}
              className={['cm-chip', x === 'libra' ? 'ref' : '', x === banca ? 'activ' : ''].join(' ').trim()}>
              {scurt(x)}
            </button>
          </Tooltip>
        ))}
      </div>
    </div>
  )

  const dovada = /^https?:/.test(b.dovada ?? '')
    ? <a href={b.dovada!} target="_blank" rel="noopener noreferrer">{t('campanii.youtube.dovada_link')}</a>
    : (b.dovada || t('campanii.youtube.dovada_implicit'))
  const cuTitlu = (txt: string, titlu: string) => <Tooltip title={titlu}><span>{txt}</span></Tooltip>

  return (
    <>
      <BaraSectiune taburi={taburi} info={info} filtre={filtre} />
      {banda}
      <section className="cm-sec">
        <div className="yt-tabel">
          <p className="note yt-cap">
            <T k="campanii.youtube.cap_tabel" params={{
              eticheta_banca: <EtichetaBanca slug={banca} m={m} />,
              de_la: zi(d.de_la),
              pana_la: zi(d.data_extragerii),
              eticheta_yt: eticheta,
              dovada,
            }} />
          </p>
          {!vs.length ? (
            <p className="note">{t('campanii.youtube.fara_videoclipuri', { luni: d.luni || 12 })}</p>
          ) : (
            // `key`: la altă bancă tabelul pornește iar de la sortarea implicită, ca în aplicația veche
            <Tabel<VideoclipYoutube>
              key={banca}
              randuri={vizibile}
              cheieRand={(v) => v.id}
              implicit={['data', 'descend']}
              gol={t('campanii.youtube.gol')}
              coloane={[
                { cheie: 'data', cap: t('campanii.comun.col_data'), s: (v) => v.publicat_la ?? '',
                  td: () => ({ className: 'mono yt-zi' }), val: (v) => zi(v.publicat_la) },
                { cheie: 'titlu', cap: t('campanii.comun.col_titlu'), s: (v) => v.titlu ?? '',
                  val: (v) => (
                    <>
                      <Tooltip title={t('campanii.youtube.video_link_tooltip')}>
                        <a href={v.link ?? undefined} target="_blank" rel="noopener noreferrer">{v.titlu || v.id} ↗</a>
                      </Tooltip>
                      {v.nou && <Tooltip title={nouTitlu}><span className="yt-et-nou">{t('campanii.youtube.nou')}</span></Tooltip>}
                    </>
                  ) },
                { cheie: 'durata', cap: cuTitlu(t('campanii.youtube.durata'), t('campanii.youtube.durata_tooltip')), num: true,
                  s: (v) => v.durata_sec, val: (v) => durataTxt(v.durata_sec) },
                { cheie: 'vizualizari', cap: t('campanii.youtube.col_vizualizari'), num: true,
                  s: (v) => v.vizualizari, val: (v) => num(v.vizualizari, locale, 0) },
                { cheie: 'likeuri', cap: cuTitlu(t('campanii.youtube.col_likeuri'), t('campanii.youtube.col_likeuri_tooltip')), num: true,
                  s: (v) => v.likeuri, val: (v) => num(v.likeuri, locale, 0) },
                { cheie: 'comentarii', cap: cuTitlu(t('campanii.youtube.col_comentarii'), t('campanii.youtube.col_comentarii_tooltip')), num: true,
                  s: (v) => v.comentarii, val: (v) => num(v.comentarii, locale, 0) },
              ]}
            />
          )}
        </div>
        {despre}
        {subsol}
      </section>
    </>
  )
}
