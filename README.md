# Market Command Center

Monitorizare a concurenței bancare din România: colectăm date publice de la 30
de bănci și fintech-uri, le normalizăm într-un vocabular comun și le comparăm.

Doar date publice. Se respectă `robots.txt`, User-Agent onest, fără ocolirea
WAF-urilor sau a captcha. Autorii recenziilor se pseudonimizează la ingest
(hash cu sare) — Apple întoarce numele real, deci anonimizarea o facem noi.

> **Prototip funcțional, în construcție activă.** Cifrele de mai jos sunt o
> fotografie de la **23 septembrie 2026**, după terminarea extracției din
> PDF-uri pe toate băncile.

---

## Ce e în bază acum

| | |
|---|---|
| bănci | 30 |
| surse (URL-uri + documente) | 903 |
| observații (prețuri, dobânzi) | 19.104 |
| în coada de verificare umană | 1.491 |
| schimbări de preț detectate | 18 |

Patru variante de colectare, cu acoperiri diferite — de aceea rulează toate:

| proveniență | observații | ce acoperă |
|---|---|---|
| `pdf` | 11.894 | comisioane din PDF-uri de tarife (reprezintă 15.111 celule — duplicatele sunt strânse) |
| `playwright` | 6.518 | pachetul colegului, gata extras (JSON) |
| `bs4` | 511 | depozite, scraperul propriu |
| `bs4_llm` | 181 | BS4 peste URL-urile găsite de discovery-ul LLM |

Pe secțiunile din PDF-ul de arhitectură:

| secțiune | acoperire |
|---|---|
| 2.1 Produse & prețuri | 19 bănci din 30 |
| 2.2 Rate & indicatori | 23 bănci |
| 2.3 Aplicații mobile | **19 bănci**, 130 capturi |
| 2.4 Campanii & marketing | **0 — necolectat** |
| 2.5 Rețea & operațional | 66 locații, **toate mock** |
| 2.6 Context de piață | 140 valori ROBOR/ROBID reale |
| 2.7 Sentiment | 3 bănci, 112 recenzii — limitat de feed, nu de cod |

---


## Migrări

Se rulează în ordine, după `db/schema.sql`; după orice coloană nouă în
`observations`: `db/sincronizeaza_vederi.sql`.

| migrare | ce face |
|---|---|
| 002 | surse de tip `document` |
| 003 | coada de verificare umană (vedere) |
| 004 | locații fizice: sucursale și ATM-uri |
| 005 | recenzii per locație |
| 006 | contextul valorii (la ce se referă cifra) |
| 007 | proveniența `bs4_llm` |
| 008 | istoricul valorilor: data de vigoare și starea versiunii |
| 009 | pagina de pe care banca publică documentele de tarife |
| 010 | motivul pentru care o valoare e ambiguă |
| 011 | motive concrete în coada de verificare |
| 012 | deduplicare: câte celule identice stau în spatele unui rând |
| 013 | starea `VIITOR` (preț anunțat, încă neintrat în vigoare) |
| 014 | locații din Overture Maps în locul celor mock |
| 015 | varianta de produs (`coloana`) și rolul `locator` |
| 016 | rețeaua proprie vs. rețeaua parteneră (ATM-uri) |
| 017 | App Store din pagina publică; recenziile din RSS șterse |
| 018 | proveniența `populare` permisă în `observations` |
| 019 | campaniile (2.4): `campanii`, legătura N:M `campanii_surse` (cu amprenta documentului, nu în `hashes`), `comunicate` (newsroom), rolurile `campanie` / `comunicat` în `surse`, vederea `campanii_curente`; scrise de `ingest/campanii.py`, nimic în `observations` |
| 020 | `catalog_libra`: catalogul intern de produse Libra (referință, nu colectare); 019 e rezervată campaniilor |
| 021 | sursele Libra cu rol `produs` trec pe `pauza` (produsele vin din catalog) |
| 022 | catalogul Libra înlocuiește valorile web: `metoda_extractie = 'catalog'`, `format = 'xlsx'`; vederea `observatii_inlocuite_de_catalog` le ascunde (nu le șterge) din `observatii_curente` pe același `camp`/`unitate`/categorie și segment compatibil; valorile se scriu cu `ingest/catalog_libra_valori.py` |
| 023 | vederea `observatii_din_campanii`: valorile din pagini de campanii și din regulamente de campanie (după calea URL-ului) se ascund din `observatii_curente`, nu se șterg; excepțiile sunt în migrare, cu motiv |
| 024 | sursele cu nota `ROBOTS:` care figurau `activ` trec pe `blocat` (ING 48, Patria 16, BRD 1) |
| 025 | completează `observatii_din_campanii`: se ascund și programul de loialitate eMAG Raiffeisen (`program-loialitate`, 76 de valori) și paginile TBI `landing-pages/lcp-*` (finanțări la comercianți parteneri, 29); doar vederea, `CREATE OR REPLACE` |
| 026 | aplicații iOS: `app_release.descriere` (textul din magazin) și `vazut_ultima` pe `app_release`/`app_screenshot`; `load_mobil.py` face upsert în loc de `DELETE`, deci versiunile și capturile vechi rămân; starea de acum în vederile `app_release_curente` și `app_screenshot_curente` |
| 027 | aplicațiile Android ale băncilor (analiza statică a APK-urilor, pachetul lui Nicolae din 05.10.2026): tabelele `android_*` (aplicații, versiuni, permisiuni, trackere, biblioteci, funcționalități, portofele, profil tehnic, schimbări între versiuni, texte de ecran, note), cu `provenienta` pe fiecare rând; se încarcă cu `python ingest/load_android.py <folderul pachetului>` (verifică sha256 din MANIFEST.csv); capturile și reconstrucțiile din pachet nu se încarcă |
| 028 | `robid` permis în `indici_referinta.indice`: `load_bnr.py` scrie ROBID, dar CHECK-ul din `schema.sql` îl refuza (pe baza de colectare fusese lărgit de mână) |
| 029 | fluxul `extragere_produse_bancare` (comparația cu Libra): `produse_libra` (cele 57 de produse, axa comparației, separată de `catalog_libra`), `discovery_libra`, `comparatie_libra` |
| 030 | `banci.acces_restricted`: banca refuză accesul automat (403 / WAF), deci fluxul nu o accesează |
| 031 | discovery o dată, colectare zilnică: starea jobului pe `discovery_libra` (ultima verificare, status, cod HTTP) și `inventar_libra` pentru valori (scoasă de 032) |
| 032 | structura finală a comparației: `discovery_libra` → `surse_libra`, `comparatie_libra` refăcută (interval, scenariu, citat, link la paragraf), `descopera_concurenta` |
| 033 | `surse_libra.not_found`: produsul Libra nu există la bancă / nu e publicat |
| 034 | `hashes_libra`: amprenta fiecărei surse la ultima extracție (document neschimbat = fără apel la model) |
| 035 | `comparatie_libra.scenariu` (jsonb): codul de scenariu descompus (sumă, perioadă, valută, referință) |
| 036 | `products_discovery`: produsele concurenței fără echivalent în catalogul Libra; înlocuiește `descopera_concurenta` |
| 037 | jurnalul joburilor: `job_types` (tipurile; unul nou e un `INSERT`), `jobs` (durată, tokeni, cost estimat, `errors` ținut de trigger), `jobs_error` (eroarea în `TEXT`, legată prin `id_job`), vederea `v_jobs`; scrise de `extragere_produse_bancare/jurnal_joburi.py`, citite de pagina Logging (`/api/jobs`) |
| 038 | `jobs.runed_manually` (bool, implicit `FALSE`): jobul pornit din pagina „Rulare manuală”; `jurnal_joburi.py` îl scrie `TRUE` când procesul are `MIP_RULARE_MANUALA=1` (pusă de `app/rulari.py`); `v_jobs` primește coloana la coadă; pagina „Joburi și erori” o arată ca AUTOMAT / MANUAL |

