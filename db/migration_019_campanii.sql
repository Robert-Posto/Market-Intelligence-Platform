-- Migrarea 019: campaniile de pe site-urile băncilor și comunicatele de presă
-- (pagina 2.4 „Campanii & marketing").
--
-- DE CE tabele separate și nu `observations`: o campanie nu e un preț. Pe
-- 29.09.2026, 432 de valori din pagini de campanie și din regulamente
-- apăreau ca prețuri (Cetelem cu 0% la credite, Garanti cu 6,50% la depozite
-- din campanii încheiate); migrările 023 și 025 le ascund la afișare. Aici
-- stă campania ca atare: ce oferă, cui, între ce date, cu citatul din care
-- s-a citit fiecare câmp. Valorile din campanii NU se scriu în `observations`.
--
-- Definiția e cea strictă (Nicolae, §9.1 varianta b): `tip_oferta` =
-- 'campanie' doar cu o fereastră în timp citită din text. Programele
-- permanente și ofertele fără termen se păstrează, cu `tip_oferta` 'program'
-- / 'oferta_curenta'; ce nu se poate decide din text rămâne NULL, cu
-- `stare` = 'de_verificat' și motivul în `motiv_verificare`. Nu se ghicește
-- (extracția e deterministă, fără LLM: §9.6 calea c).
--
-- Scriere: DOAR `ingest/normalizeaza_campanii.py` (brut → rând). Colectorul e
-- `ingest/campanii.py`.
--
-- Idempotentă: IF NOT EXISTS / DROP ... IF EXISTS peste tot; rulată de două
-- ori dă aceeași structură și nu atinge rândurile existente.
--
-- După rulare: db/sincronizeaza_vederi.sql (recreează `campanii_curente`).

BEGIN;

-- --------------------------------------------------------------------------
-- Rolurile noi în `surse`. Paginile și documentele de campanie se înregistrează
-- ca surse (legătura N:M de mai jos, iar ruta `/pdf` servește doar URL-uri din
-- `surse`), dar cu rol propriu: `populare_initiala.surse_active` și
-- `din_bronze` citesc doar 'produs', 'conditii', 'locator', deci un comunicat
-- sau un regulament de campanie nu mai poate fi parsat ca listă de prețuri.
-- Pe drumul ăsta a intrat comunicatul Exim cu 0% la conturi (Nicolae, §4.3).
-- --------------------------------------------------------------------------
ALTER TABLE surse DROP CONSTRAINT IF EXISTS surse_rol_check;
ALTER TABLE surse ADD CONSTRAINT surse_rol_check
  CHECK (rol IN ('produs', 'hub', 'conditii', 'context', 'locator', 'campanie', 'comunicat'));

-- --------------------------------------------------------------------------
-- CAMPANII: o campanie pe rând, identificată de documentul ei principal
-- (`cheie`: pagina de campanie, sau regulamentul când n-are pagină).
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS campanii (
    id                  BIGSERIAL PRIMARY KEY,
    id_banca            BIGINT NOT NULL REFERENCES banci (id) ON DELETE CASCADE,
    cheie               TEXT NOT NULL,      -- URL-ul documentului principal, curățat
    url                 TEXT NOT NULL,      -- adresa de arătat în aplicație

    titlu               TEXT,
    titlu_din           TEXT CHECK (titlu_din IN ('pagina', 'eticheta_link', 'document', 'url', 'manual')),
    beneficiu           TEXT,
    beneficiu_citat     TEXT,
    segment             TEXT CHECK (segment IN ('PF', 'PJ')),   -- NULL = nemarcat
    categorie_produs    TEXT,               -- categoria din `extractoare.clasifica`

    -- NULL = nedecis din text (stare 'de_verificat')
    tip_oferta          TEXT CHECK (tip_oferta IN ('campanie', 'program', 'oferta_curenta')),
    -- 'banca' și fără `organizator_citat` = publicată de bancă pe site-ul propriu,
    -- fără alt organizator numit în text. 'grup' (filiale: BCR Social Finance),
    -- 'schema_card' (Mastercard, Visa) și 'partener' se păstrează, dar nu intră
    -- în comparație (vederea `campanii_curente`, coloana `in_comparatie`).
    organizator         TEXT NOT NULL DEFAULT 'banca'
                        CHECK (organizator IN ('banca', 'grup', 'schema_card', 'partener')),
    organizator_citat   TEXT,

    fereastra_start     DATE,
    fereastra_sfarsit   DATE,
    fereastra_citat     TEXT,               -- textul exact din care s-au citit datele
    -- 'perioada_initiala' = sfârșitul anunțat; 'act_aditional' = sfârșitul după
    -- ultimul act adițional, pus de om: o regulă deterministă strica 8 cazuri la
    -- BRD și 11 la BCR (Nicolae, §4.1), deci extractorul doar semnalează actul.
    sfarsit_din         TEXT CHECK (sfarsit_din IN ('perioada_initiala', 'act_aditional')),
    -- de unde vine fereastra: 62 din 74 dintr-un document, 11 (toate BCR) doar
    -- din textul linkului de pe hub (Nicolae, §4.1)
    sursa_ferestrei     TEXT CHECK (sursa_ferestrei IN ('document', 'eticheta_link', 'url')),
    -- adevărat când citatul nu se regăsește în textul documentului sau al
    -- linkului (ex. completat de om fără citat); extractorul determinist citează
    -- mereu din text, deci scrie fals
    citat_neverificat   BOOLEAN NOT NULL DEFAULT FALSE,
    act_aditional       BOOLEAN NOT NULL DEFAULT FALSE,
    metoda_extractie    TEXT NOT NULL CHECK (metoda_extractie IN ('determinist', 'manual')),

    -- starea la data rulării (`ultima_vedere`), calculată la încărcare din
    -- fereastră; o funcție de coloanele de mai sus, nu o părere
    stare               TEXT NOT NULL CHECK (stare IN ('activa', 'incheiata', 'de_verificat')),
    motiv_verificare    TEXT,
    provenienta         TEXT NOT NULL,      -- bronze | sitemap | hub | acasa | lista | regulamente
    prima_vedere        TIMESTAMPTZ NOT NULL DEFAULT now(),
    ultima_vedere       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (id_banca, cheie)
);

CREATE INDEX IF NOT EXISTS ix_campanii_banca ON campanii (id_banca, ultima_vedere DESC);

-- --------------------------------------------------------------------------
-- CAMPANII_SURSE: legătura N:M campanie ↔ document (pagina de campanie,
-- regulamentul, actul adițional, hub-ul din care s-a citit eticheta).
--
-- Amprenta documentului stă AICI, nu în `hashes`: `hashes` e citită de
-- `populare_initiala` (NESCHIMBAT, `--din-bronze`), iar o amprentă de campanie
-- acolo ar opri extracția de prețuri pe aceeași sursă sau ar trimite pagina la
-- parserul de tarife (condiția din §4.3). `url` se păstrează separat de
-- `id_sursa`: `populare_initiala --de-la-zero` șterge sursele web, iar
-- legătura trebuie să rămână (id_sursa devine NULL, nu se pierde rândul).
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS campanii_surse (
    id              BIGSERIAL PRIMARY KEY,
    id_campanie     BIGINT NOT NULL REFERENCES campanii (id) ON DELETE CASCADE,
    id_sursa        BIGINT REFERENCES surse (id) ON DELETE SET NULL,
    url             TEXT NOT NULL,
    rol_document    TEXT NOT NULL CHECK (rol_document IN ('landing', 'regulament', 'act_aditional', 'hub')),
    eticheta_link   TEXT,                   -- textul linkului de pe hub / pagină
    format          TEXT CHECK (format IN ('html', 'pdf')),
    amprenta        TEXT,                   -- sha256 pe octeți (PDF) sau pe text (HTML)
    fara_text       BOOLEAN NOT NULL DEFAULT FALSE,   -- PDF scanat, sub 50 de caractere
    cale_bronze     TEXT,
    observat_la     TIMESTAMPTZ,            -- când s-au adus octeții extrași
    prima_vedere    TIMESTAMPTZ NOT NULL DEFAULT now(),
    ultima_vedere   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (id_campanie, url)
);

CREATE INDEX IF NOT EXISTS ix_campanii_surse_sursa ON campanii_surse (id_sursa);

-- --------------------------------------------------------------------------
-- COMUNICATE: newsroom-ul băncii (titlu, dată, URL). `e_campanie` e doar
-- regex-ul pe titlu (fără LLM); cuvântul potrivit rămâne în
-- `e_campanie_potrivire`, ca un om să poată verifica capcanele știute
-- („premi" prindea „premieră", „castig" prindea „câștigătorii" — §4.3).
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS comunicate (
    id                    BIGSERIAL PRIMARY KEY,
    id_banca              BIGINT NOT NULL REFERENCES banci (id) ON DELETE CASCADE,
    id_sursa              BIGINT REFERENCES surse (id) ON DELETE SET NULL,
    url                   TEXT NOT NULL,
    titlu                 TEXT,
    titlu_din             TEXT CHECK (titlu_din IN ('pagina', 'lista', 'url')),
    data_publicarii       DATE,
    -- data se ia din URL, din listă sau din pagină, nu din `lastmod`: la BRD
    -- 20 de adrese cu lastmod 2025 erau știri vechi atinse din nou (§4.3)
    data_din              TEXT CHECK (data_din IN ('url', 'lista', 'pagina')),
    e_campanie            BOOLEAN NOT NULL DEFAULT FALSE,
    e_campanie_potrivire  TEXT,
    provenienta           TEXT NOT NULL CHECK (provenienta IN ('sitemap', 'lista', 'json')),
    amprenta              TEXT,             -- a corpului, dacă s-a adus (nu în `hashes`)
    cale_bronze           TEXT,
    prima_vedere          TIMESTAMPTZ NOT NULL DEFAULT now(),
    ultima_vedere         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (id_banca, url)
);

-- >>> campanii_curente (bloc identic în sincronizeaza_vederi.sql)
-- --------------------------------------------------------------------------
-- Campaniile din ultima fotografie a fiecărei bănci: cele văzute în ultima
-- rulare a colectorului pe banca respectivă (aceeași zi). O campanie care nu
-- mai apare rămâne în `campanii`, cu `ultima_vedere` veche: istoric, nu șters.
--   reper          Libra e banca noastră: se arată, marcată, ca reper
--                  (lista stă și în ingest/campanii_config.py, BANCI_REPER;
--                  testul ingest/test_campanii.py pică dacă diferă)
--   in_comparatie  doar campaniile organizate de bancă; filialele, schema de
--                  card și partenerii se păstrează, fără să intre în comparație
--   incheiata_azi  fereastra s-a terminat între timp (starea e la data rulării)
-- --------------------------------------------------------------------------
DROP VIEW IF EXISTS campanii_curente;
CREATE VIEW campanii_curente AS
  SELECT c.*, b.slug AS banca, b.nume AS nume_banca,
         b.slug IN ('libra') AS reper,                          -- BANCI_REPER
         c.organizator = 'banca' AS in_comparatie,
         coalesce(c.fereastra_sfarsit < current_date, FALSE) AS incheiata_azi
  FROM campanii c
  JOIN banci b ON b.id = c.id_banca
  WHERE c.ultima_vedere::date = (SELECT max(c2.ultima_vedere)::date
                                 FROM campanii c2 WHERE c2.id_banca = c.id_banca);
-- <<< campanii_curente

COMMIT;
