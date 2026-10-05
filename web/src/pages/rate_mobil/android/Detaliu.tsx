import { useState, type ReactNode } from 'react'
import { Button, Collapse, Drawer, Input, Segmented } from 'antd'
import type { AplicatieAndroid, BiblioteciAndroid, TextEcranAndroid } from '@mcc/shared'
import { useBiblioteciAndroid } from '../../../api/android'
import type { Meta } from '../../../api/meta'
import { Pill } from '../../../components/comune'
import { Tabel } from '../../../components/Tabel'
import { T, useLang, type DictKey } from '../../../i18n'
import { faraDiacritice, formatZi, num } from '../../../util/format'
import { Captura } from './comune'
import { categorii, cheie, decodeaza, eticheta, grupPermisiune, GRUPURI_PERMISIUNI, permScurt, TIPURI_PROFIL, type Index } from './model'
import { ListaSchimbari } from './Schimbari'

/**
 * Detaliul unei aplicații, în același sertar ca dovezile din 2.1 și capturile iOS
 * (`Sertar` din components/ e legat de /api/celula, deci nu se potrivește aici).
 * Tot ce știm despre aplicație, pe grupe pliate: BT Pay are 211 biblioteci, Revolut
 * 191 de valori în profilul tehnic — deschise toate, sertarul ar avea mii de pixeli.
 */
export default function Detaliu({ pachet, ix, m, onClose }: { pachet: string | null; ix: Index; m: Meta; onClose: () => void }) {
  const { t } = useLang()
  const a = pachet ? ix.app[pachet] : undefined
  const titlu = a ? `${m.nume[a.banca] ?? a.banca} · ${a.aplicatie}` : ''
  return (
    <Drawer open={!!a} onClose={onClose} width="min(880px, 94vw)" title={<span className="sertar-titlu">{titlu}</span>} closeIcon={null}
      extra={<Button onClick={onClose}>{t('sertar.inchide')}</Button>} destroyOnClose>
      {a && <Corp a={a} ix={ix} />}
    </Drawer>
  )
}

/** Capul unei grupe: numele, o precizare (versiunea) și câte elemente are. */
function Cap({ nume, extra, n }: { nume: string; extra?: string | null; n: number | null }) {
  const { locale } = useLang()
  return (
    <div className="g-cap">
      <span className="gn">{nume}</span>
      <span className="gi">{extra ?? ''}</span>
      <span className="gc">{num(n, locale, 0)}</span>
    </div>
  )
}

