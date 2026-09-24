"""Comisioanele din documentele standardizate prin Legea 258/2017.

De ce anume acestea, si nu toate cele 320 de PDF-uri: formularul e impus prin lege
(directiva UE 2014/92, PAD) cu secțiuni si terminologie identice la toate bancile.
Un singur parser le acopera pe toate, iar terminologia standard face comparatia
intre banci posibila — ceea ce paginile web nu permit, fiindca fiecare banca isi
numeste serviciile altfel.

Doua lucruri au trebuit invatate din date, nu presupuse:

1. Bordurile nu se detecteaza dupa grosimea unui segment. Bancile deseneaza o
   bordura ca multe segmente scurte, cate unul pe celula; insumand lungimea pe
   aceeasi poziție, bordurile reale ies clar deasupra decoratiilor (vezi _margini).

2. Nici randurile de grila singure nu ajung. BCR pune mai multe servicii intr-un
   rand de grila, ca randuri de text fara bordura intre ele; Libra pune numele o
   singura data, urmat de multe comisioane. Asa ca randul de grila mărgineste
   acumularea (altfel numele serviciului inghite antetul si subsolul paginii), iar
   in interiorul lui se lucreaza pe randuri de text.

   Limita cunoscuta: unde etichetele si sumele se interleaveaza fara bordura
   (BCR), atribuirea numelui de serviciu poate uni doua servicii. Sumele, monedele,
   frecventele si conditiile sunt corecte; eticheta e cea nesigura.

Deosebirea fata de parser_rate: aici valorile sunt in majoritate SUME absolute
(lei, euro), nu procente. Modelul de date e separat tocmai de aceea.
"""
import re
from pathlib import Path

import pdfplumber

# "comisio", nu "comision": pluralul romanesc nu e un sufix — "comisioane" NU contine
# "comision" (comisio-ane vs comisio-n). Cu forma de singular, tiparul nu potrivea
# niciun nume de fisier si descoperirea raporta tacut zero documente.
RE_NUME_FID = re.compile(r"(informare|info)[^/\\]{0,40}comisio", re.I)
RE_TITLU_FID = re.compile(
    r"document\w*\s+de\s+informare\s+cu\s+privire\s+la\s+comisioane"
    r"|document\w*\s+privind\s+comisioanele", re.I)

# USD, GBP si CHF nu erau citite deloc: 57 de sume in 7 banci (cardurile in USD
# ale BCR si BRD, "3 USD 2,5 GBP 3 CHF" la BRCI). Pe langa suma pierduta, coada
# celulei ramasa fara valoare ("tranzacție" sub "5 USD/") ajungea nume de serviciu.
MONEDE = {"lei": "LEI", "leu": "LEI", "ron": "LEI", "eur": "EUR", "euro": "EUR",
          "usd": "USD", "gbp": "GBP", "chf": "CHF"}
BANI = r"\d{1,3}(?:[.\s]\d{3})*(?:,\d{1,2})?|\d+(?:[.,]\d{1,2})?"
# "euro" inaintea lui "eur": alternarea e ordonata, deci cu "eur" primul cuvantul
# "euro" se potrivea mereu ca "eur" si lasa un "o" orfan in linie dupa ce banda era
# taiata — iar litera ramasa se numara in _e_doar_banda.
VAL = r"(?:lei|leu|ron|euro|eur|usd|gbp|chf)"

# "Neurmat de litera", nu "\b": nota de subsol se lipeste de moneda ("2 RON2",
# "30 Lei1167", "150 LEI6"), iar cu "\b" suma se pierdea de tot — 28 de celule din
# cele 68 de documente, fiecare cu singurul ei pret. "10 EURIBOR" ramane nepotrivit.
RE_SUMA = re.compile(rf"({BANI})\s*({VAL})(?![^\W\d_])", re.I)
# Lookbehind-ul opreste potrivirea sa inceapa in MIJLOCUL unui numar, iar
# zecimalele nu mai sunt limitate la trei. Fara ele, "0,0125%" iesea 125%
# si "3,93606%" iesea 606% — regexul renunta la inceputul numarului si
# prindea coada lui. Valori false care arata perfect normal in tabel.
# Efectul secundar e dorit: "1500%" nu mai produce nimic, in loc de 500%.
RE_PROCENT = re.compile(r"(?<![\d.,])(\d{1,3}(?:[.,]\d+)?)\s*%")
# comision zero declarat in cuvinte
RE_GRATUIT = re.compile(
    r"\bgratuit\b|f[aă]r[aă]\s+comision|nu\s+se\s+percepe|\bincluse?\b", re.I)
# ...dar "Produse și servicii incluse" e titlul listei din pachet, nu un pret.
# Citit ca "gratuit", dadea 12 valori false (ProCredit 7, Vista 3, Techventures 2),
# intre ele "Administrare pachet: gratuit" la Techventures si "Cost lunar:
# gratuit" la fiecare pachet ProCredit.
RE_TITLU_INCLUSE = re.compile(
    r"^\W*(?:produse|servicii)(?:\s+(?:[șsş]i)\s+(?:produse|servicii))?\s+incluse\b", re.I)
