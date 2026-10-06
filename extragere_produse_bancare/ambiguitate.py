"""Comisioanele din listele de tarife NEstandardizate.

Separat de parser_pdf (formularul impus prin Legea 258/2017) fiindca geometria e
alta. Analiza valorii e comuna si se importa; doar citirea tabelului se schimba.

Patru lucruri masurate pe documente, nu presupuse:

1. Coloanele se citesc PE RAND, nu pe pagina. Uniunea bordurilor pe toata pagina
   da coloane false: pe BCR_Tarife-PJ pag. 9 ieseau 14, iar textul se rupea in
   "8 LEI +" si "TVA/entitate client". La inaltimea fiecarui rand, bordurile reale
   sunt 4. Cauza: o pagina contine mai multe tabele, cu geometrii diferite.

2. O bordura nu taie niciodata un cuvant. Cuvintele se grupeaza in secvente
   despartite de spatiu alb, iar o secventa se rupe doar acolo unde bordura cade
   intre doua cuvinte. Fara asta, "30 EUR" ajungea "30" intr-o celula si "EUR" in
   alta — adica valoarea se pierdea de tot, nu doar se muta.

3. Unele tabele nu au NICIO bordura verticala (Garanti, toate paginile de tarife).
   Acolo coloana se deduce din golurile de spatiu alb.

4. Bordurile desenate de doua ori la 1 punct distanta (Salt: 6 si 7, 253 si 254)
   sunt aceeasi bordura; se grupeaza.

Ce aduce in plus fata de formularul standardizat: sectiunea (ierarhia "4.2. PLATI"
apoi "A. In lei"), fiindca acelasi nume de serviciu apare de mai multe ori sub
sectiuni diferite, si numele coloanei in tabelele matriceale, fiindca patru valori
identice pe un rand sunt patru pachete diferite, nu o valoare repetata.
"""
import re
import statistics
from pathlib import Path

import pdfplumber

from crawler.parser_pdf import RE_PRAG, analizeaza_linie, rol_de_conditie

# doua borduri mai apropiate de atat sunt aceeasi bordura desenata de doua ori
TOL_BORDURA = 3
# o bordura de celula acopera cel putin un rand de text; sub asta e decoratie sau
# sigla. Fara pragul absolut, pe coperta Raiffeisen ieseau 15 "coloane" din
# vectorii siglei: maxim acumulat 35 de puncte pe o pagina de 595, deci totul
# trecea pragul relativ.
INALTIME_MIN_BORDURA = 6
# acoperirea minima a cuvintelor de pe rand: sub ea, bordurile nu sunt ale acestui
# tabel si se trece pe golurile de spatiu alb
ACOPERIRE_MIN = 0.6

RE_DOAR_INDEX = re.compile(r"^(?:\d+(?:\.\d+)*\.?|[A-Za-z]\.|[IVX]+\.)$")
RE_INDEX_LA_INCEPUT = re.compile(r"^(\d+(?:\.\d+)*\.?|[A-Z]\.|[IVX]+\.)\s+(.+)$")
# Indexul unei sectiuni se scrie cu punct ("7.", "4.2."). Fara punct obligatoriu,
# orice rand care incepe cu o cifra devenea sectiune: nota de subsol "2 intrări
# gratuite pe an," ajunsese titlu, iar titlul adevarat se pierdea.
RE_INDEX_SECTIUNE = re.compile(r"^(\d+(?:\.\d+)*\.|[A-Z]\.|[IVX]+\.)\s+(.+)$")
RE_DOAR_MONEDE = re.compile(r"^(?:\s*(?:lei|leu|ron|eur|euro|usd|gbp|chf)\s*[/,;]?)+$",
                            re.I)
RE_INDEX_LA_SFARSIT = re.compile(r"\s+\d+(?:\.\d+){1,}\.?$")
RE_LITERA_SAU_ROMAN = re.compile(r"^[A-Z]\.$|^[IVX]+\.$")
RE_DOBANDA = re.compile(r"dob[âa]nd|interest\s+(rate|on)|\bDAE\b|rata\s+anual", re.I)
# Nu tot ce e scris in lista de tarife e un comision. Verificarea de mana a gasit
# 3 din 24: o limita de tranzactionare si doua rate de dobanda raportate ca
# preturi. Categoria nu arunca valoarea — o marcheaza, ca sa nu intre in
# comparatia de comisioane.
RE_LIMITA = re.compile(
    r"limit[ăae]\w*\s+de\s+tranzac|valoare\s+tranzac|num[ăa]r\w*\s+de\s+tranzac"
    r"|\bplafon", re.I)