function Corp({ a, ix }: { a: AplicatieAndroid; ix: Index }) {
  const { t, locale } = useLang()
  // bibliotecile se cer la deschiderea sertarului, nu cu restul paginii (3.644 de rânduri în total)
  const bib = useBiblioteciAndroid(a.package)
  const nr = (v: number | null | undefined) => num(v, locale, 0)
  const versiuni = ix.versiuni[a.package] ?? []
  const ultima = ix.ultima[a.package] ?? null
  const perm = ix.perm[a.package] ?? []
  const trk = ix.trackere[a.package] ?? []
  const profil = ix.profil[a.package] ?? []
  const sch = ix.schimbari[a.package] ?? []
  const texte = ix.texte[a.package] ?? []
  const note = ix.note[a.package] ?? []

  // permisiunile sensibile întâi, în ordinea coloanelor din matrice; restul alfabetic
  const ordine = (p: string) => {
    const g = grupPermisiune(p)
    return g ? GRUPURI_PERMISIUNI.indexOf(g) : GRUPURI_PERMISIUNI.length
  }
  const permOrdonate = perm.slice().sort((x, y) => ordine(x) - ordine(y) || x.localeCompare(y))

  const tipuri = [...TIPURI_PROFIL, ...[...new Set(profil.map((p) => p.tip))].filter((x) => !TIPURI_PROFIL.includes(x))]
    .map((tip) => [tip, profil.filter((p) => p.tip === tip).map((p) => p.valoare)] as const)
    .filter(([, vs]) => vs.length)

  const fapte: [string, ReactNode][] = [
    [t('mobil.android_d_pachet'), <span className="mono">{a.package}</span>],
    [t('mobil.android_col_rol'), eticheta(t, 'rol', a.rol)],
    [t('mobil.android_framework'), <>{eticheta(t, 'fw', a.framework)} · {t('mobil.android_platforma', { p: eticheta(t, 'plat', a.platforma_tehnica) })}</>],
    [t('mobil.android_d_versiunea_noua'), <span className="mono">{a.versiune_cea_mai_noua ?? '—'}</span>],
    [t('mobil.android_d_versiunea_analizata'), <span className="mono">{a.versiune_analizata ?? '—'}</span>],
    [t('mobil.android_d_sdk'), <span className="mono">{nr(a.min_sdk)} → {nr(a.target_sdk)}</span>],
    [t('mobil.android_col_captura'), <Captura v={a.captura} />],
    [t('mobil.android_d_texte_apk'), <span className="mono">{nr(a.nr_texte_in_apk)}</span>],
    [t('mobil.android_col_data'), <span className="mono">{a.data_extragere ? formatZi(a.data_extragere, locale) : '—'}</span>],
  ]

  const items = [
    {
      key: 'versiuni',
      label: <Cap nume={t('mobil.android_d_versiuni')} n={versiuni.length} />,
      children: (
        <div className="an-corp">
          <Tabel
            randuri={versiuni}
            cheieRand={(v) => v.version_name}
            coloane={[
              { cheie: 'v', cap: t('mobil.versiune'), td: () => ({ className: 'mono an-nowrap' }),
                val: (v) => (
                  <>
                    {v.version_name}{' '}
                    {v.version_name === ultima && <Pill>{t('mobil.android_d_cea_mai_noua')}</Pill>}
                    {v.version_name === a.versiune_analizata && <Pill>{t('mobil.android_d_analizata')}</Pill>}
                  </>
                ) },
              { cheie: 'cod', cap: t('mobil.android_d_cod'), num: true, val: (v) => (v.version_code ?? '—') },
              { cheie: 'data', cap: t('mobil.android_col_data'), td: () => ({ className: 'mono an-nowrap' }),
                val: (v) => (v.data_extragere ? formatZi(v.data_extragere, locale) : '—') },
              { cheie: 'sdk', cap: t('mobil.android_d_sdk'), td: () => ({ className: 'mono an-nowrap' }), val: (v) => `${nr(v.min_sdk)} → ${nr(v.target_sdk)}` },
              { cheie: 'perm', cap: t('mobil.android_col_permisiuni'), num: true, val: (v) => nr(v.nr_permisiuni) },
              { cheie: 'trk', cap: t('mobil.android_col_trackere'), num: true, val: (v) => nr(v.nr_trackere) },
              { cheie: 'bib', cap: t('mobil.android_col_biblioteci'), num: true, val: (v) => nr(v.nr_biblioteci) },
              { cheie: 'so', cap: t('mobil.android_col_native'), num: true, val: (v) => nr(v.nr_librarii_native) },
            ]}
          />
        </div>
      ),
    },
    ...(versiuni.length > 1
      ? [{
          key: 'schimbari',
          label: <Cap nume={t('mobil.android_s.schimbari')} n={sch.length} />,
          children: <div className="an-corp"><ListaSchimbari randuri={sch} /></div>,
        }]
      : []),
    {
      key: 'permisiuni',
      label: <Cap nume={t('mobil.android_col_permisiuni')} extra={ultima} n={perm.length} />,
      children: (
        <div className="an-corp">
          <p className="note an-d-sub">{t('mobil.android_d_permisiuni_sub')}</p>
          <ul className="an-lista an-col">
            {permOrdonate.map((p) => {
              const g = grupPermisiune(p)
              return (
                <li key={p} className={g ? undefined : 'gri'}>
                  {permScurt(p)}{g && <> <Pill>{t(`mobil.android_perm.${g.k}` as DictKey)}</Pill></>}
                </li>
              )
            })}
          </ul>
        </div>
      ),
    },
    {
      key: 'trackere',
      label: <Cap nume={t('mobil.android_col_trackere')} extra={ultima} n={trk.length} />,
      children: (
        <div className="an-corp">
          {trk.length ? (
            <ul className="an-lista an-trk">
              {trk.map((x) => (
                <li key={x.tracker}>
                  <b>{x.tracker}</b>
                  {categorii(x, t) && <span className="gri"> · {categorii(x, t)}</span>}
                  {x.dovada && <span className="sub mono">{t('mobil.android_gasit_ca', { dovada: x.dovada })}</span>}
                </li>
              ))}
            </ul>
          ) : <p className="note">{t('mobil.android_niciun_tracker')}</p>}
        </div>
      ),
    },
    {
      key: 'profil',
      label: <Cap nume={t('mobil.android_d_profil')} extra={a.versiune_analizata} n={profil.length} />,
      children: (
        <div className="an-corp">
          {tipuri.length ? tipuri.map(([tip, vs]) => {
            const k = cheie('tip_d', tip)
            return (
              <div key={tip} className="an-profil">
                <h4 className="mb-h4">{eticheta(t, 'tip', tip)} · {nr(vs.length)}</h4>
                {k && <p className="note an-d-sub">{t(k)}</p>}
                <ul className="an-lista an-col">
                  {vs.map((v, i) => <li key={i}>{v.trim() || <span className="gri">{t('mobil.android_d_gol')}</span>}</li>)}
                </ul>
              </div>
            )
          }) : <p className="note">{t('mobil.android_d_fara_profil')}</p>}
        </div>
      ),
    },
    {
      key: 'texte',
      label: <Cap nume={t('mobil.android_d_texte')} extra={a.versiune_analizata} n={texte.length} />,
      children: <div className="an-corp"><Texte texte={texte} /></div>,
    },
    {
      key: 'biblioteci',
      // în cap, cifra versiunii celei mai noi (ca în tabel), nu suma pe toate versiunile: Libra avea 148, nu 296
      label: <Cap nume={t('mobil.android_col_biblioteci')} extra={ultima}
        n={bib.data ? bib.data.filter((b) => !ultima || b.version_name === ultima).length : a.nr_biblioteci} />,
      children: (
        <div className="an-corp">
          {bib.isLoading && <p className="note">{t('comun.se_incarca')}</p>}
          {bib.error && <p className="note" style={{ color: 'var(--warn)' }}><T k="comun.eroare" params={{ mesaj: (bib.error as Error).message }} /></p>}
          {bib.data && <Biblioteci date={bib.data} ultima={ultima} />}
        </div>
      ),
    },
  ]

  return (
    <>
      <dl className="an-fapte">
        {fapte.map(([e, v]) => (
          <div key={e}>
            <dt>{e}</dt>
            <dd>{v}</dd>
          </div>
        ))}
      </dl>
      {/* notele lui Nicolae sunt observații din teren: rămân cum au fost scrise */}
      {note.map((n, i) => <div key={i} className="callout an-nota"><b>{t('mobil.android_d_nota')}</b> {n}</div>)}
      <Collapse className="grupe" defaultActiveKey={['versiuni', 'schimbari']} items={items} />
    </>
  )
}