## ⚠️ În lucru acum — scrieți înainte să prindeți ceva de aici

Ca să nu ne călcăm pe picioare.

| zonă | stare |
|---|---|
| `router.py --pas pdf` pe toate băncile | **terminat** — 96 PDF-uri, 15.111 comisioane |
| încărcarea aplicațiilor în 2.3 / 2.7 | **terminat** — 19 bănci |
| cascada de transport (Playwright) | **blocat: cere decizie de conformitate** |
| măsurare pentru 2.4 (campanii) | planificat, neînceput |

### Zonă înghețată deliberat

**Stratul autonom nu se atinge**: scheduler, rulări periodice. Prioritatea
curentă e doar popularea inițială — cât de multe date reale se pot aduna.
Automatizarea peste o acoperire proastă ar ascunde golurile.

**Excepția, intenționată (01.10.2026, decizia lui Robert):** butoanele
„Rulează” din Overview (din 06.10.2026 în pagina „Rulare manuală”, grupul Jobs),
până acum mockup înghețat, sunt deblocate ca **rulări manuale** — „doar ca să ai opțiunea să actualizezi manual” scripturile care
altfel ar rula automat. Nu e scheduler: nu pornește nimic singur. Funcționează
**doar pe laptopul lui Robert**, cu `MIP_PERMITE_RULARI=1` în `.env`; fără
variabila asta (pe serverul comun), secțiunea arată „Rulările manuale sunt
oprite pe acest server (MIP_PERMITE_RULARI)”, butoanele sunt dezactivate și
serverul refuză pornirea (403). Detalii la „Rulări manuale”, mai jos.

---

## Pornire

```bash
pip install -r requirements.txt      # Python 3.12
playwright install chromium          # doar pentru crawler/, nu vine prin pip

docker compose up -d                 # PostgreSQL 16
psql < db/schema.sql                 # apoi migrările 002..011, în ordine
psql < db/sincronizeaza_vederi.sql   # DUPĂ orice migrare care adaugă coloane

cp .env.example .env                 # completează cheile
python app/server.py                 # http://localhost:8765
```

`.env` nu e versionat. Cere `MIP_DSN`, `MIP_SALT` (obligatoriu — scripturile
refuză să ruleze fără el) și `ANTHROPIC_API_KEY` pentru discovery.

> `sincronizeaza_vederi.sql` nu e opțional. Vederea `observatii_curente` e
> definită cu `SELECT *`, iar Postgres îngheață lista de coloane la creare: o
> coloană adăugată ulterior nu apare, și API-ul cade cu 500 deși tabela o are.

### Autentificare (Active Directory)

Orice dată (`/api/*`, `/pdf`, `/logos`, paginile din `app/`) cere sesiune: logare cu contul de Windows, verificat la
AD prin LDAPS (`app/autentificare.py`). Rolul vine din grupurile AD, inclusiv imbricate: `MCC_LDAP_GRUP_ADMIN` →
admin, `MCC_LDAP_GRUP_ANALIST` → analist (în ambele → admin, în niciunul → 403). Doar adminul are „Rulare manuală”
și „Joburi și erori” (`/api/rulari*`, `/api/rulare_manuala*`, `/api/jobs`): 403 pentru analist, verificat pe server.

- **Pe laptop**: cât timp AD-ul nu e configurat (`MCC_LDAP_*` goale), intri automat ca admin, fără logare
  (`GET /api/sesiune` dă `local: true`). `MCC_AUTH_LOCAL=admin|analist` în `.env` alege rolul; cu AD configurat
  și fără ea, aplicația cere logare. Doar pentru cereri adresate lui `localhost` / `127.0.0.1` / `[::1]`. Nu are efect pe cererile venite prin nginx (`X-Real-IP`) și nici
  cu `MCC_AUTH_OBLIGATORIE=1`.
- **Pe server**: `MCC_LDAP_*` în `.env` (model în `.env.example`; ce se cere de la IT în `deploy/INSTALARE.md`),
  iar `mcc.service` pune `MCC_AUTH_OBLIGATORIE=1`.
- Rute: `POST /api/autentificare` `{utilizator, parola}`, `GET /api/sesiune`, `POST /api/delogare`. Cookie
  `mcc_sesiune` (`HttpOnly`, `SameSite=Strict`; pe HTTPS `__Host-mcc_sesiune`, cu `Secure`); expiră după
  `MCC_SESIUNE_ORE` (8) fără activitate și oricum după 12 h. 3 parole greșite pe utilizator (20 pe adresă) în
  30 de minute → 429, fără să mai întrebe AD-ul (configurabile: `MCC_AUTH_*` în `.env.example`). Sesiunile stau în
  memorie; jurnalul în `loguri/autentificare.log`, fără parole.
