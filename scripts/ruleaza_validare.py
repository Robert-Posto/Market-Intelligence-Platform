"""Aplica validarea pe inregistrarile tipizate si raporteaza."""
import json, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from crawler.validator import valideaza

recs = json.loads(Path("output/rate_tipizate.json").read_text(encoding="utf-8"))
indici = json.loads(Path("output/bnr_indici.json").read_text(encoding="utf-8"))
# EURIBOR nu e publicat de BNR; luam valoarea afisata de Patria, cu indicativ
recs, sumar = valideaza(recs, indici, euribor_referinta=2.568)

if sumar.get("referinta_ircc_expirata"):
    print("!! ATENTIE: BNR nu a publicat inca trimestrul IRCC aplicabil azi.")
    print("   Verificarile IRCC sunt neconcludente pana la publicare.\n")

print("=== SUMAR VALIDARE ===")
for k in ("OK", "SUSPECT", "SURSA_VECHE"):
    print(f"  {k:<14} {sumar.get(k, 0):>4}")
print(f"  {'confirmate cu BNR':<14} {sumar.get('confirmate_cu_bnr', 0):>4}")
print(f"  {'consistente aritmetic':<14} {sumar.get('consistente_aritmetic', 0):>4}")

print("\n=== SURSE INVECHITE DETECTATE ===")
vechi = [r for r in recs if r["stare"] == "SURSA_VECHE"]
vazut = set()
for r in vechi:
    cheie = (r["banca"], r["tip_rata"], r["valoare"])
    if cheie in vazut:
        continue
    vazut.add(cheie)
    print(f"  [{r['banca']:<10}] {r['tip_rata']:<16} {r['valoare']:>7}%")
    print(f"      {r['verificari'][-1]}")
    print(f"      {r['sursa_url'][:96]}")

print("\n=== CONFIRMATE CU BNR ===")
conf = [r for r in recs if any("confirmat cu BNR" in v for v in r["verificari"])]
vazut = set()
for r in conf:
    cheie = (r["banca"], r["tip_rata"], r["valoare"])
    if cheie in vazut:
        continue
    vazut.add(cheie)
    # nota relevanta, nu prima din lista (prima poate fi cea despre perioada)
    nota = next(v for v in r["verificari"] if "confirmat cu BNR" in v)
    print(f"  [{r['banca']:<10}] {r['tip_rata']:<16} {r['valoare']:>7}%  {nota}")

print("\n=== INDICE IMPLICIT (total - marja, citit din pagina) ===")
vazut = set()
for r in [x for x in recs if x.get("indice_implicit")]:
    nota = next(v for v in r["verificari"] if v.startswith("indice implicit"))
    if nota in vazut:
        continue
    vazut.add(nota)
    print(f"  [{r['banca']:<10}] {nota}")
    print(f"      {r['sursa_url'][:96]}")

print("\n=== CONSISTENTE ARITMETIC (indice + marja = nominala) ===")
for r in [x for x in recs if any("consistent aritmetic" in v for v in x["verificari"])][:8]:
    print(f"  [{r['banca']}] {r['verificari'][-1]}")

print("\n=== SUSPECTE ===")
for r in [x for x in recs if x["stare"] == "SUSPECT"][:8]:
    print(f"  [{r['banca']}] {r['tip_rata']}={r['valoare']}% :: {r['verificari'][-1][:90]}")
    print(f"      {r['text_sursa'][:110]}")

Path("output/rate_validate.json").write_text(
    json.dumps(recs, ensure_ascii=False, indent=2), encoding="utf-8")
print("\n>> output/rate_validate.json")
