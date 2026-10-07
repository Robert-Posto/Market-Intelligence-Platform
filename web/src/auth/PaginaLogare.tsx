import { useState } from 'react'
import { MoonOutlined, SunOutlined } from '@ant-design/icons'
import { Alert, Button, Form, Input } from 'antd'
import { Comutator } from '../components/Comutator'
import { useLang, type DictKey, type Lang } from '../i18n'
import { useTema, type Tema } from '../tema'
import type { CodLogare } from './context'
import { useSesiune } from '.'

interface Valori {
  utilizator: string
  parola: string
}

/** Logare pe tot ecranul, cu marca aplicației; limba și tema se aleg și aici, înainte de logare. */
export default function PaginaLogare() {
  const { t, lang, setLang } = useLang()
  const { intunecat, setTema } = useTema()
  const { logare, expirata } = useSesiune()
  const [form] = Form.useForm<Valori>()
  const [seVerifica, setSeVerifica] = useState(false)
  const [eroare, setEroare] = useState<CodLogare | null>(null)

  const trimite = async ({ utilizator, parola }: Valori) => {
    // parola nu rămâne în starea formularului după trimitere, nici dacă logarea eșuează
    form.setFieldValue('parola', '')
    setSeVerifica(true)
    setEroare(null)
    const cod = await logare(utilizator.trim(), parola)
    // la succes componenta dispare; starea de mai jos contează doar la eșec
    setSeVerifica(false)
    if (cod) setEroare(cod)
  }

  return (
    <div className="logare">
      <div className="logare-comutatoare">
        <Comutator<Lang>
          size="small"
          value={lang}
          onChange={setLang}
          options={[
            { label: 'RO', value: 'ro' },
            { label: 'EN', value: 'en' },
          ]}
        />
        <Comutator<Tema>
          size="small"
          value={intunecat ? 'intunecat' : 'luminos'}
          onChange={setTema}
          aria-label={t('comun.tema.eticheta')}
          options={[
            { value: 'luminos', title: t('comun.tema.luminos'), label: <SunOutlined aria-label={t('comun.tema.luminos')} /> },
            { value: 'intunecat', title: t('comun.tema.intunecat'), label: <MoonOutlined aria-label={t('comun.tema.intunecat')} /> },
          ]}
        />
      </div>
      <main className="logare-card">
        <div className="logare-marca">
          <span className="t">Marketing <i>Command</i> Center</span>
          <span className="s">{t('comun.nav.subtitlu')}</span>
        </div>
        <h1>{t('auth.titlu')}</h1>
        <p className="note">{t('auth.subtitlu')}</p>
        {expirata && !eroare && <Alert className="logare-alerta" type="info" showIcon message={t('auth.expirata')} />}
        {eroare && <Alert className="logare-alerta" type="error" showIcon role="alert" message={t(`auth.eroare.${eroare}` as DictKey)} />}
        <Form<Valori> form={form} layout="vertical" requiredMark={false} onFinish={trimite} disabled={seVerifica}>
          <Form.Item name="utilizator" label={t('auth.utilizator')} rules={[{ required: true, whitespace: true, message: t('auth.cere_utilizator') }]}>
            <Input autoComplete="username" autoFocus placeholder={t('auth.utilizator_ph')} maxLength={64} />
          </Form.Item>
          <Form.Item name="parola" label={t('auth.parola')} rules={[{ required: true, whitespace: true, message: t('auth.cere_parola') }]}>
            <Input.Password autoComplete="current-password" maxLength={256} />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={seVerifica}>{t('auth.intra')}</Button>
        </Form>
      </main>
    </div>
  )
}
