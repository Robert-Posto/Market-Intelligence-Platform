-- PATCH LOCAL (mip): adaugat ON CONFLICT DO NOTHING la fiecare INSERT.
-- Motiv: verificarea NOT EXISTS din fisierul original nu vede randurile
-- inserate de ACELASI statement, deci un URL care apare de doua ori in
-- aceeasi lista de VALUES trece de verificare si pica pe indexul unic
-- ux_surse_url (caz real: tarife-comisioane-standard-pf.sv.pdf la Raiffeisen).
-- Originalul nemodificat: Downloads/flux-colectare/append-surse.sql
-- =====================================================================
-- append-surse.sql — generat de genereaza-surse-sql.py la 2026-09-21
--
-- 27 banci, 340 documente din
-- 30 inventare. Mod: ALTER TABLE pe CHECK-uri.
--
-- Necesita `banci` si `produse` deja populate (append.sql).
--
-- Idempotent: fiecare rand se insereaza doar daca `sursa` nu exista deja.
-- Merge si fara indexul unic pe surse.sursa, care in db.sql e comentat.
--
-- status='activ'   270
-- status='pauza'    70  cer verificare manuala inainte de crawl
--
-- Coloane lasate NULL, intentionat:
--   robots_ok             inventarele nu au informatia per document
--   metoda_verificata_la  `metoda` e o estimare a modelului, nu o masuratoare
--   metoda_extractie      se completeaza cand alegi flowul per sursa
--   legal_review_ref      vine din review-ul juridic
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- Largirea CHECK-urilor
--
-- Inventarele produc valori pe care db.sql nu le accepta. Fara ALTER-urile
-- astea, 21 documente cu rol `context` si
-- 24 cu frecventa
-- `trimestrial`/`la_descoperire` ar fi respinse de constrangeri.
--
-- Alternativa, daca nu vrei sa atingi schema: ruleaza generatorul cu
-- --mapeaza. Atunci rolul `context` devine NULL si frecventele se aproximeaza.
-- ---------------------------------------------------------------------
ALTER TABLE surse DROP CONSTRAINT IF EXISTS surse_rol_check;
ALTER TABLE surse ADD  CONSTRAINT surse_rol_check
    CHECK (rol IN ('produs', 'hub', 'conditii', 'context'));

ALTER TABLE surse DROP CONSTRAINT IF EXISTS surse_frecventa_check;
ALTER TABLE surse ADD  CONSTRAINT surse_frecventa_check
    CHECK (frecventa IN ('zilnic', 'saptamanal', 'lunar', 'manual', 'trimestrial', 'la_descoperire'));

-- ---------------------------------------------------------------------
-- banca-transilvania  (13 documente)
-- ---------------------------------------------------------------------
INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda,
                   produse, frecventa, status)
SELECT b.id, v.tip_sursa, v.sursa, v.rol, v.format, v.metoda,
       v.produse, v.frecventa, v.status
FROM banci b
CROSS JOIN (VALUES
    ('url', 'https://www.bancatransilvania.ro/taxe-si-comisioane', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.bancatransilvania.ro/files/app/media/Taxe-si-comisioane/Persoane-fizice.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'pauza'),  -- pauza: adresa raportata fara sa fi fost deschisa
    ('url', 'https://www.bancatransilvania.ro/documente-utile-bt', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.bancatransilvania.ro/companii/finantare/credite/factoring', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('factoring') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.btleasing.ro/leasing-auto-pentru-companii', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('leasing') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.btleasing.ro/leasing-echipamente-pentru-companii', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('leasing') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.bancatransilvania.ro/carduri/carduri-de-cumparaturi/star-card', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'dae', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.bancatransilvania.ro/conturi-si-operatiuni/conturi/abonament-cont-curent', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.bancatransilvania.ro/credite/credite-de-nevoi/creditul-de-nevoi-personale-standard', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dae', 'dobanda-nominala', 'ipotecar-refinantare', 'marja-ircc', 'robor-euribor') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.bancatransilvania.ro/companii/finantare/credite/credit-de-investitii', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('ipotecar-refinantare') ORDER BY nume)::BIGINT[], 'lunar', 'pauza'),  -- pauza: incredere_metoda 0.5
    ('url', 'https://www.bancatransilvania.ro/companii/corporate', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'pauza'),  -- pauza: incredere_metoda 0.65
    ('url', 'https://www.bancatransilvania.ro/companii/conturi-carduri/carduri-business/card-de-credit-visa-business', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit') ORDER BY nume)::BIGINT[], 'saptamanal', 'pauza'),  -- pauza: incredere_metoda 0.6
    ('url', 'https://www.bancatransilvania.ro/news/comunicate-de-presa/credite-noua-casa-prin-banca-transilvania-', 'context', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('marja-ircc', 'noua-casa', 'robor-euribor') ORDER BY nume)::BIGINT[], 'la_descoperire', 'activ')
) AS v (tip_sursa, sursa, rol, format, metoda, produse, frecventa, status)
WHERE b.slug = 'banca-transilvania'
  AND NOT EXISTS (SELECT 1 FROM surse s WHERE s.sursa = v.sursa)
ON CONFLICT DO NOTHING;
-- ---------------------------------------------------------------------
-- bankofchina  (17 documente)
-- ---------------------------------------------------------------------
INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda,
                   produse, frecventa, status)
SELECT b.id, v.tip_sursa, v.sursa, v.rol, v.format, v.metoda,
       v.produse, v.frecventa, v.status
FROM banci b
CROSS JOIN (VALUES
    ('url', 'https://www.bankofchina.com/ro/en/', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.bankofchina.com/ro/en/cbservice/cb1/', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.bankofchina.com/ro/en/cbservice/cb1/202104/t20210430_19360672.html', 'produs', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.bankofchina.com/ro/en/cbservice/cb1/202104/t20210430_19360670.html', 'produs', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.bankofchina.com/ro/en/cbservice/cb2/', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.bankofchina.com/ro/en/cbservice/cb2/202104/t20210430_19360666.html', 'produs', 'html', 'http', '{}'::BIGINT[], 'lunar', 'pauza'),  -- pauza: incredere_metoda 0.65
    ('url', 'https://www.bankofchina.com/ro/en/cbservice/cb4/', 'hub', 'html', 'http', '{}'::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.bankofchina.com/ro/en/cbservice/cb4/202104/t20210430_19360668.html', 'context', 'html', 'http', '{}'::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.bankofchina.com/ro/en/bocinfo/bi4/', 'hub', 'html', 'http', '{}'::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.bankofchina.com/ro/en/bocinfo/bi4/202609/t20260921_25693493.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('curs-valutar-propriu') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.bankofchina.com/ro/en/bocinfo/bi2/202109/t20210908_20014518.html', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://pic.bankofchina.com/bocappd/Romania/202507/P020250701398817431078.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'cont-curent', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.bankofchina.com/ro/en/cbservice/cb3/', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.bankofchina.com/ro/en/cbservice/cb3/cb32/202104/t20210430_19360696.html', 'context', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.bankofchina.com/ro/en/cbservice/cb3/cb32/202104/t20210430_19360692.html', 'context', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.bankofchina.com/ro/en/cbservice/RMBSrv/202104/t20210430_19360664.html', 'context', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.bankofchina.com/ro/en/cbservice/cbo/', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ')
) AS v (tip_sursa, sursa, rol, format, metoda, produse, frecventa, status)
WHERE b.slug = 'bankofchina'
  AND NOT EXISTS (SELECT 1 FROM surse s WHERE s.sursa = v.sursa)
ON CONFLICT DO NOTHING;
-- banorient: inventar fara documente, nimic de inserat
-- ---------------------------------------------------------------------
-- bcr-locuinte  (4 documente)
-- ---------------------------------------------------------------------
INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda,
                   produse, frecventa, status)
SELECT b.id, v.tip_sursa, v.sursa, v.rol, v.format, v.metoda,
       v.produse, v.frecventa, v.status
FROM banci b
CROSS JOIN (VALUES
    ('url', 'https://www.bcrlocuinte.ro/ro/bpl', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'pauza'),  -- pauza: adresa raportata fara sa fi fost deschisa
    ('url', 'https://www.bcrlocuinte.ro/ro/creditare', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.bcrlocuinte.ro/ro/creditare/creditul-locativ', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'dae', 'dobanda-nominala', 'ipotecar-refinantare') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.bcrlocuinte.ro/ro/despre-noi', 'context', 'html', 'http', '{}'::BIGINT[], 'trimestrial', 'activ')
) AS v (tip_sursa, sursa, rol, format, metoda, produse, frecventa, status)
WHERE b.slug = 'bcr-locuinte'
  AND NOT EXISTS (SELECT 1 FROM surse s WHERE s.sursa = v.sursa)
ON CONFLICT DO NOTHING;
-- ---------------------------------------------------------------------
-- bcr  (13 documente)
-- ---------------------------------------------------------------------
INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda,
                   produse, frecventa, status)
