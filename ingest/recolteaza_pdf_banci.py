"""Recoltează linkurile de PDF de pe pagina de tarife a fiecărei bănci.

Problema pe care o rezolvă: la BCR, „Administrarea contului (EURO)" vine din
`Document-de-informare-cu-privire-la-comisioane-cont-EUR_19.06.2024.pdf`, dar
documentul nu se poate deschide — pachetul sursă reține doar calea locală, nu
URL-ul de descărcare, iar discovery-ul LLM a găsit doar 40 de URL-uri de PDF în
toată piața, din care 9 s-au potrivit exact. Restul valorilor primeau doar un
link către pagina generală de comisioane a băncii, ceea ce nu e documentul.

Ce face: pentru fiecare bancă ia pagina ei de publicare (`banci.pagina_documente`,
aleasă anterior) și paginile de tip `hub`, citește TOATE linkurile care se termină
în `.pdf` și le potrivește cu numele documentelor locale. Potrivirea e pe numele
normalizat, exact ca la `leaga_url_documente.py`: prefixul de amprentă scos,
punctuație ignorată, URL-decodat.

Nu ghicește adrese și nu caută pe internet. Citește doar pagini pe care le avem
deja în `surse`, iar un link se acceptă numai dacă numele fișierului se
potrivește peste prag. Un link greșit ar trimite la alt document decât cifra,
adică opusul unei dovezi.

Politețea e cea a stivei proprii: robots.txt, User-Agent onest, delay.

Rulare:  python ingest/recolteaza_pdf_banci.py
         python ingest/recolteaza_pdf_banci.py --banca bcr
         python ingest/recolteaza_pdf_banci.py --prag 0.90
"""

import argparse
import collections
import difflib
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
from bs4 import BeautifulSoup                                     # noqa: E402
from scraper import (                                             # noqa: E402
    DELAY_BETWEEN_REQUESTS, fetch_page, robots_allowed,
)

# Acelasi prag ca la potrivirea document<->URL descoperit, si pentru acelasi
# motiv masurat: la 0.85, `Ghid_tarife_comisioane.pdf` se lega la
# `Ghid_dobanzi_si_comisioane_credite.pdf`, alt document.
PRAG = 0.95
MAX_PAGINI = 4        # per banca: pagina de publicare + hub-urile

# Un PDF de pe pagina unei banci e candidat de document de TARIFE doar daca
# numele sau textul linkului o spune. Fara filtrul asta s-ar inregistra tot:
# pe pagina BCR sunt 204 PDF-uri, din care majoritatea sunt formulare de
# cerere, rapoarte anuale si politici de cookie-uri. `comisio`, nu `comision`:
# „comisioane" NU contine „comision".
RE_TARIF = re.compile(
    r"comisio|tarif|taxe|lista[-_ ]?de[-_ ]?preturi|pret|fee|pricing|"
    r"dobanzi|informare", re.I
)
MAX_INREGISTRATE = 12      # per banca, ca sa nu umplem inventarul cu zgomot


def norm(s):
    s = urllib.parse.unquote(os.path.basename(str(s))).lower()
    s = re.sub(r"^[0-9a-f]{8}_", "", s)          # prefixul de amprenta din pachet
    return re.sub(r"[^a-z0-9]+", "", s.replace(".pdf", ""))


