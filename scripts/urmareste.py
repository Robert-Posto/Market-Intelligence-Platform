"""Ce s-a schimbat la bănci de la ultima rulare.

Rulare:  python scripts/urmareste.py          — compara si scrie registrul
         python scripts/urmareste.py --uita-te — doar raporteaza, nu scrie
Ieșire:  output/urme.json                     — registrul de amprente (URL_CHECK)

Amprenta e pe octeții documentului, nu pe valorile extrase. Vezi crawler/urme.py
pentru motiv: un diff pe valori confunda schimbarile bancilor cu schimbarile mele.
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path

RADACINA = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADACINA))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from crawler.urme import (actualizeaza, amprenta_parser, citeste_urme, compara,
                          comparatie_de_valori_permisa, observa, scrie_urme)

ORDINE = ["SCHIMBAT", "NOU", "LIPSA", "AMBIGUU", "NESCHIMBAT", "NEVERIFICAT",
          "NEDESCARCAT"]


def main():
    doar_priveste = "--uita-te" in sys.argv

    versiune = amprenta_parser()
    urme = citeste_urme()
    observat, momente = observa()
    stari = compara(urme, observat, momente)

    print(f"versiunea parserului:  {versiune}")
    print(f"rulari anterioare:     {len(urme.get('rulari', []))}")
    print(f"documente referite:    {len(observat)}\n")

    pe_stare = Counter(s["stare"] for s in stari.values())
    for st in ORDINE:
        if pe_stare.get(st):
            print(f"  {st:<13} {pe_stare[st]:>4}")
    print()

    # --- constatarea propriu-zisa ---
    schimbate = {u: s for u, s in stari.items() if s["stare"] == "SCHIMBAT"}
    if schimbate:
        print("=== S-A SCHIMBAT LA BANCA ===")
        for u, s in sorted(schimbate.items(), key=lambda kv: kv[1]["banca"]):
            print(f"  [{s['banca']}] {u}")
            print(f"      {s['amprenta_veche'][:12]} -> {s['amprenta'][:12]}  "
                  f"({s.get('octeti', 0):,} octeți)")
        print()
    elif urme.get("rulari"):
        print("niciun document nu si-a schimbat octeții de la ultima rulare.\n")

    lipsa = {u: s for u, s in stari.items() if s["stare"] == "LIPSA"}
    if lipsa:
        print("=== NU MAI E REFERIT (banca a fost recrawlata) ===")
        for u, s in sorted(lipsa.items(), key=lambda kv: kv[1].get("banca") or ""):
            print(f"  [{s.get('banca')}] {u}")
        print()

    ambigue = [s for s in stari.values() if s["stare"] == "AMBIGUU"]
    if ambigue:
        cai = sorted({s.get("cale") for s in ambigue})
        print(f"{len(ambigue)} documente AMBIGUU: {len(cai)} fișiere locale sunt")
        print("folosite de mai multe URL-uri, deci octeții de pe disc aparțin")
        print("URL-ului descărcat ultimul si comparatia nu spune nimic despre")
        print("niciunul. Se rezolvă la urmatoarea sonda, care da fiecarui URL")
        print("propriul fisier: python scripts/sonda_schimbari.py")
        print()

    neverif = sum(1 for s in stari.values() if s["stare"] == "NEVERIFICAT")
    if neverif:
        print(f"{neverif} documente NEVERIFICAT: banca lor nu a fost recrawlata, "
              f"deci absența nu dovedește nimic.\n")

    # --- conformitate: robots.txt e per origine ---
    strain = defaultdict(list)
    for u, s in stari.items():
        if s["stare"] in ("NOU", "NESCHIMBAT", "SCHIMBAT") and not s.get("origine_proprie"):
            strain[s["origine"]].append(s["banca"])
    if strain:
        print("=== ORIGINI FARA ROBOTS.TXT CITIT ===")
        print("robots.txt e per origine prin standard. Documentele descarcate de")
        print("pe originile de mai jos nu au o regula citita pentru ele:\n")
        for o, banci in sorted(strain.items(), key=lambda kv: -len(kv[1])):
            print(f"  {o:<30} {len(banci):>3} doc   (legate de la: "
                  f"{', '.join(sorted(set(banci)))})")
        print(f"\n  total: {sum(len(v) for v in strain.values())} documente "
              f"de pe {len(strain)} origini neverificate")
        print("  de rezolvat: python scripts/verifica_robots_origini.py\n")

    # --- are voie diferenta de valori sa fie interpretata? ---
    permis, motiv = comparatie_de_valori_permisa(urme, versiune)
    print(f"comparație de valori: {'DA' if permis else 'NU'} — {motiv}")

    if doar_priveste:
        print("\n(--uita-te: registrul NU s-a scris)")
        return

    scris, mesaj = scrie_urme(actualizeaza(urme, stari, momente, versiune))
    print(f"\n{'>>' if scris else '!!'} {mesaj}")
    if scris:
        print(f"   output/urme.json")


if __name__ == "__main__":
    main()
