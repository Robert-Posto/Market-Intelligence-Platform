"""De cand e valabil ce scrie in document — citit din textul lui, nu de la server.

De ce e nevoie de o a treia sursa de data, cand avem deja doua:

  `Last-Modified`  — momentul fișierului pe server. Minte des: la multe origini
                     e momentul umplerii cache-ului. Sonda a prins deja o origine
                     care il schimba pe octeți identici.
  numele fișierului — exista la o minoritate, si spune uneori doar luna.
  TEXTUL            — "in vigoare incepand cu data de 21.09.2026". Singura sursa
                     care exprima o DECIZIE, nu o operație tehnica.

Problema pe care o rezolva: bancile nu sterg versiunile vechi de pe site. Avem
pe disc ghidul BRD "din 01.09.2026" si cel "din 21.09.2026", cu acelasi nume de
fișier, la URL-uri diferite. Le parsam pe amandoua, si comisioanele intra la
gramada. Nimic nu spune care e in vigoare azi.

Ce NU face: nu ghiceste. Daca nu gaseste o data, intoarce None, iar apelantul
marcheaza `DATA_NECUNOSCUTA` — inca o stare din familia "nu pot sa spun". Un
document fara data nu devine "probabil curent".

--- Cele trei capcane, gasite masurand, nu presupunand -----------------------

Un inventar peste toate cele 808 documente (`scripts/inventar_date.py`) a scos
la iveala trei feluri in care o cautare naiva ar fi produs date GREȘITE. O data
gresita e mai rea decat niciuna: arata exact ca una buna.

  1. "valabil PANA LA 30.09.2026" — data de SFARSIT, nu de inceput. Apare la
     indicii de referinta. Citita ca data de intrare in vigoare, ar fi facut un
     document expirat sa para proaspat.
  2. "clientii care au depus cerere incepand cu data de 15 iulie 2026" — o
     conditie de eligibilitate din corpul documentului, nu data documentului.
  3. "versiunea 12", "versiunea v_1.4" — numar de versiune, nu data.

Aparari, in ordine: se citeste doar ANTETUL (prima pagina, primele caractere),
fiindca data de intrare in vigoare sta pe coperta iar capcanele stau in corp;
ancorele de sfarsit sunt respinse explicit; ancorele slabe vin ultimele.
"""
import re
import unicodedata
from datetime import date

LUNI = ["ianuarie", "februarie", "martie", "aprilie", "mai", "iunie", "iulie",
        "august", "septembrie", "octombrie", "noiembrie", "decembrie"]
# Abrevierile apar pe coperte: "versiune oct.2024", "versiunea 3/ sep. 2025".
# "mai" e si luna intreaga si abreviere, deci nu se repeta.
PRESCURTARI = {"ian": 1, "feb": 2, "mar": 3, "apr": 4, "iun": 6, "iul": 7,
               "aug": 8, "sep": 9, "sept": 9, "oct": 10, "noi": 11, "nov": 11,
               "dec": 12}

# Marginile plauzibilului. Sub ele, aproape sigur am prins altceva decat data de
# intrare in vigoare — o nota de subsol istorica, un numar de lege, un IBAN rupt.
AN_MINIM = 2015
ANI_IN_VIITOR = 2

# Cat din document se citeste. Data de intrare in vigoare sta pe coperta sau in
# antet; capcanele de mai sus stau in corp. Restrangerea la antet e cea mai
# ieftina aparare si singura care le prinde pe toate trei deodata.
CARACTERE_ANTET = 1200

# Ancorele, in ordinea autoritatii. Prima care da o data plauzibila castiga, deci
# ordinea E semantica: "in vigoare din" bate "actualizat la", fiindca a doua poate
# fi data ultimei corecturi de tipar, nu a deciziei comerciale.
#
# Textul se cauta FARA diacritice (vezi _fara_diacritice): PDF-urile bancare le
# pierd neregulat, iar "începând" si "incepand" trebuie sa fie acelasi cuvant.
ANCORE = [
    ("vigoare",     r"in\s*vigoare(?:\s*(?:incepand\s*cu|de\s*la|din|la))?"
                    r"(?:\s*data\s*de)?"),
    ("valabil",     r"valabil\w*(?:\s*(?:incepand\s*cu|de\s*la|din|pentru))?"
                    r"(?:\s*data\s*de)?"),
    ("aplicabil",   r"aplicabil\w*(?:\s*(?:incepand\s*cu|de\s*la|din))?"
                    r"(?:\s*data\s*de)?"),
    ("incepand",    r"incepand\s*cu(?:\s*data\s*de)?"),
    # Campul "Data:" din formularul standardizat de informare cu privire la
    # comisioane — impus de lege, deci scris la fel la toate bancile. Cere doua
    # puncte imediat, ca "Data nasterii:" sa nu intre.
    ("camp_data",   r"\bdata\s*:"),
    ("versiune",    r"(?:versiun\w*|editi\w*)(?:\s*din)?"),
    ("la_data_de",  r"la\s*data\s*de"),
    ("actualizat",  r"(?:actualizat\w*|ultima\s*actualizare)(?:\s*la)?"),
]

