# Popularea inițială de la zero — plan de implementare

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Baza `mip` populată o singură dată, de la zero, numai cu scripturile din repo, pe flow-ul din `docs/arhitectura-flow.html` (figurile 2 și 3), cu îmbunătățirile măsurate.

**Architecture:** Trei benzi legate prin tabele, nu prin apeluri: (A) descoperirea scrie doar în `surse`/`surse_produse`; (B) extracția citește `surse`, aduce octeții (requests; Playwright doar pentru pagini JS; STOP la blocaj), sanitizează, compară amprenta, scrie Bronze doar la schimbare, extrage determinist, LLM doar ca rezervă verificată, validează, normalizează și scrie în `observations`; (C) locatoarele băncilor scriu în `locatii`. Punctul de intrare rămâne `ingest/populare_initiala.py`.

**Tech Stack:** Python 3.12+, PostgreSQL 16 (Docker `mip-db`), psycopg2, requests, BeautifulSoup/lxml, Playwright (Chromium), pdfplumber (prin parserele din `crawler/`), anthropic SDK, DuckDB (doar pentru Overture).

**Spec:** `docs/superpowers/specs/2026-09-23-populare-initiala-design.md`

## Global Constraints

- Doar date publice. `robots.txt` verificat pe fiecare origine, inclusiv CDN-uri și **după redirect**.
- User-Agent unic: `crawler.UA` din `crawler/__init__.py`, pe requests și pe Playwright. Nu se imită un browser.
- La 401/403/407/429/451 sau la o pagină „Access denied" servită cu 200: **STOP**. Sursa devine `status='blocat'`, cu dovada în `nota_extractie`. Nu se încearcă alt canal.
- `web_fetch`/`web_search` NU se folosesc pe băncile blocate (CEC, BT, UniCredit, Intesa).
- Nu se folosesc date colectate anterior: `date/pachet/*`, `date/rezultate_*.json`, Bronze vechi, inventarul actual din `surse`. `date/pachet/etalon_manual.json` se folosește DOAR ca etalon de măsurare.
- Claude nu extrage date manual; totul trece prin scripturi.
- Nu se atinge stratul autonom (scheduler, rulări periodice, butoanele `disabled` din Overview).
- Migrare nouă = `db/migration_NNN_<nume>.sql`, următorul număr (ultimul existent: 014). După orice coloană nouă în `observations`: `docker exec -i mip-db psql -U mip -d mip < db/sincronizeaza_vederi.sql`.
- Orice pachet nou în `requirements.txt`, în același commit.
- Identificatori în română, fără diacritice; texte pentru utilizator și documentație cu diacritice. Comentariile spun **de ce**, cu cifra măsurată.
- Scripturile care afișează diacritice: `sys.stdout.reconfigure(encoding="utf-8")`.
- Commit-uri în română, „zonă: ce și de ce", fără `Co-Authored-By`. **Fără push** (doar Robert decide).
- Rulează totul din rădăcina repo-ului `C:\Users\robert.postolache\Downloads\mip`.
- Testele: fișiere `ingest/test_*.py` cu `unittest`, rulate cu `python -m unittest ingest.test_<nume> -v`. Testele existente trebuie să rămână verzi: `python -m unittest discover -s ingest -p "test_*.py"` și `python scripts/test_validare.py`.

**Abatere asumată față de spec:** punctul 6 (dobânzi pe toate coloanele unui rând) se **măsoară** în Task 13, dar nu se implementează aici: `crawler/parser_rate.py` are deja `_coloane_suplimentare`, iar re-scorarea arată o pierdere la Vista #38. Întâi cifra, apoi decizia; rezultatul intră în `docs/IMBUNATATIRI.md`.

**A doua abatere:** punctul 10 (un singur parser robots) se aplică pe fluxul de populare: `flux`, `transport` și `descoperire` folosesc doar `crawler/robots.py`. `ingest/robots_matcher.py` rămâne doar pentru scripturile BS4 vechi (`scraper.py`, `extract_deposits.py`), care nu fac parte din popularea inițială; înlocuirea lui acolo e o sarcină separată, trecută în `docs/IMBUNATATIRI.md`.

---

## Structura fișierelor

| fișier | responsabilitate | nou/modificat |
|---|---|---|
| `ingest/transport.py` | aduce octeții unei adrese și clasifică răspunsul (OK / JS / BLOCAT / DISPARUT / REINCEARCA); Playwright doar pentru JS; robots după redirect; pauze per origine | nou |
| `ingest/sanitizare.py` | textul sanitizat al unei pagini + amprenta de conținut | nou |
| `ingest/flux.py` | robots (`permite`, `reguli_pentru`), Bronze (`scrie_bronze`, `cale_bronze`); **fără** cascadă și fără `adu_llm` | modificat |
| `ingest/populare_initiala.py` | punctul de intrare: `--de-la-zero`, descoperire, extracție, validare, scriere | modificat |
| `ingest/extractoare.py` | `din_pdf` (coloană, segment, categorie), `din_html` (import reparat, linii-problemă, `_rec`), `din_locator` | modificat |
| `ingest/normalizeaza.py` | coloana `coloana`, cheia de deduplicare, `SUSPECT`, `scrie(..., banci=)` | modificat |
| `ingest/validare.py` | leagă `crawler/validator.py` de înregistrările brute de dobânzi | nou |
| `ingest/llm_rezerva.py` | LLM ca rezervă de extracție, cu verificare literală | nou |
| `ingest/descoperire.py` | banda A1: sitemap ∪ navigare, clasificare, scriere în `surse` | nou |
| `ingest/descoperire_llm.py` | banda A2: `claudeCrawl.py` adaptat, doar pentru goluri, cost logat | nou (din `flux-colectare/claudeCrawl.py`) |
| `crawler/robots.py` | grupul care numește UA-ul nostru | modificat |
| `crawler/vocabular.py` | trei concepte lipsă | modificat |
| `app/server.py` | robots.txt pe proxy-ul `/pdf` | modificat |
| `ingest/load_locatii_overture.py` | tiparul Cetelem | modificat |
| `scripts/rescore_etalon.py` | re-scorarea dobânzilor pe etalon | nou |
| `db/migration_015_coloana_locator.sql` | `observations.coloana`, `surse.rol='locator'` | nou |
| `docs/IMBUNATATIRI.md` | fiecare îmbunătățire, cu cifre înainte/după | nou |

---

### Task 1: Reparații care blochează rularea

`din_html` importă `parser_rate` de pe o cale care nu mai există după merge (`ModuleNotFoundError` la prima pagină HTML). `scrie()` șterge toate observațiile metodei, deci `--banca cec` ar șterge celelalte 29 de bănci.

**Files:**
- Modify: `ingest/extractoare.py` (funcția `din_html`, ~linia 487)
- Modify: `ingest/normalizeaza.py` (funcția `scrie`, pasul 3)
- Test: `ingest/test_reparatii.py`

**Interfaces:**
- Produces: `normalizeaza.scrie(randuri, metoda, raport=None, sterge=True, banci=None)` — cu `banci` (listă de slug-uri) șterge doar observațiile acelor bănci.

- [ ] **Step 1: Write the failing test**

```python
# ingest/test_reparatii.py
import os
import sys
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]


class TestReparatii(unittest.TestCase):
    def test_din_html_importa_parserul_din_crawler(self):
        import extractoare
        html = ("<html><head><title>Depozite la termen</title></head><body>"
                "<h1>Depozit clasic</h1><table><tr><td>12 luni</td><td>5,50%</td>"
                "</tr></table></body></html>").encode("utf-8")
        brute, nota = extractoare.din_html(html, "https://exemplu.ro/depozite-la-termen",
                                           "libra")
        self.assertTrue(any(b.get("valoare") == 5.5 for b in brute), nota)

    def test_scrie_accepta_banci(self):
        import inspect
        import normalizeaza
        self.assertIn("banci", inspect.signature(normalizeaza.scrie).parameters)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest ingest.test_reparatii -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'parser_rate'` și `'banci' not found`.

- [ ] **Step 3: Implement**

În `ingest/extractoare.py`, în `din_html`, înlocuiește:

```python
    from parser_rate import parseaza_linie

    html = octeti.decode("utf-8", errors="replace")
    soup = BeautifulSoup(html, "lxml")
```

cu:

```python
    from crawler.parser_rate import parseaza_linie

    # Octeți, nu text: BeautifulSoup citește charset-ul din <meta>. Decodarea
    # forțată în UTF-8 strica diacriticele paginilor servite în windows-1250.
    soup = BeautifulSoup(octeti, "lxml")
```

În `ingest/normalizeaza.py`, semnătura și pasul 3 din `scrie`:

```python
def scrie(randuri, metoda, raport=None, sterge=True, banci=None):
```

```python
            # --- 3. idempotență pe proveniență (sărită la scriere incrementală)
            # Cu `banci`, doar băncile rulate: `--banca cec` ștergea altfel
            # observațiile tuturor celorlalte bănci.
            if sterge and banci:
                cur.execute(
                    """DELETE FROM observations o USING surse s, banci b
                       WHERE o.id_sursa = s.id AND b.id = s.id_banca
                         AND o.metoda_extractie = %s AND b.slug = ANY(%s)""",
                    (metoda, list(banci)))
                raport["observatii_sterse"] += cur.rowcount
            elif sterge:
                cur.execute("DELETE FROM observations WHERE metoda_extractie = %s",
                            (metoda,))
                raport["observatii_sterse"] += cur.rowcount
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest ingest.test_reparatii -v`
Expected: PASS (2 teste).

- [ ] **Step 5: Commit**

```bash
git add ingest/extractoare.py ingest/normalizeaza.py ingest/test_reparatii.py
git commit -m "ingest: din_html importa parser_rate din crawler, --banca sterge doar banca ei"
```

---

### Task 2: Transportul — clasificarea răspunsului și aducerea octeților

Regula echipei: o bancă blocată se documentează ca blocată. Cascada veche trecea la Playwright cu UA de Chrome și apoi la LLM după un 403.

**Files:**
- Create: `ingest/transport.py`
- Test: `ingest/test_transport.py`

**Interfaces:**
- Consumes: `crawler.UA`; `flux.permite(url, banca_id) -> bool`, `flux.intarziere(url, banca_id) -> float` (Task 3).
- Produces:
  - `clasifica_raspuns(status: int|None, tip_continut: str, corp: bytes) -> str` — una din `"OK" | "JS" | "BLOCAT" | "DISPARUT" | "REINCEARCA" | "REDIRECT_SERIALIZAT"`.
  - `adu(url: str, banca_id: str, stare: dict) -> Rezultat` unde `Rezultat` e `namedtuple("Rezultat", "verdict octeti url_final transport nota")`.

- [ ] **Step 1: Write the failing test**

