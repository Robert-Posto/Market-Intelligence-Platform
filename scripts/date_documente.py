"""Data de intrare in vigoare pentru fiecare document din care scoatem cifre.

Rulare:  python scripts/date_documente.py
Ieșire:  output/date_documente.json   — cheia e calea relativa din output/crawl/pdf

De ce un pas separat si nu o coloana in parseri: data se citeste o singura data
pe document, nu o data pe comision. Ghidul BRD da 502 comisioane; citirea datei
de 502 ori ar fi de 502 ori aceeasi deschidere de fișier.

Fișierul rezultat tine si DOVADA — fragmentul exact din care s-a citit data. Un
sistem care spune "01.09.2026" fara sa arate de unde cere sa fie crezut pe
cuvant, si tocmai asta incercam sa nu facem.

Ce se face cu el: `unifica_comisioane.py` il citeste si pune pe fiecare comision
`data_vigoare` si `stare_data`. Cand acelasi comision apare in doua versiuni ale
aceluiasi document, castiga cel cu data mai noua.
"""
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

RADACINA = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADACINA))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from crawler.data_document import data_documentului, familie_document

PDFURI = RADACINA / "output" / "crawl" / "pdf"
IESIRE = RADACINA / "output" / "date_documente.json"
SURSE = [RADACINA / "output" / "comisioane_unificate.json"]


def documente_cu_cifre():
    """Doar documentele din care am scos efectiv valori.

    Pe disc sunt 808 PDF-uri, dar majoritatea sunt contracte, brosuri si
    regulamente de promotie din care nu iese niciun comision. Data lor nu
    schimba nimic, iar citirea lor ar tripla timpul pasului.
    """
    cai = set()
    for f in SURSE:
        if not f.exists():
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        v = d if isinstance(d, list) else list(d.values())[0]
        for x in v:
            if x.get("sursa_pdf"):
                cai.add(x["sursa_pdf"].replace("\\", "/"))
    return sorted(cai)


def marcheaza_dubluri(rezultat):
    """Acelasi document sub doua nume — marcat `DUBLURA`, pastrat unul singur.

    Nu e o ciudatenie a bancilor, e urma noastra: pana la schimbarea de numire,
    descarcarile se salvau dupa numele de baza, iar doua adrese care duceau la
    acelasi fișier se suprascriau. Dupa schimbare, aceleasi documente au venit
    a doua oara cu prefix de unicitate, si vechile copii au ramas pe disc.

    Nu se sterge nimic de pe disc. Se marcheaza, iar valorile din copii nu se
    mai numara de doua ori. Formularele standardizate erau cel mai afectate:
    parserul lor nu dedublează, deci fiecare copie isi aducea comisioanele.
    """
    pe_amprenta = defaultdict(list)
    for rel, v in rezultat.items():
        if v.get("amprenta"):
            pe_amprenta[v["amprenta"]].append(rel)
    n = 0
    for _a, membri in pe_amprenta.items():
        if len(membri) < 2:
            continue
        # se pastreaza numele cu prefix de unicitate: e cel pe care crawlul
        # actual il produce, deci cel care se va reimprospata la urmatoarea rulare
        pastrat = sorted(membri, key=lambda r: (len(Path(r).name), r))[-1]
        for rel in membri:
            if rel != pastrat:
                rezultat[rel]["stare"] = "DUBLURA"
                rezultat[rel]["dublura_a"] = pastrat
                n += 1
    return n