RE_FRECVENTA = re.compile(
    r"\b(lunar|anual|trimestrial|semestrial|zilnic|"
    r"pe\s+opera[tț]iune|per\s+opera[tț]iune|la\s+fiecare)\b"
    # si forma cu bara, care e cea folosita in listele de tarife: "5 lei/lună",
    # "1% /an", "min. 1 LEI/tranzacție". Cu doar formele in cuvinte, frecventa
    # lipsea exact acolo unde e scrisa cel mai des.
    r"|/\s*(lun[ăa]|an|zi|trimestru|semestru|opera[tț]iune|tranzac[tț]ie|card|mesaj)\b"
    r"|\bpe\s+(lun[ăa]|an|zi|trimestru|semestru)\b", re.I)
# forma din text -> eticheta normalizata
FRECVENTE = {
    "luna": "lunar", "lună": "lunar", "lunar": "lunar",
    "an": "anual", "anual": "anual",
    "zi": "zilnic", "zilnic": "zilnic",
    "trimestru": "trimestrial", "trimestrial": "trimestrial",
    "semestru": "semestrial", "semestrial": "semestrial",
}
# Banda de valoare a tranzactiei, NU comisionul: "0 – 49.999 Lei", "peste 50.000 Lei".
# Fara asta, 49.999 ajungea raportat drept comision de transfer — aceeasi capcana ca
# "avans 15%" pe web: o cifra cu moneda langa ea, care nu e un pret. Banda e insa
# utila: e conditia in care se aplica comisionul.
RE_PRAG = re.compile(
    rf"(?:{BANI})\s*{VAL}?\s*[–—-]\s*(?:{BANI})\s*{VAL}"
    # "intre 1.000,00 99.999,99 EUR": separatorul dintre capete lipseste uneori.
    #
    # Alternativa asta trebuie sa stea INAINTEA celei cu un singur capat, altfel nu
    # se aplica niciodata: alternarea in Python e ordonata, iar pe "intre 0 lei –
    # 49.999,99 lei" varianta de mai jos potrivea doar "intre 0 lei" si lasa capatul
    # din dreapta in linie, de unde ieșea comision de 49.999,99 lei. Erau 9 valori
    # de banda raportate drept preturi (Libra x6, BRCI, TBI), iar linia
    # transfer_credit/pf avea din cauza lor dispersie interna de 111.111x.
    #
    # Cuvantul spune singur cate capete are banda: "intre" si "de la" au doua,
    # "peste", "sub" si "pana la" au unul. De aceea extinderea se face numai pe
    # primele doua — pe "sub 1.000 lei - 5 lei" ar mancat comisionul.
    rf"|\b(?:[îi]ntre|de\s+la)\s+(?:{BANI})\s*{VAL}?"
    rf"\s*(?:si|and|p[âa]n[ăa]\s+la|[-–—])?\s*(?:{BANI})\s*{VAL}"
    # separatorul de dupa cuvantul de prag poate fi si "/": Salt scrie "sau pana
    # la/200 EUR luna". Cu `\s+` pragul scapa si 200 iese drept comision.
    # "pana in" pe langa "pana la": BRCI scrie "pentru sume până în 50.000 Lei: 5 lei",
    # iar fara varianta cu "in" pragul de 50.000 ieșea drept comision de transfer
    rf"|\b(?:peste|sub|p[âa]n[ăa]\s+(?:la|[îi]n)|[îi]ntre|de\s+la)[\s/]+(?:{BANI})\s*{VAL}"
    # si cu simbol, nu doar in cuvinte: listele de tarife scriu "≤ 1.500 LEI",
    # "> 20.000 LEI", "sume < 1.000,00 EUR". Erau 149 de praguri raportate drept
    # preturi — 3,6% din valorile listelor de tarife.
    # "=" dupa simbol e obligatoriu opțional: BRD scrie ">=12.000 lei", iar fara
    # el pragul trecea drept comision
    rf"|[<>≤≥]=?\s*(?:{BANI})\s*{VAL}?", re.I)
# rolul unei sume care margineste un comision procentual: "minim 10 Lei, maxim 100 Lei"
# Documentele scriu abrevierile "min." si "max", nu formele intregi. Cu doar
# "minim|maxim", rolul nu se atribuia niciodata — pierdere silentioasa.
RE_ROL = re.compile(
    r"\b(min|minim|minimum|max|maxim|maximum|cel\s+pu[tț]in|cel\s+mult)\b\.?", re.I)

# --- cifre care nu sunt preturi, a doua runda: cerinte si limite ---
#
# Continuarea lui RE_PRAG. Pragul de acolo e banda in care se aplica comisionul
# ("0 – 49.999 Lei"); aici sunt trei alte feluri de cifre cu moneda langa ele care
# tot nu sunt preturi, gasite prin dispersia tabelului de comparatie: linia cu cea
# mai mare dispersie e mereu linia cu o cifra care n-are ce cauta acolo.
#
# Ce NU se poate face: filtrat pe cuvantul "minim". El are doua sensuri, iar
# masurat, 56 din cele 66 de apariții sunt plafoane reale de comision, in care 15
# din "0,1% min. 15 EUR" chiar E pretul. Ce separa sensurile e substantivul care
# guverneaza cifra: o incasare, un rulaj, un sold sau un venit sunt cerinte pe care
# clientul le indeplineste, nu margini ale pretului.
CERINTA_CLIENT = (r"[îi]ncas[ăa]r\w*|rulaj|de[țt]inut\w*|de[țt]iner\w*|resurse"
                  r"|sold|economii|salari\w*|venit\w*")
