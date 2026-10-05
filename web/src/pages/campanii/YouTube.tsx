import { BaraSectiune } from '../../components/Banda'
import type { PropsSectiune } from './tipuri'

/** Secțiune 2.4 în lucru: o mută agentul care deține fișierul. */
export default function YouTube({ taburi, subsol }: PropsSectiune) {
  return (
    <>
      <BaraSectiune taburi={taburi} />
      <section className="cm-sec">{subsol}</section>
    </>
  )
}
