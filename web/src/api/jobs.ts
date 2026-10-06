import { useQuery } from '@tanstack/react-query'
import { Jobs } from '@mcc/shared'
import { api } from './client'

/** Cât timp un job rulează, jurnalul se cere din nou singur: altfel durata și costul ar sta pe loc. */
const REIMPROSPATARE_MS = 30_000

const inCurs = (d: Jobs | undefined) => !!d && d.disponibil && d.totaluri.in_curs > 0

export const useJobs = (zile: number, tip: string | null) =>
  useQuery({
    queryKey: ['jobs', zile, tip],
    queryFn: () => api('/api/jobs', Jobs, { zile, tip }),
    refetchInterval: (q) => (inCurs(q.state.data) ? REIMPROSPATARE_MS : false),
    placeholderData: (anterior) => anterior,
  })

/** Erorile unui singur job, oricât de vechi: cererea pornește doar după ce s-a ales jobul. */
export const useEroriJob = (job: number | null, activ: boolean) =>
  useQuery({
    queryKey: ['jobs', 'erori', job],
    queryFn: () => api('/api/jobs', Jobs, { job }),
    enabled: job !== null,
    refetchInterval: activ ? REIMPROSPATARE_MS : false,
  })
