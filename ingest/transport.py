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

Înainte de ORICE cerere (adresa de plecare și fiecare pas de redirect),
adresa se curăță de parametrii de urmărire (`flux.curata_url`), apoi:

    EXCLUS          câștigători, onboarding, previzualizare, recomandare
                    (`flux.motiv_excludere`) → nu se cere, motivul în notă
    BLOCAT          originea e BLOCAT (în rularea asta sau din jurnal) → nu se cere
    ROBOTS          robots.txt interzice → nu se cere
    REDIRECTURI     peste MAX_PASI_REDIRECT redirecturi → STOP

Originea devine BLOCAT la a doua conexiune resetată, la o pagină de WAF sau
la 429; de atunci nu mai primește nicio cerere, pe niciun canal. Cererile spre
aceeași origine stau la coadă (`flux.coada_origine`), și între procese.

Playwright folosește `crawler.UA`, nu un UA de Chrome.
"""

import collections
import re
import time
from urllib.parse import urljoin, urlparse

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
    """Crawl-delay per origine, doar în proces (îl folosește locatoare_js).
    `adu` stă în schimb la coada originii (`flux.coada_origine`), care ține
    pauza și între procese."""
    o = urlparse(url).netloc
    pauza = _pauza(url, banca_id)
    ultima = stare.setdefault("ultima_cerere", {}).get(o, 0)
    rest = ultima + pauza - time.monotonic()
    if rest > 0:
        time.sleep(rest)
    stare["ultima_cerere"][o] = time.monotonic()


MAX_PASI_REDIRECT = 5


def _pauza(url, banca_id):
    """Crawl-delay per origine. Patria cere 5 s; bucla veche dormea 1,5 s fix."""
    return max(flux.intarziere(url, banca_id), 1.5)


def _refuz(url, banca_id, pas_redirect=False):
    """Ce oprește o adresă ÎNAINTE de cerere; None dacă se poate cere.

    Aceleași trei verificări la adresa de plecare și la fiecare pas al unui
    redirect: excluderile (câștigători, onboarding, previzualizare,
    recomandări), originea BLOCAT, robots.txt.
    """
    motiv = flux.motiv_excludere(url)
    if motiv:
        return Rezultat("EXCLUS", None, url, None, motiv)
    motiv = flux.blocat(url)
    if motiv:
        return Rezultat("BLOCAT", None, url, None, f"origine BLOCAT (jurnal): {motiv}")
    if not flux.permite(url, banca_id):
        nota = f"redirect spre adresă interzisă: {url}" if pas_redirect else "interzis de robots.txt"
        return Rezultat("ROBOTS", None, url, None, nota[:300])
    return None


def _http(url, banca_id):
    """GET fără redirecturi automate: fiecare `Location` trece prin `_refuz`
    ÎNAINTE de cererea următoare, cu cel mult MAX_PASI_REDIRECT pași.

    Înainte, requests urma redirecturile orb și robots se verifica doar pe
    adresa finală, după descărcare (Nicolae, §10.1 punctul 4): un pas
    intermediar interzis era deja cerut.

    Întoarce (status, tip, corp, url_final, nota, refuz); `refuz` e un
    Rezultat când un pas a fost oprit sau originea a devenit BLOCAT.
    """
    import requests
    for _pas in range(MAX_PASI_REDIRECT + 1):
        try:
            with flux.coada_origine(url, _pauza(url, banca_id)):
                r = requests.get(url, headers=ANTETE, timeout=45, allow_redirects=False)
        except requests.RequestException as exc:
            if flux.e_resetare(exc) and flux.noteaza_resetare(url, banca_id):
                return None, "", b"", url, type(exc).__name__, Rezultat(
                    "BLOCAT", None, url, "http",
                    f"conexiune resetată de două ori ({type(exc).__name__}): origine BLOCAT")
            return None, "", b"", url, type(exc).__name__, None
        if not r.is_redirect:
            return (r.status_code, r.headers.get("Content-Type", ""), r.content, url,
                    f"HTTP {r.status_code}", None)
        urmatorul = flux.curata_url(urljoin(url, r.headers["Location"]))
        refuz = _refuz(urmatorul, banca_id, pas_redirect=True)
        if refuz:
            return None, "", b"", urmatorul, refuz.nota, refuz
        url = urmatorul
    nota = f"peste {MAX_PASI_REDIRECT} redirecturi"
    return None, "", b"", url, nota, Rezultat("REDIRECTURI", None, url, "http", nota)


def _garda_navigare(banca_id, refuzuri):
    """Playwright urmează singur redirecturile; garda oprește în browser orice
    navigare a cadrului principal pe care `_refuz` n-o permite."""
    def garda(route):
        req = route.request
        if req.is_navigation_request() and req.frame.parent_frame is None:
            refuz = _refuz(flux.curata_url(req.url), banca_id, pas_redirect=True)
            if refuz:
                refuzuri.append(refuz)
                return route.abort("blockedbyclient")
        return route.continue_()
    return garda


def _playwright(url, banca_id, stare):
    if "browser" not in stare:
        from playwright.sync_api import sync_playwright
        stare["pw"] = sync_playwright().start()
        stare["browser"] = stare["pw"].chromium.launch(headless=True)
        stare["ctx"] = stare["browser"].new_context(user_agent=UA, locale="ro-RO")
    refuzuri = []
    pg = stare["ctx"].new_page()
    try:
        pg.route("**/*", _garda_navigare(banca_id, refuzuri))
        with flux.coada_origine(url, _pauza(url, banca_id)):
            r = pg.goto(url, wait_until="domcontentloaded", timeout=45000)
            status = r.status if r else None
            # statusul se citește ÎNAINTE de așteptare: după, pagina poate fi alta
            pg.wait_for_timeout(1800)
            continut = pg.content().encode("utf-8")
        if refuzuri:
            return None, "", b"", refuzuri[0].url_final, refuzuri[0].nota, refuzuri[0]
        return status, "text/html", continut, pg.url, f"HTTP {status}, randat", None
    except Exception as exc:
        if refuzuri:
            return None, "", b"", refuzuri[0].url_final, refuzuri[0].nota, refuzuri[0]
        return None, "", b"", url, type(exc).__name__, None
    finally:
        pg.close()


def inchide(stare):
    if "browser" in stare:
        stare["browser"].close()
        stare["pw"].stop()


def adu(url, banca_id, stare, _adancime=0):
    url = flux.curata_url(url)
    refuz = _refuz(url, banca_id)
    if refuz:
        return refuz
    status, tip, corp, final, nota, refuz = _http(url, banca_id)
    if refuz:
        return refuz
    verdict = clasifica_raspuns(status, tip, corp)
    transport = "http"
    nota = _actualizeaza_nota_blocat(verdict, status, corp, nota)

    if verdict == "REINCEARCA":
        time.sleep(10)
        status, tip, corp, final, nota, refuz = _http(url, banca_id)
        if refuz:
            return refuz
        verdict = clasifica_raspuns(status, tip, corp)
        nota = _actualizeaza_nota_blocat(verdict, status, corp, nota)
    if verdict == "JS" and not url.lower().split("?")[0].endswith(".pdf"):
        status, tip, corp, final, nota, refuz = _playwright(url, banca_id, stare)
        if refuz:
            return refuz._replace(transport="playwright")
        verdict, transport = clasifica_raspuns(status, tip, corp), "playwright"
        nota = _actualizeaza_nota_blocat(verdict, status, corp, nota)
        if verdict == "JS":          # tot schelet și în browser: nimic de citit
            verdict = "OK"
    if verdict == "REDIRECT_SERIALIZAT" and _adancime < 2:
        m = re.search(rb"^Location:\s*(\S+)", corp, re.M | re.I)
        if m:
            return adu(urljoin(final, m.group(1).decode("latin-1")), banca_id, stare, _adancime + 1)
        verdict = "REINCEARCA"
    if verdict == "BLOCAT" and (status == 429 or _evidenta_blocaj(status, corp)):
        # Pagina de WAF (sau „prea multe cereri") refuză originea, nu doar
        # adresa: restul cererilor spre ea s-ar lovi de același filtru — așa
        # s-au adunat cele 4 × 403 din testul de marketing. Un 403 simplu, fără
        # semnătură de WAF, rămâne pe sursă, ca înainte.
        flux.marcheaza_blocat(final, nota, banca_id)
    # Robots se verifică și pe adresa FINALĂ: la http fiecare pas e verificat
    # deja în `_http`; rămâne pentru Playwright (redirecturi din JavaScript).
    if verdict == "OK" and final != url and not flux.permite(final, banca_id):
        return Rezultat("ROBOTS", None, final, transport, "redirect spre adresă interzisă")
    return Rezultat(verdict, corp if verdict == "OK" else None, final, transport, nota)
