# Fluxul datelor și vederile care filtrează

- `observations` nu se șterge niciodată; ce nu se afișează e filtrat de vederea `observatii_curente` (definită în `db/sincronizeaza_vederi.sql`, refăcută de migrările 022, 023, 025). Exclude: `stare_data` ISTORIC/DUBLURA/VIITOR, valorile din campanii și regulamente (vederea `observatii_din_campanii`, după calea URL-ului), valorile Libra înlocuite de catalog (`observatii_inlocuite_de_catalog`).
- „De ce nu apare o valoare?” → verifică în ordine: `stare_data`, `ambiguu`/`motiv_ambiguu` (coada de verificare, `/api/coada`), `observatii_din_campanii`, `observatii_inlocuite_de_catalog`, `surse.status`.
- După o coloană nouă în `observations`: rulează `db/sincronizeaza_vederi.sql` (altfel `SELECT *` din vedere îngheață coloanele și API-ul dă 500).
- Încărcările sunt idempotente prin `provenienta` (campanii, android) sau prin metoda de extracție (`populare`): fiecare încărcare șterge doar ce a scris ea.
- Băncile blocate (WAF/robots) se documentează în `surse.nota_extractie` și au 0 cereri; lista: `BLOCATE` din `ingest/campanii_config.py` și jurnalul `loguri/origini_blocate.jsonl`.
- Prețurile Libra: produsele vin din catalogul intern (`catalog_libra`, `BANCI_CU_CATALOG` în `ingest/normalizeaza.py`), nu de pe web.