RE_CERINTA = re.compile(
    # "exista o incasare de minimum 1.000 LEI", "incasari minime3 de 700.000 EUR",
    # "sunt detinute minimum 2.000 EUR", "Rulaj al incasarilor de minim 75%"
    rf"(?:{CERINTA_CLIENT})[^.;]{{0,30}}?\bminim\w*\b[^.;]{{0,12}}?\d"
    rf"|\bminim\w*\b[^.;]{{0,30}}?(?:{CERINTA_CLIENT})[^.;]{{0,12}}?\d"
    # definitia unui tip de client, nu un comision: BRD isi defineste clientii
    # vulnerabili prin "al caror venit lunar nu depaseste 60% din salariul minim".
    # Cele trei valori de 60% ieseau in tabel drept comision procentual.
    rf"|(?:{CERINTA_CLIENT})[^.;]{{0,40}}?(?:nu\s+)?dep[ăa][șs]e[șs]te[^.;]{{0,12}}?\d", re.I)
# Un procent lipit de "reducere" e un discount, nu comisionul: "100% reducere fata de
# platile standard" ieșea drept comision de 100%. Atenție, "Gratuit / 12,5 LEI pentru
# conturile din programul OUG 130/2020" NU intra aici — acolo 12,5 e un pret real,
# alternativa la gratuitate.
RE_REDUCERE = re.compile(r"reducer[ei][^.;]{0,30}?\d|\d\s*%[^.;]{0,15}?reducere", re.I)
# A cincea familie: pragul spus prin comparativ, nu prin "minim". Raiffeisen imparte
# transferurile in "Operatiuni de plata de mica valoare (mai mici decat 50.000 lei)",
# iar Libra conditioneaza o dobanda de "sold mai mare de 500 RON" — in ambele, cifra
# e marimea de la care se schimba regula, nu pretul.
#
# Excepția e idiomul care margineste comisionul insuși: "0,5% din valoarea nominala
# totala, DAR NU MAI PUTIN DE ..." (BCR) si "DAR NU MAI MULT DE 0,01% per zi de
# intarziere" (TBI) — acolo numarul e pret, cu rol de plafon. Discriminantul nu e
# cuvantul comparativ, ci daca e negat: "nu mai puțin de" leaga numarul de comision,
# "mai puțin de" il leaga de operatiune.
#
# Verificat pe toate cele 9 valori din corpus care conțin un comparativ: 6 sunt praguri
# (Raiffeisen 50.000, Libra 500 x5), 2 sunt plafoane de comision (BCR, TBI), iar a noua
# e un superlativ — "0,5% din valoarea CEA MAI MARE a limitei de credit" — pe care
# prepozitia obligatorie de dupa comparativ o lasa afara, fiindca acolo urmeaza "a".
# "mare" face pluralul "mari", deci tulpina e "mar", nu "mare" — a sasea data in
# proiect in care pluralul romanesc nu e un sufix lipit la singular. Fara asta,
# "Operatiuni de plata de mare valoare (mai mari sau egale cu 50.000 lei)" trecea.
RE_COMPARATIV = re.compile(
    r"\bmai\s+(?:mic|mar[ei]|mult|pu[țt]in)\w*\s+(?:sau\s+egal\w*\s+)?"
    r"(?:de|dec[âa]t|cu)\b", re.I)
RE_MARGINE_COMISION = re.compile(r"\bnu\s+mai\s+(?:mic|mar[ei]|mult|pu[țt]in)", re.I)
# A patra familie, unde discriminantul e invers: nu textul, ci eticheta. Garanti are
# un tabel de limite de tranzacționare in care eticheta e chiar "limită zilnică" si
# textul doar "500.000 LEI". Ancorarea la inceput e obligatorie: "Comision SMS -
# peste limita inclusă în abonament" e un comision real de 0,8 LEI, iar "din card de
# credit – limită avans numerar" e unul de 1% + 5 LEI.
RE_ETICHETA_LIMITA = re.compile(r"^\s*(?:limit[ăa]|plafon)\b", re.I)
# ...dar nici eticheta ancorata nu ajunge singura. La Raiffeisen, eticheta "Limita
# zilnică de retragere numerar" a prins prin atribuire un comision real — textul
# "5% (minim 10 lei) din suma utilizată" e formula unui pret, nu o limita. Cele doua
# valori erau singurii falsi pozitivi din 35. Deci eticheta de limita se aplica doar
# cand celula e practic numai cifra ("500.000 LEI", "3.000 lei"), sau cand textul
# vorbeste el insusi despre o limita ("max. 40% din limita de credit").
RE_LIMITA_IN_TEXT = re.compile(r"limit[ăa]|plafon", re.I)
# Limita spusa in fraza, in fata cifrei: ProCredit scrie "Retrageri de numerar,
# gratuite ... în limita a 5.000 LEI/zi", si 5.000 ieșea pret de retragere (9
# valori, 2.000-10.000). Se leaga de cifra ei, nu de rand: pe acelasi rand poate
# sta si pretul.
RE_IN_LIMITA_A = re.compile(r"\blimit[ăa]\s+(?:a|de)\s+(\d[\d.,]*)", re.I)
# A cincea familie, si singura cu discriminant pur structural: pragul se rupe peste
# granita coloanei. Garanti scrie "Transfer credit de mică valoare (sub" in coloana
# de nume si "50.000 LEI)" in cea de valoare — deci 50.000 ieșea drept comision de
# transfer, si o singura astfel de cifra facea nefolositoare o linie cu 6 banci.
# Semnul e paranteza: eticheta deschide una pe care celula de valoare o inchide.
# Cuvantul de prag de la capatul etichetei NU e de ajuns ca semn — BCR are
# "...administrare Pachet tuturor criteriilor de la" urmat de "39 LEI", unde "de la"
# e o referinta la o secțiune si 39 e un pret adevarat.
RE_PRAG_IN_PARANTEZA = re.compile(
    r"\b(?:sub|peste|p[âa]n[ăa]\s+la|de\s+la|[îi]ntre)\b|[<>≤≥]", re.I)
