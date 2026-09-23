"""Acoperire: enumera toate procentele de pe o pagina si le pune fata in fata
cu ce am extras. Nu decide singur — marcheaza doar ce lipseste, ca sa judec eu.
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RADACINA = Path(__file__).resolve().parent.parent
TEXTE = RADACINA / "output" / "etalon_texte"

RE_PROC = re.compile(r"(\d{1,3}(?:[.,]\d{1,5})?)\s*(?:%|p\.?p\.?|puncte procentuale)")


def nume_fisier(url):
    p = urlparse(url)
    s = (p.netloc + p.path).strip("/").replace("/", "_")
    return re.sub(r"[^A-Za-z0-9._-]", "_", s)[:120] + ".txt"


def main():
    # Fara asta, lipsa argumentului ieșea ca IndexError pe sys.argv[1] — un
    # traceback care inseamna "ai uitat argumentul" costa timp degeaba, iar
    # scriptul pleaca in arhiva la un coleg.
    if len(sys.argv) < 2:
        print(__doc__.strip())
        print("\nRulare:  python scripts/acoperire_etalon.py <url>")
        existente = sorted(p.name for p in TEXTE.glob("*.txt")) if TEXTE.exists() else []
        if existente:
            print(f"\nPagini deja culese in {TEXTE.relative_to(RADACINA)} "
                  f"({len(existente)}):")
            for nume in existente[:10]:
                print(f"  {nume}")
            if len(existente) > 10:
                print(f"  ... si alte {len(existente) - 10}")
        return

    url = sys.argv[1]
    d = json.load(open(RADACINA / "output/rate_validate.json", encoding="utf-8"))
    extrase = [r for r in d if r["sursa_url"] == url]
    val_extrase = {}
    for r in extrase:
        val_extrase.setdefault(round(r["valoare"], 4), []).append(r["tip_rata"])

    # Nu toate URL-urile din rate_validate.json au textul cules: etalonul e un
    # eșantion, nu tot crawlul. Lipsa e un rezultat, nu o eroare — spusa asa, nu
    # ca traceback pe read_text.
    cale_text = TEXTE / nume_fisier(url)
    if not cale_text.exists():
        print(f"pagina nu e culeasa in etalon: {url}")
        print(f"  ar trebui sa fie {cale_text.relative_to(RADACINA)}")
        print("  culege-o mai intai: python scripts/culege_etalon.py")
        return

    text = re.sub(r"\s+", " ", cale_text.read_text(encoding="utf-8"))
    gasite = {}
    for m in RE_PROC.finditer(text):
        v = float(m.group(1).replace(",", "."))
        ctx = text[max(0, m.start() - 95):m.end() + 55]
        gasite.setdefault(round(v, 4), []).append(ctx)

    print(f"URL: {url}")
    print(f"procente distincte in pagina: {len(gasite)} | valori extrase de noi: {len(val_extrase)}")
    print()
    print(f"{'val':>9} {'nr.ap':>5}  {'extras ca':<34} context")
    for v in sorted(gasite):
        tipuri = val_extrase.get(v)
        eticheta = ",".join(sorted(set(tipuri))) if tipuri else "— LIPSA —"
        print(f"{v:>9} {len(gasite[v]):>5}  {eticheta:<34} {gasite[v][0][:110]!r}")
    lipsa = [v for v in gasite if v not in val_extrase]
    print()
    print(f"procente din pagina pe care nu le-am extras: {len(lipsa)}/{len(gasite)}")


if __name__ == "__main__":
    main()
