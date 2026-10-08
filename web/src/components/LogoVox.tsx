import { useId } from 'react'

/**
 * Siglele Vox, alese pe 07.10.2026 din pânza cu variante: 1A (bula plină cu V decupat) în butonul
 * din bara laterală, 15C (insigna cu unda de voce) lângă titlul paginii. Desenul e plin în `currentColor`,
 * iar V-ul și unda sunt găuri adevărate (mask), nu linii în culoarea fundalului: butonul din bară
 * își schimbă fundalul la hover și când pagina e activă.
 */
interface Props {
  className?: string
  size?: number
}

/** `useId` dă „:r1:”; fără două puncte, ca `url(#…)` să nu depindă de cum le citește browserul. */
const useMasca = () => 'vox-' + useId().replace(/:/g, '')

export function VoxBula({ className, size = 16 }: Props) {
  const m = useMasca()
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 64 64" aria-hidden="true" focusable="false">
      <mask id={m}>
        <rect width="64" height="64" fill="#fff" />
        <path d="M22 20L32 37L42 20" fill="none" stroke="#000" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
      </mask>
      <path
        mask={`url(#${m})`}
        fill="currentColor"
        d="M20 8H44A14 14 0 0 1 58 22V34A14 14 0 0 1 44 48H26L14 57C14.6 53 15 50 14.6 46.6A14 14 0 0 1 6 34V22A14 14 0 0 1 20 8Z"
      />
    </svg>
  )
}

export function VoxInsigna({ className, size = 32 }: Props) {
  const m = useMasca()
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 64 64" aria-hidden="true" focusable="false">
      <mask id={m}>
        <rect width="64" height="64" fill="#fff" />
        <g fill="none" stroke="#000" strokeLinecap="round" strokeLinejoin="round">
          <path d="M10 32H14L17 27L20 37L24 19" strokeWidth="4" />
          <path d="M24 19L32 46L40 19" strokeWidth="6" />
          <path d="M40 19L44 37L47 27L50 32H54" strokeWidth="4" />
        </g>
      </mask>
      <rect mask={`url(#${m})`} fill="currentColor" x="4" y="4" width="56" height="56" rx="15" />
    </svg>
  )
}