```python
# ingest/test_transport.py
import os
import sys
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import transport as T


class TestClasificare(unittest.TestCase):
    def test_coduri_de_blocaj(self):
        for cod in (401, 403, 407, 429, 451):
            self.assertEqual(T.clasifica_raspuns(cod, "text/html", b"x"), "BLOCAT")

    def test_blocaj_servit_cu_200(self):
        corp = b"<html><title>Access Denied</title>Reference #18.2f</html>"
        self.assertEqual(T.clasifica_raspuns(200, "text/html", corp), "BLOCAT")

    def test_503_cu_pagina_de_blocaj(self):
        self.assertEqual(T.clasifica_raspuns(503, "text/html", b"Just a moment..."), "BLOCAT")

    def test_503_simplu_se_reincearca(self):
        self.assertEqual(T.clasifica_raspuns(503, "text/html", b"maintenance"), "REINCEARCA")

    def test_disparut(self):
        self.assertEqual(T.clasifica_raspuns(404, "text/html", b""), "DISPARUT")

    def test_pdf(self):
        self.assertEqual(T.clasifica_raspuns(200, "application/pdf", b"%PDF-1.7 ..."), "OK")

    def test_pagina_js_goala(self):
        corp = b'<html><body><div id="root"></div>' + b"<script></script>" * 3 + b"</body></html>"
        self.assertEqual(T.clasifica_raspuns(200, "text/html", corp), "JS")

    def test_pagina_normala(self):
        corp = ("<html><body><main>" + "Depozit la termen 12 luni 5,5% " * 40
                + "</main></body></html>").encode()
        self.assertEqual(T.clasifica_raspuns(200, "text/html", corp), "OK")

    def test_redirect_serializat_in_corp(self):
        # Patria servea un 302 serializat în corpul unui răspuns 200
        corp = b"HTTP/1.0 302 Found\r\nLocation: https://www.patriabank.ro/x\r\n\r\n<!DOCTYPE html>"
        self.assertEqual(T.clasifica_raspuns(200, "text/html", corp), "REDIRECT_SERIALIZAT")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest ingest.test_transport -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'transport'`.

- [ ] **Step 3: Implement `ingest/transport.py`**

```python
"""Aducerea octeților unei surse, cu o singură regulă de escaladare.

De ce există: cascada veche (http → playwright → llm) trecea mai departe la
ORICE eșec, inclusiv la 403. Așa au „răspuns" BT, Intesa și UniCredit pe 23.09:
le-am ocolit filtrul, ceea ce regula echipei interzice explicit („o bancă
blocată se documentează ca blocată"). Acum:

    BLOCAT          401/403/407/429/451, sau pagină „Access denied" → STOP
    DISPARUT        404/410
    REINCEARCA      5xx/timeout → o reîncercare cu pauză, fără escaladare
    JS              200, dar pagina e un schelet randat în browser → Playwright
    REDIRECT_SERIALIZAT  corpul începe cu „HTTP/" (Patria) → se urmează Location
    OK              restul

Playwright folosește `crawler.UA`, nu un UA de Chrome.
"""

import collections
import re
import time
from urllib.parse import urlparse

from crawler import UA

import flux

Rezultat = collections.namedtuple("Rezultat", "verdict octeti url_final transport nota")

RE_BLOCAJ = re.compile(
    rb"access denied|acces blocat|request (was )?rejected|support id|incapsula|"
    rb"cf-chl|just a moment|attention required|captcha|/TSPD/|reference #\d",
    re.I)
RE_SCHELET_JS = re.compile(rb'id="(root|app|__next)"|enable javascript', re.I)
RE_TAGURI = re.compile(rb"<[^>]+>")
# Sub atâtea caractere de text vizibil, o pagină de produs e un schelet: o
# pagină reală de depozite are mii de caractere.
TEXT_MINIM = 400
ANTETE = {"User-Agent": UA, "Accept-Language": "ro,en;q=0.8"}


def _text_vizibil(corp):
    fara_script = re.sub(rb"<script.*?</script>|<style.*?</style>", b"", corp, flags=re.S | re.I)
    return RE_TAGURI.sub(b" ", fara_script).strip()


def clasifica_raspuns(status, tip_continut, corp):
    corp = corp or b""
    if status in (401, 403, 407, 429, 451):
        return "BLOCAT"
    if status == 503 and RE_BLOCAJ.search(corp[:5000]):
        return "BLOCAT"
    if status in (404, 410):
        return "DISPARUT"
    if status is None or status >= 500:
        return "REINCEARCA"
    if corp.startswith(b"HTTP/"):
        return "REDIRECT_SERIALIZAT"
    if corp.startswith(b"%PDF"):
        return "OK"
    if RE_BLOCAJ.search(corp[:5000]):
        return "BLOCAT"
    if "html" in (tip_continut or "") and len(_text_vizibil(corp)) < TEXT_MINIM and (
            RE_SCHELET_JS.search(corp) or corp.count(b"<script") > 15):
        return "JS"
    return "OK"


def _asteapta(url, banca_id, stare):
    """Crawl-delay per origine. Patria cere 5 s; bucla veche dormea 1,5 s fix."""
    o = urlparse(url).netloc
    pauza = max(flux.intarziere(url, banca_id), 1.5)
    ultima = stare.setdefault("ultima_cerere", {}).get(o, 0)
    rest = ultima + pauza - time.monotonic()
    if rest > 0:
        time.sleep(rest)
    stare["ultima_cerere"][o] = time.monotonic()


def _http(url):
    import requests
    try:
        r = requests.get(url, headers=ANTETE, timeout=45)
    except requests.RequestException as exc:
        return None, "", b"", url, type(exc).__name__
    return r.status_code, r.headers.get("Content-Type", ""), r.content, r.url, f"HTTP {r.status_code}"


def _playwright(url, stare):
    if "browser" not in stare:
        from playwright.sync_api import sync_playwright
        stare["pw"] = sync_playwright().start()
        stare["browser"] = stare["pw"].chromium.launch(headless=True)
        stare["ctx"] = stare["browser"].new_context(user_agent=UA, locale="ro-RO")
    pg = stare["ctx"].new_page()
    try:
        r = pg.goto(url, wait_until="domcontentloaded", timeout=45000)
        status = r.status if r else None
        # statusul se citește ÎNAINTE de așteptare: după, pagina poate fi alta
        pg.wait_for_timeout(1800)
        return status, "text/html", pg.content().encode("utf-8"), pg.url, f"HTTP {status}, randat"
    except Exception as exc:
        return None, "", b"", url, type(exc).__name__
    finally:
        pg.close()


def inchide(stare):
    if "browser" in stare:
        stare["browser"].close()
        stare["pw"].stop()


def adu(url, banca_id, stare, _adancime=0):
    if not flux.permite(url, banca_id):
        return Rezultat("ROBOTS", None, url, None, "interzis de robots.txt")
    _asteapta(url, banca_id, stare)
    status, tip, corp, final, nota = _http(url)
    verdict = clasifica_raspuns(status, tip, corp)
    transport = "http"

    if verdict == "REINCEARCA":
        time.sleep(10)
        status, tip, corp, final, nota = _http(url)
        verdict = clasifica_raspuns(status, tip, corp)
    if verdict == "JS" and not url.lower().split("?")[0].endswith(".pdf"):
        _asteapta(url, banca_id, stare)
        status, tip, corp, final, nota = _playwright(url, stare)
        verdict, transport = clasifica_raspuns(status, tip, corp), "playwright"
        if verdict == "JS":          # tot schelet și în browser: nimic de citit
            verdict = "OK"
    if verdict == "REDIRECT_SERIALIZAT" and _adancime < 2:
        m = re.search(rb"^Location:\s*(\S+)", corp, re.M | re.I)
        if m:
            return adu(m.group(1).decode("latin-1"), banca_id, stare, _adancime + 1)
        verdict = "REINCEARCA"
    # Robots se verifică și pe adresa FINALĂ: un redirect poate duce pe altă
    # origine, cu alte reguli.
    if verdict == "OK" and final != url and not flux.permite(final, banca_id):
        return Rezultat("ROBOTS", None, final, transport, "redirect spre adresă interzisă")
    return Rezultat(verdict, corp if verdict == "OK" else None, final, transport, nota)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest ingest.test_transport -v`
Expected: PASS (9 teste). (`flux.intarziere` nu e apelat de teste; Task 3 îl adaugă.)

- [ ] **Step 5: Commit**

```bash
git add ingest/transport.py ingest/test_transport.py
git commit -m "ingest: transport cu stop la blocaj, Playwright doar pentru JS, robots dupa redirect"
```

---

### Task 3: Robots — un singur parser, cu grupul UA-ului nostru

`crawler/robots.py` aplică doar grupul `*`. `robots_matcher.py` greșește pe fișiere reale (la BCR permite `/search`, se potrivește pe subșir). Rămâne `crawler/robots.py`, extins.

**Files:**
- Modify: `crawler/robots.py` (`__init__`, `_parseaza`)
- Modify: `ingest/flux.py` (`permite`, nou `intarziere`, `reguli_pentru`)
- Test: `ingest/test_robots_crawler.py`

**Interfaces:**
- Produces: `RegulliRobots(banca_id, base_url, delay_implicit=2, ua_token="LibraBank-MarketIntel-Test")`; `flux.reguli_pentru(url, banca_id) -> RegulliRobots`; `flux.intarziere(url, banca_id) -> float`.

- [ ] **Step 1: Write the failing test**

```python
# ingest/test_robots_crawler.py
import os
import sys
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

from crawler.robots import RegulliRobots


def reguli(text):
    r = RegulliRobots("test", "https://exemplu.ro")
    r._parseaza(text)
    return r


class TestRobots(unittest.TestCase):
    def test_wildcard_pdf(self):
        r = reguli("User-agent: *\nDisallow: *.pdf\n")
        self.assertFalse(r.permite("https://exemplu.ro/docs/tarife.pdf"))
        self.assertTrue(r.permite("https://exemplu.ro/docs/tarife"))

    def test_grupuri_stea_repetate_se_unesc(self):
        r = reguli("User-agent: *\nDisallow: /a\n\nUser-agent: Googlebot\nDisallow: /\n\n"
                   "User-agent: *\nDisallow: /search\n")
        self.assertFalse(r.permite("https://exemplu.ro/search?q=x"))
        self.assertTrue(r.permite("https://exemplu.ro/credite"))

    def test_query_conteaza(self):
        r = reguli("User-agent: *\nDisallow: /?s=\n")
        self.assertFalse(r.permite("https://exemplu.ro/?s=card"))

    def test_grupul_care_ne_numeste_bate_steaua(self):
        r = reguli("User-agent: *\nDisallow: /\n\nUser-agent: LibraBank-MarketIntel-Test\n"
                   "Allow: /\n")
        self.assertTrue(r.permite("https://exemplu.ro/credite"))

    def test_grup_test_nu_ne_prinde_pe_subsir(self):
        # „Test" nu e UA-ul nostru, deși UA-ul nostru conține „-Test/"
        r = reguli("User-agent: Test\nDisallow: /\n\nUser-agent: *\nCrawl-delay: 5\n")
        self.assertTrue(r.permite("https://exemplu.ro/credite"))
        self.assertEqual(r.delay, 5)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest ingest.test_robots_crawler -v`
