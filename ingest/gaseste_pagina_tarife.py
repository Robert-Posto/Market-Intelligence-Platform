"""Caută pagina de tarife pe site-ul băncii, pentru băncile la care lipsește.

Context: după potrivirea exactă document↔URL (9 din 68) și după alegerea
paginii de publicare din URL-urile deja descoperite (16 bănci), rămâneau
1.192 de observații fără niciun link — 29% din pagina 2.1 — concentrate în
5 bănci și 9 documente: brd (500), brci (404), techventures (260), salt (221),
bcr-locuinte (24).

Cauza: pentru ele discovery-ul nu a găsit nicio pagină de tarife, iar singurul
candidat era pagina principală. O pagină principală nu e „de unde se publică
documentul", deci a fost respinsă de pragul minim — corect.

Ce face scriptul, și de ce așa: NU ghicește adrese. Ia o pagină pe care o avem
deja pentru bancă (hub sau pagina principală), citește linkurile din ea și
păstrează doar pe cele care arată ca o pagină de tarife — după textul ancorei
SAU după adresă. Apoi verifică fiecare candidat cu o cerere reală și îl
acceptă doar dacă răspunde 200 ȘI conținutul menționează tarife/comisioane.
Așa, orice pagină adăugată e o afirmație verificată, nu o presupunere despre
cum își organizează banca site-ul.

Politețea e cea a stivei proprii: robots.txt, User-Agent onest, delay.

Rulare:  python ingest/gaseste_pagina_tarife.py
         python ingest/gaseste_pagina_tarife.py --banca brd
"""

import argparse
import collections
import io
import os
import re
import sys
import time
import urllib.parse

import psycopg2

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AICI))
sys.path.insert(0, AICI)
import config                      # noqa: E402
import normalizeaza as N           # noqa: E402

SCRAPING = os.path.join(os.path.expanduser("~"), "Desktop", "Scraping")
sys.path.insert(0, SCRAPING)

from bs4 import BeautifulSoup                                     # noqa: E402
from scraper import (                                             # noqa: E402
    DELAY_BETWEEN_REQUESTS, fetch_page, robots_allowed, strip_diacritics,
)

# Ce arată ca o pagină de tarife. `comisio`, nu `comision`: „comisioane" NU
# conține „comision" — după `comisio` vine `a`, nu `n`.
SEMNE = re.compile(
    r"tarif|comisio|taxe|lista[-_ ]?de[-_ ]?preturi|documente|"
    r"informatii[-_ ]?utile|fees|pricing", re.I
)

# Confirmarea din conținutul paginii: dacă nu apar cuvintele astea, pagina nu e
# ce pretinde linkul. Fără verificarea asta, un link de meniu numit „Documente"
# care duce la rapoarte anuale ar fi acceptat.
CONFIRMARE = re.compile(r"comisio|tarif|taxe|pret", re.I)

MAX_CANDIDATI = 6      # per bancă, ca să nu batem site-ul


def curata(url, baza):
    """URL absolut, fără fragment și fără parametri de urmărire."""
    u = urllib.parse.urljoin(baza, (url or "").strip())
    p = urllib.parse.urlparse(u)
    if p.scheme not in ("http", "https"):
        return None
    return urllib.parse.urlunparse((p.scheme, p.netloc, p.path, "", "", ""))


def candidati_din(html, baza, gazda):
    """Linkuri care arată ca pagini de tarife, ordonate după cât de convingătoare.

    Se punctează atât textul ancorei cât și adresa: unele bănci pun „Tarife și
    comisioane" pe un link cu adresă opacă, altele invers.
    """
    soup = BeautifulSoup(html, "lxml")
    gasite = {}
    for a in soup.find_all("a", href=True):
        u = curata(a["href"], baza)
        if not u:
            continue
        # Se rămâne pe domeniul băncii; un link extern nu e pagina ei de tarife.
        if urllib.parse.urlparse(u).netloc.replace("www.", "") not in gazda:
            continue
        if u.lower().endswith(".pdf"):
            continue          # un PDF e alt document, nu pagina de publicare
        text = strip_diacritics(a.get_text(" ", strip=True))[:90]
        cale = strip_diacritics(urllib.parse.unquote(urllib.parse.urlparse(u).path))
        pct = 0
        if SEMNE.search(text):
            pct += 2          # textul ancorei e semnalul mai bun
        if SEMNE.search(cale):
            pct += 1
        if pct and (u not in gasite or pct > gasite[u][0]):
            gasite[u] = (pct, text)
    return sorted(((p, t, u) for u, (p, t) in gasite.items()), reverse=True)