SELECT b.id, v.tip_sursa, v.sursa, v.rol, v.format, v.metoda,
       v.produse, v.frecventa, v.status
FROM banci b
CROSS JOIN (VALUES
    ('url', 'https://www.bcr.ro/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'comisioane', 'cont-curent', 'dae', 'dobanda-nominala', 'ipotecar-refinantare', 'marja-ircc') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.bcr.ro/ro/persoane-fizice/informatii-utile/comisioane', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.bcr.ro/content/dam/ro/bcr/www_bcr_ro/Persoane-fizice/Documente-importante/Tarif_standard_de_comisioane_PF.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.bcr.ro/ro/persoane-fizice/credite/credite-pentru-casa/noua-casa-bcr', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('ipotecar-refinantare', 'marja-ircc', 'noua-casa', 'robor-euribor') ORDER BY nume)::BIGINT[], 'trimestrial', 'activ'),
    ('url', 'https://www.bcr.ro/ro/persoane-fizice/credite/credite-pentru-casa/casa-mea-bcr', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dae', 'dobanda-nominala', 'ipotecar-refinantare', 'marja-ircc', 'robor-euribor') ORDER BY nume)::BIGINT[], 'trimestrial', 'activ'),
    ('url', 'https://www.bcr.ro/ro/business/informatii-utile', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.bcr.ro/ro/persoane-fizice/carduri-de-cumparaturi/cardul-de-credit-online', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'comisioane', 'dae', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.bcr.ro/ro/curs-valutar', 'produs', 'html', 'playwright', ARRAY(SELECT id FROM produse WHERE nume IN ('curs-valutar-propriu') ORDER BY nume)::BIGINT[], 'zilnic', 'pauza'),  -- pauza: metoda playwright e o estimare, nu o masuratoare; incredere_metoda 0.25
    ('url', 'https://www.bcr.ro/ro/business/general/finantare/supply-chain-finance/factoring', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.bcr.ro/ro/business/general/finantare/supply-chain-finance/factoring/factoring-intern', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('factoring') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.bcr.ro/ro/business/general/conturi-si-servicii/servicii-cash-management', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cash-management') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.bcr.ro/ro/business', 'hub', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dobanda-nominala') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.bcr.ro/ro/persoane-fizice/digital-banking/cont-online-george', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ')
) AS v (tip_sursa, sursa, rol, format, metoda, produse, frecventa, status)
WHERE b.slug = 'bcr'
  AND NOT EXISTS (SELECT 1 FROM surse s WHERE s.sursa = v.sursa)
ON CONFLICT DO NOTHING;
-- ---------------------------------------------------------------------
-- bid  (8 documente)
-- ---------------------------------------------------------------------
INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda,
                   produse, frecventa, status)
SELECT b.id, v.tip_sursa, v.sursa, v.rol, v.format, v.metoda,
       v.produse, v.frecventa, v.status
FROM banci b
CROSS JOIN (VALUES
    ('url', 'https://www.bidromania.eu/', 'context', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.bidromania.eu/produse/credite/creditare-directa', 'produs', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.bidromania.eu/produse/credite/fondul-de-participare-regional', 'produs', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.bidromania.eu/produse/credite/fondul-de-participare-tranzitie-justa', 'produs', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.bidromania.eu/produse/garantii/diaspora-investeste-acasa', 'produs', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.bidromania.eu/produse/garantii/garantii-de-portofoliu-pentru-imm-uri', 'produs', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.bidromania.eu/produse/garantii/garantii-individuale-pentru-mediul-public', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.bidromania.eu/transparenta/rapoarte', 'hub', 'html', 'http', '{}'::BIGINT[], 'trimestrial', 'activ')
) AS v (tip_sursa, sursa, rol, format, metoda, produse, frecventa, status)
WHERE b.slug = 'bid'
  AND NOT EXISTS (SELECT 1 FROM surse s WHERE s.sursa = v.sursa)
ON CONFLICT DO NOTHING;
-- ---------------------------------------------------------------------
-- bnpparibas  (5 documente)
-- ---------------------------------------------------------------------
INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda,
                   produse, frecventa, status)
SELECT b.id, v.tip_sursa, v.sursa, v.rol, v.format, v.metoda,
       v.produse, v.frecventa, v.status
FROM banci b
CROSS JOIN (VALUES
    ('url', 'https://romania.bnpparibas.com/', 'context', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.romania.bnpparibas.com/en/corporates-institutions/', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.romania.bnpparibas.com/en/private-clients/', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.romania.bnpparibas.com/en/legal-information/', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.romania.bnpparibas.com/app/uploads/sites/37/2025/11/gtcs-ro-nov-2025.pdf', 'conditii', 'pdf', 'http', '{}'::BIGINT[], 'la_descoperire', 'activ')
) AS v (tip_sursa, sursa, rol, format, metoda, produse, frecventa, status)
WHERE b.slug = 'bnpparibas'
  AND NOT EXISTS (SELECT 1 FROM surse s WHERE s.sursa = v.sursa)
ON CONFLICT DO NOTHING;
-- ---------------------------------------------------------------------
-- brci  (12 documente)
-- ---------------------------------------------------------------------
INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda,
                   produse, frecventa, status)
SELECT b.id, v.tip_sursa, v.sursa, v.rol, v.format, v.metoda,
       v.produse, v.frecventa, v.status
FROM banci b
CROSS JOIN (VALUES
    ('url', 'https://vreaucont.brci.ro/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://vreaucont.brci.ro/onboarding', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'lunar', 'pauza'),  -- pauza: adresa raportata fara sa fi fost deschisa
    ('url', 'https://www.brci.ro/ro/produse/cont-curent.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'cont-curent', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.brci.ro/ro/produse/cont-curent-pj.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'cont-curent', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'zilnic', 'pauza'),  -- pauza: adresa raportata fara sa fi fost deschisa
    ('url', 'https://www.brci.ro/public/index.php/ro/produse/overdraft.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'dae', 'dobanda-nominala', 'marja-ircc') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.brci.ro/files/public/fisiere/Lista%20Tarife%20si%20Comisioane%20PJ%20%20mai%202024.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.brci.ro/ro/produse/card-mastercard-business.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane') ORDER BY nume)::BIGINT[], 'saptamanal', 'pauza'),  -- pauza: adresa raportata fara sa fi fost deschisa
    ('url', 'https://www.brci.ro/ro/articol/despre-brci.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('curs-valutar-propriu') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www2.brci.ro/', 'hub', 'html', 'http', '{}'::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.brci.ro/public/index.php/ro/produse/factoring/beneficii.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('factoring') ORDER BY nume)::BIGINT[], 'lunar', 'pauza'),  -- pauza: incredere_metoda 0.55; adresa raportata fara sa fi fost deschisa
    ('url', 'https://companii.brci.ro/pjonboarding', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cont-curent', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.brci.ro/ro/articol/actualizare-liste-comisioane-operatiuni-cu-instrumente-financiare-pf-si-pj-din-13-12-2024.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane') ORDER BY nume)::BIGINT[], 'saptamanal', 'pauza')  -- pauza: adresa raportata fara sa fi fost deschisa
) AS v (tip_sursa, sursa, rol, format, metoda, produse, frecventa, status)
WHERE b.slug = 'brci'
  AND NOT EXISTS (SELECT 1 FROM surse s WHERE s.sursa = v.sursa)
ON CONFLICT DO NOTHING;
-- ---------------------------------------------------------------------
-- brd  (5 documente)
-- ---------------------------------------------------------------------
INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda,
                   produse, frecventa, status)
SELECT b.id, v.tip_sursa, v.sursa, v.rol, v.format, v.metoda,
       v.produse, v.frecventa, v.status
FROM banci b
CROSS JOIN (VALUES
    ('url', 'https://www.brd.ro/', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.brd.ro/sites/default/files/_files/pdf/Ghid_dobanzi_si_comisioane_credite.pdf', 'conditii', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'dobanda-nominala', 'ipotecar-refinantare', 'marja-ircc', 'noua-casa', 'robor-euribor') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.brd.ro/sites/default/files/_files/pdf/Informatii%20privind%20accesibilitatea%20pentru%20consumatori%20a%20serviciilor%20din%20oferta%20BRD.pdf', 'context', 'pdf', 'http', '{}'::BIGINT[], 'la_descoperire', 'activ'),
    ('url', 'https://www.brd.ro/companii/imm-sub-1m-euro/finantare/factoring-si-scontare', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('factoring') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.brd.ro/companii/leasing', 'produs', 'html', 'playwright', '{}'::BIGINT[], 'lunar', 'pauza')  -- pauza: metoda playwright e o estimare, nu o masuratoare; incredere_metoda 0.35
) AS v (tip_sursa, sursa, rol, format, metoda, produse, frecventa, status)
WHERE b.slug = 'brd'
  AND NOT EXISTS (SELECT 1 FROM surse s WHERE s.sursa = v.sursa)
ON CONFLICT DO NOTHING;
-- ---------------------------------------------------------------------
-- cec  (15 documente)
-- ---------------------------------------------------------------------
INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda,
                   produse, frecventa, status)
