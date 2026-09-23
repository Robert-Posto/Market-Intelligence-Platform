-- Recreează vederile peste `observations`. DE RULAT DUPĂ ORICE MIGRARE care
-- adaugă o coloană în `observations`.
--
-- De ce e nevoie: `observatii_curente` e definită cu `SELECT *`, iar Postgres
-- expandează `*` la momentul creării și îngheață lista de coloane. O coloană
-- adăugată ulterior NU apare în vedere, iar o interogare care o cere prin
-- vedere cade cu „column o.motiv_ambiguu does not exist" — adică API-ul
-- răspunde 500, deși tabela are coloana. S-a întâmplat la migrarea 010.
--
-- Rulare:
--   docker exec -i mip-db psql -U mip -d mip < db/sincronizeaza_vederi.sql

DROP VIEW IF EXISTS observatii_curente;

-- Ce se arată implicit: tot ce nu e o versiune depășită, o dublură sau un
-- preț anunțat care nu se aplică încă (VIITOR, migrarea 013).
-- Regula stă aici o singură dată, ca fiecare interogare a aplicației să nu o
-- repete (și să nu o uite).
CREATE VIEW observatii_curente AS
  SELECT * FROM observations
  WHERE stare_data IS NULL OR stare_data NOT IN ('ISTORIC', 'DUBLURA', 'VIITOR');

-- Verificare: vederea trebuie să expună exact coloanele tabelei. Dacă nu,
-- oprim cu eroare în loc să lăsăm API-ul să cadă mai târziu cu 500.
DO $$
DECLARE lipsa TEXT;
BEGIN
  SELECT string_agg(column_name, ', ') INTO lipsa
  FROM information_schema.columns t
  WHERE t.table_name = 'observations'
    AND NOT EXISTS (
      SELECT 1 FROM information_schema.columns v
      WHERE v.table_name = 'observatii_curente' AND v.column_name = t.column_name);
  IF lipsa IS NOT NULL THEN
    RAISE EXCEPTION 'observatii_curente nu expune coloanele: %', lipsa;
  END IF;
  RAISE NOTICE 'observatii_curente e sincronizată cu observations';
END $$;
