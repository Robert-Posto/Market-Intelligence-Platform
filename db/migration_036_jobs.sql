-- Migrarea 036: jurnalul joburilor — cât a durat fiecare rulare, cât a consumat
-- (tokeni, dolari) și ce erori a avut.
--
-- Ce se adaugă:
--   job_types    tipurile de job; un tip nou e un INSERT aici, nu o migrare care
--                schimbă un CHECK
--   jobs         o rulare: tip, bancă, început / sfârșit, consum, numărul de erori
--   jobs_error   fiecare eroare, legată de jobul ei prin id_job, textul în TEXT
--   v_jobs       vederea pentru pagina Logging (/api/jobs): durata și starea efectivă
--
-- Cine scrie: extragere_produse_bancare/jurnal_joburi.py, folosit de descopera_surse_libra.py (discovery),
-- extrage_comparatie_libra.py (extragere) și descopera_produse.py (produse_noi).
-- Un job = o rulare pe o bancă; `--simulare` și `--din-json` nu sunt joburi
-- (nu cheamă modelul, nu descarcă nimic).
--
-- `jobs.errors` e INT8 și se ține la zi din trigger, la fiecare rând în
-- jobs_error: scriptul nu trebuie să numere singur, deci contorul nu poate
-- diverge de erorile salvate.
--
-- Costul e ESTIMAREA din preturi.py (prețuri de listă × tokenii raportați de
-- API), nu factura. `cost_complet = FALSE` când un model folosit nu era în
-- tabelul de prețuri: costul afișat e atunci o limită inferioară.
--
-- Idempotentă.

BEGIN;

