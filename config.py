"""Citeste .env din radacina proiectului, fara dependente externe.

Variabilele deja setate in mediu au prioritate peste .env - asa se poate
suprascrie punctual la rulare, fara sa editezi fisierul.

Secretele nu se logheaza niciodata. `raport()` intoarce doar daca o cheie
exista si cat de lunga e, nu valoarea.
"""

import io
import os

RADACINA = os.path.dirname(os.path.abspath(__file__))
CALE_ENV = os.path.join(RADACINA, ".env")


def incarca(cale=CALE_ENV):
    """Pune in os.environ ce lipseste. Intoarce cheile citite din fisier."""
    citite = []
    if not os.path.exists(cale):
        return citite
    with io.open(cale, encoding="utf-8") as f:
        for linie in f:
            linie = linie.strip()
            if not linie or linie.startswith("#") or "=" not in linie:
                continue
            cheie, _, valoare = linie.partition("=")
            cheie, valoare = cheie.strip(), valoare.strip()
            citite.append(cheie)
            os.environ.setdefault(cheie, valoare)
    return citite


def cere(cheie):
    """Valoarea unei variabile obligatorii. Ridica eroare daca lipseste."""
    incarca()
    v = os.environ.get(cheie)
    if not v:
        raise RuntimeError(
            f"{cheie} lipseste. Pune-o in {CALE_ENV} (vezi .env.example) "
            "sau in mediu inainte de rulare."
        )
    return v


def raport():
    """Ce e configurat, fara sa scurga valorile."""
    incarca()
    linii = []
    for cheie in ("ANTHROPIC_API_KEY", "MIP_SALT", "MIP_DSN", "MIP_PORT"):
        v = os.environ.get(cheie)
        if not v:
            linii.append(f"{cheie}: LIPSA")
        elif "KEY" in cheie or "SALT" in cheie:
            linii.append(f"{cheie}: setat ({len(v)} caractere)")
        else:
            linii.append(f"{cheie}: {v}")
    return "\n".join(linii)


if __name__ == "__main__":
    print(raport())
