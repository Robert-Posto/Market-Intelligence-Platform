import { useQuery } from '@tanstack/react-query'
import { api } from './client'

/** Cererile zonei „context_istoric” (le scrie agentul care mută paginile ei). */
export const _context_istoric = { useQuery, api }
