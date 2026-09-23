"""Cat din volumul de comisioane acopera un dicționar de N denumiri?

Se rulează ÎNAINTE de a construi dicționarul canonic, ca să știm unde să tăiem.
Fără măsurătoarea asta, alegerea „primele 20 de servicii" e arbitrară.

Grupează denumirile după cuvintele lor cheie, nu după text exact: „Retrageri de
numerar în lei de la ghişeul băncii" și „Retrageri numerar în LEI de la ATM-uri
din România" împart cuvintele care contează (retragere, numerar), iar diferența
e canalul.

Rulare: python scripts/masoara_vocabular.py
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

RADACINA = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADACINA))

# cuvinte care nu deosebesc un serviciu de altul
GOALE = {
    "de", "la", "in", "din", "pe", "cu", "si", "sau", "pentru", "prin", "catre",
    "a", "al", "ale", "unui", "unei", "un", "o", "the", "of", "and", "to",
    "lei", "leu", "ron", "eur", "euro", "usd", "valuta", "moneda",
    "banca", "bancii", "bancar", "bancare", "banci", "client", "clientului",
    "clientilor", "cont", "contul", "contului", "conturi", "conturile",
    "comision", "comisioane", "comisionul", "taxa", "taxe", "tarif",
}


def normalizeaza(text):
    """Cuvintele-cheie ale unei denumiri, fara diacritice si fara cuvinte goale."""
    t = (text or "").lower()
    for a, b in zip("ăâîșțţşĭ", "aaistts i"):
        t = t.replace(a, b)
    cuvinte = re.findall(r"[a-z]{3,}", t)
    return [c for c in cuvinte if c not in GOALE]


def radacina(cuvant):
    """Taie desinențele care nu schimba serviciul: retrageri/retragere -> retrager."""
    for coada in ("urilor", "elor", "ilor", "uri", "ile", "ilo", "ele", "ii",
                  "ea", "ul", "ui", "le", "i", "e", "a"):
        if len(cuvant) > 5 and cuvant.endswith(coada):
            return cuvant[: -len(coada)]
    return cuvant


def semnatura(text, cate=2):
    """Cheia de grupare: primele cuvinte-cheie, cu rădăcina tăiată."""
    c = [radacina(x) for x in normalizeaza(text)]
    return " ".join(sorted(c[:cate])) if c else ""


def main():
    toate = []
    for nume in ("comisioane_pdf.json", "comisioane_tarife.json"):
        date = json.loads((RADACINA / "output" / nume).read_text(encoding="utf-8"))
        toate.extend(x for x in date if x.get("categorie", "comision") == "comision")
    print(f"comisioane (fara dobanzi/limite/cursuri): {len(toate)}\n")

    for cate in (1, 2, 3):
        grupe = Counter(semnatura(x["serviciu"], cate) for x in toate)
        grupe.pop("", None)
        total = sum(grupe.values())
        print(f"gruparea pe {cate} cuvinte-cheie: {len(grupe)} grupe")
        acumulat = 0
        for prag in (10, 20, 30, 50, 100, 200):
            acumulat = sum(n for _g, n in grupe.most_common(prag))
            print(f"   primele {prag:4} grupe acopera {acumulat:5} valori "
                  f"({100 * acumulat // total:3}%)")
        print()

    grupe = Counter(semnatura(x["serviciu"], 2) for x in toate)
    grupe.pop("", None)
    banci = {}
    for x in toate:
        banci.setdefault(semnatura(x["serviciu"], 2), set()).add(x["banca"])
    print("cele mai frecvente grupe (2 cuvinte-cheie), cu cate banci le au:")
    for g, n in grupe.most_common(30):
        print(f"  {n:4} valori  {len(banci[g]):2} banci  {g}")


if __name__ == "__main__":
    main()
