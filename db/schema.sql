-- =====================================================================
-- Structura bazei de date - v4 (fix pe v3 din flux-colectare/db.sql)
-- banci -> surse -> hashes
--                -> observations <- produse
-- Dialect: PostgreSQL
--
-- Fata de v3, fix-urile aplicate (toate documentate, niciunul silentios):
--   1. Scoase cele doua virgule orfane (linia 84 si 109 din v3) care
--      impiedicau rularea.
--   2. Index unic pe surse.sursa activat (era comentat) - fara el, aceeasi
--      sursa poate intra de doua ori din discovery rulat de mai multe ori.
--   3. surse.produse (BIGINT[]) inlocuit cu tabelul de legatura
--      surse_produse - decizie deja luata in artifact (Flow-uri MIP,
--      figura 2): un produs poate aparea pe mai multe surse, si invers,
--      iar un array nu poate avea integritate referentiala pe elemente.
--   4. observations.id_hash - legatura spre hashes, care in v3 nu era
--      referita de nimeni.
--   5. observations.metoda_extractie - provenienta (care unealta a produs
--      valoarea: playwright | bs4 | llm | manual), absenta in v3.
--   6. observations.unitate cu CHECK pe vocabularul real emis de
--      extractor (parser_rate.py), nu pe exemplul din comentariul v3.
-- =====================================================================


-- ---------------------------------------------------------------------
-- 1. BANCI
-- ---------------------------------------------------------------------
CREATE TABLE banci (
    id           BIGSERIAL PRIMARY KEY,
    slug         TEXT NOT NULL UNIQUE,
    nume         TEXT NOT NULL UNIQUE,
    tier         SMALLINT CHECK (tier BETWEEN 1 AND 3),
    segment_real TEXT,
    activ        BOOLEAN NOT NULL DEFAULT TRUE
);


-- ---------------------------------------------------------------------
-- 2. PRODUSE  (catalog generic)
-- ---------------------------------------------------------------------
CREATE TABLE produse (
    id            BIGSERIAL PRIMARY KEY,
    nume          TEXT NOT NULL UNIQUE,
    activ         BOOLEAN NOT NULL DEFAULT TRUE
);


-- ---------------------------------------------------------------------
-- 3. SURSE
-- ---------------------------------------------------------------------
CREATE TABLE surse (
    id                    BIGSERIAL PRIMARY KEY,
    id_banca              BIGINT NOT NULL
                          REFERENCES banci (id) ON DELETE CASCADE,

    tip_sursa             TEXT NOT NULL
                          CHECK (tip_sursa IN ('url', 'aplicatie', 'reclama')),
    sursa                 TEXT NOT NULL,        -- URL / id app / identificator reclama
    rol                   TEXT CHECK (rol IN ('produs', 'hub', 'conditii', 'context')),

    -- doar pentru tip_sursa = 'url'
    format                TEXT CHECK (format IN ('html', 'pdf', 'xml')),
    metoda                TEXT CHECK (metoda IN ('http', 'playwright', 'manual')),
    robots_ok             BOOLEAN,

    metoda_extractie      TEXT,
    metoda_verificata_la  TIMESTAMPTZ,

    frecventa             TEXT CHECK (frecventa IN ('zilnic', 'saptamanal', 'lunar', 'manual')),
    status                TEXT NOT NULL DEFAULT 'activ'
                          CHECK (status IN ('activ', 'pauza', 'eroare', 'blocat', 'retras')),
    ultima_rulare         TIMESTAMPTZ,
    legal_review_ref      TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- campurile web au sens doar pentru URL-uri
    CONSTRAINT ck_surse_web_only CHECK (
        tip_sursa = 'url' OR (format IS NULL AND robots_ok IS NULL)
    )
);

CREATE UNIQUE INDEX ux_surse_url     ON surse (id_banca, sursa) WHERE tip_sursa = 'url';
CREATE UNIQUE INDEX ux_surse_non_url ON surse (id_banca, tip_sursa, sursa)
                                     WHERE tip_sursa <> 'url';
CREATE INDEX ix_surse_banca   ON surse (id_banca);
CREATE INDEX ix_surse_activ   ON surse (frecventa) WHERE status = 'activ';


-- ---------------------------------------------------------------------
-- 3b. SURSE_PRODUSE  (many-to-many: un produs poate fi pe mai multe
--     surse, o sursa poate acoperi mai multe produse)
-- ---------------------------------------------------------------------
CREATE TABLE surse_produse (
    id_sursa   BIGINT NOT NULL REFERENCES surse (id)   ON DELETE CASCADE,
    id_produs  BIGINT NOT NULL REFERENCES produse (id) ON DELETE RESTRICT,
    activ      BOOLEAN NOT NULL DEFAULT TRUE,  -- fals cand legatura devine "produsul nu mai apare aici"
    PRIMARY KEY (id_sursa, id_produs)
);


-- ---------------------------------------------------------------------
-- 4. HASHES  (amprenta zilnica a sursei: s-a modificat sau nu?)
--    Se populeaza doar pentru continut descarcabil: html / pdf / xml
--    Amprenta e pe OCTETII documentului (dupa sanitizare), niciodata pe
--    valorile extrase - vezi urme.py din pachetul Playwright: un diff pe
--    valori confunda "banca a schimbat" cu "parserul a schimbat".
-- ---------------------------------------------------------------------
CREATE TABLE hashes (
    id         BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    id_sursa   BIGINT NOT NULL REFERENCES surse (id) ON DELETE CASCADE,
    format     TEXT CHECK (format IN ('html', 'pdf', 'xml')),
    hash       TEXT NOT NULL
);

