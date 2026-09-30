-- Migrarea 026: istoricul aplicațiilor iOS se păstrează; descrierea se salvează.
--
-- Până acum `ingest/load_mobil.py` ștergea la fiecare rulare toate rândurile
-- iOS din `app_release` și `app_screenshot`, apoi le rescria: o versiune sau o
-- captură de ieri dispărea, deci nu se putea vedea ce și-a schimbat banca în
-- magazin (Nicolae, §4.5 punctul 2 și §10.1 punctul 5). Acum rândurile se
-- actualizează (upsert pe constrângerile unice existente) și poartă
-- `vazut_ultima`: data ultimei rulări care le-a văzut. Starea „de acum” se
-- citește din vederile de mai jos, nu se obține ștergând trecutul.
--
-- `descriere`: câmpul `description` din Lookup, textul de marketing al
-- aplicației, care nu se salva deloc.
--
-- Idempotentă: se poate rula de mai multe ori.

ALTER TABLE app_release ADD COLUMN IF NOT EXISTS descriere TEXT;
COMMENT ON COLUMN app_release.descriere IS
  'Descrierea aplicației din App Store (câmpul `description` din iTunes Lookup).';

ALTER TABLE app_release    ADD COLUMN IF NOT EXISTS vazut_ultima TIMESTAMPTZ;
ALTER TABLE app_screenshot ADD COLUMN IF NOT EXISTS vazut_ultima TIMESTAMPTZ;
-- Rândurile existente au fost văzute ultima oară când au fost scrise.
UPDATE app_release    SET vazut_ultima = observat_la WHERE vazut_ultima IS NULL;
UPDATE app_screenshot SET vazut_ultima = observat_la WHERE vazut_ultima IS NULL;
ALTER TABLE app_release    ALTER COLUMN vazut_ultima SET DEFAULT now();
ALTER TABLE app_release    ALTER COLUMN vazut_ultima SET NOT NULL;
ALTER TABLE app_screenshot ALTER COLUMN vazut_ultima SET DEFAULT now();
ALTER TABLE app_screenshot ALTER COLUMN vazut_ultima SET NOT NULL;
COMMENT ON COLUMN app_release.vazut_ultima IS
  'Ultima rulare load_mobil.py care a văzut versiunea în magazin; `observat_la` e prima.';
COMMENT ON COLUMN app_screenshot.vazut_ultima IS
  'Ultima rulare load_mobil.py care a văzut captura; `observat_la` e prima.';

-- Starea curentă, pentru afișare: ultima versiune văzută pe bancă și
-- platformă, și capturile din ultima rulare care a văzut banca (o rulare
-- scrie totul într-o tranzacție, deci `now()` e același pe toate capturile ei).
CREATE OR REPLACE VIEW app_release_curente AS
SELECT DISTINCT ON (id_banca, platforma) *
FROM app_release
ORDER BY id_banca, platforma, vazut_ultima DESC, id DESC;

CREATE OR REPLACE VIEW app_screenshot_curente AS
SELECT sh.*
FROM app_screenshot sh
WHERE sh.vazut_ultima = (SELECT max(x.vazut_ultima) FROM app_screenshot x
                         WHERE x.id_banca = sh.id_banca AND x.platforma = sh.platforma);