SELECT b.id, v.tip_sursa, v.sursa, v.rol, v.format, v.metoda,
       v.produse, v.frecventa, v.status
FROM banci b
CROSS JOIN (VALUES
    ('url', 'https://www.cec.ro/documente-utile', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.cec.ro/curs-valutar', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('curs-valutar-propriu') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.cec.ro/curs-valutar-pj', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('curs-valutar-propriu') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.cec.ro/dobanzi-depozite-lei', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cont-curent', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.cec.ro/persoane-fizice/credite/credite-ipotecare/credit-ipotecar-dobanda-variabila', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'dae', 'dobanda-nominala', 'ipotecar-refinantare', 'marja-ircc') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.cec.ro/dobanzi-referinta-credite', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('marja-ircc', 'robor-euribor') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.cec.ro/persoane-fizice/credite/credite-ipotecare/credit-ipotecar-prima-casa', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dae', 'dobanda-nominala', 'marja-ircc', 'noua-casa') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.cec.ro/persoane-fizice/carduri-credit/cardul-credit-visa-affinity', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'dobanda-nominala', 'marja-ircc') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.cec.ro/cont-bancar-simplu', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.cec.ro/finantari-comerciale', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('factoring') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.cec.ro/cont-bancar-curent-persoane-juridice', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cash-management', 'comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.cec.ro/sites/default/files/public_folder/comisioane_operatiuni_pj.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cash-management', 'comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.cec.ro/dobanzi-depozite-lei-persoane-juridice', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dobanda-nominala') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.cec.ro/credit-activitate-curenta', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cont-curent') ORDER BY nume)::BIGINT[], 'lunar', 'pauza'),  -- pauza: incredere_metoda 0.6
    ('url', 'https://www.cec.ro/cardul-de-credit-visa-business', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'dobanda-nominala', 'robor-euribor') ORDER BY nume)::BIGINT[], 'zilnic', 'activ')
) AS v (tip_sursa, sursa, rol, format, metoda, produse, frecventa, status)
WHERE b.slug = 'cec'
  AND NOT EXISTS (SELECT 1 FROM surse s WHERE s.sursa = v.sursa)
ON CONFLICT DO NOTHING;
-- cetelem: inventar fara documente, nimic de inserat
-- ---------------------------------------------------------------------
-- citibank  (14 documente)
-- ---------------------------------------------------------------------
INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda,
                   produse, frecventa, status)
SELECT b.id, v.tip_sursa, v.sursa, v.rol, v.format, v.metoda,
       v.produse, v.frecventa, v.status
FROM banci b
CROSS JOIN (VALUES
    ('url', 'https://www.citibank.com/icg/sa/emea/romania/english/about-us.html', 'context', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.citibank.com/icg/sa/emea/romania/english/products-services/index.html', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.citibank.com/icg/sa/emea/romania/english/products-services/treasury/', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.citibank.com/icg/sa/emea/romania/english/products-services/treasury/foreign-market.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('curs-valutar-propriu') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.citibank.com/icg/sa/emea/romania/english/products-services/treasury/money-market.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dobanda-nominala') ORDER BY nume)::BIGINT[], 'zilnic', 'pauza'),  -- pauza: incredere_metoda 0.6
    ('url', 'https://www.citibank.com/icg/sa/emea/romania/english/products-services/treasury/capital-market.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.citibank.com/icg/sa/emea/romania/english/products-services/financing-solutions/corp-banking.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cont-curent') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.citibank.com/icg/sa/emea/romania/english/products-services/trade-services/', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.citibank.com/icg/sa/emea/romania/english/products-services/trade-services/trade-finance.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('factoring') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.citibank.com/icg/sa/emea/romania/english/products-services/trade-services/trade-services.html', 'produs', 'html', 'playwright', '{}'::BIGINT[], 'lunar', 'pauza'),  -- pauza: metoda playwright e o estimare, nu o masuratoare; incredere_metoda 0.4
    ('url', 'https://www.citibank.com/icg/sa/emea/romania/english/products-services/cash-management/', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.citibank.com/icg/sa/emea/romania/english/products-services/cash-management/payables.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cash-management') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://citibank.com/icg/sa/emea/romania/english/products-services/cash-management/visa-cards.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit') ORDER BY nume)::BIGINT[], 'lunar', 'pauza'),  -- pauza: incredere_metoda 0.5
    ('url', 'https://www.citibank.com/icg/sa/emea/romania/english/products-services/securities-fund-services/', 'context', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ')
) AS v (tip_sursa, sursa, rol, format, metoda, produse, frecventa, status)
WHERE b.slug = 'citibank'
  AND NOT EXISTS (SELECT 1 FROM surse s WHERE s.sursa = v.sursa)
ON CONFLICT DO NOTHING;
-- ---------------------------------------------------------------------
-- credex  (8 documente)
-- ---------------------------------------------------------------------
INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda,
                   produse, frecventa, status)
SELECT b.id, v.tip_sursa, v.sursa, v.rol, v.format, v.metoda,
       v.produse, v.frecventa, v.status
FROM banci b
CROSS JOIN (VALUES
    ('url', 'https://credex.ro/', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'pauza'),  -- pauza: incredere_metoda 0.6
    ('url', 'https://credex.ro/credit-de-nevoi-personale/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'dae', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://credex.ro/totul-despre-credite/card-de-credit-credex/', 'produs', 'html', 'playwright', '{}'::BIGINT[], 'saptamanal', 'pauza'),  -- pauza: metoda playwright e o estimare, nu o masuratoare; incredere_metoda 0.5
    ('url', 'https://credex.ro/intrebari-si-raspunsuri/', 'conditii', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'comisioane', 'dae', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://credex.ro/termeni-si-conditii/', 'conditii', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://credex.ro/formulare-clienti/', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://credex.ro/oferte/', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://credex.ro/despre-credex/', 'context', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ')
) AS v (tip_sursa, sursa, rol, format, metoda, produse, frecventa, status)
WHERE b.slug = 'credex'
  AND NOT EXISTS (SELECT 1 FROM surse s WHERE s.sursa = v.sursa)
ON CONFLICT DO NOTHING;
-- ---------------------------------------------------------------------
-- creditcoop  (10 documente)
-- ---------------------------------------------------------------------
INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda,
                   produse, frecventa, status)
SELECT b.id, v.tip_sursa, v.sursa, v.rol, v.format, v.metoda,
       v.produse, v.frecventa, v.status
FROM banci b
CROSS JOIN (VALUES
    ('url', 'https://www.creditcoop.ro/', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.creditcoop.ro/documente/', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.creditcoop.ro/fisiere/Document_Informare_Comisioane_cont-de-plati.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.creditcoop.ro/carduri/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.creditcoop.ro/cont-de-plati-persoane-fizice/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.creditcoop.ro/conturi-curente-persoane-juridice/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cont-curent') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.creditcoop.ro/creditul-imobiliar/', 'produs', 'html', 'playwright', ARRAY(SELECT id FROM produse WHERE nume IN ('ipotecar-refinantare') ORDER BY nume)::BIGINT[], 'lunar', 'pauza'),  -- pauza: metoda playwright e o estimare, nu o masuratoare; incredere_metoda 0.4
    ('url', 'https://www.creditcoop.ro/creditul-nevoi-personale-garantat-cu-ipoteca/', 'produs', 'html', 'playwright', ARRAY(SELECT id FROM produse WHERE nume IN ('ipotecar-refinantare') ORDER BY nume)::BIGINT[], 'saptamanal', 'pauza'),  -- pauza: metoda playwright e o estimare, nu o masuratoare; incredere_metoda 0.4
    ('url', 'https://www.creditcoop.ro/credite-pentru-investitii-imobiliare/', 'produs', 'html', 'playwright', ARRAY(SELECT id FROM produse WHERE nume IN ('ipotecar-refinantare') ORDER BY nume)::BIGINT[], 'saptamanal', 'pauza'),  -- pauza: metoda playwright e o estimare, nu o masuratoare; incredere_metoda 0.4
    ('url', 'https://www.creditcoop.ro/intrebari-frecvente/', 'context', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ')
) AS v (tip_sursa, sursa, rol, format, metoda, produse, frecventa, status)
WHERE b.slug = 'creditcoop'
  AND NOT EXISTS (SELECT 1 FROM surse s WHERE s.sursa = v.sursa)
ON CONFLICT DO NOTHING;
-- ---------------------------------------------------------------------
-- exim  (14 documente)
-- ---------------------------------------------------------------------
INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda,
                   produse, frecventa, status)
