-- Migrarea 028 (fluxul extragere_produse_bancare): banci.acces_restricted — banca refuză accesul automat.
--
-- TRUE când banca blochează accesul prin HTTP sau Playwright (403, WAF,
-- „Access denied"), cu UA-ul onest al echipei. Regula echipei: o bancă
-- blocată nu se accesează prin alt canal, deci discovery-ul și extracția o sar.
--
-- NU înseamnă blocaj: o rețea care nu rezolvă domeniul (Salt, DNS-ul
-- corporativ) sau un robots.txt care interzice doar anumite căi.
--
-- Implicit FALSE; se setează explicit, per bancă, cu dovada consemnată.
-- Idempotentă.

ALTER TABLE banci ADD COLUMN IF NOT EXISTS acces_restricted BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN banci.acces_restricted IS
  'TRUE = banca refuza accesul automat (HTTP/Playwright, UA onest). Nu se ocoleste; discovery si extractia o sar.';
