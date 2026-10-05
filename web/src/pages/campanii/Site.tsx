import { useDeferredValue, useMemo, useState, type ReactNode } from 'react'
import { Checkbox, Collapse, Input, Select, Tooltip } from 'antd'
import { useSearchParams } from 'react-router-dom'
import type { BancaCampanii, Campanie, Campanii } from '@mcc/shared'
import { useCampanii } from '../../api/campanii'
import type { Meta } from '../../api/meta'
import { Banda, BaraSectiune, Chip } from '../../components/Banda'
import { Despre, EtichetaBanca, Eroare, Pill, SeIncarca } from '../../components/comune'
import { Tabel } from '../../components/Tabel'
import { T, useLang, type DictKey } from '../../i18n'
import { deLaServer } from '../../i18n/server'
import { faraDiacritice, formatZi, num } from '../../util/format'
import type { PropsSectiune } from './tipuri'

/*
 * 2.4: campaniile de pe site-urile băncilor (migrarea 019, colectorul ingest/campanii.py).
 * Sunt 742 în rularea din 30.09.2026: vin toate deodată, iar filtrele se combină aici,
 * fără cereri noi. Implicit: doar cele active și doar cele organizate de bancă; filialele,
 * schema de card și partenerii se păstrează în bază, dar nu intră în comparație.
 */
const STARE: Record<string, [DictKey, 'ok' | 'amb' | undefined]> = {
  activa: ['campanii.activa', 'ok'],
  incheiata: ['campanii.site.stare_incheiata', undefined],
  de_verificat: ['campanii.site.stare_de_verificat', 'amb'],
}
const ORD_STARE: Record<string, number> = { activa: 0, de_verificat: 1, incheiata: 2 }
const TIP: Record<string, DictKey> = {
  campanie: 'campanii.site.tip_campanie',
  program: 'campanii.site.tip_program',
  oferta_curenta: 'campanii.site.tip_oferta_curenta',
}
const CATEG: Record<string, DictKey> = {
  conturi_carduri: 'campanii.site.categ_conturi_carduri',
  credite: 'campanii.site.categ_credite',
  depozite: 'campanii.site.categ_depozite',
}
const ORG: Record<string, [DictKey, DictKey]> = {
  grup: ['campanii.filiala', 'campanii.site.org_grup_titlu'],
  schema_card: ['campanii.site.org_schema_card', 'campanii.site.org_schema_card_titlu'],
  partener: ['campanii.site.org_partener', 'campanii.site.org_partener_titlu'],
}
const ROL: Record<string, DictKey> = {
  regulament: 'campanii.site.rol_regulament',
  act_aditional: 'campanii.site.act_aditional',
  landing: 'campanii.site.rol_document',
}

/* Pe 30.09.2026, ~215 titluri erau textul linkului de pe pagina-listă („aici” de 65 de ori
   la ING, „Vezi regulamentul, Deschide in tab nou” de 57 de ori la BCR): nu spun despre ce
   e campania. Acolo se arată și numele documentului din adresă, marcat ca atare. */
const TITLU_GOL =
  /^(aici|vezi( regulament(ul)?)?|detalii [iî]n regulament|regulament(ul)?( oficial)?( al)?( campaniei| campanie| promo[tț]iei)?|promo[tț]ie|campanii|saltbank|brd|vista bank)$/i
const titluGol = (t: string | null | undefined) => {
  const x = String(t || '').replace(/\s*,\s*deschide in tab nou\s*$/i, '').trim()
  return !x || TITLU_GOL.test(x) || /^pdf\s/i.test(x)
}
function numeDinUrl(u: string | null | undefined): string {
  try {
    const seg = new URL(u ?? '').pathname.split('/').filter(Boolean)
    return decodeURIComponent(seg[seg.length - 1] || '')
      .replace(/(\.(pdf|html?|coredownload))+$/i, '')
      .replace(/[-_]+/g, ' ')
      .trim()
  } catch {
    return ''
  }
}
const docPrincipal = (r: Campanie) => (r.documente || []).find((d) => d.rol === 'regulament') ?? null
const titluDinUrl = (r: Campanie) => (titluGol(r.titlu) ? numeDinUrl((docPrincipal(r) ?? r).url) : '')