SELECT b.id, v.tip_sursa, v.sursa, v.rol, v.format, v.metoda,
       v.produse, v.frecventa, v.status
FROM banci b
CROSS JOIN (VALUES
    ('url', 'https://www.eximbank.ro/documente-diverse/', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.eximbank.ro/curs-valutar/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('curs-valutar-propriu') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.eximbank.ro/indici-bancari/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('robor-euribor') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.eximbank.ro/2022/11/09/cont-curent-tranzactional/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cont-curent', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.eximbank.ro/wp-content/uploads/2026/06/Comisioane-Exim-Banca-Romaneasca.pdf', 'conditii', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cash-management', 'comisioane', 'cont-curent', 'factoring') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.eximbank.ro/2023/11/10/card-de-credit-mastercard-standard/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'dae', 'dobanda-nominala', 'marja-ircc') ORDER BY nume)::BIGINT[], 'trimestrial', 'activ'),
    ('url', 'https://www.eximbank.ro/2022/11/09/creditul-ipotecar/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dae', 'dobanda-nominala', 'ipotecar-refinantare', 'marja-ircc', 'noua-casa') ORDER BY nume)::BIGINT[], 'trimestrial', 'activ'),
    ('url', 'https://www.eximbank.ro/2022/11/09/creditul-ipotecar-pentru-refinantare/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dae', 'dobanda-nominala', 'ipotecar-refinantare', 'marja-ircc') ORDER BY nume)::BIGINT[], 'trimestrial', 'activ'),
    ('url', 'https://www.eximbank.ro/2026/05/25/creditul-noua-casa/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dae', 'dobanda-nominala', 'marja-ircc', 'noua-casa') ORDER BY nume)::BIGINT[], 'trimestrial', 'activ'),
    ('url', 'https://www.eximbank.ro/2022/12/05/factoring-imm-2-10-mil-lei/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('factoring') ORDER BY nume)::BIGINT[], 'lunar', 'pauza'),  -- pauza: incredere_metoda 0.65
    ('url', 'https://www.eximbank.ro/2022/12/05/trezorerie-si-investii/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cash-management') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.eximbank.ro/wp-content/uploads/2026/07/Lista-Dobanzi-Conturi-2.pdf', 'conditii', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cont-curent', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.eximbank.ro/2022/12/05/credite-corporate/', 'produs', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.eximbank.ro/sitemap/', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ')
) AS v (tip_sursa, sursa, rol, format, metoda, produse, frecventa, status)
WHERE b.slug = 'exim'
  AND NOT EXISTS (SELECT 1 FROM surse s WHERE s.sursa = v.sursa)
ON CONFLICT DO NOTHING;
-- ---------------------------------------------------------------------
-- garanti  (17 documente)
-- ---------------------------------------------------------------------
INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda,
                   produse, frecventa, status)
SELECT b.id, v.tip_sursa, v.sursa, v.rol, v.format, v.metoda,
       v.produse, v.frecventa, v.status
FROM banci b
CROSS JOIN (VALUES
    ('url', 'https://www.garantibbva.ro/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'cont-curent', 'dae') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.garantibbva.ro/wp-content/uploads/2025/11/T0012-tarife-si-comisioane-standard-persoane-fizice-10-11-2025.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.garantibbva.ro/wp-content/uploads/2026/04/T0013_V24_Tarife-si-comisioane-standard-pentru-Clientii-IMM_RO.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.garantibbva.ro/persoane-fizice/credit-imobiliar/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dae', 'dobanda-nominala', 'ipotecar-refinantare', 'marja-ircc', 'robor-euribor') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.garantibbva.ro/persoane-fizice/credit-de-nevoi-personale-cu-garantii-reale/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dae', 'dobanda-nominala', 'ipotecar-refinantare', 'marja-ircc', 'robor-euribor') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.garantibbva.ro/persoane-fizice/dobanzi-si-comisioane-credite-persoane-fizice/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dae', 'dobanda-nominala', 'ipotecar-refinantare', 'marja-ircc', 'robor-euribor') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.garantibbva.ro/en/individuals/fees-and-interest-rates-for-loans-to-individuals/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dobanda-nominala', 'marja-ircc', 'robor-euribor') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.garantibbva.ro/en/sme-and-pfa/fees-and-interest-on-sme-and-pfa-loans/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dae', 'dobanda-nominala', 'marja-ircc', 'robor-euribor') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.garantibbva.ro/en/individuals/fees-and-interest-rates-for-individuals-deposits/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dobanda-nominala') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.garantibbva.ro/en/comunicate-de-presa/garanti-caps-interest-rate-for-noua-casa-loans/', 'context', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('marja-ircc', 'noua-casa') ORDER BY nume)::BIGINT[], 'la_descoperire', 'activ'),
    ('url', 'https://www.garantibbva.ro/informatii-comisioane-cont-curent-standard-lei/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.garantibbva.ro/corporate/', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.garantibbva.ro/imm-si-pfa/', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.garantibbva.ro/corporate/scontari-de-creante-comerciale/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('factoring') ORDER BY nume)::BIGINT[], 'lunar', 'pauza'),  -- pauza: incredere_metoda 0.65
    ('url', 'https://www.garantibbva.ro/imm-si-pfa/conturi-si-servicii/managementul-lichiditatilor/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cash-management') ORDER BY nume)::BIGINT[], 'lunar', 'pauza'),  -- pauza: incredere_metoda 0.65
    ('url', 'https://www.garantibbva.ro/documente-utile/', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.garantibbva.ro/persoane-fizice/bonus-card/bonus-card-classic/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ')
) AS v (tip_sursa, sursa, rol, format, metoda, produse, frecventa, status)
WHERE b.slug = 'garanti'
  AND NOT EXISTS (SELECT 1 FROM surse s WHERE s.sursa = v.sursa)
ON CONFLICT DO NOTHING;
-- ---------------------------------------------------------------------
-- ing  (17 documente)
-- ---------------------------------------------------------------------
INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda,
                   produse, frecventa, status)
SELECT b.id, v.tip_sursa, v.sursa, v.rol, v.format, v.metoda,
       v.produse, v.frecventa, v.status
FROM banci b
CROSS JOIN (VALUES
    ('url', 'https://www.ing.ro/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('curs-valutar-propriu') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://ing.ro/persoane-fizice/curs-valutar', 'produs', 'html', 'playwright', ARRAY(SELECT id FROM produse WHERE nume IN ('curs-valutar-propriu') ORDER BY nume)::BIGINT[], 'zilnic', 'pauza'),  -- pauza: metoda playwright e o estimare, nu o masuratoare; incredere_metoda 0.4
    ('url', 'https://ing.ro/curs-valutar-pj', 'produs', 'html', 'playwright', ARRAY(SELECT id FROM produse WHERE nume IN ('curs-valutar-propriu') ORDER BY nume)::BIGINT[], 'zilnic', 'pauza'),  -- pauza: metoda playwright e o estimare, nu o masuratoare; incredere_metoda 0.4
    ('url', 'https://ing.ro/persoane-fizice/credite/ipotecar', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'dobanda-nominala', 'ipotecar-refinantare', 'marja-ircc') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://ing.ro/persoane-fizice/credite/noua-casa', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'dae', 'dobanda-nominala', 'marja-ircc', 'noua-casa', 'robor-euribor') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://ing.ro/persoane-fizice/credite/refinantare', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'ipotecar-refinantare', 'marja-ircc', 'robor-euribor') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://ing.ro/imm/solutii-de-finantare/factoring', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('factoring') ORDER BY nume)::BIGINT[], 'lunar', 'pauza'),  -- pauza: incredere_metoda 0.65
    ('url', 'https://ing.ro/persoane-fizice/carduri-si-conturi/pachete-conturi-curente', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'cont-curent', 'curs-valutar-propriu', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://ing.ro/imm/operatiuni-curente/solutii-de-cont-curent', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://ing.ro/persoane-fizice/credite/extra-rol', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'cont-curent', 'dae', 'dobanda-nominala', 'marja-ircc', 'robor-euribor') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://ing.ro/persoane-fizice/credite/ing-personal', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'dae', 'dobanda-nominala', 'marja-ircc', 'robor-euribor') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://ing.ro/persoane-fizice/carduri-si-conturi/cardurile-ing', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://ing.ro/persoane-fizice/credite/credit-card', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://ing.ro/imm/operatiuni-curente/solutii-complexe-pentru-operatiuni-curente', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cash-management') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://ing.ro/imm/operatiuni-curente/solutii-de-cont-curent/pachetele-ing-fix-cont-curent', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://ing.ro/persoane-fizice/economii-si-investitii/ing-economii-si-depozite-la-termen', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dobanda-nominala') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://ing.ro/imm/Internet-banking/ING-Business-Pro', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cont-curent', 'curs-valutar-propriu', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'lunar', 'activ')
) AS v (tip_sursa, sursa, rol, format, metoda, produse, frecventa, status)
WHERE b.slug = 'ing'
  AND NOT EXISTS (SELECT 1 FROM surse s WHERE s.sursa = v.sursa)
ON CONFLICT DO NOTHING;
-- ---------------------------------------------------------------------
-- intesa  (18 documente)
-- ---------------------------------------------------------------------
INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda,
                   produse, frecventa, status)
