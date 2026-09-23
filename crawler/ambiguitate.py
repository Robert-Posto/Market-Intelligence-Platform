"""Comisioane care nu pot fi deosebite intre ele.

Semnalul e simplu si nu cere recitirea PDF-ului: in acelasi document, sub
acelasi serviciu, cu acelasi tip, moneda si frecventa, apar MAI MULTE valori
diferite — si nimic nu spune care cand se aplica. Nici prag, nici antet de
coloana, nici detaliu.

Atunci ceva s-a pierdut la extragere, iar valorile ramase sunt adevarate dar
neatribuite: stim ca banca percepe 0 sau 2,5 lei, nu stim pentru care card.

--- De ce nu se poate detecta uitandu-te la document ------------------------

Prima idee a fost sa gasim pierderea in PDF: daca extractorul scapa caractere,
ar trebui sa se vada ca marcaje `(cid:...)` sau ca pozitii goale. Masurat pe
pagina 7 din ghidul BRD, unde stim sigur ca lipseau `>=` si `<=`:

    versiunea VECHE   4.996 caractere   ">=" prezent: NU
    versiunea NOUA    4.938 caractere   ">=" prezent: DA

Versiunea incompleta are MAI MULTE caractere si totusi ii lipsesc simbolurile.
Nu exista niciun semn, nicio urma. Un PDF care omite ceva in tacere arata
identic cu unul complet — deci semnalul nu poate veni din document, ci doar
din inconsistenta a ceea ce am extras din el.

--- Ce NU inseamna `ambiguu` ------------------------------------------------

NU inseamna "valoare gresita". Preturile sunt reale, si raman in date. Inseamna
ca intrebarea "cat costa la banca X?" nu are un singur raspuns pe care sa-l
putem justifica. De aceea valorile ambigue nu se sterg si nu ies din tabel: se
marcheaza, iar liniile care se sprijina pe ele o spun.
"""
from collections import defaultdict

# Ce face doua valori sa fie ale aceluiasi lucru. `moneda` si `frecventa` sunt
# in cheie, nu printre semnele distinctive: 10 lei si 2 euro pentru acelasi
# serviciu nu e o ambiguitate, sunt doua preturi in doua monede.
CHEIE_GRUP = ("banca", "sursa_pdf", "serviciu", "tip", "moneda", "frecventa")

# Ce poate deosebi doua valori din acelasi grup.
SEMNE = ("conditie", "coloana", "detaliu", "rol")


def _motiv(membri, are_coloane_in_document):
    """De ce nu se pot deosebi — cat de exact putem spune.

    Nu se ghiceste: daca toate valorile au acelasi semn lipsa, motivul e clar;
    altfel se spune doar ca semnele nu ajung.
    """
    # Un semn prezent la UNII si absent la ALTII e cea mai buna dovada despre ce
    # s-a pierdut: tabelul avea coloana aia, doar ca nu s-a citit peste tot.
    # Exact cazul BRD, unde din trei benzi s-a citit doar cea din mijloc —
    # "(500-50.000)" a iesit, iar "<=500" si ">=50.000" nu. Prima versiune a
    # functiei se uita doar la semnele lipsa PESTE TOT, si de aceea raporta
    # "antet de coloana pierdut" pentru un tabel caruia ii lipseau pragurile.
    for semn, eticheta in (("conditie", "prag de suma pierdut"),
                           ("coloana", "antet de coloana pierdut")):
        prezent = sum(1 for m in membri if m.get(semn))
        if 0 < prezent < len(membri):
            return eticheta
    fara = [s for s in SEMNE if all(m.get(s) in (None, "") for m in membri)]
    if "conditie" in fara and "coloana" in fara:
        # documentul are coloane in alta parte, deci tabelul asta avea un antet
        # care nu s-a citit; altfel lipseste mai degraba pragul de suma
        return ("antet de coloana pierdut" if are_coloane_in_document
                else "prag de suma pierdut")
    if "conditie" in fara:
        return "prag de suma pierdut"
    if "coloana" in fara:
        return "antet de coloana pierdut"
    return "semnele existente nu ajung pentru cate valori sunt"


def marcheaza(valori):
    """Pune `ambiguu` (bool) si `motiv_ambiguu` pe fiecare valoare. Modifica pe loc.

    Intoarce (numar_valori_ambigue, numar_grupuri).
    """
    grupuri = defaultdict(list)
    coloane_pe_document = defaultdict(bool)
    for x in valori:
        x["ambiguu"] = False
        x["motiv_ambiguu"] = None
        if x.get("coloana"):
            coloane_pe_document[x.get("sursa_pdf")] = True
    for x in valori:
        if x.get("serviciu"):
            grupuri[tuple(x.get(k) for k in CHEIE_GRUP)].append(x)

    n_val = n_gr = 0
    for _cheie, membri in grupuri.items():
        distincte = {m["valoare"] for m in membri}
        if len(distincte) < 2:
            continue
        semne = {tuple(m.get(s) for s in SEMNE) for m in membri}
        # Pragul e "mai putine semne decat valori distincte", nu "niciun semn":
        # un tabel din care s-a citit UN prag din trei tot a pierdut doua randuri.
        # Exact cazul BRD, unde banda din mijloc "(500-50.000)" s-a citit iar
        # cele de sus si de jos, scrise cu <= si >=, nu.
        if len(semne) >= len(distincte):
            continue
        n_gr += 1
        motiv = _motiv(membri, coloane_pe_document.get(membri[0].get("sursa_pdf")))
        for m in membri:
            m["ambiguu"] = True
            m["motiv_ambiguu"] = motiv
            n_val += 1
    return n_val, n_gr


def rezumat(valori):
    """(pe_motiv, pe_banca) — pentru raport."""
    pe_motiv, pe_banca = defaultdict(int), defaultdict(int)
    for x in valori:
        if x.get("ambiguu"):
            pe_motiv[x.get("motiv_ambiguu") or "?"] += 1
            pe_banca[x.get("banca")] += 1
    return dict(sorted(pe_motiv.items(), key=lambda kv: -kv[1])), \
        dict(sorted(pe_banca.items(), key=lambda kv: -kv[1]))