type Rand = Campanie & { _cauta: string }
type Numarare = { activa: number; incheiata: number; de_verificat: number }

/** Filtrele stau în adresă (`?s=site&banca=bcr&stare=toate…`); căutarea, ca la 2.1, doar în pagină. */
const P = { banca: 'banca', stare: 'stare', tip: 'tip', segment: 'segment', categ: 'categ', filiale: 'filiale' } as const

export default function Site({ m, taburi, subsol }: PropsSectiune) {
  const q = useCampanii()
  if (q.error) return <Gol taburi={taburi} corp={<Eroare e={q.error} />} />
  if (!q.data) return <Gol taburi={taburi} corp={<SeIncarca />} />
  return <Corp d={q.data} m={m} taburi={taburi} subsol={subsol} />
}

function Gol({ taburi, corp }: { taburi: ReactNode; corp: ReactNode }) {
  return (
    <>
      <BaraSectiune taburi={taburi} />
      {corp}
    </>
  )
}

function Corp({ d, m, taburi, subsol }: { d: Campanii; m: Meta; taburi: ReactNode; subsol: ReactNode }) {
  const { t, lang, locale } = useLang()
  const [sp, setSp] = useSearchParams()
  const [cauta, setCauta] = useState('')
  const cautaAmanat = useDeferredValue(cauta)
  const nume = (b: string) => m.nume[b] ?? b
  const primaLibra = (a: string, b: string) => Number(b === 'libra') - Number(a === 'libra')

  const prep = useMemo(() => {
    const rs: Rand[] = d.randuri.map((r) => ({
      ...r,
      _cauta: faraDiacritice([r.titlu, r.beneficiu, titluDinUrl(r), m.nume[r.banca] ?? r.banca].map((x) => x ?? '').join(' ')),
    }))
    const comp = rs.filter((r) => r.in_comparatie)
    const pe: Record<string, Numarare> = {}
    for (const r of comp) {
      const x = (pe[r.banca] ??= { activa: 0, incheiata: 0, de_verificat: 0 })
      if (r.stare && r.stare in x) x[r.stare as keyof Numarare]++
    }
    return { rs, comp, pe }
  }, [d, m])
  const { rs, comp, pe } = prep

  const f = {
    banca: sp.get(P.banca) ?? '',
    // implicit „active”; „toate” se scrie în adresă, ca adresa fără parametru să rămână cea veche
    stare: sp.get(P.stare) === 'toate' ? '' : sp.get(P.stare) || 'activa',
    tip: sp.get(P.tip) ?? '',
    segment: sp.get(P.segment) ?? '',
    cat: sp.get(P.categ) ?? '',
    filiale: sp.get(P.filiale) === '1',
  }
  const schimba = (k: string, v: string) =>
    setSp((p) => {
      const n = new URLSearchParams(p)
      if (v) n.set(k, v)
      else n.delete(k)
      return n
    })
  /* tabelul fără filtrare pe ascuns: chip-ul alege banca din select (încă un clic: toate) */
  const comutaBanca = (b: string) => schimba(P.banca, f.banca === b ? '' : b)

  const cq = faraDiacritice(cautaAmanat.trim())
  const potriveste = (val: string | null | undefined, ales: string, gol: string) => !ales || (ales === gol ? !val : val === ales)
  const lista = rs.filter(
    (r) =>
      (f.filiale || r.in_comparatie) &&
      (!f.banca || r.banca === f.banca) &&
      (!f.stare || r.stare === f.stare) &&
      potriveste(r.tip_oferta, f.tip, 'nedecis') &&
      potriveste(r.segment, f.segment, 'nemarcat') &&
      potriveste(r.categorie_produs, f.cat, 'nemarcata') &&
      (!cq || r._cauta.includes(cq)),
  )

  const slugs = Object.keys(pe).sort(
    (a, b) => primaLibra(a, b) || pe[b]!.activa - pe[a]!.activa || nume(a).localeCompare(nume(b), locale),
  )
  const rulare = String(d.rulare?.campanii || '').slice(0, 10)
  const zi = formatZi(rulare, locale)
  const nActive = comp.filter((r) => r.stare === 'activa').length
  const banciCu = [...new Set(rs.map((r) => r.banca))].sort((a, b) => primaLibra(a, b) || nume(a).localeCompare(nume(b), locale))
  const nFil = rs.length - comp.length
  const nGol = rs.filter((r) => titluGol(r.titlu)).length
  const motive: Record<string, number> = {}
  for (const r of rs.filter((x) => x.stare === 'de_verificat')) {
    for (const x of (r.motiv_verificare || '').split('; ')) {
      const k = x.replace(/: .*$/, '').replace(/ e \d.*$/, '')
      motive[k] = (motive[k] || 0) + 1
    }
  }

  const info = (
    <Pill tip="ok" title={t('campanii.comun.info_rulare_tooltip')}>
      {t('campanii.comun.info_rulare', { data: zi })}
    </Pill>
  )
  const sel = (eticheta: string, k: string, valoare: string, optiuni: { value: string; label: string }[], latime: number) => (
    <label className="f">
      {eticheta}
      <Select value={valoare} options={optiuni} style={{ width: latime }} popupMatchSelectWidth={false}
        // „active” e implicitul stării: nu se scrie în adresă
        onChange={(v: string) => schimba(k, k === P.stare && v === 'activa' ? '' : v)} />
    </label>
  )
  const toate = { value: '', label: t('campanii.comun.toate') }
  const filtre = (
    <>
      {sel(t('campanii.comun.banca'), P.banca, f.banca,
        [{ value: '', label: t('campanii.comun.toate_bancile') }, ...banciCu.map((b) => ({ value: b, label: nume(b) }))], 185)}
      {sel(t('campanii.site.stare'), P.stare, f.stare || 'toate', [
        { value: 'activa', label: t('campanii.site.filtru.stare_active') },
        { value: 'de_verificat', label: t('campanii.site.filtru.stare_de_verificat') },
        { value: 'incheiata', label: t('campanii.site.filtru.stare_incheiate') },
        { value: 'toate', label: t('campanii.comun.toate_mic') },
      ], 130)}
      {sel(t('campanii.site.filtru.tip_oferta'), P.tip, f.tip, [
        toate,
        ...Object.entries(TIP).map(([k, v]) => ({ value: k, label: t(v) })),
        { value: 'nedecis', label: t('campanii.site.filtru.tip_nedecis') },
      ], 150)}
      {sel(t('campanii.site.segment'), P.segment, f.segment, [
        toate,
        { value: 'PF', label: t('campanii.site.filtru.segment_pf') },
        { value: 'PJ', label: t('campanii.site.filtru.segment_pj') },
        { value: 'nemarcat', label: t('campanii.site.filtru.segment_nemarcat') },
      ], 150)}
      {sel(t('campanii.site.categorie'), P.categ, f.cat, [
        toate,
        ...Object.entries(CATEG).map(([k, v]) => ({ value: k, label: t(v) })),
        { value: 'nemarcata', label: t('campanii.site.filtru.categ_nemarcata') },
      ], 150)}
      <label className="f">
        {t('campanii.comun.cauta')}
        <Input className="cauta" type="search" allowClear placeholder={t('campanii.site.filtru.cauta_placeholder')}
          value={cauta} onChange={(e) => setCauta(e.target.value)} />
      </label>
      <Tooltip title={t('campanii.site.filtru.filiale_tooltip')}>
        <Checkbox className="bifa" checked={f.filiale} onChange={(e) => schimba(P.filiale, e.target.checked ? '1' : '')}>
          {t('campanii.site.filtru.filiale', { n: nFil })}
        </Checkbox>
      </Tooltip>
    </>
  )

  const grup = (s: string) => (d.banci ?? []).filter((b) => b.stare === s)
  const listaBanci = (bs: BancaCampanii[]) =>
    bs.map((b, i) => (
      <span key={b.banca}>
        {i > 0 && ', '}
        {b.motiv ? <Tooltip title={deLaServer(b.motiv, lang)}><span>{nume(b.banca)}</span></Tooltip> : nume(b.banca)}
      </span>
    ))
  const fara = (d.banci ?? []).filter((b) => b.stare === 'colectat' && !pe[b.banca])
  const nFara = fara.length + grup('blocat').length + grup('in_afara_scopului').length + grup('fara_config').length

  return (
    <>
      <BaraSectiune taburi={taburi} info={info} filtre={filtre} />
      <Banda
        cifre={[
          { n: num(nActive, locale, 0), eticheta: t('campanii.site.banda.active'), titlu: t('campanii.site.banda.active_tooltip', { data: zi }) },
          { n: num(comp.length, locale, 0), eticheta: t('campanii.site.banda.gasite') },
          { n: num(slugs.length, locale, 0), eticheta: t('campanii.site.banda.banci') },
        ]}
        eticheta={t('campanii.site.banda.eticheta_chipuri')}
        chipuri={slugs.length ? slugs.map((b) => (
          <Chip key={b} slug={b} m={m} n={num(pe[b]!.activa, locale, 0)} activ={f.banca === b} onClick={() => comutaBanca(b)}
            titlu={t('campanii.site.chip_tooltip', { active: pe[b]!.activa, incheiate: pe[b]!.incheiata, de_verificat: pe[b]!.de_verificat })} />
        )) : undefined}
      />
      <section className="cm-sec">
        <Rezultat lista={lista} m={m} />
        <div className="cs-note">
          <Collapse
            ghost
            className="despre"
            items={[{
              key: 'l',
              label: <span className="despre-cap">ⓘ {t('campanii.site.lipsa.titlu', { n: nFara })}</span>,
              children: (
                <div className="note">
                  {fara.length > 0 && <T k="campanii.site.lipsa.colectate_fara" params={{ lista: listaBanci(fara) }} />}
                  <T k="campanii.site.lipsa.blocate_afara" params={{ blocate: listaBanci(grup('blocat')), in_afara: listaBanci(grup('in_afara_scopului')) }} />
                  {grup('fara_config').length > 0 && <T k="campanii.site.lipsa.neconfigurate" params={{ lista: listaBanci(grup('fara_config')) }} />}
                  <br />
                  <span className="gri">{t('campanii.site.lipsa.hover')}</span>
                </div>
              ),
            }]}
          />
          <Despre>
            <T k="campanii.site.despre.p1_ce_e_campanie" />
            <T k="campanii.site.despre.p2_starea" params={{
              motive: Object.entries(motive).sort((a, b) => b[1] - a[1]).slice(0, 5)
                .map(([k, x]) => `${deLaServer(k, lang)} (${num(x, locale, 0)})`).join(', '),
            }} />
            <T k="campanii.site.despre.p3_organizator" params={{ n_filiale: num(nFil, locale, 0) }} />
            <T k="campanii.site.despre.p4_documente" />
            <T k="campanii.site.despre.p5_titluri" params={{ n_gol: num(nGol, locale, 0) }} />
            <T k="campanii.site.despre.p6_banci" />
            <T k="campanii.site.despre.p7_rulare" params={{ data: zi }} />
          </Despre>
        </div>
        {subsol}
      </section>
    </>
  )
}

