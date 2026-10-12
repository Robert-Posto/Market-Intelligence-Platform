import { Tooltip } from 'antd'
import { useLang, type DictKey } from '../i18n'
import { formatZi } from '../util/format'

export interface DateValoare {
  data_citat?: string | null
  data_document?: string | null
  data_document_sursa?: string | null
  data_extragere?: string | null
}

const SURSA_DATEI: Record<string, DictKey> = {
  text: 'dv.sursa.text', pdf_modificat: 'dv.sursa.pdf_modificat', pdf_creat: 'dv.sursa.pdf_creat',
  http_last_modified: 'dv.sursa.http',
}

/**
 * De când e valoarea, ca să se poată verifica dacă vine din documentul potrivit: data scrisă lângă
 * cifră („valabil începând cu …”), altfel data documentului, altfel ziua extragerii — cu eticheta ei,
 * ca o dată de document să nu treacă drept dată a citatului. Tooltip-ul le arată pe toate.
 * Nimic pentru valorile fără date (colectarea echipei).
 */
export function DataValorii({ d, className = 'sub' }: { d: DateValoare; className?: string }) {
  const { t, locale } = useLang()
  const zi = (x?: string | null) => (x ? formatZi(x, locale) : '—')
  const text = d.data_citat ? t('dv.citat', { data: zi(d.data_citat) })
    : d.data_document ? t('dv.document', { data: zi(d.data_document) })
      : d.data_extragere ? t('dv.extragere', { data: zi(d.data_extragere) })
        : null
  if (!text) return null
  const sursa = d.data_document_sursa && SURSA_DATEI[d.data_document_sursa]
  const titlu = t('dv.titlu', {
    citat: zi(d.data_citat), document: zi(d.data_document),
    sursa: sursa ? t(sursa) : '—', extragere: zi(d.data_extragere),
  })
  return (
    <Tooltip title={titlu}>
      <span className={`${className} data-valorii${d.data_citat ? ' din-citat' : ''}`}>{text}</span>
    </Tooltip>
  )
}