# ...iar in paranteza poate sta si un plafon, nu un prag: Libra are
# "(min 25 ... 500 euro)", unde 500 e marginea de sus a comisionului, deci un pret.
RE_PLAFON_IN_PARANTEZA = re.compile(r"\b(?:min|max)\w*\b", re.I)


def _inchide_paranteza_etichetei(text, eticheta):
    """Celula de valoare inchide o paranteza de prag deschisa in eticheta."""
    if text.count(")") <= text.count("(") or eticheta.count("(") <= eticheta.count(")"):
        return False
    coada = eticheta[eticheta.rfind("(") + 1:]
    return bool(RE_PRAG_IN_PARANTEZA.search(coada)
                and not RE_PLAFON_IN_PARANTEZA.search(coada))


def _doar_cifra(text, prag_litere=12):
    """Celula e practic numai valoarea: cifra, moneda si cel mult un cuvant."""
    rest = re.sub(r"[\d.,%]+", " ", text)
    rest = re.sub(r"\b(lei|ron|eur|euro|usd|gbp|chf)\b", " ", rest, flags=re.I)
    return len(re.findall(r"[A-Za-zĂÂÎȘȚăâîșț]", rest)) < prag_litere


def rol_de_conditie(text, eticheta, valoare):
    """"conditie" daca cifra e o cerinta sau o limita, nu pretul; altfel None.

    Valoarea se pastreaza — limita zilnica a Garanti e informatie reala despre banca
    — dar iese din comparatia de preturi, la fel ca plafoanele min/max.

    Zeroul nu e niciodata o cerinta: nicio banca nu cere un sold minim de 0 lei.
    Fara conditia asta regula avea 12 falsi pozitivi din 23, toti cu valoarea 0
    ("0 Lei in limita primelor 5 retrageri" — acolo zeroul ESTE pretul, iar limita e
    conditia lui).
    """
    if not valoare:
        return None
    if (eticheta and RE_ETICHETA_LIMITA.match(eticheta) and text
            and (_doar_cifra(text) or RE_LIMITA_IN_TEXT.search(text))):
        return "conditie"
    if text and (RE_CERINTA.search(text) or RE_REDUCERE.search(text)):
        return "conditie"
    if text and any(suma(m.group(1)) == valoare for m in RE_IN_LIMITA_A.finditer(text)):
        return "conditie"
    if (text and RE_COMPARATIV.search(text)
            and not RE_MARGINE_COMISION.search(text)):
        return "conditie"
    if text and eticheta and _inchide_paranteza_etichetei(text, eticheta):
        return "conditie"
    return None


RE_DOBANDA = re.compile(r"dob[âa]nd|interest\s+(rate|on)|\bDAE\b|rata\s+anual", re.I)
# "dobânzii" nu contine "dobând": "Marja fixa a dobanzii" (ProCredit, 13 procente)
# si "Rata dobanzii penalizatoare" (Nexent, 8) ieseau comisioane. Doar cand
# eticheta INCEPE cu dobanda: "dobânz" oriunde muta 98 de valori, intre ele toate
# comisioanele de card Raiffeisen, a caror sectiune se cheama "TARIFE SI DOBANZI".
RE_DOBANDA_CAP = re.compile(r"^\W*(?:valoarea\s+)?(?:rat|marj)\w*\s+(?:\w+\s+){0,2}dob[âa]nz",
                            re.I)
# Nu tot ce e scris in lista de tarife e un comision. Verificarea de mana a gasit
# 3 din 24: o limita de tranzactionare si doua rate de dobanda raportate ca
# preturi. Categoria nu arunca valoarea — o marcheaza, ca sa nu intre in
# comparatia de comisioane.
RE_LIMITA = re.compile(
    r"limit[ăae]\w*\s+de\s+tranzac|valoare\s+tranzac|num[ăa]r\w*\s+de\s+tranzac"
    r"|\bplafon", re.I)
# Limita spusa direct: "limită zilnică", "limită maximă pe tranzacție" (Garanti,
# Vista, Raiffeisen: 52 de valori de ordinul 10.000-1.000.000 lei numarate drept
# comisioane). Doar cand celula e practic numai cifra: sub "Limita zilnică de
# retragere numerar", Raiffeisen scrie "5% (minim 10 lei) din suma utilizată",
# adica pretul, nu limita (vezi rol_de_conditie).
RE_LIMITA_SPUSA = re.compile(r"limit[ăae]\w*\s+(?:zilnic|maxim|minim|lunar)", re.I)
RE_CURS = re.compile(r"curs\s+(de\s+)?schimb|curs\s+bnr|exchange\s+rate", re.I)


