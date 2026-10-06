import { useRef } from 'react'
import { Modal } from 'antd'
import type { ValoareLibra } from '@mcc/shared'
import { linkDocument } from '../../components/Dovezi'
import { etNume } from '../../components/valori'
import { T, useLang, type DictKey } from '../../i18n'
import { formatZi, num } from '../../util/format'
import Iconita, { Eticheta } from './Iconita'
import { SCURT, conditie, etichete, valoare } from './logica'

/**
 * Dovada unei valori: cifra, scenariul, citatul și linkul spre document.
 * Modal AntD în locul celui scris de mână în Next.js: aceeași apariție, plus
 * focus și Escape gratuit. Un PDF se deschide în vizualizatorul propriu
 * (`linkDocument`), cu citatul căutat în document: serverul nu trimite pagina.
 */
export default function ModalDovada({ v, inchide }: { v: ValoareLibra | null; inchide: () => void }) {
  const { t, tn, locale } = useLang()
  // ultima valoare rămâne în fereastră cât durează animația de închidere; altfel se golea înainte să dispară
  const ultima = useRef(v)
  if (v) ultima.current = v
  const a = ultima.current
  return (
    <Modal open={!!v} onCancel={inchide} footer={null} width={620} destroyOnHidden
      title={a && <span className="pl-modal-t">{SCURT[a.banca] ?? a.banca} · {etNume(a.camp, t)}</span>}>
      {a && <Corp a={a} t={t} tn={tn} locale={locale} />}
    </Modal>
  )
}

function Corp({ a, t, tn, locale }: { a: ValoareLibra } & Pick<ReturnType<typeof useLang>, 't' | 'tn' | 'locale'>) {
  const sc = a.scenariu ?? {}
  const e = etichete(a.scenariu, a, t, tn, locale)
  const cond = conditie(a)
  const doc = a.url ?? a.link ?? ''
  const pdf = a.tip === 'pdf'
  const href = pdf ? linkDocument(doc, 1, a.citat ?? '') : (a.link ?? doc)
  const laParagraf = !pdf && a.link && a.link !== a.url
  return (
    <div className="pl-modal">
      {a.denumire_banca && <p className="note" style={{ marginTop: 0 }}>{a.denumire_banca}</p>}
      <p className="pl-modal-val"><b>{valoare(a, t, locale)}</b></p>
      {e.length > 0 && <p className="pl-sc-mare">{e.map((x, i) => <Eticheta key={i} e={x} />)}</p>}
      {cond && <p><T k="pl.m.conditie" params={{ c: cond }} /></p>}
      {sc.referinta && (
        <p className="pl-ref-linie">
          <Iconita n="tinta" />
          <span>
            <T k="pl.m.ref" params={{
              nume: sc.referinta.nume,
              potrivire: t(`pl.m.ref.${sc.referinta.potrivire}` as DictKey),
              motiv: sc.referinta.motiv ? ` — ${sc.referinta.motiv}` : '',
            }} />
          </span>
        </p>
      )}
      {(sc.reguli ?? []).length > 0 && (
        <div className="pl-reguli">
          <T k="pl.m.corectat" />
          <ul>{sc.reguli!.map((r, i) => <li key={i}>{r}</li>)}</ul>
        </div>
      )}
      {sc.cod && (
        <p className="gri" style={{ fontSize: 12 }}>
          {t('pl.m.scenariu')} <span className="mono">{sc.cod}</span>{sc.din_trepte ? t('pl.m.din_trepte') : ''}
        </p>
      )}
      {/* citatul e textul documentului: nu se traduce */}
      <blockquote className="pl-citat">{a.citat ?? ''}</blockquote>
      <p>
        <a href={href} target="_blank" rel="noopener noreferrer">{t(laParagraf ? 'pl.m.deschide_paragraf' : 'pl.m.deschide')}</a>
        <span className="gri"> · {(a.tip ?? '').toUpperCase()}</span>
      </p>
      <p className="note">
        {t('pl.m.subsol', {
          incredere: a.incredere != null ? num(a.incredere, locale) : '—',
          zi: formatZi(a.data_colectare, locale),
          stare: t(a.stare === 'validat' ? 'pl.m.validat' : 'pl.m.propunere'),
        })}
      </p>
      {a.ambiguu && <p className="callout warn">{a.motiv_ambiguu ?? t('pl.m.amb_implicit')}</p>}
    </div>
  )
}