SELECT b.id, v.tip_sursa, v.sursa, v.rol, v.format, v.metoda,
       v.produse, v.frecventa, v.status
FROM banci b
CROSS JOIN (VALUES
    ('url', 'https://www.intesasanpaolobank.ro/', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'pauza'),  -- pauza: incredere_metoda 0.6
    ('url', 'https://www.intesasanpaolobank.ro/bine-de-stiut/tarife-si-comisioane.html', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.intesasanpaolobank.ro/document/documents/ISPROMANIA/tarife-comisioane/Tarife-%C8%99i-Comisioane---Persoane-Fizice-valabile-din-15.12.2025.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.intesasanpaolobank.ro/document/documents/ISPROMANIA/tarife-comisioane/LCS-PERSOANE-JURIDICE_Septembrie-2026.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'cash-management', 'comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.intesasanpaolobank.ro/document/documents/ISPROMANIA/tarife-comisioane/Dobanzi-produse-de-economisire-17.09.2026.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dobanda-nominala') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.intesasanpaolobank.ro/document/documents/ISPROMANIA/tarife-comisioane/Costuri-credite.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'dobanda-nominala', 'ipotecar-refinantare', 'marja-ircc', 'noua-casa') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.intesasanpaolobank.ro/document/documents/ISPROMANIA/kfs/caracteristici-noua-casa.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('marja-ircc', 'noua-casa') ORDER BY nume)::BIGINT[], 'saptamanal', 'pauza'),  -- pauza: adresa raportata fara sa fi fost deschisa
    ('url', 'https://www.intesasanpaolobank.ro/persoane-fizice/credite/credit-nevoi-personale.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dae', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.intesasanpaolobank.ro/persoane-fizice/credite/credit-ipotecar-campanie.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dae', 'dobanda-nominala', 'ipotecar-refinantare', 'marja-ircc', 'robor-euribor') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.intesasanpaolobank.ro/persoane-fizice/pachet-card-cont.html', 'hub', 'html', 'playwright', '{}'::BIGINT[], 'saptamanal', 'pauza'),  -- pauza: metoda playwright e o estimare, nu o masuratoare; incredere_metoda 0.4
    ('url', 'https://www.intesasanpaolobank.ro/persoane-fizice/curs-valutar.html', 'produs', 'html', 'playwright', '{}'::BIGINT[], 'zilnic', 'pauza'),  -- pauza: metoda playwright e o estimare, nu o masuratoare; incredere_metoda 0.3
    ('url', 'https://www.intesasanpaolobank.ro/en/persoane-fizice/card-credit.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.intesasanpaolobank.ro/imm/credite-imm/leasing-imm.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('leasing', 'marja-ircc', 'robor-euribor') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.intesasanpaolobank.ro/imm', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.intesasanpaolobank.ro/corporate', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.intesasanpaolobank.ro/microintreprinderi-antreprenori', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.intesasanpaolobank.ro/corporate/cash-management.html', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'pauza'),  -- pauza: incredere_metoda 0.6
    ('url', 'https://www.intesasanpaolobank.ro/corporate/Finantarea-comertului-corporate/Factoring-Corporate.html', 'produs', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ')
) AS v (tip_sursa, sursa, rol, format, metoda, produse, frecventa, status)
WHERE b.slug = 'intesa'
  AND NOT EXISTS (SELECT 1 FROM surse s WHERE s.sursa = v.sursa)
ON CONFLICT DO NOTHING;
-- ---------------------------------------------------------------------
-- libra  (12 documente)
-- ---------------------------------------------------------------------
INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda,
                   produse, frecventa, status)
SELECT b.id, v.tip_sursa, v.sursa, v.rol, v.format, v.metoda,
       v.produse, v.frecventa, v.status
FROM banci b
CROSS JOIN (VALUES
    ('url', 'https://www.librabank.ro/', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.librabank.ro/comisioane', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.librabank.ro/Curs_valutar', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('curs-valutar-propriu') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.librabank.ro/dobanda-simulare-imprumut-credit-ipotecar', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dae', 'dobanda-nominala', 'ipotecar-refinantare', 'marja-ircc', 'robor-euribor') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.librabank.ro/card-de-credit-cumparaturi', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'comisioane', 'dae', 'dobanda-nominala', 'marja-ircc', 'robor-euribor') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.librabank.ro/leasing-financiar', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('leasing') ORDER BY nume)::BIGINT[], 'lunar', 'pauza'),  -- pauza: incredere_metoda 0.65
    ('url', 'https://www.librabank.ro/dobanzi-depozite-la-termen', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dobanda-nominala') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.librabank.ro/documente_contractuale/Tarife_si_Comisioane_PF.pdf', 'conditii', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.librabank.ro/documente_contractuale/Tarife_si_Comisioane_PJ.pdf', 'conditii', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cash-management', 'comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.librabank.ro/credit-nevoi-personale-cu-ipoteca', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dae', 'dobanda-nominala', 'ipotecar-refinantare', 'marja-ircc', 'robor-euribor') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.librabank.ro/credit-overdraft', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dae', 'dobanda-nominala', 'marja-ircc', 'robor-euribor') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.librabank.ro/card-business', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane') ORDER BY nume)::BIGINT[], 'lunar', 'activ')
) AS v (tip_sursa, sursa, rol, format, metoda, produse, frecventa, status)
WHERE b.slug = 'libra'
  AND NOT EXISTS (SELECT 1 FROM surse s WHERE s.sursa = v.sursa)
ON CONFLICT DO NOTHING;
-- ---------------------------------------------------------------------
-- nexent  (15 documente)
-- ---------------------------------------------------------------------
INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda,
                   produse, frecventa, status)
SELECT b.id, v.tip_sursa, v.sursa, v.rol, v.format, v.metoda,
       v.produse, v.frecventa, v.status
FROM banci b
CROSS JOIN (VALUES
    ('url', 'https://www.nexentbank.ro/', 'hub', 'html', 'http', '{}'::BIGINT[], 'la_descoperire', 'activ'),
    ('url', 'https://www.nexentbank.ro/Standard-interests-fees-and-commissions', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('curs-valutar-propriu', 'dobanda-nominala', 'robor-euribor') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.nexentbank.ro/upload/media/document/0001/07/311089d6c56fae2ffc6b154a5634e774b78cac8c.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'comisioane', 'dae', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.nexentbank.ro/upload/media/document/0001/07/d79f5526970ef9646a7cdb4cb18416b9052414a9.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.nexentbank.ro/upload/media/document/0001/06/392a1102707c42b193f6f9bf8307ee75bbe2c491.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dae', 'dobanda-nominala', 'ipotecar-refinantare', 'marja-ircc') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.nexentbank.ro/Persoane-Juridice/Intreprinderi-Mici-si-Mijlocii/Credite-IMM', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'pauza'),  -- pauza: incredere_metoda 0.6
    ('url', 'https://www.nexentbank.ro/Persoane-Juridice/Corporatii/Cash-management', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cash-management', 'curs-valutar-propriu', 'robor-euribor') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.nexentbank.ro/Persoane-Juridice/Corporatii/Finantari', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'pauza'),  -- pauza: incredere_metoda 0.65
    ('url', 'https://www.nexentbank.ro/Persoane-Juridice/Intreprinderi-Mici-si-Mijlocii/Credite-IMM/Finantarea-creantelor', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('factoring') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.nexentbank.ro/persoane-fizice/Credite/Creditul-Acasa', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dae', 'dobanda-nominala', 'ipotecar-refinantare', 'marja-ircc') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.nexentbank.ro/persoane-fizice/Credite', 'hub', 'html', 'http', '{}'::BIGINT[], 'la_descoperire', 'pauza'),  -- pauza: incredere_metoda 0.65
    ('url', 'https://www.nexentbank.ro/persoane-fizice/Conturi-curente', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'cont-curent', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.nexentbank.ro/persoane-fizice/Carduri-de-credit/CardAvantaj', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit') ORDER BY nume)::BIGINT[], 'saptamanal', 'pauza'),  -- pauza: incredere_metoda 0.55
    ('url', 'https://www.nexentbank.ro/dobanzi-cotatii-si-cursuri/cursuri', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('curs-valutar-propriu') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.nexentbank.ro/dobanzi-cotatii-si-cursuri/indici-ai-pietei-monetare', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('robor-euribor') ORDER BY nume)::BIGINT[], 'zilnic', 'activ')
) AS v (tip_sursa, sursa, rol, format, metoda, produse, frecventa, status)
WHERE b.slug = 'nexent'
  AND NOT EXISTS (SELECT 1 FROM surse s WHERE s.sursa = v.sursa)
