-- Migrarea 025: completează regula din 023 (vederea `observatii_din_campanii`).
--
-- DE CE: două cazuri lăsate vizibile în 023 ca incerte au fost decise de
-- Robert pe 29.09: se ASCUND și ele.
--   1. Programul de loialitate al cardului eMAG (Raiffeisen,
--      `regulament-aa1-aa2-aa3-program-loialitate-card-emag`): 76 de valori
--      curente, procente de puncte (1–3%) citite ca `comision` /
--      `modificare_credit`. Iese din lista programelor permanente.
--   2. Paginile TBI `landing-pages/lcp-*`: finanțări la comercianți parteneri
--      (0% pe 4 rate, exemple de 15–35%, cu categoria greșită `depozite` /
--      `curs`). Intră ca 'campanie'.
-- Restul regulii și excepția BRD (dobânda standard a cardului de credit)
-- rămân ca în 023.
--
-- Ce face: redefinește doar `observatii_din_campanii`, cu aceleași coloane
-- (CREATE OR REPLACE), deci `observatii_curente` nu trebuie refăcută: o
-- citește la fiecare cerere. Nu șterge nimic.
--
-- Idempotentă: rulată de două ori, dă același rezultat. Reversibilă: se
-- rulează din nou blocul din 023.

BEGIN;

-- >>> observatii_din_campanii (bloc identic în sincronizeaza_vederi.sql și în
--     ultima migrare care îl redefinește, acum 025; testul
--     ingest/test_valori_din_campanii.py pică dacă diferă)
-- --------------------------------------------------------------------------
-- Valorile venite din pagini de CAMPANIE / PROMOȚIE sau din REGULAMENTE de
-- campanie (migrarea 023, completată de 025). Se ascund în
-- `observatii_curente`, nu se șterg.
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
--     Programul de loialitate al cardului eMAG (Raiffeisen, `program-loialitate`)
--     a fost aici în 023; din 025 se ascunde, la decizia lui Robert (29.09):
--     cele 76 de valori sunt procente de puncte (1–3%) citite ca `comision` /
--     `modificare_credit`, nu tarife.
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
--       landing-pages/lcp-           TBI, finanțări la comercianți parteneri (0% pe
--                                    4 rate, exemple de 15–35% cu categoria greșită
--                                    `depozite`/`curs`); adăugat în 025, la decizia
--                                    lui Robert (29.09)
--   Cuvinte lăsate intenționat afară: „oferta"/„oferte" (ProCredit
--   oferta-credite-imobiliare e oferta standard; BRD card-de-credit-oferte e
--   pagina produsului), „landing" în general (ProCredit landing/progreen-imobiliar
--   e produsul ProHome), „special" (conturi speciale pentru fonduri europene),
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
CREATE OR REPLACE VIEW observatii_din_campanii AS
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
      '%tombola%', '%landing-pages/lcp-%'])
  ), clasificate AS (
    SELECT u.*,
           CASE
             WHEN cale LIKE '%regulament%'
              AND NOT cale LIKE ANY (ARRAY['%plata-in-rate%', '%regulament-beneficii%'])
               THEN 'regulament'
             WHEN cale LIKE ANY (ARRAY['%campani%', '%campaign%', '%campain%', '%promoti%',
                                       '%concurs%', '%oferta-speciala%', '%oferte-speciale%',
                                       '%premiaz%', '%rate-fara-dobanda%', '%tombola%',
                                       '%/landing-pages/lcp-%'])
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

-- Verificare: `observatii_curente` rămâne sincronizată cu `observations`.
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
