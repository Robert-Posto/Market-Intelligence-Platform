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


def text_sanitizat(octeti):
    soup = BeautifulSoup(octeti, "lxml")
    for tag in soup.find_all(ZGOMOT):
        tag.decompose()
    radacina = (soup.find("main") or soup.find(attrs={"role": "main"})
                or soup.find("article") or soup.body or soup)
    text = radacina.get_text(separator=" ", strip=True)
    text = RE_ISO.sub(" ", RE_ORA.sub(" ", text))
    return re.sub(r"\s+", " ", text).strip()


def amprenta_continut(octeti):
    date = octeti if octeti.startswith(b"%PDF") else text_sanitizat(octeti).encode("utf-8")
    return hashlib.sha256(date).hexdigest()[:16]
