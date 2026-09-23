"""Descarca logourile bancilor din Wikimedia Commons / Wikipedia.

De ce nu de pe site-urile bancilor: patru dintre ele (BT, UniCredit, CEC, BRD)
blocheaza descarcarea prin WAF sau dau 404 pe favicon. Commons are fisierele
de logo ca atare, in SVG, si permite descarcarea.

Titlurile de fisier sunt CURATE, verificate manual unul cu unul, nu luate din
primul rezultat de căutare. Motivul: căutarea automată a intors gresit pentru
trei banci - filiala bulgara pentru UniCredit (`Unicredit Bulbank logo.svg`),
o firma germana pentru CEC (`Cec-logo-spez-3z...`) si un logo de turneu de
tenis pentru Garanti. Un logo greșit pe harta arata exact ca unul corect, deci
verificarea nu se poate sari.

Pentru ING, Garanti si Libra se pastreaza logoul deja descarcat de pe site-ul
propriu - e autentic si nu are rost inlocuit.
"""

import io
import os
import sys
import time
import urllib.parse

import requests

AICI = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.join(os.path.dirname(AICI), "app", "logos")

HEADERS = {
    "User-Agent": "LibraBank-MarketIntel-Test/0.1 "
                  "(test intern; contact: robert.postolache@librabank.ro)"
}
DELAY = 1.0

# slug -> (wiki, titlu de fisier verificat manual)
FISIERE = {
    "bcr":                ("commons", "File:Banca Comercială Română logo.png"),
    "brd":                ("commons", "File:BRD logo.svg"),
    "banca-transilvania": ("commons", "File:Banca Transilvania logo.svg"),
    "raiffeisen":         ("commons", "File:Raiffeisen Bank International logo.svg"),
    "unicredit":          ("commons", "File:Unicredit logo.svg"),
    "patria":             ("commons", "File:Patria Bank logo.svg"),
    "salt":               ("commons", "File:Salt Bank logo.svg"),
    "cec":                ("ro",      "Fișier:CEC Bank.svg"),
}

# pastrate de pe site-ul propriu al bancii (autentice, deja descarcate)
PASTRATE = {"ing": "ing.svg", "garanti": "garanti.jpg", "libra": "libra.ico"}

API = {
    "commons": "https://commons.wikimedia.org/w/api.php",
    "ro": "https://ro.wikipedia.org/w/api.php",
}


def url_fisier(wiki, titlu):
    r = requests.get(API[wiki], headers=HEADERS, timeout=20, params={
        "action": "query", "format": "json", "titles": titlu,
        "prop": "imageinfo", "iiprop": "url|size|mime",
    })
    r.raise_for_status()
    for _, p in ((r.json().get("query") or {}).get("pages") or {}).items():
        for info in (p.get("imageinfo") or []):
            return info.get("url"), info.get("mime"), info.get("size")
    return None, None, None


def main():
    err = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
    os.makedirs(DEST, exist_ok=True)

    for slug, (wiki, titlu) in FISIERE.items():
        try:
            url, mime, marime = url_fisier(wiki, titlu)
            if not url:
                err.write(f"RATAT {slug:22s} fisier negasit: {titlu}\n")
                continue
            # URL-urile Commons vin cu query (?utm_source=...), deci extensia se
            # ia din calea curata, nu din URL-ul intreg
            cale_url = urllib.parse.urlparse(url).path
            ext = ".svg" if (mime or "").endswith("svg+xml") else (os.path.splitext(cale_url)[1] or ".png")
            r = requests.get(url, headers=HEADERS, timeout=25)
            r.raise_for_status()
            # scoate variantele vechi ale aceluiasi slug, ca sa nu rămână doua
            for vechi in os.listdir(DEST):
                if vechi.rsplit(".", 1)[0] == slug and not vechi.endswith(ext):
                    os.remove(os.path.join(DEST, vechi))
            cale = os.path.join(DEST, slug + ext)
            with open(cale, "wb") as f:
                f.write(r.content)
            err.write(f"OK    {slug:22s} {os.path.basename(cale):34s} {len(r.content):>7d}b\n")
        except Exception as exc:
            err.write(f"RATAT {slug:22s} {exc.__class__.__name__}: {exc}\n")
        time.sleep(DELAY)

    for slug, fisier in PASTRATE.items():
        exista = os.path.exists(os.path.join(DEST, fisier))
        err.write(f"{'PASTRAT' if exista else 'LIPSA  '} {slug:22s} {fisier} (de pe site propriu)\n")

    err.flush()


if __name__ == "__main__":
    main()