-- ── job_types ────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS job_types (
    cod        TEXT PRIMARY KEY,                -- ce scrie scriptul în jobs.type
    denumire   TEXT NOT NULL,                   -- ce apare în pagină
    descriere  TEXT,
    script     TEXT,                            -- scriptul care îl rulează
    ordine     INTEGER NOT NULL DEFAULT 100,    -- ordinea în filtre și culoarea în grafic
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO job_types (cod, denumire, descriere, script, ordine) VALUES
    ('discovery',   'Discovery surse',
     'Unde se găsesc, la o bancă, datele fiecărui produs Libra (sau ale echivalentului). Scrie în surse_libra.',
     'descopera_surse_libra.py', 10),
    ('extragere',   'Extragere date',
     'Valorile (dobânzi, comisioane, sume) din sursele găsite la discovery. Scrie în comparatie_libra.',
     'extrage_comparatie_libra.py', 20),
    ('produse_noi', 'Produse pe care Libra nu le are',
     'Produsele concurenței fără echivalent în catalogul Libra. Scrie în products_discovery.',
     'descopera_produse.py', 30)
ON CONFLICT (cod) DO UPDATE SET
    denumire = EXCLUDED.denumire, descriere = EXCLUDED.descriere,
    script = EXCLUDED.script, ordine = EXCLUDED.ordine;

COMMENT ON TABLE job_types IS
  'Tipurile de job. Un tip nou se adauga cu INSERT; jobs.type are FK aici.';


-- ── jobs ─────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS jobs (
    id                   BIGSERIAL PRIMARY KEY,
    type                 TEXT NOT NULL REFERENCES job_types (cod),

    started_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at             TIMESTAMPTZ,              -- NULL = în curs sau procesul a murit
    -- ultimul semn de viață; un job în curs care nu mai scrie de o oră e afișat
    -- „abandonat" (proces oprit fără să apuce să închidă rândul)
    actualizat_la        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (ended_at IS NULL OR ended_at >= started_at),

    errors               INT8 NOT NULL DEFAULT 0,  -- ținut la zi de trigger, din jobs_error

    -- in_curs -> reusit (fără erori) / cu_erori (a terminat, dar cu erori)
    --         / esuat (s-a oprit pe o excepție) / intrerupt (Ctrl+C)
    stare                TEXT NOT NULL DEFAULT 'in_curs'
                         CHECK (stare IN ('in_curs', 'reusit', 'cu_erori', 'esuat', 'intrerupt')),

    banca                TEXT,                     -- slug; fără FK: și o bancă greșită e un job eșuat de jurnalizat
    model                TEXT,                     -- modelul principal; NULL dacă jobul n-a chemat modelul
    parametri            JSONB,                    -- argumentele din linia de comandă
    rezumat              TEXT,                     -- linia de final a scriptului

    -- consumul, adunat din `usage` al fiecărui răspuns API
    apeluri              BIGINT NOT NULL DEFAULT 0,
    tokeni_intrare       BIGINT NOT NULL DEFAULT 0,
    tokeni_iesire        BIGINT NOT NULL DEFAULT 0,
    tokeni_cache_citire  BIGINT NOT NULL DEFAULT 0,
    tokeni_cache_scriere BIGINT NOT NULL DEFAULT 0,
    cost_usd             NUMERIC(12, 6) NOT NULL DEFAULT 0,
    cost_complet         BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS ix_jobs_started_at ON jobs (started_at DESC);
CREATE INDEX IF NOT EXISTS ix_jobs_type       ON jobs (type, started_at DESC);

COMMENT ON TABLE jobs IS
  'O rulare a unui job (tip x banca): durata, consumul de tokeni, costul estimat si numarul de erori.';
COMMENT ON COLUMN jobs.errors IS
  'Numarul de randuri din jobs_error ale jobului; il tine trigger-ul trg_jobs_error_numara.';
COMMENT ON COLUMN jobs.cost_usd IS
  'Estimare din preturile de lista (preturi.py), nu factura.';


-- ── jobs_error ───────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS jobs_error (
    id         BIGSERIAL PRIMARY KEY,
    id_job     BIGINT NOT NULL REFERENCES jobs (id) ON DELETE CASCADE,
    eroare     TEXT NOT NULL,                   -- mesajul; la o excepție, și traceback-ul
    context    TEXT,                            -- unde: codul produsului, URL-ul, candidatul
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_jobs_error_job        ON jobs_error (id_job);
CREATE INDEX IF NOT EXISTS ix_jobs_error_created_at ON jobs_error (created_at DESC);

COMMENT ON TABLE jobs_error IS
  'Erorile unui job, legate prin id_job. Textul erorii in `eroare`.';


-- ── contorul jobs.errors ─────────────────────────────────────────

CREATE OR REPLACE FUNCTION jobs_error_numara() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE jobs SET errors = errors + 1, actualizat_la = now() WHERE id = NEW.id_job;
    ELSE
        UPDATE jobs SET errors = GREATEST(errors - 1, 0) WHERE id = OLD.id_job;
    END IF;
    RETURN NULL;
END $$;

DROP TRIGGER IF EXISTS trg_jobs_error_numara ON jobs_error;
CREATE TRIGGER trg_jobs_error_numara
    AFTER INSERT OR DELETE ON jobs_error
    FOR EACH ROW EXECUTE FUNCTION jobs_error_numara();


-- ── vederea ──────────────────────────────────────────────────────

CREATE OR REPLACE VIEW v_jobs AS
SELECT j.id,
       j.type,
       t.denumire AS tip,
       j.banca,
       j.started_at,
       j.ended_at,
       -- un job în curs își arată durata de până acum
       EXTRACT(EPOCH FROM (COALESCE(j.ended_at, now()) - j.started_at))::NUMERIC(12, 1) AS durata_s,
       CASE WHEN j.stare = 'in_curs' AND j.actualizat_la < now() - INTERVAL '1 hour'
            THEN 'abandonat' ELSE j.stare END AS stare,
       j.errors,
       j.model,
       j.apeluri,
       j.tokeni_intrare,
       j.tokeni_iesire,
       j.tokeni_cache_citire,
       j.tokeni_cache_scriere,
       j.cost_usd,
       j.cost_complet,
       j.parametri,
       j.rezumat
  FROM jobs j
  JOIN job_types t ON t.cod = j.type;

COMMIT;
