"""Descarca o singura data logo-ul fiecarei banci, local, in app/logos/.

De ce local si nu hotlink: un marker pe harta s-ar incarca de pe serverul
bancii la fiecare afisare. Descarcat o data, nu mai trimitem trafic catre
competitori si harta functioneaza si offline.

Ordinea de preferinta pe fiecare sit: apple-touch-icon (cel mai mare si mai
curat), apoi <link rel=icon>, apoi og:image, apoi /favicon.ico. Daca nimic nu
merge, banca rămâne fara logo si harta foloseste un marker generat cu
inițiale - se raporteaza explicit, nu se ascunde.

User-Agent onest, o cerere per banca, delay intre ele.
"""

import io
import os
import sys
import time
import urllib.parse

import requests
from bs4 import BeautifulSoup

AICI = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.join(os.path.dirname(AICI), "app", "logos")

USER_AGENT = (
    "LibraBank-MarketIntel-Test/0.1 "
    "(test intern, doar resurse publice; contact: robert.postolache@librabank.ro)"
)
HEADERS = {"User-Agent": USER_AGENT}
DELAY = 1.5

# slug din `banci` -> pagina de start
SITE = {
    "bcr": "https://www.bcr.ro/",
    "brd": "https://www.brd.ro/",
    "banca-transilvania": "https://www.bancatransilvania.ro/",
    "raiffeisen": "https://www.raiffeisen.ro/",
    "ing": "https://ing.ro/",
    "unicredit": "https://www.unicredit.ro/",
    "cec": "https://www.cec.ro/",
    "garanti": "https://www.garantibbva.ro/",
    "libra": "https://www.librabank.ro/",
    "patria": "https://www.patriabank.ro/",
    "salt": "https://salt.bank/",
}

EXT_PERMISE = {
    "image/png": ".png", "image/x-icon": ".ico", "image/vnd.microsoft.icon": ".ico",
    "image/svg+xml": ".svg", "image/jpeg": ".jpg", "image/webp": ".webp",
}


def candidati(html, baza):
    """URL-uri de logo, in ordinea preferintei."""
    soup = BeautifulSoup(html, "lxml")
    gasite = []

    def adauga(href):
        if href:
            gasite.append(urllib.parse.urljoin(baza, href))

    for rel in ("apple-touch-icon", "apple-touch-icon-precomposed"):
        for tag in soup.find_all("link", rel=lambda v: v and rel in " ".join(v).lower()):
            adauga(tag.get("href"))
    for tag in soup.find_all("link", rel=lambda v: v and "icon" in " ".join(v).lower()):
        adauga(tag.get("href"))
    og = soup.find("meta", attrs={"property": "og:image"})
    if og:
        adauga(og.get("content"))
    adauga("/favicon.ico")
    # pastreaza ordinea, fara duplicate
    vazute, ordonate = set(), []
    for u in gasite:
        if u not in vazute:
            vazute.add(u)
            ordonate.append(u)
    return ordonate


def main():
    err = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
    os.makedirs(DEST, exist_ok=True)
    reusite, ratate = [], []

    for slug, url in SITE.items():
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
        except Exception as exc:
            ratate.append((slug, f"pagina: {exc.__class__.__name__}"))
            time.sleep(DELAY)
            continue

        salvat = None
        for cand in candidati(r.text, r.url)[:6]:
            try:
                ir = requests.get(cand, headers=HEADERS, timeout=15)
                ir.raise_for_status()
            except Exception:
                continue
            tip = (ir.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            ext = EXT_PERMISE.get(tip)
            if not ext or len(ir.content) < 200:
                continue
            cale = os.path.join(DEST, slug + ext)
            with open(cale, "wb") as f:
                f.write(ir.content)
            salvat = (os.path.basename(cale), len(ir.content), cand)
            break

        if salvat:
            reusite.append((slug,) + salvat)
            err.write(f"OK    {slug:20s} {salvat[0]:16s} {salvat[1]:>7d}b\n")
        else:
            ratate.append((slug, "niciun candidat valid"))
            err.write(f"RATAT {slug:20s} niciun candidat valid\n")
        time.sleep(DELAY)

    err.write(f"\n{len(reusite)} logo-uri salvate, {len(ratate)} ratate\n")
    for slug, motiv in ratate:
        err.write(f"  fara logo: {slug} ({motiv})\n")
    err.flush()


if __name__ == "__main__":
    main()
