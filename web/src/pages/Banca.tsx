import { useState } from 'react'
import { Button, Select } from 'antd'
import { Link, useSearchParams } from 'react-router-dom'
import type { AcoperireFisa, MatriceFisa, Rate as RateT, Sentiment } from '@mcc/shared'
import { GRUPURI_FISA, useAcoperireFisa, useCatalogLibra, useLocatiiFisa, useMatriceFisa } from '../api/banca'
import { useMeta, type Meta } from '../api/meta'
import { useRate, useSentiment } from '../api/rate_mobil'
import { Eroare, Pill, SeIncarca } from '../components/comune'
import Sertar, { type CerereSertar } from '../components/Sertar'
import { Tabel } from '../components/Tabel'
import { etDesc, etNume } from '../components/valori'
import { T, useLang, type DictKey } from '../i18n'
import { faraDiacritice, formatZi, num } from '../util/format'
import Catalog from './banca/Catalog'
import '../styles/banca.css'

const GRUP_ET: Record<(typeof GRUPURI_FISA)[number], DictKey> = {
  cont_curent: 'produse.grup_cont_curent',
  carduri: 'produse.grup_carduri',
  transferuri: 'produse.grup_transferuri',
}
const CATEGORII: [string, DictKey][] = [
  ['depozite', 'banca.cat_depozite'],
  ['credite', 'banca.cat_credite'],
  ['conturi_carduri', 'banca.cat_conturi_carduri'],
]

type BancaAcoperire = AcoperireFisa['pe_banca'][number]
type Pret = MatriceFisa['celule'][number] & { grup: DictKey }
type Dobanda = RateT['celule'][number] & { cat: string; catEt: DictKey }

/**
 * Fișa unei bănci (#/banca?b=<slug>): tot ce avem despre o bancă, într-un loc;
 * înainte trebuia căutată pe fiecare pagină în parte. Fără `b`, fișa Libra.
 */
export default function Banca() {
  const { t } = useLang()
  const [sp, setSp] = useSearchParams()
  const slug = sp.get('b') || 'libra'
  const [sertar, setSertar] = useState<CerereSertar | null>(null)
  const meta = useMeta()
  const a = useAcoperireFisa()
  const mat = useMatriceFisa()
  // dobânzile pe categorie, fără termen și produs: aceeași cerere ca 2.2 la prima deschidere
  const rate = [useRate('depozite', '', ''), useRate('credite', '', ''), useRate('conturi_carduri', '', '')]
  const sent = useSentiment(slug, '', '')
  const loc = useLocatiiFisa()
  // Libra: produsele vin din catalogul intern (migrarea 020), nu de pe web
  const catalog = useCatalogLibra(slug === 'libra')

  const eroare = [meta, a, mat, ...rate, sent, loc, catalog].find((q) => q.error)?.error
  if (eroare) return <Eroare e={eroare} />
  if (!meta.data || !a.data) return <SeIncarca />
  const r = a.data.pe_banca.find((x) => x.slug === slug)
  if (!r) {
    return (
      <section>
        <p className="note">{t('banca.necunoscuta', { slug })}</p>
      </section>
    )
  }
  const gata = mat.data && rate.every((q) => q.data) && sent.data && loc.data && (slug !== 'libra' || catalog.data)

  return (
    <>
      <div className="bara-fixa">
        <div className="filtre">
          <label className="f">{t('banca.filtru_banca')}
            {/* căutarea ține locul tastării din <select>-ul vechi (scrii „BCR”, ajungi la BCR); fără diacritice, ca restul căutărilor */}
            <Select value={slug} onChange={(v) => setSp({ b: v })} style={{ minWidth: 260 }} popupMatchSelectWidth={false}
              showSearch filterOption={(q, o) => faraDiacritice(String(o?.label ?? '')).includes(faraDiacritice(q))}
              options={a.data.pe_banca.map((x) => ({ value: x.slug, label: x.nume }))} />
          </label>
          <Butoane r={r} />
        </div>
      </div>
      {!gata ? <SeIncarca /> : (
        <>
          <Casete r={r} m={meta.data} l={loc.data!.banci.find((x) => x.slug === slug)} />
          {slug === 'libra' && catalog.data!.length > 0 && <Catalog cat={catalog.data!} />}
          <Comisioane slug={slug} matrice={mat.data!} deschide={setSertar} />
          <Dobanzi slug={slug} rate={rate.map((q) => q.data!)} deschide={setSertar} />
          <Recenzii slug={slug} sent={sent.data!} vechi={sent.isPlaceholderData} />
        </>
      )}
      <Sertar cerere={sertar} onClose={() => setSertar(null)} />
    </>
  )
}

