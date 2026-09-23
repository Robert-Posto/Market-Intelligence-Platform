-- Rulat INAINTE de seed_sources.sql.
--
-- seed_sources.sql a fost generat pentru schema v3, care avea `surse.produse`
-- ca BIGINT[]. Schema v4 foloseste tabelul de legatura `surse_produse`.
-- Ca sa nu parsam SQL generat (fragil), adaugam temporar coloana array,
-- lasam fisierul sa ruleze nemodificat, apoi mutam datele in tabelul de
-- legatura si stergem coloana (load_sources_post.sql).
ALTER TABLE surse ADD COLUMN IF NOT EXISTS produse BIGINT[] NOT NULL DEFAULT '{}';
