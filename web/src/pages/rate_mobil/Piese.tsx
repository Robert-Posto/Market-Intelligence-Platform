import { cloneElement, isValidElement, useId, useState, type ReactElement } from 'react'
import { Collapse, Image, Modal, Tooltip } from 'antd'
import { DislikeFilled, LikeFilled } from '@ant-design/icons'
import { useLang } from '../../i18n'
import { num } from '../../util/format'
import { rezumate, rezumatePlay, type TextRoEn } from './dateLocale'

/** Cinci stele SVG umplute proporțional cu nota (4,47 → a cincea umplută 47%), ca în store. */
export function Stele({ nota, marime = 22 }: { nota: number | null; marime?: number }) {
  const id = useId()
  const { locale } = useLang()
  if (nota === null) return <span className="gri">—</span>
  const umplut = Math.max(0, Math.min(5, nota))
  return (
    <span className="ap-stele" role="img" aria-label={`${num(nota, locale)} / 5`} title={`${num(nota, locale)} / 5`}>
      {[0, 1, 2, 3, 4].map((i) => {
        const p = Math.max(0, Math.min(1, umplut - i))
        return (
          <svg key={i} width={marime} height={marime} viewBox="0 0 24 24" aria-hidden>
            <defs>
              <linearGradient id={`${id}-${i}`}>
                <stop offset={p} stopColor="var(--stea)" />
                <stop offset={p} stopColor="var(--stea-gol)" />
              </linearGradient>
            </defs>
            <path fill={`url(#${id}-${i})`}
              d="M12 2.6l2.85 6.06 6.6.8-4.88 4.55 1.27 6.54L12 17.3l-5.84 3.25 1.27-6.54L2.55 9.46l6.6-.8z" />
          </svg>
        )
      })}
    </span>
  )
}

/**
 * Capturile ca miniaturi; clic → toate capturile într-un modal, 4 pe rând, ca povestea pe care
 * o spune banca să se vadă dintr-o privire; clic pe una din grilă → vizualizatorul antd
 * (mărire, rotire, săgeți între capturi). Pe sertarul vechi, o captură de 300px nu se citea.
 * `no-referrer`: play-lh.googleusercontent.com răspunde 429 (pagină HTML, deci ERR_BLOCKED_BY_ORB
 * în browser) unei cereri de imagine cu antete de browser și `Referer: localhost`; fără Referer,
 * 200 (măsurat 06.10.2026). Capturile Apple merg oricum.
 */
export function Galerie({ urls, inaltime, clasa, titlu }: { urls: string[]; inaltime: number; clasa: string; titlu: string }) {
  const { t, tn } = useLang()
  const [grila, setGrila] = useState(false)
  const [curenta, setCurenta] = useState<number | null>(null)
  return (
    <>
      <div className={clasa} tabIndex={0} aria-label={t('mobil.capturi')}>
        {urls.map((u, i) => (
          <button key={`${i}-${u}`} type="button" className="ap-miniatura" onClick={() => setGrila(true)} title={t('mobil.vezi_toate_capturile')}>
            <img src={u} alt={t('mobil.captura_alt', { i: i + 1 })} loading="lazy" referrerPolicy="no-referrer" style={{ height: inaltime }} />
          </button>
        ))}
      </div>
      <Modal open={grila} onCancel={() => setGrila(false)} footer={null} centered width="min(1240px, 94vw)" destroyOnHidden
        className="ap-grila-modal" title={<span className="sertar-titlu">{titlu}</span>}>
        <p className="note" style={{ margin: '0 0 14px' }}>{tn('mobil.n_capturi', urls.length)} · {t('mobil.clic_zoom')}</p>
        <div className="ap-grila">
          {urls.map((u, i) => (
            <button key={`${i}-${u}`} type="button" className="ap-miniatura" onClick={() => setCurenta(i)} title={t('mobil.deschide_marit')}>
              <img src={u} alt={t('mobil.captura_alt', { i: i + 1 })} loading="lazy" referrerPolicy="no-referrer" />
            </button>
          ))}
        </div>
      </Modal>
      <Image.PreviewGroup items={urls}
        preview={{ visible: curenta !== null, current: curenta ?? 0, onChange: setCurenta, onVisibleChange: (v) => { if (!v) setCurenta(null) },
          imageRender: (img) => (isValidElement(img) ? cloneElement(img as ReactElement<{ referrerPolicy?: string }>, { referrerPolicy: 'no-referrer' }) : img) }} />
    </>
  )
}

/** Rezumatul AI al recenziilor colectate: textul, apoi plusurile (like) și minusurile (dislike). */
export function RezumatAi({ banca, compact, sursa = 'ios' }: { banca: string; compact?: boolean; sursa?: 'ios' | 'play' }) {
  const { t, lang } = useLang()
  const fisier = sursa === 'play' ? rezumatePlay : rezumate
  const r = fisier?.aplicatii[banca]
  const txt = (x: TextRoEn) => (lang === 'en' ? x.en : x.ro)
  if (!r) {
    return (
      <div className="ap-rezumat">
        <div className="ap-eticheta">{t('mobil.rezumat_ai')}</div>
        <p className="gri ap-rezumat-gol">{t('mobil.rezumat_lipsa')}</p>
      </div>
    )
  }
  return (
    <div className={['ap-rezumat', compact ? 'compact' : ''].join(' ').trim()}>
      <Tooltip title={t(sursa === 'play' ? 'mobil.rezumat_ai_title_play' : 'mobil.rezumat_ai_title', { de: fisier!.generat_de, la: fisier!.generat_la })}>
        <div className="ap-eticheta">{t('mobil.rezumat_ai')} · {t('mobil.din_n_recenzii', { n: r.n_recenzii })}</div>
      </Tooltip>
      <p className="ap-rezumat-txt">{txt(r.rezumat)}</p>
      <div className="ap-pro-contra">
        <ul className="ap-pro">
          {r.pro.length ? r.pro.map((x, i) => <li key={i}><LikeFilled aria-hidden /> <span>{txt(x)}</span></li>)
            : <li className="gri"><LikeFilled aria-hidden /> <span>{t('mobil.fara_plusuri')}</span></li>}
        </ul>
        <ul className="ap-contra">
          {r.contra.map((x, i) => <li key={i}><DislikeFilled aria-hidden /> <span>{txt(x)}</span></li>)}
        </ul>
      </div>
    </div>
  )
}

/** „Ce e nou” pliat: notele de lansare ajung la 401 caractere (BCR, 05.10.2026); deschise, ar lungi fiecare card. Folosit la iOS și la Android. */
export function CeENou({ text }: { text: string | null }) {
  if (!text) return <span className="gri">—</span>
  return (
    // clicul pe „ce e nou” deschide textul, nu filtrul pe bancă
    <div onClick={(e) => e.stopPropagation()}>
      <Collapse ghost className="despre mb-nou"
        items={[{ key: 'n', label: <span className="despre-cap">ⓘ {text.slice(0, 70).replace(/\s+\S*$/, '')}…</span>,
          children: <div className="note mb-nou-txt">{text}</div> }]} />
    </div>
  )
}