- Teste: `python app/test_autentificare.py` (inclusiv cu un DC fals pe loopback, prin LDAPS) și
  `python app/test_server_autentificare.py`.

### Colectare

```bash
python ingest/router.py --pas playwright    # citește pachetul colegului
python ingest/router.py --pas bs4           # depozite
python ingest/router.py --pas descoperite   # BS4 peste URL-urile LLM (rețea)
python ingest/router.py --pas pdf           # comisioane din PDF-uri (rețea)
```

Pași auxiliari, care pregătesc sursele:

```bash
python ingest/recolteaza_pdf_banci.py   # găsește PDF-urile de tarife pe site-uri
python ingest/cauta_app_id.py           # id-uri de App Store
python ingest/fetch_logos_site.py       # sigle, de pe site-ul fiecărei bănci
python ingest/extract_deposits.py       # depozite (BS4) -> date/rezultate_depozite.json, citit de --pas bs4
python ingest/itunes_lookup.py          # App Store -> date/rezultate_app_store.json, citit de load_appstore.py
```

Campaniile și comunicatele (2.4, după migrarea 019; configurația pe bancă e
în `ingest/campanii_config.py`):

```bash
python ingest/campanii.py --simulare [--newsroom]   # ce s-ar cere, fără nicio cerere
python ingest/campanii.py --doar-bronze             # doar documentele deja în Bronze, fără rețea
python ingest/campanii.py [--banca <slug>]          # cu rețea, prin transport.adu
python ingest/campanii.py --newsroom [--corp-luni 24]
```

Reclamele Bing (2.4, test până la avizul juridic), într-un fișier local din
`output/reclame/`, nu în bază:

```bash
python ingest/microsoft_ad_library.py [--banca <slug>]   # ~10 cereri/min, oprire la 429 repetat
```

Fiecare pas e **idempotent**: șterge doar ce a scris aceeași proveniență, apoi
rescrie. Rularea repetată nu dublează. `--banca <slug>` restrânge la o bancă.

### Rulări manuale (pagina „Rulare manuală”)

Pagina „Rulare manuală” (grupul Jobs, `#/rulare`; până pe 06.10.2026 secțiunea
pliată din Overview) pornește, la cerere, un script dintr-o **listă fixă**
(`app/rulari.py`, `COMENZI`). Activă doar cu `MIP_PERMITE_RULARI=1` în `.env`
(în `.env.example` e `0`); serverul trebuie repornit după ce schimbi variabila.

Se pornește **doar de pe aceeași origine cu serverul**: `npm run build`, apoi
`http://localhost:8765/app/#/rulare` (serverul servește `web/dist` pe `/app/`). Din Vite
(`localhost:5173`) pornirea e refuzată intenționat cu „Origin nepermis”; acolo pagina doar
arată estimarea și starea.

**„Începe job”** deschide un modal pentru cele trei joburi ale fluxului de
comparație cu Libra (`JOBURI`, id-ul = codul din `job_types`): tipul, banca (din
`extragere_produse_bancare/banci.json`, 30) și, la discovery și extragere, produsul
(un cod activ din `produse_libra`). Cu toate alese, `GET /api/rulare_manuala/estimare`
dă costul și durata din joburile încheiate (`v_jobs`): aceeași bancă și produs, apoi
același produs, apoi aceeași bancă, apoi orice job de același tip. **Aceste joburi cheamă
modelul, deci costă** (06.10.2026: discovery $0,04–0,53 pe produs, extragere $0–0,37);
pornirea e clicul explicit de după estimare. Fiecare proces pornit din pagină primește
`MIP_RULARE_MANUALA=1`, deci jobul apare în „Joburi și erori” ca MANUAL (migrarea 038).

| job | ce rulează | bancă | produs |
|---|---|---|---|
| Discovery surse | `extragere_produse_bancare/descopera_surse_libra.py --forteaza --banca X --produse P` | obligatoriu | obligatoriu |
| Extragere date | `extragere_produse_bancare/extrage_comparatie_libra.py --banca X --produse P` | obligatoriu | obligatoriu |
| Produse pe care Libra nu le are | `extragere_produse_bancare/descopera_produse.py --banca X` | obligatoriu | — |

Scripturile de colectare, sub buton:

| comandă | ce rulează | bancă | rețea | estimare inițială |
|---|---|---|---|---|
| Indicii BNR | `ingest/load_bnr.py` | — | da | 1 min |
| YouTube | `ingest/youtube_api.py --luni 12` | — | da | 2 min (01.10: 51 de cereri, 2 min) |
| Aplicații iOS | `ingest/load_mobil.py` | — | da | 2 min |
| Campanii de pe site-uri | `ingest/campanii.py` | opțional | da | 60 min toate (30.09: 61 min), 5 min pe bancă |
| Comunicate de presă | `ingest/campanii.py --newsroom` | opțional | da | 2 min toate (30.09: 1 min 14 s), 1 min pe bancă |
| Reclame Bing | `ingest/microsoft_ad_library.py` | — | da | 140 min (29.09: 706 cereri la ~11 s); băncile deja luate în aceeași zi se sar |
| Prețuri și dobânzi | `ingest/populare_initiala.py --llm-rezerva --banca X` | obligatoriu | da | 20 min pe bancă |
| Refacere din Bronze | `ingest/populare_initiala.py --din-bronze --llm-rezerva --banca X` | obligatoriu | nu | 10 min pe bancă |

- „Prețuri și dobânzi” fără `--din-bronze` e `ruleaza_banca`: șterge amprentele
  băncii, rulează din nou descoperirea, descarcă din nou fiecare sursă și
  înlocuiește valorile `populare` ale băncii. Ambele variante de prețuri rulează
  cu `MIP_LLM_DOAR_CACHE=1`: rezerva LLM folosește doar răspunsurile deja
  plătite, fără apeluri noi.
