"""Transforma rezultatul crawl-ului in raport Markdown citibil.

Rulare:  python scripts/raport.py
Iesire:  output/RAPORT.md
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RADACINA = Path(__file__).resolve().parent.parent
CRAWL = RADACINA / "output" / "crawl"
RAPORT = RADACINA / "output" / "RAPORT.md"

# linii care chiar conțin o rată/DAE utila, nu simple mențiuni de marketing
RE_UTIL = re.compile(
    r"(DAE|dobând|dobanda|IRCC|ROBOR|EURIBOR)[^.]{0,120}?\d+[,.]\d+\s*%", re.IGNORECASE)


def incarca():
    cale = CRAWL / "consolidat.json"
    if not cale.exists():
        sys.exit(f"Lipsește {cale}. Rulează mai întâi: python -m crawler.main")
    return json.loads(cale.read_text(encoding="utf-8"))


def main():
    date = incarca()
    linii = ["# Raport produse si tarife bancare", ""]
    linii.append(f"Generat: {date['moment']}")
    linii.append("")

    bnr = date.get("bnr_curs_referinta")
    if bnr and bnr.get("zile"):
        zi = bnr["zile"][0]
        cursuri = zi.get("cursuri", {})
        principale = ["EUR", "USD", "GBP", "CHF"]
        text = ", ".join(f"{v}={cursuri[v]}" for v in principale if v in cursuri)
        linii += [f"## Curs de referinta BNR — {zi.get('data')}", "", text, ""]

    # tabel de acoperire
    linii += ["## Acoperire", "",
              "| Banca | Pagini | Tabele | Linii cu rate | PDF gasite | PDF descarcate | Sarite (robots) | Erori |",
              "|---|---|---|---|---|---|---|---|"]
    for b in date["banci"]:
        s = b.get("sumar")
        if not s:
            linii.append(f"| {b['nume']} | — | — | — | — | — | — | "
                         f"{b.get('eroare_fatala', 'fara date')[:40]} |")
            continue
        linii.append(
            f"| {b['nume']} | {s['pagini_extrase']} | {s['tabele_total']} | "
            f"{s['linii_rata_total']} | {s['pdfs_gasite']} | {s['pdfs_descarcate']} | "
            f"{s['pdfs_sarite_robots']} | {s['erori']} |")
    linii.append("")

    # detalii pe banca
    linii += ["## Rate si dobanzi gasite", ""]
    for b in date["banci"]:
        pagini = b.get("pagini") or []
        utile = []
        for p in pagini:
            for l in p["linii_rata"]:
                if RE_UTIL.search(l):
                    utile.append((p["categorie"], p["url"], l))
        if not utile:
            continue
        linii += [f"### {b['nume']}", ""]
        vazute = set()
        for cat, url, l in utile[:25]:
            cheie = l[:80]
            if cheie in vazute:
                continue
            vazute.add(cheie)
            linii.append(f"- **[{cat}]** {l[:230]}")
        linii.append("")
        # documentele descarcate
        docs = [d for p in pagini for d in p["pdfs"] if d.get("fisier_local")]
        if docs:
            linii.append(f"  Documente descarcate ({len(docs)}):")
            for d in docs[:12]:
                linii.append(f"  - `{d['fisier_local']}` — {d['text'][:70]}")
            linii.append("")

    # curs valutar propriu, pe banca
    linii += ["## Curs valutar propriu (tabele extrase)", ""]
    for b in date["banci"]:
        for p in (b.get("pagini") or []):
            if p["categorie"] != "curs_valutar" or not p["tabele"]:
                continue
            linii += [f"### {b['nume']}", f"Sursa: {p['url']}", ""]
            for t in p["tabele"][:2]:
                for rand in t["randuri"][:8]:
                    linii.append("- " + " | ".join(c[:22] for c in rand if c))
                linii.append("")
            break

    RAPORT.write_text("\n".join(linii), encoding="utf-8")
    print(f"Raport scris in {RAPORT}")
    print(f"  {len(date['banci'])} banci, "
          f"{sum(len(b.get('pagini') or []) for b in date['banci'])} pagini")


if __name__ == "__main__":
    main()
