-- Migrarea 023: valorile luate din pagini de campanie și din regulamente de
-- campanie nu mai apar ca prețuri standard ale băncii.
--
-- DE CE: în comparațiile de prețuri (paginile Produse și Rate, prin vederea
-- `observatii_curente`) intrau valori de pe pagini de promoții, campanii
-- încheiate și regulamente de campanie, ca și cum ar fi prețurile curente.
-- Cazul cel mai grav: Cetelem apărea cu 0% dobândă nominală la credite, pentru
-- că toate dobânzile ei veneau din `cetelem.ro/promotii-credite-*` (rate fără
-- dobândă la magazine partenere). La fel, Garanti apărea cu 6,50–6,75% la
-- depozite din `campanii-incheiate/...` (campanii terminate; dobânzile ei
-- standard sunt 4–5,10%), iar regulamentele puneau premii și bugete de
-- campanie („112.500 lei", „1.247.118,80 lei") printre comisioane.
--
-- Ce face: ASCUNDE — nu șterge — aceste valori, prin vederea
-- `observatii_din_campanii`, exclusă din `observatii_curente`. Același model ca
-- migrarea 022. Regula completă e comentată mai jos (identic cu
-- db/sincronizeaza_vederi.sql, care rămâne definiția curentă a vederilor; aici
-- e copia de la momentul migrării).
--
-- Reversibilă: se reface `observatii_curente` fără condiția nouă și totul
-- reapare; nimic nu s-a șters. Idempotentă: rulată de două ori, dă același
-- rezultat. Nu adaugă coloane.
--
-- (019 rămâne rezervată tabelei de campanii; când va exista, regula de aici
-- poate citi din ea în loc de URL.)

BEGIN;

DROP VIEW IF EXISTS observatii_curente;
DROP VIEW IF EXISTS observatii_inlocuite_de_catalog;
DROP VIEW IF EXISTS observatii_din_campanii;

-- --------------------------------------------------------------------------
-- Valorile catalogului intern: identic cu migrarea 022, recreată doar pentru
-- că `observatii_curente` depinde de ea.
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
    AND (NOT (o.pf OR NOT o.pj) OR a.pf)
    AND (NOT (o.pj OR NOT o.pf) OR a.pj);