# Ce urmeaza dupa ancora si o anuleaza. "valabil pana la 30.09" e o data de
# expirare; luata drept data de intrare in vigoare, ar intineri un document mort.
RE_SFARSIT = re.compile(r"^\s*(?:pana|p[aâ]n[aă])\s*(?:la|in|l[aă])\b")

# Cat de departe de ancora mai poate sta data. 40 de caractere acopera
# "in vigoare incepand cu data de 21.09.2026" cu tot cu punctuatie intercalata,
# fara sa ajunga la urmatoarea propoziție.
FEREASTRA = 40

_LUNA_TXT = "|".join(LUNI)
_PRESC = "|".join(sorted(PRESCURTARI, key=len, reverse=True))  # "sept" inainte de "sep"

RE_DATE = [
    # zi.luna.an si an-luna-zi
    ("zi",   re.compile(r"(\d{1,2})\s*[.\-/]\s*(\d{1,2})\s*[.\-/]\s*(\d{4})")),
    ("zi",   re.compile(r"(\d{4})\s*[.\-/]\s*(\d{1,2})\s*[.\-/]\s*(\d{1,2})")),
    # "01 octombrie 2026"
    ("zi",   re.compile(rf"(\d{{1,2}})\s*[.,]?\s*({_LUNA_TXT})\s*(\d{{4}})")),
    # "octombrie 2026" — luna intreaga, fara zi
    ("luna", re.compile(rf"({_LUNA_TXT})\s*(\d{{4}})")),
    # "oct.2024", "sep. 2025" — prescurtat. Ultimul, ca "mai" sa fie prins de
    # tiparele de mai sus, nu aici.
    ("luna", re.compile(rf"\b({_PRESC})\.?\s*(\d{{4}})")),
]


def _fara_diacritice(text):
    """Text minuscul, fara diacritice — 'Începând' si 'incepand' devin la fel.

    Se face prin descompunere Unicode, nu prin tabel de inlocuiri: 's' apare in
    PDF-uri si cu sedila (U+015F) si cu virgula dedesubt (U+0219), iar un tabel
    scris de mana rateaza jumatate. Lungimea se pastreaza caracter cu caracter,
    ca pozitiile gasite in textul normalizat sa ramana valide.
    """
    iesire = []
    for c in text.lower():
        baza = "".join(x for x in unicodedata.normalize("NFD", c)
                       if not unicodedata.combining(x))
        iesire.append(baza if len(baza) == 1 else c)
    return "".join(iesire)


def _construieste(grupuri, forma):
    """(data, precizie) dintr-o potrivire, ori (None, None) daca e implauzibila."""
    try:
        if forma == "luna":
            eticheta, an = grupuri[0], int(grupuri[1])
            luna = (LUNI.index(eticheta) + 1 if eticheta in LUNI
                    else PRESCURTARI[eticheta])
            zi = 1
        elif grupuri[1] in LUNI:
            zi, luna, an = int(grupuri[0]), LUNI.index(grupuri[1]) + 1, int(grupuri[2])
        elif len(grupuri[0]) == 4:
            an, luna, zi = int(grupuri[0]), int(grupuri[1]), int(grupuri[2])
        else:
            zi, luna, an = int(grupuri[0]), int(grupuri[1]), int(grupuri[2])
        d = date(an, luna, zi)
    except (ValueError, IndexError, KeyError):
        return None, None
    if not (AN_MINIM <= an <= date.today().year + ANI_IN_VIITOR):
        return None, None
    return d, forma


def data_din_text(text, doar_antet=True):
    """(data, precizie, ancora, dovada) sau (None, None, None, None).

    `dovada` e fragmentul exact din document, pastrat ca un om sa poata verifica
    fara sa redeschida PDF-ul. Un sistem care spune "01.09.2026" fara sa arate de
    unde cere sa fie crezut pe cuvant, si tocmai asta incercam sa nu facem.
    """
    plat = _fara_diacritice(re.sub(r"\s+", " ", text or ""))
    if doar_antet:
        plat = plat[:CARACTERE_ANTET]
    for nume, tipar_ancora in ANCORE:
        for m in re.finditer(tipar_ancora, plat):
            zona = plat[m.end():m.end() + FEREASTRA]
            if RE_SFARSIT.match(zona):        # "valabil pana la ..." — data de sfarsit
                continue
            for forma, tipar in RE_DATE:
                md = tipar.search(zona)
                if not md:
                    continue
                d, precizie = _construieste(md.groups(), forma)
                if d:
                    dovada = plat[max(0, m.start() - 10):m.end() + md.end()].strip()
                    return d, precizie, nume, dovada[:120]
    return None, None, None, None