- Nu sunt în listă: TikTok (neaprobat), Google (exportul manual al colegului),
  `--de-la-zero`, `--paralel` sau orice pas care golește date, migrările.
- Un singur proces odată; al doilea primește „rulează deja …”. **Oprește**
  închide tot arborele de procese (`taskkill /T /F`).
- Ieșirea în `loguri/rulari/<id>_<AAAAMMZZ_HHMMSS>.log`; la final, un rând în
  `loguri/rulari/istoric.jsonl` (bancă, început, sfârșit, durată, cod de ieșire,
  ultimele rânduri). Estimarea afișată devine mediana rulărilor reușite din
  istoric, pe aceeași bancă dacă există.
- Securitate: rutele de pornire sunt doar `POST`, doar cu variabila, doar de pe
  loopback (`verify_request`), cu `Host` = `localhost`/`127.0.0.1`/`[::1]` și
  portul nostru, `Origin` (dacă e trimis) aceeași pagină, `Content-Type:
  application/json` și antetul `X-MIP-Token` (aleator, generat la pornirea
  serverului, primit de pagină prin `GET /api/rulari`). Din cerere ajung în
  linia de comandă doar id-ul comenzii (căutat în listă), slug-ul băncii
  (căutat în `ingest/banks.py` + tabela `banci`, la joburi în `banci.json` al
  fluxului) și, la joburi, codul produsului (căutat în `produse_libra`, un singur
  cod). Teste: `python app/test_rulari.py`.

### Vox (pagina `#/vox`)

O întrebare despre **o valoare** a unei bănci („Cât costă administrarea contului la BCR?”), în
română sau engleză. Modelul (`app/vox.py`) doar traduce întrebarea în banca, conceptul,
categoria și termenul căutat, cu schemă strictă; valorile, citatele și documentele vin din
`observatii_curente` prin `celula()`, ca Sertar-ul din 2.1. Modelul nu vede nicio valoare și nu
scrie nicio cifră; singurul lui text pe ecran e o întrebare înapoi, etichetată ca atare. Ce n-are
concept (găleata `comision`) se caută după text în denumirile și citatele băncii, cu cuvintele
tăiate la rădăcină („datoria vamală” găsește „datoriei vamale”), și apare marcat „căutare după
text”. Campaniile și recenziile nu intră: pagina răspunde că sunt în afara ei; aplicațiile au punctul lor, mai jos.

- Activă **doar local**: `MIP_PERMITE_VOX=1` și cheia reală `ANTHROPIC_API_KEY` în `.env`,
  apoi repornește serverul. Pe `mcc-test` rămâne oprită: logarea AD protejează rutele, dar
  istoricul conversațiilor e comun tuturor utilizatorilor, nu al fiecăruia, iar fiecare întrebare costă.
  Pe laptop, cu `MCC_AUTH_LOCAL=admin`, Vox merge fără logare, ca restul aplicației.
- Merge și din `npm run dev`: proxy-ul Vite rescrie Host-ul la server, dar Origin rămâne
  `localhost:5173`, deci ruta acceptă și acest Origin (rulările nu).
- Modelul: `claude-haiku-4-5` (`MIP_VOX_MODEL`). Măsurat pe 08.10.2026 (`mip_merge`):
  12.842 de tokeni de intrare pe întrebare (promptul cu 30 de bănci și 127 de concepte), $0,0016
  pe întrebare cu promptul în cache. Promptul stă în cache o oră de la ultima întrebare (`ttl: "1h"`,
  din 08.10.2026; înainte, 5 minute). Prima întrebare îl scrie (scrierea de o oră costă de 2 ori prețul
  de intrare): ≈ $0,027, dedus din evaluarea de mai jos ($0,0963 − 43 × ~$0,0016); apoi $0,0016 pe
  întrebare. În conversația de test din 08.10.2026 (18 întrebări, 7,5 cenți), cu cache-ul de 5 minute,
  promptul s-a scris de 3 ori, la prima întrebare și după două pauze, de 9 și de 5 minute: 4,9 cenți din
  cele 7,5. Cu cache-ul de o oră, aceeași conversație ar fi costat 5,5 cenți (calculat din jurnalul ei).
- Evaluarea interpretării (`python app/eval_vox.py --da`, 30 de întrebări reale): 30 din 30
  corecte pe 07.10.2026, $0,0576. Pe 06.10, „incoming payment” la BRD ieșea `transfer_credit` în loc
  de `incasare` în 2 rulări din 4, iar „APR” la Libra ieșea dobânda nominală (7,71–7,84%) în loc de
  DAE (8,09–8,37%); promptul spune acum ce înseamnă termenii englezești. Întrebările despre servicii
  fără concept („datoria vamală”, „TrezoNet” la BCR) cer `concept: null` și text de căutat; înainte
  de corecturi Haiku le marca „neclar”, cu o clarificare falsă („nu se găsește în tarife”). Cu 10
  întrebări de clasament și una despre aplicații (41 în total): 41 din 41 pe 07.10.2026, $0,0811, la
  `temperature: 0` (trimis
  prin `extra_body`, doar la Haiku 4.5: SDK-ul 1.x l-a scos din semnătură, iar Opus 4.7+ îl refuză). La
  temperatura implicită, patru rulări cu aceleași întrebări dăduseră 36, 36, 39 și 37, cu alte greșeli
  de fiecare dată. Pe 08.10.2026, „Cât costă administrarea contului la BCR și la BRD?”, pusă după o
  întrebare „pentru firme”, păstra segmentul PJ deși nu-l spunea: o întrebare care se înțelege singură
  e acum nouă, nu o continuare. Cu cazul ăsta, cu termenul la depozite și cu „și la BRD?” (care trebuie
  să păstreze PJ), 44 din 44, $0,0867 (cache de 5 minute). Cu cache-ul de o oră, tot 44 din 44 pe
  08.10.2026, $0,0963 în total ($0,0022 pe întrebare în medie, 12.842 de tokeni de intrare pe întrebare):
  cu $0,0096 mai mult, cât costă scrierea de o oră (de 2 ori prețul de intrare, nu de 1,25) pe cei
  ~12.800 de tokeni ai promptului. Fără `--da`, scriptul arată doar estimarea, ~$0,10.
