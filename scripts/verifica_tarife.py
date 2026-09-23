"""Verifica automat ca fiecare valoare extrasa exista in pagina ei din PDF.

Ce prinde: valori fabricate de geometrie — cifre lipite din doua celule diferite,
sume compuse din bucati de rand, texte mutate de pe alta pagina. Ce NU prinde:
eticheta greșita, fiindca eticheta e o judecata, nu o potrivire de text. Pentru
eticheta e nevoie de verificare de mana (scripts/etalon_tarife.py).

Rulare: python scripts/verifica_tarife.py
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

RADACINA = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADACINA))

import pdfplumber

PDFURI = RADACINA / "output" / "crawl" / "pdf"


def normalizeaza(t):
    """Fara spatii si fara diacritice: comparam continutul, nu asezarea."""
    t = t.lower()
    for a, b in zip("ăâîșțţşĭ", "aaistts i"):
        t = t.replace(a, b)
    return re.sub(r"\s+", "", t)


def main():
    date = json.loads((RADACINA / "output" / "comisioane_tarife.json")
                      .read_text(encoding="utf-8"))
    pe_pagina = defaultdict(list)
    for x in date:
        pe_pagina[(x["sursa_pdf"], x["pagina"])].append(x)

    gasite = lipsa = 0
    exemple = []
    pe_banca = Counter()
    lipsa_pe_banca = Counter()
    for (sursa, nr), inregistrari in sorted(pe_pagina.items()):
        with pdfplumber.open(str(PDFURI / sursa)) as pdf:
            text = normalizeaza(pdf.pages[nr - 1].extract_text() or "")
        for x in inregistrari:
            pe_banca[x["banca"]] += 1
            if normalizeaza(x["text_sursa"]) in text:
                gasite += 1
            else:
                lipsa += 1
                lipsa_pe_banca[x["banca"]] += 1
                if len(exemple) < 15:
                    exemple.append(x)

    total = gasite + lipsa
    print(f"valori verificate: {total}")
    print(f"  text-sursa regasit in pagina: {gasite} ({100*gasite//total}%)")
    print(f"  neregasit:                    {lipsa}")
    if lipsa:
        print("\npe banca (neregasite / total):")
        for banca, n in pe_banca.most_common():
            if lipsa_pe_banca[banca]:
                print(f"  {banca:12} {lipsa_pe_banca[banca]:4} / {n:4}")
        print("\nexemple de neregasite:")
        for x in exemple:
            print(f"  {x['banca']:11} p{x['pagina']:<3} {x['tip']:16} "
                  f"{x['valoare']}  <<{x['text_sursa'][:60]}>>")


if __name__ == "__main__":
    main()
