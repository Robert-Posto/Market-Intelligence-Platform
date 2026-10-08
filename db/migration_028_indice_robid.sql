-- Migrarea 028: `robid` permis în `indici_referinta.indice`.
--
-- `ingest/load_bnr.py` scrie ROBID alături de ROBOR, dar CHECK-ul din
-- schema.sql permitea doar ircc / robor / euribor. Pe baza de colectare
-- constrângerea fusese lărgită de mână, fără migrare; pe serverul de test
-- (mcc-test, 06.10.2026), instalat din schema.sql + migrări, încărcarea a căzut
-- la primul rând: CheckViolation pe (robid, O/N, 5.78, 2026-10-05).
--
-- Idempotent: DROP ... IF EXISTS, apoi constrângerea lărgită.

BEGIN;

ALTER TABLE indici_referinta DROP CONSTRAINT IF EXISTS indici_referinta_indice_check;
ALTER TABLE indici_referinta ADD CONSTRAINT indici_referinta_indice_check
    CHECK (indice IN ('ircc', 'robor', 'robid', 'euribor'));

COMMIT;
