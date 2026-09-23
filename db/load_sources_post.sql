-- Rulat DUPA seed_sources.sql: muta legaturile sursa-produs din coloana
-- array temporara in tabelul de legatura, apoi scoate coloana.
BEGIN;

INSERT INTO surse_produse (id_sursa, id_produs)
SELECT s.id, p
FROM surse s, unnest(s.produse) AS p
ON CONFLICT DO NOTHING;

ALTER TABLE surse DROP COLUMN produse;

COMMIT;
