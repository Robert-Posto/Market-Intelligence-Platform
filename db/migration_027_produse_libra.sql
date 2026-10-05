-- Migrarea 027 (fluxul extragere_produse_bancare): produsele Libra ca axă de comparație — produse_libra,
-- discovery_libra, comparatie_libra.
--
-- DE CE: comparația pornește de la Libra, nu de la ce publică băncile. Pentru
-- fiecare produs din catalogul lui Robert se caută echivalentul la fiecare
-- competitor. Trei pași, trei tabele, în ordinea în care se populează:
--
--   produse_libra     referința: cele 57 de produse din catalog
--        │
--   discovery_libra   candidații: bancă × produs Libra -> adresă + paragraful
--        │            literal de acolo. Pot fi mai mulți per pereche (pagina
--        │            produsului, PDF-ul de tarife, FIPC-ul).
--        │
--   comparatie_libra  decizia: UN rând per bancă × produs Libra — care e
--                     echivalentul, cât de bun e, și din ce sursă.
--
-- DE CE produse_libra separat de catalog_libra (migrarea 020): catalog_libra
-- e exportul integral (criterii de eligibilitate, „când să recomand", praguri
-- FICO — informații interne de vânzare), legat de fișier/foaie/rând. Aici stă
-- doar ce trebuie discovery-ului și comparației. Legătura e `cod`, stabil între
-- exporturi; `id` depinde de ordinea încărcării.
--
-- Idempotentă: IF NOT EXISTS peste tot; a doua rulare nu schimbă nimic.

BEGIN;