def categorie(sectiune, serviciu, text, celula=""):
    """Ce fel de cifra e: comision, dobanda, limita de tranzactionare sau curs."""
    tot = f"{sectiune or ''} {serviciu or ''} {text or ''}"
    if RE_DOBANDA.search(tot) or RE_DOBANDA_CAP.search(serviciu or ""):
        return "dobanda"
    if RE_LIMITA.search(tot):
        return "limita"
    if RE_LIMITA_SPUSA.search(tot) and celula and _doar_cifra(celula):
        return "limita"
    if RE_CURS.search(tot):
        return "curs"
    return "comision"


# Secțiunile impuse de formular. Ele sunt adevarata axa de comparatie intre banci:
# masurat pe cele 16 documente, toate cinci apar LITERAL la toate cele 5 banci, in
# timp ce numele serviciilor se potrivesc intre banci doar in 4 cazuri din 116.
# Deci legea standardizeaza structura, nu formularea — si secțiunea e ce putem
# alinia fara sa interpretam.
SECTIUNI_PAD = [
    ("servicii_de_cont", r"servicii\s+de\s+cont\s+generale"),
    ("plati", r"pl[ăa][țt]i\s*\(\s*cu\s+excep[țt]ia\s+cardurilor\s*\)"),
    ("carduri_si_numerar", r"carduri\s+[șşs]i\s+numerar"),
    ("descoperit_de_cont", r"descoperit\s+de\s+cont\s+[șşs]i\s+servicii\s+conexe"),
    ("alte_servicii", r"alte\s+servicii"),
]
RE_SECTIUNI_PAD = [(nume, re.compile(rf"^\s*{tipar}\s*:?\s*$", re.I))
                   for nume, tipar in SECTIUNI_PAD]

# Nota de valabilitate, scrisa in coloana de NUME, imediat sub serviciu, cu acelasi
# corp de litera si acelasi gol vertical ca o continuare de nume (Libra). Nici
# corpul literei, nici grila nu o deosebesc — singurul semn e cum incepe fraza.
# Ea nu e numele serviciului, dar nici nu se arunca: pleaca in "detaliu".
RE_NOTA = re.compile(
    r"^\s*(?:[*†‡]+\s*)+\S|^\s*(?:p[âa]n[ăa]\s+la\s+data|[îi]ncep[âa]nd\s+(?:cu|de)"
    r"|dup[ăa]\s+\d|not[ăa]\s*:|excep[tț])", re.I)


def suma(text):
    """'2.500' -> 2500.0 ; '2,50' -> 2.5 ; '15' -> 15.0

    Atentie: formatul romanesc foloseste punctul ca separator de mii, deci
    float('2.500') = 2.5 ar fi o eroare de trei ordine de marime.
    """
    t = text.strip().replace(" ", "")
    if "," in t and "." in t:
        if t.rindex(".") > t.rindex(","):
            t = t.replace(",", "")
        else:
            t = t.replace(".", "").replace(",", ".")
    elif "," in t:
        t = t.replace(",", ".")
    elif "." in t:
        coada = t.split(".")[-1]
        # ".500" cu exact 3 cifre = separator de mii; ".50" = zecimale
        t = t.replace(".", "") if len(coada) == 3 else t
    try:
        return float(t)
    except ValueError:
        return None


def _margini(masurate, toleranta, prag_relativ):
    """Pozitiile cu lungime acumulata mare — bordurile reale ale tabelului.

    Criteriul nu poate fi lungimea unui segment: o bordura e desenata ca multe
    segmente scurte, cate unul pe celula. Insumand pe aceeasi poziție, bordurile
    ies clar deasupra decoratiilor. Masurat pe BCR, pagina 1: x=90 -> 823,
    x=307 -> 650, x=523 -> 823 (borduri) fata de x=96 -> 80, x=165 -> 96 (decoratii).
    """
    grupuri = []
    for poz, lungime in sorted(masurate):
        if grupuri and poz - grupuri[-1][0] <= toleranta:
            grupuri[-1][1] += lungime
        else:
            grupuri.append([poz, lungime])
    if not grupuri:
        return []
    maxim = max(g[1] for g in grupuri)
    return [g[0] for g in grupuri if g[1] >= prag_relativ * maxim]


def coloane(pagina, toleranta=3, prag_relativ=0.25):
    """Marginile verticale ale tabelului (x), deduse din muchiile desenate."""
    vert = [(round(e["x0"], 1), e["bottom"] - e["top"])
            for e in pagina.edges if e["orientation"] == "v"]
    return _margini(vert, toleranta, prag_relativ)


