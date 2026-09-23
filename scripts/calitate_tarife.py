"""Calitatea etichetei de serviciu, pe document si pe bancă.

Nu inlocuieste verificarea de mana — o extinde. Regulile de mai jos sunt semne
MASURABILE de eticheta stricata, calibrate pe cele 48 de valori verificate de
mana: fiecare eticheta pe care am judecat-o greșita incalca cel puțin una.

Rulare: python scripts/calitate_tarife.py [comisioane_tarife.json|comisioane_pdf.json]
        implicit: amandoua, ca sa fie comparabile
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RADACINA = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADACINA))

# un nume de serviciu nu incepe cu litera mica (e continuarea unei fraze rupte)
RE_INCEPE_MIC = re.compile(r"^[a-zăâîșț]")
# nici nu se termina cu legatura sau semn de continuare
RE_TERMINA_RUPT = re.compile(r"\b(si|sau|de|la|in|pe|cu|din|prin|pentru|catre|"
                             r"c[ăa]tre|[îi]n|[şs]i)\s*$|[/,(]\s*$", re.I)
# nici nu conține un preț: acela e scurgere din coloana de valori
RE_ARE_PRET = re.compile(r"\d[\d.,]*\s*(lei|leu|ron|eur|euro|usd)\b|\d\s*%", re.I)
# ...dar o BANDA de suma in eticheta e legitima, nu o scurgere: CreditCoop numeste
# subserviciile chiar asa ("• Pentru sume ≤ 100 lei", "• În monedă metalică > 10
# lei"). Toate cele 46 de etichete pe care regula le respingea la CreditCoop erau
# corecte — greșea masuratoarea, nu parserul.
from crawler.parser_pdf import RE_PRAG  # noqa: E402  (dupa sys.path)
LUNGIME_MAX = 100     # peste asta s-au lipit doua servicii
LUNGIME_MIN = 6


def motive(serviciu):
    """Semnele de eticheta stricata, ca lista de motive."""
    if not serviciu:
        return ["lipsa"]
    m = []
    if len(serviciu) < LUNGIME_MIN:
        m.append("prea scurta")
    if len(serviciu) > LUNGIME_MAX:
        m.append("doua servicii lipite")
    if RE_INCEPE_MIC.match(serviciu):
        m.append("incepe cu litera mica")
    if RE_TERMINA_RUPT.search(serviciu):
        m.append("se termina rupt")
    if RE_ARE_PRET.search(RE_PRAG.sub(" ", serviciu)):
        m.append("conține un preț")
    return m


def raport(nume):
    """Calitatea etichetelor dintr-un fisier de comisioane."""
    date = json.loads((RADACINA / "output" / nume).read_text(encoding="utf-8"))
    print(f"\n{'=' * 72}\n{nume}\n{'=' * 72}")
    pe_banca = defaultdict(lambda: [0, 0])
    pe_document = defaultdict(lambda: [0, 0])
    toate_motivele = Counter()
    for x in date:
        m = motive(x["serviciu"])
        toate_motivele.update(m or ["curata"])
        for cheie, tinta in ((x["banca"], pe_banca),
                             (x["sursa_pdf"], pe_document)):
            tinta[cheie][0] += 1
            if not m:
                tinta[cheie][1] += 1

    total = len(date)
    curate = sum(1 for x in date if not motive(x["serviciu"]))
    print(f"total valori: {total}\netichete curate: {curate} "
          f"({100*curate//total}%)\n")
    print(f"{'bancă':13} {'valori':>7} {'curate':>7} {'%':>5}")
    for banca, (n, ok) in sorted(pe_banca.items(), key=lambda kv: -kv[1][0]):
        print(f"{banca:13} {n:7} {ok:7} {100*ok//n:4}%")

    print(f"\n{'document':52} {'valori':>7} {'%curate':>8}")
    for doc, (n, ok) in sorted(pe_document.items(), key=lambda kv: kv[1][1]/kv[1][0]):
        print(f"{doc.split(chr(92))[-1][:52]:52} {n:7} {100*ok//n:7}%")

    print("\nmotive (o eticheta poate avea mai multe):")
    for motiv, n in toate_motivele.most_common():
        print(f"  {n:5}  {motiv}")


def main():
    if len(sys.argv) > 1:
        raport(sys.argv[1])
    else:
        for nume in ("comisioane_pdf.json", "comisioane_tarife.json"):
            raport(nume)


if __name__ == "__main__":
    main()
