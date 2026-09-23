-- Migrarea 006: contextul valorii — la ce se referă, de fapt, cifra.
--
-- Problema care a impus-o: in interfata, o celula arata „7,5 lei" si nimeni
-- nu putea spune pentru CE. Cauza era la incarcare, nu la afisare: pachetul
-- Playwright livreaza campurile care explica valoarea, iar prima versiune a
-- loaderului pastra doar conceptul canonic si citatul.
--
-- Completitudinea reala a campurilor, masurata pe cele 5.578 de comisioane:
--   serviciu   100%   numele dat de banca („Administrarea contului (EURO)")
--   pagina     100%   pagina din PDF, pentru verificare
--   sectiune    92%   unde in document („servicii_de_cont", „plati")
--   frecventa   15%   lunar / anual / per operatiune - schimba complet sensul
--   conditie     4%   pragul de suma la care se aplica
--   detaliu      2%   precizari („Standard SWIFT")
--
-- `surse.url_public`: pentru documentele PDF, calea locala nu e un link. URL-ul
-- real nu vine in pachet, dar la unele documente se poate lega de un URL
-- descoperit de discovery. Se face doar la potrivire exacta de nume - un link
-- greșit ar trimite pe cineva la alt document decat cel din care vine cifra,
-- adica exact opusul unei dovezi.

ALTER TABLE observations ADD COLUMN IF NOT EXISTS serviciu  TEXT;
ALTER TABLE observations ADD COLUMN IF NOT EXISTS sectiune  TEXT;
ALTER TABLE observations ADD COLUMN IF NOT EXISTS conditie  TEXT;
ALTER TABLE observations ADD COLUMN IF NOT EXISTS frecventa TEXT;
ALTER TABLE observations ADD COLUMN IF NOT EXISTS detaliu   TEXT;
ALTER TABLE observations ADD COLUMN IF NOT EXISTS pagina    INTEGER;

ALTER TABLE surse ADD COLUMN IF NOT EXISTS url_public TEXT;

CREATE INDEX IF NOT EXISTS ix_observations_serviciu ON observations (serviciu);
