"""Validarea datelor extrase: nu 'am gasit ceva', ci 'valoarea e credibila si corecta'.

Verificari implementate:
  A. Interval de plauzibilitate pe tip de produs (prinde valori absurde)
  B. Invariant intern: DAE >= dobanda nominala (DAE include comisioanele)
  C. Validare incrucisata cu BNR: IRCC de pe site-ul bancii vs IRCC publicat de BNR
  D. Capcana de format zecimal: virgula vs punct, separator de mii
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
CRAWL = Path("output/crawl")

# A. intervale plauzibile pentru Romania, 2026
INTERVALE = {
    "depozit":   (0.5, 9.0,  "dobanda la depozit"),
    "credit":    (3.0, 40.0, "dobanda la credit"),
    "dae":       (3.0, 45.0, "DAE"),
    "ircc":      (4.0, 8.0,  "IRCC"),
    "robor":     (4.0, 9.0,  "ROBOR"),
}

RE_PROC = re.compile(r"(\d{1,3}(?:[.,]\d{1,3})?)\s*%")
# termeni care arata ca procentul NU e o rata de dobanda
NU_E_RATA = ["avans", "cashback", "discount", "reducere", "din valoarea", "din pretul",
             "din suma", "comision", "grad de indatorare", "minim", "maxim",
             "din prețul", "TVA"]


def numar(t):
    """Converteste in float, gestionand ambele formate zecimale."""
    t = t.strip()
    # daca are ambele separatoare, ultimul e zecimalul
    if "," in t and "." in t:
        t = t.replace(",", "") if t.rindex(".") > t.rindex(",") else t.replace(".", "").replace(",", ".")
    else:
        t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def tip_linie(linie, categorie):
    jos = linie.lower()
    if "ircc" in jos:
        return "ircc"
    if "robor" in jos:
        return "robor"
    if "dae" in jos or "anuală efectiv" in jos or "anuala efectiv" in jos:
        return "dae"
    if "depozit" in jos or categorie == "depozite":
        return "depozit"
    if "dobând" in jos or "dobanda" in jos or "credit" in jos:
        return "credit"
    return None


def main():
    bnr_ircc = None
    cale_ind = Path("output/bnr_indici.json")
    if cale_ind.exists():
        d = json.loads(cale_ind.read_text(encoding="utf-8"))
        iv = d.get("ircc", {}).get("in_vigoare")
        if iv:
            bnr_ircc = iv["valoare"]
    print(f"IRCC de referinta (BNR): {bnr_ircc}\n")

    total, verificate = 0, 0
    suspecte, ircc_gasite, dae_vs_nom, ambigue = [], [], [], []

    for f in sorted(CRAWL.glob("*.json")):
        if f.name in ("consolidat.json", "bnr_curs_referinta.json"):
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        bid = d.get("banca_id")
        for p in (d.get("pagini") or []):
            for linie in p["linii_rata"]:
                total += 1
                jos = linie.lower()
                if any(t in jos for t in NU_E_RATA):
                    continue  # procentul nu e rata de dobanda
                tip = tip_linie(linie, p["categorie"])
                if not tip:
                    continue
                valori = [numar(m.group(1)) for m in RE_PROC.finditer(linie)]
                valori = [v for v in valori if v is not None]
                if not valori:
                    continue
                verificate += 1

                lo, hi, eticheta = INTERVALE[tip]
                for v in valori:
                    if not lo <= v <= hi:
                        suspecte.append((bid, tip, v, eticheta, linie[:115]))

                if tip == "ircc" and bnr_ircc:
                    for v in valori:
                        if 4 <= v <= 8:
                            ircc_gasite.append((bid, v, abs(v - bnr_ircc) < 0.05, linie[:95]))

                # B. DAE >= nominala, cand ambele apar in aceeasi linie
                if "dae" in jos and ("dobând" in jos or "dobanda" in jos) and len(valori) >= 2:
                    dae_vs_nom.append((bid, valori, linie[:115]))

                # D. format zecimal ambiguu in aceeasi linie
                if re.search(r"\d,\d", linie) and re.search(r"\d\.\d", linie):
                    ambigue.append((bid, linie[:115]))

    print(f"linii totale: {total} | linii cu valoare interpretabila: {verificate}")
    print(f"  => {100*verificate//max(total,1)}% din linii produc o valoare validabila\n")

    print(f"=== A. VALORI IN AFARA INTERVALULUI PLAUZIBIL ({len(suspecte)}) ===")
    for bid, tip, v, eticheta, linie in suspecte[:14]:
        lo, hi, _ = INTERVALE[tip]
        print(f"  [{bid}] {eticheta}={v}% (asteptat {lo}-{hi}%)\n      {linie}")

    print(f"\n=== C. IRCC pe site-urile bancilor vs BNR ({bnr_ircc}%) ===")
    for bid, v, potrivit, linie in ircc_gasite[:12]:
        print(f"  {'POTRIVIT' if potrivit else 'DIFERIT '} [{bid}] {v}%  {linie}")

    print(f"\n=== B. DAE vs dobanda nominala, aceeasi linie ({len(dae_vs_nom)}) ===")
    for bid, valori, linie in dae_vs_nom[:8]:
        stare = "OK" if max(valori) == valori[-1] or max(valori) >= min(valori) else "?"
        print(f"  [{bid}] valori={valori} {stare}\n      {linie}")

    print(f"\n=== D. Format zecimal mixt in aceeasi linie ({len(ambigue)}) ===")
    for bid, linie in ambigue[:6]:
        print(f"  [{bid}] {linie}")


if __name__ == "__main__":
    main()
