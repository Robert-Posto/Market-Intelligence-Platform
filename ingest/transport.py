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
# Peste atâta text vizibil, o potrivire cu tiparele de blocaj e un cuvânt din
# pagina reală (reCAPTCHA pe un formular), nu o pagină de blocaj.
TEXT_MAXIM_BLOCAJ = 1500
ANTETE = {"User-Agent": UA, "Accept-Language": "ro,en;q=0.8"}


def _text_vizibil(corp):
    fara_script = re.sub(rb"<script.*?</script>|<style.*?</style>", b"", corp, flags=re.S | re.I)
    return RE_TAGURI.sub(b" ", fara_script).strip()


def _evidenta_blocaj(status, corp):
    """Extrage dovada textului de blocaj din corp cand pagina e detectata ca blocata."""
    corp = corp or b""
    m = RE_BLOCAJ.search(corp[:5000])
    if m:
        try:
            return m.group(0).decode('latin-1')
        except:
            return m.group(0).decode('utf-8', errors='replace')
    return None


def _actualizeaza_nota_blocat(verdict, status, corp, nota):
    """Actualizeaza nota cu dovada de blocaj daca verdictul e BLOCAT din continut."""
    if verdict == "BLOCAT" and status not in (401, 403, 407, 429, 451):
        evidenta = _evidenta_blocaj(status, corp)
        if evidenta:
            return f'HTTP {status}: pagina de blocaj - {evidenta}'
    return nota


def clasifica_raspuns(status, tip_continut, corp):
    corp = corp or b""
    if status in (401, 403, 407, 429, 451):
        return "BLOCAT"
    if status in (404, 410):
        return "DISPARUT"
    if status is not None and 500 <= status < 600 and RE_BLOCAJ.search(corp[:5000]):
        return "BLOCAT"
    if status is None or status >= 500:
        return "REINCEARCA"
    if corp.startswith(b"HTTP/"):
        return "REDIRECT_SERIALIZAT"
    if corp.startswith(b"%PDF"):
        return "OK"
    # O pagină de blocaj servită cu 200 e aproape goală. Fără pragul ăsta,
    # cuvântul „captcha" din formularul de contact al paginii Vista (23.09)
    # marca toată banca drept blocată.
    if RE_BLOCAJ.search(corp[:5000]) and len(_text_vizibil(corp)) < TEXT_MAXIM_BLOCAJ:
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
    nota = _actualizeaza_nota_blocat(verdict, status, corp, nota)

    if verdict == "REINCEARCA":
        time.sleep(10)
        status, tip, corp, final, nota = _http(url)
        verdict = clasifica_raspuns(status, tip, corp)
        nota = _actualizeaza_nota_blocat(verdict, status, corp, nota)
    if verdict == "JS" and not url.lower().split("?")[0].endswith(".pdf"):
        _asteapta(url, banca_id, stare)
        status, tip, corp, final, nota = _playwright(url, stare)
        verdict, transport = clasifica_raspuns(status, tip, corp), "playwright"
        nota = _actualizeaza_nota_blocat(verdict, status, corp, nota)
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
