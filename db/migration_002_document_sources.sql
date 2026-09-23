-- Migrarea 002: surse de tip `document`.
--
-- De ce: pachetul Playwright livreaza comisioanele cu `sursa_pdf` = calea
-- relativa a documentului descarcat (ex. `bcr/75f21725_Tarif_standard...pdf`),
-- NU un URL. URL-ul de origine nu e inregistrat in JSON-urile primite, deci
-- nu putem inventa unul. Inregistram documentul ca sursa de tip `document`,
-- cu calea drept identificator - trasabil inapoi in pachet, si suficient ca
-- `observations` sa aiba cheie straina valida.
--
-- Consecinta asumata: o sursa `document` nu se poate re-descarca automat pana
-- cand cineva completeaza URL-ul. Se vede in rapoarte ca atare.

ALTER TABLE surse DROP CONSTRAINT IF EXISTS surse_tip_sursa_check;
ALTER TABLE surse ADD  CONSTRAINT surse_tip_sursa_check
    CHECK (tip_sursa IN ('url', 'document', 'aplicatie', 'reclama'));

-- format are sens si pentru documente; robots_ok rămâne doar pentru URL-uri
ALTER TABLE surse DROP CONSTRAINT IF EXISTS ck_surse_web_only;
ALTER TABLE surse ADD  CONSTRAINT ck_surse_web_only CHECK (
    tip_sursa IN ('url', 'document') OR (format IS NULL AND robots_ok IS NULL)
);
ALTER TABLE surse ADD  CONSTRAINT ck_surse_robots_url_only CHECK (
    tip_sursa = 'url' OR robots_ok IS NULL
);

-- frecventele produse de discovery, deja largite de seed_sources.sql;
-- repetate aici ca schema sa fie consistenta si la o instalare curata
ALTER TABLE surse DROP CONSTRAINT IF EXISTS surse_frecventa_check;
ALTER TABLE surse ADD  CONSTRAINT surse_frecventa_check
    CHECK (frecventa IN ('zilnic', 'saptamanal', 'lunar', 'manual',
                         'trimestrial', 'la_descoperire'));
