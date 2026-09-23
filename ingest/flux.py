"""Traseul unei surse, ca în figura 3 din artefact — cu cele trei transporturi.

Un singur drum, aplicat la fel oricărei surse:

    robots.txt ─► transport (cascadă) ─► Bronze ─► amprentă vs. ieri
                                                        │
                            identică ──► STOP (nimic nou)
                                                        │
                                                   diferită
                                                        ▼
                                          extracție ─► normalizare ─► observations

TRANSPORTUL E O CASCADĂ, în ordinea cerută:

  1. `http`        stiva proprie (Desktop/Scraping/scraper.py) — `requests`,
                   User-Agent care ne identifică, delay, detecție de encoding.
                   Cea mai ieftină și cea mai transparentă. Merge pe majoritate.

  2. `playwright`  motorul colegului (pentru_coleg_bs4_21sept/crawler) — browser
                   Chromium real. Ia paginile randate prin JS și trece de unele
                   WAF-uri. Măsurat: deblochează CEC (403 pe http, 200 aici, cu
                   9 PDF-uri). NU trece de Banca Transilvania, UniCredit și
                   Intesa — acolo răspunsul e „Acces blocat", explicit, și ne
                   oprim.

  3. `llm`         `web_fetch` server-side (flux-colectare/claudeCrawl.py).
                   Cererea pleacă din infrastructura Anthropic, cu agentul
                   `Claude-User`, iar robots.txt e impus de ei. Codul nostru nu
                   atinge serverul băncii. Ultima treaptă fiindcă costă bani
                   per apel și întoarce text extras, nu marcaj.

Se folosesc implementările colegilor, nu doar rezultatele lor:

    crawler/robots.py     robots.txt după RFC 9309, cu wildcard-uri.
                          `urllib.robotparser` face doar potrivire pe prefix și
                          ar rata `Disallow: *.pdf` — regula reală a ING.
    crawler/urme.py       amprentă pe OCTEȚI + nume stabil de fișier. Amprenta
                          pe valori ar confunda „banca a schimbat prețul" cu
                          „noi am schimbat parserul".
    crawler/parser_pdf    formularele standardizate prin Legea 258/2017
    crawler/parser_tarife listele de tarife nestandardizate
    crawler/vocabular     maparea la conceptul canonic
    parser_rate.py        dobânzile din HTML (varianta proprie)

Rulare:
    python ingest/flux.py --pas tot          # toate sursele neprocesate
    python ingest/flux.py --banca cec
    python ingest/flux.py --limita 10 --fara-llm
"""

import argparse
import collections
import io
import os
import sys
import time

import psycopg2

AICI = os.path.dirname(os.path.abspath(__file__))
RADACINA = os.path.dirname(AICI)
sys.path.insert(0, RADACINA)
sys.path.insert(0, AICI)

SCRAPING = os.path.join(os.path.expanduser("~"), "Desktop", "Scraping")
PACHET = os.path.join(os.path.expanduser("~"), "Downloads", "pentru_coleg_bs4_21sept")
FLUX_LLM = os.path.join(os.path.expanduser("~"), "Downloads", "flux-colectare")
for p in (SCRAPING, PACHET, FLUX_LLM):
    sys.path.insert(0, p)

import config                      # noqa: E402
import extractoare                 # noqa: E402
import normalizeaza as N           # noqa: E402

BRONZE = os.path.join(RADACINA, "bronze")

# User-Agent pentru browser. E cel din codul colegului și e corect aici: cu
# Playwright rulează chiar Chromium, deci un UA de Chrome nu e o minciună —
# spre deosebire de `requests` care ar pretinde același lucru. Stiva `http`
# folosește UA-ul nostru, care ne identifică explicit.
UA_BROWSER = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")


# ==========================================================================
# robots.txt — implementarea colegului, nu urllib
# ==========================================================================

def _reguli_robots():
    from crawler.robots import RegulliRobots
    return RegulliRobots


_CACHE_ROBOTS = {}


def permite(url, banca_id):
    """robots.txt după RFC 9309, o citire per origine.

    Se folosește `crawler/robots.py`, nu `urllib.robotparser`. Motivul e o
    greșeală pe care am făcut-o deja: `urllib` face doar potrivire pe prefix și
    ratează wildcard-urile, iar ING are `Disallow: *.pdf`. Am descărcat trei
    PDF-uri de la ING în ciuda interdicției și a trebuit să șterg 903
    observații.
    """
    from urllib.parse import urlparse
    o = urlparse(url)
    origine = f"{o.scheme}://{o.netloc}"
    if origine not in _CACHE_ROBOTS:
        R = _reguli_robots()
        reguli = R(banca_id, origine)
        try:
            # `citeste` acceptă o pagină Playwright sau un context de cereri;
            # aici îi dăm textul adus cu stiva simplă, care e suficient în
            # majoritatea cazurilor.
            import requests
            from scraper import HEADERS
            r = requests.get(origine + "/robots.txt", headers=HEADERS, timeout=15)
            reguli._parseaza(r.text if r.ok else "")
        except Exception:
            reguli._parseaza("")       # inaccesibil => fără restricții declarate
        _CACHE_ROBOTS[origine] = reguli
    return _CACHE_ROBOTS[origine].permite(url)


# ==========================================================================
# Transporturile, în ordinea cascadei
# ==========================================================================

def adu_http(url, _stare):
    """Treapta 1: stiva proprie. requests, UA care ne identifică."""
    import requests
    from scraper import HEADERS
    try:
        r = requests.get(url, headers=HEADERS, timeout=45)
    except Exception as exc:
        return None, f"{type(exc).__name__}"
    if not r.ok:
        return None, f"HTTP {r.status_code}"
    return r.content, f"HTTP 200, {len(r.content)} octeți"


