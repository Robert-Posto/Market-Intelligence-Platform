import { useState } from 'react'
import { Input, Select } from 'antd'
import type { ProdusCatalogLibra } from '@mcc/shared'
import { Despre } from '../../components/comune'
import { Tabel } from '../../components/Tabel'
import { T, useLang, type DictKey } from '../../i18n'
import { faraDiacritice, formatZi, num } from '../../util/format'

/** „Conturi curente (CONT)” → „Conturi curente”: codul din paranteză e al exportului, nu al cititorului. */
const faraParanteza = (t: string | null) => String(t || '').replace(/\s*\([A-Z_]+\)\s*$/, '')

const SEGMENTE: [string, DictKey][] = [
  ['', 'catalog.pf_si_pj'],
  ['PF', 'catalog.persoane_fizice'],
  ['PJ', 'catalog.firme'],
]

/**
 * Catalogul intern Libra. Produsele Libra vin din exportul intern (Sales Command
 * Center), nu de pe web: e referința după care se va face colectarea pe produse
 * la celelalte bănci. Nu are citat și link ca valorile colectate; proveniența e
 * fișierul exportat. Filtrele (categorie, segment, căutare) lucrează pe loc,
 * fără cerere nouă, și nu intră în adresă (nici în aplicația veche nu intrau).
 */
export default function Catalog({ cat }: { cat: ProdusCatalogLibra[] }) {
  const { t, tn, locale } = useLang()
  const [categorie, setCategorie] = useState('')
  const [segment, setSegment] = useState('')
  const [cauta, setCauta] = useState('')

  const categorii = [...new Map(cat.filter((x) => x.categorie_cod).map((x) => [x.categorie_cod!, faraParanteza(x.categorie)])).entries()]
  const q = faraDiacritice(cauta.trim())
  // „PF+PJ” intră și la PF, și la PJ: produsul e pentru oricine
  // cheia rândului e poziția: unicitatea în bază e (fișier, foaie, rând), nu codul produsului
  const vizibile = cat.map((x, i) => ({ ...x, _k: i })).filter((x) =>
    (!categorie || x.categorie_cod === categorie)
    && (!segment || (x.segment || '').includes(segment))
    && (!q || faraDiacritice(`${x.denumire} ${x.cod} ${x.caracteristici || ''} ${x.categorie || ''}`).includes(q)))

  const p0 = cat[0]!
  const generat = p0.generat_la ? formatZi(p0.generat_la, locale) : ''

  return (
    <section className="bk-catalog">
      <div className="filtre bk-catalog-cap">
        <h2>
          {t('catalog.titlu')}{' '}
          <span className="mono gri bk-catalog-n">{tn('catalog.nr_produse', cat.length, { n: num(cat.length, locale, 0) })}</span>
        </h2>
        <Select value={categorie} onChange={setCategorie} style={{ minWidth: 140, marginLeft: 'auto' }} popupMatchSelectWidth={false}
          options={[
            { value: '', label: t('catalog.toate_categoriile') },
            ...categorii.map(([k, n]) => ({ value: k, label: `${n} (${num(cat.filter((x) => x.categorie_cod === k).length, locale, 0)})` })),
          ]} />
        <Select value={segment} onChange={setSegment} popupMatchSelectWidth={false}
          options={SEGMENTE.map(([v, k]) => ({ value: v, label: t(k) }))} />
        <Input className="cauta" allowClear placeholder={t('catalog.cauta_placeholder')} value={cauta} onChange={(e) => setCauta(e.target.value)} style={{ width: 230 }} />
      </div>
      {/* derulare în tabel (70% din ecran): restul fișei rămâne la îndemână */}
      <div className="bk-catalog-wrap">
        <Tabel
          randuri={vizibile}
          cheieRand={(x) => String(x._k)}
          coloane={[
            {
              cheie: 'produs', cap: t('catalog.col_produs'), s: (x) => x.denumire,
              val: (x) => (
                <>
                  <b style={{ fontWeight: 600 }}>{x.denumire}</b>
                  {x.produs_prioritar && <> <span className="eticheta-best" title={t('catalog.prioritar_tooltip')}>{t('catalog.prioritar')}</span></>}
                  <span className="sub mono">{x.cod}</span>
                </>
              ),
            },
            { cheie: 'categorie', cap: t('catalog.col_categorie'), s: (x) => faraParanteza(x.categorie), val: (x) => faraParanteza(x.categorie) || '—' },
            { cheie: 'segment', cap: t('catalog.col_pentru_cine'), s: (x) => x.segment, val: (x) => pentruCine(x, t) },
            { cheie: 'ofera', cap: t('catalog.col_ce_ofera'), val: (x) => <>{x.caracteristici || '—'}<Detalii x={x} /></> },
          ]}
        />
      </div>
      <Despre>
        <T k={generat ? 'catalog.sursa_cu_data' : 'catalog.sursa_fara_data'} params={{ fisier: p0.fisier, data: generat }} />
      </Despre>
    </section>
  )
}

function pentruCine(x: ProdusCatalogLibra, t: (k: DictKey) => string): string {
  if (x.segment === 'PF+PJ') return t('catalog.pf_si_pj')
  if (x.segment === 'PF') return t('catalog.persoane_fizice')
  if (x.segment === 'PJ') return t('catalog.firme')
  // segment necunoscut (o formulare nouă în export): textul exportului, cum vine
  return x.adresabilitate || '—'
}

/** Recomandarea și eligibilitatea, pliate sub „Ce oferă”: textele vin din export și rămân cum sunt. */
function Detalii({ x }: { x: ProdusCatalogLibra }) {
  const { t, locale } = useLang()
  const lei = (v: number) => t('catalog.lei', { valoare: num(v, locale, 0) })
  const min = x.cifra_afaceri_min
  const max = x.cifra_afaceri_max
  const elig = [
    min !== null && max !== null ? t('catalog.cifra_afaceri_interval', { min: lei(min), max: lei(max) })
      : min !== null ? t('catalog.cifra_afaceri_min', { min: lei(min) })
        : max !== null ? t('catalog.cifra_afaceri_max', { max: lei(max) }) : '',
    x.vechime_min_ani !== null ? t('catalog.vechime_min', { n: num(x.vechime_min_ani, locale) }) : '',
    x.vechime_max_ani !== null ? t('catalog.vechime_max', { n: num(x.vechime_max_ani, locale) }) : '',
    x.linii_business ? t('catalog.linii_business', { linii: x.linii_business }) : '',
    x.caen_prefixe ? t('catalog.caen', { prefixe: x.caen_prefixe }) : '',
    x.criterii_eligibilitate || '',
  ].filter(Boolean)
  if (!x.cand_recomand && !elig.length) return null
  return (
    <div className="bk-detalii">
      <Despre eticheta={t('catalog.detalii')}>
        {x.cand_recomand && <T k="catalog.cand_recomanzi" params={{ recomandare: x.cand_recomand }} />}
        {elig.length > 0 && <T k="catalog.eligibilitate" params={{ criterii: elig.join(' · ') }} />}
      </Despre>
    </div>
  )
}