- **Clasamente.** „Care bancă are cel mai mic comision de administrare?”, „Unde stă Libra la DAE pentru
  ipotecar?”: Vox ordonează băncile cu celulele din 2.1 (comisioane, în lei, PF dacă întrebarea nu spune
  altfel) și 2.2 (dobânzi, pe categorie), deci aceleași cifre ca paginile (`celule_matrice`,
  `celule_rate`). Implicit pe mediană; „cea mai ieftină variantă” ordonează pe cea mai bună valoare a
  fiecărei bănci. Egalitățile au loc comun (la administrarea contului PF, 7 din 14 bănci au mediana
  0 lei, `mip_merge`, 07.10.2026); Libra și băncile numite sunt evidențiate; cu termen sau tip de credit,
  un al doilea bloc arată valorile la care sursa nu le spune (pe 7–12 luni: 2 bănci cu termen, 9 fără);
  băncile fără date apar cu motivul. La valori egale, rândul de la mediană (serviciul afișat sub cifră)
  se alege după cheia observației, deci paginile și Vox arată același rând.
- **Fișa citește ce e în date** (08.10.2026). La dobânzi, câte un card pe monedă, din coloana `valuta`
  (fără ghicit din text; gol = „monedă nespusă”): Libra · depozit, fără termen (11 valori), are 4,75% în
  lei, 1,95% în euro și 9 valori fără monedă; „Vezi dovezile” de pe un card pe monedă deschide sertarul
  doar pe moneda lui (`/api/celula?valuta=eur`: 1 valoare, nu cele 11). La comisioanele cu mai multe
  frecvențe, intervalul se arată pe frecvență (BCR · administrare cont PF: pe lună 0–100 lei, pe an
  0–1.200, fără frecvență 0–100). Notele, limitele și cursurile stau separat, la „Alte valori găsite”
  (Garanti · schimbarea PIN-ului: doar limite contactless). Fiecare rând arată data intrării în vigoare,
  când sursa o are (69% din valori; la BCR · administrare cont, 467 din 570). Clasamentele de dobânzi
  păstrează cifrele din 2.2 și spun la ce bănci valorile includ și alte monede (depozit pe 12 luni:
  Raiffeisen, 2 din 2 valori în altă monedă decât lei).
- **Butoane fără model.** Sub răspuns: „Pentru firme” / „Pentru persoane fizice” (la comisioane) și
  „Compară cu Libra” (la căutare). Serverul aplică butonul pe interpretarea răspunsului (`vox.din_buton`),
  deci tura costă 0 și nu poate fi înțeleasă greșit; `POST /api/vox` cu `buton` + `anterior`.
- **Segmentul.** Rezumatul și tabelul se împart pe persoane fizice, PFA, IMM, firme și „fără segment
  în sursă”, PF primul: BCR · administrare cont avea 302 valori PJ, 234 PFA și 33 PF într-un singur
  interval, 0–1.200 lei (`mip_merge`, 07.10.2026). Segmentul vine din `cod_scenariu`; la dobânzi
  sursele nu-l spun, deci acolo nu apare. „Vezi dovezile” deschide sertarul exact pe grupă
  (`/api/celula?segment=pf&strict=1`); sertarul din 2.1 și Versus folosește regula lui 2.1 (segmentul
  plus rândurile nemarcate).
- **Termenul și tipul de credit** se citesc din textul băncii, deci pot goli un răspuns: la „depozit
  pe 12 luni” 28 din 30 de bănci n-aveau nicio valoare. Când răspunsul exact iese gol, Vox cade pe
  „termen nespecificat”, apoi și pe „credit nespecificat”, și spune ce filtru a căzut (Libra: 11
  dobânzi fără termen în sursă; băncile fără valori scad la 20). Dacă nici așa nu iese nimic, fișa
  spune câte valori sunt fără niciun filtru.
- **De ce lipsește o bancă.** Fișa goală spune câte surse ale băncii sunt interzise de `robots.txt`
  sau refuzate de site și câte sunt PDF-uri (ING: 48 de PDF-uri interzise din 158 de surse), ori că
  valoarea n-a apărut în sursele colectate; și că lipsa din bază nu înseamnă că banca n-are produsul.
- **Aplicațiile** (08.10.2026). „Ce bănci au RoPay?”, „Ce are BT Pay și n-are Libra?”, „Ce notă are aplicația
  Libra?”, „Care bancă are cea mai bună aplicație?”: tipul `aplicatii`. Funcțiile vin din analiza APK (24 de
  aplicații, 13 funcții, cu verdictul paginii Android: „sigur”, „probabil”, „absent”, „neconcludent”), notele din App
  Store (în bază, 19 aplicații, 24.09.2026) și din Google Play (`date/google_play.json`, 22 de aplicații, 06.10.2026;
  fără fișier, fișa spune „Google Play necolectat”). Diferențele dintre două aplicații sunt pe două niveluri: „sigur”
  față de „absent” e o diferență sigură, „probabil” față de „absent” una probabilă; „neconcludent” nu se compară
  (BT Pay vs Libra: RoPay sigură; chatul, marketingul și asistentul vocal probabile). Clasamentul notelor n-are prag:
  nota se compară rotunjită la o zecimală, cu loc comun (în Google Play, BCR, BRD, ING, Revolut și UniCredit au toate
  4,8). ProCredit e pe locul 1 în App Store cu 5,0 din 6 note, deci fișa spune asta și întreabă ce prag vrei, cu
  butoanele „Cel puțin 100 de note” (App Store: 12 aplicații clasate, 7 sub prag) și „Cel puțin 1.000 de note” (App
  Store: 8; Libra, cu 971, iese sub prag). Pragul se poate scrie și în întrebare. Cu funcțiile și numele aplicațiilor,
  promptul a crescut de la 12.842 la 13.901 tokeni de intrare pe întrebare (8,2%). Evaluarea din 09.10.2026, cu 53 de
  întrebări: 52 din 53, $0,1235. Singura greșeală, „Ce scriu clienții despre BT Pay?”, ieșea `aplicatii` cu nota în loc de
  `in_afara`; promptul spune acum că nota înseamnă doar stelele și numărul de note, iar ce scriu clienții e în afara lui
  Vox (nevalidat încă de o evaluare nouă).