function Rezultat({ lista, m }: { lista: Rand[]; m: Meta }) {
  const { t, tn, locale } = useLang()
  const n = (s: string) => lista.filter((r) => r.stare === s).length
  const banci = new Set(lista.map((r) => r.banca)).size
  const campanii = <T k={lista.length === 1 ? 'campanii.site.rezumat_campanii_1' : 'campanii.site.rezumat_campanii_n'} params={{ n: num(lista.length, locale, 0) }} />
  const banciTxt = tn('campanii.n_banci', banci, { n: num(banci, locale, 0) })
  const rezumat = (
    <p className="note" style={{ margin: '0 0 10px', maxWidth: 'none' }}>
      {lista.length
        ? <T k="campanii.site.rezumat_cu_stari" params={{ campanii, banci: banciTxt, active: num(n('activa'), locale, 0), de_verificat: num(n('de_verificat'), locale, 0), incheiate: num(n('incheiata'), locale, 0) }} />
        : <T k="campanii.site.rezumat" params={{ campanii, banci: banciTxt }} />}
    </p>
  )
  if (!lista.length) return <>{rezumat}<p className="note">{t('campanii.site.nicio_campanie_filtre')}</p></>

  /* cele mai noi întâi, fără perioadă la coadă; Tabel păstrează ordinea până la primul clic pe antet */
  const inceput = (r: Campanie) => r.fereastra_start || r.fereastra_sfarsit || ''
  const ordonate = lista.slice().sort((a, b) => Number(!inceput(a)) - Number(!inceput(b)) || inceput(b).localeCompare(inceput(a)))
  return (
    <>
      {rezumat}
      <Tabel
        randuri={ordonate}
        cheieRand={(r) => String(r.id ?? `${r.banca}|${r.url}|${r.titlu}`)}
        libra={(r) => r.banca}
        coloane={[
          { cheie: 'banca', cap: t('campanii.comun.banca'), s: (r) => m.nume[r.banca] ?? r.banca, td: () => ({ className: 'cs-nowrap' }),
            val: (r) => {
              const o = r.organizator ? ORG[r.organizator] : undefined
              return (
                <>
                  <EtichetaBanca slug={r.banca} m={m} fisa tag />
                  {o && <div><Pill title={t(o[1]) + (r.organizator_citat ? ': ' + r.organizator_citat : '')}>{t(o[0])}</Pill></div>}
                </>
              )
            } },
          { cheie: 'campanie', cap: t('campanii.site.col_campanie'), s: (r) => r.titlu || '', val: (r) => <CelulaCampanie r={r} /> },
          { cheie: 'perioada', cap: <Tooltip title={t('campanii.site.col_perioada_titlu')}>{t('campanii.site.col_perioada')}</Tooltip>,
            s: inceput,
            td: (r) => ({ className: 'mono cs-nowrap', title: r.fereastra_citat ? t('campanii.site.citat_perioada_tooltip', { citat: r.fereastra_citat }) : undefined }),
            val: (r) => <CelulaPerioada r={r} /> },
          { cheie: 'segment', cap: t('campanii.site.segment'), s: (r) => r.segment || '', val: (r) => r.segment || '—' },
          { cheie: 'categorie', cap: t('campanii.site.categorie'), s: (r) => r.categorie_produs || '',
            val: (r) => (r.categorie_produs ? (CATEG[r.categorie_produs] ? t(CATEG[r.categorie_produs]!) : r.categorie_produs) : '—') },
          { cheie: 'stare', cap: t('campanii.site.stare'), s: (r) => (r.stare ? ORD_STARE[r.stare] : undefined), val: (r) => <CelulaStare r={r} /> },
          { cheie: 'documente', cap: t('campanii.site.col_documente'), td: () => ({ className: 'cs-nowrap' }), val: (r) => <CelulaDocumente r={r} /> },
        ]}
      />
    </>
  )
}

