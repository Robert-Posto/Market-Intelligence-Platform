-- Migrarea 008: istoricul valorilor — data de vigoare și starea versiunii.
--
-- Prima încărcare arunca istoricul: excludea `stare_data IN (ISTORIC, DUBLURA)`
-- și nu păstra deloc `data_vigoare`. Motivul de atunci era corect (fără filtru,
-- tarifele BCR din martie intrau peste cele din august și agregatele erau
-- false), dar soluția era greșită: filtrul aparține AFIȘĂRII, nu încărcării.
-- Măsurat în pachetul sursă: 22 date de vigoare distincte, 31 rânduri ISTORIC,
-- 427 DUBLURA, și 27 de servicii unde același comision are preț diferit la date
-- diferite — de exemplu BCR „Transfer credit intrabancar la ghișeu": 15 lei la
-- 2024-06-14, 30 lei la 2024-06-19. Exact ce vrea să vadă cineva care urmărește
-- concurența, și exact ce se pierdea.
--
-- Filozofia e cea din figura 1 a artefactului: se încarcă tot, se marchează
-- versiunea, iar interfața arată implicit doar ce e în vigoare. Schimbarea de
-- preț („change_event") e produsul, nu un efect secundar.

ALTER TABLE observations ADD COLUMN IF NOT EXISTS data_vigoare DATE;
ALTER TABLE observations ADD COLUMN IF NOT EXISTS stare_data   TEXT;

-- Vocabularul e cel din pachetul sursă (data_document.py), plus NULL pentru
-- observațiile fără datare (ratele din HTML: pagina nu declară o dată de
-- vigoare, deci a pretinde una ar fi invenție).
ALTER TABLE observations DROP CONSTRAINT IF EXISTS ck_observations_stare_data;
ALTER TABLE observations ADD CONSTRAINT ck_observations_stare_data
  CHECK (stare_data IS NULL OR stare_data IN
         ('IN_VIGOARE', 'ISTORIC', 'DUBLURA', 'DATA_NECUNOSCUTA'));

CREATE INDEX IF NOT EXISTS ix_observations_vigoare
  ON observations (data_vigoare DESC) WHERE data_vigoare IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_observations_stare
  ON observations (stare_data);

-- Ce se arată implicit: tot ce nu e o versiune depășită sau o dublură.
-- Vederea există ca regula să fie scrisă o singură dată, nu repetată în
-- fiecare interogare a aplicației.
CREATE OR REPLACE VIEW observatii_curente AS
  SELECT * FROM observations
  WHERE stare_data IS NULL OR stare_data NOT IN ('ISTORIC', 'DUBLURA');

-- Schimbările de preț: același serviciu, la aceeași bancă, cu valori diferite
-- la date de vigoare diferite. `lag` peste data de vigoare dă valoarea
-- anterioară; se păstrează doar rândurile unde valoarea s-a schimbat efectiv.
-- Nu e un tabel, ci o vedere: se recalculează din observații, deci nu poate
-- rămâne desincronizată de ele.
CREATE OR REPLACE VIEW schimbari_pret AS
  WITH pasi AS (
    SELECT b.slug AS banca, b.nume AS banca_nume, o.camp, o.serviciu, o.unitate,
           o.data_vigoare, o.valoare_num, o.citat, o.pagina,
           s.sursa, s.url_public, o.metoda_extractie,
           lag(o.valoare_num)  OVER w AS valoare_ant,
           lag(o.data_vigoare) OVER w AS data_ant
    FROM observations o
    JOIN surse s ON s.id = o.id_sursa
    JOIN banci b ON b.id = s.id_banca
    WHERE o.data_vigoare IS NOT NULL AND o.valoare_num IS NOT NULL
      AND o.stare_data <> 'DUBLURA'
    WINDOW w AS (PARTITION BY b.slug, o.camp, o.serviciu, o.unitate
                 ORDER BY o.data_vigoare, o.valoare_num)
  )
  SELECT banca, banca_nume, camp, serviciu, unitate,
         data_ant, valoare_ant, data_vigoare AS data_noua, valoare_num AS valoare_noua,
         (valoare_num - valoare_ant) AS delta,
         CASE WHEN valoare_ant = 0 THEN NULL
              ELSE round(100 * (valoare_num - valoare_ant) / valoare_ant, 1) END AS delta_pct,
         citat, pagina, sursa, url_public, metoda_extractie
  FROM pasi
  WHERE valoare_ant IS NOT NULL AND valoare_ant <> valoare_num
    AND data_ant <> data_vigoare;