ON CONFLICT DO NOTHING;
-- ---------------------------------------------------------------------
-- patria  (18 documente)
-- ---------------------------------------------------------------------
INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda,
                   produse, frecventa, status)
SELECT b.id, v.tip_sursa, v.sursa, v.rol, v.format, v.metoda,
       v.produse, v.frecventa, v.status
FROM banci b
CROSS JOIN (VALUES
    ('url', 'https://en.patriabank.ro/exchange-rates', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('curs-valutar-propriu') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.patriabank.ro/persoane-fizice/credite/creditul-de-nevoi-personale-cu-ipoteca', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dae', 'dobanda-nominala', 'ipotecar-refinantare', 'marja-ircc', 'robor-euribor') ORDER BY nume)::BIGINT[], 'trimestrial', 'pauza'),  -- pauza: incredere_metoda 0.55
    ('url', 'https://en.patriabank.ro/persoane-fizice/credite/creditul-ipotecar-patria-acasa', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dae', 'ipotecar-refinantare', 'marja-ircc', 'robor-euribor') ORDER BY nume)::BIGINT[], 'trimestrial', 'pauza'),  -- pauza: incredere_metoda 0.55
    ('url', 'https://en.patriabank.ro/persoane-fizice/credite/credit-refinantare-online-credit-ipotecar', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dae', 'dobanda-nominala', 'ipotecar-refinantare', 'marja-ircc', 'robor-euribor') ORDER BY nume)::BIGINT[], 'trimestrial', 'pauza'),  -- pauza: incredere_metoda 0.55
    ('url', 'https://www.patriabank.ro/persoane-fizice/credite/descoperit-de-cont', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dae', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'lunar', 'pauza'),  -- pauza: incredere_metoda 0.55; adresa raportata fara sa fi fost deschisa
    ('url', 'https://en.patriabank.ro/persoane-fizice/carduri-si-conturi/card-de-credit', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit') ORDER BY nume)::BIGINT[], 'lunar', 'pauza'),  -- pauza: incredere_metoda 0.5
    ('url', 'https://en.patriabank.ro/creditonline', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cont-curent', 'dae', 'dobanda-nominala', 'marja-ircc') ORDER BY nume)::BIGINT[], 'trimestrial', 'pauza'),  -- pauza: incredere_metoda 0.5
    ('url', 'https://www.patriabank.ro/persoane-fizice/credite/credit-de-nevoi-personale-patria-plus', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dobanda-nominala', 'marja-ircc') ORDER BY nume)::BIGINT[], 'trimestrial', 'pauza'),  -- pauza: incredere_metoda 0.5; adresa raportata fara sa fi fost deschisa
    ('url', 'https://en.patriabank.ro/persoane-fizice/credite/credit-de-consum-econom', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'dae', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'trimestrial', 'pauza'),  -- pauza: incredere_metoda 0.5; adresa raportata fara sa fi fost deschisa
    ('url', 'https://en.patriabank.ro/persoane-fizice/economii/depozite-bancare', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'zilnic', 'pauza'),  -- pauza: incredere_metoda 0.5
    ('url', 'https://www.patriabank.ro/imm/operatiuni-curente', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cash-management', 'cont-curent') ORDER BY nume)::BIGINT[], 'lunar', 'pauza'),  -- pauza: incredere_metoda 0.45
    ('url', 'https://www.patriabank.ro/imm/credite/factoring-intern-cu-recurs', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('factoring') ORDER BY nume)::BIGINT[], 'lunar', 'pauza'),  -- pauza: incredere_metoda 0.5
    ('url', 'https://www.patriabank.ro/imm/credite/credite-pentru-activitatea-curenta', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'pauza'),  -- pauza: incredere_metoda 0.45; adresa raportata fara sa fi fost deschisa
    ('url', 'https://www.patriabank.ro/imm_corporate', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'pauza'),  -- pauza: incredere_metoda 0.45
    ('url', 'https://www.patriabank.ro/afaceri-mici/operatiuni-curente/pachete-de-cont-curent', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'lunar', 'pauza'),  -- pauza: incredere_metoda 0.5
    ('url', 'https://www.patriabank.ro/persoane-fizice/carduri-si-conturi/servicii-de-baza', 'conditii', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'pauza'),  -- pauza: incredere_metoda 0.45
    ('url', 'https://www.patriabank.ro/despre-patria/informatii-presa/comunicate-de-presa/credit-ipotecar-fara-avans-in-bani', 'context', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dobanda-nominala', 'ipotecar-refinantare', 'marja-ircc', 'robor-euribor') ORDER BY nume)::BIGINT[], 'la_descoperire', 'pauza'),  -- pauza: incredere_metoda 0.55; adresa raportata fara sa fi fost deschisa
    ('url', 'https://www.patriabank.ro/persoane-fizice', 'hub', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('ipotecar-refinantare') ORDER BY nume)::BIGINT[], 'saptamanal', 'pauza')  -- pauza: incredere_metoda 0.5
) AS v (tip_sursa, sursa, rol, format, metoda, produse, frecventa, status)
WHERE b.slug = 'patria'
  AND NOT EXISTS (SELECT 1 FROM surse s WHERE s.sursa = v.sursa)
ON CONFLICT DO NOTHING;
-- ---------------------------------------------------------------------
-- pko  (7 documente)
-- ---------------------------------------------------------------------
INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda,
                   produse, frecventa, status)
SELECT b.id, v.tip_sursa, v.sursa, v.rol, v.format, v.metoda,
       v.produse, v.frecventa, v.status
FROM banci b
CROSS JOIN (VALUES
    ('url', 'https://www.pkobp.pl/ro/filiala-romania', 'context', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.pkobp.pl/ro/filiala-romania/produse', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.pkobp.pl/ro/filiala-romania/documente', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.pkobp.pl/api/public/496b3921-7d8c-4694-9ac7-738457471fab.pdf?content-disposition=filename=Lista_de_preturi_(cu_1.05.2026).pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cash-management', 'comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.pkobp.pl/api/public/0207e7ad-b15e-43c3-bc65-ab25ba54ba5e.pdf?content-disposition=filename=Lista_de_preturi.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cash-management', 'comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.pkobp.pl/api/public/2b04fb89-3eaf-4316-bbce-dc79d8f58b12.pdf?content-disposition=filename=Ratele_dobânzilor.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dobanda-nominala', 'marja-ircc', 'robor-euribor') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.pkobp.pl/api/public/3edd41b7-b421-4021-abbc-a39bf0a99b17.pdf?content-disposition=filename=Fișă_informativă_pentru_deponenți.pdf', 'conditii', 'pdf', 'http', '{}'::BIGINT[], 'la_descoperire', 'activ')
) AS v (tip_sursa, sursa, rol, format, metoda, produse, frecventa, status)
WHERE b.slug = 'pko'
  AND NOT EXISTS (SELECT 1 FROM surse s WHERE s.sursa = v.sursa)
ON CONFLICT DO NOTHING;
-- ---------------------------------------------------------------------
-- procredit  (17 documente)
-- ---------------------------------------------------------------------
INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda,
                   produse, frecventa, status)
SELECT b.id, v.tip_sursa, v.sursa, v.rol, v.format, v.metoda,
       v.produse, v.frecventa, v.status
FROM banci b
CROSS JOIN (VALUES
    ('url', 'https://www.procreditbank.ro/lista-de-preturi/', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.procreditbank.ro/documente-utile/', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.procreditbank.ro/lista-cursurilor-de-schimb/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('curs-valutar-propriu') ORDER BY nume)::BIGINT[], 'zilnic', 'pauza'),  -- pauza: incredere_metoda 0.55
    ('url', 'https://www.procreditbank.ro/persoane-fizice/pachete-cont-bancar/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.procreditbank.ro/persoane-fizice/credit-imobiliar-ipotecar/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'dae', 'dobanda-nominala', 'ipotecar-refinantare', 'marja-ircc', 'noua-casa', 'robor-euribor') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.procreditbank.ro/persoane-fizice/credit-de-nevoi-personale/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'dae', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.procreditbank.ro/persoane-fizice/overdraft-flexfund/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.procreditbank.ro/persoane-fizice/carduri-visa/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.procreditbank.ro/persoane-fizice/depozit-la-termen/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dobanda-nominala') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.procreditbank.ro/persoane-fizice/cont-economii-flexsave/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cont-curent', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.procreditbank.ro/companii/servicii-bancare/solutii-cash-management/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cash-management') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.procreditbank.ro/companii/servicii-bancare/cont-curent/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'lunar', 'pauza'),  -- pauza: incredere_metoda 0.6
    ('url', 'https://www.procreditbank.ro/companii/servicii-bancare/carduri-visa-business/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.procreditbank.ro/companii/credite/limita-de-credit/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cash-management') ORDER BY nume)::BIGINT[], 'lunar', 'pauza'),  -- pauza: incredere_metoda 0.65
    ('url', 'https://www.procreditbank.ro/companii/credite/credite-pentru-investitii/', 'produs', 'html', 'http', '{}'::BIGINT[], 'lunar', 'pauza'),  -- pauza: incredere_metoda 0.65
    ('url', 'https://www.procreditbank.ro/companii/depozite-la-termen/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dobanda-nominala') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.procreditbank.ro/', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ')
) AS v (tip_sursa, sursa, rol, format, metoda, produse, frecventa, status)
WHERE b.slug = 'procredit'
  AND NOT EXISTS (SELECT 1 FROM surse s WHERE s.sursa = v.sursa)
