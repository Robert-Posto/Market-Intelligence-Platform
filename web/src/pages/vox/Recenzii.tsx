import { useState, type ReactNode } from 'react'
import type { Aplicatii as AplicatiiT, BlocRecenzii, MagazinRecenzii } from '@mcc/shared'
import type { Meta } from '../../api/meta'
import { EtichetaBanca } from '../../components/comune'
import { useLang, type DictKey } from '../../i18n'
import { faraDiacritice, formatZi } from '../../util/format'
import { CardRecenzie } from '../rate_mobil/Recenzii'
import '../../styles/rate_mobil.css'

/**
 * Recenziile în Vox (app/vox.py, `_recenzii_raspuns`): așa cum le-au scris clienții, pe bancă și pe magazin. Primele 5 pe
 * magazin, cu „Arată toate”; textele de peste 400 de caractere se scurtează (în App Store, 45 trec de 500, cea mai lungă
 * are 1.811; 09.10.2026).
 */
const PRIMELE = 5
const LUNGIME = 400

/**
 * Cuvintele găsite, îngroșate cu aceeași regulă ca serverul (`vox.potriveste_recenzia`: fără diacritice, litere mici,
 * rădăcina e începutul cuvântului), ca o recenzie arătată să aibă mereu cuvântul îngroșat.
 */
function TextRecenzie({ text, cuvinte }: { text: string; cuvinte: string[] }) {
  const { t } = useLang()
  const [tot, setTot] = useState(false)
  const scurt = !tot && text.length > LUNGIME
  const vizibil = scurt ? `${text.slice(0, LUNGIME).trimEnd()}…` : text
  const radacini = cuvinte.map(faraDiacritice)
  const parti: ReactNode[] = []
  let ultim = 0
  if (radacini.length) {
    for (const m of vizibil.matchAll(/[\p{L}\p{N}]+/gu)) {
      if (radacini.some((c) => faraDiacritice(m[0]).startsWith(c))) {
        parti.push(vizibil.slice(ultim, m.index), <b key={m.index} className="vox-gasit">{m[0]}</b>)
        ultim = (m.index ?? 0) + m[0].length
      }
    }
  }
  parti.push(vizibil.slice(ultim))
  return (
    <>
      {parti}
      {scurt && <> <button type="button" className="vox-link" onClick={() => setTot(true)}>{t('vox.aplicatii.recenzii.mai_mult')}</button></>}
    </>
  )
}

function BlocMagazin({ k, mg, banca, m, cuvinte, cautat }: {
  k: 'play' | 'app_store'; mg: MagazinRecenzii; banca: string; m: Meta; cuvinte: string[]; cautat: string | null
}) {
  const { t, tn } = useLang()
  const [toate, setToate] = useState(false)
  const magazin = t(`vox.aplicatii.magazin.${k}` as DictKey)
  const vizibile = toate ? mg.recenzii : mg.recenzii.slice(0, PRIMELE)
  return (
    <div className="vox-rec-magazin">
      <span className="vox-segment-cap">
        {cautat
          ? tn('vox.aplicatii.recenzii.magazin_cautare', mg.recenzii.length, { magazin, din: mg.din, text: cautat })
          : t('vox.aplicatii.recenzii.magazin', { magazin, n: mg.din })}
      </span>
      {!mg.recenzii.length && !cautat && <p className="vox-nota"><span className="vox-punct gri" />{t('vox.aplicatii.recenzii.nimic')}</p>}
      {vizibile.map((r, i) => (
        <CardRecenzie key={`${r.data}-${i}`} banca={banca} m={m} nota={r.nota} data={r.data} versiune={r.versiune}
          magazin={magazin} text={r.text ? <TextRecenzie text={r.text} cuvinte={cuvinte} /> : null} raspuns={r.raspuns_banca}
          raspunsData={r.raspuns_data ?? null} />
      ))}
      {mg.recenzii.length > vizibile.length && (
        <button type="button" className="vox-link vox-clas-toate" onClick={() => setToate(true)}>
          {t('vox.clasament.arata_toate', { n: mg.recenzii.length })}
        </button>
      )}
    </div>
  )
}

function BlocBanca({ b, m, cuvinte, cautat }: { b: BlocRecenzii; m: Meta; cuvinte: string[]; cautat: string | null }) {
  const { t } = useLang()
  const potriviri = (b.play?.recenzii.length ?? 0) + (b.app_store?.recenzii.length ?? 0)
  const din = (b.play?.din ?? 0) + (b.app_store?.din ?? 0)
  return (
    <section className={b.evidentiata ? 'vox-rec-banca evidentiata' : 'vox-rec-banca'}>
      <div className="vox-rec-cap">
        <EtichetaBanca slug={b.banca} m={m} tag />
        {b.aplicatie && <span className="vox-meta">{b.aplicatie}</span>}
      </div>
      {b.fara_aplicatie
        ? <p className="vox-nota"><span className="vox-punct gri" />{t('vox.aplicatii.fara_apk')}</p>
        : cautat && potriviri === 0
          ? <p className="vox-nota"><span className="vox-punct" />{t('vox.aplicatii.recenzii.nimic_banca', { text: cautat, din, banca: m.nume[b.banca] ?? b.banca })}</p>
          : (
            <>
              {b.play
                ? <BlocMagazin k="play" mg={b.play} banca={b.banca} m={m} cuvinte={cuvinte} cautat={cautat} />
                : <p className="vox-nota"><span className="vox-punct gri" />{t('vox.aplicatii.play_lipsa')}</p>}
              {b.app_store && <BlocMagazin k="app_store" mg={b.app_store} banca={b.banca} m={m} cuvinte={cuvinte} cautat={cautat} />}
            </>
          )}
    </section>
  )
}

export default function Recenzii({ a, m }: { a: AplicatiiT; m: Meta }) {
  const { t, locale } = useLang()
  const blocuri = a.blocuri ?? []
  const cuvinte = a.cuvinte ?? []
  const cautat = a.text_cautat
  return (
    <>
      <div className="vox-clas-antet">
        <b>{cautat ? t('vox.aplicatii.recenzii.titlu_cautare', { text: cautat }) : t('vox.aplicatii.recenzii.titlu')}</b>
      </div>
      <p className="vox-nota"><span className="vox-punct gri" />
        {t('vox.aplicatii.recenzii.esantion', { data: a.play_la ? formatZi(a.play_la, locale) : '—' })}
      </p>
      {!blocuri.length && cautat && (
        <p className="vox-nota"><span className="vox-punct" />{t('vox.aplicatii.recenzii.nimic_nicaieri', { text: cautat })}</p>
      )}
      {blocuri.map((b) => <BlocBanca key={b.banca} b={b} m={m} cuvinte={cuvinte} cautat={cautat} />)}
      {!!a.fara_potriviri && !!blocuri.length && cautat && (
        <p className="vox-nota"><span className="vox-punct gri" />{t('vox.aplicatii.recenzii.fara_potriviri', { n: a.fara_potriviri, text: cautat })}</p>
      )}
    </>
  )
}
