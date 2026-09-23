"""Extrage comisioanele din listele de tarife nestandardizate.

Rulare:  python scripts/parseaza_tarife.py
Ieșire:  output/comisioane_tarife.json

Dedublarea e obligatorie aici, nu o rafinare: bancile lasa pe site toate versiunile
in vigoare succesiv (BCR PJ are iulie, august si martie 2026), iar fara ea aceeasi
lista de tarife ar intra de trei ori in date si ar dubla tot ce numaram.
"""
import hashlib
from functools import lru_cache
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RADACINA = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADACINA))

from crawler.data_document import data_documentului
from crawler.parser_pdf import RE_NUME_FID
from crawler.parser_tarife import extrage_tarife

PDFURI = RADACINA / "output" / "crawl" / "pdf"
RE_TARIF = re.compile(r"tarif|comisio|taxe|speze", re.I)

LUNI = ["ianuarie", "februarie", "martie", "aprilie", "mai", "iunie", "iulie",
        "august", "septembrie", "octombrie", "noiembrie", "decembrie"]
# si abrevierile: brci scrie "mai_2024" pe o versiune si "vers_oct_2024" pe
# urmatoarea, iar fara "oct" cele doua versiuni intrau amandoua in date
SCURT = ["ian", "feb", "mar", "apr", "mai", "iun", "iul", "aug", "sep", "oct",
         "noi", "dec"]
RE_LUNA = re.compile(r"(?<![a-z])(?:" + "|".join(LUNI + SCURT) + r")(?![a-z])", re.I)


def _cheie_familie(nume):
    """Numele fara data si fara numarul de versiune: versiunile aceluiasi document.

    "%20" din numele descarcate devine "20" si se lipeste de cifre, deci si el cade
    la eliminarea cifrelor.
    """
    # Prefixul de unicitate pus la descarcare (8 cifre hexa si liniuta de jos) se
    # scoate INTAI si intreg. Altfel cifrele lui cad la regula de mai jos iar
    # literele raman lipite in fața numelui, si doua versiuni ale aceluiasi
    # document primesc chei diferite:
    #     4f609199_BCR_..._martie  ->  "fbcrtarifesicomisioanepjro"
    #     aca9ef45_BCR_..._august  ->  "acaefbcrtarifesicomisioanepjro"
    # Asta a fost o regresie a schimbarii de numire: dedublarea pe familii a
    # incetat sa mai grupeze nimic, si tarifele BCR din martie si iulie au intrat
    # in date alaturi de cel din august.
    t = re.sub(r"^[0-9a-f]{8}_", "", nume.lower())
    t = RE_LUNA.sub("", t)
    t = re.sub(r"\d+", "", t)
    # nu "\b": underscore-ul e caracter de cuvant, deci intre "_" si "v" nu exista
    # granita si "_vers_" scapa neatins — de aici doua versiuni brci in date
    t = re.sub(r"(?<![a-z])(?:vers|rev|incepand|cu|din|de|la)(?![a-z])", "", t)
    return re.sub(r"[^a-z]+", "", t)


def _vechime_din_nume(nume):
    """Cheie de sortare: mai mare = mai nou. (an, luna) din numele fisierului."""
    an = max((int(a) for a in re.findall(r"20\d{2}", nume)), default=0)
    m = RE_LUNA.search(nume)
    luna = 0
    if m:
        gasit = m.group(0).lower()
        luna = next(i for i, l in enumerate(LUNI, 1)
                    if l == gasit or l.startswith(gasit))
    return (an, luna)


@lru_cache(maxsize=None)
def _vechime(cale_text):
    """Cat de noua e o versiune. Intai data din DOCUMENT, apoi cea din nume.

    Numele nu ajunge, si cazul care o dovedeste e BRD. Trei fisiere cu acelasi
    nume de baza, niciunul cu data in nume:

        158b3251_Ghid_tarife_comisioane.pdf   -> "in vigoare din 21.09.2026"
        8bfeb70d_Ghid_tarife_comisioane.pdf   -> "in vigoare din 01.09.2026"
        Ghid_tarife_comisioane.pdf            -> identic cu al doilea

    Fara data din document, sortarea cadea pe nume, adica pe ordinea alfabetica
    a prefixelor de unicitate — si pastra versiunea din 1 septembrie, aruncand-o
    pe cea din 21 cu motivul "versiune mai veche". Exact pe dos.

    Deschiderea in plus a documentului costa sub un minut pe toate cele ~74 de
    candidate, si e singurul mod de a sti CARE versiune e mai noua atunci cand
    banca nu pune data in nume.
    """
    cale = Path(cale_text)
    v = data_documentului(cale)
    if v.get("data_vigoare"):
        return (1, v["data_vigoare"], cale.name)
    an, luna = _vechime_din_nume(cale.name)
    # documentele fara data citita raman sub cele cu data: preferam o versiune
    # despre care stim cand a intrat in vigoare uneia despre care nu stim nimic
    return (0, f"{an:04d}-{luna:02d}", cale.name)


