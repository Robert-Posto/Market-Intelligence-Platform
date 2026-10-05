-- Migrarea 032 (fluxul extragere_produse_bancare): hashes_libra — amprenta fiecărei surse la ultima extracție.
--
-- DE CE: jobul de extracție descarcă zilnic fiecare URL din surse_libra. Dacă
-- documentul nu s-a schimbat de la rularea precedentă, nu are sens să plătim
-- din nou extracția cu model. Flow-urile (flow-html.py, flow-pdf.py) calculează
-- deja amprenta pe TEXTUL SANITIZAT — fără meniu, cookie-uri, ore — și se opresc
-- singure cu stare = neschimbat când primesc `hash_anterior` identic, înainte de
-- orice apel la model. Lipsea doar locul unde să ținem amprenta între rulări.
--
-- DE CE nu `hashes`: tabela există deja în MIP, legată de `surse` a lor.
--
-- Un rând per sursă (id_sursa): un produs are de obicei 2-4 surse, fiecare cu
-- documentul ei. id_banca și id_produs_libra sunt redundante cu surse_libra,
-- păstrate pentru interogări directe pe bancă × produs.
--
-- Idempotentă.

CREATE TABLE IF NOT EXISTS hashes_libra (
    id               BIGSERIAL PRIMARY KEY,
    id_banca         BIGINT NOT NULL REFERENCES banci (id) ON DELETE CASCADE,
    id_produs_libra  BIGINT NOT NULL REFERENCES produse_libra (id) ON DELETE CASCADE,
    id_sursa         BIGINT NOT NULL UNIQUE REFERENCES surse_libra (id) ON DELETE CASCADE,
    hash             TEXT NOT NULL,          -- sha256 pe textul sanitizat (HTML) sau pe textul PDF
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),   -- prima amprentă a sursei
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),   -- ultima dată când amprenta s-a schimbat
    verificat_la     TIMESTAMPTZ NOT NULL DEFAULT now()    -- ultima comparație, schimbată sau nu
);

CREATE INDEX IF NOT EXISTS ix_hashes_libra_pereche ON hashes_libra (id_banca, id_produs_libra);

COMMENT ON TABLE hashes_libra IS
  'Amprenta documentului fiecarei surse la ultima extractie. Identica -> extractia se opreste fara apel la model.';
