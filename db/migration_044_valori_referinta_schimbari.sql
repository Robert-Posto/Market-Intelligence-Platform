-- Migrarea 044: istoricul din valori_referinta ține doar schimbările, ca evoluția să se vadă.
--
-- DE CE: după 043 fiecare rulare de consolidare adăuga tot setul (~3.300 de rânduri), deși de la o
-- rulare la alta se schimbă câteva cifre: după 3 rulări erau 6.562 de rânduri pe baza „curent”, iar
-- evoluția unei cifre se citea doar comparând seturi întregi. Acum consolideaza_referinta.py:
--   - adaugă un rând doar când referința unei chei (bancă × produs × câmp) se schimbă: altă cifră,
--     altă unitate / monedă sau altă stare (ex. din `referinta` în `conflict`);
--   - când e la fel, actualizează doar `confirmat_la` pe ultimul rând (ultima rulare care a văzut-o);
--   - când o cheie nu mai e evaluată (câmp scos din fișă, produs negăsit la bancă), adaugă un rând
--     `lipsa` cu motivul, ca cifra veche să nu rămână „curentă” la nesfârșit.
-- Un rând e deci o perioadă: valabil de la `generat_la` (prima rulare cu cifra asta) până la
-- `confirmat_la` (ultima care a confirmat-o).
--
-- Rândurile deja scrise se compactează: rândurile consecutive identice ale aceleiași chei devin
-- unul, cu `confirmat_la` = ultima lor rulare. Sunt copii exacte, deci nu se pierde nimic.
--
-- Vederi:
--   valori_referinta_curente  ultimul rând pe cheie (ce citesc paginile)
--   schimbari_referinta       fiecare schimbare: cifra veche, cifra nouă, când, cu datele documentului
--
-- Idempotentă: compactarea și vederile se pot rula de mai multe ori.

BEGIN;

ALTER TABLE valori_referinta ADD COLUMN IF NOT EXISTS confirmat_la TIMESTAMPTZ;
UPDATE valori_referinta SET confirmat_la = generat_la WHERE confirmat_la IS NULL;
ALTER TABLE valori_referinta ALTER COLUMN confirmat_la SET DEFAULT now(),
                             ALTER COLUMN confirmat_la SET NOT NULL;

-- compactarea: grupele de rânduri consecutive identice pe cheie
WITH ordonat AS (
    SELECT id, generat_la,
           (stare IS NOT DISTINCT FROM lag(stare) OVER w
            AND valoare_num IS NOT DISTINCT FROM lag(valoare_num) OVER w
            AND unitate IS NOT DISTINCT FROM lag(unitate) OVER w
            AND moneda IS NOT DISTINCT FROM lag(moneda) OVER w
            AND lag(id) OVER w IS NOT NULL) AS la_fel,
           baza, id_banca, id_produs_libra, camp_cheie
      FROM valori_referinta
    WINDOW w AS (PARTITION BY baza, id_banca, id_produs_libra, camp_cheie ORDER BY generat_la, id)
), grupe AS (
    SELECT *, sum(CASE WHEN la_fel THEN 0 ELSE 1 END)
                  OVER (PARTITION BY baza, id_banca, id_produs_libra, camp_cheie ORDER BY generat_la, id) AS g
      FROM ordonat
), capete AS (
    SELECT min(id) FILTER (WHERE NOT la_fel) AS pastrat, max(generat_la) AS ultima, array_agg(id) AS ids
      FROM grupe GROUP BY baza, id_banca, id_produs_libra, camp_cheie, g
), confirmate AS (
    UPDATE valori_referinta v SET confirmat_la = c.ultima
      FROM capete c WHERE v.id = c.pastrat AND v.confirmat_la < c.ultima
    RETURNING v.id
)
DELETE FROM valori_referinta v
 USING capete c
 WHERE v.id = ANY(c.ids) AND v.id <> c.pastrat;

-- o cheie are cel mult un rând pe rulare
CREATE UNIQUE INDEX IF NOT EXISTS ux_valori_referinta_cheie_rulare
    ON valori_referinta (baza, id_banca, id_produs_libra, camp_cheie, generat_la);

-- ultimul rând pe cheie: ce citesc paginile (înainte: ultima rulare pe pereche, când fiecare
-- rulare scria tot setul)
CREATE OR REPLACE VIEW valori_referinta_curente AS
SELECT DISTINCT ON (v.baza, v.id_banca, v.id_produs_libra, v.camp_cheie) v.*
  FROM valori_referinta v
 ORDER BY v.baza, v.id_banca, v.id_produs_libra, v.camp_cheie, v.generat_la DESC, v.id DESC;

COMMENT ON VIEW valori_referinta_curente IS
  'Ultimul rând pe baza × bancă × produs Libra × câmp cheie; istoricul (doar schimbările) rămâne în valori_referinta.';

-- evoluția: fiecare schimbare a referinței unei chei, cu cifra de dinainte
CREATE OR REPLACE VIEW schimbari_referinta AS
SELECT * FROM (
    SELECT v.baza, b.slug AS banca, p.cod AS produs, p.denumire AS produs_denumire, v.camp_cheie,
           lag(v.valoare_num) OVER w AS valoare_veche, v.valoare_num AS valoare_noua,
           lag(v.unitate) OVER w AS unitate_veche, v.unitate AS unitate_noua,
           lag(v.stare) OVER w AS stare_veche, v.stare AS stare_noua,
           CASE WHEN lag(v.valoare_num) OVER w IS NOT NULL AND v.valoare_num IS NOT NULL
                     AND lag(v.unitate) OVER w IS NOT DISTINCT FROM v.unitate
                THEN v.valoare_num - lag(v.valoare_num) OVER w END AS diferenta,
           lag(v.generat_la) OVER w AS valabil_de_la, lag(v.confirmat_la) OVER w AS confirmat_pana_la,
           v.generat_la AS schimbat_la, v.data_extragere, v.data_citat, v.data_document, v.data_document_sursa,
           v.motiv, v.surse->0->>'url' AS sursa, v.surse->0->>'citat' AS citat
      FROM valori_referinta v
      JOIN banci b ON b.id = v.id_banca
      JOIN produse_libra p ON p.id = v.id_produs_libra
    WINDOW w AS (PARTITION BY v.baza, v.id_banca, v.id_produs_libra, v.camp_cheie ORDER BY v.generat_la, v.id)
) x
 WHERE x.valabil_de_la IS NOT NULL;

COMMENT ON VIEW schimbari_referinta IS
  'Fiecare schimbare a valorii de referință (bancă × produs Libra × câmp cheie): cifra veche, cifra nouă, când.';

COMMIT;
