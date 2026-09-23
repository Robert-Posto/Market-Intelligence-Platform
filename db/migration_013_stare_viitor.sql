-- Migrarea 013: starea `VIITOR` — un preț anunțat, încă neintrat în vigoare.
--
-- `crawler/data_document.stare_fata_de()` (codul colegului) întoarce trei
-- stări: IN_VIGOARE, VIITOR, DATA_NECUNOSCUTA. Migrarea 008 a permis doar
-- IN_VIGOARE, ISTORIC, DUBLURA și DATA_NECUNOSCUTA, deci primul document datat
-- în viitor (o ofertă de servicii valabilă din 12.10.2026) a picat pe CHECK la
-- popularea din 23.09.2026 — și, fiind o singură inserare în bloc, a anulat tot
-- lotul.
--
-- VIITOR nu e o eroare: banca a publicat prețul, dar nu se aplică încă. De
-- aceea se PĂSTREAZĂ în tabelă (apare în istoric și în `schimbari_pret`), dar
-- NU se arată printre prețurile curente.
--
-- După rulare:
--   docker exec -i mip-db psql -U mip -d mip < db/sincronizeaza_vederi.sql

ALTER TABLE observations DROP CONSTRAINT IF EXISTS ck_observations_stare_data;
ALTER TABLE observations ADD CONSTRAINT ck_observations_stare_data
  CHECK (stare_data IS NULL OR stare_data IN
         ('IN_VIGOARE', 'VIITOR', 'ISTORIC', 'DUBLURA', 'DATA_NECUNOSCUTA'));
