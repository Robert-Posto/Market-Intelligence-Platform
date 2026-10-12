/**
 * /api/news: brief-ul de știri din containerul „Sinteză” (Overview), scris de ingest/brief_stiri.py
 * în tabela `news`. Forma lui `continut` e verificată și de bază (migrarea 041, `news_valideaza`);
 * aici e aceeași, ca o schimbare de structură să apară ca eroare cu numele câmpului.
 * Fiecare element citează în `surse` id-uri din `continut.surse`.
 */
import { z } from 'zod'

const surse = z.array(z.number())

export const GravitateAlerta = z.enum(['critica', 'ridicata', 'medie', 'scazuta'])
export type GravitateAlerta = z.infer<typeof GravitateAlerta>
export const IncrederePredictie = z.enum(['scazuta', 'medie', 'ridicata'])
export const DirectieTrend = z.enum(['crestere', 'scadere', 'stabil', 'nou'])
export type DirectieTrend = z.infer<typeof DirectieTrend>
export const TipOportunitate = z.enum(['produs', 'marketing', 'pret', 'comunicare'])

export const ContinutNews = z
  .object({
    versiune: z.literal(1),
    perioada: z.object({ de_la: z.string(), pana_la: z.string() }),
    generare: z.object({ model: z.string(), nr_stiri: z.number(), nr_subiecte: z.number() }).passthrough(),
    sinteza: z.string(),
    alerte: z.array(z.object({
      titlu: z.string(),
      gravitate: GravitateAlerta,
      descriere: z.string(),
      impact_libra: z.string(),
      banci: z.array(z.string()),
      surse,
    })),
    predictii: z.array(z.object({
      enunt: z.string(),
      orizont: z.string(),
      incredere: IncrederePredictie,
      argument: z.string(),
      surse,
    })),
    trenduri: z.array(z.object({ tema: z.string(), directie: DirectieTrend, descriere: z.string(), surse })),
    concurenta: z.array(z.object({ banca: z.string(), descriere: z.string(), surse })),
    oportunitati: z.array(z.object({
      titlu: z.string(),
      tip: TipOportunitate,
      propunere: z.string(),
      argument: z.string(),
      surse,
    })),
    surse: z.array(z.object({
      id: z.number(),
      titlu: z.string(),
      url: z.string(),
      publicatie: z.string(),
      publicat_la: z.string(),
    })),
  })
  .passthrough()
export type ContinutNews = z.infer<typeof ContinutNews>

export const News = z.discriminatedUnion('disponibil', [
  z.object({ disponibil: z.literal(false), motiv: z.string() }),
  z.object({
    disponibil: z.literal(true),
    /** null = niciun brief încă */
    brief: z.object({ id: z.number(), created_at: z.string(), continut: ContinutNews }).nullable(),
    /** cele mai noi brief-uri (id, created_at), pentru alegerea unuia mai vechi */
    istoric: z.array(z.object({ id: z.number(), created_at: z.string() })),
  }),
])
export type News = z.infer<typeof News>
