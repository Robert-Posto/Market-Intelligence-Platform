-- Migrarea 021: sursele de produs Libra trec pe pauză.
--
-- DE CE: produsele Libra vin din catalogul intern (`catalog_libra`, migrarea
-- 020); pentru Libra nu se mai face scraping pe produse. Regula din cod e
-- `BANCI_CU_CATALOG` în ingest/normalizeaza.py; aici se aliniază și inventarul.
--
-- NU se șterge nimic: observațiile deja colectate din aceste surse rămân
-- (datele nu se aruncă), iar sursele rămân în inventar, doar nu mai sunt
-- 'activ'. Documentele de tarife (rol 'conditii') și localizatoarele rămân
-- active. Idempotentă: a doua rulare nu găsește nimic de schimbat.

UPDATE surse s
   SET status = 'pauza',
       nota_extractie = 'produsele Libra vin din catalogul intern (catalog_libra), nu de pe web'
                        || COALESCE(' | anterior: ' || s.nota_extractie, '')
  FROM banci b
 WHERE b.id = s.id_banca
   AND b.slug = 'libra'
   AND s.rol = 'produs'
   AND (s.nota_extractie IS NULL
        OR s.nota_extractie NOT LIKE 'produsele Libra vin din catalogul intern%');