ON CONFLICT DO NOTHING;
-- ---------------------------------------------------------------------
-- raiffeisen  (19 documente)
-- ---------------------------------------------------------------------
INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda,
                   produse, frecventa, status)
SELECT b.id, v.tip_sursa, v.sursa, v.rol, v.format, v.metoda,
       v.produse, v.frecventa, v.status
FROM banci b
CROSS JOIN (VALUES
    ('url', 'https://www.raiffeisen.ro/content/dam/rbi/retail/eu/ro/documents/pf/tarife-comisioane-standard-pf.sv.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'comisioane', 'cont-curent', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.raiffeisen.ro/content/dam/rbi/retail/eu/ro/documents/pj/tarife-si-comisioane-imm-si-profesii-liberale.sv.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'cash-management', 'comisioane', 'cont-curent', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.raiffeisen.ro/content/dam/rbi/retail/eu/ro/documents/corporatii/tarife-si-comisioane-standard.sv.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'cash-management', 'comisioane', 'cont-curent', 'factoring') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.raiffeisen.ro/ro/home/curs-valutar.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('curs-valutar-propriu') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.raiffeisen.ro/ro/persoane-fizice/produsele-noastre/credite/credit-imobiliar-casa-ta.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dae', 'ipotecar-refinantare', 'marja-ircc', 'robor-euribor') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.raiffeisen.ro/ro/imm.html', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.raiffeisen.ro/ro/corporatii.html', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'pauza'),  -- pauza: incredere_metoda 0.6
    ('url', 'https://www.raiffeisen.ro/content/dam/rbi/retail/eu/ro/documents/pf/tarife-comisioane-standard-pf.sv.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dobanda-nominala') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.raiffeisen.ro/ro/imm/produse-si-servicii/finantare/leasing-financiar.html', 'produs', 'html', 'playwright', ARRAY(SELECT id FROM produse WHERE nume IN ('leasing') ORDER BY nume)::BIGINT[], 'lunar', 'pauza'),  -- pauza: metoda playwright e o estimare, nu o masuratoare; incredere_metoda 0.5
    ('url', 'https://www.raiffeisen.ro/ro/corporatii/produse-si-servicii/solutii-de-finantare/factoring.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('factoring') ORDER BY nume)::BIGINT[], 'lunar', 'pauza'),  -- pauza: adresa raportata fara sa fi fost deschisa
    ('url', 'https://www.raiffeisen.ro/ro/corporatii/produse-si-servicii/plati-si-cash-management.html', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.raiffeisen.ro/ro/corporatii/produse-si-servicii/managementul-lichiditatilor.html', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.raiffeisen.ro/ro/persoane-fizice/produsele-noastre/credite/credit-de-refinantare-fara-ipoteca.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dae', 'dobanda-nominala', 'ipotecar-refinantare') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.raiffeisen.ro/ro/persoane-fizice/produsele-noastre/credite/overdraft.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dae', 'dobanda-nominala', 'marja-ircc', 'robor-euribor') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.raiffeisen.ro/ro/persoane-fizice/produsele-noastre/carduri/carduri-de-cumparaturi.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.raiffeisen.ro/ro/persoane-fizice/in-sprijinul-tau/informatii-utile.html', 'context', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('robor-euribor') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.raiffeisen.ro/ro/persoane-fizice/produsele-noastre/credite/creditul-imobiliar-prin-programul-guvernamental-noua-casa.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dae', 'ipotecar-refinantare', 'marja-ircc', 'noua-casa', 'robor-euribor') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.raiffeisen.ro/ro/persoane-fizice/produsele-noastre/credite/credit-de-refinantare-garantat-cu-ipoteca.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dae', 'ipotecar-refinantare', 'marja-ircc', 'robor-euribor') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.raiffeisen.ro/', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ')
) AS v (tip_sursa, sursa, rol, format, metoda, produse, frecventa, status)
WHERE b.slug = 'raiffeisen'
  AND NOT EXISTS (SELECT 1 FROM surse s WHERE s.sursa = v.sursa)
ON CONFLICT DO NOTHING;
-- ---------------------------------------------------------------------
-- revolut  (16 documente)
-- ---------------------------------------------------------------------
INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda,
                   produse, frecventa, status)
SELECT b.id, v.tip_sursa, v.sursa, v.rol, v.format, v.metoda,
       v.produse, v.frecventa, v.status
FROM banci b
CROSS JOIN (VALUES
    ('url', 'https://www.revolut.com/en-RO/', 'context', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cont-curent', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.revolut.com/en-RO/our-pricing-plans/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'cont-curent', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.revolut.com/en-RO/business/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cash-management', 'cont-curent', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.revolut.com/en-RO/personal-loans/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dae', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.revolut.com/en-RO/refi-loan/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dae', 'dobanda-nominala', 'ipotecar-refinantare') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.revolut.com/en-RO/legal/', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.revolut.com/en-RO/legal/fees/', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.revolut.com/en-RO/legal/business-fees/', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.revolut.com/en-RO/legal/branch-fid/', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://cdn.revolut.com/terms_and_conditions/pdf/fee_information_document_romania_f71ed713_1.3.0_1778170731_en.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.revolut.com/en-RO/cards/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.revolut.com/en-RO/legal/standard-fees/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.revolut.com/en-RO/legal/business-basic-fees/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cash-management', 'comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.revolut.com/en-RO/instant-access-savings/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dobanda-nominala') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.revolut.com/ro-RO/currency-converter/convert-eur-to-ron-exchange-rate/?amount=20000', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('curs-valutar-propriu') ORDER BY nume)::BIGINT[], 'zilnic', 'pauza'),  -- pauza: adresa raportata fara sa fi fost deschisa
    ('url', 'https://www.revolut.com/en-RO/business/business-account-plans/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cash-management', 'comisioane', 'cont-curent', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'lunar', 'activ')
) AS v (tip_sursa, sursa, rol, format, metoda, produse, frecventa, status)
WHERE b.slug = 'revolut'
  AND NOT EXISTS (SELECT 1 FROM surse s WHERE s.sursa = v.sursa)
ON CONFLICT DO NOTHING;
-- salt: inventar fara documente, nimic de inserat
-- ---------------------------------------------------------------------
-- tbi  (12 documente)
-- ---------------------------------------------------------------------
INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda,
                   produse, frecventa, status)
SELECT b.id, v.tip_sursa, v.sursa, v.rol, v.format, v.metoda,
       v.produse, v.frecventa, v.status
FROM banci b
CROSS JOIN (VALUES
    ('url', 'https://tbibank.ro/despre-tbi-group/documente/', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://tbibank.ro/wp-content/uploads/2026/09/Lista-de-dobanzi-taxe-si-comisioane-pentru-persoane-fizice_30.03.2026-1.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'cont-curent', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://tbibank.ro/wp-content/uploads/2026/09/Document-de-informare-cu-privire-la-comisioane_Cont-curent-standard-1.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://tbibank.ro/wp-content/uploads/docs/Documente%20pentru%20persoane%20juridice/Lista%20de%20dobanzi%2C%20taxe%20si%20comisioane%20pentru%20persoane%20juridice%20si%20entitati%20asimilate.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'cont-curent', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://tbibank.ro/persoane-fizice/operatiuni-bancare/operatiuni-cont-curent/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'pauza'),  -- pauza: incredere_metoda 0.65
    ('url', 'https://tbibank.ro/rate-de-schimb/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('curs-valutar-propriu') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://tbibank.ro/product/depozitul-online/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dobanda-nominala') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://tbibank.ro/product/creditul-tau-personal/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'dae', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://tbibank.ro/companii/depozite/depozit-persoane-juridice/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://tbibank.ro/en/business-banking/', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'pauza'),  -- pauza: adresa raportata fara sa fi fost deschisa
    ('url', 'https://tbibank.ro/en/business-banking/payments/accounts/', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cash-management') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://tbibank.ro/despre-tbi-group/tbi-leasing/', 'context', 'html', 'http', '{}'::BIGINT[], 'la_descoperire', 'activ')
) AS v (tip_sursa, sursa, rol, format, metoda, produse, frecventa, status)
WHERE b.slug = 'tbi'
  AND NOT EXISTS (SELECT 1 FROM surse s WHERE s.sursa = v.sursa)
ON CONFLICT DO NOTHING;
-- ---------------------------------------------------------------------
-- techventures  (1 documente)
-- ---------------------------------------------------------------------
INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda,
                   produse, frecventa, status)
