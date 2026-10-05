-- Migrarea 030 (fluxul extragere_produse_bancare): structura finală a fluxului Libra.
--
--   banci                  (există)
--   produse_libra          referința: cele 57 de produse din catalog
--   surse_libra            DE UNDE: la ce bancă, pentru ce produs Libra, la ce
--                          URL (html / pdf / xml) și cu ce metodă. Pe ea rulează
--                          jobul zilnic.
--   comparatie_libra       CE VALOARE: la banca X, produsul Libra Y are valoarea
--                          Z pe intervalul W (ex. BT, DEPOZIT_TERMEN, dobândă
--                          6,25%, 12 luni).
--   descopera_concurenta   produsele concurenței care NU au corespondent în
--                          suita Libra.
--
-- DE CE surse_libra și nu `surse`: în aceeași bază există tabela `surse` a
-- MIP (245 de rânduri, citită de aplicația lor). surse_libra e fosta
-- discovery_libra (027/029), redenumită — avea deja exact coloanele astea.
--
-- Scoate inventar_libra (029): nu mai face parte din flux.
-- Tabelele atinse erau goale la aplicare (verificat: 0 rânduri).

BEGIN;

DROP VIEW  IF EXISTS v_comparatie_libra;
DROP TABLE IF EXISTS inventar_libra;
DROP TABLE IF EXISTS comparatie_libra;

-- ── surse_libra (fosta discovery_libra) ───────────────────────────

ALTER TABLE IF EXISTS discovery_libra RENAME TO surse_libra;
ALTER SEQUENCE IF EXISTS discovery_libra_id_seq RENAME TO surse_libra_id_seq;
ALTER TABLE surse_libra RENAME CONSTRAINT ux_discovery_libra         TO ux_surse_libra;
ALTER TABLE surse_libra RENAME CONSTRAINT ux_discovery_libra_pereche TO ux_surse_libra_pereche;
ALTER INDEX IF EXISTS ix_discovery_libra_pereche RENAME TO ix_surse_libra_pereche;

COMMENT ON TABLE surse_libra IS
  'Unde se gaseste, la o banca, un produs Libra: URL, tip (html/pdf/xml), metoda. Jobul zilnic le parcurge.';


-- ── comparatie_libra: valorile ────────────────────────────────────

CREATE TABLE comparatie_libra (
    id                BIGSERIAL PRIMARY KEY,
    id_banca          BIGINT NOT NULL REFERENCES banci (id) ON DELETE CASCADE,
    id_produs_libra   BIGINT NOT NULL REFERENCES produse_libra (id) ON DELETE CASCADE,
    id_sursa          BIGINT NOT NULL,         -- URL-ul din surse_libra de unde s-a citit
    denumire_la_banca TEXT,                    -- numele lor comercial, ex. „Depozitul Star"

    -- valoarea
    camp              TEXT NOT NULL,           -- dobanda, dae, comision_administrare, suma_max...
    valoare_num       NUMERIC,
    valoare_text      TEXT,                    -- când nu e număr: „gratuit", „variabilă"
    CHECK (valoare_num IS NOT NULL OR valoare_text IS NOT NULL),
    unitate           TEXT,                    -- %, lei, eur, lei/luna
    moneda            TEXT,                    -- RON, EUR, USD

    -- intervalul la care se aplică valoarea: termen, sumă sau vechime.
    -- „12 luni" = 12..12; „10.000–150.000 lei" = 10000..150000; „peste 50.000" = 50000..NULL
    interval_min      NUMERIC,
    interval_max      NUMERIC,
    unitate_interval  TEXT CHECK (unitate_interval IN ('zile', 'luni', 'ani', 'lei', 'eur', 'usd')),
    CHECK ((interval_min IS NULL AND interval_max IS NULL) = (unitate_interval IS NULL)),
    CHECK (interval_min IS NULL OR interval_max IS NULL OR interval_min <= interval_max),
    conditie          TEXT,                    -- restul condițiilor: „cu salariu virat", „online"

    -- dovada, pentru audit
    citat             TEXT NOT NULL,           -- fragmentul literal din care s-a citit cifra
    link_live         TEXT,                    -- url + #:~:text=citat (derulează și evidențiază)
    pagina_pdf        INTEGER,

    -- proveniență și verificare (regula echipei: ce propune un LLM se verifică)
    metoda_extractie  TEXT NOT NULL CHECK (metoda_extractie IN ('parser', 'llm', 'manual', 'catalog')),
    incredere         NUMERIC(3, 2) CHECK (incredere BETWEEN 0 AND 1),
    ambiguu           BOOLEAN NOT NULL DEFAULT FALSE,
    motiv_ambiguu     TEXT,
    CHECK (NOT ambiguu OR motiv_ambiguu IS NOT NULL),
    stare             TEXT NOT NULL DEFAULT 'propus' CHECK (stare IN ('propus', 'validat', 'respins')),
    verificat_de      TEXT,
    verificat_la      TIMESTAMPTZ,
    CHECK (stare = 'propus' OR (verificat_de IS NOT NULL AND verificat_la IS NOT NULL)),

    data_colectare    DATE NOT NULL DEFAULT CURRENT_DATE,   -- ultima dată când jobul a văzut-o
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- sursa e a aceleiași bănci și a aceluiași produs: un rând BT nu poate
    -- trimite la un URL găsit la BCR
    CONSTRAINT fk_comparatie_sursa FOREIGN KEY (id_sursa, id_banca, id_produs_libra)
        REFERENCES surse_libra (id, id_banca, id_produs_libra) ON DELETE RESTRICT,
    -- o singură valoare per bancă × produs × câmp × interval × condiție;
    -- NULLS NOT DISTINCT: două rânduri fără interval sunt aceeași cheie
    CONSTRAINT ux_comparatie_libra UNIQUE NULLS NOT DISTINCT
        (id_banca, id_produs_libra, camp, interval_min, interval_max, unitate_interval, moneda, conditie)
);

