-- Migrarea 016: rețeaua proprie a băncii vs. rețeaua parteneră.
--
-- Locatorul Patria (`window.branchesList`, actualizat 11.06.2026) listează
-- 617 ATM-uri, dar sunt ATM-uri Euronet, unde clienții Patria retrag fără
-- comision — nu ATM-uri Patria. Numărate ca „ATM-uri proprii", umflau rețeaua
-- băncii de câteva ori. Se păstrează (informația e reală și utilă), dar marcate.

ALTER TABLE locatii ADD COLUMN IF NOT EXISTS retea TEXT NOT NULL DEFAULT 'proprie';
ALTER TABLE locatii DROP CONSTRAINT IF EXISTS locatii_retea_check;
ALTER TABLE locatii ADD CONSTRAINT locatii_retea_check CHECK (retea IN ('proprie', 'partener'));
