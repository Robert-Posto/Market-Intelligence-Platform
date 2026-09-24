-- Migrarea 015: varianta de produs (coloana din tabelul de tarife) și rolul
-- `locator` pentru paginile de rețea (ATM/sucursale).
--
-- `coloana`: parser_tarife o citea la 1.100 din 5.578 de rânduri (Visa /
-- Mastercard / Gold), dar se pierdea înainte de bază, iar deduplicarea unea
-- variantele diferite ca și cum ar fi același produs (2.081 de rânduri unite
-- pe eșantion; 1.710 cu coloana în cheie).
--
-- După rulare: db/sincronizeaza_vederi.sql

ALTER TABLE observations ADD COLUMN IF NOT EXISTS coloana TEXT;

ALTER TABLE surse DROP CONSTRAINT IF EXISTS surse_rol_check;
ALTER TABLE surse ADD CONSTRAINT surse_rol_check
  CHECK (rol IN ('produs', 'hub', 'conditii', 'context', 'locator'));