Expected: FAIL la `test_grupul_care_ne_numeste_bate_steaua`.

- [ ] **Step 3: Implement**

În `crawler/robots.py`, `__init__` primește `ua_token="LibraBank-MarketIntel-Test"` și păstrează reguli separate:

```python
    def __init__(self, banca_id, base_url, delay_implicit=2,
                 ua_token="LibraBank-MarketIntel-Test"):
        ...
        self.ua_token = ua_token.lower()
        self.reguli_proprii = []    # grupul care ne numește explicit
        self._grup_propriu = False
```

În `_parseaza`, la `user-agent` se reține și dacă grupul ne numește, prin potrivire EXACTĂ pe token (RFC 9309: produsul, fără versiune), iar la `allow`/`disallow`/`crawl-delay` regula merge în lista grupului curent:

```python
            if cheie == "user-agent":
                if not in_grup_stea:
                    grup_curent_are_stea = False
                    self._grup_propriu = False
                grup_curent_are_stea = grup_curent_are_stea or valoare == "*"
                self._grup_propriu = self._grup_propriu or valoare.lower() == self.ua_token
                in_grup_stea = True
                self._grup_stea = grup_curent_are_stea
                continue
            ...
            in_grup_stea = False
            if not (self._grup_stea or self._grup_propriu):
                continue
            destinatie = self.reguli_proprii if self._grup_propriu else self.reguli
            if cheie in ("disallow", "allow"):
                if valoare == "":
                    continue
                destinatie.append((len(valoare), cheie == "allow", _compileaza(valoare)))
            elif cheie == "crawl-delay":
                try:
                    self.delay = max(self.delay, float(valoare))
                except ValueError:
                    pass
```

În `permite`, grupul propriu, dacă există, înlocuiește grupul `*` (RFC 9309, 2.2.1):

```python
        reguli = self.reguli_proprii or self.reguli
        cel_mai_lung, permite = -1, True
        for lungime, este_allow, regex in reguli:
```

În `ingest/flux.py`, `permite` păstrează textul și statusul ca dovadă și se adaugă:

```python
def reguli_pentru(url, banca_id):
    from urllib.parse import urlparse
    o = urlparse(url)
    origine = f"{o.scheme}://{o.netloc}"
    if origine not in _CACHE_ROBOTS:
        import requests
        from crawler import UA
        from crawler.robots import RegulliRobots
        reguli = RegulliRobots(banca_id, origine)
        try:
            r = requests.get(origine + "/robots.txt", headers={"User-Agent": UA}, timeout=15)
            reguli.status = f"HTTP {r.status_code}"
            reguli.text_brut = r.text if r.ok else ""
            # RFC 9309: 4xx = fără restricții; 5xx/timeout = abatere asumată
            # a echipei, tratat ca permis (README, „Conformitate").
            reguli._parseaza(reguli.text_brut)
        except Exception as exc:
            reguli.status = f"inaccesibil ({type(exc).__name__})"
            reguli._parseaza("")
        _CACHE_ROBOTS[origine] = reguli
    return _CACHE_ROBOTS[origine]


def permite(url, banca_id):
    return reguli_pentru(url, banca_id).permite(url)


def intarziere(url, banca_id):
    return reguli_pentru(url, banca_id).delay
```

- [ ] **Step 4: Run tests**

Run: `python -m unittest ingest.test_robots_crawler -v` → PASS (5).
Run: `python scripts/test_validare.py` → `0 eșuate`.

- [ ] **Step 5: Commit**

```bash
git add crawler/robots.py ingest/flux.py ingest/test_robots_crawler.py
git commit -m "crawler: robots aplica grupul care ne numeste, flux pastreaza dovada si Crawl-delay"
```

---

### Task 4: Sanitizare și amprentă pe conținut

Figura 3: amprenta se calculează pe textul sanitizat, nu pe octeți — un token de sesiune sau un banner schimbă octeții fără să schimbe prețurile. Pentru PDF rămân octeții.

**Files:**
- Create: `ingest/sanitizare.py`
- Test: `ingest/test_sanitizare.py`

**Interfaces:**
- Consumes: `ingest/fetch_deposit_pages.clean_main_text` (logica, portată aici).
- Produces: `text_sanitizat(octeti: bytes) -> str`; `amprenta_continut(octeti: bytes) -> str` (16 hex).

- [ ] **Step 1: Write the failing test**

```python
# ingest/test_sanitizare.py
import os
import sys
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import sanitizare as S


class TestSanitizare(unittest.TestCase):
    def test_meniul_si_ora_nu_schimba_amprenta(self):
        a = b"<html><nav>Meniu A</nav><main>Depozit 5,5% valabil 01.04-30.06</main>" \
            b"<footer>generat 10:31:07</footer></html>"
        b = b"<html><nav>Meniu B</nav><main>Depozit 5,5% valabil 01.04-30.06</main>" \
            b"<footer>generat 11:02:44</footer></html>"
        self.assertEqual(S.amprenta_continut(a), S.amprenta_continut(b))

    def test_pretul_schimba_amprenta(self):
        a = b"<main>Depozit 5,5%</main>"
        b = b"<main>Depozit 5,75%</main>"
        self.assertNotEqual(S.amprenta_continut(a), S.amprenta_continut(b))

    def test_perioada_de_valabilitate_se_pastreaza(self):
        self.assertIn("01.04.2026", S.text_sanitizat(b"<main>valabil din 01.04.2026</main>"))

    def test_pdf_pe_octeti(self):
        self.assertNotEqual(S.amprenta_continut(b"%PDF-1.7 a"), S.amprenta_continut(b"%PDF-1.7 b"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run** `python -m unittest ingest.test_sanitizare -v` → FAIL (`No module named 'sanitizare'`).

- [ ] **Step 3: Implement `ingest/sanitizare.py`**

```python
"""Textul unei pagini fără meniu, footer și cod — ce se compară între rulări.

Tag-urile eliminate sunt cele din `fetch_deposit_pages.clean_main_text`, care
merge deja pe 22 de bănci. NU se elimină div-urile cu „cookie" în nume: la
Nexent, `cookie-block-new` conținea toată pagina.

Datele de tip zz.ll.aaaa RĂMÂN: „valabil 01.04–30.06" la IRCC e o schimbare
reală. Se elimină doar orele și marcajele ISO, care se schimbă la fiecare cerere.
"""

import hashlib
import re

from bs4 import BeautifulSoup

ZGOMOT = ["script", "style", "noscript", "nav", "header", "footer", "svg",
          "iframe", "form", "button"]
RE_ORA = re.compile(r"\b\d{1,2}:\d{2}(:\d{2})?\b")
RE_ISO = re.compile(r"\b\d{4}-\d{2}-\d{2}T[\d:.+Z-]+")


def text_sanitizat(octeti):
    soup = BeautifulSoup(octeti, "lxml")
    for tag in soup.find_all(ZGOMOT):
        tag.decompose()
    radacina = (soup.find("main") or soup.find(attrs={"role": "main"})
                or soup.find("article") or soup.body or soup)
    text = radacina.get_text(separator=" ", strip=True)
    text = RE_ISO.sub(" ", RE_ORA.sub(" ", text))
    return re.sub(r"\s+", " ", text).strip()


def amprenta_continut(octeti):
    date = octeti if octeti.startswith(b"%PDF") else text_sanitizat(octeti).encode("utf-8")
    return hashlib.sha256(date).hexdigest()[:16]
```

- [ ] **Step 4: Run** `python -m unittest ingest.test_sanitizare -v` → PASS (4).

- [ ] **Step 5: Commit**

```bash
git add ingest/sanitizare.py ingest/test_sanitizare.py
git commit -m "ingest: amprenta pe textul sanitizat, ca in figura 3"
```

---

### Task 5: Coloana, segmentul și categoria până în bază

Măsurat pe eșantion: `parser_tarife` citește `coloana` (varianta de card) la 1.100 din 5.578 de rânduri, dar `din_pdf` n-o transmitea, iar deduplicarea unea variantele: 2.081 rânduri unite; cu `coloana` în cheie, 1.710.

**Files:**
- Create: `db/migration_015_coloana_locator.sql`
- Modify: `ingest/extractoare.py` (`din_pdf`), `ingest/normalizeaza.py` (`brut`, `COLOANE`, `CHEIE_DUPLICAT`, `normalizeaza`, `scrie`)
- Test: `ingest/test_coloana.py`

**Interfaces:**
- Produces: `extractoare.segment_din_nume(nume: str) -> str|None` (`"pf"|"pj"|"imm"|"pfa"`); câmpul brut `coloana`; coloana `observations.coloana`; `surse.rol` acceptă `'locator'` (folosit în Task 11–12).

- [ ] **Step 1: Write the failing test**

```python
# ingest/test_coloana.py
import os
import sys
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import extractoare
import normalizeaza as N


def rand(**kw):
    baza = dict(banca="bcr", camp="emitere_card", cod_scenariu=None, serviciu="Emitere card",
                valoare_num=0, valoare_text=None, unitate="lei", conditie=None,
                frecventa=None, data_vigoare=None, citat="0 lei")
    baza.update(kw)
    return baza


class TestColoana(unittest.TestCase):
    def test_segment_din_nume(self):
        self.assertEqual(extractoare.segment_din_nume("Tarife_si_Comisioane_PJ.pdf"), "pj")
        self.assertEqual(extractoare.segment_din_nume("lista-tarife-persoane-fizice.pdf"), "pf")
        self.assertIsNone(extractoare.segment_din_nume("document.pdf"))

    def test_coloane_diferite_nu_se_unesc(self):
        rez = N.dedup([rand(coloana="Visa Classic"), rand(coloana="Mastercard Gold")])
        self.assertEqual(len(rez), 2)

    def test_aceeasi_coloana_se_uneste(self):
        rez = N.dedup([rand(coloana="Visa"), rand(coloana="Visa")])
        self.assertEqual(len(rez), 1)
        self.assertEqual(rez[0]["nr_aparitii"], 2)

    def test_coloana_e_in_coloanele_bazei(self):
        self.assertIn("coloana", N.COLOANE)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run** `python -m unittest ingest.test_coloana -v` → FAIL.

- [ ] **Step 3: Implement**

`db/migration_015_coloana_locator.sql`:

```sql
-- Migrarea 015: varianta de produs (coloana din tabelul de tarife) și rolul
-- `locator` pentru paginile de rețea (ATM/sucursale).
--
-- `coloana`: parser_tarife o citea la 1.100 din 5.578 de rânduri (Visa /
-- Mastercard / Gold), dar se pierdea înainte de bază, iar deduplicarea unea
-- variantele diferite ca și cum ar fi același produs.

ALTER TABLE observations ADD COLUMN IF NOT EXISTS coloana TEXT;

ALTER TABLE surse DROP CONSTRAINT IF EXISTS surse_rol_check;
ALTER TABLE surse ADD CONSTRAINT surse_rol_check
  CHECK (rol IN ('produs', 'hub', 'conditii', 'context', 'locator'));
```

