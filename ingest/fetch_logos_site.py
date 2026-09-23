"""Ia sigla fiecărei bănci de pe site-ul ei propriu.

De ce așa și nu prin căutare: prima încercare a folosit căutare automată pe
Wikimedia Commons și a adus sigle GREȘITE — pentru UniCredit filiala bulgară
Bulbank, pentru CEC o firmă germană cu același acronim, pentru Garanti logoul
unui turneu de tenis. O siglă greșită pe o hartă de concurență e mai rea decât
lipsa unei sigle, fiindcă nimeni nu o mai verifică.

Aici nu se caută nimic. Se citesc paginile pe care le avem deja în `surse`
pentru banca respectivă și se extrage sigla din ELE. Domeniul e al băncii, deci
nu se poate strecura altă companie.

Ordinea de preferință, de la cel mai de încredere la cel mai slab:
  1. `<img>` din header / nav cu „logo" în src, alt, class sau id
  2. `<link rel="apple-touch-icon">`  - de obicei sigla pe fundal, 180x180
  3. `<meta property="og:image">`     - uneori sigla, uneori o poză de campanie
  4. `<link rel="icon">` / favicon.ico - mic, dar e tot al băncii

Fiecare candidat se descarcă și se acceptă doar dacă răspunde 200, are un
Content-Type de imagine și trece de un prag de dimensiune. Un favicon de 16px
alb-negru e acceptat ca ultimă variantă: interfața îl afișează mic oricum.

Nu suprascrie siglele existente decât cu `--rescrie`.

Rulare:  python ingest/fetch_logos_site.py
         python ingest/fetch_logos_site.py --banca tbi
         python ingest/fetch_logos_site.py --rescrie
"""

import argparse
import collections
import hashlib
import io
import os
import re
import sys
import time
import urllib.parse

import psycopg2
import requests

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AICI))
sys.path.insert(0, AICI)
import config                      # noqa: E402
import normalizeaza as N           # noqa: E402

SCRAPING = os.path.join(os.path.expanduser("~"), "Desktop", "Scraping")
sys.path.insert(0, SCRAPING)

from bs4 import BeautifulSoup                                     # noqa: E402
from scraper import (                                             # noqa: E402
    DELAY_BETWEEN_REQUESTS, HEADERS, REQUEST_TIMEOUT, fetch_page, robots_allowed,
)

DOSAR = os.path.join(os.path.dirname(AICI), "app", "logos")

TIPURI = {
    "image/svg+xml": "svg", "image/png": "png", "image/jpeg": "jpg",
    "image/webp": "webp", "image/gif": "gif", "image/x-icon": "ico",
    "image/vnd.microsoft.icon": "ico",
}
MIN_OCTETI = 400          # sub asta e un pixel transparent sau un fișier rupt
# Peste asta nu e o siglă. Prins pe date reale: logoul Fondului de Garantare a
# Depozitelor are 1,2 MB și a fost cules de trei ori, ca siglă pentru trei
# bănci diferite.
MAX_OCTETI = 300_000
SEMN_LOGO = re.compile(r"logo|brand|sigla", re.I)

# Insigne de terți pe care băncile le pun în pagină și care NU sunt sigla lor.
# Lista e scurtă și explicită pe motive: fiecare intrare a produs o siglă
# greșită într-o rulare reală, nu e o precauție teoretică.
#   fgdb.ro  Fondul de Garantare a Depozitelor Bancare — insignă obligatorie,
#            apare la creditcoop, exim și procredit, deci ar fi dat aceeași
#            „siglă" pentru trei bănci
#   arb.ro   Asociația Română a Băncilor
TERTI = re.compile(
    r"(^|\.)(fgdb\.ro|arb\.ro|visa\.com|mastercard\.|europa\.eu|"
    r"facebook\.|linkedin\.|twitter\.|x\.com|instagram\.|youtube\.)", re.I
)


def domeniu(u):
    """Domeniul înregistrabil, aproximat prin ultimele două-trei etichete.

    `cdn.erstegroup.com` și `www.bcr.ro` sunt domenii diferite, dar amândouă
    legitime pentru BCR — de aceea diferența de domeniu e o penalizare, nu un
    refuz. Refuzate sunt doar gazdele din `TERTI`.
    """
    g = urllib.parse.urlparse(u).netloc.lower().split(":")[0]
    p = g.split(".")
    return ".".join(p[-3:]) if len(p) > 2 and len(p[-2]) <= 3 else ".".join(p[-2:])


def candidati(html, baza):
    """Candidați de siglă, în ordinea încrederii. Fiecare: (punctaj, url)."""
    soup = BeautifulSoup(html, "lxml")
    out = []

    dom_pagina = domeniu(baza)

    def adauga(u, pct):
        if not u:
            return
        a = urllib.parse.urljoin(baza, u.strip().split()[0])   # srcset -> primul
        p = urllib.parse.urlparse(a)
        if p.scheme not in ("http", "https"):
            return
        gazda = p.netloc.lower().split(":")[0]
        if TERTI.search(gazda):
            return                       # insignă de terț, nu sigla băncii
        # Pe domeniul propriu e aproape sigur sigla lui; pe alt domeniu poate
        # fi un CDN legitim (BCR folosește cdn.erstegroup.com), deci se
        # penalizează, nu se refuză.
        if domeniu(a) != dom_pagina:
            pct -= 45
        out.append((pct, urllib.parse.urlunparse(
            (p.scheme, p.netloc, p.path, "", p.query, ""))))

    # 1. imagini din header/nav cu „logo" în atribute
    zone = soup.find_all(["header", "nav"]) or [soup]
    for z in zone:
        for img in z.find_all("img"):
            atrib = " ".join(filter(None, [
                img.get("src", ""), img.get("alt", ""), img.get("id", ""),
                " ".join(img.get("class", []) or []),
            ]))
            if SEMN_LOGO.search(atrib):
                adauga(img.get("src") or img.get("data-src") or
                       (img.get("srcset") or "").split(",")[0], 100)
    # orice imagine cu „logo" în src, oriunde în pagină
    for img in soup.find_all("img"):
        if SEMN_LOGO.search(img.get("src") or ""):
            adauga(img.get("src"), 70)

    for rel, pct in (("apple-touch-icon", 60), ("apple-touch-icon-precomposed", 55),
                     ("icon", 30), ("shortcut icon", 30), ("mask-icon", 25)):
        for lk in soup.find_all("link", rel=lambda v, r=rel: v and r in
                                [x.lower() for x in (v if isinstance(v, list) else [v])]):
            adauga(lk.get("href"), pct)

    og = soup.find("meta", attrs={"property": "og:image"})
    if og:
        adauga(og.get("content"), 40)

    # dedup păstrând cel mai mare punctaj
    best = {}
    for pct, u in out:
        if u not in best or pct > best[u]:
            best[u] = pct
    return sorted(((p, u) for u, p in best.items()), reverse=True)


