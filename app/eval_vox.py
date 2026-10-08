"""Evaluarea interpretării din Vox: întrebări reale, cu interpretarea așteptată
(app/vox_exemple.json). Compară doar câmpurile scrise în `asteptat`.

Fiecare întrebare e un apel real la model, deci costă. Fără `--da`, scriptul arată doar câte
întrebări sunt și estimarea. Contextul (băncile, conceptele) vine din baza din MIP_DSN, ca la
server; valorile nu se caută (evaluarea e doar a interpretării), iar jurnalul merge într-un
director temporar, nu în loguri/vox/.

Rulare:  python app/eval_vox.py          # estimarea, fără niciun apel
         python app/eval_vox.py --da     # apelurile reale
"""

import argparse
import json
import os
import sys
import tempfile

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AICI)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import vox  # noqa: E402
import server  # noqa: E402  (funcțiile de citire din bază)

# măsurat pe 06.10.2026 (Haiku 4.5, mip_merge): $0,0015 pe întrebare cu promptul în cache
# (11.568 de tokeni de intrare); prima întrebare scrie cache-ul, $0,0147 (măsurat în pagină)
COST_PRIMA, COST_ESTIMAT = 0.014, 0.0015


def potriveste(asteptat, primit):
    gresite = []
    for k, v in asteptat.items():
        if k == "text_cautat_nenul":
            if bool(primit.get("text_cautat")) != v:
                gresite.append(k)
        elif k == "banci":
            if sorted(primit.get("banci") or []) != sorted(v):
                gresite.append(k)
        elif primit.get(k) != v:
            gresite.append(k)
    return gresite


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--da", action="store_true", help="fă apelurile reale (costă)")
    a = p.parse_args()
    with open(os.path.join(AICI, "vox_exemple.json"), encoding="utf-8") as f:
        exemple = json.load(f)
    estimat = COST_PRIMA + (len(exemple) - 1) * COST_ESTIMAT
    print(f"{len(exemple)} întrebări, model {vox.model()}, cost estimat ~${estimat:.2f}")
    if not a.da:
        print("Fără --da nu se face niciun apel.")
        return 0
    if not vox.cheie_reala():
        print("ANTHROPIC_API_KEY din .env nu e o cheie reală.")
        return 2
    q = vox.Vox(context=server._context_vox, cauta=lambda *x: [],
                           stare_banca=lambda b: None, dir_jurnal=tempfile.mkdtemp(prefix="eval_vox_"))
    corecte, cost, intrare = 0, 0.0, 0
    for i, e in enumerate(exemple, 1):
        d = q.intreaba(e["intrebare"], e.get("anterior"))
        gresite = potriveste(e["asteptat"], d["interpretare"])
        corecte += not gresite
        cost += d["cost_usd"] or 0
        intrare += d["tokeni"]["intrare"] + d["tokeni"]["citire_cache"] + d["tokeni"]["scriere_cache"]
        print(f"{i:>2}. {'✓' if not gresite else '✗ ' + ', '.join(gresite)}  {e['intrebare']}")
        if gresite:
            print("    primit:", json.dumps(d["interpretare"], ensure_ascii=False))
    print(f"\n{corecte}/{len(exemple)} corecte · cost ${cost:.4f} (${cost / len(exemple):.4f} pe întrebare)"
          f" · {intrare // len(exemple)} tokeni de intrare pe întrebare")
    return 0 if corecte == len(exemple) else 1


if __name__ == "__main__":
    sys.exit(main())