RE_CURS = re.compile(r"curs\s+(de\s+)?schimb|curs\s+bnr|exchange\s+rate", re.I)
# Randurile din cuprins ("CONTURI CURENTE ... PAG. 3") arata ca titluri de
# sectiune si deveneau sectiuni: BCR PDAI avea "PACHET DE SERVICII PAG. 7".
RE_CUPRINS = re.compile(r"\bpag\.?\s*\d+\b", re.I)
# o celula care e doar semn de lista nu e eticheta ("•" ajunsese numele a 15
# servicii la BRCI)
RE_DOAR_ORNAMENT = re.compile(r"^[\s•·○▪\-–—~*+.,:;()\[\]/]*$")
# semne ca un rand continua fraza de deasupra, nu incepe un nume nou
RE_CONTINUARE = re.compile(r"^[a-zăâîșț(\[]")
RE_TERMINA_DESCHIS = re.compile(
    r"(\b(si|sau|de|la|in|pe|cu|din|prin|pentru|c[ăa]tre|[îi]n|[şs]i)|[-–/,:])\s*$", re.I)

# Un titlu cu majuscule trebuie sa se si intinda peste tabel. Fara conditia de
# latime, orice fragment de eticheta rupt pe randul lui trecea drept titlu ("SEPA",
# "PLATINUM", "CIP;") si, mai rau, fura numele serviciului: la detectarea unei
# sectiuni tamponul de eticheta se goleste.
LATIME_MIN_TITLU = 0.55
# Un titlu cu majuscule are cel puțin atatea litere. Codurile de moneda si
# abrevierile ("USD/", "ATM", "SEPA", "CIP") stau singure pe un rand si treceau
# drept sectiuni, luand cu ele numele serviciului: "USD/" ajunsese sectiunea cu
# cele mai multe valori din documentul BRD.
LITERE_MIN_TITLU = 6
# Un rand fara nicio coloana e fie o linie de tabel simplu, fie un paragraf de
# conditii contractuale. Peste atatea cuvinte e proza, si procentele din ea sunt
# clauze de penalizare, nu tarife (masurat pe TBI).
CUVINTE_MAX_RAND_UNIC = 12
# Antetul si subsolul paginii se repeta la aceeasi inaltime pe majoritatea
# paginilor. Fara filtru, "Phoenix Tower, Calea Vitan 6-6A..." ajungea numele
# serviciului pentru 23 de comisioane.
REPETARE_MOBILIER = 0.4
MARGINE_MOBILIER = 0.08


# Multe liste de tarife nu scriu spatiile in PDF: la toleranta implicita de 3
# puncte, pdfplumber lipea cuvintele ("OPERATIUNIFARANUMERAR", "SchimbarecodPIN").
# Masurat pe Ghid_tarife BRD: la 1,5 lipiturile scad de la 168 la 6, iar cuvintele
# rupte greșit cresc doar de la 24 la 45 din 5058. Documentele care au spatii reale
# nu sunt afectate deloc (Tarif_standard BCR: identic la orice toleranta).
TOL_ORIZONTALA = 1.5


def randuri_de_cuvinte(pagina, toleranta=3):
    """Cuvintele grupate pe randuri de text, in ordinea paginii."""
    grupe = {}
    for w in pagina.extract_words(use_text_flow=False, x_tolerance=TOL_ORIZONTALA):
        grupe.setdefault(round(w["top"] / toleranta), []).append(w)
    return [sorted(grupe[k], key=lambda w: w["x0"]) for k in sorted(grupe)]


def margini_la(vert, y, toleranta=TOL_BORDURA):
    """Bordurile verticale prezente la inaltimea y, grupate."""
    poz = sorted(e["x0"] for e in vert
                 if e["bottom"] - e["top"] >= INALTIME_MIN_BORDURA
                 and e["top"] - 1 <= y <= e["bottom"] + 1)
    out = []
    for x in poz:
        if not out or x - out[-1] > toleranta:
            out.append(round(x, 1))
    return out


