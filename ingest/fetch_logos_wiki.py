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

Pentru ING se pastreaza logoul deja descarcat de pe site-ul propriu. Garanti
si Libra aveau tot de pe site, dar erau gresite: la Garanti o poza de campanie
(og:image), la Libra favicon-ul de 16px. Verificarea din 28.09.2026 a mai gasit
sigla „GlobalMarkets” in locul BNP Paribas si sigla alba a BCR Locuinte,
invizibila pe cardul alb.

`DE_PE_SITE` sunt adrese directe de sigla, citite din antetul site-ului bancii
si verificate vizual; se descarca doar daca robots.txt le permite.
"""

import io
import os
import re
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
    "unicredit":          ("commons", "File:Unicredit logo.svg"),
    "patria":             ("commons", "File:Patria Bank logo.svg"),
    "salt":               ("commons", "File:Salt Bank logo.svg"),
    "cec":                ("ro",      "Fișier:CEC Bank.svg"),
    "garanti":            ("commons", "File:Garanti BBVA 2019.svg"),
    "intesa":             ("commons", "File:Intesa Sanpaolo logo.svg"),
    "revolut":            ("commons", "File:Revolut logo.svg"),
    "citibank":           ("commons", "File:Citi logo March 2023.svg"),
}
# Raiffeisen nu mai vine de aici: Commons are doar sigla grupului
# („Raiffeisen Bank International”), nu pe cea a bancii din Romania.

# slug -> (adresa sigla de pe site-ul bancii, fundal pus sub o sigla alba sau None)
DE_PE_SITE = {
    "raiffeisen":   ("https://www.raiffeisen.ro/content/dam/rbi/common/logos/Raiffeisen%20Bank.svg", None),
    "bnpparibas":   ("https://www.romania.bnpparibas.com/app/themes/bnpp-pays-v2c/assets/img/static/logo-bnp.svg", None),
    "libra":        ("https://www.librabank.ro/imagini/logo-libra.svg", None),
    "techventures": ("https://techventures.bank/build/techventures-logo-dark-b8cRZPpV.png", None),
    "brci":         ("https://www.brci.ro/images/logo-brci.png", None),
    # banorientfrance.com interzice tot prin robots.txt; sigla vine de pe pagina
    # de membri a Asociatiei Romane a Bancilor, care o permite. Imaginea e un
    # card de 500x281 cu sigla in mijloc: fara decupare iesea de 20px pe card.
    "banorient":    ("https://www.arb.ro/wp-content/uploads/2021/11/ARB-logo-banque-banorient-france.jpg", None),
    # sigla e alba, facuta pentru antetul bleumarin al site-ului (#0b1f42, cea mai
    # folosita culoare din pagina); nu exista varianta color nici pe site, nici pe
    # Commons, Wikipedia sau ARB. Pe cardul alb nu se vedea deloc.
    "bcr-locuinte": ("https://cdn.erstegroup.com/content/dam/ro/bcr/common/logo-svg/"
                     "BCRBancapentruLocuinte_web_internal-material.svg", "#0b1f42"),
}

# pastrate de pe site-ul propriu al bancii (autentice, deja descarcate)
PASTRATE = {"ing": "ing.svg"}

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


def scrie(slug, ext, continut):
    """Scoate variantele vechi ale aceluiasi slug, ca sa nu ramana doua."""
    for vechi in os.listdir(DEST):
        if vechi.rsplit(".", 1)[0] == slug and not vechi.endswith(ext):
            os.remove(os.path.join(DEST, vechi))
    cale = os.path.join(DEST, slug + ext)
    with open(cale, "wb") as f:
        f.write(continut)
    return cale


def fara_margini(continut, ext):
    """Decupeaza marginile albe ale unei imagini raster; un SVG ramane neatins."""
    if ext == ".svg":
        return continut
    from PIL import Image, ImageChops
    img = Image.open(io.BytesIO(continut)).convert("RGB")
    cutie = ImageChops.difference(img, Image.new("RGB", img.size, (255, 255, 255))).point(
        lambda v: 255 if v > 24 else 0).getbbox()
    if not cutie or (cutie[2] - cutie[0]) * (cutie[3] - cutie[1]) > 0.9 * img.width * img.height:
        return continut
    m = 4
    cutie = (max(cutie[0] - m, 0), max(cutie[1] - m, 0), min(cutie[2] + m, img.width), min(cutie[3] + m, img.height))
    iesire = io.BytesIO()
    img.crop(cutie).save(iesire, "PNG" if ext == ".png" else "JPEG", quality=95)
    return iesire.getvalue()


def cu_fundal(svg, culoare):
    """Pune un dreptunghi colorat sub desen, cu margine, fara sa atinga sigla."""
    text = svg.decode("utf-8")
    vb = re.search(r'viewBox="([\d.\-]+) ([\d.\-]+) ([\d.]+) ([\d.]+)"', text)
    x, y, w, h = (float(v) for v in vb.groups())
    m = h * 0.22
    x, y, w, h = x - m, y - m, w + 2 * m, h + 2 * m
    text = text.replace(vb.group(0), f'viewBox="{x:g} {y:g} {w:g} {h:g}"', 1)
    rect = f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{m * 0.6:g}" fill="{culoare}"/>'
    i = text.index(">", text.index("<svg")) + 1
    return (text[:i] + rect + text[i:]).encode("utf-8")


def din_site(err):
    sys.path.insert(0, AICI)
    from scraper import robots_allowed
    tipuri = {"image/svg+xml": ".svg", "image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
    for slug, (url, fundal) in DE_PE_SITE.items():
        try:
            stare, motiv, _ = robots_allowed(url)
            if stare == "disallow":
                err.write(f"SARIT {slug:22s} robots.txt: {motiv}\n")
                continue
            r = requests.get(url, headers=HEADERS, timeout=25)
            r.raise_for_status()
            ext = tipuri.get(r.headers.get("Content-Type", "").split(";")[0].strip())
            if not ext:
                err.write(f"RATAT {slug:22s} Content-Type {r.headers.get('Content-Type')}\n")
                continue
            continut = fara_margini(r.content, ext)
            if fundal:
                continut = cu_fundal(continut, fundal)
            cale = scrie(slug, ext, continut)
            err.write(f"OK    {slug:22s} {os.path.basename(cale):34s} {len(continut):>7d}b (site)\n")
        except Exception as exc:
            err.write(f"RATAT {slug:22s} {exc.__class__.__name__}: {exc}\n")
        time.sleep(DELAY)


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
            cale = scrie(slug, ext, r.content)
            err.write(f"OK    {slug:22s} {os.path.basename(cale):34s} {len(r.content):>7d}b\n")
        except Exception as exc:
            err.write(f"RATAT {slug:22s} {exc.__class__.__name__}: {exc}\n")
        time.sleep(DELAY)

    din_site(err)

    for slug, fisier in PASTRATE.items():
        exista = os.path.exists(os.path.join(DEST, fisier))
        err.write(f"{'PASTRAT' if exista else 'LIPSA  '} {slug:22s} {fisier} (de pe site propriu)\n")

    err.flush()


if __name__ == "__main__":
    main()