function CelulaCampanie({ r }: { r: Campanie }) {
  const { t } = useLang()
  const dinUrl = titluDinUrl(r)
  const ben = r.beneficiu || ''
  const scurt = ben.length > 160 ? ben.slice(0, 159) + '…' : ben
  return (
    <>
      {dinUrl ? (
        <>
          <b title={t('campanii.site.titlu_din_adresa_titlu', { eticheta: r.titlu || '' })}>{dinUrl}</b>{' '}
          <span className="gri" style={{ fontSize: 11 }}>{t('campanii.site.din_adresa_paranteze')}</span>
        </>
      ) : (
        <b>{r.titlu || '—'}</b>
      )}
      {r.tip_oferta && r.tip_oferta !== 'campanie' && <> <Pill>{TIP[r.tip_oferta] ? t(TIP[r.tip_oferta]!) : r.tip_oferta}</Pill></>}
      {ben && <div className="gri cs-ben" title={t('campanii.site.citat_titlu', { citat: ben })}>{scurt}</div>}
    </>
  )
}

function CelulaPerioada({ r }: { r: Campanie }) {
  const { t, locale } = useLang()
  if (!r.fereastra_start && !r.fereastra_sfarsit) return <span className="gri">{t('campanii.site.fara_perioada')}</span>
  const din = r.sursa_ferestrei === 'eticheta_link' ? t('campanii.site.din_eticheta_linkului') : r.sursa_ferestrei === 'url' ? t('campanii.site.din_adresa') : ''
  return (
    <>
      {formatZi(r.fereastra_start, locale)} – {formatZi(r.fereastra_sfarsit, locale)}
      {din && <div className="gri" style={{ fontSize: 11 }}>{din}</div>}
      {r.act_aditional && <> <Pill tip="amb" title={t('campanii.site.act_aditional_titlu')}>{t('campanii.site.act_aditional')}</Pill></>}
    </>
  )
}

