import { useState, type ReactNode } from 'react'
import { Button, Tooltip } from 'antd'
import type { AplicatieAndroid } from '@mcc/shared'
import type { Meta } from '../../../api/meta'
import { Despre, EtichetaBanca, Pill } from '../../../components/comune'
import { T, useLang } from '../../../i18n'
import { formatZi, num } from '../../../util/format'
import { cheie, eticheta, type Index } from './model'

/**
 * Banca (sigla, numele, „noi” la Libra) și aplicația dedesubt: BRD și Nexent au
 * câte două aplicații, deci numele băncii singur nu spune despre care e vorba.
 */
export function CelulaApp({ a, m, versiune }: { a: AplicatieAndroid; m: Meta; versiune?: string | null }) {
  return (
    <>
      <EtichetaBanca slug={a.banca} m={m} fisa tag />
      <span className="sub an-sub">
        {a.aplicatie}
        {versiune && <span className="mono an-ver"> · {versiune}</span>}
      </span>
    </>
  )
}

/**
 * Protecția la captură, din ce s-a întâmplat la pornirea pe telefonul de test.
 * `simplu`: text care se poate rupe, nu pastilă (în tabel, „refuză telefonul de
 * test” ținea coloana la 187 px).
 */
export function Captura({ v, simplu }: { v: string | null; simplu?: boolean }) {
  const { t } = useLang()
  if (!v) return <span className="gri">—</span>
  const k = cheie('captura_d', v)
  const et = eticheta(t, 'captura', v)
  if (simplu) return <Tooltip title={k ? t(k) : undefined}><span className="an-captura">{et}</span></Tooltip>
  return <Pill title={k ? t(k) : undefined}>{et}</Pill>
}

/** Verdictul unei funcționalități: formă și culoare, ca să se citească și fără culori. */
const SIMBOL: Record<string, string> = { sigur: '✓', probabil: '✓', absent: '–', neconcludent: '?' }
export function Verdict({ v }: { v: string }) {
  return <span className={`an-v ${v}`}>{SIMBOL[v] ?? '·'}</span>
}

/** Bifa din matricele de permisiuni și portofele; golul e „—”, ca în restul tabelelor. */
export function Bifa({ da, children }: { da: boolean; children?: ReactNode }) {
  return da ? <span className="an-da">✓{children}</span> : <span className="gri">—</span>
}

/** Liste lungi (38 de biblioteci actualizate la Raiffeisen 4.80): primele câteva, restul la cerere. */
export function ListaScurta({ items, max = 8, render }: { items: string[]; max?: number; render?: (x: string) => ReactNode }) {
  const { t } = useLang()
  const [toate, setToate] = useState(false)
  if (!items.length) return <span className="gri">—</span>
  const vizibile = toate ? items : items.slice(0, max)
  return (
    <>
      <ul className="an-lista">
        {vizibile.map((x, i) => <li key={i}>{render ? render(x) : x}</li>)}
      </ul>
      {items.length > max && (
        <Button size="small" type="link" className="an-mai" onClick={(e) => { e.stopPropagation(); setToate(!toate) }}>
          {toate ? t('mobil.android_mai_putine') : t('mobil.android_inca', { n: items.length - max })}
        </Button>
      )}
    </>
  )
}

/**
 * „Despre date”, sub fiecare secțiune. Cifrele se socotesc din răspuns, pe toate
 * aplicațiile (nu pe filtru): pe 05.10.2026 erau 24 de aplicații de la 22 de bănci,
 * 14 web, iar Libra, Raiffeisen și Revolut aveau o versiune mai nouă decât cea analizată.
 */
export function DespreDate({ ix, m }: { ix: Index; m: Meta }) {
  const { t, locale } = useLang()
  const toate = ix.toate
  const cuApp = new Set(toate.map((a) => a.banca))
  const banci = Object.keys(m.nume)
  const fara = banci.filter((b) => !cuApp.has(b)).map((b) => m.nume[b] ?? b).sort((a, b) => a.localeCompare(b, locale))
  // „web” ca în pachet: tot ce nu e nativ (Capacitor, React Native, Cordova, Flutter) își ține textul pe server
  const web = toate.filter((a) => a.framework && a.framework !== 'nativ')
  const peFw = new Map<string, number>()
  for (const a of web) peFw.set(a.framework!, (peFw.get(a.framework!) ?? 0) + 1)
  const detaliu = [...peFw].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], locale)).map(([f, n]) => `${f} ${n}`).join(', ')
  const difera = toate.filter((a) => a.versiune_analizata && a.versiune_cea_mai_noua && a.versiune_analizata !== a.versiune_cea_mai_noua)
  return (
    <Despre>
      <T k="mobil.android_despre_sursa" />
      {ix.incarcat_la && <> <T k="mobil.android_despre_incarcat" params={{ data: formatZi(ix.incarcat_la, locale) }} /></>}
      <br />
      {difera.length
        ? <T k="mobil.android_despre_versiuni" params={{
            lista: difera.map((a) => `${a.aplicatie} ${a.versiune_analizata} → ${a.versiune_cea_mai_noua}`).join(', '),
          }} />
        : <T k="mobil.android_despre_versiuni_la_fel" />}
      <br />
      <T k="mobil.android_despre_web" params={{ web: num(web.length, locale, 0), n: num(toate.length, locale, 0), detaliu }} />
      <br />
      {fara.length > 0 && (
        <><T k="mobil.android_despre_fara" params={{ n: num(fara.length, locale, 0), total: num(banci.length, locale, 0), banci: fara.join(', ') }} />{' '}</>
      )}
      {t('mobil.android_despre_play')}
    </Despre>
  )
}

/** Explicația secțiunii și „Despre date”, pe același rând până se deschid (ca `.cs-note` la 2.4). */
export function Note({ ix, m, children }: { ix: Index; m: Meta; children?: ReactNode }) {
  const { t } = useLang()
  return (
    <div className="an-note">
      {children && <Despre eticheta={t('mobil.android_cum_se_citeste')}>{children}</Despre>}
      <DespreDate ix={ix} m={m} />
    </div>
  )
}
