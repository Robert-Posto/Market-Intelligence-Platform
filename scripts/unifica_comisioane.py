"""Unește cele două seturi de comisioane și le mapează pe vocabularul canonic.

Rulare:  python scripts/unifica_comisioane.py
Ieșire:  output/comisioane_unificate.json  (toate, cu concept/canal/destinatie)
         output/comparatie_comisioane.md   (tabelul serviciu x bancă)

Asta e pasul care face comparația posibilă. Până acum aveam extragere.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RADACINA = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADACINA))

from crawler.vocabular import canonic

SURSE = {
    "formular_standardizat": "comisioane_pdf.json",
    "lista_tarife": "comisioane_tarife.json",
}
# cate bănci trebuie să aibă un serviciu ca să merite o linie în tabel: sub 3,
# nu e o comparație, e o observație despre o bancă
MIN_BANCI = 3

# Segmentul de clienti sta in numele documentului, deci se citeste determinist —
# nu e o judecata ca maparea denumirilor. Fara el comparam preturi PF cu preturi
# PJ: la poprire, Libra are 20 lei pentru persoane fizice si 50 pentru juridice,
# iar mediana le amesteca intr-un singur numar care nu descrie niciuna.
# Atenție la granița de cuvant: "_" e caracter de cuvant, deci `\bPF\b` NU
# potrivește in "Tarife_si_Comisioane_PF.pdf". A treia data cand capcana asta
# apare in proiect, de aceea aici e scrisa cu lookaround pe litere.
def _abrev(litere):
    return rf"(?<![A-Za-z]){litere}(?![A-Za-z])"


SEGMENTE = [
    ("pj", rf"{_abrev('PJ')}|persoane[_\s-]?juridice|juridice"
           r"|legal[_\s-]?entities|corporate"),
    ("imm", rf"{_abrev('IMM')}|profesii[_\s-]?liberale|{_abrev('SME')}"),
    ("pfa", rf"{_abrev('PDAI')}|activit[ăa][țt]i[_\s-]?independente|{_abrev('PFA')}"),
    ("pf", rf"{_abrev('PF')}|persoane[_\s-]?fizice|fizice"
           r"|private[_\s-]?individuals"),
]


def segment(sursa_pdf):
    """Segmentul de clienti, din numele documentului: pf, pj, imm, pfa sau None."""
    for nume, tipar in SEGMENTE:
        if re.search(tipar, sursa_pdf, re.I):
            return nume
    return None


from crawler.ambiguitate import marcheaza, rezumat


def date_pe_document():
    """Ce spune `date_documente.json` despre fiecare document, ori {} daca lipsește.

    Pasul e optional cu buna stiinta: daca fișierul nu exista inca, comisioanele
    ies nedatate, cu `stare_data` = `NECITIT`, si asta se vede in raport. Un pas
    care lipsește nu trebuie sa faca lantul sa para ca a mers.
    """
    f = RADACINA / "output" / "date_documente.json"
    if not f.exists():
        print("!! output/date_documente.json lipsește — comisioanele ies "
              "NEDATATE. Ruleaza intai scripts/date_documente.py")
        return {}
    return json.loads(f.read_text(encoding="utf-8"))


def incarca():
    """Toate comisioanele, cu sursa marcată și maparea canonică aplicată."""
    pe_doc = date_pe_document()
    toate = []
    for eticheta, nume in SURSE.items():
        date = json.loads((RADACINA / "output" / nume).read_text(encoding="utf-8"))
        for x in date:
            concept, canal, destinatie = canonic(x)
            # cheia din date_documente.json e cu bara normala; sursa_pdf vine
            # din Path si pe Windows are bara inversa
            d = pe_doc.get((x.get("sursa_pdf") or "").replace("\\", "/"), {})
            toate.append({
                **x,
                "sursa_set": eticheta,
                "data_vigoare": d.get("data_vigoare"),
                "sursa_data": d.get("sursa_data"),
                # IN_VIGOARE / ISTORIC / DUBLURA / DATA_NECUNOSCUTA / NECITIT.
                # Ultimele trei inseamna toate "nu pot spune ca pretul asta e
                # cel de azi" — din trei motive diferite, care nu trebuie
                # confundate intre ele.
                "stare_data": d.get("stare", "NECITIT"),
                # categoria lipsește în setul standardizat: acolo tot ce am extras
                # e comision, documentul nu conține dobânzi
                "categorie": x.get("categorie", "comision"),
                # Formularul standardizat se aplica prin lege DOAR conturilor de
                # plati ale consumatorilor (directiva PAD), deci toate cele 430
                # sunt persoane fizice, chiar daca numele fisierului nu o spune.
                "segment": ("pf" if eticheta == "formular_standardizat"
                            else segment(x["sursa_pdf"])),
                "concept": concept,
                "canal": canal,
                "destinatie": destinatie,
            })
    return toate


def _reprezentativ(valori):
    """Prețul reprezentativ al unui grup: mediana, plus intervalul dacă diferă.

    Un `?` la coada celulei inseamna ca cel putin una din valorile din spatele ei
    e neatribuita: banca percepe si 0 si 2,5 lei pentru acelasi serviciu, si nu
    stim dupa ce criteriu. Cifra ramane — e reala — dar nu e un raspuns complet.
    """
    sume = sorted(v["valoare"] for v in valori)
    m = median(sume)
    semn = "?" if any(v.get("ambiguu") for v in valori) else ""
    if sume[0] == sume[-1]:
        return f"{m:g}{semn}"
    return f"{m:g} ({sume[0]:g}–{sume[-1]:g}){semn}"


# Cat de mult pot varia valorile dintr-o linie ca aceasta sa rămana o comparatie.
# Peste atat, mediana nu mai reprezinta nimic: "transfer_credit LEI" la Libra avea
# interval 0,45–50.000, adica adunase transferuri domestice mici cu RTGS urgent.
DISPERSIE_MAX = 5


def _raport(valori):
    """Raportul intre cea mai mare si cea mai mica valoare nenula."""
    nenule = [v for v in valori if v]
    return max(nenule) / min(nenule) if nenule else 1.0


# O linie pune doua intrebari diferite, iar `max/min` pe toate valorile la comun nu
# raspunde la niciuna: amesteca dezacordul dintre banci cu eterogenitatea din
# interiorul unei banci. Masurat pe cele 73 de linii, cele doua masuri separate dau
# acelasi numar de linii de incredere (46 fata de 45), dar sunt corecte pe toate
# cele trei linii unde difera de vechea masura — si spun UNDE e problema:
#
#   administrare_cont/pf/lunar   8 banci   max/min=17  intre=4,0  intern=5
#       -> comparabila; cei 17 veneau din intervalul 0-50 al unui singur ProCredit
#   livrare_card/pf/LEI          3 banci   max/min=3   intre=5,3  intern=2
#       -> NU e comparabila: Salt cere 30-50 lei, ceilalti 0-15. max/min ascundea
#          asta punand toate valorile la comun.
def dispersie_intre(pe_banca):
    """Dezacordul dintre banci, pe chiar cifrele afisate in tabel (medianele)."""
    return _raport([median(sorted(v["valoare"] for v in valori))
                    for valori in pe_banca.values()])


def dispersie_interna(pe_banca):
    """Cea mai mare imprastiere din interiorul unei singure banci.

    Asta era motivul original al masurii: "transfer_credit LEI" la Libra avea
    interval 0,45-50.000, adica adunase transferuri domestice mici cu RTGS urgent,
    iar mediana unei astfel de celule nu descrie nimic.
    """
    return max(_raport([v["valoare"] for v in valori])
               for valori in pe_banca.values())


def e_de_incredere(pe_banca):
    """Linia e o comparatie doar daca trec amandoua masurile."""
    return (dispersie_intre(pe_banca) <= DISPERSIE_MAX
            and dispersie_interna(pe_banca) <= DISPERSIE_MAX)


def tabel(comisioane):
    """Liniile tabelului serviciu x bancă, doar pentru ce se poate compara."""
    grupe = defaultdict(lambda: defaultdict(list))
    for x in comisioane:
        # cifrele care sunt cerinte sau limite, nu preturi: limita zilnica a
        # Garanti (1.000.000 lei) sau rulajul minim cerut de BCR (10.000 lei/luna)
        # nu se compara cu un comision. Vezi rol_de_conditie in parser_pdf.
        if not x["concept"] or x["valoare"] is None or x["rol"] == "conditie":
            continue
        # Frecventa E parte din identitatea pretului, nu un detaliu: 5 lei/luna si
        # 60 lei/an sunt acelasi pret, iar 5 lei/operatiune e cu totul altceva.
        # Fara ea, "administrare_cont pf LEI" aduna 21 de valori lunare cu 8 anuale
        # la 9 banci, si mediana nu descria niciuna. E citita determinist din text,
        # ca segmentul — nu e o judecata, deci putea sta in cheie de la inceput.
        # Rolul, la fel: un plafon "min. 15 EUR" al unui comision procentual nu e
        # acelasi lucru cu un comision fix de 15 EUR.
        cheie = (x["concept"], x["segment"] or "-", x["canal"] or "-",
                 x["destinatie"] or "-", x["moneda"] or "-", x["tip"],
                 x["frecventa"] or "-", x["rol"] or "-")
        grupe[cheie][x["banca"]].append(x)
    return {k: v for k, v in grupe.items() if len(v) >= MIN_BANCI}


def main():
    toate = incarca()

    n_amb, n_gr = marcheaza(toate)
    pe_motiv, pe_banca_amb = rezumat(toate)
    print(f"valori care nu pot fi deosebite intre ele: {n_amb} "
          f"({100*n_amb//max(len(toate),1)}%) in {n_gr} grupuri")
    for motiv, n in pe_motiv.items():
        print(f"  {n:5}  {motiv}")
    print(f"  pe banca: {pe_banca_amb}")
    print()

    pe_stare = Counter(x["stare_data"] for x in toate)
    print("valori pe starea documentului din care vin:")
    for s, n in pe_stare.most_common():
        print(f"  {n:5}  {s}")
    curente = [x for x in toate if x["stare_data"] == "IN_VIGOARE"]
    print(f"\n  din care pot fi numite PRETUL DE AZI: {len(curente)} "
          f"({100*len(curente)//max(len(toate),1)}%)\n")

    comisioane = [x for x in toate if x["categorie"] == "comision"]
    mapate = [x for x in comisioane if x["concept"]]
    print(f"total valori:            {len(toate)}")
    print(f"  din care comisioane:   {len(comisioane)}")
    print(f"  mapate pe un concept:  {len(mapate)} "
          f"({100 * len(mapate) // len(comisioane)}%)")
    print(f"  cu canal:              {sum(1 for x in mapate if x['canal'])}")
    print(f"  cu destinație:         {sum(1 for x in mapate if x['destinatie'])}")

    print(f"\nconcepte folosite: {len(set(x['concept'] for x in mapate))} "
          f"din {len(set(c for c, _ in __import__('crawler.vocabular', fromlist=['SERVICII']).SERVICII))}")
    for concept, n in Counter(x["concept"] for x in mapate).most_common():
        banci = len({x["banca"] for x in mapate if x["concept"] == concept})
        print(f"  {n:5} valori  {banci:2} bănci  {concept}")

    nemapate = [x for x in comisioane if not x["concept"]]
    print(f"\nNEMAPATE: {len(nemapate)} — cele mai frecvente denumiri:")
    for s, n in Counter(x["serviciu"] or "(fără nume)"
                        for x in nemapate).most_common(12):
        print(f"  {n:4}  {s[:72]}")

    # Din tabelul comparativ ies DOAR cele doua stari despre care avem DOVADA ca
    # sunt gresite: o versiune mai noua a aceluiasi document exista (`ISTORIC`),
    # sau acelasi fișier se numara de doua ori (`DUBLURA`).
    #
    # `DATA_NECUNOSCUTA` RAMANE. Tentatia e sa iasa si ea — "daca nu stim data,
    # nu stim daca e pretul de azi". Dar masurat, regula aia ar fi taiat Libra
    # de la 876 de valori la 65, si ar fi sters cu totul Eximbank, Salt si BCR
    # Locuinte. A nu sti data unui document nu e o dovada ca e vechi; e o
    # dovada ca banca nu si-a datat documentul. Le pastram si le marcam.
    EXCLUSE = ("ISTORIC", "DUBLURA")
    inainte = len(comisioane)
    comparabile = [x for x in comisioane if x["stare_data"] not in EXCLUSE]
    scoase = Counter(x["stare_data"] for x in comisioane
                     if x["stare_data"] in EXCLUSE)
    print(f"\nscoase din comparatie: {inainte - len(comparabile)} "
          f"({dict(scoase)}) — raman {len(comparabile)}")
    print("  (DATA_NECUNOSCUTA ramane: lipsa datei nu e dovada de vechime)")

    linii = tabel(comparabile)
    print(f"\nlinii comparabile (>={MIN_BANCI} bănci): {len(linii)}")

    ies = RADACINA / "output" / "comisioane_unificate.json"
    ies.write_text(json.dumps(toate, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n>> {ies.relative_to(RADACINA)}")
    scrie_tabel(linii, len(comisioane), len(mapate))


def scrie_tabel(linii, total_comisioane, total_mapate):
    """Tabelul de comparație, în Markdown, cu Libra evidențiată."""
    banci = sorted({b for pe_banca in linii.values() for b in pe_banca})
    rand = ["libra"] + [b for b in banci if b != "libra"]
    strans = {k: v for k, v in linii.items() if e_de_incredere(v)}
    larg = {k: v for k, v in linii.items() if not e_de_incredere(v)}

    out = ["# Comparația comisioanelor între bănci",
           "",
           "Generat de `scripts/unifica_comisioane.py`. Fiecare linie e un serviciu",
           "canonic, un canal, o destinație, o monedă și un tip de valoare — altfel",
           "s-ar compara lucruri diferite. Cifra e mediana, iar în paranteză",
           "intervalul, când banca are mai multe valori pentru același serviciu.",
           "",
           f"Doar serviciile prezente la cel puțin {MIN_BANCI} bănci: sub atât nu e o",
           "comparație, e o observație despre o bancă.",
           "",
           "## Cum se citește, și ce nu e aici",
           "",
           f"**Acoperire.** Din {total_comisioane} de comisioane extrase, "
           f"{total_mapate} ({100 * total_mapate // total_comisioane}%) s-au putut",
           "mapa pe unul din cele 26 de concepte canonice. Restul sunt servicii",
           "specifice unei singure bănci, sau valori a căror etichetă s-a pierdut la",
           "extragere. Ele rămân în `comisioane_unificate.json`, nemapate — nu",
           "ghicite.",
           "",
           "**Maparea denumirilor e singurul pas din tot lanțul care nu se poate",
           "verifica geometric** — e o judecată. Legea 258/2017 standardizează",
           "structura formularului, nu formularea: doar 4 denumiri din 116 sunt",
           "folosite de 3 bănci din 5. Verificată de mână pe 22 de valori luate la",
           "întâmplare: **20 concepte corecte din 22**.",
           "",
           "**Segmentul** (pf/pj/imm/pfa) se citește din numele documentului, deci e",
           "determinist. Fără el s-ar compara prețuri pentru persoane fizice cu",
           "prețuri pentru firme: la poprire, Libra are 20 lei la PF și 50 la PJ.",
           "Unde scrie `-`, documentul nu spune.",
           ""]
    out += [
        "**Semnul `?` de după o cifră** înseamnă că cel puțin una din valorile din",
        "spatele ei nu poate fi atribuită. În același document, sub același serviciu,",
        "banca are mai multe prețuri diferite și nimic nu spune care când se aplică —",
        "pragul de sumă sau antetul coloanei s-a pierdut la extragere. Eximbank cere 0",
        "lei pentru schimbarea PIN-ului la unele carduri și 2,5 la altele; tipul",
        "cardului nu s-a citit. **Cifra e reală, dar nu e un răspuns complet.**",
        "",
        "Valorile astea **rămân** în comparație. A le scoate ar însemna să aruncăm",
        "prețuri adevărate fiindcă nu le știm eticheta.",
        "",
        "**Cele două măsuri de eterogenitate.** O linie e o comparație doar dacă trec",
        f"amândouă, fiecare cu limita de {DISPERSIE_MAX}×:",
        "",
        "- **între** — de câte ori diferă cifrele afișate (medianele) între bănci. Peste",
        "  limită, băncile nu vând același lucru la prețuri comparabile.",
        "- **intern** — cea mai mare împrăștiere din interiorul unei singure bănci. Peste",
        "  limită, celula aceea adună servicii diferite, iar mediana ei nu descrie nimic.",
        "",
        "`max/min` pe toate valorile la comun nu răspunde la niciuna din întrebări: la",
        "`livrare_card` dădea 3× și trecea linia, deși Salt cere 30–50 lei față de 0–15",
        "la ceilalți.",
        "",
    ]
    for titlu, nota, grup in [
        (f"## Linii de încredere ({len(strans)})",
         "Amândouă măsurile sub limită, deci mediana reprezintă ceva.", strans),
        (f"## Linii prea eterogene ({len(larg)})",
         "Coloanele **între** și **intern** spun care măsură a depășit limita, deci "
         "ce e de reparat: `între` mare cere o cheie mai fină (de obicei destinația, "
         "nescrisă în document), `intern` mare cere etichete mai bune. Intervalul e "
         "informativ, mediana **nu**.", larg),
    ]:
        out += [titlu, "", nota, "",
                "| serviciu | segm. | canal | dest. | mon. | tip | frecv. | rol | "
                "între | intern | " + " | ".join(rand) + " |",
                "|" + "---|" * (10 + len(rand))]
        for (concept, seg, canal, dest, moneda, tip, frecv, rol), pe_banca in sorted(
                grup.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            celule = [_reprezentativ(pe_banca[b]) if b in pe_banca else ""
                      for b in rand]
            out.append(f"| {concept} | {seg} | {canal} | {dest} | {moneda} | "
                       f"{tip.replace('comision_', '')} | {frecv} | {rol} | "
                       f"{dispersie_intre(pe_banca):.0f}× | "
                       f"{dispersie_interna(pe_banca):.0f}× | "
                       + " | ".join(celule) + " |")
        out.append("")
    cale = RADACINA / "output" / "comparatie_comisioane.md"
    cale.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f">> {cale.relative_to(RADACINA)}")


if __name__ == "__main__":
    main()
