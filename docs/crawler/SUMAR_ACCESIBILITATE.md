# Sumar accesibilitate crawling — bănci din România

<!-- antet-vechime -->
> **Cifrele din documentul ăsta sunt cele de pe 16 septembrie 2026 și nu au fost
> actualizate.** Se păstrează ca jurnal de lucru: arată ce se știa atunci și
> cum s-a ajuns acolo. **Totalurile curente sunt în
> [CONSTATARI.md](CONSTATARI.md)**, iar regulile de filtrare pentru integrare
> în [CITESTE_PENTRU_MERGE.md](CITESTE_PENTRU_MERGE.md).

Testat: 2026-09-16 | Metodă: Playwright (Chromium headless, UA Chrome 128) + verificare robots.txt

## Verdict pe bancă

| Bancă | Playwright | robots.txt | Directive AI | Verdict |
|---|---|---|---|---|
| BCR | 200 OK | Allow: / | **Allow ClaudeBot + Claude-User** | ✅ Crawl OK (testat complet) |
| BRD | 200 OK | permisiv | **Allow agentic-AI: Claude-User** | ✅ Crawl OK |
| Raiffeisen | 200 OK | fără Disallow | — | ✅ Crawl OK |
| Exim Banca Românească | 200 OK | 404 (inexistent) | — | ✅ Crawl OK |
| Garanti BBVA | 200 OK | 309 Allow, 0 Disallow | — | ✅ Crawl OK |
| Libra Internet Bank | 200 OK | Allow: / | **Allow ClaudeBot** | ✅ Crawl OK (banca noastră) |
| Vista Bank | 200 OK | 404 | — | ✅ Crawl OK |
| ProCredit Bank | 200 OK | doar /wp-admin/ | — | ✅ Crawl OK |
| Salt Bank | 200 OK | 404 | — | ✅ Crawl OK |
| TechVentures Bank | 200 OK | doar /*?pentru=* | — | ✅ Crawl OK |
| BRCI | 200 OK | 404 | — | ✅ Crawl OK |
| BCR Banca pentru Locuințe | 200 OK | minor | — | ✅ Crawl OK |
| CREDITCOOP | 200 OK | minor | — | ✅ Crawl OK |
| BID | 200 OK | inexistent | — | ✅ Crawl OK |
| Revolut | 200 OK | standard | — | ✅ Crawl OK |
| tbi bank | 200 OK | standard (Yoast) | — | ✅ Crawl OK |
| **Nexent Bank** (ex-Credit Europe) | 200 OK | permisiv (/!res/, /!tpls/, /!sys/) | — | ✅ Crawl OK — date retail bogate |
| BNP Paribas SA Paris | 200 OK | permisiv | — | ⚠️ Accesibil, dar zero date retail (corporate) |
| BNP Paribas PF / Cetelem | 200 OK (doar prin browser) | `*` → Disallow gol | — | ⚠️ Accesibil, randament mic (fără DAE publicat) |
| Bank of China (CEE) | 200 OK | permisiv | — | ⚠️ Accesibil, zero date retail (corporate) |
| **Banque Banorient France** | 200 OK | ❌ **`User-agent: *` → `Disallow: /`** | — | ⛔ **Interzis explicit — exclus din crawl** |
| **PKO Bank Polski** | timeout TCP | inaccesibil | — | ❌ Inaccesibil public (verificat din 2 rețele) |
| Patria Bank | 200 OK | Crawl-delay: 5; `*` = Disallow (gol) | Disallow GPTBot, Google-Extended, CCBot | ✅ Crawl OK (testat; vezi nota) |
| ING | 200 OK | 403 (RFC 9309: 4xx = fără restricții) | necunoscut | ✅ Crawl OK (testat) |
| **Intesa Sanpaolo** | **403 Access Denied** (Akamai) | 403 | — | ❌ Blocat |
| **Banca Transilvania** | **403 Acces blocat** (WAF) | — | — | ❌ Blocat |
| **UniCredit** | **403 Request Failed** (WAF grup) | — | — | ❌ Blocat |
| **BNR** (site principal) | conexiune închisă | — | — | ❌ Blochează automatizarea browser |
| Credex (IFN) | 200 OK pe **credex.ro** | doar /wp-admin/ | — | ✅ Crawl OK (domeniu corect: credex.ro) |
| ~~credexbank.ro~~ | TLS renegociere în buclă | — | — | ❌ Domeniu nefuncțional global (nu e rețeaua noastră) |
| Citibank RO | eroare conexiune | — | — | ⚙️ Domeniu nefuncțional (Citi a ieșit din retail RO) |

## Concluzii

- **18 bănci accesibile** pentru crawling (inclusiv BCR, testat în profunzime).
- **4 blocate** de WAF: BT, UniCredit, Intesa Sanpaolo, BNR (doar site principal).
- Blocajele sunt politici individuale de bancă, **nu o problemă de metodă**.
- BCR, BRD și Libra **permit explicit** agenți AI în robots.txt.

## Excepții de tratat separat

- **Patria Bank**: blochează explicit crawlerele AI (GPTBot, Google-Extended, CCBot). ClaudeBot nu e numit,
  dar intenția e clară. Recomandare: exclus din crawl sau cerut acord direct.
- **ING**: robots.txt returnează 403, deci nu putem verifica ce permit. Recomandare: prudență.
- **BNR curs valutar**: `curs.bnr.ro/nbrfxrates.xml` funcționează perfect (feed oficial, inclusiv istoric pe ani).

## Date confirmate extractibile (test pe BCR)

- Curs valutar propriu: 6 tabele (EUR 5,1880 / 5,3390)
- Comisioane: 8 PDF-uri de pe `cdn.erstegroup.com` (Tarif standard PF — 284 KB, descărcat OK)
- Dobânzi + DAE: `george-credit` → 5,79%–14,99%, DAE 13,90%/16,41%
- Marjă peste IRCC: `casa-mea-bcr` → IRCC + 2,3%; `descoperit-de-cont` → IRCC + 7,99%
- Valoarea IRCC: publicată direct de BCR — 5,56% (valabil până la 30.09.2026)
