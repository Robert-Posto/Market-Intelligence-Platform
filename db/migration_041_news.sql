-- Migrarea 041: `news`, brief-urile despre piața bancară (sinteză, alerte, predicții, ...).
--
-- DE CE: un brief se generează de N ori pe zi din știrile colectate (RSS, comunicate BNR / ASF,
-- semnalele din MIP) și se afișează pe site. Conținutul e un singur document (jsonb), dar cu o
-- structură fixă, verificată de bază: pagina citește mereu aceleași chei, iar un brief generat
-- greșit (cheie lipsă, gravitate inventată, afirmație fără sursă) e refuzat la INSERT, nu afișat.
--
-- Structura lui `continut` (versiunea 1). Toate cheile sunt obligatorii; listele pot fi goale.
--   versiune      1
--   perioada      {de_la, pana_la}: intervalul știrilor acoperite (text ISO 8601)
--   generare      {model, nr_stiri, nr_subiecte}: cu ce s-a scris și din câte știri / subiecte
--   sinteza       text: „pe scurt”, ce contează din perioadă
--   alerte        [{titlu, gravitate, descriere, impact_libra, banci, surse}]
--                   gravitate: critica / ridicata / medie / scazuta
--   predictii     [{enunt, orizont, incredere, argument, surse}]
--                   orizont: text liber („2 săptămâni”, „T1 2027”); incredere: scazuta / medie / ridicata
--   trenduri      [{tema, directie, descriere, surse}]
--                   directie: crestere / scadere / stabil / nou
--   concurenta    [{banca, descriere, surse}]
--   oportunitati  [{titlu, tip, propunere, argument, surse}]
--                   tip: produs / marketing / pret / comunicare
--   surse         [{id, titlu, url, publicatie, publicat_la}]
-- `banci` / `banca` sunt slug-uri din `banci` (nu se verifică aici: o bancă neurmărită poate apărea
-- în știri). `surse` din fiecare element e o listă nevidă de id-uri din `continut.surse`: nicio
-- afirmație fără știrea din care vine.
--
-- Cine scrie: doar scriptul care generează brief-ul (serverul rămâne read-only).
--
-- Idempotentă: IF NOT EXISTS / CREATE OR REPLACE.

BEGIN;

-- Verifică structura și spune ce e greșit (un CHECK simplu ar spune doar „violates check constraint”).
CREATE OR REPLACE FUNCTION news_valideaza(c jsonb) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE
    sectiune text;
    camp     text;
    el       jsonb;
    i        int;
    ids      jsonb;
    -- câmpurile obligatorii ale fiecărui element, pe secțiune (pe lângă `surse`)
    campuri  jsonb := '{
        "alerte":       ["titlu", "gravitate", "descriere", "impact_libra", "banci"],
        "predictii":    ["enunt", "orizont", "incredere", "argument"],
        "trenduri":     ["tema", "directie", "descriere"],
        "concurenta":   ["banca", "descriere"],
        "oportunitati": ["titlu", "tip", "propunere", "argument"]
    }';
    -- valorile permise ale câmpurilor închise
    valori   jsonb := '{
        "gravitate": ["critica", "ridicata", "medie", "scazuta"],
        "incredere": ["scazuta", "medie", "ridicata"],
        "directie":  ["crestere", "scadere", "stabil", "nou"],
        "tip":       ["produs", "marketing", "pret", "comunicare"]
    }';
