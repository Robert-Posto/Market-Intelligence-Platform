-- Migrarea 007: proveniența `bs4_llm` — extracție BS4 peste surse găsite de LLM.
--
-- De ce o valoare nouă și nu `bs4`: sunt două rulări diferite, cu liste de
-- intrare diferite, iar `bs4` se șterge în întregime la reîncărcarea
-- depozitelor (loaderul e idempotent prin DELETE pe metoda_extractie). Fără
-- valoare separată, o reîncărcare a depozitelor ar șterge silențios rezultatul
-- unei rulări de 200 de pagini.
--
-- Semantic e și corect: `bs4` = scraperul propriu pe lista proprie de bănci;
-- `bs4_llm` = același extractor, dar pe URL-urile descoperite de discovery-ul
-- LLM. A doua variantă e singura care ajunge la bănci ca banca-transilvania,
-- unicredit, cec, intesa, citibank — care aveau surse descoperite și zero date.
--
-- `surse.ultima_rulare` se completează la extracție, ca o rulare următoare să
-- poată fi incrementală.

ALTER TABLE observations DROP CONSTRAINT IF EXISTS observations_metoda_extractie_check;
ALTER TABLE observations ADD CONSTRAINT observations_metoda_extractie_check
  CHECK (metoda_extractie IN ('playwright', 'bs4', 'bs4_llm', 'llm', 'manual'));

-- Motivul pentru care o sursă n-a produs nimic e informație, nu lipsă de
-- informație: „blocat de robots.txt" și „pagină încărcată prin JS" cer acțiuni
-- diferite. Fără coloana asta, ambele arată identic (sursă fără observații).
ALTER TABLE surse ADD COLUMN IF NOT EXISTS nota_extractie TEXT;

CREATE INDEX IF NOT EXISTS ix_surse_neextrase
  ON surse (id_banca) WHERE metoda_extractie IS NULL;
