"""Extrage comisioanele din documentele standardizate prin Legea 258/2017.

Rulare:  python scripts/parseaza_pdf.py
Ieșire:  output/comisioane_pdf.json
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RADACINA = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADACINA))

from crawler.parser_pdf import documente_standardizate, extrage

PDFURI = RADACINA / "output" / "crawl" / "pdf"


def main():
    documente, respinse = documente_standardizate(PDFURI)
    print(f"documente standardizate gasite: {len(documente)}")
    for cale, motiv in respinse:
        print(f"  respins: {cale.name[:50]:52} {motiv}")
    print()

    toate, erori = [], []
    for cale in documente:
        banca = cale.parent.name
        try:
            inr = extrage(cale, banca, radacina=PDFURI)
        except Exception as e:
            # mesajul complet, nu doar tipul: un NameError dintr-o refactorizare a
            # trecut o data drept "document problematic" si a ascuns o regresie de
            # 177 de comisioane
            print(f"  EROARE  {banca:12} {cale.name[:48]}  {type(e).__name__}: {e}")
            erori.append((banca, cale.name, f"{type(e).__name__}: {e}"))
            continue
        toate.extend(inr)
        print(f"  {len(inr):4} comisioane  {banca:12} {cale.name[:52]}")

    if erori:
        print(f"\n!! {len(erori)} documente au eșuat — totalul de mai jos e INCOMPLET")
    print(f"\ntotal: {len(toate)} comisioane din "
          f"{len(documente) - len(erori)}/{len(documente)} documente")
    print(f"\npe tip:     {dict(Counter(x['tip'] for x in toate))}")
    print(f"pe moneda:  {dict(Counter(x['moneda'] for x in toate))}")
    print(f"pe banca:   {dict(Counter(x['banca'] for x in toate))}")
    print(f"frecvente:  {dict(Counter(x['frecventa'] for x in toate if x['frecventa']))}")
    print(f"cu conditie de suma: {sum(1 for x in toate if x['conditie'])}")

    servicii = Counter(x["serviciu"] for x in toate if x["serviciu"])
    print(f"\nservicii distincte: {len(servicii)}")
    print("cele mai frecvente:")
    for s, n in servicii.most_common(12):
        print(f"  {n:3}  {s[:68]}")

    ies = RADACINA / "output" / "comisioane_pdf.json"
    ies.write_text(json.dumps(toate, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n>> {ies.relative_to(RADACINA)}")


if __name__ == "__main__":
    main()