- Lista băncilor și a conceptelor se citește din bază la prima întrebare. După o încărcare de date
  nouă, repornește serverul.
- Istoricul: fiecare conversație e un fișier pe laptop, `loguri/vox/conversatii/<id>.jsonl` (un rând
  pe întrebare, cu răspunsul ei; o redenumire e tot un rând). Coloana „Conversații” din pagină le
  redeschide fără model (gratuit), le caută în titlu și în întrebări (fără diacritice, cu cuvintele
  tăiate la rădăcină ca la căutarea după text), le redenumește și le șterge; cea deschisă stă în
  adresă (`#/vox?c=<id>`). Jurnalul de costuri rămâne separat, în `loguri/vox/AAAA-LL.jsonl`.
- Teste fără rețea: `python app/test_vox.py` și `python app/test_celula.py` (segmentul, moneda și data din
  `/api/celula`; nota de monedă din clasamente).

### Pachetul Playwright (`crawler/`)

`--pas playwright` și `load_bnr.py` citesc din `date/pachet/`, un instantaneu
versionat (rularea din 21 septembrie). Crawler-ul **nu** scrie acolo, ci în
`output/`, care nu e versionat. Rularea nouă e deci în doi timpi, deliberat: un
crawl stricat nu ajunge singur în bază.

```bash
# 1. crawl (~30 min): 6 procese PARALELE, fiecare într-un terminal propriu
mkdir -p output/log
python -m crawler.main --banci patria,salt,cetelem                       --pdf --max-pe-banca 80 > output/log/grup1.txt
python -m crawler.main --banci brd,libra,tbi,bnpparibas                  --pdf --max-pe-banca 80 > output/log/grup2.txt
python -m crawler.main --banci ing,vista,bcrlocuinte,revolut             --pdf --max-pe-banca 80 > output/log/grup3.txt
python -m crawler.main --banci bcr,raiffeisen,garanti,bid                --pdf --max-pe-banca 80 > output/log/grup4.txt
python -m crawler.main --banci eximbank,procredit,creditcoop,bankofchina --pdf --max-pe-banca 80 > output/log/grup5.txt
python -m crawler.main --banci nexent,techventures,brci,credex           --pdf --max-pe-banca 80 > output/log/grup6.txt

# 2. lanțul post-crawl (~2 min, 13 pași), din rădăcina repo-ului
python scripts/dupa_crawl.py

# 3. promovare: exact fișierele pe care le citește ingest/
cp output/{comisioane_unificate,rate_validate,date_documente,bnr_indici}.json date/pachet/
```

`dupa_crawl.py` așteaptă **toate șase** log-urile `output/log/grup1..6.txt`,
fiecare terminat cu „Rezultate in:". Cu mai puține grupuri, stă 75 de minute
și abia apoi pornește.

Gruparea e echilibrare de încărcare, nu ordine alfabetică: pauzele din
`robots.txt` sunt per origine, deci băncile diferite pot merge în paralel.
`grup1` are 3 bănci, nu 4, fiindcă Patria cere `Crawl-delay: 5`, singura din
lot peste 2s. La 18 sept grupurile au durat între 14 min (grup3) și 29 min
(grup6). Dacă rearanjezi băncile, echilibrează după pauză, nu după număr. Înainte de promovare, `git diff --stat date/pachet/`
arată cât s-a schimbat. Regula de filtrare pe `stare_data` e în
`docs/crawler/CITESTE_PENTRU_MERGE.md`.

### Înainte de commit

```bash
python app/verifica_pagini.py    # randează fiecare pagină într-un V8 real
```

Obligatoriu după orice modificare în `app/`. O eroare de JavaScript lasă pagina
complet albă, iar serverul răspunde vesel cu 200 — din terminal arată identic
cu „merge". S-a întâmplat de două ori, ambele din același motiv: un ghilimet
`"` ASCII pus în loc de `”` într-un text românesc, care închide șirul devreme
și doboară tot blocul `<script>`. Verificatorul localizează automat bucata.

### Interfața nouă (React, în lucru pe ramura `stack-scc`)

Trecerea la stack-ul Sales Command Center (02.10.2026): `web/` (React 18,
Vite 6, Ant Design 5) și `shared/` (schemele Zod ale API-ului). La 05.10.2026
sunt mutate toate cele 12 pagini, harta (`#/harta?banca=…`, MapLibre) și
vizualizatorul PDF (`#/document?u=…&p=…&q=…`, PDF.js); aplicația veche din
`app/` rămâne neatinsă. Datele vin tot de la `app/server.py`, prin proxy-ul Vite;
colectarea rămâne în Python.

```bash
npm install                 # Node 20+
python app/server.py        # API-ul, pe :8765
npm run dev                 # interfața nouă, pe http://localhost:5173
npm run typecheck && npm run build   # înainte de commit, după orice modificare în web/ sau shared/
```

Textele sunt în `web/src/i18n/dict/*.ts`, câte o pereche `[română, engleză]`
pe cheie (1.137 la 02.10.2026, plus cele adăugate la mutarea paginilor). Datele băncilor (servicii, citate, recenzii)
nu se traduc: sunt dovezi. Rulările manuale nu se pot porni din `npm run dev`:
serverul refuză cererile de pe alt port, iar verificarea nu se slăbește.

### Serena (opțional, pentru Claude Code)

Serena îi dă lui Claude navigare pe simboluri prin cod și o hartă comună a proiectului
(`.serena/memories/`). Configurarea e în repo (`.mcp.json`, `.claude/`), deci după `git pull` mai
trebuie doar instalat programul, o singură dată pe mașină:

```bash
winget install astral-sh.uv
uv tool install --python 3.11 git+https://github.com/oraios/serena@a8e30ff531a0092ece01c3a2bb9bb2833c7aa41a
uv tool update-shell        # pune ~/.local/bin în PATH; repornește VS Code după
```

Python 3.11, nu 3.14: Serena fixează `pyyaml` 6.0.2, care n-are pachet gata compilat pentru 3.14.
`uv` aduce singur 3.11, separat de Python-ul proiectului. La prima deschidere a proiectului,
Claude Code întreabă dacă aprobă serverul `serena` din `.mcp.json`: răspunde da. De acolo pornește
singur, iar după un commit care schimbă structura codului îți amintește să actualizezi memoriile
(`/actualizeaza-memoria`). Fără Serena instalată, proiectul merge normal, doar fără aceste unelte.

