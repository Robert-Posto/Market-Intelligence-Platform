# Harta codului

- `crawler/`: crawler-ul Playwright și parserele (colegul Nicolae). `vocabular.py` = singurul loc al conceptelor canonice; `robots.py` = matcher RFC 9309; `__init__.py` = UA-ul (ecusonul), un singur loc.
- `ingest/`: colectarea și încărcarea.
  - `flux.py` (robots.txt pe disc, BLOCAT pe origine, coada pe origine, `curata_url`, `motiv_excludere`) și `transport.py` (`adu`: redirecturi pas cu pas, cascada http → Playwright): toate cererile spre bănci trec pe aici.
  - `descoperire.py` → `populare_initiala.py` (orchestrează) → `extractoare.py` → `versiuni.py` → `normalizeaza.py` (singurul drum brut → `observations`).
  - Campanii: `campanii.py`, `campanii_config.py`, `campanii_extractie.py`, `normalizeaza_campanii.py` (singurul drum spre `campanii`/`comunicate`).
  - Loadere separate: `load_mobil.py` (iOS), `load_android.py` (pachet Android, sha256 din MANIFEST), `load_bnr.py`, `load_catalog_libra.py` + `catalog_libra_valori.py`, `youtube_api.py`, `tiktok_api.py` (nerulat), `microsoft_ad_library.py`.
  - `google_play_app.mjs` (Node, `google-play-scraper`, doar pagina `/store/apps/details`): scrie `date/google_play*.json`, citite de 2.3 la build.
- `extragere_produse_bancare/`: fluxul separat al comparației cu Libra (tabele, joburi, cost, inventare JSON) → `mem:date/comparatie_libra`.
  - Teste: `ingest/test_*.py` (unittest, fără rețea).
- `app/server.py`: `interoghează(sql, params)` = singurul acces la bază; dicționarul `RUTE` mapează `/api/*` → funcții (o funcție pe zonă, ex. `android(q)`, `campanii()`); `Handler` servește fișierele statice, `/pdf` și build-ul React (`web/dist`) pe `/app/`, pe aceeași origine cu API-ul; `app/rulari.py` = rulările manuale (lista fixă `COMENZI`, active doar cu `MIP_PERMITE_RULARI=1`; pagina lor e „Rulare manuală”, nu Overview).
- `shared/src/<zonă>.ts`: schemele Zod ale răspunsurilor API, exportate din `shared/src/index.ts`.
- `web/src/`: `App.tsx` (rute, `HashRouter`), `pagini.ts` (meniul), `api/<zonă>.ts` (useQuery + `api(cale, Schema)` din `api/client.ts`), `pages/` (o pagină = un fișier; folder pentru paginile mari: `campanii/`, `rate_mobil/android/`, `versus/`, `harta/`, `banca/`, `document/`, `surse_coada/`, `logging/`), `components/` (`Tabel`, `Sertar`, `Dovezi`, `Banda`, `Paginare`, `BareStele`, `comune.tsx`), `i18n/` (`index.tsx`: `t`/`tn`/`<T>`; `server.ts`: `deLaServer`; `dict/*.ts`: perechi [română, engleză]).
- `db/`: `schema.sql` + `migration_NNN_*.sql` (002–038) + `sincronizeaza_vederi.sql`.
- `deploy/`: serverul de test `mcc-test.libra.bank` (nginx servește `web/dist`, `app/server.py` ca serviciu systemd); `deploy.sh` livrează HEAD de pe laptop; ce e pe server: `deploy/INSTALARE.md`.
- Date în fișiere, nu în bază: `output/reclame/` (Bing, Google), `output/youtube/` (șters la 30 de zile), `date/retele_sociale.csv`, `date/youtube_canale.csv`, `date/google_play*.json` (în afara git). Documentele brute: `bronze/` (în afara git).
