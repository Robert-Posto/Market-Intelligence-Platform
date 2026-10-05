-- Migrarea 029 (fluxul extragere_produse_bancare): fluxul în doi timpi — discovery o dată, colectare zilnică.
--
--   1. DISCOVERY inițial (rar, cu LLM): 30 de bănci × produse_libra.
--        comparatie_libra  are banca un echivalent? un rând per pereche
--        discovery_libra   la ce URL, ce tip de conținut, ce metodă
--   2. JOB ZILNIC (fără LLM acolo unde nu s-a schimbat nimic): parcurge
--      discovery_libra, descarcă fiecare URL, compară amprenta cu ultima
--      rulare și extrage doar la schimbare.
--        inventar_libra    valorile, cu citat și istoric
--
-- Ce se schimbă față de 027:
--   - comparatie_libra pierde id_discovery. Rândul spune DOAR dacă banca are
--     echivalent; de unde vin cifrele spune inventar_libra, per valoare.
--   - discovery_libra primește starea jobului zilnic.
--   - inventar_libra, nou.
--
-- Tabelele 027 erau goale la aplicare. Idempotentă.

BEGIN;

-- ── comparatie_libra: fără sursă ──────────────────────────────────

DROP VIEW IF EXISTS v_comparatie_libra;
ALTER TABLE comparatie_libra DROP CONSTRAINT IF EXISTS fk_comparatie_discovery;
ALTER TABLE comparatie_libra DROP CONSTRAINT IF EXISTS comparatie_libra_check1;   -- inexistent <-> id_discovery NULL
ALTER TABLE comparatie_libra DROP COLUMN IF EXISTS id_discovery;
ALTER TABLE comparatie_libra DROP COLUMN IF EXISTS valori;   -- valorile stau în inventar_libra

COMMENT ON TABLE comparatie_libra IS
  'Un rand per banca x produs Libra: are banca un echivalent (echivalent/similar/inexistent) si cum se numeste la ei. Lista pe care o urmareste jobul zilnic.';


-- ── discovery_libra: starea jobului zilnic ────────────────────────

ALTER TABLE discovery_libra
    ADD COLUMN IF NOT EXISTS ultima_verificare  TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS ultimul_status     TEXT
        CHECK (ultimul_status IN ('ok', 'neschimbat', 'blocat', 'negasit', 'eroare')),
    ADD COLUMN IF NOT EXISTS ultimul_cod_http   INTEGER,
    ADD COLUMN IF NOT EXISTS ultimul_hash       TEXT,       -- amprenta textului sanitizat la ultima rulare
    ADD COLUMN IF NOT EXISTS esecuri_consecutive INTEGER NOT NULL DEFAULT 0;
    -- esecuri_consecutive: după câteva 404 la rând, URL-ul s-a mutat și cere
    -- un discovery nou pentru pereche, nu reîncercări zilnice la nesfârșit

COMMENT ON COLUMN discovery_libra.metoda IS
  'Metoda recomandata la discovery (estimare). Jobul zilnic o foloseste; daca http nu aduce cifre, se re-estimeaza.';


-- ── inventar_libra: valorile ──────────────────────────────────────

CREATE TABLE IF NOT EXISTS inventar_libra (
    id               BIGSERIAL PRIMARY KEY,
    id_banca         BIGINT NOT NULL REFERENCES banci (id) ON DELETE CASCADE,
    id_produs_libra  BIGINT NOT NULL REFERENCES produse_libra (id) ON DELETE CASCADE,
    id_discovery     BIGINT NOT NULL,          -- URL-ul din care vine valoarea (audit)

    -- valoarea
    camp             TEXT NOT NULL,            -- ex. dobanda, dae, comision_administrare, suma_max
    valoare_num      NUMERIC,
    valoare_text     TEXT,                     -- când nu e un număr: „gratuit", „variabilă"
    CHECK (valoare_num IS NOT NULL OR valoare_text IS NOT NULL),
    unitate          TEXT,                     -- %, lei, eur, luni, zile
    moneda           TEXT,                     -- RON, EUR, USD
    conditie         TEXT NOT NULL DEFAULT '', -- scenariul: „12 luni, sume > 50.000 lei", „cu salariu virat"
                                               -- '' și nu NULL: face parte din cheia unică

    -- dovada
    citat            TEXT NOT NULL,            -- fragmentul literal din care s-a citit cifra
    link_live        TEXT,                     -- url + #:~:text=citat
    pagina_pdf       INTEGER,
    hash_continut    TEXT,                     -- amprenta documentului în care s-a văzut

    -- istoric: o valoare se scrie o dată și se prelungește cât rămâne la fel;
    -- la schimbare se închide rândul vechi și se deschide unul nou
    valabil_de_la    DATE NOT NULL DEFAULT CURRENT_DATE,
    valabil_pana     DATE,                     -- NULL = valoarea curentă
    ultima_confirmare DATE NOT NULL DEFAULT CURRENT_DATE,

    -- proveniența și verificarea
    metoda_extractie TEXT NOT NULL CHECK (metoda_extractie IN ('parser', 'llm', 'manual')),
    incredere        NUMERIC(3, 2) CHECK (incredere BETWEEN 0 AND 1),
    ambiguu          BOOLEAN NOT NULL DEFAULT FALSE,
    motiv_ambiguu    TEXT,
    CHECK (NOT ambiguu OR motiv_ambiguu IS NOT NULL),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- valoarea vine de la aceeași bancă și același produs ca URL-ul ei
    CONSTRAINT fk_inventar_discovery FOREIGN KEY (id_discovery, id_banca, id_produs_libra)
        REFERENCES discovery_libra (id, id_banca, id_produs_libra) ON DELETE RESTRICT,
    CHECK (valabil_pana IS NULL OR valabil_pana >= valabil_de_la)
);

-- o singură valoare CURENTĂ per sursă × câmp × condiție
CREATE UNIQUE INDEX IF NOT EXISTS ux_inventar_libra_curent
    ON inventar_libra (id_discovery, camp, conditie) WHERE valabil_pana IS NULL;
CREATE INDEX IF NOT EXISTS ix_inventar_libra_pereche
    ON inventar_libra (id_banca, id_produs_libra) WHERE valabil_pana IS NULL;

COMMENT ON TABLE inventar_libra IS
  'Valorile colectate zilnic pentru produsele Libra, cu citat si istoric (valabil_de_la / valabil_pana).';


-- ── vederea: comparația cu valorile curente ───────────────────────

CREATE OR REPLACE VIEW v_comparatie_libra AS
SELECT c.id              AS id_comparatie,
       b.slug            AS banca,
       b.nume            AS nume_banca,
       p.cod             AS cod_produs,
       p.denumire        AS produs_libra,
       p.segment,
       c.tip_potrivire,
       c.motiv_potrivire,
       c.denumire_la_banca,
       c.stare           AS stare_comparatie,
       i.camp,
       i.valoare_num,
       i.valoare_text,
       i.unitate,
       i.moneda,
       i.conditie,
       i.citat,
       COALESCE(i.link_live, d.url) AS link,
       d.url,
       i.valabil_de_la,
       i.ultima_confirmare,
       i.ambiguu
  FROM comparatie_libra c
  JOIN banci b           ON b.id = c.id_banca
  JOIN produse_libra p   ON p.id = c.id_produs_libra
  LEFT JOIN inventar_libra i  ON i.id_banca = c.id_banca
                             AND i.id_produs_libra = c.id_produs_libra
                             AND i.valabil_pana IS NULL
  LEFT JOIN discovery_libra d ON d.id = i.id_discovery;

COMMIT;
