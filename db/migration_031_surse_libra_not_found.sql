-- Migrarea 031 (fluxul extragere_produse_bancare): surse_libra.not_found — produsul Libra nu a fost găsit la bancă.
--
-- DE CE: „nu există la BT" e un rezultat, nu o lipsă de date. Fără un rând
-- pentru el, o pereche bancă × produs fără surse arată la fel cu una pe care
-- nu am căutat-o încă.
--
-- Un rând not_found = TRUE nu are URL, tip, rol sau citat; motivul stă în
-- explicatie_incredere (ex. „[produs_inexistent] BT a aderat la RoPay doar
-- pentru persoane fizice"). Coloanele devin opționale DOAR pentru aceste
-- rânduri: un rând găsit le cere în continuare pe toate.
--
-- Idempotentă.

BEGIN;

ALTER TABLE surse_libra ADD COLUMN IF NOT EXISTS not_found BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE surse_libra ALTER COLUMN url       DROP NOT NULL;
ALTER TABLE surse_libra ALTER COLUMN tip       DROP NOT NULL;
ALTER TABLE surse_libra ALTER COLUMN rol       DROP NOT NULL;
ALTER TABLE surse_libra ALTER COLUMN citat     DROP NOT NULL;
ALTER TABLE surse_libra ALTER COLUMN incredere DROP NOT NULL;

ALTER TABLE surse_libra DROP CONSTRAINT IF EXISTS ck_surse_libra_not_found;
ALTER TABLE surse_libra ADD CONSTRAINT ck_surse_libra_not_found CHECK (
    CASE WHEN not_found
         THEN url IS NULL AND explicatie_incredere IS NOT NULL      -- negăsit: fără adresă, cu motiv
         ELSE url IS NOT NULL AND tip IS NOT NULL AND rol IS NOT NULL
              AND citat IS NOT NULL AND incredere IS NOT NULL       -- găsit: tot ce era obligatoriu
    END);

-- cel mult un rând „negăsit" per bancă × produs (UNIQUE pe url nu-l prinde: url e NULL)
CREATE UNIQUE INDEX IF NOT EXISTS ux_surse_libra_not_found
    ON surse_libra (id_banca, id_produs_libra) WHERE not_found;

COMMENT ON COLUMN surse_libra.not_found IS
  'TRUE = discovery-ul nu a gasit produsul Libra (sau un echivalent) la banca. Fara url; motivul in explicatie_incredere.';

COMMIT;
