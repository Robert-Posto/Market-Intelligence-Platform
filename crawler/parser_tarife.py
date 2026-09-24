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
from collections import defaultdict
from pathlib import Path

import pdfplumber

from crawler.parser_pdf import (BANI, MONEDE, RE_PRAG, VAL, _e_subpunct,
                                analizeaza_linie, categorie, rol_de_conditie, suma_bani)

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
# acelasi index, dar singur in celula lui; fara litere ("a." e semn de lista)
RE_INDEX_CELULA = re.compile(r"^(?:\d+(?:\.\d+)*\.|[IVX]+\.)$")
RE_DOAR_MONEDE = re.compile(r"^(?:\s*(?:lei|leu|ron|eur|euro|usd|gbp|chf)\s*[/,;]?)+$",
                            re.I)
RE_INDEX_LA_SFARSIT = re.compile(r"\s+\d+(?:\.\d+){1,}\.?$")
RE_LITERA_SAU_ROMAN = re.compile(r"^[A-Z]\.$|^[IVX]+\.$")
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
# ...dar "PLATI" are 5 si e un titlu adevarat: la Vista, fara el, platile
# interbancare de sub el (10,51 si 20,51 lei) ramaneau sub "INCASARI" si ieseau
# incasari
RE_TITLU_SCURT = re.compile(r"^\W*PL[ĂA][ȚŢT]I\W*$")
# Un rand fara nicio coloana e fie o linie de tabel simplu, fie un paragraf de
# conditii contractuale. Peste atatea cuvinte e proza, si procentele din ea sunt
# clauze de penalizare, nu tarife (masurat pe TBI).
CUVINTE_MAX_RAND_UNIC = 12
# Antetul si subsolul paginii se repeta la aceeasi inaltime pe majoritatea
# paginilor. Fara filtru, "Phoenix Tower, Calea Vitan 6-6A..." ajungea numele
# serviciului pentru 23 de comisioane.
REPETARE_MOBILIER = 0.4
MARGINE_MOBILIER = 0.08


# Titlul unei liste de tarife, citit din pagina, nu din numele fisierului. Numele
# minte sau lipsește: Nexent isi publica listele cu nume-hash
# ("fdab3b17d18...pdf"), Vista isi numeste lista "Anexa_1_CGA", ProCredit
# "LISTA-PRETURI". Masurat pe cele 487 de PDF-uri din 23 sept: 17 liste de tarife
# nu erau citite deloc, iar Nexent si Vista ieseau fara niciun comision.
# Ancorat la inceput de rand: in corpul unui contract "conform Listei de tarife"
# e o trimitere, nu un titlu.
RE_TITLU_TARIFE = re.compile(
    r"^\W*(?:anexa\s*\d*\W*)?"
    r"(?:list[ăa]\s+(?:de\s+)?(?:taxe|taxelor|tarife|tarifelor|comisioane|comisioanelor"
    r"|pre[țt]uri)"
    r"|tarife\s*(?:,|[șsş]i)\s*(?:comisioane|taxe|termeni)"
    r"|(?:taxe|dob[âa]nzi)\s*,\s*comisioane"
    r"|comisioane\s*(?:,|[șsş]i)\s*(?:taxe|tarife|speze)"
    r"|ghid\w*\s+(?:de\s+)?tarife)", re.I)
# titlul sta sus pe prima pagina; la Vista abia dupa un paragraf de avertisment
RANDURI_TITLU = 15


def e_lista_tarife(cale):
    """Prima pagina are, sus, titlul unei liste de tarife?"""
    try:
        with pdfplumber.open(str(cale)) as pdf:
            text = (pdf.pages[0].extract_text() or "") if pdf.pages else ""
    except Exception:
        return False
    randuri = [r for r in text.splitlines() if r.strip()][:RANDURI_TITLU]
    return any(RE_TITLU_TARIFE.search(r) for r in randuri)


# Multe liste de tarife nu scriu spatiile in PDF: la toleranta implicita de 3
# puncte, pdfplumber lipea cuvintele ("OPERATIUNIFARANUMERAR", "SchimbarecodPIN").
# Masurat pe Ghid_tarife BRD: la 1,5 lipiturile scad de la 168 la 6, iar cuvintele
# rupte greșit cresc doar de la 24 la 45 din 5058. Documentele care au spatii reale
# nu sunt afectate deloc (Tarif_standard BCR: identic la orice toleranta).
TOL_ORIZONTALA = 1.5


# Exponentul unei note ("plată4", "RON1", "lei2") are baza cu 3,8-5,4 pt deasupra
# literelor de langa el. Doua marimi de litera pe aceeasi linie ("2,595" la 10 pt,
# "%," la 10,6 pt, ProCredit) difera cu 0,15 pt, iar TBI are un rand cu baza
# urcata cu 1,06 pt la mijlocul lui "set-up": acelea nu sunt exponenti.
TOL_LINIE_DE_BAZA = 2


# Toate tolerantele din fisier sunt in puncte de pagina A4. Lista Raiffeisen IMM
# (6f118df0) e scanata la 300 dpi: pagini de 3508x2480 pt, litere de 40 pt, deci
# de 4,17 ori mai mare. Acolo 3 pt nu mai tin un rand laolalta: cifrele si moneda
# cadeau pe randuri diferite ("0,5 lei" si "1" in loc de 0,51 lei, "1 lei" in loc
# de 10, "5" fara "LEI"), iar initiala intr-un font substituit, cu 5,5 pt mai jos,
# rupea "Executare" in "E" si "xecutare". Doar peste 1,5: A5 (0,71, litere de
# 7 pt) si prezentarea 1024x768 a BCR (1,22) au litere obisnuite.
LATURA_A4 = 842
SCARA_MIN = 1.5