Run: `docker exec -i mip-db psql -U mip -d mip < db/migration_015_coloana_locator.sql` apoi `docker exec -i mip-db psql -U mip -d mip < db/sincronizeaza_vederi.sql` → `observatii_curente e sincronizată`.

În `ingest/extractoare.py`, lângă `_parsere_pdf` (tiparele portate din `scripts/unifica_comisioane.py`):

```python
def _abrev(a):
    return rf"(?<![A-Za-z]){a}(?![A-Za-z])"


# Portat din scripts/unifica_comisioane.py: segmentul din NUMELE documentului.
# Fără el, lista PF și lista PJ a aceleiași bănci se unesc la deduplicare.
SEGMENTE = [
    ("pj", rf"{_abrev('PJ')}|persoane[_\s-]?juridice|juridice|legal[_\s-]?entities|corporate"),
    ("imm", rf"{_abrev('IMM')}|profesii[_\s-]?liberale|{_abrev('SME')}"),
    ("pfa", rf"{_abrev('PDAI')}|activit[ăa][țt]i[_\s-]?independente|{_abrev('PFA')}"),
    ("pf", rf"{_abrev('PF')}|persoane[_\s-]?fizice|fizice|private[_\s-]?individuals"),
]


def segment_din_nume(nume):
    for seg, tipar in SEGMENTE:
        if re.search(tipar, nume or "", re.I):
            return seg
    return None
```

În `din_pdf`, înainte de buclă: `seg_doc = segment_din_nume(sursa or str(cale))`; în `brut(...)`: `segment=c.get("segment") or seg_doc`, `coloana=c.get("coloana")`, `categorie=c.get("categorie")`.

În `ingest/normalizeaza.py`: în `brut` adaugă `"coloana": None,`; `COLOANE` primește `"coloana"` la final; `CHEIE_DUPLICAT` primește `"coloana"`; în `normalizeaza()` rândul primește `"coloana": b.get("coloana")`; în `scrie()`, tuplul din `valori.append(...)` primește `r.get("coloana")` pe ultima poziție, în aceeași ordine ca `COLOANE`.

- [ ] **Step 4: Run** `python -m unittest ingest.test_coloana -v` → PASS (4). Run `python -m unittest ingest.test_reparatii -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add db/migration_015_coloana_locator.sql ingest/extractoare.py ingest/normalizeaza.py ingest/test_coloana.py
git commit -m "ingest: coloana si segmentul ajung in baza, deduplicarea nu mai uneste variante"
```

---

### Task 6: Validatorul colegului pe dobânzi

`crawler/validator.py` (37/38 verdicte corecte pe etalon) nu era conectat. Rulează pe TOT setul de dobânzi o dată, fiindcă consensul între bănci și regula DAE ≥ nominală au nevoie de toate.

**Files:**
- Create: `ingest/validare.py`
- Modify: `ingest/extractoare.py` (`din_html`: păstrează dicționarul parserului în `_rec`), `ingest/normalizeaza.py` (`_incredere`)
- Test: `ingest/test_validare_rate.py`

**Interfaces:**
- Consumes: `crawler.validator.valideaza(inregistrari, indici_bnr=None) -> (inregistrari, sumar)` — setează `r["stare"]` ∈ {OK, SUSPECT, SURSA_VECHE, NEVERIFICAT}.
- Produces: `validare.valideaza_rate(brute: list[dict], valideaza=None) -> collections.Counter`.

- [ ] **Step 1: Write the failing test**

```python
# ingest/test_validare_rate.py
import os
import sys
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import normalizeaza as N
import validare


def fals(recs, indici_bnr=None):
    recs[0]["stare"], recs[1]["stare"] = "SUSPECT", "OK"
    return recs, {}


class TestValidare(unittest.TestCase):
    def test_suspect_devine_ambiguu(self):
        brute = [N.brut(banca="x", sursa="u", _rec={"tip_rata": "dae", "valoare": 7.0}),
                 N.brut(banca="x", sursa="u", _rec={"tip_rata": "nominala", "valoare": 9.0})]
        raport = validare.valideaza_rate(brute, valideaza=fals)
        self.assertTrue(brute[0]["ambiguu"])
        self.assertIn("validator", brute[0]["motiv_ambiguu"])
        self.assertFalse(brute[1]["ambiguu"])
        self.assertEqual(raport["validator_SUSPECT"], 1)

    def test_validatorul_real_da_o_stare(self):
        from crawler.parser_rate import parseaza_linie
        recs, _ = parseaza_linie("Dobânda nominală fixă 7,50%, DAE 8,12%", "x",
                                 "credite", "https://x.ro/credit")
        brute = [N.brut(banca="x", sursa="https://x.ro/credit", _rec=r) for r in recs]
        validare.valideaza_rate(brute)
        for b in brute:
            self.assertIn(b["stare"], {"OK", "SUSPECT", "SURSA_VECHE", "NEVERIFICAT"})

    def test_suspect_plafoneaza_increderea(self):
        self.assertLessEqual(N._incredere({"incredere": 0.9, "stare": "SUSPECT"}), 0.5)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run** `python -m unittest ingest.test_validare_rate -v` → FAIL.

- [ ] **Step 3: Implement**

`ingest/validare.py`:

```python
"""Validatorul colegului (crawler/validator.py) aplicat dobânzilor extrase.

Pe etalon: 37 din 38 de verdicte corecte. Rulează o dată pe tot setul, nu pe
pagină: consensul indicilor între bănci și regula „DAE ≥ nominală pe aceeași
pagină" au nevoie de toate valorile.

SUSPECT și SURSA_VECHE nu se șterg: devin `ambiguu`, deci ajung în coada de
verificare umană, cum cere figura 3.
"""

import collections


def valideaza_rate(brute, valideaza=None):
    if valideaza is None:
        from crawler.validator import valideaza
    cu_rec = [b for b in brute if b.get("_rec")]
    raport = collections.Counter()
    if not cu_rec:
        return raport
    recs = [b["_rec"] for b in cu_rec]
    valideaza(recs, None)       # fără indici BNR: validatorul trece pe consens
    for b, r in zip(cu_rec, recs):
        stare = r.get("stare") or "NEVERIFICAT"
        b["stare"] = stare
        raport[f"validator_{stare}"] += 1
        if stare in ("SUSPECT", "SURSA_VECHE"):
            b["ambiguu"] = True
            b["motiv_ambiguu"] = f"validator: {stare}"
    return raport
```

În `din_html`, în `brut(...)` pentru dobânzi, adaugă `_rec=r`. În `normalizeaza._incredere`, după ramura `SURSA_VECHE`:

```python
    if b.get("stare") == "SUSPECT":
        c = min(c, 0.5)          # o verificare automată a eșuat
```

- [ ] **Step 4: Run** `python -m unittest ingest.test_validare_rate -v` → PASS (3).

- [ ] **Step 5: Commit**

```bash
git add ingest/validare.py ingest/extractoare.py ingest/normalizeaza.py ingest/test_validare_rate.py
git commit -m "ingest: validatorul colegului pe dobanzi, suspectele merg in coada"
```

---

### Task 7: LLM ca rezervă de extracție, cu verificare literală

Figura 3: „determinist întâi, LLM doar dacă nu găsește nimic". `parseaza_linie` întoarce deja semnalul (`problema != None`), dar `din_html` îl arunca. Vechiul `adu_llm` salva textul REPOVESTIT de model; aici modelul primește textul nostru și orice cifră propusă trebuie să apară literal în linie.

**Files:**
- Create: `ingest/llm_rezerva.py`
- Modify: `ingest/extractoare.py` (`din_html`: colectează liniile-problemă), `ingest/populare_initiala.py` (apel în `extrage`, Task 8)
- Test: `ingest/test_llm_rezerva.py`

**Interfaces:**
- Produces: `llm_rezerva.extrage(linii: list[str], banca: str, url: str, categorie: str, client=None, raport=None) -> list[dict]` (brute cu `incredere ≤ 0.6`, `_rec` pentru validator); `din_html` pune liniile-problemă în `ultimele_probleme` (atribut de modul: `extractoare.PROBLEME[url] = [...]`).

- [ ] **Step 1: Write the failing test**

```python
# ingest/test_llm_rezerva.py
import json
import os
import sys
import types
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import llm_rezerva


class ClientFals:
    def __init__(self, valori):
        self.valori = valori
        self.messages = self

    def create(self, **kw):
        text = json.dumps({"valori": self.valori})
        return types.SimpleNamespace(
            content=[types.SimpleNamespace(type="text", text=text)],
            usage=types.SimpleNamespace(input_tokens=100, output_tokens=20))