def descarca(url):
    """Descarcă și validează. Întoarce (octeți, extensie) sau (None, motiv)."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.RequestException as exc:
        return None, f"{exc.__class__.__name__}"
    if not r.ok:
        return None, f"HTTP {r.status_code}"
    ct = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
    ext = TIPURI.get(ct)
    if not ext:
        # unele servere nu declară tipul corect; ne uităm la conținut
        cap = r.content[:16]
        if cap.startswith(b"\x89PNG"):
            ext = "png"
        elif cap.startswith(b"\xff\xd8\xff"):
            ext = "jpg"
        elif b"<svg" in r.content[:600].lower():
            ext = "svg"
        else:
            return None, f"tip neacceptat: {ct or '?'}"
    if len(r.content) < MIN_OCTETI:
        return None, f"prea mic ({len(r.content)} octeți)"
    if len(r.content) > MAX_OCTETI:
        return None, f"prea mare pentru o siglă ({len(r.content)} octeți)"
    return r.content, ext


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--banca", help="doar o bancă (slug)")
    ap.add_argument("--rescrie", action="store_true", help="suprascrie siglele existente")
    a = ap.parse_args()

    config.incarca()
    err = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", write_through=True)
    raport = collections.Counter()
    os.makedirs(DOSAR, exist_ok=True)
    existente = {f.rsplit(".", 1)[0] for f in os.listdir(DOSAR) if "." in f}
    # Amprenta fiecărei sigle păstrate. Aceeași imagine nu poate fi sigla a
    # două bănci: dacă apare a doua oară, e o insignă comună, nu o siglă.
    # Se pornește de la siglele deja salvate, ca o rulare parțială să nu
    # accepte un duplicat al unei sigle luate într-o rulare anterioară.
    amprente = {}
    for f in os.listdir(DOSAR):
        cale = os.path.join(DOSAR, f)
        if os.path.isfile(cale):
            with open(cale, "rb") as fh:
                amprente[hashlib.sha256(fh.read()).hexdigest()] = f.rsplit(".", 1)[0]

    with psycopg2.connect(N.dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT b.slug, b.nume,
                          array_agg(s.sursa ORDER BY length(s.sursa)) AS pagini
                   FROM banci b
                   LEFT JOIN surse s ON s.id_banca = b.id AND s.tip_sursa = 'url'
                                     AND s.format = 'html'
                   WHERE (%s = '' OR b.slug = %s)
                   GROUP BY 1, 2 ORDER BY 1""",
                (a.banca or "", a.banca or ""),
            )
            banci = cur.fetchall()

    for slug, nume, pagini in banci:
        if slug in existente and not a.rescrie:
            raport["deja_are"] += 1
            continue
        pagini = [p for p in (pagini or []) if p]
        if not pagini:
            err.write(f"{slug:20s} nicio pagină în surse — nimic de citit\n")
            raport["fara_pagini"] += 1
            continue

        gasit = False
        # cea mai scurtă pagină e de regulă pagina principală, unde e sigla
        for pagina in pagini[:2]:
            stare, _m, cd = robots_allowed(pagina)
            pauza = max(DELAY_BETWEEN_REQUESTS, cd or 0)
            if stare == "disallow":
                time.sleep(pauza)
                continue
            p = fetch_page(pagina)
            time.sleep(pauza)
            if not p["ok"]:
                err.write(f"{slug:20s} {p['error'][:52]}\n")
                continue
            for pct, u in candidati(p["html"], p["final_url"] or pagina)[:6]:
                octeti, motiv = descarca(u)
                time.sleep(0.4)
                if not octeti:
                    continue
                ext = motiv
                amp = hashlib.sha256(octeti).hexdigest()
                if amp in amprente and amprente[amp] != slug:
                    err.write(f"{slug:20s} -- aceeași imagine ca la "
                              f"{amprente[amp]}: insignă comună, nu siglă\n")
                    raport["duplicat_respins"] += 1
                    continue
                cale = os.path.join(DOSAR, f"{slug}.{ext}")
                with open(cale, "wb") as f:
                    f.write(octeti)
                amprente[amp] = slug
                err.write(f"{slug:20s} OK [{pct:3d}] {len(octeti):7d} oct  {ext:4s} {u[:56]}\n")
                raport["luate"] += 1
                gasit = True
                break
            if gasit:
                break
        if not gasit:
            err.write(f"{slug:20s} niciun candidat valid de siglă\n")
            raport["fara_candidat"] += 1

    N.raporteaza(raport, sys.stderr)


if __name__ == "__main__":
    main()