def gol_minim_rand(cuvinte):
    """Cat de mare trebuie sa fie un gol ca sa desparta coloane, pe acest rand.

    Derivat din rand, nu fix: documentele au corpuri de litera intre 6 si 12
    puncte, deci un prag fix ar rupe randurile dese si ar lipi randurile rare.
    """
    goluri = [b["x0"] - a["x1"] for a, b in zip(cuvinte, cuvinte[1:])]
    goluri = [g for g in goluri if g > 0]
    if not goluri:
        return 8.0
    return max(8.0, 4 * statistics.median(goluri))


def secvente(cuvinte, gol_minim):
    """Cuvintele grupate in secvente de text continuu: (x0, x1, cuvinte)."""
    grupuri = [[cuvinte[0]]]
    for a, b in zip(cuvinte, cuvinte[1:]):
        if b["x0"] - a["x1"] >= gol_minim:
            grupuri.append([b])
        else:
            grupuri[-1].append(b)
    return [(g[0]["x0"], g[-1]["x1"], g) for g in grupuri]


def rupe_la_borduri(secv, margini):
    """Rupe o secventa acolo unde o bordura cade intre doua cuvinte.

    O bordura nu taie niciodata un cuvant: daca trece prin mijlocul unuia, nu e
    bordura pentru randul acesta (celula e unita peste ea).
    """
    out = []
    for _x0, _x1, cuvinte in secv:
        bucata = [cuvinte[0]]
        for a, b in zip(cuvinte, cuvinte[1:]):
            if any(a["x1"] <= m <= b["x0"] for m in margini):
                out.append((bucata[0]["x0"], bucata[-1]["x1"], bucata))
                bucata = [b]
            else:
                bucata.append(b)
        out.append((bucata[0]["x0"], bucata[-1]["x1"], bucata))
    return out


def celule(cuvinte, margini):
    """Textul pe fiecare coloana: secventele repartizate dupa suprapunere.

    Repartizarea se face pe secventa, nu pe cuvant: numele unei coloane e adesea
    mai lat decat coloana insasi, iar centrul fiecarui cuvant in parte l-ar
    imprastia pe doua celule.
    """
    n = len(margini) - 1
    cos = [[] for _ in range(n)]
    for x0, x1, cuv in rupe_la_borduri(secvente(cuvinte, gol_minim_rand(cuvinte)),
                                       margini):
        acoperiri = [max(0.0, min(x1, margini[i + 1]) - max(x0, margini[i]))
                     for i in range(n)]
        if max(acoperiri, default=0) <= 0:
            continue    # text in afara tabelului: antet sau subsol de pagina
        cos[acoperiri.index(max(acoperiri))].append(" ".join(w["text"] for w in cuv))
    return [re.sub(r"\s+", " ", " ".join(c)).strip() for c in cos]


def margini_rand(vert, cuvinte):
    """Marginile de folosit pentru acest rand: borduri, altfel goluri, altfel una."""
    y = (min(w["top"] for w in cuvinte) + max(w["bottom"] for w in cuvinte)) / 2
    m = margini_la(vert, y)
    if len(m) >= 2:
        inauntru = sum(1 for w in cuvinte
                       if m[0] <= (w["x0"] + w["x1"]) / 2 <= m[-1])
        if inauntru >= ACOPERIRE_MIN * len(cuvinte):
            return m, "bordura"
    gol = gol_minim_rand(cuvinte)
    taieturi = [(a["x1"] + b["x0"]) / 2 for a, b in zip(cuvinte, cuvinte[1:])
                if b["x0"] - a["x1"] >= gol]
    capete = [cuvinte[0]["x0"] - 1, cuvinte[-1]["x1"] + 1]
    if taieturi:
        return [capete[0]] + taieturi + [capete[1]], "gol"
    return capete, "unic"


def _celula_eticheta(texte, analiza):
    """Indicele celulei care poarta numele serviciului, sau None.

    Nu e coloana 0: multe liste au o coloana de numerotare ("Nr. crt.") sau un
    semn de lista inaintea numelui, iar unele pun preturile in STANGA si
    descrierea in dreapta (tariful de evaluari al BCR). Se alege celula fara
    valoare cu cel mai mult text — numele serviciului e cel mai lung lucru de pe
    rand care nu e un preț.
    """
    candidate = [i for i, t in enumerate(texte)
                 if t and not RE_DOAR_INDEX.match(t)
                 and not RE_DOAR_ORNAMENT.match(t) and not analiza[i][0]]
    return max(candidate, key=lambda i: len(texte[i])) if candidate else None