/** Legăturile spre celelalte pagini, cu banca aleasă și cu cifrele ei (aceleași adrese ca în aplicația veche). */
function Butoane({ r }: { r: BancaAcoperire }) {
  const { t, locale } = useLang()
  const s = encodeURIComponent(r.slug)
  const n = (v: number) => num(v, locale, 0)
  // Versus pune Libra mereu în stânga: de pe fișa Libra se deschide fără bancă aleasă
  const linkuri: [string, string][] = [
    [`#/versus?banci=${r.slug === 'libra' ? '' : s}`, t('banca.buton_compara')],
    [`#/istoric?banca=${s}`, t('banca.buton_istoric', { n: n(r.schimbari) })],
    [`#/surse?banca=${s}`, t('banca.buton_surse', { n: n(r.surse) })],
    [`#/coada?banca=${s}`, t('banca.buton_de_verificat', { n: n(r.in_coada) })],
    [`#/harta?banca=${s}`, t('banca.buton_pe_harta')],
  ]
  return (
    <div className="bk-butoane">
      {linkuri.map(([h, txt]) => <Button key={h} href={h}>{txt}</Button>)}
    </div>
  )
}

function Casete({ r, m, l }: { r: BancaAcoperire; m: Meta; l: { sucursale: number; atm: number; atm_parteneri: number } | undefined }) {
  const { t, tn, locale } = useLang()
  const logo = m.logo[r.slug]
  const retea = l && [
    tn('banca.kpi_retea_sucursale', l.sucursale, { n: num(l.sucursale, locale, 0) }),
    tn('banca.kpi_retea_atm', l.atm, { n: num(l.atm, locale, 0) }),
    ...(l.atm_parteneri ? [tn('banca.kpi_retea_parteneri', l.atm_parteneri, { n: num(l.atm_parteneri, locale, 0) })] : []),
  ].join(' · ')
  return (
    <div className="kpi bk-kpi">
      <div>
        <div className="e">{logo && <img className="bk-logo" src={logo} alt="" />}{m.nume[r.slug] ?? r.slug}</div>
        <div className="l">
          {r.blocate
            ? <Pill tip="amb">{t('banca.kpi_site_blocat')}</Pill>
            : tn('banca.kpi_surse_urmarite', r.surse, { n: num(r.surse, locale, 0) })}
        </div>
      </div>
      <div><div className="e">{t('banca.comisioane')}</div><div className="n">{num(r.comisioane, locale, 0)}</div><div className="l">{t('banca.kpi_preturi_curente')}</div></div>
      <div><div className="e">{t('banca.dobanzi')}</div><div className="n">{num(r.dobanzi, locale, 0)}</div><div className="l">{t('banca.kpi_valori_curente')}</div></div>
      <div>
        <div className="e">{t('banca.kpi_aplicatia')}</div>
        <div className="n">{r.rating ? `${num(r.rating, locale)} ★` : '—'}</div>
        <div className="l">
          {r.note
            ? t(r.note === 1 ? 'banca.kpi_note_app_store_1' : 'banca.kpi_note_app_store', { n: num(r.note, locale, 0) })
            : t('banca.kpi_neidentificata_app_store')}
        </div>
      </div>
      <div>
        <div className="e">{t('banca.kpi_retea_proprie')}</div>
        <div className="n">{l ? num(l.sucursale + l.atm, locale, 0) : '—'}</div>
        <div className="l">{retea || t('banca.kpi_fara_locatii')}</div>
      </div>
    </div>
  )
}

function Comisioane({ slug, matrice, deschide }: { slug: string; matrice: MatriceFisa[]; deschide: (c: CerereSertar) => void }) {
  const { t, locale } = useLang()
  const preturi: Pret[] = matrice.flatMap((d, i) =>
    d.celule.filter((c) => c.banca === slug).map((c) => ({ ...c, grup: GRUP_ET[GRUPURI_FISA[i]!] })))
  return (
    <section>
      <h2>{t('banca.comisioane')}</h2>
      {preturi.length ? (
        <Tabel
          randuri={preturi}
          cheieRand={(x) => `${x.grup}|${x.camp}`}
          onRand={(x) => deschide({ banca: slug, camp: x.camp, unitate: 'lei', scenariu: '' })}
          coloane={[
            { cheie: 'grup', cap: t('banca.col_categorie'), s: (x) => t(x.grup), val: (x) => t(x.grup) },
            {
              cheie: 'serviciu', cap: t('banca.col_serviciu'), s: (x) => etNume(x.camp, t),
              val: (x) => <><b style={{ fontWeight: 500 }}>{etNume(x.camp, t)}</b><span className="sub">{etDesc(x.camp, t)}</span></>,
            },
            { cheie: 'valoare', cap: t('banca.col_de_obicei'), num: true, s: (x) => x.valoare, val: (x) => <b>{t('banca.suma_lei', { suma: num(x.valoare, locale) })}</b> },
            {
              cheie: 'interval', cap: t('banca.col_interval'), num: true, s: (x) => x.minim,
              val: (x) => x.minim === x.maxim
                ? t('banca.suma_lei', { suma: num(x.minim, locale) })
                : t('banca.interval_lei', { minim: num(x.minim, locale), maxim: num(x.maxim, locale) }),
            },
            { cheie: 'n', cap: t('banca.col_preturi'), num: true, s: (x) => x.n, val: (x) => num(x.n, locale, 0) },
            { cheie: 'gratuite', cap: t('banca.col_gratuite'), num: true, s: (x) => x.gratuite, val: (x) => (x.gratuite ? num(x.gratuite, locale, 0) : '—') },
          ]}
        />
      ) : <p className="note">{t('banca.niciun_comision')}</p>}
      <p className="note">{t('banca.nota_clic_rand')}</p>
    </section>
  )
}