def linii_de_text(pagina, margini, toleranta=3):
    """[(sus, jos, [text_pe_fiecare_coloana])] — randuri de text, pe coloane.

    Lucram pe randuri de text, nu pe randuri de grila, fiindca bordura orizontala
    lipseste adesea intre subservicii (vezi nota din capul modulului).
    """
    if len(margini) < 2:
        return []
    grupe = {}
    for w in pagina.extract_words(use_text_flow=False):
        grupe.setdefault(round(w["top"] / toleranta), []).append(w)

    out = []
    for cheie in sorted(grupe):
        cuvinte = grupe[cheie]
        celule = [[] for _ in range(len(margini) - 1)]
        for w in sorted(cuvinte, key=lambda w: w["x0"]):
            centru = (w["x0"] + w["x1"]) / 2
            for i in range(len(margini) - 1):
                if margini[i] <= centru <= margini[i + 1]:
                    celule[i].append(w["text"])
                    break
            # cuvintele din afara tabelului (antet, nota de pagina) se ignora
        texte = [re.sub(r"\s+", " ", " ".join(c)).strip() for c in celule]
        if any(texte):
            out.append((min(w["top"] for w in cuvinte),
                        max(w["bottom"] for w in cuvinte), texte))
    return out


def _desprinde_prag(linie):
    """Scoate expresia de banda din linie si o intoarce separat.

    Sumele din interiorul benzii sunt praguri, nu comisioane, deci trebuie scoase
    inainte de a cauta comisionul in restul liniei.
    """
    m = RE_PRAG.search(linie)
    if not m:
        return linie, None
    rest = linie[:m.start()] + " " + linie[m.end():]
    return rest, re.sub(r"\s+", " ", m.group(0)).strip()


def _frecventa(linie):
    """Frecventa comisionului, normalizata: "/lună" si "lunar" dau amandoua "lunar"."""
    m = RE_FRECVENTA.search(linie)
    if not m:
        return None
    gasit = re.sub(r"\s+", " ", next(g for g in m.groups() if g)).lower()
    return FRECVENTE.get(gasit, "pe " + gasit)


def analizeaza_linie(text):
    """(valori, prag, frecventa, descriere) dintr-un text de o singura linie.

    valori: [(tip, valoare, moneda, rol)]
    descriere != None cand linia nu poarta nicio valoare — atunci e eticheta
    subserviciului, iar suma vine pe un rand urmator.
    """
    if not text:
        return [], None, None, None
    linie, prag = _desprinde_prag(text)
    frecventa = _frecventa(linie)

    def rol_pentru(poz):
        """Rolul se citeste imediat inaintea sumei, nu o data pe linie.

        "0,12% min 15 EURO, max 500 EURO" are trei valori cu trei roluri diferite;
        un singur rol pe linie le dadea pe toate "minim".
        """
        # ultima potrivire, nu prima: in "min 15 EURO, max 500" fereastra din fata
        # lui 500 contine si "min", iar prima potrivire ar da rolul greșit
        gasite = list(RE_ROL.finditer(linie[max(0, poz - 18):poz]))
        if not gasite:
            return None
        # Normalizat, nu textul din document: documentele scriu si "min" si "minim",
        # iar rolul intra in cheia de grupare a tabelului de comparatie — nenormalizat,
        # acelasi plafon ieșea pe doua rânduri diferite. Erau 287 de "min" si 32 de
        # "minim" in listele de tarife.
        gasit = gasite[-1].group(1).lower()
        # "cel puțin" -> min, "cel mult" -> max
        return "min" if gasit.startswith("min") or "pu" in gasit else "max"

    valori = []
    for m in RE_PROCENT.finditer(linie):
        v = suma(m.group(1))
        if v is not None:
            valori.append(("comision_procent", v, None, rol_pentru(m.start())))
    for m in RE_SUMA.finditer(linie):
        v = suma(m.group(1))
        if v is not None:
            valori.append(("comision_suma", v, MONEDE[m.group(2).lower()],
                           rol_pentru(m.start())))
    if (not valori and RE_GRATUIT.search(linie) and not re.search(r"\d", linie)
            and not RE_TITLU_INCLUSE.match(linie)):
        valori.append(("gratuit", 0.0, None, None))

    descriere = None
    if not valori:
        d = RE_FRECVENTA.sub("", linie).strip(" :-–•")
        descriere = d if len(d) >= 4 else None
    return valori, prag, frecventa, descriere


def randuri_grila(pagina, toleranta=3, prag_relativ=0.25):
    """Marginile orizontale ale tabelului (y)."""
    oriz = [(round(e["top"], 1), e["x1"] - e["x0"])
            for e in pagina.edges if e["orientation"] == "h"]
    return _margini(oriz, toleranta, prag_relativ)


def blocuri(cale):
    """[(nr_pagina, [linii_de_text])] — liniile grupate pe randuri de grila.

    Randul de grila face doua lucruri, si amandoua s-au dovedit necesare la
    masuratoare:

    - **filtreaza**: randurile din afara suprafetei tabelului (preambulul
      documentului, notele de subsol) nu sunt tarife. Fara filtru ies 58 de valori
      in plus, din proza.
    - **desparte servicii**: am incercat sa renunț la rolul asta si sa las doar
      golul vertical sa margineasca eticheta (vezi blocuri_eticheta), fiindca
      granita de grila taie in doua lista de conținut a pachetului George. A ieșit
      mai rau: 61% etichete curate fata de 70%. Deci exista servicii vecine pe care
      grila le desparte corect si golul vertical nu.
    """
    out = []
    with pdfplumber.open(str(cale)) as pdf:
        for nr, pagina in enumerate(pdf.pages, 1):
            margini = coloane(pagina)
            linii = linii_de_text(pagina, margini)
            if not linii:
                continue
            praguri = randuri_grila(pagina)
            if len(praguri) < 2:
                # pagina fara borduri orizontale: fiecare linie e propriul bloc,
                # ca sa nu se acumuleze nemarginit
                out.extend((nr, [ln]) for ln in linii)
                continue
            for i in range(len(praguri) - 1):
                sus, jos = praguri[i], praguri[i + 1]
                bloc = [ln for ln in linii if sus - 1 <= ln[0] < jos]
                if bloc:
                    out.append((nr, bloc))
    return out