class TestRezerva(unittest.TestCase):
    LINIE = "Depozit 6 luni\t4,25%\t12 luni\t4,60%"

    def test_accepta_doar_cifre_din_text(self):
        client = ClientFals([
            {"tip_rata": "nominala", "valoare": 4.25, "perioada": "6 luni", "citat": "4,25%"},
            {"tip_rata": "nominala", "valoare": 9.99, "perioada": "24 luni", "citat": "9,99%"},
        ])
        rez = llm_rezerva.extrage([self.LINIE], "libra", "https://x.ro/d", "depozite",
                                  client=client)
        self.assertEqual([b["valoare"] for b in rez], [4.25])
        self.assertLessEqual(rez[0]["incredere"], 0.6)

    def test_fara_linii_fara_apel(self):
        self.assertEqual(llm_rezerva.extrage([], "libra", "u", "depozite", client=None), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run** `python -m unittest ingest.test_llm_rezerva -v` → FAIL.

- [ ] **Step 3: Implement `ingest/llm_rezerva.py`**

```python
"""Rezerva de extracție prin LLM: doar pe liniile pe care parserul nu le-a
putut citi, și doar cu cifre care apar LITERAL în linie.

Motivul regulii literale e măsurat: pe 23.09, `web_fetch` întorcea textul
REPOVESTIT de model („Iată textul integral al paginii…"), deci o cifră putea
fi rescrisă. Aici modelul nu aduce nimic de pe web: primește textul nostru.
Încrederea e plafonată la 0,6, deci valorile trec prin validare și, sub prag,
prin coada de verificare.
"""

import json
import os
import re

import normalizeaza as N

MODEL = os.environ.get("MODEL_REZERVA", "claude-sonnet-5")
MAX_LINII = 20
SISTEM = ("Extragi dobânzi dintr-un text de pe site-ul unei bănci. Răspunzi DOAR cu JSON: "
          '{"valori": [{"tip_rata": "nominala|dae|marja_ircc|marja_euribor", '
          '"valoare": număr, "perioada": text sau null, "citat": fragmentul exact}]}. '
          "Nu inventa: fiecare valoare trebuie să apară în text. Dacă nu e nimic, "
          '{"valori": []}.')


def _forme(valoare):
    v = float(valoare)
    forme = {f"{v:g}", f"{v:.2f}", f"{v:.1f}"}
    return {f.replace(".", ",") for f in forme} | forme


def cifra_in_text(valoare, text):
    try:
        return any(re.search(rf"(?<![\d,.]){re.escape(f)}(?![\d])", text) for f in _forme(valoare))
    except (TypeError, ValueError):
        return False


def extrage(linii, banca, url, categorie, client=None, raport=None):
    linii = [l for l in linii if l.strip()][:MAX_LINII]
    if not linii:
        return []
    if client is None:
        import anthropic
        client = anthropic.Anthropic()
    text = "\n".join(linii)
    r = client.messages.create(model=MODEL, max_tokens=1500, system=SISTEM,
                               messages=[{"role": "user", "content": text}])
    if raport is not None:
        raport["llm_rezerva_apeluri"] += 1
        raport["llm_rezerva_tokeni_intrare"] += r.usage.input_tokens
        raport["llm_rezerva_tokeni_iesire"] += r.usage.output_tokens
    raspuns = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
    try:
        valori = json.loads(raspuns[raspuns.find("{"):raspuns.rfind("}") + 1])["valori"]
    except (ValueError, KeyError):
        return []
    brute = []
    for v in valori:
        if not cifra_in_text(v.get("valoare"), text):
            if raport is not None:
                raport["llm_rezerva_respinse_nu_apar_in_text"] += 1
            continue
        rec = {"tip_rata": v.get("tip_rata"), "valoare": float(v["valoare"]),
               "perioada": v.get("perioada"), "text_sursa": v.get("citat"),
               "sursa_url": url, "banca": banca}
        brute.append(N.brut(
            banca=banca, sursa=url, frecventa_sursa="zilnic", concept=v.get("tip_rata"),
            tip="rata", valoare=float(v["valoare"]), frecventa=v.get("perioada"),
            categorie=categorie, perioada=v.get("perioada"), citat=v.get("citat"),
            incredere=0.6, _rec=rec))
    return brute
```

În `din_html`: la începutul modulului `PROBLEME = {}`; în buclă, `inreg, problema = parseaza_linie(...)` și `if problema: PROBLEME.setdefault(url, []).append(linie)`.

- [ ] **Step 4: Run** `python -m unittest ingest.test_llm_rezerva -v` → PASS (2).

- [ ] **Step 5: Commit**

```bash
git add ingest/llm_rezerva.py ingest/extractoare.py ingest/test_llm_rezerva.py
git commit -m "ingest: LLM doar ca rezerva de extractie, cu cifre verificate literal"
```

---

### Task 8: Traseul unei surse în `populare_initiala.py`, ca în figura 3

**Files:**
- Modify: `ingest/populare_initiala.py` (`proceseaza`, `extrage`, `main`; se elimină `din_fisiere`, `din_bronze`, `--doar-fisiere`, `--din-bronze`, `--fara-llm`)
- Modify: `ingest/flux.py` (se elimină `adu_http`, `adu_playwright`, `adu_llm`, `CASCADA`, `UA_BROWSER`; `cale_bronze` fără `.pdf` forțat)
- Test: `ingest/test_traseu.py`

**Interfaces:**
- Consumes: `transport.adu`, `transport.inchide`, `sanitizare.amprenta_continut`, `validare.valideaza_rate`, `llm_rezerva.extrage`, `extractoare.PROBLEME`, `normalizeaza.scrie(..., banci=)`.
- Produces: `proceseaza(sursa, cur, stare, raport, cu_llm=True) -> (brute, jurnal)`; flag-uri: `--de-la-zero`, `--banca`, `--limita`, `--fara-llm-rezerva`.

- [ ] **Step 1: Write the failing test**

```python
# ingest/test_traseu.py
import collections
import os
import sys
import unittest
from unittest import mock

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import populare_initiala as P
import transport as T


class Cursor:
    def __init__(self, cunoscute=()):
        self.cunoscute, self.executate, self._rez = set(cunoscute), [], None

    def execute(self, sql, params=None):
        self.executate.append((sql, params))
        if sql.startswith("SELECT 1 FROM hashes"):
            self._rez = (1,) if params[1] in self.cunoscute else None

    def fetchone(self):
        return self._rez


SURSA = (7, "cec", "https://cec.ro/tarife", "html", "produs")


class TestTraseu(unittest.TestCase):
    def test_blocat_marcheaza_sursa_si_se_opreste(self):
        cur = Cursor()
        with mock.patch.object(T, "adu", return_value=T.Rezultat("BLOCAT", None, SURSA[2], "http", "HTTP 403")):
            brute, j = P.proceseaza(SURSA, cur, {}, collections.Counter())
        self.assertEqual((brute, j["stare"]), ([], "BLOCAT"))
        self.assertTrue(any("status = 'blocat'" in s for s, _ in cur.executate))

    def test_continut_neschimbat_nu_scrie_bronze(self):
        octeti = b"<main>Depozit 5%</main>"
        import sanitizare
        cur = Cursor(cunoscute={sanitizare.amprenta_continut(octeti)})
        with mock.patch.object(T, "adu", return_value=T.Rezultat("OK", octeti, SURSA[2], "http", "HTTP 200")), \
             mock.patch.object(P.flux, "scrie_bronze") as bronze:
            brute, j = P.proceseaza(SURSA, cur, {}, collections.Counter())
        self.assertEqual(j["stare"], "NESCHIMBAT")
        bronze.assert_not_called()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run** `python -m unittest ingest.test_traseu -v` → FAIL.

- [ ] **Step 3: Implement**

În `ingest/populare_initiala.py`, `proceseaza` devine:

```python
def proceseaza(sursa, cur, stare, raport, cu_llm=True):
    """Traseul complet pentru o sursă, ca în figura 3. Întoarce (brute, jurnal)."""
    sid, slug, url, fmt, rol = sursa
    j = {"sursa": url, "banca": slug, "transport": None, "stare": None, "nota": None}
    rez = transport.adu(url, slug, stare)
    j["transport"], j["nota"] = rez.transport, rez.nota
    if rez.verdict != "OK":
        j["stare"] = rez.verdict
        if rez.verdict == "BLOCAT":
            # Documentat ca blocat, cu dovada; nu se încearcă alt canal.
            cur.execute("UPDATE surse SET status = 'blocat', nota_extractie = %s, "
                        "ultima_rulare = now() WHERE id = %s",
                        (f"blocat de bancă: {rez.nota}", sid))
        return [], j

    amp = sanitizare.amprenta_continut(rez.octeti)
    if flux.amprenta_cunoscuta(cur, sid, amp):
        j["stare"] = "NESCHIMBAT"
        return [], j
    cur.execute("INSERT INTO hashes (id_sursa, format, hash) VALUES (%s, %s, %s)",
                (sid, "pdf" if rez.octeti.startswith(b"%PDF") else "html", amp))
    cale = flux.scrie_bronze(url, rez.octeti)      # Bronze DOAR la schimbare
    return extrage(rez.octeti, cale, slug, url, rol, j, raport, cu_llm)


def extrage(octeti, cale, slug, url, rol, j, raport, cu_llm=True):
    if rol == "locator":
        b_noi, nota = extractoare.din_locator(octeti, url, slug)   # Task 12
    elif octeti.startswith(b"%PDF"):
        b_noi, nota = extractoare.din_pdf(cale, slug, sursa=url)
    else:
        b_noi, nota = extractoare.din_html(octeti, url, slug, rol)
        probleme = extractoare.PROBLEME.pop(url, [])
        if cu_llm and probleme and not any(b.get("tip") == "rata" for b in b_noi):
            categorie = extractoare.clasifica(url, None)[0] or "credite"
            b_noi += llm_rezerva.extrage(probleme, slug, url, categorie, raport=raport)
    j["nota"], j["stare"] = nota, ("OK" if b_noi else "GOL")
    return b_noi, j
```

`main()`:

```python
    ap.add_argument("--de-la-zero", action="store_true",
                    help="golește observațiile, amprentele și inventarul url/document; "
                         "Bronze se mută în bronze_arhiva_<data>")
    ap.add_argument("--fara-llm-rezerva", action="store_true")
    ...
    if a.de_la_zero and not a.banca:
        goleste_tot(err)
    err.write("═══ 1. Descoperire\n")
    descoperire.ruleaza(err, raport, a.banca)                  # Task 10
    err.write("\n═══ 2. Extracție\n")
    brute = din_retea(err, raport, a.banca, a.limita, not a.fara_llm_rezerva)
    raport.update(validare.valideaza_rate(brute))
    err.write(f"\n═══ 3. Normalizare + dedup + scriere ({len(brute)} brute)\n")
    randuri = [x for x in (N.normalizeaza(b, raport) for b in brute) if x]
    N.scrie(randuri, METODA, raport, banci=[a.banca] if a.banca else None)
```

`goleste_tot`:

```python
def goleste_tot(err):
    """Pornire de la zero: nu rămâne nimic din colectările anterioare.

    Rămân cataloagele (`banci`, `produse`) și sursele care nu sunt web
    (aplicații mobile), fiindcă track-ul mobil le folosește.
    """
    import datetime
    import shutil
    with psycopg2.connect(N.dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM observations")
            o = cur.rowcount
            cur.execute("DELETE FROM hashes")
            cur.execute("DELETE FROM surse WHERE tip_sursa IN ('url', 'document')")
            s = cur.rowcount
    if os.path.isdir(flux.BRONZE):
        shutil.move(flux.BRONZE, f"{flux.BRONZE}_arhiva_{datetime.date.today()}")
    err.write(f"de la zero: {o} observații și {s} surse șterse, Bronze arhivat.\n\n")
```

În `din_retea` (fostul `din_rețea`): `proceseaza(s, cur, stare, raport, cu_llm)`; se șterge `time.sleep(1.5)` (pauza e acum în `transport`); `finally: transport.inchide(stare)`; interogarea surselor include și `rol = 'locator'`.

În `ingest/flux.py`, `cale_bronze`:

```python
def cale_bronze(url):
    from crawler.urme import nume_din_url
    nume = nume_din_url(url)
    # urme.nume_din_url pune „.pdf" la orice nume; o pagină HTML nu e PDF.
    if nume.endswith(".pdf") and not url.lower().split("?")[0].endswith(".pdf"):
        nume = nume[:-4]
    return os.path.join(BRONZE, nume)
```

Importuri noi în `populare_initiala.py`, la începutul modulului: `import transport`, `import sanitizare`, `import validare`, `import llm_rezerva`. **`descoperire` se importă în `main()`** (`import descoperire` chiar înainte de `descoperire.ruleaza(...)`): modulul apare abia în Task 10, iar testul acestui task importă `populare_initiala`. La fel, `extractoare.din_locator` apare în Task 12; până atunci nicio sursă nu are `rol='locator'`, deci ramura nu se execută.

- [ ] **Step 4: Run** `python -m unittest ingest.test_traseu -v` → PASS (2). Run `python -m unittest discover -s ingest -p "test_*.py"` → OK.

- [ ] **Step 5: Commit**

```bash
git add ingest/populare_initiala.py ingest/flux.py ingest/test_traseu.py
git commit -m "ingest: traseul din figura 3, stop la blocaj, Bronze doar la schimbare, --de-la-zero"
```

---

### Task 9: Vocabular — trei concepte lipsă

Măsurat pe eșantion: 64,5% mapate. Printre nemapate, concepte reale: „Taxa recuperare card" (23), contestare nejustificată (~38), pachet de servicii.

**Files:**
- Modify: `crawler/vocabular.py` (`SERVICII`, înaintea ultimelor două intrări, `file_cec` și `alerta_sms`, care trebuie să rămână ultimele)
- Test: `ingest/test_vocabular_nou.py`

- [ ] **Step 1: Write the failing test**

```python
# ingest/test_vocabular_nou.py
import os
import sys
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

from crawler import vocabular


def concept(serviciu):
    return vocabular.canonic({"serviciu": serviciu, "sectiune": "", "detaliu": ""})[0]


class TestVocabular(unittest.TestCase):
    def test_recuperare_card(self):
        self.assertEqual(concept("Taxa recuperare card reținut de ATM"), "recuperare_card")

    def test_contestare(self):
        self.assertEqual(concept("Contestare nejustificată a unei tranzacții"), "contestare_tranzactie")

    def test_pachet(self):
        self.assertEqual(concept("Comision lunar pachet de servicii"), "pachet_servicii")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run** `python -m unittest ingest.test_vocabular_nou -v` → FAIL.

- [ ] **Step 3: Implement** — în `SERVICII`, imediat înainte de `("file_cec", ...)`:

```python
    # Adăugate pe 23.09.2026: concepte reale printre valorile nemapate
    # („Taxa recuperare card", 23 de valori; contestare nejustificată, ~38).
    ("recuperare_card", r"recuper\w*[^.]{0,30}card|card[^.]{0,30}(re[țt]inut|recuper)"),
    ("contestare_tranzactie", r"contest\w*[^.]{0,40}(nejustificat|tranzac|opera[țt]iun)"),
    ("pachet_servicii", r"pachet\w*\s+de\s+servicii|abonament\w*\s+lunar[^.]{0,20}pachet"),
```

- [ ] **Step 4: Run tests**

Run: `python -m unittest ingest.test_vocabular_nou -v` → PASS (3).
Run: `python scripts/test_validare.py` → `0 eșuate` (dacă un test existent se strică, noua regulă e prea largă: se restrânge, nu se modifică testul).

- [ ] **Step 5: Commit**

```bash
git add crawler/vocabular.py ingest/test_vocabular_nou.py
git commit -m "crawler: vocabular cu recuperare card, contestare si pachet de servicii"
```

---

### Task 10: Descoperirea A1 — sitemap ∪ navigare, toate adresele clasificate

Crawler-ul colegului salva doar paginile vizitate (≤80) și naviga doar dacă sitemap-ul era gol, pe un nivel. Măsurat: 39% din cerințe acoperite; cursul valutar găsit la 5 din 23 de bănci; `patriabank.ro/curs-valutar` există, dar lipsește din sitemap.

**Files:**
- Create: `ingest/descoperire.py`
- Test: `ingest/test_descoperire.py`

**Interfaces:**
- Consumes: `transport.adu`; `flux.reguli_pentru(url, banca).sitemapuri`; `extractoare.clasifica(url, titlu) -> (categorie, produs, sursa)`; `ingest/banks.py: BANKS` (30 de bănci, `name`, `url`, `acces_cunoscut`).
- Produces: `clasifica_adresa(url, text_link="") -> dict|None` cu cheile `rol`, `format`, `produs`; `ruleaza(err, raport, banca=None) -> None` (scrie în `surse` și `surse_produse`).

- [ ] **Step 1: Write the failing test**

```python
# ingest/test_descoperire.py
import os
import sys
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import descoperire as D


class TestClasificare(unittest.TestCase):
    def test_pdf_de_tarife(self):
        c = D.clasifica_adresa("https://www.bcr.ro/content/dam/ro/tarife-pf.pdf")
        self.assertEqual((c["rol"], c["format"], c["produs"]), ("conditii", "pdf", "comisioane"))

    def test_document_fara_sufix_pdf(self):
        c = D.clasifica_adresa("https://x.ro/download?id=12", "Lista de tarife și comisioane (PDF)")
        self.assertEqual(c["rol"], "conditii")

    def test_locator(self):
        self.assertEqual(D.clasifica_adresa("https://x.ro/retea-unitati-atm")["rol"], "locator")

    def test_formular_standardizat_nu_e_exclus(self):
        self.assertIsNotNone(D.clasifica_adresa("https://x.ro/formular-standardizat-comisioane.pdf"))

    def test_zgomot_exclus(self):
        self.assertIsNone(D.clasifica_adresa("https://x.ro/blog/5-sfaturi"))
        self.assertIsNone(D.clasifica_adresa("https://x.ro/cariere"))

    def test_url_normalizat(self):
        self.assertEqual(D.normalizeaza_url("https://X.ro/credite/?utm_source=a#top"),
                         "https://x.ro/credite")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run** `python -m unittest ingest.test_descoperire -v` → FAIL.

- [ ] **Step 3: Implement `ingest/descoperire.py`**

```python
"""Banda A1: găsește adresele unei bănci și le scrie în `surse`. Nicio cifră.

Față de crawler/main.py (colegul), trei schimbări măsurate:
  - sitemap ∪ navigare, nu navigare doar când sitemap-ul e gol:
    `patriabank.ro/curs-valutar` există, dar lipsește din sitemap-ul de 624 de
    adrese; cursul valutar era găsit la 5 bănci din 23;
  - TOATE adresele clasificate se salvează, nu doar cele ≤80 vizitate;
  - EXCLUDE fără „formular", „contact", „campanii", „atm", „sucursal": prindeau
    formularul standardizat de comisioane și locatoarele pentru hartă.

Pentru a nu extrage 2.565 de pagini la BCR, fiecare produs primește cel mult
MAX_PE_PRODUS pagini `activ`; restul intră `pauza`, vizibile în inventar.
Documentele (tarife) și locatoarele intră toate `activ`.
"""

import collections
import gzip
import re
import sys
from urllib.parse import urljoin, urlparse, urlunparse

import psycopg2
from bs4 import BeautifulSoup

import extractoare
import flux
import normalizeaza as N
import transport
from banks import BANKS

MAX_PE_PRODUS = 6
MAX_PAGINI_NAVIGARE = 40
MAX_COPII_SITEMAP = 50
ZGOMOT = ["blog", "news", "/stiri", "presa", "comunicat", "cariere", "csr", "cookie",
          "gdpr", "confidential", "protectia-datelor", "politica-de", "despre-noi",
          "investitori", "arhiva", "login", "autentificare", "fraud", "securitate",
          "reclamat", "sitemap", "rss", "/tag/", "/author/", "search", "?s="]
RE_LOCATOR = re.compile(r"retea|unitati|agentii|sucursal|locati|harta|\batm\b|bancomat|"
                        r"branch|locator|find-us|puncte-de-lucru", re.I)
RE_DOCUMENT_TEXT = re.compile(r"\bpdf\b|descarc|download|lista de tarife|formular", re.I)
RE_DOCUMENT_URL = re.compile(r"\.pdf($|\?)|/dam/|/download|/documente?/", re.I)


def normalizeaza_url(url):
    p = urlparse(url.strip())
    cale = p.path.rstrip("/") or "/"
    interogare = "&".join(q for q in p.query.split("&") if q and not q.startswith("utm_"))
    return urlunparse((p.scheme, p.netloc.lower(), cale, "", interogare, ""))


def clasifica_adresa(url, text_link=""):
    jos = url.lower()
    if any(z in jos for z in ZGOMOT):
        return None
    if RE_LOCATOR.search(urlparse(jos).path):
        return {"rol": "locator", "format": "html", "produs": None}
    e_document = bool(RE_DOCUMENT_URL.search(jos) or RE_DOCUMENT_TEXT.search(text_link or ""))
    categorie, produs, _ = extractoare.clasifica(url, text_link)
    if e_document:
        return {"rol": "conditii", "format": "pdf" if ".pdf" in jos else None,
                "produs": produs or "comisioane"}
    if not categorie:
        return None
    return {"rol": "produs", "format": "html", "produs": produs}


def _pe_domeniu(url, baza):
    radacina = lambda h: ".".join((h or "").lower().split(".")[-2:])
    return radacina(urlparse(url).netloc) == radacina(urlparse(baza).netloc)


def din_sitemap(baza, slug, stare, raport):
    reguli = flux.reguli_pentru(baza, slug)
    de_citit = list(dict.fromkeys(reguli.sitemapuri + [urljoin(baza, "/sitemap.xml")]))
    vazute, gasite = set(), []
    while de_citit and len(vazute) < MAX_COPII_SITEMAP:
        u = de_citit.pop(0)
        if u in vazute:
            continue
        vazute.add(u)
        rez = transport.adu(u, slug, stare)
        if rez.verdict != "OK":
            raport[f"sitemap_{rez.verdict}"] += 1
            continue
        corp = rez.octeti
        if corp[:2] == b"\x1f\x8b":
            corp = gzip.decompress(corp)
        text = corp.decode("utf-8", errors="replace")
        locuri = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", text)
        if "<sitemapindex" in text.lower():
            de_citit.extend(locuri)
        else:
            gasite.extend(l for l in locuri if _pe_domeniu(l, baza))
    if de_citit:
        raport["sitemap_copii_necitite"] += len(de_citit)   # nicio limită tăcută
    return [(u, "") for u in gasite]


def din_navigare(baza, slug, stare, raport):
    """BFS pe 2 niveluri: linkurile se păstrează cu textul lor (ajută la PDF-uri)."""
    frontiera, vazute, gasite, pagini = [baza], {baza}, [], 0
    for adancime in range(2):
        urmatoare = []
        for u in frontiera:
            if pagini >= MAX_PAGINI_NAVIGARE:
                break
            rez = transport.adu(u, slug, stare)
            pagini += 1
            if rez.verdict != "OK" or rez.octeti.startswith(b"%PDF"):
                if rez.verdict == "BLOCAT" and u == baza:
                    return None                       # banca ne-a blocat
                continue
            soup = BeautifulSoup(rez.octeti, "lxml")
            for a in soup.find_all("a", href=True):
                l = urljoin(rez.url_final, a["href"]).split("#")[0]
                if not l.startswith("http") or l in vazute:
                    continue
                vazute.add(l)
                text = a.get_text(" ", strip=True)
                gasite.append((l, text))
                if _pe_domeniu(l, baza) and clasifica_adresa(l, text):
                    urmatoare.append(l)
        frontiera = urmatoare
    return gasite


def _slug_pentru(nume, cur):
    cur.execute("SELECT slug FROM banci WHERE nume = %s", (nume,))
    r = cur.fetchone()
    return r[0] if r else None


def ruleaza(err, raport, banca=None):
    stare = {}
    try:
        with psycopg2.connect(N.dsn()) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT nume, id FROM produse")
                produse = dict(cur.fetchall())
                for b in BANKS:
                    slug = _slug_pentru(b["name"], cur)
                    if not slug or (banca and slug != banca):
                        continue
                    nav = din_navigare(b["url"], slug, stare, raport)
                    if nav is None:
                        cur.execute(
                            """INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format,
                                   metoda, status, nota_extractie, frecventa)
                               SELECT id, 'url', %s, 'hub', 'html', 'http', 'blocat',
                                      'blocat de bancă la descoperire', 'lunar'
                               FROM banci WHERE slug = %s
                               ON CONFLICT DO NOTHING""", (b["url"], slug))
                        err.write(f"  {slug:20s} BLOCAT — documentat, fără alt canal\n")
                        raport["banci_blocate"] += 1
                        continue
                    candidati = din_sitemap(b["url"], slug, stare, raport) + nav
                    alese, pe_produs = {}, collections.Counter()
                    for u, text in candidati:
                        if not _pe_domeniu(u, b["url"]) and not RE_DOCUMENT_URL.search(u):
                            continue
                        c = clasifica_adresa(u, text)
                        if not c:
                            continue
                        alese.setdefault(normalizeaza_url(u), c)
                    for u, c in alese.items():
                        activ = c["rol"] != "produs" or pe_produs[c["produs"]] < MAX_PE_PRODUS
                        if c["rol"] == "produs" and activ:
                            pe_produs[c["produs"]] += 1
                        cur.execute(
                            """INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format,
                                   metoda, status, frecventa, nota_extractie)
                               SELECT id, 'url', %s, %s, %s, 'http', %s, 'lunar', %s
                               FROM banci WHERE slug = %s
                               ON CONFLICT DO NOTHING RETURNING id""",
                            (u, c["rol"], c["format"], "activ" if activ else "pauza",
                             None if activ else "descoperit, peste plafonul pe produs", slug))
                        r = cur.fetchone()
                        if r and c["produs"] in produse:
                            cur.execute("INSERT INTO surse_produse (id_sursa, id_produs) "
                                        "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                                        (r[0], produse[c["produs"]]))
                    n_activ = sum(1 for c in alese.values() if c["rol"] != "produs") + sum(pe_produs.values())
                    err.write(f"  {slug:20s} {len(alese):5d} adrese · {n_activ:4d} active\n")
                    raport["surse_descoperite"] += len(alese)
                    conn.commit()
    finally:
        transport.inchide(stare)
```

Notă pentru implementator: `ux_surse_url` e UNIQUE pe `(id_banca, sursa)`, deci `ON CONFLICT DO NOTHING` acoperă redescoperirile. Dacă `surse_produse` n-are cheie unică, `ON CONFLICT DO NOTHING` nu are efect, dar nici nu dublează: rândul `surse` e nou doar o dată.

- [ ] **Step 4: Run** `python -m unittest ingest.test_descoperire -v` → PASS (6).

- [ ] **Step 5: Probă reală pe o bancă mică, apoi commit**

Run: `python -c "import sys,io,collections; sys.path[:0]=['.','ingest']; import config; config.incarca(); import descoperire; r=collections.Counter(); descoperire.ruleaza(sys.stderr, r, 'vista'); print(dict(r))"`
Expected: o linie `vista  N adrese · M active`, cu N > 0; zero erori.

```bash
git add ingest/descoperire.py ingest/test_descoperire.py
git commit -m "ingest: descoperire sitemap si navigare, toate adresele clasificate in surse"
```

---

### Task 11: Descoperirea A2 — LLM doar pentru goluri, cu cost logat

`claudeCrawl.py` nu înregistra costul, nu verifica adresele și avea Salt pe domeniul greșit (`saltbank.ro`). Rulează DOAR pentru produsele lipsă după A1 și NU pe băncile blocate.

**Files:**
- Create: `ingest/descoperire_llm.py` (copiat din `C:\Users\robert.postolache\Downloads\flux-colectare\claudeCrawl.py`, apoi modificat)
- Test: `ingest/test_descoperire_llm.py`

**Interfaces:**
- Consumes: `transport.adu` (verificarea adreselor), `descoperire.clasifica_adresa`, `descoperire.normalizeaza_url`.
- Produces: `goluri(cur, slug) -> list[str]` (produsele fără nicio sursă activă); `ruleaza_banca(slug, url_banca, produse_lipsa, client=None) -> dict` cu `documente`, `cost` (`tokeni_intrare`, `tokeni_iesire`); CLI `python ingest/descoperire_llm.py --banca vista [--scrie]`.

- [ ] **Step 1: Write the failing test**

```python
# ingest/test_descoperire_llm.py
import os
import sys
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import descoperire_llm as L


class TestLlm(unittest.TestCase):
    def test_banci_blocate_sunt_sarite(self):
        self.assertTrue(L.e_blocata("cec"))
        self.assertTrue(L.e_blocata("banca-transilvania"))
        self.assertFalse(L.e_blocata("vista"))

    def test_domenii_permise_din_url(self):
        self.assertEqual(L.domenii("https://salt.bank/"), ["salt.bank", "www.salt.bank"])

    def test_cost_se_insumeaza(self):
        c = L.Cost()
        c.adauga(type("U", (), {"input_tokens": 100, "output_tokens": 30})())
        c.adauga(type("U", (), {"input_tokens": 50, "output_tokens": 10})())
        self.assertEqual((c.intrare, c.iesire), (150, 40))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run** `python -m unittest ingest.test_descoperire_llm -v` → FAIL.

- [ ] **Step 3: Implement**

Copiază `claudeCrawl.py` în `ingest/descoperire_llm.py` și modifică:

1. Configurarea din variabile de mediu dispare; `ruleaza_banca(slug, url_banca, produse_lipsa, client=None)` primește parametrii. `DOMENII_PERMISE` devine `domenii(url_banca)`:

```python
BLOCATE = {"cec", "banca-transilvania", "unicredit", "intesa"}   # 403 pe 23.09.2026


def e_blocata(slug):
    """Regula echipei: o bancă blocată nu se accesează prin alt canal, nici prin
    infrastructura Anthropic."""
    return slug in BLOCATE


def domenii(url_banca):
    gazda = urlparse(url_banca).netloc.lower().removeprefix("www.")
    return [gazda, f"www.{gazda}"]


class Cost:
    def __init__(self):
        self.intrare = self.iesire = 0

    def adauga(self, usage):
        self.intrare += usage.input_tokens
        self.iesire += usage.output_tokens
```

2. `PRODUSE` se citește din tabela `produse` (aceleași 14 nume); mesajul inițial cere DOAR produsele din `produse_lipsa`: `f"Caută doar: {', '.join(produse_lipsa)}. Restul sunt deja acoperite."`.
3. `MODEL = os.environ.get("MODEL", "claude-sonnet-5")`.
4. În bucla de ture: `cost.adauga(r.usage)` după fiecare `get_final_message()`; rezultatul întoarce `"cost": {"tokeni_intrare": cost.intrare, "tokeni_iesire": cost.iesire}`.
5. Fiecare adresă propusă se verifică înainte de scriere: `transport.adu(u, slug, stare).verdict == "OK"` și `descoperire.clasifica_adresa(u, d.get("dovada", ""))` nu e `None`; altfel se numără `respinse`.
6. `goluri(cur, slug)`:

```python
def goluri(cur, slug):
    cur.execute("""SELECT p.nume FROM produse p
                   WHERE NOT EXISTS (
                     SELECT 1 FROM surse_produse sp JOIN surse s ON s.id = sp.id_sursa
                     JOIN banci b ON b.id = s.id_banca
                     WHERE sp.id_produs = p.id AND b.slug = %s AND s.status = 'activ')
                   ORDER BY p.nume""", (slug,))
    return [r[0] for r in cur.fetchall()]
```

7. CLI: `--banca` obligatoriu; fără `--scrie` afișează doar documentele propuse și costul; cu `--scrie` le inserează în `surse`/`surse_produse` exact ca în `descoperire.ruleaza` (status `activ`, `nota_extractie='descoperit prin LLM'`).

- [ ] **Step 4: Run** `python -m unittest ingest.test_descoperire_llm -v` → PASS (3).

- [ ] **Step 5: Commit**

```bash
git add ingest/descoperire_llm.py ingest/test_descoperire_llm.py
git commit -m "ingest: descoperirea LLM in repo, doar pentru goluri, cost logat, fara banci blocate"
```

---

### Task 12: Locatoarele băncilor → `locatii`

**Files:**
- Modify: `ingest/extractoare.py` (nou `din_locator`), `ingest/populare_initiala.py` (scriere în `locatii` după extracție)
- Modify: `ingest/load_locatii_overture.py` (tiparul Cetelem)
- Test: `ingest/test_locator.py`

**Interfaces:**
- Produces: `extractoare.din_locator(octeti, url, slug) -> (list[dict], str)`, fiecare dict cu `tip` (`atm`|`sucursala`), `nume`, `adresa`, `lat`, `lon`, `program`; `populare_initiala.scrie_locatii(puncte, raport)`.

- [ ] **Step 1: Write the failing test**

```python
# ingest/test_locator.py
import os
import sys
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import extractoare


class TestLocator(unittest.TestCase):
    def test_json_inline(self):
        html = b"""<script>var agentii = [{"name":"Agentia Unirii","type":"branch",
        "address":"Bd. Unirii 1","lat":44.4268,"lng":26.1025,"schedule":"L-V 9-17"},
        {"name":"ATM Mall","type":"atm","latitude":"44.43","longitude":"26.05"}];</script>"""
        puncte, _ = extractoare.din_locator(html, "https://x.ro/retea", "libra")
        self.assertEqual(len(puncte), 2)
        self.assertEqual(puncte[0]["tip"], "sucursala")
        self.assertEqual(puncte[1]["tip"], "atm")
        self.assertAlmostEqual(puncte[0]["lat"], 44.4268)
        self.assertEqual(puncte[0]["program"], "L-V 9-17")

    def test_atribute_data(self):
        html = b'<div class="atm" data-lat="45.75" data-lng="21.22">ATM Timisoara</div>'
        puncte, _ = extractoare.din_locator(html, "https://x.ro/atm", "libra")
        self.assertEqual((puncte[0]["tip"], puncte[0]["lat"]), ("atm", 45.75))

    def test_coordonate_in_afara_romaniei_se_arunca(self):
        html = b'<div data-lat="48.85" data-lng="2.35">Paris</div>'
        self.assertEqual(extractoare.din_locator(html, "https://x.ro/retea", "libra")[0], [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run** `python -m unittest ingest.test_locator -v` → FAIL.

- [ ] **Step 3: Implement**

În `ingest/extractoare.py`:

```python
# ==========================================================================
# 6. Locatoare: sucursale și ATM-uri, din pagina de rețea a băncii
# ==========================================================================

RE_OBIECT_JSON = re.compile(r"\{[^{}]*?(?:\"lat(?:itude)?\"|\"lng\"|\"lon(?:gitude)?\")[^{}]*\}", re.S)
CHEI_LAT, CHEI_LON = ("lat", "latitude"), ("lng", "lon", "longitude")
CHEI_NUME = ("name", "nume", "title", "denumire")
CHEI_ADRESA = ("address", "adresa", "street")
CHEI_PROGRAM = ("schedule", "program", "hours", "orar", "opening_hours")


def _in_romania(lat, lon):
    return 43.6 <= lat <= 48.3 and 20.2 <= lon <= 29.8


def _tip_locatie(text):
    return "atm" if re.search(r"\batm\b|bancomat", text or "", re.I) else "sucursala"


def _primul(d, chei):
    for k in chei:
        if d.get(k) not in (None, ""):
            return d[k]
    return None


def din_locator(octeti, url, slug):
    """Coordonate din JSON-ul inclus în pagină sau din atribute `data-lat`.

    Punctele în afara României se aruncă: unele locatoare listează și rețeaua
    grupului din alte țări.
    """
    import json
    from bs4 import BeautifulSoup
    text = octeti.decode("utf-8", errors="replace")
    puncte = []
    for m in RE_OBIECT_JSON.finditer(text):
        try:
            d = json.loads(m.group(0))
            lat, lon = float(_primul(d, CHEI_LAT)), float(_primul(d, CHEI_LON))
        except (ValueError, TypeError):
            continue
        tip = _tip_locatie(" ".join(str(d.get(k, "")) for k in ("type", "tip", "category", "name")))
        puncte.append({"tip": tip, "nume": _primul(d, CHEI_NUME), "adresa": _primul(d, CHEI_ADRESA),
                       "lat": lat, "lon": lon, "program": _primul(d, CHEI_PROGRAM)})
    for el in BeautifulSoup(octeti, "lxml").select("[data-lat]"):
        try:
            lat = float(el["data-lat"])
            lon = float(el.get("data-lng") or el.get("data-lon"))
        except (ValueError, TypeError):
            continue
        eticheta = " ".join(el.get("class", [])) + " " + el.get_text(" ", strip=True)
        puncte.append({"tip": _tip_locatie(eticheta), "nume": el.get_text(" ", strip=True)[:120],
                       "adresa": None, "lat": lat, "lon": lon, "program": None})
    puncte = [p for p in puncte if _in_romania(p["lat"], p["lon"])]
    for p in puncte:
        p.update(banca=slug, sursa=url, _locatie=True)
    return puncte, f"locator: {len(puncte)} puncte"
```

În `populare_initiala.main()`, înainte de normalizare: `locatii = [b for b in brute if b.get("_locatie")]`; `brute = [b for b in brute if not b.get("_locatie")]`; `scrie_locatii(locatii, raport)`:

```python
def scrie_locatii(puncte, raport):
    """Locatorul băncii e sursa oficială: înlocuiește Overture la banca respectivă."""
    if not puncte:
        return
    with psycopg2.connect(N.dsn()) as conn:
        with conn.cursor() as cur:
            banci = sorted({p["banca"] for p in puncte})
            cur.execute("""DELETE FROM locatii l USING banci b
                           WHERE b.id = l.id_banca AND b.slug = ANY(%s)
                             AND l.sursa IN ('locator_banca', 'overture')""", (banci,))
            for p in puncte:
                cur.execute("""INSERT INTO locatii (id_banca, tip, nume, adresa, lat, lon,
                                   program, sursa, ref_extern)
                               SELECT id, %s, %s, %s, %s, %s, %s, 'locator_banca', %s
                               FROM banci WHERE slug = %s
                               ON CONFLICT (id_banca, tip, lat, lon) DO NOTHING""",
                            (p["tip"], p["nume"], p["adresa"], p["lat"], p["lon"],
                             p["program"], p["sursa"], p["banca"]))
                raport["locatii_locator"] += cur.rowcount
```

În `ingest/load_locatii_overture.py`, în `TIPARE`, după `citibank`: `("cetelem", re.compile(r"cetelem", re.I)),`.

- [ ] **Step 4: Run** `python -m unittest ingest.test_locator -v` → PASS (3).

- [ ] **Step 5: Commit**

```bash
git add ingest/extractoare.py ingest/populare_initiala.py ingest/load_locatii_overture.py ingest/test_locator.py
git commit -m "ingest: locatoarele bancilor in locatii, Cetelem in Overture"
```

---

### Task 13: Măsurare — re-scorarea dobânzilor pe etalon

**Files:**
- Create: `scripts/rescore_etalon.py`

- [ ] **Step 1: Implement**

```python
"""Re-scorează parserul de dobânzi pe etalonul manual (38 de valori, 16.09.2026).

Pentru fiecare item: e (tip, valoare) produs de parser pe `text_sursa`?
  tip_corect=da  → trebuie găsit      (recall pe valori corecte)
  tip_corect=nu  → nu trebuie găsit   (greșeala nu trebuie să reapară)
Etalonul e folosit ca etalon, nu ca date: nu se încarcă nicăieri.
"""
import json
import pathlib
import sys

RADACINA = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADACINA))
sys.stdout.reconfigure(encoding="utf-8")

from crawler.parser_rate import parseaza_linie

etalon = json.loads((RADACINA / "date/pachet/etalon_manual.json").read_text(encoding="utf-8"))
bune = gasite = greseli = reaparute = 0
for it in etalon:
    recs, _ = parseaza_linie(it["text_sursa"], it["banca"], "credite", it["sursa_url"])
    perechi = {(r.get("tip_rata"), round(float(r.get("valoare") or 0), 2)) for r in recs}
    cheie = (it["tip_rata_parser"], round(float(it["valoare_parser"]), 2))
    if it["tip_corect"] == "da":
        bune += 1
        gasite += cheie in perechi
    else:
        greseli += 1
        reaparute += cheie in perechi
print(f"corecte regăsite: {gasite}/{bune}   greșeli reapărute: {reaparute}/{greseli}")
```

- [ ] **Step 2: Run** `python scripts/rescore_etalon.py`
Expected: o linie `corecte regăsite: X/33   greșeli reapărute: Y/5`. Notează cifra pentru `docs/IMBUNATATIRI.md`.

- [ ] **Step 3: Commit**

```bash
git add scripts/rescore_etalon.py
git commit -m "scripts: re-scorarea dobanzilor pe etalonul manual"
```

---

### Task 14: robots.txt pe proxy-ul `/pdf`

**Files:**
- Modify: `app/server.py` (funcția `adu_pdf`)

- [ ] **Step 1: Implement** — la începutul `adu_pdf(url)`:

```python
    # ING are `Disallow: *.pdf`. Allowlist-ul din baza de date nu e suficient:
    # un PDF înregistrat înainte de verificare trecea prin proxy.
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "ingest"))
    import flux
    if not flux.permite(url, "proxy"):
        raise PermissionError("interzis de robots.txt")