/**
 * Textele citite de pe ecranele publice (fără cont), pe ecrane: întâi pornirea,
 * apoi parcurgerea. `pas` începe de la 0 în bază; aici ecranele se numără de la 1.
 */
function Texte({ texte }: { texte: TextEcranAndroid[] }) {
  const { t, locale } = useLang()
  if (!texte.length) return <p className="note">{t('mobil.android_d_fara_texte')}</p>
  const grupe = new Map<string, TextEcranAndroid[]>()
  for (const x of texte) {
    const k = `${x.sursa}|${x.pas ?? ''}|${x.data ?? ''}`
    if (!grupe.has(k)) grupe.set(k, [])
    grupe.get(k)!.push(x)
  }
  const rang = (s: string) => (s === 'pornire' ? 0 : 1)
  const lista = [...grupe.values()].sort((x, y) => rang(x[0]!.sursa) - rang(y[0]!.sursa) || (x[0]!.pas ?? 0) - (y[0]!.pas ?? 0))
  return (
    <>
      <p className="note an-d-sub">{t('mobil.android_d_texte_sub')}</p>
      {lista.map((rs) => {
        const x = rs[0]!
        const parti = [
          eticheta(t, 'text_sursa', x.sursa),
          x.sursa === 'parcurgere' && x.pas !== null ? t('mobil.android_d_ecranul', { n: x.pas + 1 }) : '',
          x.data ? formatZi(x.data, locale) : '',
        ].filter(Boolean)
        return (
          <div key={`${x.sursa}|${x.pas}|${x.data}`} className="an-ecran">
            <h4 className="mb-h4">{parti.join(' · ')}</h4>
            {rs.map((r, i) => <div key={i} className="an-text">{decodeaza(r.text)}</div>)}
          </div>
        )
      })}
    </>
  )
}

/** Bibliotecile versiunii alese (implicit cea mai nouă), cu căutare: BT Pay are 211. */
function Biblioteci({ date, ultima }: { date: BiblioteciAndroid; ultima: string | null }) {
  const { t, tn } = useLang()
  const [cauta, setCauta] = useState('')
  const versiuni = [...new Set(date.map((b) => b.version_name))]
  const [ver, setVer] = useState<string>(ultima && versiuni.includes(ultima) ? ultima : versiuni[0] ?? '')
  if (!date.length) return <p className="note">{t('mobil.android_d_fara_biblioteci')}</p>
  const c = faraDiacritice(cauta.trim())
  const l = date.filter((b) => b.version_name === ver && (!c || faraDiacritice(`${b.biblioteca} ${b.versiune ?? ''}`).includes(c)))
  return (
    <>
      <div className="s-bara">
        {versiuni.length > 1 && <Segmented<string> value={ver} onChange={setVer} options={versiuni} />}
        <Input className="cauta" allowClear placeholder={t('mobil.android_d_cauta_biblioteca')} value={cauta} onChange={(e) => setCauta(e.target.value)}
          style={{ width: 240 }} />
        <span className="note">{tn('mobil.android_n_biblioteci', l.length)}</span>
      </div>
      <ul className="an-lista an-col an-cutie">
        {l.map((b) => (
          <li key={b.biblioteca}>
            {b.biblioteca}{b.versiune && <span className="gri"> {b.versiune}</span>}
          </li>
        ))}
      </ul>
    </>
  )
}
