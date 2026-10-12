-- Migrarea 043: istoric în valori_referinta și datele valorii (extragere, citat, document).
--
-- DE CE: până acum consolideaza_referinta.py ștergea rândurile bazei și le rescria, deci se vedea
-- doar ultima cifră. Acum fiecare rulare adaugă rânduri noi (`generat_la` le grupează: now() e
-- același pe toată tranzacția), iar paginile citesc ultima rulare din vederea
-- valori_referinta_curente. Plus trei date, ca o cifră dintr-un document vechi să se poată vedea:
--
--   data_extragere  ziua în care modelul a citit valoarea (comparatie_libra.data_colectare);
--                   un document neschimbat nu se re-extrage, deci data rămâne cea a citirii
--   data_citat      data de la valoarea însăși: „valabil începând cu 30.03.2026” lângă cifră
--                   (valabil_de_la al modelului sau condiția „valabil începând cu ...”)
--   data_document   data documentului din care vine valoarea, cu `data_document_sursa`:
--                     text                textul documentului („în vigoare începând cu ...”)
--                     pdf_modificat       metadatele PDF, ModDate
--                     pdf_creat           metadatele PDF, CreationDate
--                     http_last_modified  antetul Last-Modified al serverului
--
-- comparatie_libra (și copia v1) primesc aceleași coloane: le scrie extrage_comparatie_libra.py,
-- iar consolideaza_referinta.py le copiază de pe rândul ales.
--
-- Idempotentă.

BEGIN;

-- ── comparatie_libra: datele, pe fiecare valoare extrasă ─────────────

ALTER TABLE comparatie_libra
    ADD COLUMN IF NOT EXISTS valabil_de_la       DATE,
    ADD COLUMN IF NOT EXISTS data_document       DATE,
    ADD COLUMN IF NOT EXISTS data_document_sursa TEXT
        CHECK (data_document_sursa IN ('text', 'pdf_modificat', 'pdf_creat', 'http_last_modified'));

ALTER TABLE IF EXISTS comparatie_libra_v1
    ADD COLUMN IF NOT EXISTS valabil_de_la       DATE,
    ADD COLUMN IF NOT EXISTS data_document       DATE,
    ADD COLUMN IF NOT EXISTS data_document_sursa TEXT;

-- ── valori_referinta: datele și istoricul ────────────────────────────

ALTER TABLE valori_referinta
    ADD COLUMN IF NOT EXISTS data_extragere      DATE,
    ADD COLUMN IF NOT EXISTS data_citat          DATE,
    ADD COLUMN IF NOT EXISTS data_document       DATE,
    ADD COLUMN IF NOT EXISTS data_document_sursa TEXT
        CHECK (data_document_sursa IN ('text', 'pdf_modificat', 'pdf_creat', 'http_last_modified'));

-- o cheie poate avea acum câte un rând pe rulare
ALTER TABLE valori_referinta DROP CONSTRAINT IF EXISTS valori_referinta_baza_id_banca_id_produs_libra_camp_cheie_key;
CREATE INDEX IF NOT EXISTS ix_valori_referinta_rulare
    ON valori_referinta (baza, id_banca, id_produs_libra, generat_la DESC);

-- rândurile scrise înainte de migrare: data extragerii, de pe rândul ales, dacă mai există
UPDATE valori_referinta v SET data_extragere = c.data_colectare
  FROM comparatie_libra c
 WHERE v.baza = 'curent' AND v.data_extragere IS NULL AND c.id = v.id_comparatie;

-- ── ultima rulare pe pereche: ce citesc paginile ─────────────────────
--
-- Pe pereche bancă × produs, nu pe cheie: așa ștergea și vechiul DELETE. Un câmp scos din
-- fise_produse.json nu mai apare în rularea nouă, deci nici în pagini (pe cheie ar fi rămas
-- la nesfârșit cu cifra ultimei rulări în care exista).

CREATE OR REPLACE VIEW valori_referinta_curente AS
SELECT v.*
  FROM valori_referinta v
 WHERE v.generat_la = (SELECT max(x.generat_la) FROM valori_referinta x
                        WHERE x.baza = v.baza AND x.id_banca = v.id_banca
                          AND x.id_produs_libra = v.id_produs_libra);

COMMENT ON VIEW valori_referinta_curente IS
  'Rândurile ultimei rulări din valori_referinta, pe baza × bancă × produs Libra; istoricul rămâne în tabelă.';

COMMIT;