-- >>> observatii_din_campanii (bloc identic în sincronizeaza_vederi.sql; testul
--     ingest/test_valori_din_campanii.py pică dacă cele două diferă)
-- --------------------------------------------------------------------------
-- Valorile venite din pagini de CAMPANIE / PROMOȚIE sau din REGULAMENTE de
-- campanie (migrarea 023). Se ascund în `observatii_curente`, nu se șterg.
--
-- DE CE după URL: `populare_initiala.py --de-la-zero` recreează observațiile
-- și poate recrea sursele, deci id-urile se schimbă; URL-ul rămâne. Nu există
-- încă o tabelă de campanii (019), iar `rol`/`tip_sursa` nu disting o campanie
-- de o pagină de produs.
--
-- Regula se aplică pe calea URL-ului (fără domeniu), cu litere mici și cu
-- %20 citit ca spațiu:
--   - 'regulament': calea conține „regulament". Regulamentele publicate de
--     bănci sunt, practic, ale campaniilor (legea cere regulament pentru
--     campaniile cu premii); tarifele stau în „liste de tarife" și „condiții
--     generale", nu în regulamente. EXCEPȚIE: regulamentele unor programe
--     permanente ale produsului, care nu sunt campanii și rămân vizibile:
--       plata-in-rate        BCR, programul de plată în rate al cardului de cumpărături
--       regulament-beneficii Raiffeisen, beneficiile cardurilor Visa Signature/Infinite
--       program-loialitate   Raiffeisen, programul de loialitate al cardului eMAG
--   - 'campanie': calea conține unul dintre cuvintele de mai jos. Fiecare a
--     fost verificat pe URL-urile din bază (29.09.2026):
--       campani, campaign, campain   campanie, campanii-incheiate, ended-campains (sic, Garanti)
--       \mpromo\M, promoti           Depozitul-Promo, promotii-credite, dobanda-promotionala
--                                    (nu „promovare": materialele de promovare TBI)
--       concurs                      BRD concursYOU, concursul 10 lucrări de 10
--       oferta-/oferte-speciale
--       castiga, castigi (cuvânt)    castiga-ti-bicicleta, Castiga cu cardul tau
--                                    (nu „castigam": interviul Exim despre cota de piață)
--       premii (cuvânt), premiaz     premii-de-95-000-de-lei (nu „premium")
--       bonus-<cifră>                bonus-500-lei-la-creditul-imobiliar (nu „bonus-card",
--                                    care e numele cardului Garanti)
--       rate-fara-dobanda            6-rate-fara-dobanda-prin-cardul-credex
--       tombola
--   Cuvinte lăsate intenționat afară: „oferta"/„oferte" (ProCredit
--   oferta-credite-imobiliare e oferta standard; BRD card-de-credit-oferte e
--   pagina produsului), „landing" (ProCredit landing/progreen-imobiliar e
--   produsul ProHome), „special" (conturi speciale pentru fonduri europene),
--   „black-friday" (articol de blog Raiffeisen, nu campanie).
--
-- EXCEPȚII (`exceptii` de mai jos): valori dintr-o sursă de campanie care sunt
-- totuși prețul real, curent al băncii. Rămân vizibile; coloana `exceptie` spune
-- de ce. Listă explicită, pe tiparul URL-ului (întreg, cu domeniu) și pe câmp —
-- conservator: o dobândă 0% la credit dintr-o promoție la magazine partenere nu
-- e prețul standard, deci nu intră aici. De confirmat de Robert.
--
-- Nu intră ca excepție, deși s-ar părea:
--   - BCR, depozitul promo pe 5 luni la 6%: valoarea e deja pe pagina
--     produsului (bcr.ro/.../depozitul-la-termen, vizibilă), iar în regulament
--     e extrasă ca `comision`, amestecată cu praguri de 2.000/3.000 lei.
--   - Garanti, depozitele Small Fresh Funds: toate sunt din campanii-incheiate
--     / ended-campains, deci nu mai sunt oferta curentă.
--   - ProCredit, conturile de economii PJ la 5,40% (Regulament-SA-PJ, 1 aug –
--     31 oct 2026): promoția e curentă, dar valoarea e extrasă cu categoria
--     `credite|pj`, deci ar apărea printre dobânzile la credite.
-- --------------------------------------------------------------------------
CREATE VIEW observatii_din_campanii AS
  -- Vederea se calculează la FIECARE citire a `observatii_curente`, deci
  -- contează viteza: LIKE în colația "C" (cu en_US.utf8, lower/LIKE pe toate
  -- sursele costau ~100 ms), un filtru ieftin înainte de orice expresie
  -- regulată, iar expresiile regulate doar unde e nevoie de margine de cuvânt
  -- (o alternanță mare cu \m...\M costa peste 1 s pe toate sursele).
  WITH url AS MATERIALIZED (
    -- filtrul ieftin: fiecare cuvânt al regulii conține unul dintre
    -- fragmentele astea; un cuvânt nou în regulă își pune fragmentul aici
    SELECT s.id, s.id_banca, s.sursa,
           replace(replace(lower(s.sursa COLLATE "C"), '%2520', ' '), '%20', ' ') AS url
    FROM surse s
    WHERE lower(s.sursa COLLATE "C") LIKE ANY (ARRAY[
      '%regulament%', '%campa%', '%promo%', '%concurs%', '%oferta-special%',
      '%oferte-special%', '%castig%', '%premi%', '%bonus-%', '%rate-fara-dobanda%',
      '%tombola%'])
  ), clasificate AS (
    SELECT u.*,
           CASE
             WHEN cale LIKE '%regulament%'
              AND NOT cale LIKE ANY (ARRAY['%plata-in-rate%', '%regulament-beneficii%',
                                           '%program-loialitate%'])
               THEN 'regulament'
             WHEN cale LIKE ANY (ARRAY['%campani%', '%campaign%', '%campain%', '%promoti%',
                                       '%concurs%', '%oferta-speciala%', '%oferte-speciale%',
                                       '%premiaz%', '%rate-fara-dobanda%', '%tombola%'])
               OR (cale LIKE '%promo%'  AND cale ~ '\mpromo\M')
               OR (cale LIKE '%castig%' AND cale ~ 'castig[ai]\M')
               OR (cale LIKE '%premii%' AND cale ~ 'premii\M')
               OR cale ~ 'bonus-[0-9]'
               THEN 'campanie'
           END AS tip
    FROM (SELECT url.*, regexp_replace(url.url, '^[a-z]+://[^/]*', '') AS cale FROM url) u
  ), exceptii (tipar, campuri, motiv) AS (VALUES
    -- Regulamentele BRD „24 de rate fără dobândă oriunde în lume" și „Card de
    -- credit 2500 eur" (2026) citează „exemplul reprezentativ" al cardului de
    -- credit Standard/Gold: dobândă fixă 26%, DAE 30,82% / 30,43%. Nu e un preț
    -- de campanie (campania dă rate fără dobândă, respectiv un premiu), ci
    -- dobânda standard a cardului, iar pagina cardului nu o are. Doar nominala
    -- și DAE; restul (sume totale plătibile, praguri) rămân ascunse.
    ('^https?://(www\.)?brd\.ro/.*regulament[ _]campanie[ _]+_?(24 de rate fara dobanda|carddecredit)',
     ARRAY['nominala', 'dae'],
     'BRD: dobânda standard a cardului de credit din exemplul reprezentativ, nu preț de campanie')
  )
  SELECT o.id, o.id_sursa, c.id_banca, o.camp, c.tip,
         (SELECT e.motiv FROM exceptii e
           WHERE c.url ~ e.tipar AND o.camp = ANY (e.campuri) LIMIT 1) AS exceptie,
         c.sursa
  FROM clasificate c
  JOIN observations o ON o.id_sursa = c.id
  WHERE c.tip IS NOT NULL;
-- <<< observatii_din_campanii

-- Ce se arată implicit: tot ce nu e o versiune depășită, o dublură, un
-- preț anunțat care nu se aplică încă (VIITOR, migrarea 013), o valoare
-- web înlocuită de catalogul intern (migrarea 022) sau o valoare dintr-o
-- campanie / un regulament de campanie (migrarea 023), în afară de excepții.
-- Regula stă aici o singură dată, ca fiecare interogare a aplicației să nu o
-- repete (și să nu o uite).
CREATE VIEW observatii_curente AS
  SELECT * FROM observations o
  WHERE (o.stare_data IS NULL OR o.stare_data NOT IN ('ISTORIC', 'DUBLURA', 'VIITOR'))
    AND NOT EXISTS (SELECT 1 FROM observatii_inlocuite_de_catalog i WHERE i.id = o.id)
    -- NOT IN, nu NOT EXISTS: Postgres o calculează o singură dată, ca tabelă
    -- hash. Cu NOT EXISTS, planificatorul subestima vederea și o recalcula
    -- pentru fiecare rând (/api/rate: de la 0,5 s la 4 s). `id` e cheie
    -- primară, deci nu e NULL și NOT IN nu are capcana cu NULL.
    AND o.id NOT IN (SELECT c.id FROM observatii_din_campanii c WHERE c.exceptie IS NULL);

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