def pdf_uri_din(html, baza):
    gasite = {}
    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        u = urllib.parse.urljoin(baza, a["href"].strip())
        p = urllib.parse.urlparse(u)
        if p.scheme not in ("http", "https"):
            continue
        if not urllib.parse.unquote(p.path).lower().endswith(".pdf"):
            continue
        curat = urllib.parse.urlunparse((p.scheme, p.netloc, p.path, "", "", ""))
        gasite[curat] = a.get_text(" ", strip=True)[:90]
    return gasite


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--banca", help="doar o bancă (slug)")
    ap.add_argument("--prag", type=float, default=PRAG)
    a = ap.parse_args()

    config.incarca()
    err = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", write_through=True)
    raport = collections.Counter()

    with psycopg2.connect(N.dsn()) as conn:
        with conn.cursor() as cur:
            # documentele care AU nevoie: fara URL propriu
            cur.execute(
                """SELECT b.slug, s.id, s.sursa,
                          (SELECT count(*)::int FROM observations o WHERE o.id_sursa = s.id)
                   FROM surse s JOIN banci b ON b.id = s.id_banca
                   WHERE s.tip_sursa = 'document' AND s.url_public IS NULL
                     AND (%s = '' OR b.slug = %s)
                   ORDER BY 1""",
                (a.banca or "", a.banca or ""),
            )
            lipsa = collections.defaultdict(list)
            for slug, sid, cale, nobs in cur.fetchall():
                lipsa[slug].append((sid, cale, nobs))

            # de unde citim: pagina de publicare, apoi hub-urile
            cur.execute(
                """SELECT b.slug, x.u FROM banci b
                   CROSS JOIN LATERAL (
                     SELECT b.pagina_documente AS u WHERE b.pagina_documente IS NOT NULL
                     UNION
                     SELECT s.sursa FROM surse s
                      WHERE s.id_banca = b.id AND s.tip_sursa = 'url'
                        AND s.format = 'html' AND s.rol IN ('hub', 'conditii')
                   ) x
                   WHERE (%s = '' OR b.slug = %s)""",
                (a.banca or "", a.banca or ""),
            )
            de_citit = collections.defaultdict(list)
            for slug, u in cur.fetchall():
                de_citit[slug].append(u)

    # Se vizitează TOATE băncile care au pagini de citit, nu doar cele cu
    # documente nelegate. Altfel o bancă fără niciun PDF în bază (ING, Patria,
    # Nexent) nu era nici măcar deschisă — deci nu avea cum să capete vreodată
    # un document de tarife.
    toate = sorted(set(lipsa) | set(de_citit))
    err.write(f"{len(toate)} bănci de vizitat "
              f"({len(lipsa)} cu documente fără URL propriu)\n\n")
    legaturi = []

    for slug in toate:
        docs = lipsa.get(slug, [])
        pagini = de_citit.get(slug, [])[:MAX_PAGINI]
        if not pagini:
            err.write(f"{slug:14s} {len(docs)} documente · nicio pagină de citit\n")
            raport["banci_fara_pagina"] += 1
            continue

        pdfuri = {}
        for u in pagini:
            stare, _m, cd = robots_allowed(u)
            pauza = max(DELAY_BETWEEN_REQUESTS, cd or 0)
            if stare == "disallow":
                time.sleep(pauza)
                continue
            p = fetch_page(u)
            time.sleep(pauza)
            if p["ok"]:
                pdfuri.update(pdf_uri_din(p["html"], p["final_url"] or u))

        # Înregistrăm PDF-urile care ARATĂ ca documente de tarife, ca surse
        # noi. Potrivirea de mai jos leagă documentele pe care le avem deja;
        # asta adaugă documentele pe care nu le-am avut niciodată — singurul
        # mod în care o bancă fără nicio extracție de PDF (ING, Patria,
        # Nexent) ajunge să aibă comisioane în bază.
        noi = []
        for u, text in sorted(pdfuri.items()):
            eticheta = urllib.parse.unquote(os.path.basename(
                urllib.parse.urlparse(u).path)) + " " + (text or "")
            if RE_TARIF.search(eticheta):
                noi.append(u)
        noi = noi[:MAX_INREGISTRATE]
        if noi:
            with psycopg2.connect(N.dsn()) as c2:
                with c2.cursor() as cur2:
                    for u in noi:
                        cur2.execute(
                            """INSERT INTO surse (id_banca, tip_sursa, sursa, rol,
                                                  format, metoda, frecventa, status)
                               SELECT b.id, 'url', %s, 'conditii', 'pdf', 'http',
                                      'lunar', 'activ'
                               FROM banci b WHERE b.slug = %s
                               ON CONFLICT DO NOTHING""",
                            (u, slug),
                        )
                        raport["pdf_uri_inregistrate"] += cur2.rowcount

        gasite_aici = 0
        for sid, cale, nobs in docs:
            n = norm(cale)
            best, scor = None, 0.0
            for u in pdfuri:
                r = difflib.SequenceMatcher(None, n, norm(u)).ratio()
                if r > scor:
                    best, scor = u, r
            if best and scor >= a.prag:
                legaturi.append((sid, best))
                gasite_aici += 1
                raport["documente_legate"] += 1
                raport["observatii_acoperite"] += nobs
                err.write(f"  OK {scor:.2f}  {os.path.basename(cale)[:46]:48s} -> {best[:56]}\n")
        err.write(f"{slug:14s} {len(docs)} documente · {len(pdfuri)} PDF-uri pe pagini · "
                  f"{gasite_aici} legate\n")
        raport["pdfuri_vazute"] += len(pdfuri)

    if legaturi:
        with psycopg2.connect(N.dsn()) as conn:
            with conn.cursor() as cur:
                psycopg2.extras = __import__("psycopg2.extras", fromlist=["extras"])
                for sid, u in legaturi:
                    cur.execute("UPDATE surse SET url_public = %s WHERE id = %s", (u, sid))

    err.write(f"\n{raport['documente_legate']} documente au acum URL propriu, "
              f"acoperind {raport['observatii_acoperite']} observații\n")
    N.raporteaza(raport, sys.stderr)


if __name__ == "__main__":
    main()
