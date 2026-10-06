-- Migrarea 037: jobs.runed_manually — jobul a fost pornit de mână din pagina „Rulare manuală”
-- (grupul Jobs), nu din terminal sau din altă automatizare.
--
-- Cine scrie: extragere_produse_bancare/jurnal_joburi.py, din variabila MIP_RULARE_MANUALA=1,
-- pe care app/rulari.py o pune doar procesului pornit din pagină. Joburile de dinainte rămân
-- FALSE (implicitul): nu se știe retroactiv cum au fost pornite.
-- Pagina „Joburi și erori” o arată ca AUTOMAT / MANUAL.
--
-- Numele coloanei e cel cerut în specificație (06.10.2026), chiar dacă nu e engleza corectă.
-- `v_jobs` primește coloana la coadă: CREATE OR REPLACE VIEW poate doar adăuga la sfârșit.
--
-- Idempotentă.

BEGIN;

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS runed_manually BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN jobs.runed_manually IS
  'TRUE = pornit din pagina Rulare manuala (MIP_RULARE_MANUALA=1); FALSE = terminal / automat';

CREATE OR REPLACE VIEW v_jobs AS
SELECT j.id,
       j.type,
       t.denumire AS tip,
       j.banca,
       j.started_at,
       j.ended_at,
       -- un job în curs își arată durata de până acum
       EXTRACT(EPOCH FROM (COALESCE(j.ended_at, now()) - j.started_at))::NUMERIC(12, 1) AS durata_s,
       CASE WHEN j.stare = 'in_curs' AND j.actualizat_la < now() - INTERVAL '1 hour'
            THEN 'abandonat' ELSE j.stare END AS stare,
       j.errors,
       j.model,
       j.apeluri,
       j.tokeni_intrare,
       j.tokeni_iesire,
       j.tokeni_cache_citire,
       j.tokeni_cache_scriere,
       j.cost_usd,
       j.cost_complet,
       j.parametri,
       j.rezumat,
       j.runed_manually
  FROM jobs j
  JOIN job_types t ON t.cod = j.type;

COMMIT;
