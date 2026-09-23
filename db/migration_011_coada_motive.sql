-- Migrarea 011: coada de verificare spune motivul CONCRET, nu unul generic.
--
-- Vederea veche scria „valoare reala, dar neatribuibila" pentru toate cele 716
-- valori ambigue. Formularea nu spune nimic: nu se poate decide ce să faci cu
-- rândul. Motivul real vine acum din `observations.motiv_ambiguu` (migrarea
-- 010) și e unul din două, măsurate în pachetul sursă:
--
--   antet de coloana pierdut   526  Tabelul din PDF avea mai multe coloane
--                                   (pachet Standard / Gold, sau PF / PJ) și
--                                   s-a pierdut care coloană e a cifrei.
--                                   Prețul e corect; nu se știe pentru care
--                                   variantă de produs.
--   prag de suma pierdut       190  Comisionul e pe tranșe („1 leu până la
--                                   1.000 lei, 3 lei peste"). Tranșele s-au
--                                   pierdut, deci avem 1, 3, 5, 15 lei fără
--                                   să știm de la ce sumă se aplică fiecare.
--
-- Amândouă sunt pierderi de STRUCTURĂ la citirea tabelului, nu greșeli de
-- citire a cifrei — de-aia valoarea se păstrează și se exclude doar din
-- comparații.
--
-- Pragurile nu mai sunt scrise de mână în vedere: se citesc din tabela
-- `praguri_plauzibilitate`, populată din `normalizeaza.PRAGURI`. Erau trei
-- copii ale acelorași numere (încărcare, vedere, API) și puteau ajunge
-- diferite fără ca nimeni să observe.

CREATE TABLE IF NOT EXISTS praguri_plauzibilitate (
  cheie   TEXT PRIMARY KEY,
  valoare NUMERIC NOT NULL,
  nota    TEXT
);

INSERT INTO praguri_plauzibilitate (cheie, valoare, nota) VALUES
  ('suma',             10000, 'un comision de retail nu trece de atât; mai sus sunt limite de retragere sau capital social extras ca preț'),
  ('procent_absolut',     40, 'mai sus nu e dobândă, ci reducere procentuală sau cotă de garantare')
ON CONFLICT (cheie) DO UPDATE SET valoare = EXCLUDED.valoare, nota = EXCLUDED.nota;

-- DROP + CREATE, nu CREATE OR REPLACE: Postgres refuza sa schimbe numele
-- sau ordinea coloanelor unei vederi existente.
DROP VIEW IF EXISTS coada_verificare;
CREATE VIEW coada_verificare AS
  SELECT o.id,
         b.slug AS banca,
         b.nume AS banca_nume,
         p.nume AS produs,
         o.camp,
         o.serviciu,
         o.valoare_num,
         o.unitate,
         o.confidence,
         o.ambiguu,
         o.motiv_ambiguu,
         o.citat,
         o.pagina,
         s.sursa,
         s.tip_sursa,
         s.url_public,
         o.metoda_extractie,
         CASE
           WHEN o.unitate IN ('lei','eur','usd')
                AND o.valoare_num > (SELECT valoare FROM praguri_plauzibilitate WHERE cheie = 'suma')
                AND o.camp <> 'conditie'          THEN 'sumă implauzibilă'
           WHEN o.unitate = 'procent'
                AND o.valoare_num > (SELECT valoare FROM praguri_plauzibilitate WHERE cheie = 'procent_absolut')
                                                  THEN 'procent implauzibil'
           WHEN o.ambiguu                         THEN coalesce(o.motiv_ambiguu, 'ambiguu, motiv nenotat')
           ELSE 'încredere scăzută'
         END AS motiv
  FROM observations o
  JOIN surse s   ON s.id = o.id_sursa
  JOIN banci b   ON b.id = s.id_banca
  JOIN produse p ON p.id = o.id_produs
  WHERE (o.unitate IN ('lei','eur','usd')
         AND o.valoare_num > (SELECT valoare FROM praguri_plauzibilitate WHERE cheie = 'suma')
         AND o.camp <> 'conditie')
     OR (o.unitate = 'procent'
         AND o.valoare_num > (SELECT valoare FROM praguri_plauzibilitate WHERE cheie = 'procent_absolut'))
     OR o.ambiguu
     OR o.confidence < 0.7;
