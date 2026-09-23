-- Migrarea 004: locatii fizice (sucursale si ATM-uri).
--
-- Corespunde secțiunii 2.5 din PDF-ul de arhitectura („Numar si localizare
-- sucursale/ATM, program"). Tabel separat de `surse`/`observations`: o locatie
-- nu e o valoare extrasa dintr-un document, e o entitate cu coordonate.
--
-- `sursa` spune de unde vine randul, ca sa nu se confunde datele de test cu
-- cele reale: 'mock' pentru datele de testare a hartii, 'google_places' cand
-- se conecteaza API-ul, 'locator_banca' pentru scraping din locatorul propriu
-- al bancii, 'onrc' pentru verificarea incrucisata din registru.

CREATE TABLE IF NOT EXISTS locatii (
    id           BIGSERIAL PRIMARY KEY,
    id_banca     BIGINT NOT NULL REFERENCES banci (id) ON DELETE CASCADE,
    tip          TEXT NOT NULL CHECK (tip IN ('sucursala', 'atm')),
    nume         TEXT,
    adresa       TEXT,
    oras         TEXT,
    sector       TEXT,
    lat          NUMERIC(9, 6) NOT NULL,
    lon          NUMERIC(9, 6) NOT NULL,
    program      TEXT,
    sursa        TEXT NOT NULL CHECK (sursa IN ('mock', 'google_places', 'locator_banca', 'onrc')),
    observat_la  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (id_banca, tip, lat, lon)
);

CREATE INDEX IF NOT EXISTS ix_locatii_banca ON locatii (id_banca);
CREATE INDEX IF NOT EXISTS ix_locatii_tip   ON locatii (tip);
CREATE INDEX IF NOT EXISTS ix_locatii_geo   ON locatii (lat, lon);
