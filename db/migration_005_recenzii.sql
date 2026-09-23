-- Migrarea 005: recenzii per locatie.
--
-- Forma urmareste ce intoarce efectiv Google Places, ca sa nu refacem schema
-- cand se conecteaza API-ul:
--   pe locatie:  rating (medie) + nr_recenzii (total)
--   pe recenzie: author_name, rating, text, time  -> autor_hash, rating, text, postat_la
--
-- `autor_hash`, nu numele: Places intoarce numele real al autorului. Aceeasi
-- regula ca la app_review (secțiunea 1 din PDF) - pseudonimizare la ingest,
-- obligatorie, nu opțională.

ALTER TABLE locatii ADD COLUMN IF NOT EXISTS rating      NUMERIC(2, 1);
ALTER TABLE locatii ADD COLUMN IF NOT EXISTS nr_recenzii INTEGER;

CREATE TABLE IF NOT EXISTS locatii_recenzii (
    id          BIGSERIAL PRIMARY KEY,
    id_locatie  BIGINT NOT NULL REFERENCES locatii (id) ON DELETE CASCADE,
    rating      SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    text        TEXT,
    autor_hash  TEXT NOT NULL,
    postat_la   DATE,
    sursa       TEXT NOT NULL CHECK (sursa IN ('mock', 'google_places')),
    UNIQUE (id_locatie, autor_hash, postat_la)
);

CREATE INDEX IF NOT EXISTS ix_recenzii_locatie ON locatii_recenzii (id_locatie);
