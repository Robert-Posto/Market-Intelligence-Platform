import { useMemo, useState, type ComponentType } from 'react'
import { Input, Segmented, Select } from 'antd'
import { useSearchParams } from 'react-router-dom'
import { useAndroid } from '../../../api/android'
import { useMeta } from '../../../api/meta'
import { Eroare, SeIncarca } from '../../../components/comune'
import { useLang, type DictKey } from '../../../i18n'
import { faraDiacritice, num } from '../../../util/format'
import Aplicatii from './Aplicatii'
import Detaliu from './Detaliu'
import Functionalitati from './Functionalitati'
import { eticheta, indexeaza, sePotriveste, type PropsSectiune, type Sectiune } from './model'
import Portofele from './Portofele'
import Schimbari from './Schimbari'
import TrackerePermisiuni from './TrackerePermisiuni'
import '../../../styles/android.css'

const SECTIUNI: { k: Sectiune; nume: DictKey; C: ComponentType<PropsSectiune> }[] = [
  { k: 'aplicatii', nume: 'mobil.android_s.aplicatii', C: Aplicatii },
  { k: 'functionalitati', nume: 'mobil.android_s.functionalitati', C: Functionalitati },
  { k: 'trackere', nume: 'mobil.android_s.trackere', C: TrackerePermisiuni },
  { k: 'portofele', nume: 'mobil.android_s.portofele', C: Portofele },
  { k: 'schimbari', nume: 'mobil.android_s.schimbari', C: Schimbari },
]

/**
 * 2.3, Android: analiza statică a APK-urilor (pachetul lui Nicolae din 05.10.2026),
 * nu pagina din Google Play — fără notă, recenzii sau capturi de magazin. Cinci
 * secțiuni pe un comutator, ca la 2.4 (o singură secțiune pe ecran, aleasă în
 * adresă: `?platforma=android&s=portofele`); filtrele din bară se aplică tuturor.
 * Clic pe o aplicație, în orice secțiune, deschide detaliul ei.
 */
export default function Android() {
  const { t, tn, locale } = useLang()
  const [sp, setSp] = useSearchParams()
  const meta = useMeta()
  const q = useAndroid()
  const [cauta, setCauta] = useState('')
  const [deschis, setDeschis] = useState<string | null>(null)
  const ix = useMemo(() => (q.data ? indexeaza(q.data) : null), [q.data])

  const err = meta.error ?? q.error
  if (err) return <Eroare e={err} />
  if (!meta.data || !q.data || !ix) return <SeIncarca />
  const m = meta.data
  const d = q.data

  if (!d.aplicatii.length) {
    return (
      <section>
        <div className="gol-stare">
          <b>{t('mobil.android_gol_titlu')}</b>
          {t('mobil.android_gol')}
        </div>
      </section>
    )
  }

  const sec = SECTIUNI.find((x) => x.k === sp.get('s')) ?? SECTIUNI[0]!
  const fw = sp.get('fw') || ''
  // ca `schimba` din 2.1: parametrul gol iese din adresă, restul (platforma, secțiunea) rămâne
  const schimba = (k: string, v: string) =>
    setSp((p) => {
      const n = new URLSearchParams(p)
      if (v) n.set(k, v)
      else n.delete(k)
      return n
    })

  const frameworkuri = [...new Set(d.aplicatii.map((a) => a.framework ?? ''))].filter(Boolean).sort((a, b) => a.localeCompare(b, locale))
  const c = faraDiacritice(cauta.trim())
  const apps = d.aplicatii.filter((a) => (!fw || a.framework === fw) && sePotriveste(a, m, c))
  const filtrat = !!fw || !!c

  return (
    <>
      <div className="bara-fixa an-bara">
        <div className="filtre">
          <Segmented<Sectiune> value={sec.k} onChange={(v) => schimba('s', v)}
            options={SECTIUNI.map(({ k, nume }) => ({ value: k, label: t(nume) }))} />
          <label className="f">{t('mobil.android_framework')}
            <Select value={fw} onChange={(v: string) => schimba('fw', v)} style={{ minWidth: 170 }} popupMatchSelectWidth={false}
              options={[
                { value: '', label: t('mobil.toate') },
                ...frameworkuri.map((x) => ({
                  value: x,
                  label: `${eticheta(t, 'fw', x)} (${num(d.aplicatii.filter((a) => a.framework === x).length, locale, 0)})`,
                })),
              ]} />
          </label>
          <label className="f">{t('mobil.android_cauta')}
            <Input className="cauta" allowClear placeholder={t('mobil.android_cauta_ph')} value={cauta} onChange={(e) => setCauta(e.target.value)} />
          </label>
          {filtrat && <span className="note an-n">{tn('mobil.android_n_aplicatii', apps.length)}</span>}
        </div>
      </div>
      <sec.C key={sec.k} ix={ix} apps={apps} m={m} deschide={setDeschis} />
      <Detaliu pachet={deschis} ix={ix} m={m} onClose={() => setDeschis(null)} />
    </>
  )
}