def _e_continuare(text, precedent):
    """Randul continua numele de deasupra, in loc sa inceapa unul nou?

    Golul vertical nu poate decide aici, cum decide in formularul standardizat:
    acolo coloana de nume are randuri goale intre servicii, aici fiecare rand
    poarta un nume, deci toate randurile sunt la fel de apropiate. Ce rămane sunt
    doua semne de fraza rupta — randul incepe cu litera mica, sau cel de dinainte
    se termina cu o legatura.
    """
    return bool(RE_CONTINUARE.match(text)
                or (precedent and RE_TERMINA_DESCHIS.search(precedent)))


def _adauga_eticheta(blocuri, sus, jos, text, are_valori, gol_maxim=6):
    """Adauga un rand de eticheta la blocul curent, sau deschide unul nou.

    Blocurile sunt (sus, jos, text, e_parinte). Un rand cu valoare deschide
    intotdeauna bloc nou: intr-un tabel de tarife, randul cu preț ESTE randul
    logic. Un rand fara valoare continua numele de deasupra doar daca arata ca o
    continuare; altfel deschide un bloc de tip parinte, adica numele sub care
    urmeaza mai multe benzi de suma.
    """
    lipit = (blocuri and sus - blocuri[-1][1] <= gol_maxim
             and not are_valori and _e_continuare(text, blocuri[-1][2]))
    if lipit:
        a, _b, t, parinte = blocuri[-1]
        blocuri[-1] = (a, jos, f"{t} {text}", parinte)
    else:
        blocuri.append((sus, jos, text, not are_valori))


def _e_doar_banda(text):
    """Eticheta e doar o banda de suma, fara numele serviciului?

    "≤ 100.000 EUR", "- 100 LEI, inclusiv", "sub 49.999,99 lei" sunt etichete
    corecte, dar incomplete: serviciul e scris o data, deasupra, si dupa el vin
    mai multe benzi. Fara prefixul lui, valoarea nu se poate compara cu nimic.
    """
    rest = RE_PRAG.sub(" ", text)
    return len(re.findall(r"[A-Za-zĂÂÎȘȚăâîșț]", RE_DOAR_MONEDE.sub(" ", rest))) < 4


def _eticheta_pentru(sus, jos, blocuri):
    """Eticheta careia aparține o valoare, dupa poziția verticala.

    Suprapunerea decide cand exista, altfel cel mai apropiat centru. Ordinea de
    citire NU decide: coloana de preț e centrata vertical, coloana de nume e
    aliniata sus, deci valoarea se tiparește uneori deasupra numelui sau.
    """
    if not blocuri:
        return None
    lungime, minus_i = max((min(jos, b) - max(sus, a), -i)
                           for i, (a, b, _t, _p) in enumerate(blocuri))
    if lungime > 0:
        i = -minus_i
    else:
        centru = (sus + jos) / 2
        i = min(range(len(blocuri)),
                key=lambda k: abs((blocuri[k][0] + blocuri[k][1]) / 2 - centru))

    nume = blocuri[i][2]
    if _e_doar_banda(nume):
        parinti = [b[2] for b in blocuri[:i] if b[3] and not _e_doar_banda(b[2])]
        if parinti:
            nume = f"{parinti[-1]} {nume}"
    return nume


def categorie(sectiune, serviciu, text):
    """Ce fel de cifra e: comision, dobanda, limita de tranzactionare sau curs."""
    tot = f"{sectiune or ''} {serviciu or ''} {text or ''}"
    if RE_DOBANDA.search(tot):
        return "dobanda"
    if RE_LIMITA.search(tot):
        return "limita"
    if RE_CURS.search(tot):
        return "curs"
    return "comision"


def _desparte_index(text):
    """Indexul de la inceputul etichetei, separat de rest."""
    m = RE_INDEX_LA_INCEPUT.match(text)
    return (m.group(1), m.group(2)) if m else (None, text)


def _adancime(index):
    """Adancimea in ierarhie: "4.2." da 2, "7." da 1, "A." da 9 (frunza)."""
    if RE_LITERA_SAU_ROMAN.match(index):
        return 9
    return len([p for p in index.rstrip(".").split(".") if p])


