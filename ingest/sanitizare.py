"""Textul unei pagini fără meniu, footer și cod — ce se compară între rulări.

Figura 3 din artefact: amprenta se calculează pe textul sanitizat, nu pe
octeți. Un token de sesiune sau un banner schimbă octeții fără să schimbe
vreun preț, iar amprenta pe octeți ar fi raportat o „schimbare" la fiecare
rulare. Pentru PDF rămân octeții.

Tag-urile eliminate sunt cele din `fetch_deposit_pages.clean_main_text`, care
merge deja pe 22 de bănci. NU se elimină div-urile cu „cookie" în nume: la
Nexent, `cookie-block-new` conținea toată pagina.

Datele de tip zz.ll.aaaa RĂMÂN: „valabil 01.04–30.06" la IRCC e o schimbare
reală. Se elimină doar orele și marcajele ISO, care se schimbă la fiecare cerere.
"""

import hashlib
import re

from bs4 import BeautifulSoup

ZGOMOT = ["script", "style", "noscript", "nav", "header", "footer", "svg",
          "iframe", "form", "button"]
RE_ORA = re.compile(r"\b\d{1,2}:\d{2}(:\d{2})?\b")
RE_ISO = re.compile(r"\b\d{4}-\d{2}-\d{2}T[\d:.+Z-]+")


# Sub această parte din textul paginii, blocul „principal" e altceva decât
# conținutul. Pagina ING de refinanțare nu are <main>: primul <article> găsit
# avea 186 de caractere din 26.200, iar dobânzile rămâneau în afara lui.
PARTE_MINIMA = 0.2


def radacina_continut(soup):
    corp = soup.body or soup
    total = len(corp.get_text(" ", strip=True)) or 1
    for candidat in (soup.find("main"), soup.find(attrs={"role": "main"}), soup.find("article")):
        if candidat is not None and len(candidat.get_text(" ", strip=True)) >= PARTE_MINIMA * total:
            return candidat
    return corp


def text_sanitizat(octeti):
    soup = BeautifulSoup(octeti, "lxml")
    for tag in soup.find_all(ZGOMOT):
        tag.decompose()
    text = radacina_continut(soup).get_text(separator=" ", strip=True)
    text = RE_ISO.sub(" ", RE_ORA.sub(" ", text))
    return re.sub(r"\s+", " ", text).strip()


def amprenta_continut(octeti):
    date = octeti if octeti.startswith(b"%PDF") else text_sanitizat(octeti).encode("utf-8")
    return hashlib.sha256(date).hexdigest()[:16]