-- ── produse_libra ─────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS produse_libra (
    id              BIGSERIAL PRIMARY KEY,
    cod             TEXT NOT NULL UNIQUE,      -- „Cod" din catalog, ex. CREDIT_SIMPLU_IMM
    denumire        TEXT NOT NULL,
    descriere       TEXT,                      -- „Caracteristicile produsului"; 12 din 57 n-au
    segment         TEXT CHECK (segment IN ('PF', 'PJ', 'PF+PJ')),
    categorie_cod   TEXT,                      -- ex. CREDIT_CAPITAL_LUCRU; orientativ, nu
                                               -- sigur: cardul de credit PF e trecut aici
    prioritar       BOOLEAN NOT NULL DEFAULT FALSE,
    activ           BOOLEAN NOT NULL DEFAULT TRUE,  -- scos din catalog -> FALSE, nu DELETE:
                                                    -- comparațiile vechi rămân legate
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE produse_libra IS
  'Produsele Libra dupa care se cauta echivalentul la competitori. Sursa: catalogul intern (vezi catalog_libra), cheie `cod`.';


-- ── discovery_libra ───────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS discovery_libra (
    id                   BIGSERIAL PRIMARY KEY,
    id_banca             BIGINT NOT NULL REFERENCES banci (id) ON DELETE CASCADE,
    id_produs_libra      BIGINT NOT NULL REFERENCES produse_libra (id) ON DELETE CASCADE,

    -- unde
    url                  TEXT NOT NULL,        -- adresa deschisă efectiv, nu reconstruită
    tip                  TEXT NOT NULL CHECK (tip IN ('html', 'pdf', 'xml')),
    rol                  TEXT NOT NULL CHECK (rol IN ('pagina-produs', 'tarife', 'dobanzi',
                                                      'conditii', 'simulator')),
    metoda               TEXT CHECK (metoda IN ('http', 'playwright')),  -- estimare, nu măsurătoare
    pagina_pdf           INTEGER,              -- la PDF: pagina paragrafului (pentru #page=N)

    -- ce
    denumire_la_banca    TEXT,                 -- numele lor comercial, ex. „Depozitul Star"
    citat                TEXT NOT NULL,        -- paragraful LITERAL; dovada, nu se înlocuiește
    citat_verificat      BOOLEAN,              -- găsit în textul primit; NULL = nu s-a putut
                                               -- verifica (PDF: nu avem textul)
    link_live            TEXT,                 -- url + #:~:text=… (derulează și evidențiază);
                                               -- doar când citat_verificat, altfel NULL
    rezumat              TEXT,                 -- opțional, generat; nu ține loc de citat
    rezumat_generat_de   TEXT,                 -- modelul care a scris rezumatul
    CHECK (rezumat IS NULL OR rezumat_generat_de IS NOT NULL),

    -- cât de sigur
    incredere            NUMERIC(3, 2) NOT NULL CHECK (incredere BETWEEN 0 AND 1),
    explicatie_incredere TEXT,

    -- audit
    hash_continut        TEXT,                 -- amprenta documentului la descoperire (Bronze)
    model                TEXT,                 -- ce model a propus sursa
    stare                TEXT NOT NULL DEFAULT 'propus'
                         CHECK (stare IN ('propus', 'respins', 'folosit')),
    motiv_respingere     TEXT,
    CHECK (stare <> 'respins' OR motiv_respingere IS NOT NULL),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT ux_discovery_libra UNIQUE (id_banca, id_produs_libra, url),
    -- ținta cheii compuse din comparatie_libra (vezi mai jos)
    CONSTRAINT ux_discovery_libra_pereche UNIQUE (id, id_banca, id_produs_libra)
);

CREATE INDEX IF NOT EXISTS ix_discovery_libra_pereche ON discovery_libra (id_banca, id_produs_libra);

COMMENT ON TABLE discovery_libra IS
  'Candidati: unde se gaseste, la o banca, echivalentul unui produs Libra. Propuneri — intra in comparatie_libra abia dupa alegere.';


-- ── comparatie_libra ──────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS comparatie_libra (
    id                BIGSERIAL PRIMARY KEY,
    id_banca          BIGINT NOT NULL REFERENCES banci (id) ON DELETE CASCADE,
    id_produs_libra   BIGINT NOT NULL REFERENCES produse_libra (id) ON DELETE CASCADE,
    id_discovery      BIGINT,                  -- sursa aleasă; NULL doar la „inexistent"

    -- Potrivirea nu e 1:1. Fără coloana asta tabelul arată curat și compară
    -- lucruri diferite: „Credit Hipocrate" nu are echivalent direct nicăieri.
    tip_potrivire     TEXT NOT NULL CHECK (tip_potrivire IN ('echivalent', 'similar', 'inexistent')),
    motiv_potrivire   TEXT NOT NULL,           -- ex. „aceeași perioadă, dar dobândă variabilă"
    denumire_la_banca TEXT,

    -- valorile comparate, pe care le citește interfața; structura se fixează
    -- după primele rezultate reale (ex. {"dobanda": 6.25, "unitate": "%", "termen_luni": 12})
    valori            JSONB,

    -- validare umană (regula echipei: ce propune un LLM trece prin verificare)
    stare             TEXT NOT NULL DEFAULT 'propus'
                      CHECK (stare IN ('propus', 'validat', 'respins')),
    verificat_de      TEXT,
    verificat_la      TIMESTAMPTZ,
    CHECK (stare = 'propus' OR (verificat_de IS NOT NULL AND verificat_la IS NOT NULL)),

    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT ux_comparatie_libra UNIQUE (id_banca, id_produs_libra),
    -- „inexistent" nu are sursă; celelalte trebuie să aibă
    CHECK ((tip_potrivire = 'inexistent') = (id_discovery IS NULL)),
    -- sursa aleasă e a ACELEIAȘI bănci și a ACELUIAȘI produs: fără cheia
    -- compusă, un rând BT ar putea trimite la un citat găsit la BCR
    CONSTRAINT fk_comparatie_discovery FOREIGN KEY (id_discovery, id_banca, id_produs_libra)
        REFERENCES discovery_libra (id, id_banca, id_produs_libra) ON DELETE RESTRICT
);

COMMENT ON TABLE comparatie_libra IS
  'Un rand per banca x produs Libra: echivalentul ales, cat de bun e (tip_potrivire) si sursa lui (id_discovery).';


-- ── vederea pentru interfață ──────────────────────────────────────
-- Tot ce trebuie pe un rând de comparație, inclusiv linkul spre paragraf.

CREATE OR REPLACE VIEW v_comparatie_libra AS
SELECT c.id,
       b.slug            AS banca,
       b.nume            AS nume_banca,
       p.cod             AS cod_produs,
       p.denumire        AS produs_libra,
       p.segment,
       c.tip_potrivire,
       c.motiv_potrivire,
       COALESCE(c.denumire_la_banca, d.denumire_la_banca) AS denumire_la_banca,
       c.valori,
       d.url,
       d.link_live,
       d.pagina_pdf,
       d.citat,
       d.citat_verificat,
       d.incredere,
       c.stare,
       c.verificat_de,
       c.verificat_la,
       c.updated_at
  FROM comparatie_libra c
  JOIN banci b          ON b.id = c.id_banca
  JOIN produse_libra p  ON p.id = c.id_produs_libra
  LEFT JOIN discovery_libra d ON d.id = c.id_discovery;

COMMIT;