function Dobanzi({ slug, rate, deschide }: { slug: string; rate: RateT[]; deschide: (c: CerereSertar) => void }) {
  const { t, locale } = useLang()
  const dobanzi: Dobanda[] = rate.flatMap((d, i) =>
    d.celule.filter((c) => c.banca === slug).map((c) => ({ ...c, cat: CATEGORII[i]![0], catEt: CATEGORII[i]![1] })))
  return (
    <section>
      <h2>{t('banca.dobanzi')}</h2>
      {dobanzi.length ? (
        <Tabel
          randuri={dobanzi}
          cheieRand={(x) => `${x.cat}|${x.camp}`}
          // categoria e și scenariul: `nominala` e și dobândă de depozit, și de credit
          onRand={(x) => deschide({ banca: slug, camp: x.camp, unitate: 'procent', scenariu: x.cat })}
          coloane={[
            { cheie: 'cat', cap: t('banca.col_categorie'), s: (x) => t(x.catEt), val: (x) => t(x.catEt) },
            { cheie: 'tip', cap: t('banca.col_tip'), s: (x) => etNume(x.camp, t), val: (x) => etNume(x.camp, t) },
            { cheie: 'valoare', cap: t('banca.col_tipica'), num: true, s: (x) => x.valoare, val: (x) => <b>{num(x.valoare, locale)}%</b> },
            { cheie: 'interval', cap: t('banca.col_interval'), num: true, s: (x) => x.minim, val: (x) => `${num(x.minim, locale)}–${num(x.maxim, locale)}%` },
            { cheie: 'n', cap: t('banca.col_valori'), num: true, s: (x) => x.n, val: (x) => num(x.n, locale, 0) },
            // denumirea ofertei e a băncii: nu se traduce
            { cheie: 'exemplu', cap: t('banca.col_exemplu'), val: (x) => (x.serviciu || '').slice(0, 70) },
          ]}
        />
      ) : <p className="note">{t('banca.nicio_dobanda')}</p>}
    </section>
  )
}

/** Primele trei recenzii (serverul le dă pe bancă de la nota cea mai mică), cu legătura spre toate în 2.3. */
function Recenzii({ slug, sent, vechi }: { slug: string; sent: Sentiment; vechi: boolean }) {
  const { t, locale } = useLang()
  const s = sent.sumar.find((x) => x.banca === slug)
  return (
    // altă bancă aleasă: recenziile celei vechi rămân estompate până vin cele noi
    <section className="bk-recenzii" style={{ opacity: vechi ? 0.45 : 1 }}>
      <h2>{t('banca.recenzii')}</h2>
      {s ? (
        <>
          <p className="note" style={{ margin: '0 0 10px' }}>
            <T k={s.negative === 1 ? 'banca.recenzii_sumar_o_negativa' : 'banca.recenzii_sumar'} params={{
              medie_text: num(s.medie_text, locale),
              n_recenzii: num(s.review_uri, locale, 0),
              negative: num(s.negative, locale, 0),
              medie_store: num(s.medie_store, locale),
            }} />{' '}
            <Link className="bk-toate" to={`/mobil?banca=${encodeURIComponent(slug)}&la=recenzii`}>{t('banca.toate_recenziile')}</Link>
          </p>
          {sent.recente.slice(0, 3).map((x, i) => {
            const n = Math.max(0, Math.min(5, x.rating ?? 0))
            return (
              <div className="rec" key={i}>
                <div className="rec-cap">
                  <span className={`rec-stele${n >= 4 ? ' bun' : n <= 2 ? ' rau' : ''}`}>{'★'.repeat(n)}{'☆'.repeat(5 - n)}</span>
                  <span className="mono gri rec-data">{x.postat_la ? formatZi(x.postat_la, locale) : ''}</span>
                </div>
                {/* textul recenziei rămâne cum l-a scris omul, netradus */}
                <div className="rec-txt">{x.text || ''}</div>
              </div>
            )
          })}
        </>
      ) : <p className="note">{t('banca.nicio_recenzie')}</p>}
    </section>
  )
}