class Sectiuni:
    """Ierarhia de titluri activa, pe adancimi."""

    def __init__(self):
        self.pe_adancime = {}
        self.ultima = None

    def pune(self, index, titlu):
        a = _adancime(index) if index else 1
        for mai_adanc in [k for k in self.pe_adancime if k > a]:
            del self.pe_adancime[mai_adanc]
        self.pe_adancime[a] = titlu
        self.ultima = a

    def alipeste(self, titlu):
        """Titlurile cu majuscule se rup pe doua randuri: "CONTURI CURENTE CU" / "SERVICII DE BAZA"."""
        if self.ultima is None:
            self.pune(None, titlu)
        else:
            self.pe_adancime[self.ultima] += " " + titlu

    def cale(self):
        return " > ".join(self.pe_adancime[k] for k in sorted(self.pe_adancime))


def _mobilier(randuri, npagini):
    """Textele de antet/subsol: aceeasi linie, in marginea paginii, pe multe pagini."""
    if npagini < 3:
        return set()
    pe_text = {}
    for nr, _cuvinte, _m, _g, texte, in_margine in randuri:
        if in_margine:
            pe_text.setdefault(" ".join(texte).strip(), set()).add(nr)
    prag = max(2, int(REPETARE_MOBILIER * npagini))
    return {t for t, pagini in pe_text.items() if t and len(pagini) >= prag}


def randuri_document(cale):
    """Randurile de tabel ale documentului, fara antetul si subsolul paginii.

    (nr_pagina, cuvinte, margini, geometrie, texte)
    """
    brute = []
    with pdfplumber.open(str(cale)) as pdf:
        npagini = len(pdf.pages)
        for nr_pagina, pagina in enumerate(pdf.pages, 1):
            vert = [e for e in pagina.edges if e["orientation"] == "v"]
            for cuvinte in randuri_de_cuvinte(pagina):
                margini, geometrie = margini_rand(vert, cuvinte)
                texte = celule(cuvinte, margini)
                if not any(texte):
                    continue
                y = min(w["top"] for w in cuvinte)
                in_margine = (y < MARGINE_MOBILIER * pagina.height
                              or y > (1 - MARGINE_MOBILIER) * pagina.height)
                brute.append((nr_pagina, cuvinte, margini, geometrie, texte,
                              in_margine))
    respinse = _mobilier(brute, npagini)
    return [r[:5] for r in brute if " ".join(r[4]).strip() not in respinse]


def _e_titlu(texte, nevide, margini, latime_tabel):
    """(index, titlu) daca randul e un titlu de sectiune, altfel None."""
    if len(nevide) != 1:
        return None
    i = nevide[0]
    t = texte[i]
    if len(t) > 90 or not re.search(r"[A-Za-zĂÂÎȘȚăâîșț]{3}", t):
        return None
    if t.endswith(",") or RE_DOAR_MONEDE.match(t):
        return None     # fragment de fraza, sau un rand de antet cu monede
    m = RE_INDEX_SECTIUNE.match(t)
    if m:
        return m.group(1), m.group(2)
    # latimea CELULEI, nu a tabelului: un titlu se intinde peste tabel, iar
    # "EUR" sau "ATM" intr-o celula ingusta a unui tabel lat nu e titlu — cu
    # latimea tabelului treceau amandoua si stergeau numele serviciului
    latime_celula = margini[i + 1] - margini[i]
    intins = latime_tabel and latime_celula >= LATIME_MIN_TITLU * latime_tabel
    destul = len(re.findall(r"[A-Za-zĂÂÎȘȚ]", t)) >= LITERE_MIN_TITLU
    if t == t.upper() and intins and destul:
        return None, t
    return None


# o suma cu moneda dupa ea; moneda urmata de cifra ("lei2") e nota de subsol, nu suma
RE_SUMA_CU_MONEDA = re.compile(
    r"\d[\d.,]*\s*(?:lei|ron|eur|euro|usd|gbp|chf)(?![a-z])", re.I)