---

## Probleme cunoscute

Ordonate după cât dor.

### Date

**16 bănci n-au avut niciodată comisioane** fiindcă pipeline-ul nu citea
PDF-uri. Corelația măsurată era perfectă: comisioane în bază exact la băncile
care aveau un PDF adus de pachetul colegului, zero la restul. Rezolvat
structural (`din_pdf` + `vocabular.canonic`), iar 2.1 a crescut de la 13 la 19
bănci.

**11 bănci rămân la zero**, din trei cauze care cer soluții diferite:

| cauză | bănci | ce ar rezolva |
|---|---|---|
| au PDF-uri, dar descărcarea dă 403 | intesa, unicredit, cec, banca-transilvania | browser real — **decizie de conformitate în așteptare** |
| au pagini, dar niciun PDF de tarife găsit pe ele | patria (38 pagini), credex, cetelem, citibank, bid | recoltare mai bună sau tarife publicate doar în HTML |
| fără nicio sursă descoperită | banorient | lipsește discovery-ul, nu extracția |

Despre cele patru cu 403: **nu e o problemă de antete.** Verificat — refuză și
cu antete HTTP complete, deci e detectare reală de bot. Singura cale rămasă e
un browser real (Playwright), iar asta cere o decizie de conformitate: un
browser nu e o ocolire de WAF, dar e accesarea unui site care ne-a refuzat
explicit prin alt canal. Falsificarea User-Agent-ului **nu** e o opțiune — ar
fi evaziune de detecție, interzisă de regulile proiectului.

`bnpparibas` e un caz aparte: are 2 PDF-uri și a extras 1 singură valoare, în
procente — deci nu apare la comisioane.

**2.3 și 2.7 vin de pe pagina publică App Store, nu din feed-ul RSS.**
robots.txt al `itunes.apple.com` interzice feed-ul de recenzii
(`Disallow: /*/rss/*`, verificat 24.09.2026); cele 112 recenzii luate de acolo
au fost șterse. Pagina `apps.apple.com/ro/app/id…` e permisă și dă, pentru
toate cele 19 aplicații, versiunea, ratingul, **distribuția pe stele** și
recenziile afișate de Apple (~8 pe aplicație, alese de ei, nu neapărat cele
mai recente). Recenziile se acumulează între rulări (`ON CONFLICT DO NOTHING`),
nu se șterg. Doar magazinul românesc: în `us`, recenziile Citibank și Revolut
erau 0% în română. Istoricul complet al recenziilor unui concurent se poate
obține doar de la un furnizor licențiat.

**11 bănci fără id de aplicație confirmat.** Patru probabil n-au aplicație
(bcr-locuinte, bid, cec, creditcoop). Șapte au aplicația *grupului*, dar de pe
altă piață: BANOtouch e a mamei franceze, IKO e cea poloneză, iar `tbi`
potrivea „TBI Banking" publicat de **Trade Bank of Iraq**. Nu se scriu —
recenziile unor clienți francezi sau irakieni arată ca date bune și nu sunt.
Singura pe care aș paria că e corectă și totuși e respinsă: **techventures**,
doar fiindcă aplicația declară interfață numai în engleză. Cere confirmare
umană.

**5 bănci fără siglă**: intesa, revolut, techventures, citibank, banorient.
WAF sau timeout.

**2.5 e integral mock.** 66 de locații generate pentru hartă, în forma Google
Places. Nu sunt date reale și nu trebuie citite ca atare. Pe hartă se arată
doar nota, nu și texte de recenzii: o notă mock se citește ca cifră de
umplutură, un comentariu mock se citește ca părere reală de client.

### Calitate

**Rata de mapare la vocabularul canonic scade pe măsură ce adăugăm bănci.**
Pe ING singur ieșise 74,9%, peste cele 71,9% ale pachetului colegului. Pe toate
cele 21 de bănci împreună e **58,8%** — deci ~41% din comisioanele extrase
rămân în găleata generică `comision` și **nu apar în nicio comparație**.

Cel mai prost stau:

| bancă | valori | mapate |
|---|---|---|
| revolut | 64 | 7,8% |
| bcr | 4.068 | 45,7% |
| bankofchina | 72 | 51,4% |
| libra | 434 | 56,5% |
| brd | 733 | 56,8% |

BCR contează cel mai mult: 4.068 de valori la 45,7% înseamnă ~2.200 de
comisioane extrase corect dar invizibile. **Ăsta e cel mai valoros lucru de
lucrat la 2.1** — nu mai multă extracție, ci extinderea vocabularului canonic
peste denumirile pe care nu le acoperă.

