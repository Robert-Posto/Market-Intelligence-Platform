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
# ...sau cu punct in interior, fara cel final: Raiffeisen scrie "5.3 Multicash",
# "5.5 MT 101", "7.4 Incasso" (212 valori isi schimba secțiunea). Fara el, "5.5
# MT 101" nu era nici subtitlu (doua litere), iar abonamentul MT101 ramanea sub
# "5.4 Free-Way" (vama), iar 8 plati de sub "4.1" ieseau incasari. Punctul din
# interior tine afara nota "2 intrări", cifrele scurte suma "2.500 lei", iar
# majuscula randul de tarif "15.3 comision zero" (BCR, pretul in aceeasi celula).
RE_INDEX_SECTIUNE = re.compile(
    r"^(\d+(?:\.\d+)*\.|\d{1,2}(?:\.\d{1,2})+(?=\s+[A-ZĂÂÎȘȚŞŢ])|[A-Z]\.|[IVX]+\.)"
    r"\s+(.+)$")
# acelasi index, dar singur in celula lui; fara litere ("a." e semn de lista)
RE_INDEX_CELULA = re.compile(r"^(?:\d+(?:\.\d+)*\.|[IVX]+\.)$")
# Cu paranteze: "(USD) (EUR)" ajunsese titlu la BCR si inlocuia "14. Carduri de
# Debit în Valută" (13 valori). "EUR*" nu intra: titlul Libra "ORDINE DE PLATA
# CONDITIONATE || EUR*" recunoscut dadea transfer_credit si notificarii OPC-ului
# primit, care e documentar (6 greșite fata de 7 corecte).
# "FX" e valuta, la Nexent ("RON/FX"): altfel coloana monedei ajungea eticheta
RE_DOAR_MONEDE = re.compile(
    r"^[\s()/,;]*(?:(?:lei|leu|ron|eur|euro|usd|gbp|chf|fx)[\s()/,;]*)+$", re.I)
# Componente de cel mult doua cifre: o data are anul de patru ("Cu token cumpărat
# începând cu 05.04.2019" ramanea "...începând cu", casetele "după 21.07.2014" la
# fel; 6 etichete BCR si BRD), iar suma are grupe de trei ("Plăți instant ≤ LEI
# 5.000" ramanea "≤ LEI"; 8 etichete ProCredit, BRCI, Garanti)
RE_INDEX_LA_SFARSIT = re.compile(r"\s+\d{1,2}(?:\.\d{1,2})+\.?$")
# o paranteza, si una neinchisa pana la capatul celulei
RE_PARANTEZA = re.compile(r"\([^)]*\)?")
# Doar liniuta: nota cu bulina "• nu se aplica conturilor in valuta..." (Vista)
# ramane subtitlu, altfel pragul de 100.000 lei din ea lua administrare_cont.
RE_LINIUTA = re.compile(r"^\s*[-–—]\s*\S")
RE_LITERA_SAU_ROMAN = re.compile(r"^[A-Z]\.$|^[IVX]+\.$")
RE_ROMAN = re.compile(r"^[IVX]+\.$")
# Randurile din cuprins ("CONTURI CURENTE ... PAG. 3") arata ca titluri de
# sectiune si deveneau sectiuni: BCR PDAI avea "PACHET DE SERVICII PAG. 7".
RE_CUPRINS = re.compile(r"\bpag\.?\s*\d+\b", re.I)
# o celula care e doar semn de lista nu e eticheta ("•" ajunsese numele a 15
# servicii la BRCI); nici "N/A" (serviciul nu exista pentru cardul din coloana):
# la Raiffeisen, "N/A" ajunsese numele pachetului de protectie a cardului
RE_DOAR_ORNAMENT = re.compile(
    r"^[\s•·○▪√\-–—~*+.,:;()\[\]/]*$"
    r"|^\s*(?:n/a|nu\s+(?:e|este)\s+(?:cazul|posibil))\W*$", re.I)
# dobanda in puncte procentuale sau pe un indice de referinta: celula tabelului de
# dobanzi, nu numele unui comision (vezi _celula_eticheta)
RE_VALOARE_DOBANDA = re.compile(r"\d\s*pp\b|\b(?:IRCC|EURIBOR|ROBOR)\b", re.I)
# un numar fara moneda nu e un nume: capetele de banda din matricea BCR de
# transferuri ("1.200,01 | 1.500 | 25 | 1500,01 | 1%") ajungeau eticheta
RE_DOAR_NUMAR = re.compile(r"^[\d.,\s]+$")
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
    """Indicii celulelor care poarta numele serviciului, in ordine; [] daca nu e.

    Nu e coloana 0: multe liste au o coloana de numerotare ("Nr. crt.") sau un
    semn de lista inaintea numelui, iar unele pun preturile in STANGA si
    descrierea in dreapta (tariful de evaluari al BCR).

    Pe un rand cu valori, numele e celula de text cea mai apropiata la STANGA
    primei valori. "Cel mai lung text de pe rand" lua altceva de fiecare data cand
    pe rand mai era o fraza: la BRD (ghidul de credite) doua tabele stau alaturate,
    DOBANZI | COMISIOANE, iar comisioanele primeau descrierea creditului din
    stanga; la BCR PJ, coloana Comentarii din dreapta pretului ("Se percepe o
    singura data la inrolare") batea numele ("Taxa de inrolare"); la Raiffeisen,
    "invitat; pentru invitati" din coloana Infinite batea "Loungekey". O celula cu
    dobanda (RE_VALOARE_DOBANDA) opreste cautarea: e tabelul vecin, nu numele.
    Cand valoarea sta in prima coloana, numele sunt celulele din dreapta ei, unite
    ("Raport evaluare" + "Casă/vilă cu terenul aferent", BCR).

    Pe un rand fara valori ramane celula cu cel mai mult text. Textul din
    `coloane_pret` (vezi coloane_de_pret) e coada celulei de preț, nu un nume. BCR
    scrie "min. 1 LEI/" pe un rand si "tranzacție" pe urmatorul, iar "tranzacție",
    "operațiune" si "nepermisă" ajunsesera nume de serviciu.
    """
    candidate = [i for i, t in enumerate(texte)
                 if t and i not in coloane_pret and not RE_DOAR_INDEX.match(t)
                 and not RE_DOAR_ORNAMENT.match(t) and not analiza[i][0]]
    valori = [i for i, a in enumerate(analiza) if a[0]]
    if not valori:
        return [max(candidate, key=lambda i: len(texte[i]))] if candidate else []
    candidate = [i for i in candidate if not RE_DOAR_NUMAR.match(texte[i])]
    stanga = []
    for i in range(valori[0] - 1, -1, -1):
        if RE_VALOARE_DOBANDA.search(texte[i]):
            break
        if i in candidate:
            stanga.insert(0, i)
    # Moneda dintre nume si pret nu e numele (Nexent: "Cesiune | RON/FX | 0,20%"),
    # dar singura pe rand e banda de sub nume (BRCI: "Lei", "USD", "CHF" sub
    # "Administrare lunara Cont Curent")
    nume = [i for i in stanga if not RE_DOAR_MONEDE.match(texte[i])] or stanga
    if not nume:
        return [i for i in candidate if i > valori[0]]
    # Varianta scurta din coloana vecina se compune cu numele din stanga ei, de pe
    # acelasi rand: "Incidente de plata - Consultare baza de date | centrala | 6
    # lei" (BRD), "Administrare | Principal | 2 lei" (Eximbank). Singura, varianta
    # nu spune serviciul, iar _celula_din_stanga o completeaza doar unde exista
    # borduri. Litera mica nu ajunge: "clădire viitoare – evaluare intermediară"
    # e un nume intreg, iar in stanga ei sta tabelul de dobanzi (BRD).
    return nume if _cuvinte_cu_sens(texte[nume[-1]]) <= 2 else nume[-1:]