def _e_rand_antet(texte, nevide, dupa_valori):
    """Randul fara valori e chiar antetul coloanelor, nu continuarea unei celule.

    Regula "mai multe celule, niciuna cu valoare" nu ajunge. La Salt, matricea are
    pe coloane nivelurile de card (Standard / Platinum), iar celulele de valoare se
    rup pe trei-patru randuri: "GRATUIT" / "in limita primelor 5 retrageri" / "sau
    pana la 1.500 RON/luna" / "(oricare limita este atinsa prima)". Randurile de
    continuare n-au valoare si au mai multe celule, deci intrau la antet si se
    lipeau peste el — de acolo antete-fraza ca "Standard in limita primelor 5
    retrageri sau pana la 1.500 RON/luna".

    Semnul e acelasi folosit deja la continuarea etichetelor (_e_continuare):
    continuarea unei fraze incepe cu litera mica sau cu paranteza, un nume de
    coloana nu.

    Dar litera mica singura taia si antete reale: la BCR, antetul "Națională și
    internațională" e pe doua randuri, iar al doilea incepe cu "i" mic si era
    respins. Rezultat: antetul rămanea "Națională și", iar 12 valori primeau
    destinatia `national` cand comisionul se aplica la amandoua.

    Ce le separa e poziția: un antet se continua INAINTE de primul rand cu valori
    al tabelului, o celula de valoare se continua DUPA. Deci regula literei mici se
    aplica doar dupa ce tabelul a inceput sa dea valori.
    """
    if len(nevide) < 2 or max(nevide) < 1:
        return False
    if dupa_valori and any(RE_CONTINUARE.match(texte[i]) for i in nevide):
        return False
    # Un rand cu benzi de suma nu e antet, e chiar randul de preturi — dar unul ale
    # carui cifre au fost consumate de RE_PRAG, deci pare fara valori. La BCR,
    # "Taxa de emitere | 50-100 lei | 5 – 100 lei | 30 – 500 lei" ajungea antet, si
    # era al doilea cel mai frecvent din document. Aici "50-100 lei" nu e o banda
    # de prag, e intervalul de pret al cardului — ambiguitate reala in sursa, dar
    # oricum nu e numele coloanei.
    if any(RE_PRAG.search(texte[i]) for i in nevide):
        return False
    # ...si nici o cifra lipita de o moneda: "3 USD 2,5 GBP 3 CHF" si "12 USD/" sunt
    # randuri de preturi in valute pe care RE_PRAG nu le prinde (n-au banda). Un nume
    # de coloana poate conține moneda ("NOIR LEI", "Visa lei"), dar nu o suma.
    if any(RE_SUMA_CU_MONEDA.search(texte[i]) for i in nevide):
        return False
    return True


# Un nume de coloana mai lung de atat nu mai e un nume. Antetele se acumuleaza pe
# mai multe randuri (la BCR, "MasterCard Corporate Ron" / "LEI" / "Nationala si
# internationala" sunt trei randuri ale aceluiasi antet), iar fara limita
# acumularea inghite si randuri care nu erau antet.
LUNGIME_MAX_ANTET = 48


def _aduna_antet(vechi, nou):
    """Lipeste randul nou de antet la ce s-a strans deja, pana la limita."""
    if not nou:
        return vechi
    if not vechi:
        return nou.strip()
    if len(vechi) >= LUNGIME_MAX_ANTET:
        return vechi        # antetul e deja intreg; ce urmeaza nu mai e nume de coloana
    return f"{vechi} {nou}".strip()


