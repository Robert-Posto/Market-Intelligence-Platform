-- Migrarea 033 (fluxul extragere_produse_bancare): comparatie_libra.scenariu — codul de scenariu descompus în câmpuri.
--
-- DE CE: extractorul pune pe valorile multiple ale aceluiași câmp un cod compus
-- de model (CASA_VERDE_350K_300L_PREMIUM_3ANI la Raiffeisen, IP_300K_240L_FIX3ANI
-- la BRD), fără format comun între bănci. Pe pagină apărea ca text brut sub
-- fiecare valoare, iar valorile nu se puteau alinia pe scenariu.
--
-- `scenariu` ține dimensiunile scoase determinist (mip/scenariu_libra.py):
--   {"cod", "suma", "suma_max", "moneda", "perioada_luni", "perioada_zile",
--    "fix_ani", "venit_min", "etichete": [...]}
-- iar interval_min / interval_max / unitate_interval primesc axa principală
-- (perioada, altfel suma). Ce nu se recunoaște rămâne în `etichete`.
--
-- Idempotentă.
ALTER TABLE comparatie_libra ADD COLUMN IF NOT EXISTS scenariu JSONB;
COMMENT ON COLUMN comparatie_libra.scenariu IS
  'Codul de scenariu al extractorului, descompus: suma, perioada, perioada fixa, venit minim, etichete.';
