import { useEffect, useMemo, useState } from 'react'
import { Button, Checkbox, Segmented, Tooltip } from 'antd'
import { Link, useSearchParams } from 'react-router-dom'
import type { ReteaBanca, ReteaPunct } from '@mcc/shared'
import { useMeta } from '../api/meta'
import { useLocatii } from '../api/retea'
import { Eroare } from '../components/comune'
import { T, useLang } from '../i18n'
import { num } from '../util/format'
import { pregatesteSigle, type Sigle, type TipLocatie } from './harta/desen'
import Mapa from './harta/Mapa'
import '../styles/retea.css'

const FARA_BANCI: ReteaBanca[] = []
const FARA_PUNCTE: ReteaPunct[] = []
const FARA_LOGO: Record<string, string> = {}

/**
 * Harta sucursalelor și ATM-urilor, pe tot ecranul, fără meniul aplicației
 * (ca harta.html din aplicația veche). `#/harta?banca=bcr,ing` pornește cu
 * doar acele bănci bifate și centrat pe punctele lor; altfel, toate.
 */
export default function Harta() {
  const { t, locale } = useLang()
  const [sp] = useSearchParams()
  const param = sp.get('banca') || ''
  const q = useLocatii()
  const meta = useMeta()
  const [tip, setTip] = useState<'' | TipLocatie>('')
  // bifele utilizatorului țin doar cât rămâne aceeași adresă: alt `?banca=` pornește din nou din link
  const [alegere, setAlegere] = useState<{ param: string; banci: Set<string> } | null>(null)
  const [sigle, setSigle] = useState<Sigle | null>(null)
  const [nrZona, setNrZona] = useState<number | null>(null)

  useEffect(() => {
    const inainte = document.title
    document.title = t('harta.titlu_pagina')
    return () => { document.title = inainte }
  }, [t])

  const banci = q.data?.banci ?? FARA_BANCI
  const toate = q.data?.puncte ?? FARA_PUNCTE
  const logo = meta.data?.logo ?? FARA_LOGO
  const dinLink = useMemo(() => param.split(',').filter((s) => banci.some((b) => b.slug === s)), [param, banci])
  const implicite = useMemo(() => new Set(dinLink.length ? dinLink : banci.map((b) => b.slug)), [dinLink, banci])
  const selectate = alegere && alegere.param === param ? alegere.banci : implicite
  const alege = (s: Set<string>) => setAlegere({ param, banci: s })
  const vizibile = useMemo(
    () => toate.filter((p) => selectate.has(p.banca) && (!tip || p.tip === tip)),
    [toate, selectate, tip],
  )

  useEffect(() => {
    if (!q.data || !meta.data) return
    let anulat = false
    void pregatesteSigle(q.data.banci.map((b) => b.slug), meta.data.logo).then((s) => { if (!anulat) setSigle(s) })
    return () => { anulat = true }
  }, [q.data, meta.data])

  const suc = vizibile.filter((p) => p.tip === 'sucursala').length
  const proprii = vizibile.filter((p) => p.tip === 'atm' && p.retea !== 'partener').length
  const partenere = vizibile.filter((p) => p.retea === 'partener').length
  const cuNota = vizibile.filter((p) => p.rating !== null && p.rating !== undefined)
  const medie = cuNota.length ? cuNota.reduce((s, p) => s + Number(p.rating), 0) / cuNota.length : null
  const detaliu = [
    t('harta.stat.detaliu', { sucursale: num(suc, locale, 0), atm_proprii: num(proprii, locale, 0) }),
    partenere ? t('harta.stat.detaliu_partenere', { partenere: num(partenere, locale, 0) }) : '',
    medie ? t('harta.stat.detaliu_nota_medie', { medie: medie.toLocaleString(locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }) : '',
  ].filter(Boolean).join(' · ')
  const zona = !vizibile.length || nrZona === null ? ''
    : nrZona ? t('harta.zona.vizibile', { n: num(nrZona, locale, 0) }) : t('harta.zona.niciuna')
  const unaAleasa = selectate.size === 1 ? [...selectate][0]! : null

  return (
    <div className="ht-pagina">
      <header className="ht-antet">
        <h1>{t('harta.antet.titlu')}</h1>
        <div className="ht-sub">
          <T k="harta.antet.surse" /> · <Link to="/overview">{t('harta.antet.inapoi')}</Link>
        </div>
      </header>
      <div className="ht-layout">
        <aside className="ht-panou">
          {q.error ? <Eroare e={q.error} /> : meta.error ? <Eroare e={meta.error} /> : (
            <div className="ht-stat">
              <b>{q.data ? num(vizibile.length, locale, 0) : '—'}</b>
              <span>{q.data ? detaliu : t('harta.stat.se_incarca')}</span>
              <span className="ht-nr-zona">{zona}</span>
            </div>
          )}

          <div className="ht-bloc">
            <h2>{t('harta.filtru_tip.titlu')}</h2>
            <Segmented<'' | TipLocatie>
              block
              className="ht-segment"
              value={tip}
              onChange={setTip}
              options={[
                { value: '', label: t('harta.toate') },
                { value: 'sucursala', label: t('harta.filtru_tip.sucursale') },
                { value: 'atm', label: t('harta.filtru_tip.atm') },
              ]}
            />
            {/* codurile din legendă sunt exemple de pe hartă (BT, Patria), nu text de tradus */}
            <div className="ht-legenda">
              <div className="ht-lg"><span className="ht-lg-suc">BT</span> <span><T k="harta.legenda.sucursala" /></span></div>
              <div className="ht-lg"><span className="ht-lg-atm">BT</span> <span><T k="harta.legenda.atm_propriu" /></span></div>
              <div className="ht-lg"><span className="ht-lg-atm" style={{ opacity: 0.45 }}>PAT</span> <span><T k="harta.legenda.atm_partener" /></span></div>
              <div className="ht-lg"><span className="ht-grup" style={{ width: 30, height: 30, fontSize: 11 }}>42</span> <span><T k="harta.legenda.grup" /></span></div>
              <p className="ht-lg-nota"><T k="harta.legenda.carduri" /></p>
            </div>
          </div>

          <div className="ht-bloc">
            <h2>{t('harta.banci.titlu')} {q.data && <span className="ht-nr-banci">({selectate.size}/{banci.length})</span>}</h2>
            <div className="ht-butoane">
              <Button size="small" onClick={() => alege(new Set(banci.map((b) => b.slug)))}>{t('harta.toate')}</Button>
              <Button size="small" onClick={() => alege(new Set())}>{t('harta.banci.niciuna')}</Button>
            </div>
            <div className="ht-lista">
              {banci.map((b) => (
                <Checkbox
                  key={b.slug}
                  className="ht-rand"
                  checked={selectate.has(b.slug)}
                  onChange={(e) => {
                    const n = new Set(selectate)
                    if (e.target.checked) n.add(b.slug)
                    else n.delete(b.slug)
                    alege(n)
                  }}
                >
                  <span className="ht-bara" style={{ background: sigle?.culori[b.slug] ?? '#9aa7b4' }} />
                  {logo[b.slug] && <img className="ht-logo" src={logo[b.slug]} alt={b.nume} />}
                  <Tooltip title={b.nume} mouseEnterDelay={0.4}><span className="ht-nume">{b.nume}</span></Tooltip>
                  <span className="ht-n">{t('harta.lista_banci.numar', { sucursale: b.sucursale, atm: b.atm })}</span>
                </Checkbox>
              ))}
            </div>
          </div>

          <p className="ht-nota"><T k="harta.nota_acoperire" /></p>
        </aside>
        <Mapa
          banci={banci}
          vizibile={vizibile}
          toate={toate}
          sigle={sigle}
          logo={logo}
          culoareGrup={unaAleasa ? sigle?.culori[unaAleasa] ?? null : null}
          incadrare={dinLink.length ? param : null}
          onZona={setNrZona}
        />
      </div>
    </div>
  )
}
