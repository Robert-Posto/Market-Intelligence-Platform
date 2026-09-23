"""Genereaza SQL pentru indicii de referinta BNR (bnr_indici.json, pachet 21 sept).

Ce e in fisier: ROBID si ROBOR, 7 scadente (O/N, T/N, 1W, 1M, 3M, 6M, 12M),
10 zile de serie.

Ce NU e: IRCC. In rularea din care provine fisierul, pagina BNR de IRCC a picat
cu `net::ERR_CONNECTION_CLOSED`, iar fisierul pastreaza eroarea in loc de date.
Nu inventam o valoare - se raporteaza ca lipsa. IRCC conteaza cel mai mult
pentru ipotecare, deci e o lipsa de urmarit, nu un detaliu.

Idempotent: are ON CONFLICT DO NOTHING pe (indice, scadenta, valabil_din).
"""

import io
import json
import os
import sys

FISIER = os.path.join(
    os.path.expanduser("~"), "Downloads", "pentru_coleg_bs4_21sept", "output",
    "bnr_indici.json",
)


def main():
    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n")
    err = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

    with io.open(FISIER, encoding="utf-8") as f:
        d = json.load(f)

    ircc = d.get("ircc") or {}
    if "eroare" in ircc:
        err.write(f"LIPSA IRCC: {ircc['eroare']}\n")

    rr = d.get("robid_robor") or {}
    zile = rr.get("zile") or []
    sursa = rr.get("sursa") or "bnr"

    out.write("BEGIN;\n")
    n = 0
    for zi in zile:
        data = zi.get("data")          # 'dd.mm.yyyy'
        if not data:
            continue
        z, l, a = data.split(".")
        iso = f"{a}-{l}-{z}"
        for indice in ("robid", "robor"):
            for scadenta, valoare in (zi.get(indice) or {}).items():
                if valoare is None:
                    continue
                out.write(
                    "INSERT INTO indici_referinta (indice, scadenta, valoare, "
                    f"valabil_din, sursa) VALUES ('{indice}', '{scadenta}', "
                    f"{float(valoare)!r}, DATE '{iso}', '{sursa}')\n"
                    "ON CONFLICT DO NOTHING;\n"
                )
                n += 1
    out.write("COMMIT;\n")
    out.flush()

    err.write(f"valori de indice generate: {n} ({len(zile)} zile x 2 indici x 7 scadente)\n")
    err.flush()


if __name__ == "__main__":
    main()
