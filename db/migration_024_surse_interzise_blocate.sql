-- Migrarea 024: sursele interzise de robots.txt nu mai stau `activ`.
--
-- DE CE: la ultima populare, `transport.adu` a refuzat corect aceste adrese
-- (robots.txt al băncii le interzice) și a scris motivul în `nota_extractie`
-- („ROBOTS: interzis de robots.txt", „ROBOTS: redirect spre adresă
-- interzisă"), dar `status` a rămas 'activ' — doar verdictul BLOCAT schimba
-- statusul. Nicolae, §10.1 punctul 7: trebuie `blocat`. Pe 29.09: ING 48
-- (PDF-urile, `Disallow: *.pdf`), Patria 16 (`/d/`, `/r/`), BRD 1 (redirect
-- spre un PDF interzis) = 65 de surse, niciuna cu observații.
--
-- Ce face: doar `status` → 'blocat'. Nota rămâne neatinsă, ca dovadă; nu se
-- șterge nimic. 'blocat' e deja permis de `surse_status_check`
-- (activ, pauza, eroare, blocat, retras).
--
-- Idempotentă: a doua rulare nu mai găsește surse 'activ' cu nota asta.
-- Reversibilă: aceeași condiție, cu status 'activ'.

BEGIN;

UPDATE surse
   SET status = 'blocat'
 WHERE status = 'activ'
   AND nota_extractie LIKE 'ROBOTS:%';

COMMIT;