CREATE INDEX ix_hashes_sursa ON hashes (id_sursa, created_at DESC);


-- ---------------------------------------------------------------------
-- 5. OBSERVATIONS
-- ---------------------------------------------------------------------
CREATE TABLE observations (
    id                BIGSERIAL PRIMARY KEY,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    id_sursa          BIGINT NOT NULL
                      REFERENCES surse (id)   ON DELETE CASCADE,
    id_produs         BIGINT NOT NULL
                      REFERENCES produse (id) ON DELETE RESTRICT,
    id_hash           BIGINT
                      REFERENCES hashes (id)  ON DELETE SET NULL,

    camp              TEXT NOT NULL,        -- 'dobanda', 'comision_administrare'
    cod_scenariu      TEXT,                 -- 'nev_5000_24l'

    valoare_num       NUMERIC(18, 6),
    valoare_text      TEXT,
    unitate           TEXT CHECK (unitate IN (
                          'procent', 'lei', 'eur', 'usd', 'zile', 'luni',
                          'ani', 'numar', 'puncte_procentuale', 'altele'
                      )),
    valuta            CHAR(3),

    citat             TEXT,                 -- fragmentul din sursa, pentru audit
    confidence        NUMERIC(4, 3) CHECK (confidence BETWEEN 0 AND 1),
    ambiguu           BOOLEAN NOT NULL DEFAULT FALSE,  -- vezi ambiguitate.py: real, dar neatribuibil
    metoda_extractie  TEXT CHECK (metoda_extractie IN ('playwright', 'bs4', 'llm', 'manual'))
);

CREATE INDEX ix_observations_sursa  ON observations (id_sursa);
CREATE INDEX ix_observations_produs ON observations (id_produs);


-- ---------------------------------------------------------------------
-- 6. CHANGE_EVENTS  (semnalul care conteaza - vezi diferente.py)
-- ---------------------------------------------------------------------
CREATE TABLE change_events (
    id           BIGSERIAL PRIMARY KEY,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    id_sursa     BIGINT NOT NULL REFERENCES surse (id) ON DELETE CASCADE,
    tip          TEXT NOT NULL CHECK (tip IN (
                     'valoare_noua', 'valoare_schimbata', 'produs_retras',
                     'sursa_negasita', 'url_actualizat'
                 )),
    severitate   TEXT NOT NULL DEFAULT 'normala' CHECK (severitate IN ('normala', 'mare')),
    detalii      JSONB,
    notificat    BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX ix_change_events_sursa ON change_events (id_sursa, created_at DESC);


-- ---------------------------------------------------------------------
-- 7. APP_RELEASE / APP_REVIEW / APP_SCREENSHOT (track mobil - itunes_lookup.py)
--    Date complet separate de restul (versiune, rating, review-uri de
--    aplicatie, nu produse/dobanzi de site) - vezi figura 4, artifact.
-- ---------------------------------------------------------------------
CREATE TABLE app_release (
    id             BIGSERIAL PRIMARY KEY,
    id_banca       BIGINT NOT NULL REFERENCES banci (id) ON DELETE CASCADE,
    platforma      TEXT NOT NULL CHECK (platforma IN ('ios', 'android')),
    app_id         TEXT NOT NULL,   -- ios_app_id sau package name Android
    versiune       TEXT NOT NULL,
    note_lansare   TEXT,
    rating_agregat NUMERIC(3, 2),
    volum_rating   INTEGER,
    observat_la    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (id_banca, platforma, versiune)
);

CREATE TABLE app_review (
    id           BIGSERIAL PRIMARY KEY,
    id_banca     BIGINT NOT NULL REFERENCES banci (id) ON DELETE CASCADE,
    platforma    TEXT NOT NULL CHECK (platforma IN ('ios', 'android')),
    storefront   TEXT,            -- 'ro', 'us' etc - RSS e per tara
    rating       SMALLINT CHECK (rating BETWEEN 1 AND 5),
    versiune     TEXT,
    text         TEXT,
    autor_hash   TEXT NOT NULL,   -- pseudonimizat la ingest, obligatoriu (Apple da nume real)
    postat_la    TIMESTAMPTZ,
    UNIQUE (id_banca, platforma, storefront, autor_hash, postat_la)
);

CREATE TABLE app_screenshot (
    id          BIGSERIAL PRIMARY KEY,
    id_banca    BIGINT NOT NULL REFERENCES banci (id) ON DELETE CASCADE,
    platforma   TEXT NOT NULL CHECK (platforma IN ('ios', 'android')),
    url         TEXT NOT NULL,
    hash        TEXT,            -- pentru diff cand se schimba imaginile de marketing
    observat_la TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (id_banca, platforma, url)
);


-- ---------------------------------------------------------------------
-- 8. INDICI_REFERINTA  (BNR: IRCC / ROBOR / EURIBOR - bnr_indici.json)
-- ---------------------------------------------------------------------
CREATE TABLE indici_referinta (
    id          BIGSERIAL PRIMARY KEY,
    indice      TEXT NOT NULL CHECK (indice IN ('ircc', 'robor', 'euribor')),
    scadenta    TEXT,            -- '3M', '6M' - relevant mai ales pentru robor/euribor
    valoare     NUMERIC(6, 4) NOT NULL,
    valabil_din DATE NOT NULL,
    valabil_pana DATE,
    sursa       TEXT NOT NULL DEFAULT 'bnr',
    UNIQUE (indice, scadenta, valabil_din)
);
