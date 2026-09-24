"""Locatoarele care își încarcă punctele prin JavaScript → `locatii`.

La Patria, lista de agenții și ATM-uri e chiar în codul paginii
(`window.branchesList`), deci extracția din Bronze o găsește. La majoritatea
băncilor, harta cere punctele separat, după încărcare (un răspuns JSON), iar
pagina descărcată nu conține nicio coordonată. Aici pagina se deschide în
Playwright, cu UA-ul echipei, și se citesc răspunsurile JSON pe care le cere
ea însăși.

Reguli:
  - doar paginile care arată a locator (descoperirea a marcat ~190 de pagini
    „de rețea", dar multe sunt help-center, comunicate, promoții, PDF-uri);
  - robots.txt verificat și pe pagină, și pe adresa fiecărui răspuns JSON;
  - Crawl-delay respectat (transport._asteapta);
  - la o bancă unde se găsesc puncte, ele înlocuiesc Overture; unde nu, rămâne
    Overture.

Rulare:
    python ingest/locatoare_js.py              # toate băncile
    python ingest/locatoare_js.py --banca bcr
"""

import argparse
import collections
import os
import re
import sys

import psycopg2

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import config                      # noqa: E402
import extractoare                 # noqa: E402
import flux                        # noqa: E402
import normalizeaza as N           # noqa: E402
import populare_initiala as P      # noqa: E402
import transport                   # noqa: E402
from crawler import UA             # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RE_LOCATOR_REAL = re.compile(
    r"retea-unitati(/cauta)?(/locatii)?/?$|agentii-si-atm|agentii(\.html)?/?$|unitati-atm/?$"
    r"|harta-agenti|/sucursale/?$|/locatii/?$|atm-locator|branch-locator|find-us|puncte-de-lucru",
    re.I)
RE_FALS = re.compile(r"help-center|press|program|faq|promoti|\.pdf|noutati|remediere|"
                     r"contactless|/en/|comunicat|/details", re.I)
MAX_PE_BANCA = 3


def candidati(cur, banca=None):
    cur.execute("""SELECT b.slug, s.sursa FROM surse s JOIN banci b ON b.id = s.id_banca
                   WHERE s.rol = 'locator' AND (%s = '' OR b.slug = %s)
                   ORDER BY b.slug, length(s.sursa)""", (banca or "", banca or ""))
    pe_banca = collections.defaultdict(list)
    for slug, url in cur.fetchall():
        if RE_LOCATOR_REAL.search(url) and not RE_FALS.search(url) \
                and len(pe_banca[slug]) < MAX_PE_BANCA:
            pe_banca[slug].append(url)
    return pe_banca


def puncte_din_pagina(url, slug, stare, raport):
    """Deschide pagina și strânge coordonatele din răspunsurile JSON + din HTML."""
    if not flux.permite(url, slug):
        raport["pagina_interzisa_robots"] += 1
        return []
    transport._asteapta(url, slug, stare)
    if "browser" not in stare:
        from playwright.sync_api import sync_playwright
        stare["pw"] = sync_playwright().start()
        stare["browser"] = stare["pw"].chromium.launch(headless=True)
        stare["ctx"] = stare["browser"].new_context(user_agent=UA, locale="ro-RO")
    corpuri = []

    def la_raspuns(r):
        try:
            if "json" not in (r.headers.get("content-type") or ""):
                return
            if not flux.permite(r.url, slug):
                raport["json_interzis_robots"] += 1
                return
            corpuri.append(r.body())
        except Exception:
            raport["json_ilizibil"] += 1

    pg = stare["ctx"].new_page()
    pg.on("response", la_raspuns)
    try:
        r = pg.goto(url, wait_until="networkidle", timeout=60000)
        verdict = transport.clasifica_raspuns(r.status if r else None, "text/html",
                                              pg.content().encode("utf-8"))
        if verdict == "BLOCAT":
            raport["pagina_blocata"] += 1
            return []
        pg.wait_for_timeout(2500)
        corpuri.append(pg.content().encode("utf-8"))
    except Exception as exc:
        raport[f"eroare_{type(exc).__name__}"] += 1
    finally:
        pg.close()
    puncte = []
    for corp in corpuri:
        p, _ = extractoare.din_locator(corp, url, slug)
        puncte.extend(p)
    raport["raspunsuri_json"] += len(corpuri) - 1
    return puncte


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--banca")
    a = ap.parse_args()
    config.incarca()
    with psycopg2.connect(N.dsn()) as conn:
        with conn.cursor() as cur:
            pe_banca = candidati(cur, a.banca)
    stare, raport = {}, collections.Counter()
    try:
        for slug, urluri in sorted(pe_banca.items()):
            unice = {}
            for url in urluri:
                for p in puncte_din_pagina(url, slug, stare, raport):
                    unice.setdefault((p["tip"], round(p["lat"], 5), round(p["lon"], 5)), p)
            puncte = list(unice.values())
            c = collections.Counter((p["tip"], p["retea"]) for p in puncte)
            print(f"  {slug:16s} {len(urluri)} pagini → {len(puncte):5d} puncte {dict(c)}")
            if puncte:
                P.scrie_locatii(puncte, raport)
    finally:
        transport.inchide(stare)
    print()
    for k in sorted(raport):
        print(f"{raport[k]:6d}  {k}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
