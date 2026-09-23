"""Eșantion stratificat din listele de tarife, cu contextul paginii, pentru
verificare de mana.

Verificarea automata (scripts/verifica_tarife.py) arata doar ca textul exista in
pagina. Ea nu poate spune daca 30 de lei e comisionul serviciului sub care l-am
pus. Aceea e o judecata, si se face citind pagina.

Rulare: python scripts/etalon_tarife.py [samanta]
Ieșire: output/etalon_tarife_esantion.txt
"""
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

RADACINA = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADACINA))

import pdfplumber

PDFURI = RADACINA / "output" / "crawl" / "pdf"
PE_DOCUMENT = 1     # stratificat: fiecare document intra cu o valoare
CONTEXT = 6         # randuri de text in jurul valorii


def main():
    samanta = int(sys.argv[1]) if len(sys.argv) > 1 else 2609
    date = json.loads((RADACINA / "output" / "comisioane_tarife.json")
                      .read_text(encoding="utf-8"))
    pe_document = defaultdict(list)
    for x in date:
        pe_document[x["sursa_pdf"]].append(x)

    rnd = random.Random(samanta)
    alese = []
    for sursa in sorted(pe_document):
        alese.extend(rnd.sample(pe_document[sursa],
                                min(PE_DOCUMENT, len(pe_document[sursa]))))

    linii = [f"# Eșantion tarife pentru verificare de mana (samanta {samanta})",
             f"# {len(alese)} valori, cate {PE_DOCUMENT} din fiecare document\n"]
    for k, x in enumerate(alese, 1):
        linii.append(f"--- {k}. {x['banca']} | {x['sursa_pdf'].split('/')[-1]} "
                     f"pag. {x['pagina']} | geometrie: {x['geometrie']}")
        linii.append(f"    EXTRAS:  {x['tip']} = {x['valoare']} "
                     f"{x['moneda'] or ''} {x['frecventa'] or ''}")
        linii.append(f"    secțiune: {x['sectiune']}")
        linii.append(f"    serviciu: {x['serviciu']}")
        linii.append(f"    coloană:  {x['coloana']}")
        linii.append(f"    condiție: {x['conditie']}   rol: {x['rol']}")
        linii.append(f"    text-sursă: {x['text_sursa']}")
        with pdfplumber.open(str(PDFURI / x["sursa_pdf"])) as pdf:
            text = (pdf.pages[x["pagina"] - 1].extract_text() or "").splitlines()
        potrivite = [i for i, l in enumerate(text)
                     if x["text_sursa"][:24].strip() and
                     x["text_sursa"][:24].strip() in l]
        centru = potrivite[0] if potrivite else 0
        linii.append("    CONTEXTUL PAGINII:")
        for l in text[max(0, centru - CONTEXT):centru + CONTEXT + 1]:
            linii.append(f"      | {l}")
        linii.append("")

    ies = RADACINA / "output" / "etalon_tarife_esantion.txt"
    ies.write_text("\n".join(linii), encoding="utf-8")
    print(f">> {ies.relative_to(RADACINA)}  ({len(alese)} valori)")


if __name__ == "__main__":
    main()
