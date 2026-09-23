import json, pathlib, sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.sync_api import sync_playwright
from crawler.bnr_indici import toti_indicii

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context(user_agent=UA, locale="ro-RO").new_page()
    d = toti_indicii(pg)
    b.close()

rr = d["robid_robor"]
print("ROBOR scadente:", rr.get("scadente"))
print("zile:", len(rr.get("zile", [])))
if rr.get("zile"):
    z = rr["zile"][0]
    print(f"  {z['data']}  ROBOR: {z['robor']}")
    print(f"  {z['data']}  ROBID: {z['robid']}")
ir = d["ircc"]
print("\nIRCC in vigoare:", ir.get("in_vigoare"))
print("trimestrial:", ir.get("trimestrial", [])[:4])
print("zilnic:", ir.get("zilnic", [])[:3])

# Scrierea NU suprascrie date bune cu o eroare. Pe 18 septembrie BNR a raspuns cu
# ERR_CONNECTION_CLOSED, iar scriptul a inlocuit seriile intregi cu 322 de octeti de
# mesaj de eroare — zece zile de ROBOR pierdute, recuperate din arhiva. E exact
# mecanismul care inghite eșecuri din COMISIOANE_PDF.md §6: rularea "a reușit",
# fisierul s-a scris, si nimic n-a semnalat ca inauntru nu mai e nimic.
CALE = pathlib.Path("output/bnr_indici.json")


def _are_date(secțiune):
    return bool(secțiune.get("zile") or secțiune.get("trimestrial"))


vechi = json.loads(CALE.read_text(encoding="utf-8")) if CALE.exists() else {}
pastrat = {}
for cheie in list(d):
    if not _are_date(d[cheie]) and _are_date(vechi.get(cheie, {})):
        pastrat[cheie] = d[cheie].get("eroare") or "(fara date)"
        d[cheie] = vechi[cheie]

if pastrat:
    print(f"\n!! descarcarea a eșuat pentru: {', '.join(pastrat)}")
    print("   s-au PASTRAT datele anterioare, deci fisierul NU e actualizat")
    for cheie, motiv in pastrat.items():
        print(f"   {cheie}: {motiv[:90]}")

CALE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n>> {CALE}")