def candidati():
    """Documentele de tarife care NU sunt formularul standardizat."""
    return [c for c in sorted(PDFURI.rglob("*.pdf"))
            if RE_TARIF.search(c.name) and not RE_NUME_FID.search(c.name)]


def dedubleaza(cai):
    """(pastrate, aruncate cu motiv) — identice pe continut, apoi versiuni vechi."""
    aruncate = []
    pe_amprenta = {}
    for cale in cai:
        amp = hashlib.sha256(cale.read_bytes()).hexdigest()
        if amp in pe_amprenta:
            aruncate.append((cale, f"identic cu {pe_amprenta[amp].name[:40]}"))
        else:
            pe_amprenta[amp] = cale

    familii = defaultdict(list)
    for cale in pe_amprenta.values():
        familii[(cale.parent.name, _cheie_familie(cale.name))].append(cale)

    pastrate = []
    for _cheie, grup in sorted(familii.items()):
        grup.sort(key=lambda c: _vechime(str(c)))
        pastrate.append(grup[-1])
        for vechi in grup[:-1]:
            aruncate.append((vechi, f"versiune mai veche decat {grup[-1].name[:40]}"))
    return sorted(pastrate), aruncate


def main():
    cai = candidati()
    pastrate, aruncate = dedubleaza(cai)
    print(f"documente de tarife: {len(cai)}, "
          f"dupa dedublare: {len(pastrate)}\n")
    for cale, motiv in sorted(aruncate):
        print(f"  sarit   {cale.parent.name:12} {cale.name[:44]:46} {motiv}")
    print()

    toate, erori, goale = [], [], []
    for cale in pastrate:
        banca = cale.parent.name
        try:
            inr = extrage_tarife(cale, banca, radacina=PDFURI)
        except Exception as e:
            print(f"  EROARE  {banca:12} {cale.name[:44]:46} {type(e).__name__}: {e}")
            erori.append((banca, cale.name, f"{type(e).__name__}: {e}"))
            continue
        if not inr:
            goale.append((banca, cale.name))
        toate.extend(inr)
        print(f"  {len(inr):5} comisioane {banca:12} {cale.name[:52]}")

    if erori:
        print(f"\n!! {len(erori)} documente au eșuat — totalul de mai jos e INCOMPLET")
    if goale:
        print(f"\n!! {len(goale)} documente au dat ZERO comisioane:")
        for banca, nume in goale:
            print(f"     {banca:12} {nume[:60]}")

    print(f"\ntotal: {len(toate)} comisioane din "
          f"{len(pastrate) - len(erori) - len(goale)}/{len(pastrate)} documente")
    print(f"\npe tip:      {dict(Counter(x['tip'] for x in toate))}")
    print(f"pe moneda:   {dict(Counter(x['moneda'] for x in toate))}")
    print(f"pe banca:    {dict(Counter(x['banca'] for x in toate))}")
    print(f"geometrie:   {dict(Counter(x['geometrie'] for x in toate))}")
    print(f"categorie:   {dict(Counter(x['categorie'] for x in toate))} "
          f"(doar 'comision' intra in comparatie)")
    print(f"cu sectiune: {sum(1 for x in toate if x['sectiune'])}")
    print(f"cu coloana:  {sum(1 for x in toate if x['coloana'])}")
    print(f"cu serviciu: {sum(1 for x in toate if x['serviciu'])}")
    print(f"cu conditie: {sum(1 for x in toate if x['conditie'])}")

    servicii = Counter(x["serviciu"] for x in toate if x["serviciu"])
    print(f"\nservicii distincte: {len(servicii)}")
    for s, n in servicii.most_common(10):
        print(f"  {n:4}  {s[:70]}")

    ies = RADACINA / "output" / "comisioane_tarife.json"
    ies.write_text(json.dumps(toate, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n>> {ies.relative_to(RADACINA)}")


if __name__ == "__main__":
    main()
