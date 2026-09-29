-- Migrarea 022: catalogul intern Libra înlocuiește valorile colectate de pe web,
-- doar acolo unde le poate înlocui.
--
-- DE CE: Robert a hotărât ca, pentru Libra, prețurile și dobânzile scrise
-- explicit în catalogul intern (`catalog_libra`, migrarea 020) să ia locul
-- celor luate prin scraping. Valorile din catalog intră în `observations` prin
-- ingest/catalog_libra_valori.py, cu `metoda_extractie = 'catalog'`, pe o sursă
-- dedicată fișierului Excel (tip_sursa 'document', format 'xlsx').
--
-- Ce face:
--   1. permite `metoda_extractie = 'catalog'` în observations;
--   2. permite `format = 'xlsx'` în surse (CHECK-ul avea doar html/pdf/xml);
--   3. ASCUNDE — nu șterge — valorile web ale băncilor cu catalog pe care
--      catalogul le acoperă, prin vederea `observatii_inlocuite_de_catalog`,
--      exclusă din `observatii_curente`. Regula completă, cu segmentele, e
--      comentată mai jos (identic cu db/sincronizeaza_vederi.sql, care rămâne
--      definiția curentă a vederilor; aici e copia de la momentul migrării).
--
-- Reversibilă: se reface `observatii_curente` fără condiția NOT EXISTS și
-- totul reapare; nimic nu s-a șters. Idempotentă: rulată de două ori, dă
-- același rezultat.
--
-- (019 e rezervată pentru tabela de campanii.)

BEGIN;

ALTER TABLE observations DROP CONSTRAINT IF EXISTS observations_metoda_extractie_check;
ALTER TABLE observations ADD CONSTRAINT observations_metoda_extractie_check
  CHECK (metoda_extractie IN ('playwright', 'bs4', 'bs4_llm', 'llm', 'manual', 'populare',
                              'catalog'));

ALTER TABLE surse DROP CONSTRAINT IF EXISTS surse_format_check;
ALTER TABLE surse ADD CONSTRAINT surse_format_check
  CHECK (format IN ('html', 'pdf', 'xml', 'xlsx'));

DROP VIEW IF EXISTS observatii_curente;
DROP VIEW IF EXISTS observatii_inlocuite_de_catalog;

-- --------------------------------------------------------------------------
-- Valorile colectate de pe web pe care catalogul intern le ÎNLOCUIEȘTE
-- (migrarea 022). Se ascund în `observatii_curente`, nu se șterg.
--
-- DE CE în vedere și nu în date: o refacere din Bronze recreează observațiile
-- colectate, iar regula trebuie să rămână valabilă fără să se mai ruleze ceva;
-- și e reversibilă (scoți condiția, totul reapare). Vederea asta separată
-- spune exact CE s-a ascuns și în locul căror valori din catalog.
--
-- Băncile: `b.slug IN ('libra')` e lista BANCI_CU_CATALOG din
-- ingest/normalizeaza.py. SQL-ul nu poate citi Python-ul, deci lista stă și
-- aici; testul ingest/test_catalog_valori.py pică dacă cele două diferă.
--
-- O valoare web e ascunsă doar dacă catalogul acoperă ACELAȘI serviciu:
--   - același `camp` și aceeași `unitate` (un preț în lei nu înlocuiește unul
--     în euro), plus aceeași categorie (primul segment din cod_scenariu) la
--     `procent` — altfel o dobândă de depozit ar ascunde una de credit;
--   - segment compatibil: fiecare segment al valorii web trebuie să aibă preț
--     în catalog. Un preț doar pentru firme (pj) NU ascunde valorile marcate pf.
--     `pfa` și `imm` contează ca pj (în catalog, PFA/IMM stau la „persoane
--     juridice").
--   - valoarea web FĂRĂ segment marcat: poate fi pentru oricine, deci se
--     ascunde doar dacă catalogul acoperă AMBELE segmente (pf și pj). Motivul:
--     matricea pe PF include valorile nemarcate; dacă un preț de catalog doar
--     pentru firme le-ar ascunde, coloana PF a Librei ar pierde valori pe care
--     catalogul nu le înlocuiește.
-- Contează doar valorile de catalog curente și neambigue: o valoare de catalog
-- „de verificat" nu are voie să ascundă una observată.
-- --------------------------------------------------------------------------
CREATE VIEW observatii_inlocuite_de_catalog AS
  WITH obs AS (
    SELECT o.id, s.id_banca, o.camp, o.unitate, o.metoda_extractie, o.ambiguu,
           split_part(coalesce(o.cod_scenariu, ''), '|', 1) AS categorie,
           coalesce(o.cod_scenariu, '') ~ '(^|\|)pf(\||$)'           AS pf,
           coalesce(o.cod_scenariu, '') ~ '(^|\|)(pj|pfa|imm)(\||$)' AS pj
    FROM observations o
    JOIN surse s ON s.id = o.id_sursa
    JOIN banci b ON b.id = s.id_banca
    WHERE b.slug IN ('libra')                                   -- BANCI_CU_CATALOG
      AND (o.stare_data IS NULL OR o.stare_data NOT IN ('ISTORIC', 'DUBLURA', 'VIITOR'))
  ), acoperire AS (
    SELECT id_banca, camp, unitate,
           CASE WHEN unitate = 'procent' THEN categorie END AS categorie,
           bool_or(pf) AS pf, bool_or(pj) AS pj,
           array_agg(id ORDER BY id) AS id_catalog
    FROM obs
    WHERE metoda_extractie = 'catalog' AND NOT ambiguu
    GROUP BY 1, 2, 3, 4
  )
  SELECT o.id, o.camp, o.unitate, o.categorie,
         CASE WHEN o.pf AND o.pj THEN 'pf+pj' WHEN o.pf THEN 'pf'
              WHEN o.pj THEN 'pj' ELSE 'nemarcat' END AS segment,
         a.id_catalog
  FROM obs o
  JOIN acoperire a ON a.id_banca = o.id_banca AND a.camp = o.camp
                  AND a.unitate = o.unitate
                  AND (o.unitate <> 'procent' OR a.categorie = o.categorie)
  WHERE o.metoda_extractie IS DISTINCT FROM 'catalog'
    -- segmentele cerute de valoarea web: pf dacă e marcată pf SAU e nemarcată,
    -- pj dacă e marcată pj SAU e nemarcată; fiecare trebuie acoperit de catalog
    AND (NOT (o.pf OR NOT o.pj) OR a.pf)
    AND (NOT (o.pj OR NOT o.pf) OR a.pj);

-- Ce se arată implicit: tot ce nu e o versiune depășită, o dublură, un
-- preț anunțat care nu se aplică încă (VIITOR, migrarea 013) sau o valoare
-- web înlocuită de catalogul intern (migrarea 022, vederea de mai sus).
-- Regula stă aici o singură dată, ca fiecare interogare a aplicației să nu o
-- repete (și să nu o uite).
CREATE VIEW observatii_curente AS
  SELECT * FROM observations o
  WHERE (o.stare_data IS NULL OR o.stare_data NOT IN ('ISTORIC', 'DUBLURA', 'VIITOR'))
    AND NOT EXISTS (SELECT 1 FROM observatii_inlocuite_de_catalog i WHERE i.id = o.id);

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

COMMIT;
