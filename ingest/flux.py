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
import io
import os
import sys
import time

import psycopg2

AICI = os.path.dirname(os.path.abspath(__file__))
RADACINA = os.path.dirname(AICI)
sys.path.insert(0, RADACINA)
sys.path.insert(0, AICI)

import config                      # noqa: E402
import extractoare                 # noqa: E402
import normalizeaza as N           # noqa: E402

BRONZE = os.path.join(RADACINA, "bronze")

# ==========================================================================
# robots.txt — implementarea colegului (crawler/robots.py), nu urllib
# ==========================================================================

_CACHE_ROBOTS = {}


def reguli_pentru(url, banca_id):
    """Regulile robots.txt ale originii, citite o dată, cu dovada păstrată.

    `crawler/robots.py`, nu `urllib.robotparser`: urllib ratează wildcard-urile,
    iar ING are `Disallow: *.pdf` — am descărcat trei PDF-uri ING în ciuda
    interdicției și a trebuit să șterg 903 observații.
    """
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
            # RFC 9309: 4xx = fără restricții; 5xx/timeout = abatere asumată a
            # echipei, tratat ca permis (README, „Conformitate").
            reguli._parseaza(reguli.text_brut)
        except Exception as exc:
            reguli.status = f"inaccesibil ({type(exc).__name__})"
            reguli._parseaza("")
        _CACHE_ROBOTS[origine] = reguli
    return _CACHE_ROBOTS[origine]


def permite(url, banca_id):
    return reguli_pentru(url, banca_id).permite(url)


def intarziere(url, banca_id):
    """Crawl-delay cerut de origine (Patria: 5 s)."""
    return reguli_pentru(url, banca_id).delay


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