# suma urmata de "sau" la capat: conditia continua pe randul urmator (Vista,
# "Retragere numerar pentru sume care depasesc 10.000 EUR sau" / "echivalent
# executate fara anunt prealabil", 5 valori). Fara ";" intre ele: in lista Libra
# "Api.Investigator – 40 lei; RECOM - 33 lei; CIP (format FNIP sau", 40 si 33 sunt
# preturi.
RE_CONDITIE_DESCHISA = re.compile(
    r"\d\s*(?:lei|leu|ron|eur|euro|usd|gbp|chf)\b[\w/().\s]*\bsau\s*$", re.I)


def _conditii_in_nume(texte, analiza, i_nume):
    """{i_nume} cand celula din coloana numelui e o fraza cu o suma, altfel set().

    Suma din nume e conditia serviciului, nu pretul lui: "Dobanda cont curent de
    card (se aplica la sold mai mare de 500 RON)" (Libra), "Retragere numerar
    pentru sume care depasesc 10.000 EUR sau" (Vista). Citita ca valoare, celula nu
    mai era eticheta: randul lua numele de deasupra, iar dobanda de 1% a Libra
    iesea "Taxa recuperare card" (6 valori).

    Doar o fraza (cel putin 3 cuvinte cu sens), doar sume si doar cand fraza
    spune ca e o conditie: pretul sta pe acelasi rand in alta coloana, suma e un
    prag (rol_de_conditie) sau fraza continua cu "sau". Cu regula larga ("pretul
    sta in alta coloana a tabelului") treceau si preturile scrise in celula
    numelui: lista Libra "MF - 2 lei; Buletinul Insolventei - 4,50 lei",
    "Interogare sold gratuit** de la orice ATM" (ProCredit), nota BCR "Taxa de
    urgenta ... este de 35 EUR" — 18 concepte pierdute in setul fix.
    """
    if (i_nume is None or i_nume >= len(texte) or not analiza[i_nume][0]
            or any(tip != "comision_suma" for tip, *_r in analiza[i_nume][0])):
        return set()
    t = texte[i_nume]
    # Nici continuarea scurta cu litera mica ("minime3 de 5.000.000 EUR/an(sau
    # echiv.) sau", BRD CARD NOIR): lipita, lanțul urca pana la "Schimbare cod PIN"
    # de deasupra tabelului, iar pachetul NOIR iesea schimbare_pin sau incasare (6
    # valori)
    if _cuvinte_cu_sens(t) < 3:
        return set()
    if (any(a[0] for j, a in enumerate(analiza) if j != i_nume)
            or any(rol_de_conditie(t, None, v) for _t, v, *_r in analiza[i_nume][0])
            or RE_CONDITIE_DESCHISA.search(t)):
        return {i_nume}
    return set()


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