def verifica(url, err):
    """200 + conținut care confirmă. Altfel nu se acceptă."""
    stare, _motiv, cd = robots_allowed(url)
    if stare == "disallow":
        return False, "blocat de robots.txt", max(DELAY_BETWEEN_REQUESTS, cd or 0)
    pagina = fetch_page(url)
    pauza = max(DELAY_BETWEEN_REQUESTS, cd or 0)
    if not pagina["ok"]:
        return False, pagina["error"], pauza
    text = BeautifulSoup(pagina["html"], "lxml").get_text(" ", strip=True)
    if not CONFIRMARE.search(strip_diacritics(text[:20000])):
        return False, "pagina nu menționează tarife/comisioane", pauza
    return True, "confirmat: 200 + conținut despre tarife", pauza


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--banca", help="doar o bancă (slug)")
    a = ap.parse_args()

    config.incarca()
    err = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", write_through=True)
    raport = collections.Counter()

    with psycopg2.connect(N.dsn()) as conn:
        with conn.cursor() as cur:
            # Băncile care CHIAR au nevoie: au documente fără link și nicio
            # pagină de publicare aleasă.
            cur.execute(
                """SELECT b.slug, b.id, count(DISTINCT s.sursa)::int AS documente,
                          count(o.id)::int AS observatii
                   FROM banci b
                   JOIN surse s ON s.id_banca = b.id AND s.tip_sursa = 'document'
                                AND s.url_public IS NULL
                   LEFT JOIN observations o ON o.id_sursa = s.id
                   WHERE b.pagina_documente IS NULL AND (%s = '' OR b.slug = %s)
                   GROUP BY 1, 2 ORDER BY observatii DESC""",
                (a.banca or "", a.banca or ""),
            )
            nevoie = cur.fetchall()

            # Punctele de plecare: paginile pe care le avem deja pentru bancă.
            cur.execute(
                """SELECT b.slug, s.sursa, s.rol
                   FROM surse s JOIN banci b ON b.id = s.id_banca
                   WHERE s.tip_sursa = 'url' AND s.format = 'html'
                   ORDER BY CASE s.rol WHEN 'hub' THEN 0 WHEN 'conditii' THEN 1 ELSE 2 END,
                            length(s.sursa)"""
            )
            plecare = collections.defaultdict(list)
            for slug, url, rol in cur.fetchall():
                plecare[slug].append(url)

    err.write(f"{len(nevoie)} bănci au documente fără link și nicio pagină de publicare\n\n")
    gasite = {}

    for slug, id_banca, ndoc, nobs in nevoie:
        gazda = {urllib.parse.urlparse(u).netloc.replace("www.", "")
                 for u in plecare.get(slug, [])}
        err.write(f"{slug:14s} {ndoc} documente, {nobs} observații\n")
        if not plecare.get(slug):
            err.write("  fără nicio pagină de plecare — nimic de explorat\n")
            raport["fara_punct_de_plecare"] += 1
            continue

        toti = []
        for start in plecare[slug][:2]:          # cel mult două pagini de plecare
            p = fetch_page(start)
            time.sleep(DELAY_BETWEEN_REQUESTS)
            if not p["ok"]:
                err.write(f"  {start[:52]} -> {p['error']}\n")
                continue
            toti += candidati_din(p["html"], p["final_url"] or start, gazda)
        # dedup păstrând punctajul maxim
        unic = {}
        for pct, text, u in toti:
            if u not in unic or pct > unic[u][0]:
                unic[u] = (pct, text)
        ordonat = sorted(((p, t, u) for u, (p, t) in unic.items()), reverse=True)

        if not ordonat:
            err.write("  niciun link care să arate ca pagină de tarife\n")
            raport["fara_candidati"] += 1
            continue

        acceptat = None
        for pct, text, u in ordonat[:MAX_CANDIDATI]:
            ok, motiv, pauza = verifica(u, err)
            err.write(f"  {'DA ' if ok else '-- '} [{pct}] {u[:58]:60s} {motiv[:44]}\n")
            time.sleep(pauza)
            if ok:
                acceptat = (u, f"găsit pe site-ul băncii, link «{text[:40]}», {motiv}")
                break
        if acceptat:
            gasite[slug] = acceptat
            raport["pagini_gasite"] += 1
            raport["observatii_acoperite"] += nobs
        else:
            raport["candidati_toti_respinsi"] += 1
        err.write("\n")

    # Scrierea: pagina devine și sursă (ca să existe în inventar) și pagina de
    # publicare a băncii.
    if gasite:
        with psycopg2.connect(N.dsn()) as conn:
            with conn.cursor() as cur:
                for slug, (url, motiv) in sorted(gasite.items()):
                    cur.execute(
                        """INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format,
                                              metoda, frecventa, status)
                           SELECT b.id, 'url', %s, 'conditii', 'html', 'http', 'lunar', 'activ'
                           FROM banci b WHERE b.slug = %s
                           ON CONFLICT DO NOTHING""",
                        (url, slug),
                    )
                    cur.execute(
                        """UPDATE banci SET pagina_documente = %s,
                                            pagina_documente_motiv = %s
                           WHERE slug = %s""",
                        (url, motiv, slug),
                    )

    err.write("=== GĂSITE ===\n")
    for slug, (url, motiv) in sorted(gasite.items()):
        err.write(f"  {slug:14s} {url}\n")
    N.raporteaza(raport, sys.stderr)


if __name__ == "__main__":
    main()