CREATE INDEX ix_comparatie_libra_produs ON comparatie_libra (id_produs_libra, camp);

COMMENT ON TABLE comparatie_libra IS
  'Valorile: la banca X, produsul Libra Y are valoarea Z pe intervalul W. Libra insasi = id_banca libra.';


-- ── descopera_concurenta: produse fără corespondent Libra ─────────

CREATE TABLE IF NOT EXISTS descopera_concurenta (
    id                  BIGSERIAL PRIMARY KEY,
    id_banca            BIGINT NOT NULL REFERENCES banci (id) ON DELETE CASCADE,
    denumire_produs     TEXT NOT NULL,         -- numele lor, ex. „Creditul Casa Mea"
    categorie           TEXT,                  -- credit, depozit, card, cont, asigurare...
    segment             TEXT CHECK (segment IN ('PF', 'PJ', 'PF+PJ')),
    descriere           TEXT,                  -- rezumat: ce e și pentru cine
    descriere_generata_de TEXT,                -- modelul, dacă descrierea e generată
    url                 TEXT NOT NULL,
    tip                 TEXT NOT NULL CHECK (tip IN ('html', 'pdf', 'xml')),
    citat               TEXT NOT NULL,         -- paragraful literal care descrie produsul
    incredere           NUMERIC(3, 2) CHECK (incredere BETWEEN 0 AND 1),
    model               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ux_descopera_concurenta UNIQUE (id_banca, denumire_produs, url)
);

COMMENT ON TABLE descopera_concurenta IS
  'Produsele concurentei fara corespondent in suita Libra: ce ofera ei si noi nu.';


-- ── vederea: produs Libra, bancă, valoare, interval ───────────────

CREATE VIEW v_comparatie_libra AS
SELECT p.cod              AS cod_produs,
       p.denumire         AS produs_libra,
       b.slug             AS banca,
       b.nume             AS nume_banca,
       c.denumire_la_banca,
       c.camp,
       c.valoare_num,
       c.valoare_text,
       c.unitate,
       c.moneda,
       c.interval_min,
       c.interval_max,
       c.unitate_interval,
       c.conditie,
       c.citat,
       COALESCE(c.link_live, s.url) AS link,
       s.tip              AS tip_sursa,
       c.stare,
       c.data_colectare
  FROM comparatie_libra c
  JOIN banci b         ON b.id = c.id_banca
  JOIN produse_libra p ON p.id = c.id_produs_libra
  JOIN surse_libra s   ON s.id = c.id_sursa;

COMMIT;
