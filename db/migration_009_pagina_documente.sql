-- Migrarea 009: pagina de pe care banca publică documentele de tarife.
--
-- Problema: 2.858 din 4.099 observații de comision nu au niciun link, fiindcă
-- pachetul sursă reține doar calea locală a PDF-ului, nu URL-ul de descărcare,
-- iar PDF-urile nu sunt incluse. Din 68 de documente, doar 9 s-au putut lega
-- exact la un URL descoperit — fiindcă discovery-ul a găsit doar 40 de URL-uri
-- de PDF în total, iar restul documentelor nu sunt printre ele. Nu e un prag
-- prea strict: măsurat, nu există mai mult de potrivit.
--
-- Ce se poate face fără să mintem: pentru fiecare bancă știm pagina de pe care
-- ea publică lista de tarife (`librabank.ro/comisioane`,
-- `procreditbank.ro/lista-de-preturi/`, `bcr.ro/.../informatii-utile/comisioane`).
-- E o afirmație verificabilă și adevărată — „documentul se publică aici" — și
-- se distinge clar în interfață de un link către documentul exact.
--
-- `pagina_documente_motiv` păstrează de ce a fost aleasă pagina aceea, ca
-- alegerea să poată fi contestată fără să fie reconstituită.

ALTER TABLE banci ADD COLUMN IF NOT EXISTS pagina_documente       TEXT;
ALTER TABLE banci ADD COLUMN IF NOT EXISTS pagina_documente_motiv TEXT;
