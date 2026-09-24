-- Migrarea 017: track-ul iOS de pe pagina publică App Store, nu din feed-ul RSS.
--
-- robots.txt al itunes.apple.com (verificat 24.09.2026) interzice feed-ul de
-- recenzii: `Disallow: /*/rss/*`. Cele 112 recenzii existente (BCR, ING,
-- Libra) au venit de acolo, deci se șterg — același tratament ca PDF-urile ING
-- descărcate în ciuda `Disallow: *.pdf` (903 observații șterse).
--
-- Pagina publică `apps.apple.com/ro/app/id…` e permisă și conține ce feed-ul
-- nu avea: distribuția notelor pe stele (5★…1★), plus recenziile afișate de
-- Apple (~8 pe aplicație, alese de ei, nu cele mai recente).

DELETE FROM app_review;

ALTER TABLE app_release ADD COLUMN IF NOT EXISTS distributie_stele INTEGER[];
COMMENT ON COLUMN app_release.distributie_stele IS
  'Numărul de note pe stele, în ordinea 5★, 4★, 3★, 2★, 1★ (pagina App Store).';

ALTER TABLE app_review ADD COLUMN IF NOT EXISTS raspuns_banca TEXT;
