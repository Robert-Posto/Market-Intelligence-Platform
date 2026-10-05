import { useDeferredValue, useMemo, useState, type ReactNode } from 'react'
import { Checkbox, Input, Select } from 'antd'
import { useSearchParams } from 'react-router-dom'
import type { Comunicat } from '@mcc/shared'
import { useCampanii, useComunicate } from '../../api/campanii'
import type { Meta } from '../../api/meta'
import { Banda, BaraSectiune, Chip } from '../../components/Banda'
import { Despre, EtichetaBanca, Eroare, Pill, SeIncarca } from '../../components/comune'
import { Paginare } from '../../components/Paginare'
import { Tabel } from '../../components/Tabel'
import { T, useLang, type DictKey } from '../../i18n'
import { faraDiacritice, formatZi, num } from '../../util/format'
import type { PropsSectiune } from './tipuri'

/* 2.4: comunicatele de presă. 989 pe 30.09.2026: vin toate, paginarea e aici. */
const PE_PAGINA = 50
const DATA_DIN: Record<string, DictKey> = {
  url: 'campanii.comunicate.tooltip_data.url',
  lista: 'campanii.comunicate.tooltip_data.lista',
  pagina: 'campanii.comunicate.tooltip_data.pagina',
}

type Rand = Comunicat & { _cauta: string }

export default function Comunicate({ m, taburi, subsol }: PropsSectiune) {
  const q = useComunicate()
  // data rulării vine cu campaniile (rulare.comunicate), ca în aplicația veche
  const camp = useCampanii()
  const eroare = q.error ?? camp.error
  if (eroare) return <><BaraSectiune taburi={taburi} /><Eroare e={eroare} /></>
  if (!q.data || !camp.data) return <><BaraSectiune taburi={taburi} /><SeIncarca /></>
  return <Corp com={q.data} rulare={String(camp.data.rulare?.comunicate || '').slice(0, 10)} m={m} taburi={taburi} subsol={subsol} />
}

