"""Ce s-a schimbat intre doua versiuni ale aceluiasi document — la nivel de PRET.

Sonda de schimbari raspunde la "s-a atins documentul?". Raspunde corect, pe
octeți, si atat poate sti un HEAD urmat de o descarcare. Dar raspunsul ala e
aproape inutilizabil singur.

Masurat pe ghidul de tarife BRD, 21 septembrie, cu spatiile albe ignorate ca sa
dispara reformatarea — 13 diferente reale, din care:

    10  glife ">=" si "<=" care in versiunea veche nu erau in font
     1  data de pe coperta
     1  marcaj de nota de subsol
     1  SCHIMBARE DE PRET

Una din treisprezece. Un raport care spune "BRD si-a schimbat tarifele" e
adevarat si inutil in acelasi timp. Ce voiai sa afli era:

    brd  debit direct Simplis  1,50 lei -> gratuit  (exceptia Electrica eliminata)

--- De ce se pot compara valorile, desi de obicei nu se poate ----------------

Regula de pana acum era ca valorile extrase NU se compara intre rulari: daca
intre timp s-a modificat parserul, vezi propria ta schimbare si o iei drept
miscare de piata. Asa am raportat odata un comision "430 -> 427" care nu
existase niciodata — fusese o editare a mea.

Aici regula nu se incalca, se ocoleste. Nu comparam o valoare VECHE STOCATA cu
una noua: deschidem amandoua fisierele ACUM si le parsam cu acelasi parser, in
aceeasi clipa. Orice diferenta introdusa de parser se aplica identic celor doua
versiuni si se anuleaza. Ce ramane vine din document.
"""
import re
import unicodedata
from collections import defaultdict

# Ce identifica acelasi rand din tabel intre doua versiuni. `conditie` sta
# separat, in a doua trecere: o banda care apare sau dispare e o schimbare
# despre care vrem sa stim, nu un rand nou.
CHEIE = ("serviciu", "tip", "moneda", "frecventa", "coloana")


def _normalizeaza(text):
    """Text comparabil intre doua randari ale aceluiasi PDF.

    Se scoate TOT spatiul alb, nu se colapseaza. Randarea noua a ghidului BRD a
    mutat despartirile in cuvinte — "Oriceoperatiunediferitadecele" a devenit
    "Oriceoperatiune diferita decele" — fara sa schimbe un singur caracter de
    continut. Pastrand spatiile, fiecare rand ar fi iesit drept "disparut" plus
    "aparut", si schimbarea de pret s-ar fi pierdut in zgomot.
    """
    if text is None:
        return None
    plat = unicodedata.normalize("NFD", str(text).lower())
    plat = "".join(c for c in plat if not unicodedata.combining(c))
    return re.sub(r"\s+", "", plat)


def _cheie(x, cu_conditie=True):
    baza = tuple(_normalizeaza(x.get(c)) for c in CHEIE)
    return baza + ((_normalizeaza(x.get("conditie")),) if cu_conditie else ())


def _valori(inregistrari):
    return sorted(v["valoare"] for v in inregistrari if v.get("valoare") is not None)


def _tipuri(inregistrari):
    return sorted({v.get("tip") for v in inregistrari if v.get("tip")})


def compara(vechi, nou):
    """Diferentele de pret intre doua liste de inregistrari.

    Intoarce un dict cu patru liste. Ordinea in care se potrivesc randurile e
    deliberata, de la cea mai sigura la cea mai slaba:

      `pret`   — aceeasi cheie, inclusiv banda: doar cifra s-a mutat. Singura
                 categorie despre care se poate spune "banca a schimbat pretul".
      `banda`  — acelasi serviciu, banda diferita. Poate fi o schimbare reala
                 (un prag mutat) SAU o glifa care inainte nu se citea. Nu se
                 decide automat care din doua; se raporteaza amandoua capetele.
      `aparut` / `disparut` — randuri fara pereche.
    """
    gv, gn = defaultdict(list), defaultdict(list)
    for x in vechi:
        gv[_cheie(x)].append(x)
    for x in nou:
        gn[_cheie(x)].append(x)

    pret, banda, aparut, disparut = [], [], [], []
    for k in set(gv) | set(gn):
        a, b = _valori(gv.get(k, [])), _valori(gn.get(k, []))
        if k in gv and k in gn:
            if a != b:
                pret.append({"cheie": k, "vechi": a, "nou": b,
                             "exemplu": (gn[k] or gv[k])[0]})
        elif k in gv:
            disparut.append({"cheie": k, "valori": a, "tipuri": _tipuri(gv[k]),
                             "exemplu": gv[k][0]})
        else:
            aparut.append({"cheie": k, "valori": b, "tipuri": _tipuri(gn[k]),
                           "exemplu": gn[k][0]})

    # A doua trecere: printre randurile ramase fara pereche, cele care se
    # potrivesc daca ignoram banda. Altfel un prag citit acum si necitit inainte
    # ar aparea ca doua schimbari mari — un rand mort si unul nascut — in loc de
    # una mica.
    fv = defaultdict(list)
    for d in disparut:
        fv[d["cheie"][:-1]].append(d)
    ramase_ap, mutate = [], []
    for ap in aparut:
        pereche = fv.get(ap["cheie"][:-1])
        if pereche:
            d = pereche.pop(0)
            mutate.append({"cheie": ap["cheie"][:-1],
                           "banda_veche": d["cheie"][-1],
                           "banda_noua": ap["cheie"][-1],
                           "vechi": d["valori"], "nou": ap["valori"],
                           "exemplu": ap["exemplu"]})
        else:
            ramase_ap.append(ap)
    ramase_disp = [d for grup in fv.values() for d in grup]
    banda.extend(mutate)

    # A treia trecere: randuri fara pereche care au EXACT aceleasi valori si
    # acelasi prag. Numele serviciului e o eticheta taiata dintr-un text lung;
    # o randare noua muta despartirile in cuvinte si eticheta iese alta, desi
    # randul e acelasi. Masurat pe ghidul BRD: din 13 randuri "aparute", 12
    # erau perechile celor "disparute", doar cu numele mototolit.
    #
    # Valorile sunt continutul, numele e doar eticheta. Cand continutul e
    # identic, e reformatare, nu schimbare — si trebuie spus separat, altfel
    # singura schimbare adevarata se pierde intre douasprezece false.
    # Se compara valorile, pragul SI restul cheii in afara numelui: moneda,
    # frecventa, coloana. Numai numele are voie sa difere. Fara asta, "10 LEI"
    # si "10 EUR" pentru servicii cu nume diferite se imperecheau ca
    # "reformatare", si o schimbare de moneda ar fi disparut din raport.
    def _fara_nume(d):
        return (tuple(d["valori"]),) + tuple(d["cheie"][1:])

    reformatat = []
    dupa_valori = defaultdict(list)
    for d in ramase_disp:
        dupa_valori[_fara_nume(d)].append(d)
    inca_ap = []
    for ap in ramase_ap:
        grup = dupa_valori.get(_fara_nume(ap))
        if grup:
            d = grup.pop(0)
            reformatat.append({"valori": ap["valori"], "prag": ap["cheie"][-1],
                               "nume_vechi": d["cheie"][0],
                               "nume_nou": ap["cheie"][0]})
        else:
            inca_ap.append(ap)
    inca_disp = [d for grup in dupa_valori.values() for d in grup]

    return {"pret": pret, "banda": banda, "reformatat": reformatat,
            "aparut": inca_ap, "disparut": inca_disp}


def rezumat(dif):
    return {k: len(v) for k, v in dif.items()}