```

și în handler-ul `/pdf`, `PermissionError` → răspuns 403 cu textul „interzis de robots.txt al băncii".

- [ ] **Step 2: Verify** — pornește serverul și cere un PDF ING înregistrat: `curl -s -o NUL -w "%{http_code}" "http://127.0.0.1:8765/pdf?u=<url ING .pdf>"` → `403`. Rulează `python app/verifica_pagini.py` → `0 pagini cu erori`.

- [ ] **Step 3: Commit**

```bash
git add app/server.py
git commit -m "app: proxy-ul /pdf respecta robots.txt"
```

---

### Task 15: Rularea de la zero și raportul

Nu se execută fără confirmarea lui Robert la pasul 3 (cost LLM).

- [ ] **Step 1: Toate testele**

Run: `python -m unittest discover -s ingest -p "test_*.py"` → OK. `python scripts/test_validare.py` → `0 eșuate`.

- [ ] **Step 2: Descoperire + extracție de la zero, fără LLM de descoperire**

Run: `set PYTHONUNBUFFERED=1 && python -u ingest/populare_initiala.py --de-la-zero > loguri/populare_zero.log 2>&1`
Expected: secțiunile „1. Descoperire", „2. Extracție", „3. Normalizare"; CEC, BT, UniCredit, Intesa marcate `BLOCAT`; `=== RAPORT ===` la final.

- [ ] **Step 3: Descoperirea LLM pe o bancă, cost măsurat**

Run: `python ingest/descoperire_llm.py --banca vista`
Expected: documentele propuse și `cost: X tokeni intrare, Y ieșire`. **Oprire: se raportează costul lui Robert și se continuă cu `--scrie` pe restul băncilor neblocate doar după acordul lui.** Apoi: `python -u ingest/populare_initiala.py --banca <slug>` pentru fiecare bancă la care LLM-ul a adăugat surse.

- [ ] **Step 4: Verificări în bază**

```bash
docker exec -i mip-db psql -U mip -d mip -c "SELECT b.slug, count(o.*) obs, count(o.data_vigoare) datate, count(*) FILTER (WHERE o.ambiguu) ambigue FROM banci b LEFT JOIN surse s ON s.id_banca=b.id LEFT JOIN observations o ON o.id_sursa=s.id GROUP BY 1 ORDER BY 2 DESC;"
docker exec -i mip-db psql -U mip -d mip -c "SELECT status, count(*) FROM surse GROUP BY 1;"
docker exec -i mip-db psql -U mip -d mip -c "SELECT sursa, tip, count(*) FROM locatii GROUP BY 1,2;"
```

Run: `python app/verifica_pagini.py` (serverul pornit) → `0 pagini cu erori`.

- [ ] **Step 5: `docs/IMBUNATATIRI.md`**

Un tabel cu fiecare îmbunătățire din spec: ce s-a schimbat, cifra ÎNAINTE (rularea din 23.09: 24.837 brute, 10.160 unite, 53% datate, ~59% mapate; etalon: cifra de la Task 13 înainte de Task 6/9) și cifra DUPĂ (din `loguri/populare_zero.log` și interogările de la pasul 4). Punctul 6 (coloane multiple) apare ca „măsurat, amânat", cu motivul. Actualizează secțiunea de cifre din `README.md` și lista de migrări (014, 015).

- [ ] **Step 6: Commit**

```bash
git add docs/IMBUNATATIRI.md README.md
git commit -m "docs: imbunatatirile popularii de la zero, cu cifre inainte si dupa"
```
