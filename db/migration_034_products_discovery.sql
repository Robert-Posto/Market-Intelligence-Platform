-- Migrarea 034 (fluxul extragere_produse_bancare): products_discovery — produsele concurenței pe care Libra nu le
-- are în catalog.
--
-- Înlocuiește descopera_concurenta (030), creată pentru același lucru și rămasă
-- goală: un singur tabel pentru o singură întrebare.
--
-- Ce intră: un produs găsit pe site-ul unei bănci (descopera_produse.py) pentru
-- care clasificarea nu a găsit echivalent printre cele 57 de produse Libra. Cu
-- id_banca = Libra, rândul înseamnă „Libra îl are pe site, dar nu e în catalog”.
-- Produsele cu echivalent rămân doar în inventare-produse/produse-<banca>.json:
-- ele se compară deja în comparatie_libra.

BEGIN;

-- descopera_concurenta se scoate doar dacă e goală; altfel migrarea se oprește
DO $$
BEGIN
    IF to_regclass('public.descopera_concurenta') IS NOT NULL
       AND EXISTS (SELECT 1 FROM descopera_concurenta) THEN
        RAISE EXCEPTION 'descopera_concurenta are rânduri: mută-le întâi în products_discovery, nu se șterg';
    END IF;
END $$;
DROP TABLE IF EXISTS descopera_concurenta;

CREATE TABLE IF NOT EXISTS products_discovery (
    id                BIGSERIAL PRIMARY KEY,
    id_banca          BIGINT NOT NULL REFERENCES banci (id) ON DELETE CASCADE,
    denumire_produs   TEXT NOT NULL,           -- numele comercial de la bancă, ex. „Cont pentru copii”
    descriere_produs  TEXT,                    -- NULL când pagina n-are o descriere
    link              TEXT NOT NULL,           -- pagina produsului

    -- filtrele paginii și gruparea pe tipuri
    segment           TEXT CHECK (segment IN ('PF', 'PJ', 'PF+PJ')),
    categorie         TEXT,                    -- conturi, carduri, credite, depozite, investitii...

    -- created_at = prima rulare în care a apărut (eticheta „nou”);
    -- vazut_la   = ultima rulare în care exista (un produs retras nu se șterge)
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    vazut_la          TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- rularea lunară actualizează produsul, nu îl adaugă a doua oară
    CONSTRAINT ux_products_discovery UNIQUE (id_banca, link)
);

CREATE INDEX IF NOT EXISTS ix_products_discovery_banca     ON products_discovery (id_banca);
CREATE INDEX IF NOT EXISTS ix_products_discovery_categorie ON products_discovery (categorie);

COMMENT ON TABLE products_discovery IS
  'Produsele concurentei fara echivalent in catalogul Libra (produse_libra). Scrise de descopera_produse.py.';
COMMENT ON COLUMN products_discovery.vazut_la IS
  'Ultima rulare in care produsul era pe site; daca ramane in urma, banca l-a retras.';

COMMIT;