BEGIN
    IF jsonb_typeof(c) IS DISTINCT FROM 'object' THEN
        RAISE EXCEPTION 'news.continut: trebuie să fie un obiect';
    END IF;
    IF NOT c ?& ARRAY['versiune', 'perioada', 'generare', 'sinteza', 'alerte', 'predictii',
                      'trenduri', 'concurenta', 'oportunitati', 'surse'] THEN
        RAISE EXCEPTION 'news.continut: lipsesc cheile %', (
            SELECT string_agg(k, ', ') FROM unnest(ARRAY['versiune', 'perioada', 'generare', 'sinteza',
                'alerte', 'predictii', 'trenduri', 'concurenta', 'oportunitati', 'surse']) k
            WHERE NOT c ? k);
    END IF;
    IF c->'versiune' <> '1' THEN
        RAISE EXCEPTION 'news.continut.versiune: doar 1 e cunoscută, nu %', c->'versiune';
    END IF;
    IF jsonb_typeof(c->'perioada') <> 'object' OR NOT (c->'perioada') ?& ARRAY['de_la', 'pana_la'] THEN
        RAISE EXCEPTION 'news.continut.perioada: trebuie {de_la, pana_la}';
    END IF;
    IF jsonb_typeof(c->'generare') <> 'object'
       OR NOT (c->'generare') ?& ARRAY['model', 'nr_stiri', 'nr_subiecte'] THEN
        RAISE EXCEPTION 'news.continut.generare: trebuie {model, nr_stiri, nr_subiecte}';
    END IF;
    IF jsonb_typeof(c->'sinteza') <> 'string' OR btrim(c->>'sinteza') = '' THEN
        RAISE EXCEPTION 'news.continut.sinteza: text nevid';
    END IF;

    -- sursele: listă de {id, titlu, url, publicatie, publicat_la}, cu id-uri numerice unice
    IF jsonb_typeof(c->'surse') <> 'array' THEN
        RAISE EXCEPTION 'news.continut.surse: trebuie listă';
    END IF;
    FOR el IN SELECT * FROM jsonb_array_elements(c->'surse') LOOP
        IF jsonb_typeof(el) <> 'object' OR NOT el ?& ARRAY['id', 'titlu', 'url', 'publicatie', 'publicat_la']
           OR jsonb_typeof(el->'id') <> 'number' THEN
            RAISE EXCEPTION 'news.continut.surse: fiecare sursă e {id (număr), titlu, url, publicatie, publicat_la}, nu %', el;
        END IF;
    END LOOP;
    SELECT jsonb_agg(DISTINCT e->'id') INTO ids FROM jsonb_array_elements(c->'surse') e;
    IF coalesce(jsonb_array_length(ids), 0) <> jsonb_array_length(c->'surse') THEN
        RAISE EXCEPTION 'news.continut.surse: id-urile surselor trebuie să fie unice';
    END IF;

    -- secțiunile: liste de obiecte cu câmpurile lor, valori permise și surse care chiar există
    FOR sectiune IN SELECT jsonb_object_keys(campuri) LOOP
        IF jsonb_typeof(c->sectiune) <> 'array' THEN
            RAISE EXCEPTION 'news.continut.%: trebuie listă', sectiune;
        END IF;
        i := 0;
        FOR el IN SELECT * FROM jsonb_array_elements(c->sectiune) LOOP
            IF jsonb_typeof(el) <> 'object' THEN
                RAISE EXCEPTION 'news.continut.%[%]: trebuie obiect', sectiune, i;
            END IF;
            FOR camp IN SELECT jsonb_array_elements_text(campuri->sectiune) LOOP
                IF NOT el ? camp THEN
                    RAISE EXCEPTION 'news.continut.%[%]: lipsește „%”', sectiune, i, camp;
                END IF;
                IF valori ? camp AND NOT (valori->camp) ? (el->>camp) THEN
                    RAISE EXCEPTION 'news.continut.%[%].%: „%” nu e una din %', sectiune, i, camp, el->>camp, valori->camp;
                END IF;
            END LOOP;
            IF sectiune = 'alerte' AND jsonb_typeof(el->'banci') <> 'array' THEN
                RAISE EXCEPTION 'news.continut.alerte[%].banci: trebuie listă de slug-uri', i;
            END IF;
            IF jsonb_typeof(el->'surse') IS DISTINCT FROM 'array' OR jsonb_array_length(el->'surse') = 0 THEN
                RAISE EXCEPTION 'news.continut.%[%]: fără „surse” (cel puțin un id din continut.surse)', sectiune, i;
            END IF;
            IF EXISTS (SELECT 1 FROM jsonb_array_elements(el->'surse') s
                       WHERE NOT coalesce(ids, '[]') @> jsonb_build_array(s)) THEN
                RAISE EXCEPTION 'news.continut.%[%].surse: id-uri care nu sunt în continut.surse: %', sectiune, i, el->'surse';
            END IF;
            i := i + 1;
        END LOOP;
    END LOOP;
    RETURN true;
END $$;

CREATE TABLE IF NOT EXISTS news (
    id          BIGSERIAL PRIMARY KEY,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    continut    JSONB NOT NULL CONSTRAINT news_continut_structura CHECK (news_valideaza(continut))
);

-- pagina citește ultimul brief și istoricul, de la cel mai nou
CREATE INDEX IF NOT EXISTS ix_news_created_at ON news (created_at DESC);

-- jobul care scrie brief-ul (ingest/brief_stiri.py): `jobs.type` are cheie străină spre job_types
INSERT INTO job_types (cod, denumire, descriere, script, ordine) VALUES
    ('brief_stiri', 'Brief de știri',
     'Știrile din piața bancară (Google News, RSS, titlurile din paginile fără RSS), curățate și grupate pe subiecte, apoi brief-ul AI: sinteză, alerte, predicții, trenduri, concurență, oportunități. Scrie în news.',
     'ingest/brief_stiri.py', 50)
ON CONFLICT (cod) DO UPDATE SET
    denumire = EXCLUDED.denumire, descriere = EXCLUDED.descriere,
    script = EXCLUDED.script, ordine = EXCLUDED.ordine;

COMMIT;