def blocuri_eticheta(bloc, gol_maxim=6):
    """Etichetele grupate in blocuri: [(sus, jos, nume, nota)].

    Nota de valabilitate rămane in intinderea verticala a blocului, dar nu in
    nume. Trebuie sa rămana in intindere fiindca valoarea se tiparește adesea pe
    ultimul rand al notei: daca notele ar fi scoase de tot, valoarea ar cadea in
    afara blocului si ar pleca la serviciul urmator.

    Un nume de serviciu se rupe pe mai multe randuri, iar intre randurile lui cad
    randuri de valoare — coloana de preț e centrata vertical, coloana de nume e
    aliniata sus. Deci blocul nu se poate inchide la primul rand fara nume; se
    inchide doar la un gol vertical mare.

    Masurat pe BCR Pachet George, pagina 1: intre randurile aceleiasi etichete
    golul e 1,8 puncte, intre doua servicii diferite 15,6. Pragul de 6 sta
    comod intre ele.
    """
    out = []
    in_nota = False
    for sus, jos, texte in bloc:
        if not texte[0]:
            continue
        if out and sus - out[-1][1] <= gol_maxim:
            a, _b, nume, nota = out[-1]
            if in_nota or RE_NOTA.match(texte[0]):
                in_nota = True
                nota = f"{nota} {texte[0]}".strip()
            else:
                nume = f"{nume} {texte[0]}"
            out[-1] = (a, jos, nume, nota)
        else:
            # primul rand al unui bloc rămane nume chiar daca arata ca o nota:
            # altfel blocul ar porni fara nume si randul s-ar pierde
            in_nota = False
            out.append((sus, jos, texte[0], ""))
    return out


# Un subpunct numeste varianta, nu serviciul: "Eliberare de numerar în România" e
# urmat de "- de la ghișeele BCR" si "- de la ATM-uri BCR", iar la Raiffeisen
# "Comision pentru retrageri de numerar" de "La ATM-urile băncilor acceptatoare
# din străinătate". Pretul sta pe randul subpunctului, deci fara numele de
# deasupra valoarea ramanea doar cu canalul, fara serviciu. Folosit de ambele
# parsere: in formularul standardizat, CreditCoop scrie "Emitere card:" pe un
# rand de grila si "• Visa Classic Standard 5 lei" pe urmatorul.
# La fel randul care incepe cu un canal fizic: BRD scrie "Retragere de numerar
# ATM/POS" o data, apoi "ATM BRD", "ATM/POS alte banci din Romania", "POS in EUR,
# alte banci din Uniunea". Internet/Mobile Banking nu intra aici: "Internet
# Banking (administrare)" e chiar serviciul, nu varianta lui.
RE_SUBPUNCT = re.compile(r"^\s*[-–—•·▪~]\s*\S|^(?:la|de\s+la|prin|[îi]n|din|c[ăa]tre)\s"
                         r"|^(?:ATM|POS|MFM|EPOS)\b", re.I)


def _e_subpunct(text):
    return bool(RE_SUBPUNCT.match(text))


def eticheta_pentru(sus, jos, etichete):
    """Eticheta careia aparține o valoare, dupa poziția verticala.

    Suprapunerea decide cand exista; altfel cel mai apropiat centru. Ordinea de
    citire NU decide: pe BCR, "0 Lei" se tiparește deasupra numelui serviciului
    sau, deci in ordinea de citire ar ajunge la serviciul precedent.
    """
    if not etichete:
        return None
    suprapuneri = [(min(jos, b) - max(sus, a), -i)
                   for i, (a, b, _n, _nota) in enumerate(etichete)]
    lungime, minus_i = max(suprapuneri)
    if lungime > 0:
        return etichete[-minus_i]
    centru = (sus + jos) / 2
    return min(etichete, key=lambda e: abs((e[0] + e[1]) / 2 - centru))


def _sectiune_pad(bloc):
    """Numele secțiunii de formular, daca blocul e un titlu de secțiune.

    Vocabular inchis, nu euristica: cele cinci titluri sunt impuse prin lege si
    apar literal la toate bancile. Un titlu sta singur in randul lui de grila,
    fara nicio valoare.
    """
    texte_nume = [texte[0] for _sus, _jos, texte in bloc if texte[0]]
    are_valori = any(t for _sus, _jos, texte in bloc for t in texte[1:])
    if are_valori or len(texte_nume) != 1:
        return None
    for nume, tipar in RE_SECTIUNI_PAD:
        if tipar.match(texte_nume[0]):
            return nume
    return None


