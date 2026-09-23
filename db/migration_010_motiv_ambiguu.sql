-- Migrarea 010: de ce o valoare e marcată ambiguă.
--
-- Interfața scria „valoare reală, dar neatribuibilă" — o formulare care nu
-- spune nimic. Motivul exista în pachetul sursă și îl arunca încărcarea.
--
-- Măsurat pe cele 716 valori ambigue din pachet, sunt exact două motive:
--
--   antet de coloana pierdut   526  Tabelul din PDF avea mai multe coloane
--                                   (pachet Standard / Gold / Premium, sau
--                                   PF / PJ). La extracție s-a citit cifra,
--                                   dar nu s-a putut stabili cărei coloane
--                                   aparține. Prețul e real; nu se știe pentru
--                                   care variantă de produs.
--
--   prag de suma pierdut       190  Comisionul e pe tranșe („1 leu până la
--                                   1.000 lei, 3 lei până la 10.000 lei").
--                                   Tranșele s-au pierdut, deci avem 1, 3, 5,
--                                   15 lei fără să știm de la ce sumă începe
--                                   fiecare. Caz real: BRCI, plăți în EUR.
--
-- Amândouă sunt pierderi de STRUCTURĂ la citirea tabelului, nu greșeli de
-- citire a cifrei. De-aia valorile se păstrează și se exclud doar din
-- comparații: cifra e corectă, contextul care o face utilizabilă lipsește.

ALTER TABLE observations ADD COLUMN IF NOT EXISTS motiv_ambiguu TEXT;

CREATE INDEX IF NOT EXISTS ix_observations_motiv_ambiguu
  ON observations (motiv_ambiguu) WHERE ambiguu;
