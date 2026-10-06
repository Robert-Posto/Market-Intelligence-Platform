import type { ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Acoperire, Campanii, Retele, Stare } from '@mcc/shared'
import { api } from '../api/client'
import { useMeta } from '../api/meta'
import { EtichetaBanca, Eroare, Pill, Pliat, SeIncarca, Varsta } from '../components/comune'
import { Tabel } from '../components/Tabel'
import { T, useLang, type DictKey } from '../i18n'
import { deLaServer } from '../i18n/server'
import { num } from '../util/format'

/**
 * Overview, punctul de intrare (revamp 25.09 în aplicația veche): șapte carduri
 * pe categoriile 2.1–2.7 — cifra-cheie, câte bănci din 30, prospețimea, link —
 * apoi acoperirea pe bănci. Tabelul tehnic stă pliat. Rulările manuale s-au mutat
 * pe 06.10.2026 în pagina „Rulare manuală” (grupul Jobs).
 */
export default function Overview() {
  const { t, lang, locale } = useLang()
  const meta = useMeta()
  const q = useQuery({
    queryKey: ['overview'],
    queryFn: async () => {
      const [a, st, soc, cmp] = await Promise.all([
        api('/api/acoperire', Acoperire),
        api('/api/stare', Stare),
        api('/api/retele', Retele),
        api('/api/campanii', Campanii),
      ])
      return { a, st, soc, cmp }
    },
  })
  if (q.error) return <Eroare e={q.error} />
  if (meta.error) return <Eroare e={meta.error} />
  if (!q.data || !meta.data) return <SeIncarca />
  const { a, st, soc, cmp } = q.data
  const m = meta.data

  // 2.4: campaniile active de pe site-uri, plus conturile sociale găsite
  const conturi = soc.filter((x) => x.url && x.url !== 'NEGASIT')
  const active = cmp.randuri.filter((x) => x.stare === 'activa' && x.in_comparatie !== false)
  const c = a.categorii
  const pb = a.pe_banca
  const cate = (k: 'comisioane' | 'dobanzi' | 'rating' | 'locatii') =>
    pb.filter((b) => (k === 'rating' ? !!b.rating : b[k] > 0)).length
  const celula = (n: number) => (n ? <b>{num(n, locale, 0)}</b> : <span className="gri">—</span>)

  return (
    <>
      <div className="kpi">
        <Card cod="2.1" titlu="overview.comisioane" cifra={num(c.comisioane, locale, 0)} et={t('overview.card_comisioane_et')} banci={cate('comisioane')} data={c.comisioane_la} link="/produse" />
        <Card cod="2.2" titlu="overview.dobanzi" cifra={num(c.dobanzi, locale, 0)} et={t('overview.card_dobanzi_et')} banci={cate('dobanzi')} data={c.dobanzi_la} link="/rate" />
        <Card cod="2.3" titlu="overview.card_aplicatii_titlu" cifra={num(c.aplicatii, locale, 0)}
          et={t('overview.card_aplicatii_et', { recenzii: num(c.recenzii, locale, 0) })} banci={cate('rating')} data={c.aplicatii_la} link="/mobil" />
        <Card cod="2.4" titlu="overview.card_campanii_titlu" cifra={num(active.length, locale, 0)}
          et={t('overview.card_campanii_et', { conturi: num(conturi.length, locale, 0) })}
          banci={new Set(active.map((x) => x.banca)).size} data={cmp.rulare?.campanii ?? null} link="/campanii" />
        <Card cod="2.5" titlu="overview.card_retea_titlu" cifra={num(c.locatii, locale, 0)} et={t('overview.card_retea_et')} banci={cate('locatii')} data={c.locatii_la} link="/retea" />
        <Card cod="2.6" titlu="overview.card_context_titlu" cifra={num(c.indici, locale, 0)} et={t('overview.card_context_et')} banci={null} data={c.indici_la} link="/context" />
        <Card cod="" titlu="overview.card_istoric_titlu" cifra={num(c.schimbari, locale, 0)} et={t('overview.card_istoric_et')} banci={null} data={null} link="/istoric" />
      </div>

      <Pliat titlu={<>{t('overview.acoperire_titlu')} <span className="note">{t('overview.acoperire_subtitlu')}</span></>}>
        <section>
          <p className="note" style={{ margin: '0 0 10px' }}><T k="overview.acoperire_nota" /></p>
          <Tabel
            randuri={pb}
            cheieRand={(r) => r.slug}
            libra={(r) => r.slug}
            implicit={['comisioane', 'descend']}
            coloane={[
              { cheie: 'banca', cap: t('overview.col_banca'), s: (r) => r.nume, val: (r) => <EtichetaBanca slug={r.slug} m={m} fisa tag /> },
              { cheie: 'comisioane', cap: t('overview.comisioane'), num: true, s: (r) => r.comisioane, val: (r) => celula(r.comisioane) },
              { cheie: 'dobanzi', cap: t('overview.dobanzi'), num: true, s: (r) => r.dobanzi, val: (r) => celula(r.dobanzi) },
              { cheie: 'rating', cap: t('overview.col_aplicatie'), num: true, s: (r) => r.rating,
                val: (r) => (r.rating ? `${num(r.rating, locale)} ★` : <span className="gri">—</span>) },
              { cheie: 'locatii', cap: t('overview.col_locatii'), num: true, s: (r) => r.locatii, val: (r) => celula(r.locatii) },
              { cheie: 'recenzii', cap: t('overview.col_recenzii'), num: true, s: (r) => r.recenzii, val: (r) => celula(r.recenzii) },
              { cheie: 'schimbari', cap: t('overview.col_schimbari'), num: true, s: (r) => r.schimbari, val: (r) => celula(r.schimbari) },
              { cheie: 'coada', cap: t('overview.col_de_verificat'), num: true, s: (r) => r.in_coada,
                val: (r) => (r.in_coada
                  ? <Link className="sursa" to={`/coada?banca=${encodeURIComponent(r.slug)}`}>{num(r.in_coada, locale, 0)}</Link>
                  : <span className="gri">—</span>) },
              { cheie: 'colectare', cap: t('overview.col_colectare'),
                s: (r) => (r.blocate ? 0 : r.comisioane + r.dobanzi ? 2 : 1),
                val: (r) => r.blocate && !(r.comisioane + r.dobanzi)
                  ? <Pill tip="amb" title={t('overview.site_blocat_tooltip')}>{t('overview.site_blocat')}</Pill>
                  : r.blocate
                    ? <Pill tip="amb" title={t('overview.partial_blocat_tooltip')}>{t('overview.partial_blocat')}</Pill>
                    : r.comisioane + r.dobanzi ? <Pill tip="ok">{t('overview.are_date')}</Pill> : <Pill>{t('overview.fara_preturi')}</Pill> },
            ]}
          />
        </section>
      </Pliat>

      <Pliat titlu={t('overview.tehnic_titlu')}>
        <section>
          <Tabel
            randuri={st}
            cheieRand={(r) => r.domeniu}
            coloane={[
              { cheie: 'domeniu', cap: t('overview.col_domeniu'), val: (r) => deLaServer(r.domeniu, lang) },
              { cheie: 'randuri', cap: t('overview.col_randuri'), num: true, val: (r) => num(r.randuri, locale, 0) },
              { cheie: 'ultima', cap: t('overview.col_ultima_actualizare'),
                val: (r) => (r.ultima ? <Varsta t={r.ultima} />
                  : r.randuri ? <Pill>{t('overview.fara_data_in_tabel')}</Pill> : <Pill tip="amb">{t('overview.gol')}</Pill>) },
              { cheie: 'provenienta', cap: t('overview.col_provenienta'), val: (r) => <span className="mono">{deLaServer(r.provenienta, lang)}</span> },
            ]}
          />
        </section>
      </Pliat>
    </>
  )
}

function Card({ cod, titlu, cifra, et, banci, data, link }: {
  cod: string; titlu: DictKey; cifra: string; et: ReactNode; banci: number | null; data: string | null; link: string
}) {
  const { t } = useLang()
  return (
    <div>
      <div className="e"><span className="mono gri" style={{ fontSize: 10.5 }}>{cod}</span> {t(titlu)}</div>
      <div className="n">{cifra}</div>
      <div className="l">{et}</div>
      <div className="l">
        {banci !== null && <T k="overview.card_banci" params={{ banci }} />}
        {banci !== null && data ? ' · ' : ''}
        {data && <Varsta t={data} />}
      </div>
      <Link className="kpi-link" to={link}>{t('overview.card_deschide')}</Link>
    </div>
  )
}