def extrage(cale, banca, radacina=None):
    """Inregistrarile de comision din documentul standardizat."""
    cale = Path(cale)
    sursa = str(cale.relative_to(radacina)) if radacina else cale.name
    inregistrari = []
    serviciu = None      # ultimul nume incheiat, pentru blocurile care dau doar sume
    sectiune = None      # secțiunea de formular in care ne aflam
    # Numele de deasupra subpunctelor: randurile de grila fara pret. CreditCoop pune
    # fiecare rand in randul lui de grila ("Retrageri de numerar" / "La ghișeu:" /
    # "• Sume până la 5.000 lei"), deci eticheta blocului nu ajunge: 51 din cele
    # 114 comisioane ramaneau cu numele variantei, fara serviciu. Un subpunct fara
    # pret se adauga la lant; un nume intreg il porneste din nou.
    parinti = []

    for nr_pagina, bloc in blocuri(cale):
        titlu = _sectiune_pad(bloc)
        if titlu:
            sectiune = titlu
            parinti = []
            continue
        # Etichetele se grupeaza in blocuri cu poziție verticala, iar fiecare
        # valoare merge la blocul care o cuprinde. Versiunea anterioara potrivea
        # etichetele cu valorile una-la-una, in ordinea de citire, cand numerele
        # coincideau — si greșea exact acolo unde numele se rupe pe doua randuri.
        etichete = blocuri_eticheta(bloc)
        # analizam fiecare linie o singura data si pastram rezultatul
        analiza = []
        for _sus, _jos, texte in bloc:
            pe_linie = [analizeaza_linie(t) for t in texte[1:]]
            analiza.append(pe_linie)
        are_valori = any(v for linie in analiza for v, _p, _f, _d in linie)
        if etichete and not are_valori:
            nume = re.sub(r"\s+", " ", etichete[0][2]).strip()
            # un subpunct continua lantul, dar nu il porneste: la ProCredit,
            # "• Retrageri de numerar (LEI), gratuite..." ajunsese parintele lui
            # "• Depuneri de numerar la terminalele ProCredit"
            parinti = (parinti + [nume] if parinti else []) if _e_subpunct(nume) else [nume]

        conditie = frecventa = None
        bucati = []
        for i, (sus, jos, texte) in enumerate(bloc):
            for pe_coloana, (valori, prag, frecv, descriere) in zip(texte[1:], analiza[i]):
                if prag:
                    conditie = prag
                if frecv:
                    frecventa = frecv
                if descriere and not valori:
                    bucati.append(descriere)
                if not valori:
                    continue
                gasita = eticheta_pentru(sus, jos, etichete)
                nota = ""
                if gasita:
                    serviciu = re.sub(r"\s+", " ", gasita[2]).strip()
                    nota = gasita[3]
                    if parinti and _e_subpunct(serviciu):
                        serviciu = " ".join(parinti + [serviciu])
                detaliu = " ".join(bucati + ([nota] if nota else []))[:160] or None
                for tip, val, moneda, rol in valori:
                    inregistrari.append({
                        "banca": banca,
                        "sectiune": sectiune,
                        "serviciu": serviciu,
                        "detaliu": detaliu,
                        "tip": tip,
                        "valoare": val,
                        "moneda": moneda,
                        "frecventa": frecventa,
                        "conditie": conditie,
                        # o cerinta sau o limita bate plafonul min/max: daca cifra
                        # nu e un pret, rolul de plafon nu se mai aplica
                        "rol": rol_de_conditie(pe_coloana, serviciu, val) or rol,
                        # si in formular: "Rata de dobândă fixă: 12%" la
                        # descoperit (ProCredit, BCR, BRCI: 6 valori) iesea comision
                        "categorie": categorie(sectiune, serviciu, pe_coloana,
                                               pe_coloana),
                        "sursa_pdf": sursa,
                        "pagina": nr_pagina,
                        "text_sursa": pe_coloana[:300],
                    })
                # banda se consuma dupa comisionul pe care il conditioneaza. Fara asta
                # ramanea activa si se lipea si de comisioanele urmatoare, la care nu
                # se aplica — mai bine pierdem o conditie decat sa atasam una greșita.
                bucati = []
                conditie = None
        # Un nume intreg cu pret incheie grupul: subpunctele de dupa el nu mai sunt
        # ale parintelui de deasupra. La ProCredit, "• Plăți instant ≤ LEI 5.000"
        # ajungea "Ordine de plată programată ... • Plăți instant".
        if are_valori and etichete and not _e_subpunct(etichete[0][2]):
            parinti = []
    return inregistrari


def documente_standardizate(radacina_pdf):
    """(confirmate, respinse cu motiv) — titlul e verificat in conținut, nu in nume.

    Respinsele se intorc explicit: un document ilizibil sau cu nume inselator trebuie
    sa se vada in raport, nu sa dispara in tacere.
    """
    gasite, respinse = [], []
    for cale in sorted(Path(radacina_pdf).rglob("*.pdf")):
        if not RE_NUME_FID.search(cale.name):
            continue
        try:
            with pdfplumber.open(str(cale)) as pdf:
                text = "".join((p.extract_text() or "") for p in pdf.pages[:3])
        except (OSError, ValueError, TypeError) as e:
            respinse.append((cale, f"necitibil: {type(e).__name__}"))
            continue
        if RE_TITLU_FID.search(text):
            gasite.append(cale)
        else:
            respinse.append((cale, "numele sugereaza formularul, titlul nu apare in text"))
    return gasite, respinse