Mai apar și rânduri de gunoi de la parserul de tarife nestandardizate
(„√ produsul / serviciul este"), necuantificate.

**1.529 de valori în coada de verificare.** Nu e o listă de bug-uri, e o
funcție a sistemului: un extractor care n-ar produce niciodată cazuri de
verificat ar însemna că nu verifică nimic. Două motive domină, amândouă
pierderi de *structură* la citirea tabelului, nu greșeli de citire a cifrei:
*antet de coloană pierdut* (nu se știe pentru care pachet e prețul) și
*prag de sumă pierdut* (avem 1, 3, 5, 15 lei fără să știm de la ce sumă).

**Doar ~51% din valori au link direct la documentul sursă.** Pachetul original
reține calea locală a PDF-ului, nu URL-ul de descărcare, iar PDF-urile nu sunt
incluse. Unde nu avem documentul exact, arătăm pagina de pe care banca îl
publică — marcată vizual diferit, fiindcă **nu e** documentul.

### Arhitectură

Față de arhitectura din artefactul de design, lipsesc:

- **Bronze** — octeții bruți nu se salvează nicăieri
- **sanitizare** înainte de extracție
- **hash-skip** — `hashes` are rânduri, dar nimic nu le citește înainte de
  procesare, deci se reprocesează tot de fiecare dată
- **cascada de transport** `http → playwright`
- **LLM ca ultimă treaptă** de extracție, pentru ce niciun parser determinist
  nu citește. Există o primă piesă, `ingest/structureaza_depozite.py` (doar
  depozite, cu Claude API), dar n-a fost rulată niciodată și nu e legată de
  pipeline
- **`surse_produse`** — 583 de perechi URL×produs în bază, zero referințe în cod
- **`change_events` e gol** — schimbările de preț sunt o *vedere*
  (`schimbari_pret`), nu evenimente. Se recalculează din observații, deci nu
  pot fi desincronizate, dar nu declanșează nimic.

Primele trei există doar pentru rerulări, deci sunt în afara priorității
curente (populare inițială).

### Conformitate — abatere asumată

Un `robots.txt` care răspunde cu eroare de server (5xx) sau nu răspunde deloc
e tratat ca **„fără restricții"**, în ambele implementări
(`ingest/scraper.py:robots_allowed`, `crawler/robots.py`). RFC 9309 §2.3.1.4
cere invers: totul interzis până se poate citi. Păstrat deliberat pe durata
testării. În datele existente n-a apărut niciun astfel de caz, doar 404 și
403, tratate corect.

### Conformitate — fluxul de comparație cu Libra, de reparat

`extragere_produse_bancare/` a intrat în `main` pe 06.10.2026 cu problemele de mai jos (decis:
merge acum, reparat după), măsurate pe inventarele din repo.

- `flow-html.py` trimite antetele unui browser (`Sec-Fetch-*`, `Upgrade-Insecure-Requests`) ca să
  treacă de WAF-uri și se prezintă cu un contact `example.org`, nu cu ecusonul din `crawler/__init__.py`.
- Cererile nu trec prin `ingest/flux.py`: fluxul a cerut adrese de la băncile din `BLOCATE` (BT 89,
  CEC 20, Intesa 18, UniCredit 14; regula e 0 cereri), iar extracția nu verifică `robots.txt`.
- În inventare: 128 de valori ING din 20 de PDF-uri interzise de `robots.txt` (`Disallow: *.pdf`) și
  25 de valori Banorient de pe `banorientfrance.com` (altă piață; `banorient.ro` interzice tot).
- Descoperirea surselor folosește `web_search` / `web_fetch` de la Anthropic (păstrat deliberat).

---

## Cum e construit

```
                    ┌─ citire pachet   (JSON gata extras)          ─┐
surse (tabelă) ──►  ├─ extractor HTML  (BS4 + parser_rate)          ─┼─► înregistrare
     ▲              ├─ extractor PDF   (parser_pdf / parser_tarife) ─┤     brută
     │              └─ extractor store (iTunes Lookup)               ─┘      │
     └── discovery LLM propune URL-uri                                       ▼
                                                                    normalizeaza.py
                                                                             │
                                                                             ▼
                                                                      observations
```

Două reguli care țin totul curat:

1. **Un extractor nu știe nimic despre baza de date.** Produce o înregistrare
   brută („am găsit 7,5 pe pagina asta, la serviciul ăsta") și atât.
2. **`normalizeaza.py` e singurul loc** care traduce brut → rând de bază:
   slug-ul băncii, conceptul canonic, unitatea, `cod_scenariu`, pragurile.
   Înainte existau trei copii ale acestor reguli, în trei loadere — de aceea
   196 de pagini găsite de discovery n-au fost extrase de nimeni: niciun
   script nu le avea în listă.

Detalii în [PIPELINE.md](PIPELINE.md).

### Praguri de plauzibilitate

Într-un singur loc, `normalizeaza.PRAGURI`. Fiecare are un motiv măsurat:

| prag | de ce |
|---|---|
| sumă > 10.000 lei | limitele de retragere și capitalul social ieșeau ca preț |
| depozite > 12% | TBI apărea cu „dobândă tipică 20%" dintr-o taxă |
| credite > 30% | mai sus sunt penalități |
| carduri > 40% | dobânda reală la cardul de credit ajunge la ~28% |

Ce depășește pragul **nu se aruncă**: se marchează ambiguu, se exclude din
comparații și apare în coadă, cu citatul din document.

---

## Structură

```
app/          server.py (API read-only) · rulari.py (rulările manuale) · vox.py (Vox) · index.html (SPA, 12 pagini)
              harta.html · pdf.html (vizualizator propriu) · verifica_pagini.py
ingest/       router.py · normalizeaza.py · extractoare.py + scripturi auxiliare
              scraper.py = stiva HTTP (robots.txt, User-Agent, pauze), folosită
              de pașii BS4 · extract_deposits.py · itunes_lookup.py · test_*.py
crawler/      crawler-ul Playwright + parserele PDF + vocabular.py (sursa unică)
              parser_rate.py = singurul parser de rate, folosit și de BS4
scripts/      lanțul post-crawl (dupa_crawl.py) + teste și verificări robots
db/           schema.sql + migrările 002..011 · sincronizeaza_vederi.sql
date/         ieșiri intermediare (JSON) · rezultate_*.json = datele BS4
              pachet/ = pachetul Playwright citit de ingest/
              robots/ = robots.txt brute, dovada de conformitate
docs/crawler/ jurnalele crawler-ului; operațional e doar CITESTE_PENTRU_MERGE.md
docs/bs4/     notele scraperului BS4 (fezabilitate, comparații)
```

Serverul e **strict read-only**: nicio rută nu scrie în bază (rulările manuale
pornesc scripturile, care scriu ele; serverul nu). Interogările
folosesc parametri (`%s`), nu interpolare de text.

PDF-urile se deschid într-un **vizualizator propriu** (`pdf.html`, PDF.js), nu
în cititorul sistemului. Motivul: parametrii de deschidere Adobe (`#page=`,
`search=`) sunt implementați de plugin-ul clasic, care nu mai există în Chrome;
extensia Adobe pierde fragmentul din URL, iar Chrome ignoră `search=`. Cu
vizualizator propriu, saltul la pagină și evidențierea citatului merg
indiferent ce are instalat cititorul.

Ruta `/pdf` are **listă albă din baza de date** — servește doar documente
înregistrate ca surse. Fără ea ar fi un proxy deschis către orice adresă,
inclusiv din rețeaua internă.