def marcheaza_versiuni_depasite(rezultat):
    """Dintr-o familie cu mai multe date, doar cea mai noua ramane in vigoare.

    BCR tine simultan tariful pentru persoane juridice din martie, iulie si
    august 2026. Toate trei sunt pe site, toate trei se descarca, toate trei
    isi dau comisioanele. Doua din trei sunt preturi care nu se mai practica.

    Conditia e deliberat stransa: se compara doar documente din ACEEASI
    familie, si doar cele care au data. Un document fara data nu declasează pe
    nimeni si nu e declasat — ramane `DATA_NECUNOSCUTA`, adica "nu pot sa spun".
    """
    familii = defaultdict(list)
    for rel, v in rezultat.items():
        if v.get("stare") in ("DUBLURA", "LIPSA_PE_DISC"):
            continue
        if v.get("data_vigoare"):
            familii[v["familie"]].append(rel)
    n = 0
    for _f, membri in familii.items():
        if len(membri) < 2:
            continue
        cea_mai_noua = max(rezultat[r]["data_vigoare"] for r in membri)
        for rel in membri:
            if rezultat[rel]["data_vigoare"] < cea_mai_noua:
                rezultat[rel]["stare"] = "ISTORIC"
                rezultat[rel]["inlocuit_de"] = cea_mai_noua
                n += 1
    return n


def main():
    cai = documente_cu_cifre()
    print(f"{len(cai)} documente produc comisioane (din "
          f"{len(list(PDFURI.rglob('*.pdf')))} pe disc)\n")

    rezultat, stari, ancore = {}, Counter(), Counter()
    for i, rel in enumerate(cai, 1):
        cale = PDFURI / rel
        if not cale.exists():
            rezultat[rel] = {"stare": "LIPSA_PE_DISC"}
            stari["LIPSA_PE_DISC"] += 1
            continue
        v = data_documentului(cale)
        v["amprenta"] = hashlib.sha256(cale.read_bytes()).hexdigest()[:16]
        v["familie"] = familie_document(rel)
        rezultat[rel] = v
        stari[v["stare"]] += 1
        ancore[v["sursa_data"] or "-"] += 1
        semn = v["data_vigoare"] or "  —  "
        marca = "  !dezacord" if v["dezacord"] else ""
        print(f"  {i:4}/{len(cai)}  {semn}  {v['precizie'] or '':4}  "
              f"{(v['sursa_data'] or ''):5}  {rel[:52]}{marca}")

    n_dubluri = marcheaza_dubluri(rezultat)
    n_istoric = marcheaza_versiuni_depasite(rezultat)
    stari = Counter(v["stare"] for v in rezultat.values())

    IESIRE.write_text(json.dumps(rezultat, ensure_ascii=False, indent=1),
                      encoding="utf-8")

    print(f"\n{'='*70}")
    for s, n in stari.most_common():
        print(f"  {n:4}  {s}")
    cu_data = sum(1 for v in rezultat.values() if v.get("data_vigoare"))
    print(f"\n  cu data citita: {cu_data}/{len(cai)} = "
          f"{100*cu_data/max(len(cai),1):.0f}% din documentele cu cifre")
    print(f"  din care  {n_dubluri} copii identice  si  {n_istoric} versiuni "
          f"inlocuite de una mai noua")
    print(f"\n  sursa datei: {dict(ancore.most_common())}")

    for rel, v in sorted(rezultat.items()):
        if v.get("stare") == "ISTORIC":
            print(f"      ISTORIC  {v['data_vigoare']} -> {v['inlocuit_de']}  "
                  f"{rel[:56]}")

    # documentele fara data, listate: sunt cele la care nu putem spune daca
    # pretul e de azi. Se vad, nu dispar.
    fara = [k for k, v in rezultat.items() if v.get("stare") == "DATA_NECUNOSCUTA"]
    if fara:
        print(f"\n  {len(fara)} documente FARA data — cifrele lor raman "
              f"nedatate, nu se presupun curente:")
        for k in fara[:25]:
            print(f"      {k[:74]}")
        if len(fara) > 25:
            print(f"      ... inca {len(fara) - 25}")
    viitor = [k for k, v in rezultat.items() if v.get("stare") == "VIITOR"]
    if viitor:
        print(f"\n  {len(viitor)} documente intra in vigoare MAI TARZIU "
              f"(preturi anuntate, nu practicate azi):")
        for k in viitor:
            print(f"      {rezultat[k]['data_vigoare']}  {k[:62]}")
    print(f"\n>> {IESIRE.relative_to(RADACINA)}")


if __name__ == "__main__":
    main()