def extrage_tarife(cale, banca, radacina=None):
    """Inregistrarile de comision dintr-o lista de tarife nestandardizata."""
    cale = Path(cale)
    sursa = str(cale.relative_to(radacina)) if radacina else cale.name
    randuri = randuri_document(cale)
    latime_tabel = max((m[-1] - m[0] for _n, _c, m, _g, _t in randuri), default=0)

    sectiuni = Sectiuni()
    antete = {}          # semnatura de coloane -> numele coloanelor
    # Prima trecere strange randurile cu valori si construieste blocurile de
    # eticheta. Doua treceri sunt necesare, nu comode: continuarea unui nume poate
    # veni DUPA randul cu valoarea ("...pentru retragere" / "0,5% + 2,50 RON" /
    # "numerar"), iar intr-o singura trecere randul de valoare se emitea inainte ca
    # numele sa fie intreg — de acolo si numele trunchiat si fragmentul "numerar"
    # lipit la serviciul urmator.
    de_emis = []
    blocuri_et = []      # blocurile active; se reinnoiesc la sectiune sau pagina

    # semnaturile de coloane care au dat deja o valoare: dupa ele, un rand cu
    # litera mica e continuare de celula, nu de antet (vezi _e_rand_antet)
    semn_cu_valori = set()
    rand_titlu_caps = None    # randul ultimului titlu cu majuscule, pentru alipire
    pagina_anterioara = None
    for k, (nr_pagina, cuvinte, margini, geometrie, texte) in enumerate(randuri):
        # un rand fara nicio coloana si cu multe cuvinte e proza, nu tarif
        if geometrie == "unic" and len(cuvinte) > CUVINTE_MAX_RAND_UNIC:
            continue
        if RE_CUPRINS.search(" ".join(texte)):
            continue          # rand din cuprins, nu din tabel

        sus = min(w["top"] for w in cuvinte)
        jos = max(w["bottom"] for w in cuvinte)
        if pagina_anterioara != nr_pagina:
            blocuri_et = []          # pagina noua, alte poziții verticale
        pagina_anterioara = nr_pagina

        analiza = [analizeaza_linie(t) for t in texte]
        are_valori = any(v for v, _p, _f, _d in analiza)
        nevide = [i for i, t in enumerate(texte)
                  if t and not RE_DOAR_INDEX.match(t)]

        if not are_valori:
            titlu = _e_titlu(texte, nevide, margini, latime_tabel)
            if titlu:
                index, text = titlu
                if index is None and rand_titlu_caps == k - 1:
                    sectiuni.alipeste(text)
                else:
                    sectiuni.pune(index, text)
                rand_titlu_caps = k if index is None else None
                antete.clear()      # tabel nou, antetul vechi nu se mai aplica
                semn_cu_valori.clear()   # si tabelul nou n-a dat inca valori
                blocuri_et = []     # si alte etichete
                continue
            # antet de matrice: mai multe nume de coloana, niciunul cu valoare
            if _e_rand_antet(texte, nevide,
                             tuple(round(m) for m in margini) in semn_cu_valori):
                semn = tuple(round(m) for m in margini)
                vechi = antete.get(semn) or [""] * len(texte)
                if len(vechi) != len(texte):
                    vechi = [""] * len(texte)
                antete[semn] = [_aduna_antet(a, b) for a, b in zip(vechi, texte)]
                continue
            i_eticheta = _celula_eticheta(texte, analiza)
            if i_eticheta is not None:
                _adauga_eticheta(blocuri_et, sus, jos, texte[i_eticheta], False)
            continue

        # rand cu valori: eticheta lui poate continua si pe randurile urmatoare
        i_eticheta = _celula_eticheta(texte, analiza)
        if i_eticheta is not None:
            _adauga_eticheta(blocuri_et, sus, jos, texte[i_eticheta], True)
        semn_cu_valori.add(tuple(round(m) for m in margini))
        de_emis.append((nr_pagina, sus, jos, texte, analiza, geometrie,
                        blocuri_et, sectiuni.cale() or None,
                        antete.get(tuple(round(m) for m in margini), [])))

    # A doua trecere: acum fiecare bloc de eticheta e intreg
    inregistrari = []
    serviciu = None
    conditie = frecventa = None
    for (nr_pagina, sus, jos, texte, analiza, geometrie, etichete_active,
         sectiune, antet) in de_emis:
        gasita = _eticheta_pentru(sus, jos, etichete_active)
        if gasita:
            _index, eticheta = _desparte_index(gasita.strip())
            # indexul randului urmator se lipeste la coada ("pe adresa BCR 3.2.7.")
            eticheta = RE_INDEX_LA_SFARSIT.sub("", eticheta).strip()
            if eticheta and not RE_DOAR_INDEX.match(eticheta):
                serviciu = re.sub(r"\s+", " ", eticheta)[:160]
        for i, (valori, prag, frecv, _d) in enumerate(analiza):
            if prag:
                conditie = prag
            if frecv:
                frecventa = frecv
            for tip, val, moneda, rol in valori:
                inregistrari.append({
                    "banca": banca,
                    "sectiune": sectiune,
                    "serviciu": serviciu,
                    "coloana": (antet[i] or None) if i < len(antet) else None,
                    "tip": tip,
                    "valoare": val,
                    "moneda": moneda,
                    "frecventa": frecventa,
                    "conditie": conditie,
                    # vezi rol_de_conditie in parser_pdf: cifrele care sunt cerinte
                    # sau limite, nu preturi, ies din comparatie dar se pastreaza
                    "rol": rol_de_conditie(texte[i], serviciu, val) or rol,
                    "categorie": categorie(sectiune, serviciu,
                                           f"{texte[i]} {antet[i] if i < len(antet) else ''}"),
                    "sursa_pdf": sursa,
                    "pagina": nr_pagina,
                    "geometrie": geometrie,
                    "text_sursa": texte[i][:300],
                })
            if valori:
                # conditia se consuma dupa comisionul pe care il conditioneaza
                conditie = None
                frecventa = None
    return inregistrari