SELECT b.id, v.tip_sursa, v.sursa, v.rol, v.format, v.metoda,
       v.produse, v.frecventa, v.status
FROM banci b
CROSS JOIN (VALUES
    ('url', 'https://techventures.bank/', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ')
) AS v (tip_sursa, sursa, rol, format, metoda, produse, frecventa, status)
WHERE b.slug = 'techventures'
  AND NOT EXISTS (SELECT 1 FROM surse s WHERE s.sursa = v.sursa)
ON CONFLICT DO NOTHING;
-- ---------------------------------------------------------------------
-- unicredit  (18 documente)
-- ---------------------------------------------------------------------
INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda,
                   produse, frecventa, status)
SELECT b.id, v.tip_sursa, v.sursa, v.rol, v.format, v.metoda,
       v.produse, v.frecventa, v.status
FROM banci b
CROSS JOIN (VALUES
    ('url', 'https://www.unicredit.ro/ro/persoane-fizice.html', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'pauza'),  -- pauza: adresa raportata fara sa fi fost deschisa
    ('url', 'https://www.unicredit.ro/ro/persoane-fizice/Diverse/documente-utile.html', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.unicredit.ro/content/dam/cee2020-pws-ro/DocumentePDF/TarifeComisioanePI/Comisioane-si-dobanzi_PI.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'comisioane', 'cont-curent', 'dobanda-nominala', 'marja-ircc', 'robor-euribor') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.unicredit.ro/ro/persoane-fizice/Tranzactionare/SchimbValutar.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('curs-valutar-propriu', 'robor-euribor') ORDER BY nume)::BIGINT[], 'zilnic', 'pauza'),  -- pauza: incredere_metoda 0.6
    ('url', 'https://www.unicredit.ro/ro/persoane-fizice/Credite/reforma-indicilor-de-referinta.html', 'context', 'html', 'http', '{}'::BIGINT[], 'la_descoperire', 'activ'),
    ('url', 'https://www.unicredit.ro/ro/imm.html', 'hub', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cont-curent') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.unicredit.ro/ro/cib.html', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.unicredit.ro/ro/cib/finantare/factoring.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('factoring') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.unicredit.ro/ro/cib/finantare/leasing.html', 'hub', 'html', 'http', '{}'::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.unicredit.ro/ro/cib/cash-management/cont-curent-lichiditati-plati-si-colectari.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cash-management', 'comisioane', 'cont-curent', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.unicredit.ro/ro/persoane-fizice/Credite/credite-ipoteca.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'dae', 'dobanda-nominala', 'ipotecar-refinantare', 'marja-ircc') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.unicredit.ro/ro/persoane-fizice/Credite/credite-ipoteca/Calculator-ipotecare.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dae', 'ipotecar-refinantare', 'marja-ircc', 'robor-euribor') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.unicredit.ro/content/dam/cee2020-pws-ro/DocumentePDF/TarifeComisioanePI/CD-103-Comisioane-Dobanzi-ProduseCreditare-PersoaneFizice.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'comisioane', 'dae', 'dobanda-nominala', 'ipotecar-refinantare', 'marja-ircc', 'noua-casa', 'robor-euribor') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.unicredit.ro/ro/persoane-fizice/Credite/creditul-de-refinantare.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'dae', 'dobanda-nominala', 'ipotecar-refinantare') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.unicredit.ro/ro/persoane-fizice/Credite/carduri-de-credit.html', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'comisioane', 'dae', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.unicredit.ro/content/dam/cee2020-pws-ro/DocumentePDF/TarifeComisioaneCIB/Taxe-si-Comisioane-Corporate.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'cash-management', 'comisioane', 'cont-curent', 'dobanda-nominala', 'marja-ircc', 'robor-euribor') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.unicredit.ro/ro/imm/diverse/documente-utile.html', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.unicredit.ro/ro/cib/diverse/documente-utile.html', 'hub', 'html', 'http', '{}'::BIGINT[], 'saptamanal', 'activ')
) AS v (tip_sursa, sursa, rol, format, metoda, produse, frecventa, status)
WHERE b.slug = 'unicredit'
  AND NOT EXISTS (SELECT 1 FROM surse s WHERE s.sursa = v.sursa)
ON CONFLICT DO NOTHING;
-- ---------------------------------------------------------------------
-- vista  (15 documente)
-- ---------------------------------------------------------------------
INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda,
                   produse, frecventa, status)
SELECT b.id, v.tip_sursa, v.sursa, v.rol, v.format, v.metoda,
       v.produse, v.frecventa, v.status
FROM banci b
CROSS JOIN (VALUES
    ('url', 'https://www.vistabank.ro/', 'hub', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cont-curent', 'dobanda-nominala', 'marja-ircc') ORDER BY nume)::BIGINT[], 'zilnic', 'pauza'),  -- pauza: incredere_metoda 0.6
    ('url', 'https://www.vistabank.ro/public/docs/Indici_referinta_SEP26_RO.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('robor-euribor') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.vistabank.ro/public/docs/1000312_Anexa_1_CGA_PF_RO_12.2025.pdf?v=2', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'comisioane', 'cont-curent', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.vistabank.ro/public/docs/1000319_Anexa_1_CGA_PJ_RO_11.2025.pdf', 'produs', 'pdf', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'cash-management', 'comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'saptamanal', 'activ'),
    ('url', 'https://www.vistabank.ro/persoane-fizice/conturi-si-pachete-de-cont-curent', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.vistabank.ro/persoane-fizice/credite', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'dae', 'dobanda-nominala', 'ipotecar-refinantare', 'marja-ircc', 'noua-casa', 'robor-euribor') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.vistabank.ro/persoane-fizice/depozite', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('cont-curent', 'dobanda-nominala') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.vistabank.ro/persoane-juridice/conturi-curente', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('comisioane', 'cont-curent') ORDER BY nume)::BIGINT[], 'lunar', 'activ'),
    ('url', 'https://www.vistabank.ro/persoane-juridice/credite', 'hub', 'html', 'playwright', '{}'::BIGINT[], 'lunar', 'pauza'),  -- pauza: metoda playwright e o estimare, nu o masuratoare; incredere_metoda 0.5
    ('url', 'https://www.vistabank.ro/trezorerie', 'context', 'html', 'http', '{}'::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.vistabank.ro/persoane-fizice/carduri', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'dae', 'dobanda-nominala', 'marja-ircc') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.vistabank.ro/persoane-juridice/carduri-de-business', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('card-de-credit', 'dobanda-nominala', 'robor-euribor') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.vistabank.ro/agri', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dobanda-nominala', 'robor-euribor') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.vistabank.ro/persoane-juridice/depozite-la-termen', 'produs', 'html', 'http', ARRAY(SELECT id FROM produse WHERE nume IN ('dobanda-nominala') ORDER BY nume)::BIGINT[], 'zilnic', 'activ'),
    ('url', 'https://www.vistabank.ro/calculator-schimb-valutar-carduri', 'produs', 'html', 'playwright', '{}'::BIGINT[], 'zilnic', 'pauza')  -- pauza: metoda playwright e o estimare, nu o masuratoare; incredere_metoda 0.4
) AS v (tip_sursa, sursa, rol, format, metoda, produse, frecventa, status)
WHERE b.slug = 'vista'
  AND NOT EXISTS (SELECT 1 FROM surse s WHERE s.sursa = v.sursa)
ON CONFLICT DO NOTHING;

COMMIT;


-- ---------------------------------------------------------------------
-- Verificare
-- ---------------------------------------------------------------------
-- SELECT b.slug, count(*) FROM surse s JOIN banci b ON b.id = s.id_banca
--   GROUP BY b.slug ORDER BY 2 DESC;
-- SELECT status, count(*) FROM surse GROUP BY status;
-- Surse fara niciun produs (hub-uri si context):
-- SELECT count(*) FROM surse WHERE cardinality(produse) = 0;
-- Produse din inventare care nu s-au gasit in tabelul `produse`:
-- SELECT s.sursa FROM surse s WHERE cardinality(s.produse) = 0 AND s.rol = 'produs';
