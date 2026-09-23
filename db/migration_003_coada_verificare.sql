-- Migrarea 003: coada de verificare umana, ca view.
--
-- Piesa proiectata in artifact (figura 2, „Coadă de verificare umană") are
-- acum primii ocupanti reali. Regulile vin din erori masurate, nu presupuse:
--
--   1. valoare monetara > 10.000  - un comision de retail peste 10.000 lei/eur
--      e improbabil. Caz real gasit prin sortare descrescatoare in vizualizator:
--      „Capital Social: 1.625.341.625,40 lei" extras ca `comision`, adica un
--      numar din antetul documentului. Randurile etichetate `conditie` sunt
--      excluse - acolo o suma mare e corecta (prag de eligibilitate).
--   2. procent > 40  - nicio dobanda de retail din RO nu ajunge acolo.
--      (azi: zero randuri, deci regula e preventiva, nu retroactiva)
--   3. ambiguu  - valoare reala, dar nu se stie cui se aplica (vezi ambiguitate.py)
--   4. confidence < 0.7  - sub pragul de publicare automata
--
-- View, nu tabel: se recalculeaza la fiecare interogare, deci nu se
-- desincronizeaza de date. Cand un om rezolva un rand, decizia se scrie in
-- observations (confidence/ambiguu), iar randul iese singur din coada.

CREATE OR REPLACE VIEW coada_verificare AS
SELECT
    o.id,
    b.slug        AS banca,
    p.nume        AS produs,
    o.camp,
    o.valoare_num,
    o.unitate,
    o.confidence,
    o.ambiguu,
    o.citat,
    s.sursa,
    s.tip_sursa,
    o.metoda_extractie,
    CASE
        WHEN o.unitate IN ('lei', 'eur', 'usd') AND o.valoare_num > 10000
             AND o.camp <> 'conditie'          THEN 'suma implauzibil de mare pentru un comision'
        WHEN o.unitate = 'procent' AND o.valoare_num > 40
                                               THEN 'procent implauzibil de mare'
        WHEN o.ambiguu                         THEN 'valoare reala, dar neatribuibila'
        ELSE                                        'incredere sub prag'
    END AS motiv
FROM observations o
JOIN surse s   ON s.id = o.id_sursa
JOIN banci b   ON b.id = s.id_banca
JOIN produse p ON p.id = o.id_produs
WHERE (o.unitate IN ('lei', 'eur', 'usd') AND o.valoare_num > 10000 AND o.camp <> 'conditie')
   OR (o.unitate = 'procent' AND o.valoare_num > 40)
   OR o.ambiguu
   OR o.confidence < 0.7;
