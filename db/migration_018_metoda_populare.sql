-- Migrarea 018: proveniența `populare` permisă în observations.
--
-- `ingest/populare_initiala.py` scrie `metoda_extractie = 'populare'`, dar
-- CHECK-ul din migrarea 007 permite doar playwright, bs4, bs4_llm, llm și
-- manual. Pe o bază adusă doar cu migrările din repo, popularea de la zero din
-- 24.09.2026 a picat la scriere pe fiecare bancă cu rezultate (bankofchina,
-- bid, brci, cetelem, credex, creditcoop…), iar observations a rămas goală.
-- Bronze-ul și sursele se scriseseră, deci refacerea e `--din-bronze`.

ALTER TABLE observations DROP CONSTRAINT IF EXISTS observations_metoda_extractie_check;
ALTER TABLE observations ADD CONSTRAINT observations_metoda_extractie_check
  CHECK (metoda_extractie IN ('playwright', 'bs4', 'bs4_llm', 'llm', 'manual', 'populare'));