def _adauga_eticheta(blocuri, sus, jos, text, are_valori, gol_maxim=6, x=None,
                     x_text=None, bordura=False):
    """Adauga un rand de eticheta la blocul curent, sau deschide unul nou.

    Blocurile sunt (sus, jos, text, e_parinte, x, x_text, bordura); x e marginea
    stanga a celulei, x_text inceputul textului, bordura spune daca randul are
    borduri (ultimele doua pentru _parinte_indentat); x e None cand nu se stie
    (vezi _celula_din_stanga). Un rand cu valoare deschide bloc
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
        blocuri[-1] = (a, jos, f"{t} {text}", parinte and not are_valori, _x(ultim),
                       _x_text(ultim), _bordura(ultim))
    else:
        blocuri.append((sus, jos, text, not are_valori, x, x_text, bordura))


def _x(bloc):
    return bloc[4] if len(bloc) > 4 else None


def _x_text(bloc):
    return bloc[5] if len(bloc) > 5 else None


def _bordura(bloc):
    return len(bloc) > 6 and bloc[6]


def _x_celula(cuvinte, margini, i):
    """Unde incepe textul celulei i (in tabelele cu borduri, marginea celulei nu
    arata indentarea)."""
    xs = [w["x0"] for w in cuvinte
          if margini[i] <= (w["x0"] + w["x1"]) / 2 <= margini[i + 1]]
    return min(xs) if xs else None


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


def _deja_continut(parinte, nume):
    """Cel putin jumatate din cuvintele parintelui sunt deja in eticheta?

    Celula din stanga scrisa pe verticala ajunge si in eticheta, rand cu rand. La
    Nexent eticheta era deja "Taxa plati ... de Plati interbancare valuta ...
    (catre alte banci)", iar prefixul o mai scria o data (6 valori).
    """
    cuv = lambda t: set(re.findall(r"[^\W\d_]{3,}", t.lower()))
    din_parinte = cuv(parinte)
    return len(din_parinte & cuv(nume)) * 2 >= len(din_parinte)


# marcajele de lista, pe familii: "–" si "-" sunt acelasi nivel, "•" altul
RE_MARCAJ = re.compile(r"^\s*(?:([-–—~])|([•·▪○]))")


def _sub_parinte(blocuri, i, cu_pret=frozenset()):
    """Indicele subpunctului-parinte cu alt marcaj decat eticheta, sau None.

    BCR (credite PF, p5) scrie "Comision (flat) pentru creditele în sold", sub el
    "– Comision pentru graţie de până la 6 luni:", iar sub acesta doua randuri
    "• în cazul în care creditul (nu) înregistrează restanţe", cu pret. Parintele
    cautat doar printre numele intregi sarea peste "–", iar cele trei perechi de
    "•" ieseau la fel. Fratii cu acelasi marcaj se sar; primul bloc cu alt marcaj
    decide, si numai daca e un rand fara pret propriu.
    """
    m = RE_MARCAJ.match(blocuri[i][2])
    if not m:
        return None
    x = _x(blocuri[i])
    for k in range(i - 1, -1, -1):
        b = blocuri[k]
        if x is not None and _x(b) is not None and abs(_x(b) - x) > DX_VARIANTA:
            continue       # alta coloana
        mk = RE_MARCAJ.match(b[2])
        if mk and (mk.group(1) is None) == (m.group(1) is None):
            continue       # frate, acelasi marcaj
        if mk and b[3] and k not in cu_pret and not _e_doar_banda(b[2]):
            return k
        return None
    return None


def _bloc_pentru(sus, jos, blocuri):
    """Indicele blocului de eticheta al valorii dintre sus si jos.

    Suprapunerea decide cand exista, altfel cel mai apropiat centru. Ordinea de
    citire NU decide: coloana de preț e centrata vertical, coloana de nume e
    aliniata sus, deci valoarea se tiparește uneori deasupra numelui sau.
    """
    lungime, minus_i = max((min(jos, b[1]) - max(sus, b[0]), -i)
                           for i, b in enumerate(blocuri))
    if lungime > 0:
        return -minus_i
    centru = (sus + jos) / 2
    return min(range(len(blocuri)),
               key=lambda k: abs((blocuri[k][0] + blocuri[k][1]) / 2 - centru))


def _eticheta_pentru(sus, jos, blocuri, parinte_stanga=None, cu_pret=frozenset()):
    """Eticheta careia aparține o valoare, dupa poziția verticala (_bloc_pentru).

    `cu_pret`: indicii blocurilor care primesc direct o valoare (vezi
    _parinte_indentat).
    """
    if not blocuri:
        return None
    i = _bloc_pentru(sus, jos, blocuri)
    nume = blocuri[i][2]
    banda, subpunct = _e_doar_banda(nume), _e_subpunct(nume)
    # Varianta dintr-o coloana din dreapta isi ia intai numele din celula cu
    # bordura din stanga. "Ultimul parinte de deasupra" greseste acolo unde celula
    # din stanga e centrata: la Nexent, randul "FX 0,5%" al retragerilor lua
    # "Depuneri de numerar", fiindca "Retrageri de numerar" e scris sub el.
    #
    # Si numele intreg dintr-o sub-coloana: la BCR "Cu token cumpărat începând cu"
    # sta sub "Folosirea/Administrare Internet Banking, Mobile Banking", dar are
    # trei cuvinte cu sens, deci nu era "varianta" si ramanea fara serviciu.
    parinte = None
    if parinte_stanga and _x(blocuri[i]) is not None:
        if banda or subpunct or _e_varianta(nume):
            parinte = parinte_stanga(_x(blocuri[i]))
        else:
            parinte = parinte_stanga(_x(blocuri[i]), o_celula=True)
        if parinte and (RE_DOAR_INDEX.match(parinte) or _deja_continut(parinte, nume)):
            parinte = None
    anterior = blocuri[i - 1] if i > 0 else None
    if parinte:
        nume = f"{parinte} {nume}"
    elif (subpunct and RE_CONTINUARE.match(nume) and anterior
          and anterior[1] >= blocuri[i][0] - LIPIRE_CONTINUARE
          and RE_TERMINA_DESCHIS.search(anterior[2])
          and (_x(anterior) is None or _x(blocuri[i]) is None
               or abs(_x(anterior) - _x(blocuri[i])) <= TOL_BORDURA)):
        # Subpunctul lipit de randul deschis de deasupra, in aceeasi celula, ii
        # continua numele: BCR "Furnizare (Refacere) Card furat /pierdut
        # /schimbare nume /deteriorat /" + "la cerere" (100 Lei). Ca subpunct lua
        # ultimul parinte, "Comision pentru tranzacţii ... jocuri de noroc".
        nume = f"{anterior[2]} {nume}"
    elif banda or subpunct:
        # ierarhia de marcaje: "•" sub "–" ia si subpunctul "–" (vezi _sub_parinte)
        k = _sub_parinte(blocuri, i, cu_pret)
        if k is not None:
            nume = f"{blocuri[k][2]} {nume}"
        parinti = [b[2] for b in blocuri[:i if k is None else k]
                   if b[3] and not _e_doar_banda(b[2]) and not _e_subpunct(b[2])]
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
    else:
        parinte = _parinte_indentat(blocuri, i, cu_pret)
        if parinte:
            nume = f"{parinte} {nume}"
    return nume


# Indentarea unui subpunct fata de parintele lui: la BRD "Descoperitul autorizat de
# cont Individual" incepe la 484,5, parintele "Reînnoire/ Majorare linie de credit"
# la 473,7. Peste DX_VARIANTA e alta coloana, nu indentare.
INDENTARE_MIN = 5
# Textul aliniat la stanga sta la atat de bordura celulei (BRD: 5,6 si 16,4). Mai
# departe e centrat, iar x-ul lui arata latimea textului, nu indentarea: la BCR
# "Retrageri de numerar" (centrat, la 371) ajungea sub "Furnizare (emitere)/
# Administrare" (centrat, la 342).
PADDING_MAX = 20
# Subpunctele urmeaza parintele rand dupa rand (BRD 3,7 puncte intre ele, BCR 7,8).
# La Libra, prima linie a fiecarui paragraf e retrasa cu 9 puncte, deci arata ca un
# subpunct; dar intre "Accesare produs “Acces Investigator”: Pachet" si
# "Consultari Baze Date CIP, CRC" sunt 71 de puncte din restul paragrafului.
GOL_MAX_GRUP = 10


def _parinte_indentat(blocuri, i, cu_pret=frozenset()):
    """Numele fara pret sub care e indentata eticheta, sau None.

    Decide primul bloc de deasupra care incepe mai la stanga, in aceeasi coloana.
    Daca e un nume intreg fara pret, eticheta e subpunctul lui; daca are pret
    propriu, e alt serviciu si nu se ghiceste nimic. Blocurile mai la dreapta sunt
    frati sau subpuncte ale fratilor; cele mult mai la stanga, alt tabel (BRD pune
    DOBANZI si COMISIOANE alaturi).

    Pretul propriu se vede si cand sta pe un rand fara nume (`cu_pret`): la Libra,
    "Comision incasare OUR solicitat bancii ordonatorului transferului" are 25 euro
    centrat intre cele doua randuri ale lui, deci blocul e "fara valori", dar nu e
    parintele investigatiilor de dedesubt.

    Indentarea singura nu ajunge: randul de deasupra tabelului incepe si el mai la
    stanga, iar la Libra "www.librabank.ro" si "...achite Bancii sunt urmatoarele:"
    ajunsesera parintii a 236 de valori. Intr-un tabel cu borduri decid bordurile:
    aceeasi celula de coloana. Fara borduri se cere un semn tare: parintele se
    termina in ":" (Garanti, "Închiriere casete de siguranță (...):" peste "Tip 1:
    48,5 x 265 x 413 mm"), sau printre fratii de dedesubt e o banda de suma
    (Garanti, "Tranzacții urgente, orice sumă" dupa "> 5.000,01 LEI").
    """
    xt = _x_text(blocuri[i])
    if xt is None:
        return None
    for k in range(i - 1, -1, -1):
        b = blocuri[k]
        xb = _x_text(b)
        if xb is None or not xt - DX_VARIANTA <= xb <= xt - INDENTARE_MIN:
            continue
        nume = b[2].rstrip()
        # un nume intreg, nu coada unei fraze ("ReCom)" inchide paranteza de pe
        # randul de deasupra si ajunsese parintele taxei ANCPI)
        if (not b[3] or k in cu_pret or RE_CONTINUARE.match(nume) or nume.endswith(".")
                or nume.count(")") > nume.count("(")
                or _e_doar_banda(nume) or _e_subpunct(nume)):
            return None
        grup = [f for f in blocuri[k + 1:i]
                if _x_text(f) is not None and xt - 2 <= _x_text(f) <= xb + DX_VARIANTA]
        if _bordura(blocuri[i]):
            lant = [b] + grup + [blocuri[i]]
            ok = (_bordura(b) and abs(_x(b) - _x(blocuri[i])) <= TOL_BORDURA
                  and xb - _x(b) <= PADDING_MAX and xt - _x(blocuri[i]) <= PADDING_MAX
                  and all(d[0] - s[1] <= GOL_MAX_GRUP for s, d in zip(lant, lant[1:])))
        else:
            frati = [f[2] for f in grup if abs(_x_text(f) - xt) <= 2]
            ok = not _bordura(b) and (nume.endswith(":") or any(map(_e_doar_banda, frati)))
        return b[2] if ok else None
    return None


# Cat de mult in dreapta trebuie sa stea varianta fata de marginea tabelului.
# Coloanele de nume si de varianta sunt la zeci de puncte (BCR: 36 si 239).
DX_VARIANTA = 40
# blocul de deasupra atinge continuarea: randurile aceleiasi celule se ating sau se
# suprapun, cele din celule diferite au intre ele padding-ul celulei
LIPIRE_CONTINUARE = 3
# peste atat, "celula" dintre doua borduri e de fapt o pagina fara borduri
INALTIME_MAX_CELULA = 150
CUVINTE_MAX_PARINTE = 15


def _celula_din_stanga(geometrie_pagina, stanga, xv, sus, jos, o_celula=False):
    """Textul celulei cu bordura din stanga variantei, care cuprinde randul ei.

    BCR pune serviciul in prima coloana si canalul in a doua: "Depunere de numerar
    în contul Clientului" cuprinde randurile "Unități Bancare" si "MFM", fiecare cu
    pretul lui, iar eticheta randului era doar canalul (12 valori fara serviciu).
    Decide bordura, nu apropierea: celula din stanga e centrata pe verticala, iar
    "Casa de schimb" sta mai aproape de numele grupului URMATOR ("Retrageri de
    numerar") decat de al sau ("Depunere de monedă metalică"). Fara borduri nu se
    ghiceste nimic: dupa gol, trei servicii Nexent de pe randuri vecine se lipeau.
    """
    orizontale, cuvinte = geometrie_pagina[:2]
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
    # Tot un pret e si dobanda tabelului alaturat: la BRD, "casa" lua ca parinte
    # "ofertă standard IRCC + 5,10 pp" din coloana DOBANZI.
    if (not text or analizeaza_linie(text)[0] or RE_VALOARE_DOBANDA.search(text)
            or len(text.split()) > CUVINTE_MAX_PARINTE):
        return None
    # Pentru un nume intreg (o_celula), parintele e o singura celula: textul nu
    # trece peste o bordura verticala. Altfel "celula din stanga" a BRD (doua
    # tabele alaturate, DOBANZI | COMISIOANE) aduna trei coloane de dobanzi:
    # "oferta standard IRCC + 2,78 pp IRCC + 2,33 pp Punerea la dispoziție...".
    # Varianta nu cere asta: fara prefix nu spune nimic, iar prefixul ei are
    # uneori o coloana in plus si totusi banda (Vista: "Intre 25.000 – 50.000
    # LEI standard echiv Euro"). Bordura care taie un cuvant nu e bordura (vezi
    # rupe_la_borduri): la BCR, chenarul notei "1143" din "Clientului1143" are 9
    # puncte si trecea drept una.
    verticale = geometrie_pagina[2] if o_celula and len(geometrie_pagina) > 2 else ()
    for m in margini_la(verticale, cy):
        if (stanga + TOL_BORDURA < m < xv - TOL_BORDURA
                and any(w["x1"] <= m for w in din_celula)
                and any(w["x0"] >= m for w in din_celula)
                and not any(w["x0"] < m < w["x1"] for w in din_celula)):
            return None
    return text


def _desparte_index(text):
    """Indexul de la inceputul etichetei, separat de rest."""
    m = RE_INDEX_LA_INCEPUT.match(text)
    return (m.group(1), m.group(2)) if m else (None, text)


# Capitolul numerotat cu majuscule care isi reia numerotarea dedesubt: la BCR,
# "9. ACCEPTARE LA PLATĂ A CARDURILOR" are sub el "1. POS" si "2. E-COMM", iar la
# aceeasi adancime "1. POS" il inlocuia, deci "Taxă de înrolare" nu mai stia ca e
# acceptarea cardurilor. Tot asa "1. CONTURI" si "1. Conturi", "8. CARDURI" si
# "1. Carduri de debit": 401 valori din lista PJ isi recapata capitolul.
ADANCIME_CAPITOL = 0.5


def _majuscule(titlu):
    """Titlu de capitol: cu majuscule, fara paranteze, macar LITERE_MIN_TITLU litere.

    "POS" si "E-COMM" sunt tot cu majuscule, dar sunt subpunctele capitolului.
    """
    fara = RE_PARANTEZA.sub(" ", titlu)
    return fara == fara.upper() and len(re.findall(r"[^\W\d_]", fara)) >= LITERE_MIN_TITLU


def _adancime(index, titlu=""):
    """Adancimea in ierarhie: "4.2." da 2, "7." da 1, "A." da 9 (frunza).

    Cifra romana urmata de un titlu cu majuscule e capitol (0): la BRD, "II. LINII
    DE CREDIT" ramanea frunza sub "2. Credite pentru studii si tratamente
    medicale" (86 de valori cu secțiunea schimbata in ghidul de credite). Literele
    raman frunze ("A. In lei"). Cu majuscule
    peste tot, si in paranteza: BCR "I. CREDITE (cu excepţia creditelor pe card)"
    ramas deasupra facea din "card) > Comision de administrare credit" un
    administrare_card.
    """
    if RE_ROMAN.match(index) and titlu == titlu.upper() and _majuscule(titlu):
        return 0
    if RE_LITERA_SAU_ROMAN.match(index):
        return 9
    return len([p for p in index.rstrip(".").split(".") if p])


def _numere(index):
    """(15, 8) din "15.8" sau "15.8."; None pentru litere si cifre romane."""
    if not index or not re.fullmatch(r"\d+(?:\.\d+)*\.?", index):
        return None
    return tuple(int(p) for p in index.rstrip(".").split("."))


class Sectiuni:
    """Ierarhia de titluri activa, pe adancimi."""

    def __init__(self):
        self.pe_adancime = {}
        self.indexuri = {}      # adancime -> indexul numeric al titlului de acolo
        self.ultima = None

    def _taie(self, a):
        """Sterge nivelurile de la adancimea a in jos."""
        for k in [k for k in self.pe_adancime if k >= a]:
            del self.pe_adancime[k]
            self.indexuri.pop(k, None)

    def _reluat(self, numere):
        """Un "1." sub capitolul numerotat cu majuscule il face capitol."""
        if (numere == (1,) and 1 in self.indexuri
                and _majuscule(self.pe_adancime[1])):
            # Doar capitolul numerotat: titlul documentului ("LISTĂ PREȚURI
            # PERSOANE FIZICE") nu are index si ramane inlocuit, ca inainte.
            self.pe_adancime[ADANCIME_CAPITOL] = self.pe_adancime.pop(1)
            self.indexuri[ADANCIME_CAPITOL] = self.indexuri.pop(1)

    def pune(self, index, titlu):
        a = _adancime(index, titlu) if index else 1
        numere = _numere(index)
        if numere and len(numere) == 1:
            if _majuscule(titlu):
                self._taie(ADANCIME_CAPITOL)     # capitol nou
            else:
                self._reluat(numere)
        self._taie(a)
        self.pe_adancime[a] = titlu
        if numere:
            self.indexuri[a] = index
        self.ultima = a

    def rand_cu_index(self, index):
        """Un rand cu pret care isi poarta indexul inchide ramura fratelui de dinainte.

        La BCR, "6. Comision unic..." si "10. Cost cu avizul de legalitate" au pretul
        pe randul lor, deci nu sunt titluri, iar secțiunea ramanea "3. Comision de
        administrare credit". In lista PJ, 142 de valori stateau sub "1.1. Emitere
        card" dupa "1.2. Mentenanță anuală". "16. Comision verificare valabilitate
        procură" ramanea sub "15.8 Comisioane percepute de terţi pentru
        transferuri" si ieșea transfer_credit. Se inchide doar ramura
        care s-a terminat ("15.8" inaintea lui "16."), la aceeasi adancime sau mai
        jos, nu una reluata de la capat: "1. POS" dupa "9. ACCEPTARE..." e
        numerotarea din capitol, nu un frate.
        """
        nou = _numere(index)
        if not nou:
            return
        self._reluat(nou)
        for k in sorted(k for k in self.indexuri if k >= len(nou)):
            vechi = _numere(self.indexuri[k])
            diferit = next(((a, b) for a, b in zip(vechi, nou) if a != b), None)
            if diferit and diferit[0] < diferit[1]:
                self._taie(k)
                return

    def alipeste(self, titlu):
        """Titlurile cu majuscule se rup pe doua randuri: "CONTURI CURENTE CU" / "SERVICII DE BAZA"."""
        if self.ultima not in self.pe_adancime:
            # "ultima" s-a mutat la capitol sau a fost inchisa intre timp
            self.pune(None, titlu)
        else:
            self.pe_adancime[self.ultima] += " " + titlu

    def subtitlu(self, titlu):
        """Titlul unui grup din interiorul tabelului: sub toate titlurile reale."""
        self.pe_adancime[ADANCIME_SUBTITLU] = titlu

    def rand(self, eticheta):
        """Un rand cu eticheta proprie: ramane sub subtitlu sau il inchide.

        Se inchide la primul rand care isi numeste singur serviciul (vezi
        _e_subtitlu), afara de randul care repeta cuvantul subtitlului: la Nexent,
        "Acceptare garantie de credit..." inchidea "Scrisori de garantie", iar
        "Executare" si "Cesiune" de dupa el nu mai stiau ca sunt ale garantiei (25
        de valori in cele 7 liste, acum documentar).

        "Primul rand de sub subtitlu nu il inchide" a fost incercat si scos: ar fi
        adus "Interogare sold" la BRD (3 valori), dar multe "subtitluri" sunt de
        fapt servicii cu pretul centrat pe randul vecin ("Taxa de anulare/
        modificare" la Vista), iar fratele de sub ele lua conceptul lor: 12 mapari
        noi greșite (poprire, modificare_anulare, conversie_valutara).
        """
        sub = self.pe_adancime.get(ADANCIME_SUBTITLU)
        if sub is None or _e_varianta(eticheta):
            return
        if _cuvant_subtitlu(sub) not in re.findall(r"[^\W\d_]+", eticheta.lower()):
            del self.pe_adancime[ADANCIME_SUBTITLU]

    def cale(self):
        return " > ".join(self.pe_adancime[k] for k in sorted(self.pe_adancime))


def _mobilier(randuri, npagini, cheie=lambda t: t):
    """Textele de antet/subsol: aceeasi linie, in marginea paginii, pe multe pagini.

    Antetul Vista repetat in afara marginii ("TARIFE, TERMENI ŞI CONDIŢII PERSOANE
    FIZICE", 14 din 16 pagini, luat drept titlu) a fost incercat aici si scos: cu
    secțiunea reala sub ele, notele de sub tabel si conditiile pachetelor au primit
    concepte (17 corecte, 17 greșite: "* Comisionul Transfond..." transfer_credit,
    "Serviciu custodie" file_cec). Intai trebuie oprite valorile din note.
    """
    if npagini < 3:
        return set()
    pe_text = {}
    for nr, _cuvinte, _m, _g, texte, in_margine in randuri:
        if in_margine:
            pe_text.setdefault(cheie(" ".join(texte).strip()), set()).add(nr)
    prag = max(2, int(REPETARE_MOBILIER * npagini))
    return {t for t, pagini in pe_text.items() if t and len(pagini) >= prag}


def _fara_cifre(text):
    """Subsolul numerotat se repeta doar fara cifre: "PAGINA 3", "PAGINA 4" erau
    texte diferite, deci ramaneau, iar "PAGINA 3" ajungea eticheta a 3 valori BCR.
    Numarul paginii si "Vers.10.2026 9" la Vista, "1/3 Nexent Bank..." la fel."""
    return re.sub(r"\d+", "#", text)


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
                    [w for r in randuri_pagina for w in r], vert)
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
    # fara cifre, doar din margine: in tabel, "#" ar lua orice celula cu un numar
    numerotate = _mobilier(brute, npagini, _fara_cifre)
    return [r[:5] for r in brute
            if (t := " ".join(r[4]).strip()) not in respinse
            and not (r[5] and _fara_cifre(t) in numerotate)]


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
    return _cuvinte_cu_sens(text) <= 2


def _cuvinte_cu_sens(text):
    fara_paranteze = RE_PARANTEZA.sub(" ", text)
    # orice litera, si cu sedila: "iniţială" cu [a-zăâîșț] se rupea in doua, iar
    # "Emitere iniţială" parea un nume de trei cuvinte si inchidea subtitlul
    return len([c for c in re.findall(r"[^\W\d_]{3,}", fara_paranteze)
                if c.lower() not in CUVINTE_GOALE])


# Subtitlul scurt isi spune obiectul in ultimul cuvant ("Scrisori de garantie",
# "Ordin de plata conditionat"); unul lung e o descriere, nu un nume de grup.
CUVINTE_MAX_SUBTITLU_SCURT = 4


def _cuvant_subtitlu(subtitlu):
    """Ultimul cuvant cu sens al unui subtitlu scurt, cu litere mici, sau None."""
    fara = RE_PARANTEZA.sub(" ", subtitlu)
    if len(fara.split()) > CUVINTE_MAX_SUBTITLU_SCURT:
        return None
    cuvinte = [c.lower() for c in re.findall(r"[^\W\d_]{5,}", fara)
               if c.lower() not in CUVINTE_GOALE]
    return cuvinte[-1] if cuvinte else None


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
    # Un "0" sau "-" in coloana de pret nu e index, e pretul: la TBI, "Inchidere
    # cont curent/ Current account closing || 0" e un serviciu gratuit, nu un
    # grup. Luat drept subtitlu, dobanzile la sold de dedesubt (0%, 3 valori)
    # ieseau inchidere_cont.
    if any(texte[j] for j in range(i + 1, len(texte))):
        return False
    # Nici un element de lista: "- Caseta II (100*260*390 mm)" (Techventures) are
    # pretul pe randul de dedesubt si ajungea secțiunea casetei urmatoare.
    if (len(t) > LUNGIME_MAX_SUBTITLU or RE_CONTINUARE.match(t) or RE_LINIUTA.match(t)
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
    # Lungimea fara paranteze: "4. Cost de asigurare viaţă şi complexă (opţional,
    # încasat lunar, aplicat la soldul creditului)" are peste 90 de caractere doar
    # din paranteza, iar asigurarile BCR ramaneau sub "3. Comision de administrare".
    if (len(index) == 1 and index[0] < nevide[0]
            and len(RE_PARANTEZA.sub("", t)) <= 90 and not RE_CONTINUARE.match(t)):
        return texte[index[0]], t
    return None


def _introduce_lista(text):
    """Numele lung doar din paranteza, terminat in ":", deci nu proza.

    "Cost de asigurare de viaţă (opţional, încasat lunar, aplicat la soldul
    creditului):" (BCR) are 13 cuvinte si cadea la filtrul de proza, iar
    "- credite garantate" de sub el ramanea sub asigurarea de dinainte.
    """
    return (text.endswith(":")
            and len(RE_PARANTEZA.sub(" ", text).split()) <= CUVINTE_MAX_RAND_UNIC)


def _index_rand(texte, i_eticheta):
    """Indexul propriu al randului: in prima celula sau la inceputul numelui."""
    prima = next((x for x in texte if x), "")
    if RE_INDEX_CELULA.match(prima):
        return prima
    m = i_eticheta is not None and RE_INDEX_SECTIUNE.match(texte[i_eticheta])
    return m.group(1) if m else None


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


def _e_titlu(texte, nevide, margini, latime_tabel, col_nume=None):
    """(index, titlu) daca randul e un titlu de sectiune, altfel None.

    `col_nume` e coloana numelui in tabelul randului (vezi coloana_numelui).
    """
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
    # Lista numerotata din celula de pret sau de conditii nu e titlu: la Salt, "2.
    # Clientii Salt Fondatori." (conditia pachetului, in coloana SALT PREMIUM)
    # ajunsese secțiunea a 99 de valori pana la pagina 4, iar la ProCredit "3.
    # Deții in conturile de EURO /" pe cea a 28 de valori din paginile 1-4.
    din_nume = col_nume is None or i == col_nume
    if din_nume and _e_titlu_cu_index(t):
        m = RE_INDEX_SECTIUNE.match(t)
        return m.group(1), m.group(2)
    if len(t) > 90 or not re.search(r"[A-Za-zĂÂÎȘȚăâîșț]{3}", t):
        return None
    if t.endswith(",") or RE_DOAR_MONEDE.match(t):
        return None     # fragment de fraza, sau un rand de antet cu monede
    m = RE_INDEX_SECTIUNE.match(t)
    if m:
        return (m.group(1), m.group(2)) if din_nume else None
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

    "-", "–" sau "N/A" in coloana de pret spun ca serviciul nu exista acolo, nu
    numesc o coloana. Numarate ca nume, faceau din randul "Eliberare numerar EUR si
    USD | | -" (Libra) un antet: serviciul disparea, iar "-" ajungea coloana
    valorilor de dedesubt (46 de valori in setul fix: BRD 16, BCR 11, Libra 19).
    """
    nevide = [i for i in nevide if not RE_DOAR_ORNAMENT.match(texte[i])]
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


# Numele de pe aceeasi linie cu preturile, rupt de grila pe randul urmator: la BCR
# Locuinte, "AVIZ DE GARANTIE INITIAL" sta la 0,9 puncte sub "50 lei + TVA". A doua
# linie a unui nume sta la 6 (Vista, "Administrare" / "Pachet").
LIPIRE_SUB_PRET = 3


def _sus(rand):
    return min(w["top"] for w in rand[1])


def _pret_fara_nume(randuri, analize, j):
    """Randul j are valori, dar nicio celula care sa-i poarte numele?"""
    return (any(a[0] for a in analize[j])
            and not _celula_eticheta(randuri[j][4], analize[j]))


def _colt_antet(randuri, analize, k):
    """Coloana 0 a antetului k, cand ea numeste randul de preturi de dedesubt.

    Coltul antetului poate fi chiar numele randului de preturi, cand acela n-are
    nume: BCR PJ, "Comision administrare pachet | George Business START | DINAMIC |
    FLUX | COMPAS", apoi "| 100 | 150 | 250 | 400 LEI/lună". Doar coloana 0 si
    doar cand intre ea si primul pret nu mai e alt text in antet: la BRD (ghidul
    de credite), in coloana 0 sta tabelul de dobanzi ("CREDITUL EXPRESSO"), iar la
    BCR "3.1. | Plăți | LEI | Valută" e antetul sub "Direct Debit" ("Plăți" lua
    locul lui debitare_directa, 3 valori).

    Nu cand numele sta pe aceeasi linie cu preturile, rupt de grila (vezi
    LIPIRE_SUB_PRET); o continuare cu litera mica acolo nu e alt nume.
    """
    urm = k + 1
    semn = [round(m) for m in randuri[k][2]]
    if not (urm < len(randuri) and randuri[urm][0] == randuri[k][0]
            and [round(m) for m in randuri[urm][2]] == semn
            and _pret_fara_nume(randuri, analize, urm)):
        return None
    v = next(i for i, a in enumerate(analize[urm]) if a[0])

    def spre_stanga(texte):
        return [i for i, t in enumerate(texte[:v])
                if t and not RE_DOAR_INDEX.match(t) and not RE_DOAR_ORNAMENT.match(t)
                and not RE_DOAR_MONEDE.match(t)]

    dupa = urm + 1
    if (dupa < len(randuri) and randuri[dupa][0] == randuri[k][0]
            and _sus(randuri[dupa]) - _sus(randuri[urm]) <= LIPIRE_SUB_PRET):
        sub = spre_stanga(randuri[dupa][4])
        if sub and not RE_CONTINUARE.match(randuri[dupa][4][sub[-1]]):
            return None
    return 0 if spre_stanga(randuri[k][4]) == [0] else None


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


# Nota de sub tabel (sau dintr-o caseta) se citea ca rand de tarif: la Vista
# "*Comisionul Transfond de 0,51 LEI ... si comisionul BNR de 6 LEI pentru platile
# ≥ 50.000 LEI sunt incluse" dadea trei "comisioane", intre ele pragul de 50.000;
# la Eximbank "NOTE: 1) ... 2) 20 lei pentru Mastercard Standard..."; la BRD, TBI si
# ProCredit "4Clienti vulnerabili ... 60% din castigul salarial". Valorile raman —
# unele sunt preturi reale, dar conditionate si cu eticheta luata din nota — si
# primesc categoria "nota", care le scoate din comparatie. Masurat pe cele 50 de
# liste: 98 de valori, dintre care 47 mapate, toate pe concepte gresite (taxele
# Transfond/BNR "incluse" ca transfer_credit, disputa RoPay ca refuz_plata) in afara
# de una: BCR, "1 leu începând cu 01.09.2026" din nota 7, pretul unor pachete.
# Marcajul: asterisc, "Nota:"/"NOTE:"/"Nota bene:", sau numarul notei lipit de
# cuvant ("4Clienti", "1În", "17Financially"). Numarul urmat de spatiu nu: "1
# Comision..." e si randul numerotat al unui tabel.
RE_MARCAJ_NOTA = re.compile(
    r"^\s*(?:\*+\s*\S|(?i:not[ăae]\s*(?:bene\s*)?:)|\d{1,2}[A-ZĂÂÎȘȚ][a-zăâîșț])")
# Randurile notei incep la aceeasi margine; lista din nota e indentata (BCR "▪ 2.000
# Lei pentru Cardul George Standard" la 28 de puncte de marginea notei)
DX_NOTA = 30
LATIME_MIN_BORDURA_NOTA = 60
# Celula cu atatea cuvinte e proza: "gratuit" din ea nu e un pret. Nexent, in caseta
# de sub tabel, "...dreptul sa denunte unilateral Contractul, imediat si gratuit",
# iesea modificare_anulare gratuit (5 valori); Salt "Un glosar ... este disponibil
# in mod gratuit".
CUVINTE_MAX_GRATUIT = 12
# Antetul firmei pe prima pagina, pe care _mobilier nu-l vede sub 3 pagini: BCR
# (cardurile de credit, 2 pagini) "Capital Social: 1.625.341.625,40 lei" iesea
# comision de 1,6 miliarde, "apelabil gratuit din orice reţea naţională" gratuit.
# Pe celula valorii, nu pe eticheta: "Consemnare si confirmare capital social" e
# un serviciu cu pret (BRCI, Raiffeisen).
RE_ANTET_FIRMA = re.compile(r"capital\s+social\s*:|apelabil|din\s+orice\s+re[țţt]ea", re.I)


def _bordura_intre(orizontale, sus, jos, x):
    """O bordura orizontala trece intre doua randuri, prin dreptul lui x?

    Doua umpleri alaturate lasa aceeasi muchie de doua ori, la acelasi y, si nu e
    o linie: Vista coloreaza fiecare rand al notei cu dreptunghiul lui, deci intre
    "*Comisionul Transfond..." si "6 LEI ... sunt incluse" era o "bordura" la 84,7
    (de doua ori). O linie e o muchie singura sau un dreptunghi subtire, cu a doua
    muchie la sub 2 puncte (ProCredit, 445,1 si 445,6). Sublinierea unui cuvant nu
    e bordura: la Eximbank, "NOTE:" e subliniat pe 23 de puncte, iar bordurile de
    celula masurate au peste 270.
    """
    prin_x = [t for t, x0, x1 in orizontale
              if x0 - 1 <= x + 5 <= x1 + 1 and x1 - x0 >= LATIME_MIN_BORDURA_NOTA]
    for t in prin_x:
        if sus - 1 <= t <= jos + 1:
            gemene = sum(1 for t2 in prin_x if abs(t2 - t) < 0.1)
            subtire = any(0.1 <= abs(t2 - t) <= 2 for t2 in prin_x)
            if gemene == 1 or subtire:
                return True
    return False


def _nota_dupa(nota, pagina, x, sus, jos, nevide, proza, orizontale):
    """Nota in curs dupa randul acesta: (pagina, x, jos, sus, proza) sau None.

    Nota tine pana la urmatorul rand de tabel: unul cu mai multe celule, unul care
    incepe in alta parte, sau unul de dincolo de o bordura orizontala. La
    ProCredit, "*Excepție: retragerile ... Euronet" sta in coloana numelui, iar sub
    ea "Depuneri de numerar gratuite" incepe la acelasi x; doar bordura le
    desparte. Proza sarita de extrage_tarife deschide si ea o nota: bucatile ei
    scurte ("1EUR/2EUR).", "▪ 2.000 Lei pentru Cardul George") treceau filtrul.

    Acelasi rand vizual, rupt in doua de exponentul notei ("17Financially" la 634,
    restul frazei la 635 si x=100), continua nota oriunde ar incepe. Dar nu dupa
    proza: la Raiffeisen (pagina la 300 dpi) un rand de tabel fara goluri detectate
    e "proza", iar pretul lui, "12 lei", sta pe acelasi rand vizual la x=2726.
    """
    if len(nevide) != 1:
        return None
    if proza or RE_MARCAJ_NOTA.match(nevide[0]):
        return (pagina, x, jos, sus, proza)
    if nota and nota[0] == pagina and (
            (abs(sus - nota[3]) <= TOL_BORDURA and not nota[4])
            or (nota[1] - TOL_BORDURA <= x <= nota[1] + DX_NOTA
                and not _bordura_intre(orizontale, nota[2], sus, x))):
        return (pagina, nota[1], jos, sus, proza)
    return None


def _e_nota(tip, text):
    """Valoarea citita din proza sau din antetul firmei, nu dintr-o celula de pret."""
    return bool(RE_ANTET_FIRMA.search(text)
                or (tip == "gratuit" and len(text.split()) > CUVINTE_MAX_GRATUIT))


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
    # (pagina, x, jos, sus, proza) al notei in curs: marginea ei si ultimul ei rand
    nota = None
    for k, ((nr_pagina, cuvinte, margini, geometrie, texte), analiza) in enumerate(
            zip(randuri, analize)):
        sus = min(w["top"] for w in cuvinte)
        jos = max(w["bottom"] for w in cuvinte)
        nevide = [i for i, t in enumerate(texte)
                  if t and not RE_DOAR_INDEX.match(t)]
        x = cuvinte[0]["x0"]
        # un rand fara nicio coloana si cu multe cuvinte e proza, nu tarif
        tot_randul = " ".join(texte).strip()
        proza = (geometrie == "unic" and len(cuvinte) > CUVINTE_MAX_RAND_UNIC
                 and not _e_titlu_cu_index(tot_randul) and not _introduce_lista(tot_randul))
        nota = _nota_dupa(nota, nr_pagina, x, sus, jos, [texte[i] for i in nevide],
                          proza, geometrie_pagini[nr_pagina][0])
        if proza:
            continue
        if RE_CUPRINS.search(tot_randul):
            continue          # rand din cuprins, nu din tabel

        if pagina_anterioara != nr_pagina:
            blocuri_et = []          # pagina noua, alte poziții verticale
        pagina_anterioara = nr_pagina

        are_valori = any(v for v, _p, _f, _d in analiza)
        semn = tuple(round(m) for m in margini)
        coloane_pret = pret[semn]
        coloane_pret = coloane_pret - {col_nume.get(semn)}
        # Suma din fraza din coloana numelui e conditia serviciului, iar fraza ramane
        # numele lui (vezi _conditii_in_nume); pentru eticheta, celula n-are valori.
        # Fara coloana a numelui (tabel in care fiecare celula are o cifra), numele e
        # prima celula: Raiffeisen, "Operațiuni de plată de mare valoare (mai mari
        # sau egale cu 50.000 lei) | 6 lei".
        conditii = _conditii_in_nume(
            texte, analiza, col_nume.get(semn, nevide[0] if nevide else None))
        analiza_et = [([],) + tuple(a[1:]) if i in conditii else a
                      for i, a in enumerate(analiza)]

        if not are_valori:
            titlu = _e_titlu(texte, nevide, margini, latime_tabel, col_nume.get(semn))
            if titlu:
                index, text = titlu
                if index is None and rand_titlu_caps == k - 1:
                    sectiuni.alipeste(text)
                else:
                    # indexul din celula lui: "9." | "ACCEPTARE LA PLATĂ A CARDURILOR"
                    sectiuni.pune(index or _index_rand(texte, nevide[0]), text)
                rand_titlu_caps = k if index is None else None
                antete.clear()      # tabel nou, antetul vechi nu se mai aplica
                semn_cu_valori.clear()   # si tabelul nou n-a dat inca valori
                blocuri_et = []     # si alte etichete
                nota = None         # si nota de dinainte s-a terminat
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
                colt = _colt_antet(randuri, analize, k)
                if colt is not None:
                    # blocul se intinde pana la randul de preturi, altfel acesta lua
                    # titlul de sub el ("Componente obligatorii ale pachetului")
                    blocuri_et.append((sus, max(w["bottom"] for w in randuri[k + 1][1]),
                                       texte[colt], False, margini[colt]))
                continue
            et = _celula_eticheta(texte, analiza, coloane_pret)
            if et:
                _adauga_eticheta(blocuri_et, sus, jos, texte[et[0]], False,
                                 x=margini[et[0]],
                                 x_text=_x_celula(cuvinte, margini, et[0]),
                                 bordura=geometrie == "bordura")
                if not subtitlu:
                    sectiuni.rand(texte[et[0]])
            continue

        # rand cu valori: eticheta lui poate continua si pe randurile urmatoare
        et = _celula_eticheta(texte, analiza_et, coloane_pret)
        index_rand = _index_rand(texte, et[0] if et else None)
        if index_rand:
            sectiuni.rand_cu_index(index_rand)
        if et:
            text_et = " ".join(texte[i] for i in et)
            # un rand cu doar conditii e o linie de nume: ProCredit "Retrageri de
            # numerar (LEI), gratuite de la ATM-uri din" / "România în limita a
            # 10.000 LEI/zi" se lipesc
            _adauga_eticheta(blocuri_et, sus, jos, text_et,
                             any(a[0] for a in analiza_et), x=margini[et[0]],
                             x_text=_x_celula(cuvinte, margini, et[0]),
                             bordura=geometrie == "bordura")
            sectiuni.rand(text_et)
        semn_cu_valori.add(semn)
        pret[semn].update(i for i, a in enumerate(analiza_et) if a[0])
        de_emis.append((nr_pagina, sus, jos, texte, analiza, geometrie,
                        blocuri_et, sectiuni.cale() or None,
                        antete.get(semn, []), margini[0], nota is not None, conditii))

    # A doua trecere: acum fiecare bloc de eticheta e intreg
    cu_pret = defaultdict(set)     # lista de blocuri -> blocurile care primesc o valoare
    for _n, sus, jos, _t, _a, _g, etichete_active, *_r in de_emis:
        if etichete_active:
            cu_pret[id(etichete_active)].add(_bloc_pentru(sus, jos, etichete_active))
    inregistrari = []
    serviciu = sectiune_anterioara = None
    conditie = frecventa = None
    for (nr_pagina, sus, jos, texte, analiza, geometrie, etichete_active,
         sectiune, antet, stanga, in_nota, conditii) in de_emis:
        gasita = _eticheta_pentru(
            sus, jos, etichete_active,
            lambda xv, o_celula=False, g=geometrie_pagini[nr_pagina], st=stanga, a=sus,
            b=jos: (_celula_din_stanga(g, st, xv, a, b, o_celula)
                    if xv - st > DX_VARIANTA else None),
            cu_pret[id(etichete_active)])
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
                    "rol": ("conditie" if i in conditii
                            else rol_de_conditie(texte[i], serviciu, val) or rol),
                    "categorie": "nota" if in_nota or _e_nota(tip, texte[i]) else
                                 categorie(sectiune, serviciu,
                                           f"{texte[i]} {antet[i] if i < len(antet) else ''}",
                                           texte[i], antet[i] if i < len(antet) else ""),
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
