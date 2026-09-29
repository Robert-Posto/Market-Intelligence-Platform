-- Migrarea 020: catalogul intern de produse Libra (referință, nu colectare).
--
-- DE CE: produsele Libra vin dintr-un export intern (Sales Command Center,
-- „Catalog produse"), nu de pe web. Robert a hotărât că pentru Libra nu se mai
-- face scraping pe produse; catalogul devine REFERINȚA după care se va colecta
-- ulterior (de la celelalte bănci, sau pentru comparație).
--
-- DE CE tabel separat și nu `observations`: acolo stau doar valorile colectate
-- de pe web, fiecare cu citat și sursă. Un rând din catalog nu are URL, nu are
-- citat și nu e o valoare observată; amestecat acolo ar strica regula
-- „fiecare cifră are sursă verificabilă".
--
-- DE CE și `rand_brut` (jsonb): fidelitate. Coloanele structurate sunt o
-- comoditate de interogare; dacă exportul primește coloane noi sau valori pe
-- care nu le-am prevăzut, nimic din rândul original nu se pierde.
--
-- Cheia (fisier, foaie, rand) face reîncărcarea idempotentă: același fișier
-- încărcat de două ori nu dublează nimic (upsert), iar rândurile care au
-- dispărut din fisier se șterg de script, pentru acel fișier.
--
-- (019 e rezervată pentru tabela de campanii.)

CREATE TABLE IF NOT EXISTS catalog_libra (
    id                   BIGSERIAL PRIMARY KEY,
    id_banca             BIGINT NOT NULL REFERENCES banci (id) ON DELETE RESTRICT,

    -- coloanele exportului, ca atare (goluri -> NULL; textul e doar tăiat la capete)
    cod                  TEXT NOT NULL,             -- „Cod", ex. ABONAMENT_ELITE
    denumire             TEXT NOT NULL,             -- „Denumire"
    categorie            TEXT,                      -- „Categorie produs", cu codul în paranteză
    categorie_cod        TEXT,                      -- codul din paranteza finală a categoriei
    produs_prioritar     BOOLEAN NOT NULL DEFAULT FALSE, -- „Produs prioritar" = „Da"
    tip_produs           TEXT,                      -- „Tip produs" (completat rar, text liber)
    adresabilitate       TEXT,                      -- „Adresabilitate", textul exportului
    segment              TEXT CHECK (segment IN ('PF', 'PJ', 'PF+PJ')),
                         -- derivat din adresabilitate: „Doar persoane fizice" -> PF,
                         -- „Doar persoane juridice" -> PJ, „Oricine (PF și PJ)" -> PF+PJ;
                         -- NULL dacă apare o formulare nouă (se completează la revizuire)
    caracteristici       TEXT,                      -- „Caracteristicile produsului"
    criterii_eligibilitate TEXT,                    -- „Criterii de eligibilitate"
    cand_recomand        TEXT,                      -- „Când să recomand acest produs"
    beneficiu_client     TEXT,                      -- „Beneficiu pentru client"
    sursa_document       TEXT,                      -- „Sursa / document intern"
    cifra_afaceri_min    NUMERIC,                   -- lei
    cifra_afaceri_max    NUMERIC,                   -- lei
    angajati_min         INTEGER,
    vechime_min_ani      NUMERIC,
    vechime_max_ani      NUMERIC,
    linii_business       TEXT,                      -- „Linii de business eligibile", listă ca text
    caen_prefixe         TEXT,                      -- „CAEN eligibile (prefixe)", listă ca text

    -- rândul complet, cu numele coloanelor din antet exact ca în fișier
    rand_brut            JSONB NOT NULL,

    -- proveniența
    fisier               TEXT NOT NULL,             -- numele fișierului Excel
    foaie                TEXT NOT NULL,
    rand                 INTEGER NOT NULL,          -- numărul rândului în foaie (antetul e 1)
    generat_la           TIMESTAMP,                 -- „Generat la" din foaia Sumar (ora din export)
    importat_la          TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT ux_catalog_libra_rand UNIQUE (fisier, foaie, rand)
);

CREATE INDEX IF NOT EXISTS ix_catalog_libra_cod       ON catalog_libra (id_banca, cod);
CREATE INDEX IF NOT EXISTS ix_catalog_libra_categorie ON catalog_libra (categorie_cod);

COMMENT ON TABLE catalog_libra IS
  'Catalogul intern de produse Libra (export Sales Command Center). Referinta pentru colectarea viitoare; NU sunt valori observate pe web, deci nu intra in observations.';
