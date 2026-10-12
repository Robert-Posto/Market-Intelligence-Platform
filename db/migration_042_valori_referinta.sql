-- Migrarea 042: `valori_referinta`, o singură valoare comparabilă pe bancă × produs Libra × câmp cheie.
--
-- DE CE: comparatie_libra păstrează tot ce extrage modelul (5.009 valori neambigue pe 12.10.2026),
-- iar pentru același câmp o bancă are adesea mai multe cifre: emitere normală și urgentă, card
-- principal și suplimentar, online și la ghișeu, aceeași cifră din trei documente. O celulă cu
-- „15 prețuri, 0–150 lei” nu răspunde la „cât costă la banca X”. Tabela de aici răspunde: pentru
-- fiecare câmp cheie din fișa produsului (extragere_produse_bancare/fise_produse.json), valoarea
-- variantei de referință, din sursa cea mai sigură, cu toate sursele ei și cu variantele grupate.
--
-- Cine scrie: extragere_produse_bancare/consolideaza_referinta.py, din comparatie_libra (sau din
-- copia fluxului vechi, comparatie_libra_v1). Totul e recalculabil: rularea înlocuiește rândurile
-- bazei ei. Serverul doar citește.
--
-- `baza`: 'curent' = din comparatie_libra (ce văd paginile); 'v1' = din comparatie_libra_v1, copia
-- fluxului vechi din 12.10.2026, pentru comparația vechi vs nou.
--
-- `stare`:
--   referinta      o singură valoare pe varianta de referință
--   aproximativ    câmp de scenariu (DAE, dobândă) doar pe un caz vecin al scenariului de referință
--   conflict       mai multe valori diferite pe varianta de referință, din surse la fel de sigure:
--                  se arată cea mai des găsită, iar `alternative` le are pe celelalte; de verificat
--   doar_variante  există valori, dar niciuna pe varianta de referință (ex. doar emitere urgentă)
--   lipsa          produsul există la bancă (discovery l-a găsit), dar câmpul nu are nicio valoare
--
-- Idempotentă: IF NOT EXISTS.

BEGIN;

CREATE TABLE IF NOT EXISTS valori_referinta (
    id              BIGSERIAL PRIMARY KEY,
    baza            TEXT NOT NULL DEFAULT 'curent' CHECK (baza IN ('curent', 'v1')),
    id_banca        BIGINT NOT NULL REFERENCES banci(id) ON DELETE CASCADE,
    id_produs_libra BIGINT NOT NULL REFERENCES produse_libra(id) ON DELETE CASCADE,
    -- cheia din fise_produse.json („emitere_card”, „dae”), nu câmpul brut
    camp_cheie      TEXT NOT NULL,
    stare           TEXT NOT NULL CHECK (stare IN ('referinta', 'aproximativ', 'conflict', 'doar_variante', 'lipsa')),
    valoare_num     NUMERIC,
    unitate         TEXT,
    moneda          TEXT,
    -- câmpul brut din comparatie_libra din care vine valoarea; `derivat` = recalculată (anual / 12)
    camp_sursa      TEXT,
    derivat         BOOLEAN NOT NULL DEFAULT FALSE,
    -- rândul din comparatie_libra ales (fără cheie străină: rândurile se rescriu la extragere)
    id_comparatie   BIGINT,
    -- toate sursele valorii alese, după contopirea dublurilor: [{id_sursa, url, rol, citat, link}]
    surse           JSONB NOT NULL DEFAULT '[]',
    -- celelalte variante găsite, grupate: [{eticheta, valoare_num, unitate, n}]
    variante        JSONB NOT NULL DEFAULT '[]',
    -- la `conflict`, celelalte valori de pe varianta de referință: [{valoare_num, unitate, n}]
    alternative     JSONB NOT NULL DEFAULT '[]',
    n_brut          INT NOT NULL DEFAULT 0,      -- câte rânduri brute avea câmpul
    n_unice         INT NOT NULL DEFAULT 0,      -- câte valori distincte, după contopire
    motiv           TEXT,                        -- de ce valoarea asta, în cuvinte
    generat_la      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (baza, id_banca, id_produs_libra, camp_cheie)
);

CREATE INDEX IF NOT EXISTS ix_valori_referinta_produs ON valori_referinta (baza, id_produs_libra);

COMMIT;
