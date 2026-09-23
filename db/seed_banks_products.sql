-- =====================================================================
-- Populare initiala: banci si produse
-- Sursa: Downloads/flux-colectare/append.sql (2026-09-21), continut identic
--   banci    <- banks.py (30 intrari, cu fix-ul de URL pentru Salt Bank
--               deja aplicat in banks.py inainte de generarea acestui fisier)
--   tier     <- analiza-acces-per-banca.md, sectiunea Tier 1
--   produse  <- produse_bancare.json, cheia `categorii` (13 intrari)
--
-- Idempotent: ON CONFLICT DO NOTHING pe banci.slug si produse.nume.
-- =====================================================================

BEGIN;

INSERT INTO banci (slug, nume, tier, segment_real, activ) VALUES
    ('banca-transilvania', 'Banca Transilvania', 1, NULL, TRUE),
    ('bcr', 'BCR', 1, NULL, TRUE),
    ('cec', 'CEC Bank', 1, NULL, TRUE),
    ('ing', 'ING Bank (Sucursala București)', 1, NULL, TRUE),
    ('brd', 'BRD — Groupe Société Générale', 1, NULL, TRUE),
    ('raiffeisen', 'Raiffeisen Bank', 1, NULL, TRUE),
    ('unicredit', 'UniCredit Bank', 1, NULL, TRUE),
    ('intesa', 'Intesa Sanpaolo Bank România', 1, NULL, TRUE),
    ('vista', 'Vista Bank (Romania)', 1, NULL, TRUE),
    ('patria', 'Patria Bank', 1, NULL, TRUE),
    ('exim', 'Exim Banca Românească', 1, NULL, TRUE),
    ('libra', 'Libra Internet Bank', NULL, NULL, TRUE),  -- angajator, nu competitor
    ('procredit', 'ProCredit Bank', 1, NULL, TRUE),
    ('revolut', 'Revolut Bank UAB — Sucursala București', 1, NULL, TRUE),
    ('tbi', 'tbi bank EAD Sofia — Sucursala București', 1, NULL, TRUE),
    ('garanti', 'Garanti BBVA România', 1, NULL, TRUE),
    ('salt', 'Salt Bank', 1, NULL, TRUE),
    ('citibank', 'Citibank Europe plc — Sucursala România', NULL, NULL, TRUE),
    ('bnpparibas', 'BNP Paribas S.A. Paris — Sucursala București', NULL, NULL, TRUE),
    ('creditcoop', 'Banca Centrală Cooperatistă CREDITCOOP', 1, NULL, TRUE),
    ('bid', 'Banca de Investiții și Dezvoltare (BID)', NULL, NULL, TRUE),
    ('bankofchina', 'Bank of China (CEE) Ltd — Sucursala București', NULL, NULL, TRUE),
    ('credex', 'Credex Bank', NULL, NULL, TRUE),
    ('techventures', 'TechVentures Bank', 1, NULL, TRUE),
    ('brci', 'Banca Română de Credite și Investiții (BRCI)', NULL, NULL, TRUE),
    ('bcr-locuinte', 'BCR Banca pentru Locuințe', NULL, NULL, TRUE),
    ('nexent', 'Nexent Bank N.V. Amsterdam – Sucursala București', 1, NULL, TRUE),
    ('cetelem', 'BNP Paribas Personal Finance S.A. – Sucursala București / Cetelem', NULL, NULL, TRUE),
    ('banorient', 'Banque Banorient France S.A. – Sucursala România', NULL, NULL, TRUE),
    ('pko', 'PKO Bank Polski S.A. – Sucursala București', NULL, NULL, TRUE)
ON CONFLICT (slug) DO NOTHING;


INSERT INTO produse (nume, activ) VALUES
    ('comisioane', TRUE),
    ('cont-curent', TRUE),
    ('dobanda-nominala', TRUE),
    ('marja-ircc', TRUE),
    ('dae', TRUE),
    ('curs-valutar-propriu', TRUE),
    ('ipotecar-refinantare', TRUE),
    ('robor-euribor', TRUE),
    ('noua-casa', TRUE),
    ('card-de-credit', TRUE),
    ('factoring', TRUE),
    ('leasing', TRUE),
    ('cash-management', TRUE)
ON CONFLICT (nume) DO NOTHING;

COMMIT;