function CelulaStare({ r }: { r: Campanie }) {
  const { t, lang } = useLang()
  const s = r.stare ? STARE[r.stare] : undefined
  return (
    <>
      <Pill tip={s?.[1]}>{s ? t(s[0]) : r.stare}</Pill>
      {r.stare === 'activa' && r.incheiata_azi && (
        <Pill title={t('campanii.site.incheiata_intre_timp_titlu')}>{t('campanii.site.incheiata_intre_timp')}</Pill>
      )}
      {r.motiv_verificare && (
        <div className={`cs-motiv${r.stare === 'de_verificat' ? '' : ' gri'}`}>
          {/* motivele vin lipite cu „; ”: fiecare se traduce separat */}
          {r.motiv_verificare.split('; ').map((x) => deLaServer(x, lang)).join('; ')}
        </div>
      )}
    </>
  )
}

/* ↗ duce la sursa oficială, pe site-ul băncii; 📄 deschide copia din Bronze (exact
   versiunea din care s-au citit câmpurile) în vizualizatorul propriu, fără cerere spre
   bancă, cu citatul perioadei căutat în document. */
function CelulaDocumente({ r }: { r: Campanie }) {
  const { t, tn } = useLang()
  const lk = (href: string, text: string, titlu: string) => (
    <a className="sursa" href={href} target="_blank" rel="noopener noreferrer" title={titlu}>{text}</a>
  )
  const q = r.sursa_ferestrei === 'document' ? r.fereastra_citat || '' : ''
  const docs = (r.documente || []).filter((x) => !(x.url === r.url && x.format !== 'pdf'))
  const legaturi = docs.map((x) => {
    const et = ROL[x.rol] ? t(ROL[x.rol]!) : x.rol
    if (x.format === 'pdf' && x.in_bronze) {
      return lk(
        `/pdf.html?u=${encodeURIComponent(x.url)}&p=1&q=${encodeURIComponent(x.rol === 'regulament' ? q : '')}`,
        `📄 ${et}`,
        t(x.fara_text ? 'campanii.site.doc_bronze_scanat_titlu' : 'campanii.site.doc_bronze_titlu', { url: x.url }),
      )
    }
    return lk(x.url, `↗ ${et}`, t(x.format ? 'campanii.site.doc_pe_site_titlu' : 'campanii.site.doc_neadus_titlu', { url: x.url }))
  })
  const rest = legaturi.slice(2)
  const cuBr = (l: ReactNode[]) => l.map((x, i) => <span key={i}><br />{x}</span>)
  return (
    <>
      {r.url && lk(r.url, t('campanii.site.link_sursa'), t('campanii.site.link_sursa_titlu', { url: r.url }))}
      {cuBr(legaturi.slice(0, 2))}
      {rest.length > 0 && (
        <details className="cs-docs">
          <summary className="gri">{tn('campanii.site.documente_in_plus', rest.length)}</summary>
          {rest.map((x, i) => <span key={i}>{i > 0 && <br />}{x}</span>)}
        </details>
      )}
    </>
  )
}
