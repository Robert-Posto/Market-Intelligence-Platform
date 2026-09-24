-- Migrarea 014: locații reale din Overture Maps, în locul celor mock.
--
-- De ce Overture și nu Google Places: condițiile Google interzic păstrarea
-- coordonatelor peste 30 de zile și afișarea lor pe o hartă non-Google, iar
-- harta noastră e OpenStreetMap. De ce nu direct OpenStreetMap: robots.txt al
-- tuturor serverelor oficiale de descărcare interzice roboții (overpass-api.de
-- `Disallow: /api/`, Geofabrik `Disallow: *.osm.pbf`, planet.openstreetmap.org
-- permite doar `wget`), verificat pe 23.09.2026. Overture e publicat în
-- depozite publice S3/Azure, pentru acces programatic, cu licențe permisive
-- (CDLA Permissive 2.0, Apache 2.0, CC0).
--
-- `ref_extern` = id-ul Overture, ca un punct să poată fi urmărit între
-- versiuni. `furnizori` = seturile de date din spatele punctului (Meta,
-- Foursquare, AllThePlaces…), necesare pentru atribuire.

ALTER TABLE locatii DROP CONSTRAINT IF EXISTS locatii_sursa_check;
ALTER TABLE locatii ADD CONSTRAINT locatii_sursa_check
  CHECK (sursa IN ('mock', 'google_places', 'locator_banca', 'onrc', 'overture'));

ALTER TABLE locatii ADD COLUMN IF NOT EXISTS ref_extern TEXT;
ALTER TABLE locatii ADD COLUMN IF NOT EXISTS furnizori  TEXT;