function Corp({ com, rulare, m, taburi, subsol }: { com: Comunicat[]; rulare: string; m: Meta; taburi: ReactNode; subsol: ReactNode }) {
  const { t, locale } = useLang()
  const [sp, setSp] = useSearchParams()
  const [cauta, setCauta] = useState('')
  const cautaAmanat = useDeferredValue(cauta)
  const nume = (b: string) => m.nume[b] ?? b

  const { rs, pe, banci } = useMemo(() => {
    const rs: Rand[] = com.map((r) => ({ ...r, _cauta: faraDiacritice(`${r.titlu || ''} ${m.nume[r.banca] ?? r.banca}`) }))
    const pe: Record<string, number> = {}
    for (const r of rs) pe[r.banca] = (pe[r.banca] || 0) + 1
    const banci = Object.keys(pe).sort(
      (a, b) => Number(b === 'libra') - Number(a === 'libra') || (m.nume[a] ?? a).localeCompare(m.nume[b] ?? b, locale),
    )
    return { rs, pe, banci }
  }, [com, m, locale])

  // banca și bifa stau în adresă (`?s=comunicate&banca=bcr&campanie=1`); căutarea și pagina, doar în pagină
  const banca = sp.get('banca') ?? ''
  const doar = sp.get('campanie') === '1'
  const schimba = (k: string, v: string) =>
    setSp((p) => {
      const n = new URLSearchParams(p)
      if (v) n.set(k, v)
      else n.delete(k)
      return n
    })
  const cq = faraDiacritice(cautaAmanat.trim())
  const lista = rs.filter((r) => (!banca || r.banca === banca) && (!doar || r.e_campanie) && (!cq || r._cauta.includes(cq)))

  // orice filtru nou întoarce lista la prima pagină
  const semn = `${banca}|${doar}|${cq}`
  const [pag, setPag] = useState({ semn, off: 0 })
  const off = pag.semn === semn ? pag.off : 0

  const nCamp = rs.filter((r) => r.e_campanie).length
  const zi = formatZi(rulare, locale)
  const info = (
    <Pill tip="ok" title={t('campanii.comun.info_rulare_tooltip')}>
      {t('campanii.comun.info_rulare', { data: zi })}
    </Pill>
  )
  const filtre = (
    <>
      <label className="f">
        {t('campanii.comun.banca')}
        <Select value={banca} onChange={(v: string) => schimba('banca', v)} style={{ width: 185 }} popupMatchSelectWidth={false}
          options={[
            { value: '', label: t('campanii.comun.toate_bancile') },
            ...banci.map((b) => ({ value: b, label: `${nume(b)} (${num(pe[b], locale, 0)})` })),
          ]} />
      </label>
      <label className="f">
        {t('campanii.comun.cauta')}
        <Input className="cauta" type="search" allowClear placeholder={t('campanii.comun.cauta_in_titlu')}
          value={cauta} onChange={(e) => setCauta(e.target.value)} />
      </label>
      <Checkbox className="bifa" checked={doar} onChange={(e) => schimba('campanie', e.target.checked ? '1' : '')}>
        {t('campanii.comunicate.filtru.doar_campanie')}
      </Checkbox>
    </>
  )

  const n = lista.length
  const pagina = lista.slice(off, off + PE_PAGINA)
  return (
    <>
      <BaraSectiune taburi={taburi} info={info} filtre={filtre} />
      <Banda
        cifre={[
          { n: num(com.length, locale, 0), eticheta: t('campanii.comunicate.banda.comunicate') },
          { n: num(banci.length, locale, 0), eticheta: t('campanii.comunicate.banda.banci') },
          { n: num(nCamp, locale, 0), eticheta: t('campanii.comunicate.banda.marcate'), titlu: t('campanii.comunicate.banda.marcate_tooltip') },
        ]}
        chipuri={banci.length ? banci.map((b) => (
          <Chip key={b} slug={b} m={m} n={num(pe[b], locale, 0)} activ={banca === b}
            onClick={() => schimba('banca', banca === b ? '' : b)}
            titlu={t(pe[b] === 1 ? 'campanii.comunicate.chip_tooltip_1' : 'campanii.comunicate.chip_tooltip', { n: num(pe[b], locale, 0) })} />
        )) : undefined}
      />
      <section className="cm-sec">
        <p className="note" style={{ margin: '0 0 10px', maxWidth: 'none' }}>
          <T k={n === 1 ? 'campanii.comunicate.rezumat_1' : 'campanii.comunicate.rezumat_n'} params={{
            n: num(n, locale, 0),
            n_campanie: num(lista.filter((r) => r.e_campanie).length, locale, 0),
            n_fara_data: num(lista.filter((r) => !r.data_publicarii).length, locale, 0),
          }} />
        </p>
        {n ? (
          <>
            <Tabel
              randuri={pagina}
              cheieRand={(r) => String(r.id ?? r.url)}
              // Libra marcată, dar nefixată sus: lista e în ordinea datei
              clasaRand={(r) => (r.banca === 'libra' ? 'libra' : '')}
              coloane={[
                { cheie: 'banca', cap: t('campanii.comun.banca'), td: () => ({ className: 'cs-nowrap' }), val: (r) => <EtichetaBanca slug={r.banca} m={m} fisa tag /> },
                { cheie: 'data', cap: t('campanii.comun.col_data'),
                  td: (r) => ({
                    className: 'mono cs-nowrap',
                    title: r.data_din
                      ? DATA_DIN[r.data_din] ? t(DATA_DIN[r.data_din]!) : t('campanii.comunicate.tooltip_data.alta', { sursa: r.data_din })
                      : t('campanii.comunicate.tooltip_data.lipsa'),
                  }),
                  val: (r) => (r.data_publicarii ? formatZi(r.data_publicarii, locale) : '—') },
                { cheie: 'titlu', cap: t('campanii.comun.col_titlu'),
                  val: (r) => (
                    <a href={r.url ?? undefined} target="_blank" rel="noopener noreferrer"
                      title={r.titlu_din === 'url' ? t('campanii.comunicate.tooltip_titlu_din_adresa', { url: r.url ?? '' }) : r.url ?? ''}>
                      {r.titlu || r.url} ↗
                    </a>
                  ) },
                { cheie: 'campanie', cap: t('campanii.comunicate.col_campanie'), td: () => ({ className: 'cs-nowrap' }),
                  val: (r) => (r.e_campanie
                    ? <Pill tip="ok" title={t('campanii.comunicate.pill_campanie_tooltip', { potrivire: r.e_campanie_potrivire || '' })}>{t('campanii.comunicate.pill_campanie')}</Pill>
                    : null) },
              ]}
            />
            <Paginare total={n} offset={off} limit={PE_PAGINA} onChange={(o) => setPag({ semn, off: o })} />
          </>
        ) : (
          <p className="note">{t('campanii.comunicate.gol')}</p>
        )}
        <Despre>
          <T k="campanii.comunicate.despre.p1" params={{ data: zi }} />
          <T k="campanii.comunicate.despre.p2" />
        </Despre>
        {subsol}
      </section>
    </>
  )
}

