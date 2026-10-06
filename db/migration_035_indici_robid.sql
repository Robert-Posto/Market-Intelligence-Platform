-- Migrarea 035: indici_referinta acceptă și ROBID.
--
-- DE CE: ingest/load_bnr.py colectează de pe www.bnr.ro ROBID, ROBOR și IRCC
-- (commitul 92eac95), dar CHECK-ul din schema.sql permitea doar ircc, robor și
-- euribor. Pe o bază construită din repo, prima valoare ROBID oprea toată
-- încărcarea (CheckViolation, 05.10.2026), deci tabela rămânea goală și 2.2 / 2.6
-- nu aveau indici.
--
-- Idempotentă: constrângerea se reface cu aceeași listă, plus robid.

BEGIN;

ALTER TABLE indici_referinta DROP CONSTRAINT IF EXISTS indici_referinta_indice_check;
ALTER TABLE indici_referinta ADD CONSTRAINT indici_referinta_indice_check
    CHECK (indice IN ('ircc', 'robor', 'robid', 'euribor'));

COMMIT;
