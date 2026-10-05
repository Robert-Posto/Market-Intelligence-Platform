import { useState } from 'react'
import { Button, Checkbox, Input, Popover } from 'antd'
import type { Meta } from '../../api/meta'
import { useLang } from '../../i18n'
import { faraDiacritice } from '../../util/format'
import { MAXIM_ALESE, REFERINTA } from './model'

/**
 * Alegerea băncilor, cu căutare. Cel mult 3: după a treia bifă, restul se
 * dezactivează — nu mai tăiem în tăcere. Bifele se aplică doar la „Aplică”,
 * ca în aplicația veche; până atunci pagina rămâne pe alegerea din adresă.
 * Componenta se reface (cheia din pagină) când alegerea din adresă se schimbă.
 */
export function AlegeBanci({ toate, alese, m, onAplica }: {
  toate: string[]
  alese: string[]
  m: Meta
  onAplica: (sel: string[]) => void
}) {
  const { t } = useLang()
  const [deschis, setDeschis] = useState(false)
  const [bife, setBife] = useState<string[]>(alese)
  const [cauta, setCauta] = useState('')
  const n = bife.length
  const c = faraDiacritice(cauta.trim())
  const optiuni = toate.filter((b) => b !== REFERINTA)
  // ordinea din listă (alfabetică), nu ordinea bifelor: așa citea aplicația veche bifele din pagină
  const aplica = () => {
    onAplica(optiuni.filter((b) => bife.includes(b)).slice(0, MAXIM_ALESE))
    setDeschis(false)
  }

  const continut = (
    <div className="vs-pop">
      <Input className="cauta" allowClear placeholder={t('versus.cauta_banca_placeholder')} value={cauta} onChange={(e) => setCauta(e.target.value)} />
      <div className="vs-opt">
        {optiuni.map((b) => {
          const nume = m.nume[b] ?? b
          const ales = bife.includes(b)
          return (
            <Checkbox key={b} checked={ales} disabled={!ales && n >= MAXIM_ALESE}
              style={c && !faraDiacritice(nume).includes(c) ? { display: 'none' } : undefined}
              onChange={(e) => setBife((v) => (e.target.checked ? [...v, b] : v.filter((x) => x !== b)))}>
              {nume}
            </Checkbox>
          )
        })}
      </div>
      <div className="vs-pop-jos">
        <span className="gri">{t('versus.alese', { n })}</span>
        <Button type="primary" onClick={aplica}>{t('versus.aplica')}</Button>
      </div>
    </div>
  )
  return (
    <Popover open={deschis} onOpenChange={setDeschis} trigger="click" placement="bottomLeft" arrow={false} content={continut}>
      <Button>{t('versus.schimba_bancile')}</Button>
    </Popover>
  )
}
