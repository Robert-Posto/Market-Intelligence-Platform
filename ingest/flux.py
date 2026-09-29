"""Traseul unei surse, ca în figura 3 din artefact — cu cele trei transporturi.

Un singur drum, aplicat la fel oricărei surse:

    robots.txt ─► transport (cascadă) ─► Bronze ─► amprentă vs. ieri
                                                        │
                            identică ──► STOP (nimic nou)
                                                        │
                                                   diferită
                                                        ▼
                                          extracție ─► normalizare ─► observations

TRANSPORTUL e în `ingest/transport.py`: requests cu UA-ul echipei, Playwright
doar pentru pagini randate în JS, STOP la blocaj. Vechea cascadă (http →
playwright → llm) trecea mai departe și după un 403, deci ocolea filtrul băncii.

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
import contextlib
import datetime
import hashlib
import io
import itertools
import json
import os
import re
import sys
import threading
import time
import unicodedata
from urllib.parse import unquote, urlparse

import psycopg2

AICI = os.path.dirname(os.path.abspath(__file__))
RADACINA = os.path.dirname(AICI)
sys.path.insert(0, RADACINA)
sys.path.insert(0, AICI)

import config                      # noqa: E402
import extractoare                 # noqa: E402
import normalizeaza as N           # noqa: E402

BRONZE = os.path.join(RADACINA, "bronze")
# Copiile robots.txt, câte una la fiecare descărcare. Fișierele vechi din
# folder (bcr.txt, ing.txt...) sunt dovezi din 23.09 și nu se ating.
DIR_ROBOTS = os.path.join(RADACINA, "date", "robots")
# Originile BLOCAT, păstrate între rulări. Doar se adaugă linii; o deblocare
# e tot o linie (DEBLOCAT), scrisă de om prin `deblocheaza`.
JURNAL_BLOCAT = os.path.join(RADACINA, "loguri", "origini_blocate.jsonl")
# Coada pe origine: un fișier-lacăt per gazdă, cu ora ultimei cereri.
DIR_COADA = os.path.join(RADACINA, "loguri", "origini")


def origine_din(url):
    o = urlparse(url)
    return f"{o.scheme}://{o.netloc}".lower()


# ==========================================================================
# robots.txt — implementarea colegului (crawler/robots.py), nu urllib
# ==========================================================================

_CACHE_ROBOTS = {}


def reguli_pentru(url, banca_id):
    """Regulile robots.txt ale originii, citite o dată, cu dovada păstrată.

    `crawler/robots.py`, nu `urllib.robotparser`: urllib ratează wildcard-urile,
    iar ING are `Disallow: *.pdf` — am descărcat trei PDF-uri ING în ciuda
    interdicției și a trebuit să șterg 903 observații.

    Fiecare descărcare lasă pe disc octeții și metadatele (`salveaza_robots`):
    până acum regulile trăiau doar în memorie, deci verdictul „interzis" nu
    putea fi arătat după rulare (Nicolae, §10.1 punctul 3).
    """
    o = urlparse(url)
    origine = f"{o.scheme}://{o.netloc}"
    if origine not in _CACHE_ROBOTS:
        import requests
        from crawler import UA
        from crawler.robots import RegulliRobots
        reguli = RegulliRobots(banca_id, origine)
        if blocat(origine):
            # Origine BLOCAT: nici robots.txt nu se mai cere. `permite` refuză
            # oricum tot pe origine.
            reguli.status = "origine BLOCAT, robots.txt necerut"
            reguli._parseaza("")
            _CACHE_ROBOTS[origine] = reguli
            return reguli
        r = eroare = None
        try:
            with coada_origine(origine):
                r = requests.get(origine + "/robots.txt", headers={"User-Agent": UA}, timeout=15)
            reguli.status = f"HTTP {r.status_code}"
            reguli.text_brut = r.text if r.ok else ""
            # RFC 9309: 4xx = fără restricții; 5xx/timeout = abatere asumată a
            # echipei, tratat ca permis (README, „Conformitate").
            reguli._parseaza(reguli.text_brut)
        except Exception as exc:
            eroare = exc
            reguli.status = f"inaccesibil ({type(exc).__name__})"
            reguli._parseaza("")
            if e_resetare(exc):
                noteaza_resetare(origine, banca_id)
        # În afara lui try: o eroare de disc nu are voie să schimbe verdictul
        # în „inaccesibil, deci permis".
        salveaza_robots(origine, banca_id, r, eroare, reguli.status)
        _CACHE_ROBOTS[origine] = reguli
    return _CACHE_ROBOTS[origine]


def salveaza_robots(origine, banca_id, r=None, eroare=None, status=""):
    """Copia unei descărcări robots.txt: octeții exact cum au venit + metadatele.

    `<gazda>_<AAAA-LL-ZZTHHMM>.txt` (corpul, byte cu byte, oricare ar fi codul:
    și o pagină 404 sau o respingere WAF e dovadă) și `.json` alături (cod,
    dată, URL-ul final, redirecturile, amprenta). La timeout nu există corp,
    rămâne doar `.json`. Deschiderea cu „x" garantează că un fișier existent
    nu se suprascrie niciodată; două descărcări în același minut primesc
    sufixul _2, _3.

    5xx și timeout-ul se tratează ca permis (abaterea asumată); aici se
    marchează `abatere: true`, ca să poată fi numărate.
    """
    from crawler import UA
    gazda = urlparse(origine).netloc.lower().replace(":", "_")
    acum = datetime.datetime.now().astimezone()
    os.makedirs(DIR_ROBOTS, exist_ok=True)
    for i in itertools.count(1):
        nume = os.path.join(DIR_ROBOTS, f"{gazda}_{acum:%Y-%m-%dT%H%M}" + (f"_{i}" if i > 1 else ""))
        try:
            meta_f = open(nume + ".json", "x", encoding="utf-8")
            break
        except FileExistsError:
            continue
    cod = r.status_code if r is not None else None
    meta = {
        "origine": origine, "banca": banca_id,
        "url_cerut": origine + "/robots.txt",
        "url_final": r.url if r is not None else None,
        "redirecturi": [h.url for h in getattr(r, "history", None) or []],
        "cod_http": cod,
        "data": acum.isoformat(timespec="seconds"),
        "content_type": r.headers.get("Content-Type") if r is not None else None,
        "eroare": f"{type(eroare).__name__}: {eroare}"[:300] if eroare is not None else None,
        "status_reguli": status,
        "abatere": cod is None or cod >= 500,
        "user_agent": UA,
    }
    if r is not None:
        corp = r.content or b""
        meta.update(octeti=len(corp), sha256=hashlib.sha256(corp).hexdigest(),
                    fisier=os.path.basename(nume) + ".txt")
        with open(nume + ".txt", "xb") as f:
            f.write(corp)
    with meta_f:
        json.dump(meta, meta_f, ensure_ascii=False, indent=1)
    if meta["abatere"]:
        sys.stderr.write(f"  robots.txt {origine}: {status} — tratat ca permis "
                         f"(abatere asumată), jurnalizat în {os.path.basename(nume)}.json\n")
    return nume


def permite(url, banca_id):
    """robots.txt permite adresa ȘI originea nu e BLOCAT.

    Decizia pe robots e aceeași ca înainte; BLOCAT e în plus: după un BLOCAT
    nu mai pleacă nicio cerere spre origine, prin niciun script care trece
    prin `flux` (Nicolae, §7.3 punctul 7).
    """
    if blocat(url):
        return False
    return reguli_pentru(url, banca_id).permite(url)


def intarziere(url, banca_id):
    """Crawl-delay cerut de origine (Patria: 5 s)."""
    return reguli_pentru(url, banca_id).delay


# ==========================================================================
# BLOCAT pe origine — în memorie pe durata rulării, în jurnal între rulări
# ==========================================================================

_BLOCATE = None                     # origine -> motiv; citit la prima folosire
_RESETARI = collections.Counter()   # resetări de conexiune, pe origine, în rularea asta


def _blocate():
    global _BLOCATE
    if _BLOCATE is None:
        _BLOCATE = {}
        try:
            with open(JURNAL_BLOCAT, encoding="utf-8") as f:
                for linie in f:
                    if not linie.strip():
                        continue
                    e = json.loads(linie)
                    if e.get("actiune") == "DEBLOCAT":
                        _BLOCATE.pop(e["origine"], None)
                    else:
                        _BLOCATE[e["origine"]] = e.get("motiv") or "BLOCAT"
        except FileNotFoundError:
            pass
    return _BLOCATE


def blocat(url):
    """Motivul, dacă originea adresei e BLOCAT; altfel None."""
    return _blocate().get(origine_din(url))


def _scrie_jurnal_blocat(inregistrare):
    os.makedirs(os.path.dirname(JURNAL_BLOCAT), exist_ok=True)
    with open(JURNAL_BLOCAT, "a", encoding="utf-8") as f:
        f.write(json.dumps(inregistrare, ensure_ascii=False) + "\n")


def marcheaza_blocat(url, motiv, banca_id=None):
    """Originea nu mai primește nicio cerere: nici în rularea asta, nici în
    următoarele, până la o deblocare decisă de om. Nu se reîncearcă pe alt
    canal (alt UA, Playwright, WebFetch, alt agent)."""
    o = origine_din(url)
    if o in _blocate():
        return
    _blocate()[o] = motiv
    _scrie_jurnal_blocat({"data": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
                          "origine": o, "actiune": "BLOCAT", "banca": banca_id, "motiv": motiv})
    sys.stderr.write(f"  BLOCAT {o}: {motiv} — fără alte cereri, fără alt canal\n")


def deblocheaza(url, motiv):
    """Decizie umană, cu motiv: jurnalul nu se editează, se adaugă o linie."""
    o = origine_din(url)
    _blocate().pop(o, None)
    _RESETARI.pop(o, None)
    _scrie_jurnal_blocat({"data": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
                          "origine": o, "actiune": "DEBLOCAT", "motiv": motiv})


def e_resetare(exc):
    """Conexiune resetată de server? În requests vine împachetată:
    ConnectionError ← urllib3 ProtocolError/MaxRetryError ← ConnectionResetError."""
    de_vazut, vazute = [exc], set()
    while de_vazut:
        e = de_vazut.pop()
        if e is None or id(e) in vazute:
            continue
        vazute.add(id(e))
        if isinstance(e, ConnectionResetError):
            return True
        de_vazut += [e.__cause__, e.__context__, getattr(e, "reason", None)]
        de_vazut += [a for a in getattr(e, "args", ()) if isinstance(a, BaseException)]
    return bool(re.search(r"ConnectionResetError|reset by peer|WinError 10054|ECONNRESET", str(exc)))


def noteaza_resetare(url, banca_id=None):
    """A doua resetare pe aceeași origine în aceeași rulare → BLOCAT.
    Întoarce True dacă originea a devenit BLOCAT."""
    o = origine_din(url)
    _RESETARI[o] += 1
    if _RESETARI[o] >= 2:
        marcheaza_blocat(o, f"conexiune resetată de {_RESETARI[o]} ori", banca_id)
        return True
    return False


# ==========================================================================
# Coada pe origine: o singură cerere odată spre o origine, și între procese
# ==========================================================================
#
# Într-un proces cererile sunt deja una după alta. Suprapunerile vin din
# procese diferite: `populare_initiala --paralel` pornește câte un proces pe
# bancă, iar BCR și BCR Locuințe cer amândouă de pe cdn.erstegroup.com;
# la fel un script pornit de mână în timp ce rulează popularea. Lacătul e al
# sistemului de operare, deci dispare odată cu procesul — nu rămâne agățat.
# În fișier stă ora ultimei cereri, ca pauza (Crawl-delay) să țină și între
# procese, nu doar în fiecare proces separat.

_TINUTE = threading.local()
ASTEPTARE_MAXIMA_COADA = 600


def _ia_lacat(f):
    termen = time.monotonic() + ASTEPTARE_MAXIMA_COADA
    while True:
        try:
            f.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except OSError:
            if time.monotonic() > termen:
                raise TimeoutError(f"coada {f.name}: ocupată de peste {ASTEPTARE_MAXIMA_COADA} s")
            time.sleep(0.2)


def _elibereaza_lacat(f):
    f.seek(0)
    if os.name == "nt":
        import msvcrt
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)


@contextlib.contextmanager
def coada_origine(url, pauza=0):
    """Rândul la o origine: așteaptă cererea în curs (din orice proces), apoi
    pauza de la sfârșitul ei, apoi lasă cererea să plece."""
    gazda = urlparse(url).netloc.lower()
    tinute = _TINUTE.__dict__.setdefault("gazde", set())
    if gazda in tinute:
        # reintrare în același fir (ex. robots.txt cerut din interiorul cozii)
        yield
        return
    os.makedirs(DIR_COADA, exist_ok=True)
    with open(os.path.join(DIR_COADA, gazda.replace(":", "_") + ".lock"), "a+b") as f:
        _ia_lacat(f)
        tinute.add(gazda)
        try:
            f.seek(0)
            try:
                ultima = float(f.read().decode("ascii") or 0)
            except ValueError:
                ultima = 0.0
            rest = ultima + pauza - time.time()
            if rest > 0:
                time.sleep(rest)
            yield
        finally:
            f.seek(0)
            f.truncate()
            f.write(repr(time.time()).encode("ascii"))
            f.flush()
            tinute.discard(gazda)
            _elibereaza_lacat(f)


# ==========================================================================
# Curățarea adreselor și excluderile — înainte de orice cerere
# ==========================================================================

# Parametri de urmărire: nu schimbă conținutul, doar spun cui i-am venit.
PARAMETRI_URMARIRE = {"gclid", "dclid", "gbraid", "wbraid", "fbclid", "msclkid",
                      "_hsenc", "_hsmi"}
PREFIXE_URMARIRE = ("utm_", "gad_", "sfmc_", "mc_")

# Linkuri de recomandare: cererea ar atribui cuiva o recomandare. Nu se cer.
RE_RECOMANDARE = re.compile(r"[?&]promotion=|mgmp|referral(?:[/?#&]|$)", re.I)
# Listele de câștigători: date personale (nume, orașe), nu ofertă.
RE_CASTIGATORI = re.compile(r"castigatori|winners", re.I)
# Onboarding: formulare de deschidere de cont / internet banking.
PREFIXE_ONBOARDING = ("online.", "banking.", "cloud.email.")
# Previzualizare: servere interne ale băncii, nepublicate.
RE_PREVIZUALIZARE = re.compile(r"^review\.|(^|[.-])staging([.-]|$)")


def curata_url(url):
    """Scoate parametrii de urmărire din query; restul adresei rămâne neatins
    (ordinea și codarea celorlalți parametri, fragmentul).

    >>> curata_url("https://x.ro/p?utm_source=fb&id=3&gclid=abc#top")
    'https://x.ro/p?id=3#top'
    """
    fara_fragment, diez, fragment = url.partition("#")
    baza, semn, query = fara_fragment.partition("?")
    if not semn:
        return url
    parti = query.split("&")
    pastrate = [p for p in parti if not _e_urmarire(p)]
    if len(pastrate) == len(parti):
        return url
    query = "&".join(pastrate)
    return baza + ("?" + query if query else "") + diez + fragment


def _e_urmarire(parametru):
    cheie = unquote(parametru.split("=", 1)[0]).strip().lower()
    return cheie in PARAMETRI_URMARIRE or cheie.startswith(PREFIXE_URMARIRE)


def _fara_diacritice(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def motiv_excludere(url):
    """De ce adresa NU se cere deloc; None dacă se poate cere.

    Funcție pură. Motivul întors ajunge în nota rezultatului (și de acolo în
    `surse.nota_extractie`), deci fiecare excludere rămâne jurnalizată.
    """
    o = urlparse(url)
    gazda = (o.hostname or "").lower()
    cale = _fara_diacritice(unquote(o.path or "")).lower()
    tot = _fara_diacritice(unquote(url)).lower()
    if RE_RECOMANDARE.search(url):
        return "exclus: link de recomandare"
    if RE_CASTIGATORI.search(tot):
        return "exclus: listă de câștigători"
    if gazda.startswith(PREFIXE_ONBOARDING) or "/aplica-online" in cale or (
            gazda.startswith("george.") and "/register" in cale):
        return f"exclus: onboarding ({gazda})"
    if RE_PREVIZUALIZARE.search(gazda):
        return f"exclus: server de previzualizare ({gazda})"
    return None


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
    nume = nume_din_url(url)
    # urme.nume_din_url pune „.pdf" la orice nume; o pagină HTML nu e PDF.
    if nume.endswith(".pdf") and not url.lower().split("?")[0].endswith(".pdf"):
        nume = nume[:-4]
    return os.path.join(BRONZE, nume)


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