def data_din_nume(nume):
    """(data, precizie, dovada) din numele fișierului, ori (None, None, None).

    A doua sursa, si la unele banci SINGURA. Tarifele BCR nu contin nicio data
    in text — masurat pe toate cele 9 pagini ale unui exemplar. Data traieste
    doar in nume: `BCR_Tarife-si-Comisioane-PDAI_1-iulie-2026.pdf`. Fara sursa
    asta, BCR ramane intreg nedatat, si BCR e a doua banca dupa numarul de
    comisioane pe care ni le da.

    Separatorii se normalizeaza la spatiu, altfel "1-iulie-2026" nu seamana cu
    o data. Un an singur ("..._2025.pdf") NU se accepta: o cifra de an, fara
    luna, nu distinge doua versiuni publicate in acelasi an — adica exact
    cazul pentru care avem nevoie de data.
    """
    baza = re.sub(r"\.pdf$", "", (nume or "").rsplit("/", 1)[-1], flags=re.I)
    # Prefixul de unicitate pe care il punem noi la descarcare (8 cifre hexa si
    # liniuta de jos) nu e parte din numele bancii; scos, ca sa nu intre in
    # cautarea de cifre.
    baza = re.sub(r"^[0-9a-f]{8}_", "", baza)
    # Doua treceri, si ordinea conteaza. Intai numele asa cum e: "19.06.2024"
    # e deja o data si normalizarea l-ar rupe in "19 06 2024". Abia apoi cu
    # separatorii inlocuiti, pentru "1-iulie-2026", care altfel nu seamana cu
    # o data. O singura trecere pierde mereu una din cele doua forme.
    for varianta in (_fara_diacritice(baza),
                     _fara_diacritice(re.sub(r"[-_]+", " ", baza))):
        for forma, tipar in RE_DATE:
            m = tipar.search(varianta)
            if not m:
                continue
            d, precizie = _construieste(m.groups(), forma)
            if d:
                return d, precizie, m.group(0).strip()
    # cifre lipite: "20260901" sau "01092026"
    for tipar, ordine in ((r"(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)", "alz"),
                          (r"(?<!\d)(\d{2})(\d{2})(20\d{2})(?!\d)", "zla")):
        m = re.search(tipar, baza)
        if not m:
            continue
        g = m.groups() if ordine == "alz" else (m.group(1), m.group(2), m.group(3))
        d, precizie = _construieste(g if ordine == "zla" else g, "zi")
        if d:
            return d, precizie, m.group(0)
    return None, None, None


def text_pdf(cale, pagini=2):
    """Textul primelor pagini si motivul, daca PDF-ul nu se poate citi.

    Se deschide documentul a doua oara, desi parserul tocmai l-a deschis. E
    ~15% timp in plus pe un pas care oricum dureaza minute, si tine citirea
    datei intr-un singur loc in loc s-o imprastie in doi parseri diferiti.
    """
    import pdfplumber
    try:
        with pdfplumber.open(cale) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages[:pagini]), None
    except Exception as e:
        return None, f"eroare la citire: {type(e).__name__}"


# Legea cere documentele de preturi in romana (OUG 50/2010, Legea 258/2017),
# deci unul scris doar in engleza e traducerea unui original romanesc. Pe
# 25.09.2026, fiecare lista in engleza din baza avea geamanul romanesc de
# aceeasi data (BCR PJ, Raiffeisen corporatii si IMM, Garanti T0012). Vocabularul
# e romanesc: pe traduceri doar 47% din comisioane aveau concept, pe originale 84%.
#
# Pragul e masurat pe primele pagini ale celor 567 de PDF-uri din baza: listele
# bilingve (Techventures, TBI, PKO) au cel mult 63% cuvinte de legatura
# englezesti, cele doar in engleza cel putin 91%.
RE_CUVINTE_EN = re.compile(
    r"\b(?:the|of|and|for|with|from|to|by|or|fee|fees|account|accounts|charge|charges)\b", re.I)
RE_CUVINTE_RO = re.compile(
    r"\b(?:de|și|şi|si|pentru|cu|la|din|sau|ale|cont|contul|comision|comisionul)\b", re.I)
PRAG_ENGLEZA = 0.85


def e_traducere(text):
    """Textul e in engleza, nu in romana?

    Sub cinci cuvinte englezesti nu se decide: un document scanat sau o coperta
    goala nu spune in ce limba e.
    """
    en, ro = len(RE_CUVINTE_EN.findall(text or "")), len(RE_CUVINTE_RO.findall(text or ""))
    return en >= 5 and en >= PRAG_ENGLEZA * (en + ro)