def _scara(pagina):
    k = max(pagina.width, pagina.height) / LATURA_A4
    return k if k > SCARA_MIN else 1


def _la_scara(obiect, k):
    """Obiectul (cuvant, litera, bordura) cu coordonatele aduse la A4."""
    if k == 1:
        return obiect
    return dict(obiect, **{c: obiect[c] / k for c in ("x0", "x1", "top", "bottom")})


def _top_rand(litere):
    """Top-ul literelor de pe linia de baza a cuvantului, fara exponent."""
    baza = max(c["bottom"] for c in litere)
    return min(c["top"] for c in litere if c["bottom"] > baza - TOL_LINIE_DE_BAZA)


def randuri_de_cuvinte(pagina, toleranta=3, k=1):
    """Cuvintele grupate pe randuri de text, in ordinea paginii.

    Randul unui cuvant se da dupa literele lui de pe linia de baza, nu dupa
    top-ul cuvantului. Exponentul lipit ("plată4", "RON1", "Bank9", "banci)13")
    ridica top-ul cu 0,5-2,3 pt; peste o granita de galeata cuvantul cadea pe
    alt rand, iar valoarea ramanea cu eticheta "RON1" sau "curent1", ori lua
    randul vecin (ProCredit: "Anulare plată" ajungea "Investigații plăți").

    Nu mediana top-urilor: la ProCredit ea muta "2,595%," (cifre la 10 pt, "%"
    la 10,6) peste granita, rupea un rand de proza in doua si scotea 6 valori
    false ("1 EURO = 5.2430 RON" citit 2.430 lei). Nici gruparea in lant (rand
    nou doar dupa un gol de 3 pt): lipea pretul centrat pe verticala de randul
    etichetei, 25 de concepte pierdute si 27 mutate ("Taxă anuală de
    administrare card" ajungea retragere_numerar la Raiffeisen). Galeata
    ramane; se schimba doar cheia cuvintelor cu exponent.

    Coordonatele ies aduse la A4 (vezi _scara), cu k al paginii.

    Textul din afara paginii (pasteboard, x<0 sau x>latime) ramane deocamdata.
    Taiat, cele doua depuneri gratuite Raiffeisen IMM pierdeau eticheta falsa
    "Interbancar" (x=-717) si luau titlul tabelului, "Comisioane depunere și
    retragere numerar", deci retragere_numerar: celula lor de nume e citita ca
    valoare ("Depunere gratuit la MFM-uri"). within_bbox e si mai rau: scoate
    bordurile care ies putin din pagina (BRD: 104 concepte pierdute).
    """
    grupe = {}
    for w in pagina.extract_words(use_text_flow=False, x_tolerance=TOL_ORIZONTALA * k,
                                  y_tolerance=3 * k, return_chars=True):
        litere = [_la_scara(c, k) for c in w.pop("chars")]
        grupe.setdefault(round(_top_rand(litere) / toleranta), []).append(_la_scara(w, k))
    return [sorted(grupe[g], key=lambda w: w["x0"]) for g in sorted(grupe)]


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

    Cu doua goluri, mediana e media lor, iar de patru ori media e mereu peste
    golul mare: un rand de trei cuvinte fara borduri nu se rupea niciodata.
    Spatiul dintre cuvinte e golul mic. La Garanti, "Închidere cont Gratuit" si
    "Schimb valutar Gratuit" erau o singura celula, iar valoarea lua eticheta
    vecinului (extras_de_cont, transfer_credit); la Raiffeisen IMM la fel
    "Discrepante 100 euro" si "Abonament lunar gratuit".
    """
    goluri = [b["x0"] - a["x1"] for a, b in zip(cuvinte, cuvinte[1:])]
    goluri = [g for g in goluri if g > 0]
    if not goluri:
        return 8.0
    spatiu = min(goluri) if len(goluri) == 2 else statistics.median(goluri)
    return max(8.0, 4 * spatiu)


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


def _celula_eticheta(texte, analiza, coloane_pret=frozenset()):
    """Indicele celulei care poarta numele serviciului, sau None.

    Nu e coloana 0: multe liste au o coloana de numerotare ("Nr. crt.") sau un
    semn de lista inaintea numelui, iar unele pun preturile in STANGA si
    descrierea in dreapta (tariful de evaluari al BCR). Se alege celula fara
    valoare cu cel mai mult text — numele serviciului e cel mai lung lucru de pe
    rand care nu e un preț.

    Textul din `coloane_pret` (vezi coloane_de_pret) e coada celulei de preț, nu
    un nume. BCR scrie "min. 1 LEI/" pe un rand si "tranzacție" pe urmatorul, iar
    "tranzacție", "operațiune" si "nepermisă" ajunsesera nume de serviciu.
    """
    candidate = [i for i, t in enumerate(texte)
                 if t and i not in coloane_pret and not RE_DOAR_INDEX.match(t)
                 and not RE_DOAR_ORNAMENT.match(t) and not analiza[i][0]]
    return max(candidate, key=lambda i: len(texte[i])) if candidate else None


def coloana_numelui(randuri, analize):
    """Pe fiecare tabel (semnatura de coloane), coloana cu cel mai mult text fara pret.

    Ea nu e niciodata coloana de pret, chiar daca o eticheta are o cifra: la Libra,
    "Dobanda cont curent de card (...500 RON)" facea coloana numelui sa para de
    pret, iar randul urmator ramanea fara nume.

    Se numara o data, pe tot tabelul. Numarata din mers, dupa alegerile facute pana
    atunci, o greseala se autointretinea: la BCR, "operațiune" ales o data drept
    nume facea din coloana lui "coloana numelui", si "tranzacție" ramanea numele a
    23 de valori.
    """
    exces = defaultdict(lambda: defaultdict(int))    # texte fara pret - valori
    for (_n, _c, margini, _g, texte), analiza in zip(randuri, analize):
        semn = tuple(round(m) for m in margini)
        for i, t in enumerate(texte):
            if t and not RE_DOAR_INDEX.match(t):
                exces[semn][i] += -1 if analiza[i][0] else 1
    return {semn: max(pe_col, key=pe_col.get) for semn, pe_col in exces.items()
            if max(pe_col.values()) > 0}


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


def _adauga_eticheta(blocuri, sus, jos, text, are_valori, gol_maxim=6, x=None):
    """Adauga un rand de eticheta la blocul curent, sau deschide unul nou.

    Blocurile sunt (sus, jos, text, e_parinte, x); x e marginea stanga a celulei,
    None cand nu se stie (vezi _celula_din_stanga). Un rand cu valoare deschide bloc
    nou: intr-un tabel de tarife, randul cu preț ESTE randul logic. Un rand fara
    valoare continua numele de deasupra doar daca arata ca o continuare; altfel
    deschide un bloc de tip parinte, adica numele sub care urmeaza mai multe
    benzi de suma.

    Exceptia e numele inceput pe un rand FARA pret si continuat pe randul cu
    pret: la BRD, "Pret pachet /luna cu" / "indeplinirea conditie 0 lei/luna" /
    "de pachet". Pretul sta pe randul din mijloc, iar ca bloc nou ramanea cu
    numele "indeplinirea conditie de pachet", fara pachet si fara pret.
    """
    ultim = blocuri[-1] if blocuri else None
    lipit = ultim and sus - ultim[1] <= gol_maxim and _e_continuare(text, ultim[2])
    if lipit and are_valori:
        # ...dar nu cand randul de deasupra deschide o lista ("Utilizare ATM/POS
        # alte banci – retragere numerar:") sau randul e chiar un subpunct: acolo
        # primul element s-ar lipi de parinte, iar celelalte ar ramane fara el
        lipit = (ultim[3] and not _e_subpunct(text)
                 and not ultim[2].rstrip().endswith(":"))
    if lipit:
        a, _b, t, parinte = ultim[:4]
        blocuri[-1] = (a, jos, f"{t} {text}", parinte and not are_valori, _x(ultim))
    else:
        blocuri.append((sus, jos, text, not are_valori, x))


def _x(bloc):
    return bloc[4] if len(bloc) > 4 else None


# Ce ramane dintr-o banda dupa ce se scot sumele. RE_DOAR_MONEDE e ancorat pe tot
# textul, deci nu scotea "LEI" din "- 100 LEI, inclusiv" — exemplul chiar din
# docstring-ul de mai jos nu era recunoscut, iar benzile BCR ramaneau fara
# numele serviciului de deasupra.
RE_CUVINTE_BANDA = re.compile(
    r"\b(?:lei|leu|ron|eur|euro|usd|gbp|chf|inclusiv|exclusiv|echiv\w*)\b", re.I)


def _e_doar_banda(text):
    """Eticheta e doar o banda de suma, fara numele serviciului?

    "≤ 100.000 EUR", "- 100 LEI, inclusiv", "sub 49.999,99 lei" sunt etichete
    corecte, dar incomplete: serviciul e scris o data, deasupra, si dupa el vin
    mai multe benzi. Fara prefixul lui, valoarea nu se poate compara cu nimic.
    """
    rest = RE_CUVINTE_BANDA.sub(" ", RE_PRAG.sub(" ", text))
    return len(re.findall(r"[A-Za-zĂÂÎȘȚăâîșț]", rest)) < 4


def _eticheta_pentru(sus, jos, blocuri, parinte_stanga=None):
    """Eticheta careia aparține o valoare, dupa poziția verticala.

    Suprapunerea decide cand exista, altfel cel mai apropiat centru. Ordinea de
    citire NU decide: coloana de preț e centrata vertical, coloana de nume e
    aliniata sus, deci valoarea se tiparește uneori deasupra numelui sau.
    """
    if not blocuri:
        return None
    lungime, minus_i = max((min(jos, b[1]) - max(sus, b[0]), -i)
                           for i, b in enumerate(blocuri))
    if lungime > 0:
        i = -minus_i
    else:
        centru = (sus + jos) / 2
        i = min(range(len(blocuri)),
                key=lambda k: abs((blocuri[k][0] + blocuri[k][1]) / 2 - centru))

    nume = blocuri[i][2]
    banda, subpunct = _e_doar_banda(nume), _e_subpunct(nume)
    # Varianta dintr-o coloana din dreapta isi ia intai numele din celula cu
    # bordura din stanga. "Ultimul parinte de deasupra" greseste acolo unde celula
    # din stanga e centrata: la Nexent, randul "FX 0,5%" al retragerilor lua
    # "Depuneri de numerar", fiindca "Retrageri de numerar" e scris sub el.
    parinte = None
    if (parinte_stanga and _x(blocuri[i]) is not None
            and (banda or subpunct or _e_varianta(nume))):
        parinte = parinte_stanga(_x(blocuri[i]))
    if parinte:
        nume = f"{parinte} {nume}"
    elif banda or subpunct:
        parinti = [b[2] for b in blocuri[:i] if b[3] and not _e_doar_banda(b[2])
                   and not _e_subpunct(b[2])]
        # Subpunctul cere un nume intreg: coada unei fraze ("pentru care retragerea
        # a fost programată)") ajunsese parinte. Banda simpla nu: la BRD parintele
        # ei chiar incepe cu litera mica ("debit (cecuri si bilete la ordin) LEI"),
        # si fara el 6 valori treceau de la file_cec la transfer_credit. "În USD"
        # e si banda si subpunct, si cere nume intreg (Garanti, 8 valori).
        if subpunct:
            parinti = [p for p in parinti if not RE_CONTINUARE.match(p)]
        if parinti:
            nume = f"{parinti[-1]} {nume}"
    elif (RE_CONTINUARE.match(nume) and i > 0
          and blocuri[i - 1][1] >= blocuri[i][0] - LIPIRE_CONTINUARE):
        # Continuarea care are pret pe randul ei deschide bloc nou, deci pierdea
        # inceputul: BCR "Emiterea unui Card de debit/ (furnizarea)" + "(principal)",
        # iar "(principal)21" ramanea numele a 7 valori.
        nume = f"{blocuri[i - 1][2]} {nume}"
    return nume


# Cat de mult in dreapta trebuie sa stea varianta fata de marginea tabelului.
# Coloanele de nume si de varianta sunt la zeci de puncte (BCR: 36 si 239).
DX_VARIANTA = 40
# blocul de deasupra atinge continuarea: randurile aceleiasi celule se ating sau se
# suprapun, cele din celule diferite au intre ele padding-ul celulei
LIPIRE_CONTINUARE = 3
# peste atat, "celula" dintre doua borduri e de fapt o pagina fara borduri
INALTIME_MAX_CELULA = 150
CUVINTE_MAX_PARINTE = 15


def _celula_din_stanga(geometrie_pagina, stanga, xv, sus, jos):
    """Textul celulei cu bordura din stanga variantei, care cuprinde randul ei.

    BCR pune serviciul in prima coloana si canalul in a doua: "Depunere de numerar
    în contul Clientului" cuprinde randurile "Unități Bancare" si "MFM", fiecare cu
    pretul lui, iar eticheta randului era doar canalul (12 valori fara serviciu).
    Decide bordura, nu apropierea: celula din stanga e centrata pe verticala, iar
    "Casa de schimb" sta mai aproape de numele grupului URMATOR ("Retrageri de
    numerar") decat de al sau ("Depunere de monedă metalică"). Fara borduri nu se
    ghiceste nimic: dupa gol, trei servicii Nexent de pe randuri vecine se lipeau.
    """
    orizontale, cuvinte = geometrie_pagina
    cx, cy = (stanga + xv) / 2, (sus + jos) / 2
    # fata de mijlocul randului: literele ies cu un punct peste bordura de jos
    acopera = [t for t, x0, x1 in orizontale if x0 - 1 <= cx <= x1 + 1]
    sus_c = max((t for t in acopera if t <= cy), default=None)
    jos_c = min((t for t in acopera if t >= cy), default=None)
    if sus_c is None or jos_c is None or jos_c - sus_c > INALTIME_MAX_CELULA:
        return None
    din_celula = sorted((w for w in cuvinte
                         if stanga - 1 <= (w["x0"] + w["x1"]) / 2 < xv - 2
                         and sus_c < (w["top"] + w["bottom"]) / 2 < jos_c),
                        key=lambda w: w["top"])
    linii = []
    for w in din_celula:
        if linii and w["top"] - linii[-1][0]["top"] <= 3:
            linii[-1].append(w)
        else:
            linii.append([w])
    text = " ".join(w["text"] for linie in linii
                    for w in sorted(linie, key=lambda w: w["x0"]))
    # O celula cu preturi nu e un nume (Eximbank: "Utilizare ATM Exim Banca 0,2 %
    # minim 5 0 Lei..."), iar una cu zeci de cuvinte e un tabel intreg fara borduri
    # interioare (BRD: "MyBRD SMS atasat unui cont curent/ de economii/ ...").
    if not text or analizeaza_linie(text)[0] or len(text.split()) > CUVINTE_MAX_PARINTE:
        return None
    return text


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

    def subtitlu(self, titlu):
        """Titlul unui grup din interiorul tabelului: sub toate titlurile reale."""
        self.pe_adancime[ADANCIME_SUBTITLU] = titlu

    def inchide_subtitlu(self):
        self.pe_adancime.pop(ADANCIME_SUBTITLU, None)

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


def randuri_document(cale, geometrie_pagini=None):
    """Randurile de tabel ale documentului, fara antetul si subsolul paginii.

    (nr_pagina, cuvinte, margini, geometrie, texte). Daca primeste un dict, il
    umple cu {nr_pagina: (borduri orizontale, cuvinte)} pentru _celula_din_stanga.
    """
    brute = []
    with pdfplumber.open(str(cale)) as pdf:
        npagini = len(pdf.pages)
        for nr_pagina, pagina in enumerate(pdf.pages, 1):
            k = _scara(pagina)
            muchii = [_la_scara(e, k) for e in pagina.edges]
            vert = [e for e in muchii if e["orientation"] == "v"]
            randuri_pagina = randuri_de_cuvinte(pagina, k=k)
            if geometrie_pagini is not None:
                geometrie_pagini[nr_pagina] = (
                    [(e["top"], e["x0"], e["x1"]) for e in muchii
                     if e["orientation"] == "h" and e["x1"] - e["x0"] > 5],
                    [w for r in randuri_pagina for w in r])
            inaltime = pagina.height / k
            for cuvinte in randuri_pagina:
                margini, geometrie = margini_rand(vert, cuvinte)
                texte = celule(cuvinte, margini)
                if not any(texte):
                    continue
                y = min(w["top"] for w in cuvinte)
                in_margine = (y < MARGINE_MOBILIER * inaltime
                              or y > (1 - MARGINE_MOBILIER) * inaltime)
                brute.append((nr_pagina, cuvinte, margini, geometrie, texte,
                              in_margine))
    respinse = _mobilier(brute, npagini)
    return [r[:5] for r in brute if " ".join(r[4]).strip() not in respinse]


# Nivelul subtitlului, mai adanc decat orice index ("A." are 9): un titlu real il
# sterge, iar urmatorul subtitlu il inlocuieste.
ADANCIME_SUBTITLU = 99
# un subtitlu e un nume de grup, nu o fraza; peste atat e o nota. La 80, "Incasare
# sume din contul deschis la alt prestator de servicii - Incasari prin virament"
# (86) nu era subtitlu, si 24 de incasari Nexent ramaneau fara concept.
LUNGIME_MAX_SUBTITLU = 100


# cuvinte care nu numesc un serviciu, la numaratoarea din _e_varianta
CUVINTE_GOALE = {"lei", "leu", "ron", "eur", "euro", "usd", "gbp", "chf", "sau", "pentru",
                 "din", "prin", "catre", "către", "sub", "peste", "inclusiv", "exclusiv"}


def _e_varianta(text):
    """Eticheta numeste doar varianta serviciului de deasupra, nu serviciul?

    "Emis", "Primit", "Cesiune", "(principal)", "- 50.000 LEI, exclusiv", "ATM BRD":
    un subpunct, o banda, o continuare, sau cel mult doua cuvinte cu sens. Un
    subtitlu se aplica doar unor astfel de randuri (vezi _e_subtitlu).
    """
    if _e_subpunct(text) or RE_CONTINUARE.match(text) or _e_doar_banda(text):
        return True
    fara_paranteze = re.sub(r"\([^)]*\)?", " ", text)
    # orice litera, si cu sedila: "iniţială" cu [a-zăâîșț] se rupea in doua, iar
    # "Emitere iniţială" parea un nume de trei cuvinte si inchidea subtitlul
    cuvinte = [c for c in re.findall(r"[^\W\d_]{3,}", fara_paranteze)
               if c.lower() not in CUVINTE_GOALE]
    return len(cuvinte) <= 2


def _e_subtitlu(texte, nevide, margini, latime_tabel, geometrie):
    """Randul e titlul unui grup de servicii, scris cu litere mici?

    Titlurile cu majuscule sau cu index le prinde _e_titlu. Nexent isi scrie toate
    titlurile normal ("Scrisori de garantie", "Tranzactii cu numerar", "Alte
    servicii"), pe un rand cu bordura si o singura celula intinsa peste tabel; fara
    ele documentul nu avea nicio secțiune, iar "Cesiune", "Executare" sau "Emitere
    (trimestrial)" nu spuneau despre ce e vorba. Doar randuri cu bordura: fara
    ea, o linie lunga de nota trece la fel de bine drept titlu.

    Subtitlul se inchide la primul rand care isi numeste singur serviciul. La
    Nexent, "Ordin de plata conditionat" acopera doar "Emis" si "Primit"; dupa ele
    vin "Investigatie ordin de plata", "Scrisoare de bonitate", "Curierat Special".
    Lasat deschis, le dadea tuturor conceptul transfer_credit: verificate de mana
    40 de atribuiri, pe etichetele-varianta 16 din 19 erau corecte, pe numele
    intregi doar 9 din 19.
    """
    if geometrie != "bordura" or len(nevide) != 1:
        return False
    i = nevide[0]
    t = texte[i]
    if (len(t) > LUNGIME_MAX_SUBTITLU or RE_CONTINUARE.match(t)
            or t.rstrip().endswith((".", ",", ";")) or RE_DOAR_MONEDE.match(t)):
        return False
    latime_celula = margini[i + 1] - margini[i]
    return (bool(latime_tabel) and latime_celula >= LATIME_MIN_TITLU * latime_tabel
            and len(re.findall(r"[A-Za-zĂÂÎȘȚăâîșț]", t)) >= LITERE_MIN_TITLU)


def _titlu_din_tabel(texte, nevide):
    """(index, titlu) cand indexul sta in coloana lui, in interiorul tabelului.

    BCR scrie "11." intr-o celula si "Carduri de Debit în Lei" in urmatoarea.
    Nerecunoscut, titlul trecea drept subtitlu si era inlocuit de randul de
    dedesubt ("George Business* Business Gold..."), iar "Emitere iniţială" si
    "Reînnoire" ramaneau fara card: 90 de valori BCR fara concept.
    """
    if len(nevide) != 1:
        return None
    t = texte[nevide[0]]
    index = [j for j, x in enumerate(texte) if x and RE_INDEX_CELULA.match(x)]
    if (len(index) == 1 and index[0] < nevide[0] and len(t) <= 90
            and not RE_CONTINUARE.match(t)):
        return texte[index[0]], t
    return None


# Titlul cu index poate fi lung: "6. Taxe și comisioane aferente cardurilor de debit
# principale/suplimentare în lei și valută" (Raiffeisen) are 13 cuvinte si 91 de
# caractere, deci cadea la filtrul de proza, iar cardurile de debit ramaneau sub
# secțiunea de dinainte ("Comisioane de procesare..."). O nota numerotata se
# termina insa cu punct si e mai lunga.
LUNGIME_MAX_TITLU_INDEX = 120
CUVINTE_MAX_TITLU_INDEX = 16


def _e_titlu_cu_index(t):
    return bool(RE_INDEX_SECTIUNE.match(t) and len(t) <= LUNGIME_MAX_TITLU_INDEX
                and len(t.split()) <= CUVINTE_MAX_TITLU_INDEX
                and not t.rstrip().endswith((".", ",", ";", ":")))


def _e_titlu(texte, nevide, margini, latime_tabel):
    """(index, titlu) daca randul e un titlu de sectiune, altfel None."""
    # Titlul pe acelasi rand cu antetul de moneda: Libra scrie "ACREDITIVE DE
    # IMPORT", "GARANTII", "DIRECT DEBIT INTERBANCAR" in coloana numelui si "EUR"
    # sau "LEI" deasupra preturilor. Cu doua celule nu era titlu, iar celula ocupa
    # 45% din tabel, sub pragul de latime; asa ca "Amendamente" sau "Negociere/
    # plata" nu spuneau ale carui instrument sunt.
    monede = [i for i in nevide if RE_DOAR_MONEDE.match(texte[i])]
    rest = [i for i in nevide if i not in monede]
    if monede and len(rest) == 1:
        t = texte[rest[0]]
        if (len(t) <= 90 and t == t.upper()
                and len(re.findall(r"[A-ZĂÂÎȘȚ]", t)) >= LITERE_MIN_TITLU):
            m = RE_INDEX_SECTIUNE.match(t)
            return (m.group(1), m.group(2)) if m else (None, t)
    if len(nevide) != 1:
        return None
    i = nevide[0]
    t = texte[i]
    if _e_titlu_cu_index(t):
        m = RE_INDEX_SECTIUNE.match(t)
        return m.group(1), m.group(2)
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
    destul = (len(re.findall(r"[A-Za-zĂÂÎȘȚ]", t)) >= LITERE_MIN_TITLU
              or RE_TITLU_SCURT.match(t))
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


# --- valori pe care o celula singura nu le arata: depind de coloana sau de randul vecin

# "0" fara moneda e felul in care Nexent, TBI, Vista, Techventures si ProCredit scriu
# "gratuit": masurat pe cele 50 de liste, 360 de valori recuperate (Nexent 101, Vista
# 98, BCR 77, TBI 44). Necitit, serviciul se pierdea, iar randul "Nume || RON/FX || 0"
# devenea antet de matrice si coloana "0 0 0" se lipea de randurile de sub el.
RE_ZERO_CELULA = re.compile(r"^0\s*\**$")
# ...dar numai langa preturi: in "0 || 5 || 59 LEI" (BCR, pachetul dupa numarul de
# tranzactii, "Minim | Maxim") zeroul e un numar de tranzactii, nu un pret
RE_NUMAR_SINGUR = re.compile(r"^\d+(?:[.,]\d+)?\s*\**$")
# Intervalul de pret: "550 – 3.300 lei" (BRD, evaluarea imobilului), "2,5 - 12,5 lei"
# (Eximbank), "5 – 100 lei" (Libra). RE_PRAG il ia drept banda de suma si valoarea se
# pierdea (48 de capete, pastrate ca min/max). Banda sta insa in coloana numelui, cu
# pretul in dreapta ei pe acelasi rand.
RE_INTERVAL = re.compile(rf"^\W*({BANI})\s*(?:{VAL})?\s*[–—-]\s*({BANI})\s*({VAL})"
                         r"(?![^\W\d_])(?!.*\b(?:in|ex)clusiv)", re.I)
# Celula de pret rupta pe doua randuri, cu minimul sau maximul pe al doilea: "1,75%,
# min." / "5 EUR/USD" (BCR), "0,5%/ trimestru (min" / "75 lei)" si "(min 26 euro,
# max" / "650 euro)" (Libra), "0,20% min. 25 EUR max. 800" / "EUR". Masurat: 24 de
# sume isi primesc rolul, iar 20 de plafoane se nasc din cifra ramasa pe prima linie.
RE_ROL_DESCHIS = re.compile(
    r"\b(?:min|max|minim|maxim|minimum|maximum)\b\.?\s*(?:\d[\d.,]*\s*)?$", re.I)


def _semn(margini):
    return tuple(round(m) for m in margini)


def _alta_celula(orizontale, cx, sus, jos):
    """O bordura orizontala trece prin coloana intre cele doua linii de text?"""
    return any(sus - 1 <= t <= jos + 1 and x0 - 1 <= cx <= x1 + 1
               for t, x0, x1 in orizontale)


def _valori_din_context(randuri, analize, col_nume, geometrie_pagini):
    """Completeaza `analize` pe loc cu valorile care depind de coloana sau de vecin.

    Coloana de pret e cea in care tabelul (aceeasi semnatura de borduri) are macar o
    valoare citita de analizeaza_linie; coloana numelui nu e niciodata una.
    """
    cu_pret = defaultdict(set)
    # Pe fiecare coloana a paginii, felul celulelor nevide care nu sunt zero: "pret"
    # sau "numar" (cifra fara moneda: "3", "25 trz/lună"). Zeroul dintre numere e si
    # el un numar: la BCR, "Tranzacții incluse în pachet" are 0, 25 si 200 de
    # tranzactii in coloanele cu pretul pachetelor George Business.
    vecini = defaultdict(list)
    for k, ((nr, _c, margini, _g, texte), analiza) in enumerate(zip(randuri, analize)):
        cu_pret[_semn(margini)].update(i for i, a in enumerate(analiza) if a[0])
        for i, t in enumerate(texte):
            if t and not RE_ZERO_CELULA.match(t):
                vecini[(nr, _semn(margini), i)].append(
                    (k, "pret" if analiza[i][0] else "numar" if t[0].isdigit() else "text"))
    for semn, i in col_nume.items():
        cu_pret[semn].discard(i)

    def langa_numere(k, nr, semn, i):
        coloana = vecini[(nr, semn, i)]
        sus = [f for k2, f in coloana if k2 < k and f != "text"][-1:]
        jos = [f for k2, f in coloana if k2 > k and f != "text"][:1]
        return "numar" in sus + jos

    for k, ((nr, cuvinte, margini, geometrie, texte), analiza) in enumerate(
            zip(randuri, analize)):
        if geometrie == "unic":
            continue        # o celula singura n-are coloana care sa spuna ce e
        semn = _semn(margini)
        pret = cu_pret[semn]

        # Numele cu o cifra in el ("Dobanda cont curent de card (se aplica la sold mai
        # mare de 500 RON) || 0", Libra) nu mai e eticheta, iar zeroul ar fi luat
        # numele randului de deasupra ("Taxa recuperare card"). Fara nume, nu se citeste
        # (vezi si _zero_fara_nume, la emitere).
        zerouri = [i for i in pret if RE_ZERO_CELULA.match(texte[i])
                   and not langa_numere(k, nr, semn, i)]
        if (zerouri and not any(analiza[j][0] for j in range(len(texte)) if j not in pret)
                and not any(RE_NUMAR_SINGUR.match(t) and not RE_ZERO_CELULA.match(t)
                            for t in texte)):
            for i in zerouri:
                analiza[i] = ([("gratuit", 0.0, None, None)], None, analiza[i][2], None)

        # intervalul: pe un rand fara alt pret, cu numele serviciului in stanga lui
        are_valori = any(a[0] for a in analiza)
        for i in pret:
            m = RE_INTERVAL.match(texte[i])
            if not m or are_valori:
                continue
            if not any(t and not analiza[j][0] and not _e_doar_banda(t)
                       and not RE_DOAR_ORNAMENT.match(t) for j, t in enumerate(texte[:i])):
                continue
            moneda = MONEDE[m.group(3).lower()]
            analiza[i] = ([("comision_suma", suma_bani(m.group(1)), moneda, "min"),
                           ("comision_suma", suma_bani(m.group(2)), moneda, "max")],
                          None, analiza[i][2], None)

        if geometrie != "bordura":
            continue
        for i, t in enumerate(texte):
            if not analiza[i][0] or not RE_ROL_DESCHIS.search(t):
                continue
            # A doua linie a celulei: pe randurile urmatoare, aceeasi coloana, fara
            # bordura intre ele. Doar cand prima linie are deja pretul (procentul sau
            # minimul): "Conditie pachet ... de minim" / "40.000 EUR" (BRD) e o cerinta.
            a, b = margini[i], margini[i + 1]
            sus, jos = min(w["top"] for w in cuvinte), max(w["bottom"] for w in cuvinte)
            for k2 in range(k + 1, min(k + 6, len(randuri))):
                nr2, cuv2, m2, g2, texte2 = randuri[k2]
                sus2 = min(w["top"] for w in cuv2)
                if (nr2 != nr or g2 != "bordura" or sus2 - jos > jos - sus
                        or _alta_celula(geometrie_pagini[nr][0], (a + b) / 2, jos, sus2)):
                    break
                j = next((j for j, t2 in enumerate(texte2) if t2 and min(b, m2[j + 1])
                          - max(a, m2[j]) > 0.5 * min(b - a, m2[j + 1] - m2[j])), None)
                if j is None:
                    continue
                _lipeste_rol(analiza, i, t, analize[k2], j, texte2[j])
                break


def _zero_fara_nume(tip, text, serviciu):
    """Zeroul din coloana a ramas, dupa reconstruirea etichetei, fara un nume intreg.

    "Activare", "Transfer" sub "Direct Debit intrabancar" (BCR): cand subtitlul nu se
    vede, serviciul se ia doar din secțiunea de deasupra, si 12 zerouri ieseau file_cec.
    Cu parintele lipit ("Retrageri de numerar FX", "... prin: SMS") zeroul ramane.
    """
    return (tip == "gratuit" and bool(RE_ZERO_CELULA.match(text))
            and len(re.findall(r"[^\W\d_]{2,}", serviciu or "")) < 2)


def _lipeste_rol(analiza, i, t, analiza2, j, t2):
    """Rolul deschis pe prima linie trece la suma de pe a doua.

    Suma ramane pe randul ei, cu eticheta ei: celula de pret poate fi unita peste
    mai multe randuri (BCR, "1,75%, min. 5 EUR/USD" peste patru variante de
    retragere), iar geometria nu spune al cui e pretul. Doar o suma noua, nascuta
    din cifra de pe prima linie si moneda de pe a doua ("max. 800" / "EUR"), sta cu
    prima linie.
    """
    v1, v2 = analiza[i][0], list(analiza2[j][0])
    toate = analizeaza_linie(f"{t} {t2}")[0]
    if toate[:len(v1)] != v1 or len(toate) <= len(v1):
        return
    noi = []
    for tip, val, moneda, rol in toate[len(v1):]:
        p = next((p for p, x in enumerate(v2) if x[:3] == (tip, val, moneda)), None)
        if p is not None:
            v2[p] = (tip, val, moneda, v2[p][3] or rol)
        else:
            noi.append((tip, val, moneda, rol))
    analiza[i] = (v1 + noi,) + tuple(analiza[i][1:])
    analiza2[j] = (v2,) + tuple(analiza2[j][1:])


def extrage_tarife(cale, banca, radacina=None):
    """Inregistrarile de comision dintr-o lista de tarife nestandardizata."""
    cale = Path(cale)
    sursa = str(cale.relative_to(radacina)) if radacina else cale.name
    geometrie_pagini = {}
    randuri = randuri_document(cale, geometrie_pagini)
    analize = [[analizeaza_linie(t) for t in texte] for _n, _c, _m, _g, texte in randuri]
    col_nume = coloana_numelui(randuri, analize)
    _valori_din_context(randuri, analize, col_nume, geometrie_pagini)
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
    # coloanele in care tabelul a avut deja valori; vezi _celula_eticheta. Pe tot
    # tabelul, nu doar pe randul de deasupra: la BRD textul unei celule de pret se
    # intinde pe patru randuri ("lunar: prima tranzactie" / "gratuita, de la a
    # doua:" / "1% + 10 lei (echiv. in" / "valuta contului)"), iar "valuta
    # contului)" ajungea lipit de numele serviciului de pe randul urmator.
    pret = defaultdict(set)
    rand_titlu_caps = None    # randul ultimului titlu cu majuscule, pentru alipire
    pagina_anterioara = None
    for k, ((nr_pagina, cuvinte, margini, geometrie, texte), analiza) in enumerate(
            zip(randuri, analize)):
        # un rand fara nicio coloana si cu multe cuvinte e proza, nu tarif
        if (geometrie == "unic" and len(cuvinte) > CUVINTE_MAX_RAND_UNIC
                and not _e_titlu_cu_index(" ".join(texte).strip())):
            continue
        if RE_CUPRINS.search(" ".join(texte)):
            continue          # rand din cuprins, nu din tabel

        sus = min(w["top"] for w in cuvinte)
        jos = max(w["bottom"] for w in cuvinte)
        if pagina_anterioara != nr_pagina:
            blocuri_et = []          # pagina noua, alte poziții verticale
        pagina_anterioara = nr_pagina

        are_valori = any(v for v, _p, _f, _d in analiza)
        nevide = [i for i, t in enumerate(texte)
                  if t and not RE_DOAR_INDEX.match(t)]
        semn = tuple(round(m) for m in margini)
        coloane_pret = pret[semn]
        coloane_pret = coloane_pret - {col_nume.get(semn)}

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
            # Titlul cu index in coloana lui si subtitlul intra in secțiune, dar raman
            # si parinti pentru subpunctele de sub ei, deci nu golesc etichetele si
            # trec mai departe. Stau in acelasi tabel: golite, etichetele pierdeau
            # prefixul ("Incasso de import/incasso primit" + "La efectuarea
            # modificarii" ajungea modificare_anulare, nu documentar).
            din_tabel = _titlu_din_tabel(texte, nevide)
            subtitlu = bool(din_tabel) or _e_subtitlu(texte, nevide, margini,
                                                      latime_tabel, geometrie)
            if din_tabel:
                sectiuni.pune(*din_tabel)
            elif subtitlu:
                sectiuni.subtitlu(texte[nevide[0]])
            # antet de matrice: mai multe nume de coloana, niciunul cu valoare
            if _e_rand_antet(texte, nevide, semn in semn_cu_valori):
                vechi = antete.get(semn) or [""] * len(texte)
                if len(vechi) != len(texte):
                    vechi = [""] * len(texte)
                antete[semn] = [_aduna_antet(a, b) for a, b in zip(vechi, texte)]
                continue
            i_eticheta = _celula_eticheta(texte, analiza, coloane_pret)
            if i_eticheta is not None:
                _adauga_eticheta(blocuri_et, sus, jos, texte[i_eticheta], False,
                                 x=margini[i_eticheta])
                if not subtitlu and not _e_varianta(texte[i_eticheta]):
                    sectiuni.inchide_subtitlu()
            continue

        # rand cu valori: eticheta lui poate continua si pe randurile urmatoare
        i_eticheta = _celula_eticheta(texte, analiza, coloane_pret)
        if i_eticheta is not None:
            _adauga_eticheta(blocuri_et, sus, jos, texte[i_eticheta], True,
                             x=margini[i_eticheta])
            if not _e_varianta(texte[i_eticheta]):
                sectiuni.inchide_subtitlu()
        semn_cu_valori.add(semn)
        pret[semn].update(i for i, a in enumerate(analiza) if a[0])
        de_emis.append((nr_pagina, sus, jos, texte, analiza, geometrie,
                        blocuri_et, sectiuni.cale() or None,
                        antete.get(semn, []), margini[0]))

    # A doua trecere: acum fiecare bloc de eticheta e intreg
    inregistrari = []
    serviciu = sectiune_anterioara = None
    conditie = frecventa = None
    for (nr_pagina, sus, jos, texte, analiza, geometrie, etichete_active,
         sectiune, antet, stanga) in de_emis:
        gasita = _eticheta_pentru(
            sus, jos, etichete_active,
            lambda xv, g=geometrie_pagini[nr_pagina], st=stanga, a=sus, b=jos:
                _celula_din_stanga(g, st, xv, a, b) if xv - st > DX_VARIANTA else None)
        # Fara eticheta, randul mosteneste serviciul de deasupra: corect peste o
        # pagina rupta, greșit peste un titlu. La Vista, pretul pachetului ("5
        # LEI/Luna", "500 LEI/AN") mostenea "Taxa SWIFT" din tabelul de plati de
        # deasupra titlului "PACHETE DE PRODUSE SI SERVICII".
        if not gasita and sectiune != sectiune_anterioara:
            serviciu = None
        sectiune_anterioara = sectiune
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
                if _zero_fara_nume(tip, texte[i], serviciu):
                    continue
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
                                           f"{texte[i]} {antet[i] if i < len(antet) else ''}",
                                           texte[i]),
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