def adu_playwright(url, stare):
    """Treapta 2: browser Chromium real, motorul colegului.

    Browserul se pornește o dată per rulare și se ține în `stare` — o lansare
    costă ~1 secundă, iar pe 100 de surse asta ar fi un minut aruncat.
    """
    if "browser" not in stare:
        from playwright.sync_api import sync_playwright
        stare["pw"] = sync_playwright().start()
        stare["browser"] = stare["pw"].chromium.launch(headless=True)
        stare["ctx"] = stare["browser"].new_context(user_agent=UA_BROWSER,
                                                    locale="ro-RO")
    ctx = stare["ctx"]
    # PDF-urile se iau prin contextul de cereri al browserului, nu prin
    # navigare: o navigare la un PDF deschide vizualizatorul, nu dă octeții.
    if url.lower().split("?")[0].endswith(".pdf"):
        try:
            resp = ctx.request.get(url, timeout=60000)
            if not resp.ok:
                return None, f"HTTP {resp.status}"
            date = resp.body()
            if not date.startswith(b"%PDF"):
                return None, "răspunsul nu e PDF"
            return date, f"HTTP {resp.status}, {len(date)} octeți (browser)"
        except Exception as exc:
            return None, f"{type(exc).__name__}"
    pg = ctx.new_page()
    try:
        r = pg.goto(url, wait_until="domcontentloaded", timeout=45000)
        pg.wait_for_timeout(1800)      # lăsăm conținutul randat prin JS să apară
        if r and r.status >= 400:
            return None, f"HTTP {r.status}"
        html = pg.content()
        return html.encode("utf-8"), f"HTTP {r.status if r else '?'}, randat"
    except Exception as exc:
        return None, f"{type(exc).__name__}"
    finally:
        pg.close()


def adu_llm(url, stare):
    """Treapta 3: `web_fetch` server-side, prin Anthropic.

    Cererea nu pleacă de la noi: pleacă din infrastructura Anthropic, cu
    agentul `Claude-User`, care respectă robots.txt prin construcție. Costă
    bani per apel, deci e ultima treaptă, nu prima.

    Întoarce TEXT extras, nu marcaj — deci ce iese de aici nu poate fi dat
    parserelor de tabel, care au nevoie de geometrie. Bun pentru dobânzi și
    nume de produse, nu pentru tarife în tabel.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None, "fără ANTHROPIC_API_KEY"
    if "anthropic" not in stare:
        try:
            import anthropic
            stare["anthropic"] = anthropic.Anthropic()
        except Exception as exc:
            return None, f"clientul Anthropic: {type(exc).__name__}"
    try:
        r = stare["anthropic"].messages.create(
            model=os.environ.get("MODEL", "claude-sonnet-5"),
            max_tokens=8000,
            tools=[{"type": "web_fetch_20250910", "name": "web_fetch",
                    "max_uses": 2, "allowed_domains": [url.split("/")[2]]}],
            extra_headers={"anthropic-beta": "web-fetch-2025-09-10"},
            messages=[{"role": "user", "content":
                       f"Deschide {url} cu web_fetch și întoarce textul paginii, "
                       f"integral, fără comentarii. Dacă nu se poate deschide, "
                       f"scrie exact: INACCESIBIL."}],
        )
    except Exception as exc:
        return None, f"{type(exc).__name__}"
    text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
    if not text.strip() or "INACCESIBIL" in text[:200]:
        return None, "web_fetch nu a putut deschide pagina"
    return text.encode("utf-8"), f"web_fetch, {len(text)} caractere de text"


CASCADA = [("http", adu_http), ("playwright", adu_playwright), ("llm", adu_llm)]


# ==========================================================================
# Bronze + amprenta
# ==========================================================================

def scrie_bronze(url, octeti):
    """Octeții bruți, salvați înainte de orice interpretare.

    Numele vine din URL-ul ÎNTREG (`urme.nume_din_url`), nu din ultimul
    segment. Motivul e măsurat în `urme.py`: două adrese TBI diferite au
    același nume de fișier, iar cu nume din ultimul segment al doilea document
    suprascria primul — apoi sonda de schimbări raporta o schimbare care nu
    existase.
    """
    os.makedirs(BRONZE, exist_ok=True)
    cale = cale_bronze(url)
    with open(cale, "wb") as f:
        f.write(octeti)
    return cale


def cale_bronze(url):
    """Unde stau în Bronze octeții unei surse — același nume la scriere și la
    citire, altfel reconstruirea din Bronze ar căuta alt fișier."""
    from crawler.urme import nume_din_url
    return os.path.join(BRONZE, nume_din_url(url))


def amprenta(octeti):
    """Amprentă pe OCTEȚI, nu pe valorile extrase.

    Regula e a colegului și are un motiv măsurat: între 17 și 18 septembrie,
    numărul de comisioane a scăzut de la 430 la 427. Un diff pe valori ar fi
    raportat „au dispărut trei comisioane la bănci". Nu dispăruse nimic — se
    schimbase un regex la noi. Amprenta pe octeți separă „banca a publicat
    altceva" de „noi am schimbat parserul".
    """
    import hashlib
    return hashlib.sha256(octeti).hexdigest()[:16]


def amprenta_cunoscuta(cur, id_sursa, amp):
    """Am mai văzut exact octeții ăștia la sursa asta?"""
    cur.execute("SELECT 1 FROM hashes WHERE id_sursa = %s AND hash = %s LIMIT 1",
                (id_sursa, amp))
    return cur.fetchone() is not None