def data_documentului(cale, pagini=2):
    """Verdictul pe un document, din ambele surse.

    Textul bate numele: o propoziție scrisa in document e o declaratie a bancii,
    pe cand numele fișierului e o conventie interna care poate ramane
    neschimbata la o reincarcare. Dar cand textul tace, numele vorbeste.

    Unde cele doua NU sunt de acord, le pastram pe amandoua si o spunem. Nu
    alegem in tacere — un dezacord intre surse e informatie despre cat de mult
    merita crezuta oricare dintre ele.
    """
    text, eroare = text_pdf(cale, pagini=pagini)
    d_txt, p_txt, ancora, dovada_txt = (data_din_text(text) if text is not None
                                        else (None, None, None, eroare))
    d_nume, p_nume, dovada_nume = data_din_nume(str(cale))

    if d_txt:
        d, precizie, sursa, dovada = d_txt, p_txt, "text", dovada_txt
    elif d_nume:
        d, precizie, sursa, dovada = d_nume, p_nume, "nume", dovada_nume
    else:
        d = precizie = sursa = dovada = None

    dezacord = None
    if d_txt and d_nume and d_txt != d_nume:
        # pe precizie "luna", ziua nu e afirmata de nimeni: comparam pe luna
        aceeasi_luna = (d_txt.year, d_txt.month) == (d_nume.year, d_nume.month)
        if not (aceeasi_luna and "luna" in (p_txt, p_nume)):
            dezacord = {"text": d_txt.isoformat(), "nume": d_nume.isoformat()}

    return {"data_vigoare": d.isoformat() if d else None,
            "precizie": precizie, "sursa_data": sursa, "ancora": ancora,
            "dovada": dovada, "dezacord": dezacord,
            # Traducerea se incarca, dar ca `DUBLURA`: nu intra in comparatii si
            # nici in Istoric, unde preturile ei, citite prin alt vocabular, ar
            # parea schimbari fata de originalul romanesc.
            "stare": "DUBLURA" if e_traducere(text) else stare_fata_de(d)}


RE_PREFIX_UNIC = re.compile(r"^[0-9a-f]{8}_")
RE_DATA_IN_NUME = re.compile(
    r"\b\d{1,2}[-._ ]\d{1,2}[-._ ]20\d{2}\b|\b20\d{6}\b|\bvers?\b|\b20\d{2}\b", re.I)
RE_LUNA_IN_NUME = re.compile(
    r"\b(?:\d{1,2}[-._ ])?(?:" + "|".join(LUNI) + r"|"
    + "|".join(sorted(PRESCURTARI, key=len, reverse=True)) + r")\b", re.I)


def familie_document(rel):
    """Cheia sub care doua fișiere sunt doua VERSIUNI ale aceluiasi document.

    `BCR_Tarife-si-Comisioane-PJ_RO_1-martie-2026.pdf` si cel din august sunt
    acelasi document, publicat de doua ori. Ca sa se vada asa, din nume se scot
    prefixul nostru de unicitate, luna si anul — adica exact partile care
    difera intre versiuni.

    Separatorii devin SPATIU, nu underscore. '_' e caracter de cuvant, deci
    intre '_' si 'iulie' nu exista '\\b', iar tiparele de luna nu prind nimic:
    prima versiune a acestei functii nu a grupat nicio familie BCR, si a
    raportat linistit "0 documente depasite".
    """
    cale = str(rel).replace("\\", "/")
    banca, _, nume = cale.rpartition("/")
    nume = re.sub(r"\.pdf$", "", nume, flags=re.I)
    nume = RE_PREFIX_UNIC.sub("", nume)
    n = _fara_diacritice(re.sub(r"[-_. ]+", " ", nume))
    n = RE_LUNA_IN_NUME.sub(" ", n)
    n = RE_DATA_IN_NUME.sub(" ", n)
    n = re.sub(r"\s+", "_", n).strip("_")
    return f"{banca}/{n}" if banca else n


def stare_fata_de(d, azi=None):
    """`IN_VIGOARE`, `VIITOR` sau `DATA_NECUNOSCUTA`.

    `VIITOR` nu e o eroare — e un document care anunta o schimbare de preturi de
    la o data care n-a venit inca. Pentru o comparatie de piața aia e informatie
    valoroasa, dar preturile din el NU sunt cele practicate azi si n-au ce cauta
    intr-un tabel comparativ al zilei.
    """
    if d is None:
        return "DATA_NECUNOSCUTA"
    return "VIITOR" if d > (azi or date.today()) else "IN_VIGOARE"
