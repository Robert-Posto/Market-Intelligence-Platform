"""Bateria de teste pentru parser, regula de calendar IRCC si validator.

Fiecare caz vine dintr-o pagina reala intalnita in crawl. Cazurile marcate "NU
produce" sunt la fel de importante ca celelalte: ele opresc verificari care ar
da rezultate false.

Rulare:  python scripts/test_validare.py
"""
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crawler.data_document import (data_din_nume, data_din_text,
                                   familie_document, stare_fata_de)
from crawler.parser_pdf import RE_PROCENT
from crawler.ambiguitate import marcheaza
from crawler.diferente import compara as compara_versiuni, rezumat
from crawler.bnr_indici import ircc_in_vigoare, ircc_ultim_aplicabil, perioada_aplicare
from crawler.parser_rate import numar, parseaza_linie
from crawler.validator import _indici_impliciti, _marja_peste_ircc, _perioada_din_text
from crawler.urme import (actualizeaza, amprenta_parser, cale_unica,
                          clasifica_semnal, compara,
                          comparatie_de_valori_permisa, etag_de_incredere,
                          validator_de_incredere)

TRECUTE = ESUATE = 0


def T(cond, eticheta):
    global TRECUTE, ESUATE
    if cond:
        TRECUTE += 1
    else:
        ESUATE += 1
        print(f"  EȘEC  {eticheta}")


def P(linie, asteptat, eticheta):
    """Parseaza o linie si compara (tip, valoare) cu ce se aștepta."""
    got = sorted((i["tip_rata"], i["valoare"])
                 for i in parseaza_linie(linie, "b", "c", "u", "t")[0])
    T(got == sorted(asteptat), f"{eticheta}  (primit {got})")


# --------------------------------------------------- regula de calendar a IRCC
# Trimestrul calculat se aplica din al doilea trimestru calendaristic urmator.
T(perioada_aplicare("2026T1") == (date(2026, 7, 1), date(2026, 9, 30)), "2026T1 -> T3 2026")
T(perioada_aplicare("2025T4") == (date(2026, 4, 1), date(2026, 6, 30)), "2025T4 -> T2 2026")
T(perioada_aplicare("2025T3") == (date(2026, 1, 1), date(2026, 3, 31)), "2025T3 -> T1 2026")
T(perioada_aplicare("nu e trimestru") is None, "eticheta invalida")

SERIE = [{"perioada": "2026T1", "valoare": 5.56},
         {"perioada": "2025T4", "valoare": 5.58},
         {"perioada": "2025T3", "valoare": 5.68}]
T(ircc_in_vigoare(SERIE, date(2026, 9, 16))["valoare"] == 5.56, "in vigoare 16.09.2026")
T(ircc_in_vigoare(SERIE, date(2026, 5, 1))["valoare"] == 5.58, "in vigoare 01.05.2026")
# dupa 1 octombrie, trimestrul aplicabil nu e publicat: nu inventam o valoare
T(ircc_in_vigoare(SERIE, date(2026, 10, 15)) is None, "trimestru nepublicat -> None")
T(ircc_ultim_aplicabil(SERIE, date(2026, 10, 15))["valoare"] == 5.56, "plasa de siguranta")

# --------------------------------------------------- perioada declarata in text
T(_perioada_din_text("IRCC valabil în perioada 01.04.2026 – 30.06.2026 este 5,58%")
  == (date(2026, 4, 1), date(2026, 6, 30)), "perioada cu en-dash")
T(_perioada_din_text("IRCC aplicabil în perioada 01.07 - 30.09.2026, respectiv 5,56%")
  == (date(2026, 7, 1), date(2026, 9, 30)), "an lipsa la prima data")
T(_perioada_din_text("*IRCC valabil de la 01.07.2026: 5.56%")
  == (date(2026, 7, 1), None), "interval deschis")
T(_perioada_din_text("EURIBOR aplicabil in perioada 01.07. - 31.12.2026")
  == (date(2026, 7, 1), date(2026, 12, 31)), "punct dupa luna")
T(_perioada_din_text("nicio data aici") is None, "fara perioada")

# --------------------------------------------------- indicele implicit
T(_indici_impliciti("9.06% (IRCC + 3.5%)") == [("IRCC", 5.56, 9.06, 3.5)], "forma A")
T(_indici_impliciti("- Cu condiția: 3% + IRCC (8.68%)")
  == [("IRCC", 5.68, 8.68, 3.0)], "forma B")
# forma dominanta in piata: scaderea nu are sens, deci nu trebuie sa produca nimic
T(_indici_impliciti("4,89% fixă în primii 3 ani, apoi variabilă IRCC + 2,10%") == [],
  "fix-apoi-variabil NU produce indice implicit")
T(_indici_impliciti("De la 4,70%, ulterior variabilă: marjă 1.90% + IRCC") == [],
  "marja fara total NU produce indice implicit")

# --------------------------------------------------- marja peste care indice
T(_marja_peste_ircc({"tip_rata": "marja_ircc", "text_sursa": ""}), "marja_ircc")
T(not _marja_peste_ircc({"tip_rata": "marja_euribor", "text_sursa": ""}),
  "marja_euribor exclusa")
T(not _marja_peste_ircc({"tip_rata": "marja_fixa",
                         "text_sursa": "Euribor 6 luni + 2,20% marjă fixă"}),
  "marja_fixa peste EURIBOR exclusa")
T(_marja_peste_ircc({"tip_rata": "marja_fixa",
                     "text_sursa": "IRCC aplicabil ... marja fixă de 10%"}),
  "marja_fixa peste IRCC inclusa")

# --------------------------------------------------- parser
P("DAE 4\t8,91%\t8,04%\t6,96%\t5,49%",
  [("dae", 8.91), ("dae", 8.04), ("dae", 6.96), ("dae", 5.49)], "rand de tabel")
P("Marja fixă a dobânzii\t2,90%\t2,50%\t4,05%\t2,20%",
  [("marja_fixa", 2.9), ("marja_fixa", 2.5), ("marja_fixa", 4.05),
   ("marja_fixa", 2.2)], "rand de tabel, marje")
# celula 0 da marja, celula 1 o rata fixa: NU trebuie propagat tipul
P("Variabilă, după formula: EURIBOR 6 Luni + Marjă Fixă** 5,2 p.p.\tFIXĂ 3 ani 6% pe an",
  [("marja_euribor", 5.2)], "NU propaga peste o masura diferita")
P("Ai până la 12 rate cu 0% dobândă", [("rate_fara_dobanda", 0.0)], "promotie in rate")
P("Dobanda pentru disponibilitatile la vedere este 0% p.a.",
  [("nominala", 0.0)], "0% autentic ramane nominala")
P("Dobândă anuală: 2,20%* + IRCC sau 2,6%* + EURIBOR 6 luni",
  [("marja_ircc", 2.2), ("marja_euribor", 2.6)], "marcaje de nota de subsol")
P("Comisionul anual de administrare: Credite în Euro: 0.2% p.a.",
  [("comision_procent", 0.2)], "comision cu p.a. nu e dobanda")
P("IRCC valabil de la 01.07.2026: 5.56%", [("ircc_valoare", 5.56)], "IRCC valoare")
P("Indicele EURIBOR 6 luni este 2,568%", [("euribor_valoare", 2.568)], "capcana zecimala")
P("4.50% % + IRCC (10.18%)", [("marja_ircc", 4.5)], "paranteza e totalul")
P("Avans minim 15% din preț", [], "excludere avans")
P("Se calculează ca în exemplul cu LIBOR de 1%", [], "excludere LIBOR")

T(numar("2,568") == 2.568, "numar: virgula zecimala pe 3 cifre")
T(numar("20,000", ca_procent=False) == 20000.0, "numar: separator de mii")


# --------------------------------------------------- detecția schimbarii
# Starile care nu pot fi produse de o rulare reala inainte sa treaca o zi.
# Cazul care conteaza cel mai mult e ULTIMUL: absenta unui document la o banca
# nerecrawlata NU e o dispariție. Fara el, o rulare in care un site a picat ar
# raporta ca banca si-a retras tarifele.
_URL = "https://x.ro/tarife.pdf"


def _stare(vechi_amprenta, noua_amprenta, moment_vechi, moment_nou,
           cale="output/crawl/pdf/x/tarife.pdf"):
    urme = {"banci": {"x": moment_vechi}, "rulari": [],
            "documente": {_URL: {"banca": "x", "amprenta": vechi_amprenta,
                                 "cale": cale}} if vechi_amprenta is not None else {}}
    observat = {} if noua_amprenta is False else {
        _URL: {"banca": "x", "origine": "x.ro", "origine_proprie": True,
               "cale": cale, "amprenta": noua_amprenta,
               "motiv": None if noua_amprenta else "interzis de robots.txt"}}
    return compara(urme, observat, {"x": moment_nou})[_URL]["stare"]


T(_stare(None, "aaa", None, "L2") == "NOU", "urme: document nou")
T(_stare("aaa", "aaa", "L1", "L2") == "NESCHIMBAT", "urme: aceiasi octeți")
T(_stare("aaa", "bbb", "L1", "L2") == "SCHIMBAT", "urme: octeți diferiți")
T(_stare("aaa", None, "L1", "L2") == "NEDESCARCAT", "urme: referit, nedescarcat")
# banca A fost recrawlata (momentul s-a schimbat) si documentul nu mai apare
T(_stare("aaa", False, "L1", "L2") == "LIPSA", "urme: lipsa dupa recrawl")
# banca NU a fost recrawlata: absenta nu dovedeste nimic
T(_stare("aaa", False, "L1", "L1") == "NEVERIFICAT",
  "urme: absenta fara recrawl NU e dispariție")
# A saptea stare, adaugata dupa ce a produs o constatare falsa: doua URL-uri
# TBI ("/2023/09/" si "/2022/09/") scriu in acelasi fisier local, iar sonda a
# comparat octeții unuia cu amprenta celuilalt — "TBI si-a schimbat documentul",
# care nu se intamplase. Octeții de pe disc apartin URL-ului descarcat ultimul,
# deci nu spun nimic despre niciunul.
T(compara({"banci": {"x": "L1"}, "rulari": [],
           "documente": {_URL: {"banca": "x", "amprenta": "aaa",
                                "cale": "p/f.pdf"}}},
          {_URL: {"banca": "x", "origine": "x.ro", "origine_proprie": True,
                  "cale": "p/f.pdf", "amprenta": "bbb", "cale_partajata": True}},
          {"x": "L2"})[_URL]["stare"] == "AMBIGUU",
  "urme: cale partajata NU se raporteaza ca schimbare")
# ...iar cand calea nu mai e partajata, comparatia redevine valida
T(compara({"banci": {"x": "L1"}, "rulari": [],
           "documente": {_URL: {"banca": "x", "amprenta": "aaa",
                                "cale": "p/f.pdf"}}},
          {_URL: {"banca": "x", "origine": "x.ro", "origine_proprie": True,
                  "cale": "p/ab12cd34_f.pdf", "amprenta": "bbb",
                  "cale_partajata": False}},
          {"x": "L2"})[_URL]["stare"] == "SCHIMBAT",
  "urme: cu fisier propriu, comparatia e valida")
# calea unica e derivata din URL, deci doua URL-uri cu acelasi basename difera
T(cale_unica("https://a.ro/2023/09/f.pdf", "p/f.pdf")
  != cale_unica("https://a.ro/2022/09/f.pdf", "p/f.pdf"),
  "urme: cai unice pentru URL-uri diferite cu acelasi nume")
T(cale_unica("https://a.ro/f.pdf", "p/f.pdf")
  == cale_unica("https://a.ro/f.pdf", "p/f.pdf"),
  "urme: calea unica e stabila pentru acelasi URL")
T(cale_unica("https://a.ro/f.pdf", "p/f.pdf").endswith("_f.pdf"),
  "urme: calea unica pastreaza numele original")
# O scriere poate fi "plina" si totusi sa piarda ce a invatat sistemul.
# actualizeaza() intorcea un obiect nou cu trei chei si arunca `origini` (ce
# validator minte la ce origine), `sonde` si `semnale` (ETag-urile). Garda de
# atunci numara documentele — erau toate acolo — deci n-a prins nimic.
_BUN = {"rulari": [], "banci": {"x": "L1"},
        "origini": {"r.ro": {"lm_nesigur": True}},
        "sonde": [{"moment": "L1"}],
        "documente": {_URL: {"amprenta": "aaa", "banca": "x",
                             "cale": "p/f.pdf", "semnale": {"etag": '"a"'}}}}
_STARE = {_URL: {"stare": "NESCHIMBAT", "banca": "x", "origine": "r.ro",
                 "cale": "p/f.pdf", "amprenta": "aaa", "octeti": 1}}
_DUPA = actualizeaza(_BUN, _STARE, {"x": "L2"}, "v1")

T(_DUPA.get("origini") == _BUN["origini"], "urme: actualizeaza pastreaza origini")
T(_DUPA.get("sonde") == _BUN["sonde"], "urme: actualizeaza pastreaza sonde")
T(_DUPA["documente"][_URL].get("semnale") == {"etag": '"a"'},
  "urme: actualizeaza pastreaza semnalele HTTP")
T(_DUPA["documente"][_URL]["verificari"] == 1,
  "urme: actualizeaza numara verificarile")



# Comparatia de valori are voie doar cu parserul neatins. Intre 17 si 18
# septembrie comisioane_pdf a scazut 430 -> 427 din cauza MEA, nu a bancilor.
T(not comparatie_de_valori_permisa({"rulari": []}, "v1")[0],
  "urme: fara rulare anterioara, nu se compara")
T(comparatie_de_valori_permisa({"rulari": [{"versiune_parser": "v1"}]}, "v1")[0],
  "urme: parser neschimbat, se compara")
T(not comparatie_de_valori_permisa({"rulari": [{"versiune_parser": "v1"}]}, "v2")[0],
  "urme: parser schimbat, NU se compara")

# Amprenta parserului trebuie sa se miste cand se miste un modul de extragere.
T(len(amprenta_parser()) == 16 and amprenta_parser() == amprenta_parser(),
  "urme: amprenta parserului e stabila")


# --------------------------------------------------- semnalele HTTP
# Semnalul serverului decide DACA merita sa ne uitam; octeții decid DACA s-a
# schimbat. "DE_CITIT" nu e o stare finala, e instrucțiunea de a descarca.
# "NESCHIMBAT_PROBABIL" e finala, dar NU e o confirmare.
_RAND = {"octeti": 335669, "amprenta": "a" * 64,
         "ultima_vedere": "2026-09-16T12:00:00+00:00"}
_VECHI_IUN = "Thu, 26 Jun 2025 12:10:52 GMT"
_NOU_SEPT = "Wed, 17 Sep 2026 08:00:00 GMT"


def _sem(antete, rand=None):
    return clasifica_semnal(rand or _RAND, antete)[0]


T(_sem({"Content-Length": "335669", "Last-Modified": _VECHI_IUN})
  == "NESCHIMBAT_PROBABIL", "semnal: aceeasi lungime, nu mai nou")
T(_sem({"Content-Length": "999999"}) == "DE_CITIT",
  "semnal: alta lungime -> se descarca")
T(_sem({"Content-Length": "335669", "Last-Modified": _NOU_SEPT}) == "DE_CITIT",
  "semnal: aceeasi lungime dar mai nou -> se descarca")
T(_sem({"Last-Modified": _NOU_SEPT}) == "DE_CITIT",
  "semnal: doar Last-Modified, mai nou")
T(_sem({"Last-Modified": _VECHI_IUN}) == "NESCHIMBAT_PROBABIL",
  "semnal: doar Last-Modified, nu mai nou")
T(_sem({}) == "FARA_SEMNAL", "semnal: server mut NU e neschimbat")
# de la rularea a doua, ETag-ul stocat compara direct
_CU_ETAG = dict(_RAND, semnale={"etag": '"x"'})
T(_sem({"ETag": '"x"'}, _CU_ETAG) == "NESCHIMBAT_PROBABIL", "semnal: ETag identic")
T(_sem({"ETag": '"y"'}, _CU_ETAG) == "DE_CITIT", "semnal: ETag diferit")
# antetele vin cu majuscule diferite de la servere diferite
T(_sem({"content-length": "999999"}) == "DE_CITIT",
  "semnal: antet cu litere mici")
# Content-Length comprimat NU se compara cu marimea de pe disc: Raiffeisen
# raspunde 91.339 cu gzip pentru un fisier de 105.454. Asta a facut 57 de
# descarcari inutile din 58.
T(_sem({"Content-Length": "91339", "Content-Encoding": "gzip"}) == "FARA_SEMNAL",
  "semnal: lungime comprimata se ignora")
T(_sem({"Content-Length": "0"}) == "FARA_SEMNAL",
  "semnal: lungime 0 e absenta, nu diferența")
# Last-Modified se compara cu ce a spus serverul ultima data, nu cu ceasul
# nostru: 20 de documente raspund "azi" si ar cere descarcare pe vecie.
_CU_LM = dict(_RAND, semnale={"last_modified": _NOU_SEPT})
T(_sem({"Last-Modified": _NOU_SEPT}, _CU_LM) == "NESCHIMBAT_PROBABIL",
  "semnal: Last-Modified neschimbat fața de rularea trecuta")
T(_sem({"Last-Modified": "Fri, 18 Sep 2026 08:00:00 GMT"}, _CU_LM) == "DE_CITIT",
  "semnal: Last-Modified schimbat fața de rularea trecuta")
# Un Last-Modified pus la ora cererii nu e o informație despre document.
# Raiffeisen raspunde asa pentru 11 documente; comparat cu valoarea precedenta
# difera mereu, deci ar cere descarcare la fiecare rulare pe vecie.
_ACUM = datetime(2026, 9, 18, 14, 0, 0, tzinfo=timezone.utc)
_STAMPILA = "Fri, 18 Sep 2026 10:03:52 GMT"
T(clasifica_semnal({"octeti": 105454, "semnale": {"last_modified": _STAMPILA}},
                   {"Last-Modified": _STAMPILA, "Content-Length": "105454"},
                   acum_dt=_ACUM)[0] == "NESCHIMBAT_PROBABIL",
  "semnal: Last-Modified la ora cererii se arunca")
# ...dar o data reala din trecut rămâne folosita
T(clasifica_semnal({"octeti": 105454},
                   {"Last-Modified": "Tue, 18 Aug 2026 09:33:14 GMT",
                    "Content-Length": "999"}, acum_dt=_ACUM)[0] == "DE_CITIT",
  "semnal: data reala din trecut rămâne valida")
# ETag-ul unei origini prinse mințind nu se mai foloseste acolo
T(not etag_de_incredere({"origini": {"www.bcr.ro": {"etag_nesigur": True}}},
                        "www.bcr.ro"), "semnal: ETag nesigur pe origine")
T(etag_de_incredere({}, "www.bcr.ro"), "semnal: ETag de incredere implicit")
T(clasifica_semnal({"octeti": 105454, "semnale": {"etag": '"x"'}},
                   {"ETag": '"y"', "Content-Length": "105454"},
                   acum_dt=_ACUM, foloseste_etag=False)[0]
  == "NESCHIMBAT_PROBABIL", "semnal: cu ETag ignorat se cade pe lungime")
# Aceeasi regula, generalizata: ORICE antet care arata ca un validator poate sa
# nu fie unul, iar singurul mod de a afla e sa-l prinzi. Raiffeisen si ProCredit
# raspund cu ora umplerii cache-ului, nu cu data documentului — masurat, valoarea
# era cu 640 de secunde in urma, deci pragul de stampila o rateaza. Prinse pe
# octeți identici, originile lor nu mai folosesc Last-Modified.
_CACHE = {"octeti": 536320,
          "semnale": {"last_modified": "Fri, 18 Sep 2026 10:17:39 GMT",
                      "content_length": 536320}}
_ANTETE = {"Last-Modified": "Fri, 18 Sep 2026 10:37:37 GMT",
           "Content-Length": "536320"}
T(clasifica_semnal(_CACHE, _ANTETE, acum_dt=_ACUM)[0] == "DE_CITIT",
  "semnal: Last-Modified de cache cere descarcare cat e crezut")
T(clasifica_semnal(_CACHE, _ANTETE, acum_dt=_ACUM,
                   foloseste_lm=False)[0] == "NESCHIMBAT_PROBABIL",
  "semnal: cu Last-Modified nesigur se cade pe lungime")
T(not validator_de_incredere({"origini": {"r.ro": {"lm_nesigur": True}}}, "r.ro", "lm"),
  "semnal: lm nesigur pe origine")
T(validator_de_incredere({"origini": {"r.ro": {"lm_nesigur": True}}}, "r.ro", "etag"),
  "semnal: un validator nesigur nu-l discredita pe celalalt")
T(validator_de_incredere({}, "r.ro", "lm"), "semnal: implicit de incredere")





# --- data de intrare in vigoare, citita din textul documentului -------------
# Cazurile vin din documentele reale de pe disc. Cele "NU produce" sunt miezul:
# o data gresita e mai rea decat niciuna, fiindca arata la fel cu una buna.
from datetime import date as _D


def DD(text, asteptat, eticheta, precizie=None):
    d, p, _a, dov = data_din_text(text)
    ok = d == asteptat and (precizie is None or p == precizie)
    T(ok, f"data: {eticheta}" + ("" if ok else f"  [{d} {p}]"))
    if asteptat is not None and d == asteptat:
        T(bool(dov), f"data: {eticheta} vine cu dovada")


DD("GHID DE TARIFE SI COMISIOANE PERSOANE FIZICE "
   "in vigoare incepand cu data de 21.09.2026", _D(2026, 9, 21),
   "BRD, ghidul de tarife", "zi")
DD("Vă informăm că, la data de 20.09.2026, următoarele tipuri de dobândă",
   _D(2026, 9, 20), "BCR, dobanzi indicative", "zi")
DD("Valabil începând cu 01 octombrie 2026", _D(2026, 10, 1),
   "luna scrisa in litere", "zi")
DD("Lista de tarife, versiune mai 2024", _D(2024, 5, 1),
   "doar luna si an", "luna")
DD("Tarife aplicabile din 2026-03-15", _D(2026, 3, 15), "an-luna-zi")

# diacriticele lipsesc neregulat din PDF-uri: acelasi text trebuie citit la fel
DD("In vigoare incepand cu data de 01.09.2026", _D(2026, 9, 1),
   "fara diacritice")
DD("În vigoare începând cu data de 01.09.2026", _D(2026, 9, 1),
   "cu diacritice")
# "s" apare in PDF-uri si cu sedila (U+015F) si cu virgula dedesubt (U+0219)
DD("Valabil ş i aplicabil de la data de 05.05.2026", _D(2026, 5, 5),
   "sedila")
DD("Valabil ș i aplicabil de la data de 05.05.2026", _D(2026, 5, 5),
   "virgula dedesubt")

# NU produce
DD("In cazul clientilor care au optat inainte de 07.01.2013 se percepe 0,30 EUR",
   None, "nota de subsol istorica NU e data documentului")
DD("Contul IBAN RO49 AAAA 1B31 0075 9384 0000", None,
   "sir de cifre fara ancora")
DD("Document fara nicio data", None, "text fara data")
DD("Conform Legii 190/2018 privind protectia datelor", None,
   "numar de lege NU e data")
DD("In vigoare incepand cu data de 21.09.1999", None,
   "an sub pragul de plauzibilitate")

# ordinea ancorelor E semantica: "in vigoare" bate "actualizat"
_d, _p, _ancora, _dov = data_din_text(
    "Actualizat la 01.03.2026. In vigoare incepand cu data de 15.04.2026.")
T(_d == _D(2026, 4, 15) and _ancora == "vigoare",
  "data: 'in vigoare' bate 'actualizat' indiferent de ordinea in text")

# starea fata de azi
T(stare_fata_de(_D(2026, 9, 1), azi=_D(2026, 9, 21)) == "IN_VIGOARE",
  "data: document din trecut e in vigoare")
T(stare_fata_de(_D(2026, 11, 1), azi=_D(2026, 9, 21)) == "VIITOR",
  "data: document care intra in vigoare mai tarziu NU e pretul de azi")
T(stare_fata_de(None) == "DATA_NECUNOSCUTA",
  "data: fara data NU inseamna 'probabil curent'")




# --- data din numele fișierului --------------------------------------------
# A doua sursa, si la BCR SINGURA: tarifele lor nu contin nicio data in text,
# verificat pe toate cele 9 pagini. Fara asta, BCR ramane intreg nedatat, iar
# BCR e a doua banca dupa numarul de comisioane pe care ni le da.

def DN(nume, asteptat, eticheta, precizie=None):
    d, p, _dov = data_din_nume(nume)
    ok = (d.isoformat() if d else None) == asteptat and (precizie is None
                                                         or p == precizie)
    T(ok, f"nume: {eticheta}" + ("" if ok else f"  [{d} {p}]"))


DN("4215705e_BCR_Tarife-si-Comisioane-PDAI_1-iulie-2026.pdf", "2026-07-01",
   "luna in litere, separata cu liniute", "zi")
# doua treceri, si ordinea conteaza: normalizarea separatorilor ar rupe
# "19.06.2024" in "19 06 2024", deci numele se incearca INTAI asa cum e
DN("844abe37_Document-de-informare-cont-EUR_19.06.2024.pdf", "2024-06-19",
   "data cu puncte, nerupta de normalizare")
DN("lista-tarife-19-06-2024.pdf", "2024-06-19", "aceeasi data cu liniute")
DN("lista_tarife_20260901.pdf", "2026-09-01", "cifre lipite")
DN("Lista_Tarife_PJ_mai_2024.pdf", "2024-05-01", "doar luna", "luna")

# NU produce
DN("Document-de-informare-Pachet-George_2025.pdf", None,
   "un an singur NU distinge doua versiuni din acelasi an")
DN("Tarif_standard_de_comisioane_PF.pdf", None, "nume fara data")
# "%20" din adresa devine "20" in numele descarcat si se lipeste de cifre — a
# treia oara in proiect cand asta strica o citire de data
DN("An_203_Doc_20de_20info_20cu_20priv_20la_20comisioane_eur.pdf", None,
   "spatiile codate ca 20 NU sunt o data")


# --- familii de documente: doua fișiere = doua versiuni ale aceluiasi act ----
# Regula taie 1.304 valori din 7.201, deci trebuie sa greseasca in directia
# sigura: mai bine doua familii separate (nu taiem nimic) decat doua documente
# diferite puse in aceeasi familie (taiem preturi valide).

def F(a, b, acelasi, eticheta):
    fa, fb = familie_document(a), familie_document(b)
    T((fa == fb) == acelasi,
      f"familie: {eticheta}" + ("" if (fa == fb) == acelasi else f"  [{fa} | {fb}]"))


# aceeasi familie — versiuni succesive
F("bcr/BCR_Tarife-si-Comisioane-PJ_RO_1-martie-2026.pdf",
  "bcr/BCR_Tarife-si-Comisioane-PJ_RO_1-august-2026.pdf", True,
  "BCR, acelasi tarif in doua luni")
# bug real: '_' e caracter de cuvant, deci '\\b' nu exista intre '_' si 'iulie'.
# Prima versiune a functiei n-a grupat NICIO familie BCR si a raportat linistit
# "0 documente depasite" — un rezultat fals care arata exact ca unul bun.
F("bcr/4f609199_BCR_Tarife_si_Comisioane_PJ_RO_1_martie_2026.pdf",
  "bcr/aca9ef45_BCR_Tarife_si_Comisioane_PJ_RO_1_august_2026.pdf", True,
  "aceeasi, cu underscore in loc de liniuta")
F("brd/158b3251_Ghid_tarife_comisioane.pdf",
  "brd/8bfeb70d_Ghid_tarife_comisioane.pdf", True,
  "acelasi document sub doua prefixe de unicitate")
F("brci/Lista_Tarife_PJ_mai_2024.pdf",
  "brci/Lista_Tarife_PJ_vers_oct_2024.pdf", True,
  "aceeasi lista, mai fata de octombrie")

# familii DIFERITE — a le uni ar sterge preturi valide
F("bcr/BCR_Tarife-si-Comisioane-PJ_RO_1-august-2026.pdf",
  "bcr/BCR_Tarife-si-Comisioane-PDAI_1-august-2026.pdf", False,
  "persoane juridice fata de activitati independente")
F("libra/Tarife_si_Comisioane_PF.pdf",
  "libra/Tarife_si_Comisioane_PJ.pdf", False,
  "persoane fizice fata de juridice")
F("bcr/Tarife-si-Comisioane-PJ_1-august-2026.pdf",
  "brd/Tarife-si-Comisioane-PJ_1-august-2026.pdf", False,
  "acelasi nume la banci diferite NU e aceeasi familie")
F("libra/comisioane_card_Avanpost_Gold.pdf",
  "libra/comisioane_card_Avanpost_Gold_Junior.pdf", False,
  "Gold fata de Gold Junior sunt produse diferite")



# --- valori care nu pot fi deosebite intre ele ------------------------------
# Regula marcheaza 887 de valori din 7.201. Cazurile "NU e ambiguu" sunt la fel
# de importante: un semn pus gresit pe o cifra corecta erodeaza increderea in
# toate celelalte semne.

def _v(banca="brd", pdf="d.pdf", serviciu="X", valoare=1.0, **rest):
    baza = {"banca": banca, "sursa_pdf": pdf, "serviciu": serviciu,
            "tip": "comision_suma", "moneda": "LEI", "frecventa": None,
            "conditie": None, "coloana": None, "detaliu": None, "rol": None,
            "valoare": valoare}
    baza.update(rest)
    return baza


# cazul BRD: trei praguri in tabel, doar cel din mijloc s-a citit. Glifele
# ">=" si "<=" nu erau incorporate in font, deci randurile de sus si de jos
# si-au pierdut banda impreuna cu numarul de langa ea.
_brd = [_v(valoare=4.0), _v(valoare=8.0, conditie="(500-50.000)"),
        _v(valoare=11.0)]
_n, _g = marcheaza(_brd)
T(_n == 3 and _g == 1, f"ambiguu: BRD, trei praguri din care unul citit [{_n} {_g}]")
T(_brd[0]["motiv_ambiguu"] == "prag de suma pierdut",
  f"ambiguu: motivul e pragul  [{_brd[0]['motiv_ambiguu']}]")

# cazul Eximbank: acelasi serviciu, preturi diferite pe tipuri de card, iar
# antetul cu tipul cardului nu s-a citit. Documentul ARE coloane in alta parte,
# si de acolo se stie ca lipseste un antet, nu un prag.
_exim = [_v(banca="eximbank", serviciu="Schimbare PIN la ATM", valoare=0.0),
         _v(banca="eximbank", serviciu="Schimbare PIN la ATM", valoare=2.5),
         _v(banca="eximbank", serviciu="Altceva", valoare=9.0, coloana="Gold")]
_n, _g = marcheaza(_exim)
T(_n == 2 and _exim[0]["motiv_ambiguu"] == "antet de coloana pierdut",
  f"ambiguu: Eximbank, antet de coloana  [{_n} {_exim[0]['motiv_ambiguu']}]")

# --- NU e ambiguu ---
_la_fel = [_v(valoare=5.0), _v(valoare=5.0), _v(valoare=5.0)]
marcheaza(_la_fel)
T(not any(x["ambiguu"] for x in _la_fel),
  "ambiguu: aceeasi valoare repetata NU e o ambiguitate")

# doua monede pentru acelasi serviciu sunt doua preturi, nu o nelamurire
_monede = [_v(valoare=10.0, moneda="LEI"), _v(valoare=2.0, moneda="EUR")]
marcheaza(_monede)
T(not any(x["ambiguu"] for x in _monede),
  "ambiguu: monede diferite NU fac o ambiguitate")

_cu_praguri = [_v(valoare=4.0, conditie="<500"), _v(valoare=8.0, conditie="500-50.000"),
               _v(valoare=11.0, conditie=">50.000")]
marcheaza(_cu_praguri)
T(not any(x["ambiguu"] for x in _cu_praguri),
  "ambiguu: fiecare valoare cu pragul ei e in regula")

_alt_document = [_v(pdf="a.pdf", valoare=4.0), _v(pdf="b.pdf", valoare=8.0)]
marcheaza(_alt_document)
T(not any(x["ambiguu"] for x in _alt_document),
  "ambiguu: doua documente diferite NU se compara intre ele")

_alta_banca = [_v(banca="brd", valoare=4.0), _v(banca="bcr", valoare=8.0)]
marcheaza(_alta_banca)
T(not any(x["ambiguu"] for x in _alta_banca),
  "ambiguu: doua banci diferite NU se compara intre ele")

_fara_serviciu = [_v(serviciu=None, valoare=4.0), _v(serviciu=None, valoare=8.0)]
marcheaza(_fara_serviciu)
T(not any(x["ambiguu"] for x in _fara_serviciu),
  "ambiguu: fara nume de serviciu nu se poate spune ca e acelasi lucru")



# --- comparatia pe valori intre doua versiuni ale aceluiasi document --------
# Regula care conteaza: din 13 diferente pe octeti in ghidul BRD, UNA era o
# schimbare de pret. Un raport care nu separa cele doua e adevarat si inutil.

def _r(serviciu="X", tip="comision_suma", valoare=1.0, moneda="LEI", **rest):
    baza = {"serviciu": serviciu, "tip": tip, "valoare": valoare,
            "moneda": moneda, "frecventa": None, "coloana": None,
            "conditie": None}
    baza.update(rest)
    return baza


# pretul s-a mutat pe un rand care se potriveste exact
_d = compara_versiuni([_r(valoare=15.0)], [_r(valoare=20.0)])
T(len(_d["pret"]) == 1 and _d["pret"][0]["vechi"] == [15.0]
  and _d["pret"][0]["nou"] == [20.0], "diferente: pret mutat 15 -> 20")

# acelasi pret, nicio schimbare
_d = compara_versiuni([_r(valoare=15.0)], [_r(valoare=15.0)])
T(rezumat(_d) == {"pret": 0, "banda": 0, "reformatat": 0, "aparut": 0,
                  "disparut": 0}, f"diferente: identic nu produce nimic  [{rezumat(_d)}]")

# Randarea noua a ghidului BRD a mutat despartirile in cuvinte, fara sa schimbe
# un caracter de continut. Spatiul alb se scoate din cheie, deci astea doua sunt
# acelasi rand si nu produc NIMIC — nici macar "reformatat".
_d = compara_versiuni([_r(serviciu="Oriceoperatiunediferitadecele", valoare=7.0)],
                      [_r(serviciu="Oriceoperatiune diferita decele", valoare=7.0)])
T(rezumat(_d)["pret"] == 0 and rezumat(_d)["aparut"] == 0,
  f"diferente: despartirile in cuvinte nu conteaza  [{rezumat(_d)}]")

# Dar reformatarea muta si PUNCTUL DE TAIERE al etichetei: acelasi rand ajunge
# sa poarte alt fragment din nota de subsol de deasupra. Atunci numele chiar
# difera, si singurul lucru care le mai leaga sunt valorile identice.
_d = compara_versiuni(
    [_r(serviciu="1procenteleseaplicalavaloareatranzactiei", valoare=0.51),
     _r(serviciu="1procenteleseaplicalavaloareatranzactiei", valoare=6.0)],
    [_r(serviciu="2comisiondisputeropaypentrufiecarecaz", valoare=0.51),
     _r(serviciu="2comisiondisputeropaypentrufiecarecaz", valoare=6.0)])
T(len(_d["reformatat"]) == 1 and not _d["pret"],
  f"diferente: eticheta taiata in alt loc = reformatare  [{rezumat(_d)}]")

# diacriticele si majusculele nu fac o schimbare
_d = compara_versiuni([_r(serviciu="Retrageri de numerar")],
             [_r(serviciu="RETRAGERI DE NUMERAR")])
T(rezumat(_d)["pret"] == 0 and rezumat(_d)["aparut"] == 0,
  "diferente: majuscule si spatii nu fac o schimbare")

# cazul Electrica: randul vechi avea DOUA inregistrari pentru acelasi serviciu
# ("gratuit" si "1,5 lei"), iar cel nou are una. Excepția a fost eliminata.
# Trebuie sa se vada ca rand disparut, cu valoarea lui — nu doar numarat.
_vechi = [_r(serviciu="Simplis Debit", tip="gratuit", valoare=0.0, moneda=None),
          _r(serviciu="Simplis Debit", valoare=1.5)]
_nou = [_r(serviciu="Simplis Debit", tip="gratuit", valoare=0.0, moneda=None)]
_d = compara_versiuni(_vechi, _nou)
T(len(_d["disparut"]) == 1 and _d["disparut"][0]["valori"] == [1.5],
  f"diferente: Electrica, randul de 1,5 lei disparut  [{rezumat(_d)}]")

# un prag care apare abia acum (glifele ">=" lipseau din fontul vechi) nu e un
# rand nou, e acelasi rand cu banda citita
_d = compara_versiuni([_r(valoare=4.0, conditie=None)],
             [_r(valoare=4.0, conditie="<=500 lei")])
T(len(_d["banda"]) == 1 and not _d["aparut"] and not _d["disparut"],
  f"diferente: prag aparut = banda, nu rand nou  [{rezumat(_d)}]")

# doua servicii diferite nu se confunda intre ele
_d = compara_versiuni([_r(serviciu="A", valoare=1.0)], [_r(serviciu="B", valoare=2.0)])
T(len(_d["aparut"]) == 1 and len(_d["disparut"]) == 1 and not _d["pret"],
  f"diferente: servicii diferite raman separate  [{rezumat(_d)}]")

# aceeasi valoare la monede diferite nu e reformatare
_d = compara_versiuni([_r(valoare=10.0, moneda="LEI")], [_r(valoare=10.0, moneda="EUR")])
T(len(_d["reformatat"]) == 0,
  f"diferente: alta moneda NU e reformatare  [{rezumat(_d)}]")



# --- procentele cu multe zecimale ------------------------------------------
# Regexul vechi accepta cel mult trei zecimale si nu avea nicio ancora la
# stanga. Pe un numar mai lung renunta la inceputul lui si prindea COADA:
#
#     "Pachet extins: 0,0125%"   ->  125 %     (BCR, valoare reala in date)
#     "CME Term SOFR 6M 3,93606%"  ->  606 %
#
# Valori false care arata perfect normal intr-un tabel de comisioane. Gasite
# printr-o cautare de numere cu 4+ zecimale urmate de %, nu prin raportare.

def PC(text, asteptat, eticheta):
    got = RE_PROCENT.findall(text)
    T(got == asteptat, f"procent: {eticheta}" + ("" if got == asteptat else f"  [{got}]"))


PC("Pachet extins: 0,0125%", ["0,0125"], "patru zecimale, nu coada lor")
PC("CME Term SOFR 6M 3,93606%", ["3,93606"], "cinci zecimale")
PC("2,5%", ["2,5"], "doua zecimale")
PC("de 15%", ["15"], "intreg")
PC("0,5% + 2,5 Lei", ["0,5"], "procent urmat de suma")
PC("intre 0,1% si 0,25%", ["0,1", "0,25"], "doua procente pe aceeasi linie")
PC("IRCC 5,56%", ["5,56"], "indice")
PC("TVA 19 %", ["19"], "spatiu inaintea semnului")
# Efect secundar dorit: un numar de patru cifre nu mai produce o coada de trei.
# 1500% nu e un comision, iar 500% nici atat.
PC("comision 1500%", [], "patru cifre intregi NU produc coada")


# --- listele de tarife: titlul, subpunctele, coada celulei de pret -----------
# Toate din crawl-ul din 23 sept. Nexent, Vista si lista de preturi ProCredit nu
# erau citite deloc (numele fisierului nu spunea "tarif"), iar subpunctele de
# tipul "- de la ATM-uri BCR" ramaneau fara serviciu.
from crawler.parser_pdf import analizeaza_linie  # noqa: E402
from crawler.parser_tarife import (RE_TITLU_TARIFE, _adauga_eticheta,  # noqa: E402
                                   _celula_eticheta, _e_doar_banda, _e_titlu,
                                   _e_varianta, _eticheta_pentru, _titlu_din_tabel,
                                   categorie)
from crawler.vocabular import canonic  # noqa: E402

for titlu in ["Lista de taxe, comisioane si dobanzi aferenta cardului",   # Nexent
              "LISTĂ PREȚURI PERSOANE FIZICE",                             # ProCredit
              "Lista de Tarife, Termene și Condiții pentru persoane fizice",  # Vista
              "DOBANZI, COMISIOANE, TAXE SI ALTE COSTURI Avanpost Gold Credit",  # Libra
              "Lista taxelor și comisioanelor Salt Business",
              "Tarife și comisioane standard"]:                            # Garanti
    T(RE_TITLU_TARIFE.search(titlu), f"titlu de tarife: {titlu[:40]}")
for rand in ["Puteți consulta în orice moment Tarifele, Termenele și Condițiile",
             "conform Listei de tarife si comisioane in vigoare",
             "Regulamentul oficial al Campaniei"]:
    T(not RE_TITLU_TARIFE.search(rand), f"NU e titlu: {rand[:40]}")

# "tranzacție" sub "min. 1 LEI/" e coada celulei de pret, nu un nume
FARA = ([], None, None, None)
T(_celula_eticheta(["", "", "tranzacție", "tranzacție"], [FARA] * 4,
                   frozenset({2, 3})) is None, "coada celulei de pret NU e eticheta")
T(_celula_eticheta(["", "demagnetizat", "", ""], [FARA] * 4,
                   frozenset({2, 3})) == 1, "continuarea numelui ramane eticheta")

# blocuri: (sus, jos, text, e_parinte)
BCR = [(504, 512, "Eliberare de numerar în România", True),
       (518, 525, "- de la ghișeele BCR", False)]
T(_eticheta_pentru(515, 522, BCR) == "Eliberare de numerar în România - de la ghișeele BCR",
  "subpunctul primeste numele de deasupra")
RAIF = [(261, 270, "Comision pentru retrageri de numerar", True),
        (276, 285, "La ATM-urile băncilor acceptatoare din străinătate", False)]
T(_eticheta_pentru(276, 285, RAIF).startswith("Comision pentru retrageri de numerar La"),
  "subpunct cu prepozitie")
T(_eticheta_pentru(276, 285, [(100, 110, "pentru care retragerea a fost programată)", True),
                              (276, 285, "În EUR", False)]) == "În EUR",
  "coada unei fraze NU devine parinte")
T(_eticheta_pentru(515, 522, [(504, 512, "Taxa blocare card", False),
                              (515, 522, "Taxa recuperare card", False)]) == "Taxa recuperare card",
  "eticheta intreaga ramane neatinsa")


def CN(serviciu, asteptat, eticheta):
    got = canonic({"serviciu": serviciu})[0]
    T(got == asteptat, f"concept: {eticheta}" + ("" if got == asteptat else f"  [{got}]"))


CN("Mentenanţă anuală card", "administrare_card", "diacritice cu sedila")
CN("Plăţi intrabancare în lei și valută", "transfer_credit", "sedila in plural")
CN("Contestare nejustificată a unei tranzacţii", "refuz_plata", "contestare, nu doar contestație")
CN("Comision pentru operatiuni la comerciantii din Romania", "tranzactie_card",
   "operatiuni la comercianti")
CN("Comision pentru operatiuni (la POS/pe internet) la comerciantii de tip jocuri de noroc",
   None, "gamblingul NU intra la plata cu cardul")
CN("Emitere card - reînnoire", "reemitere_card", "reinnoirea dupa card")
CN("Inchidere pachet", "inchidere_cont", "pachetul de cont")
CN("Pret pachet/luna cu indeplinirea conditiei de pachet", "administrare_cont",
   "pretul pachetului (BRD)")
CN("Transferuri intrabancare", "transfer_credit", "transferuri (Vista)")
CN("Taxa SWIFT", "speze_swift", "taxa swift")

# --- a doua runda: 23-24 sept, masurat pe aceleasi 68 de documente ------------
# sumele in USD/GBP/CHF se citeau ca text, iar coada lor devenea nume de serviciu
T([(v[1], v[2]) for v in analizeaza_linie("30 USD/card")[0]] == [(30.0, "USD")],
  "suma in USD")
T([v[2] for v in analizeaza_linie("3 USD 2,5 GBP 3 CHF")[0]] == ["USD", "GBP", "CHF"],
  "trei valute pe un rand")

# numele inceput pe un rand fara pret si continuat pe randul cu pret (BRD)
BL = [(71, 79, "Pret pachet /luna cu", True)]
_adauga_eticheta(BL, 83, 90, "indeplinirea conditie", True)
T(len(BL) == 1 and BL[0][2] == "Pret pachet /luna cu indeplinirea conditie" and not BL[0][3],
  "randul cu pret continua numele de deasupra")
BL = [(35, 42, "Utilizare ATM/POS alte banci – retragere numerar:", True)]
_adauga_eticheta(BL, 45, 52, "- National", True)
T(len(BL) == 2, "dupa ':' incepe lista, nu continuarea")

# canalul fizic la inceput e varianta; banda cu "inclusiv" e tot banda
T(_eticheta_pentru(56, 62, [(43, 50, "Retragere de numerar ATM/POS", True),
                            (56, 62, "ATM BRD", False)]) == "Retragere de numerar ATM/POS ATM BRD",
  "ATM BRD primeste serviciul de deasupra")
T(_eticheta_pentru(56, 62, [(40, 50, "Internet Banking", True),
                            (56, 62, "Internet Banking (administrare)", False)])
  == "Internet Banking (administrare)", "Internet Banking ramane serviciu, nu varianta")
T(_e_doar_banda("- 100 LEI, inclusiv") and _e_doar_banda("Peste 50.000 LEI, inclusiv"),
  "banda cu inclusiv/exclusiv")
T(not _e_doar_banda("Plăți interbancare ≤ 50.000 LEI"), "nume cu banda NU e doar banda")

# subtitlul se aplica variantelor, nu numelor intregi
T(_e_varianta("Emitere iniţială") and _e_varianta("Primit") and _e_varianta("- 50.000 LEI"),
  "variante, si cu sedila")
T(not _e_varianta("Investigatie ordin de plata"), "nume intreg inchide subtitlul")

# titluri: index in coloana lui (BCR), titlu langa antetul de moneda (Libra)
T(_titlu_din_tabel(["11.", "Carduri de Debit în Lei"], [1]) == ("11.", "Carduri de Debit în Lei"),
  "index in coloana lui")
T(_titlu_din_tabel(["2.4.", "(de la ghișee/ ATM-uri BCR"], [1]) is None,
  "continuarea unui nume NU e titlu")
T(_e_titlu(["", "ACREDITIVE DE IMPORT", "", "", "EUR", ""], [1, 4],
           [0, 50, 300, 350, 400, 450, 573], 573) == (None, "ACREDITIVE DE IMPORT"),
  "titlu pe randul antetului de moneda")

# limita spusa direct iese din comisioane doar cand celula e numai cifra
T(categorie(None, "limită maximă pe tranzacție", "500.000 LEI", "500.000 LEI") == "limita",
  "limita maxima (Garanti)")
T(categorie(None, "Limita zilnică de retragere numerar",
            "5% (minim 10 lei) din suma utilizată",
            "5% (minim 10 lei) din suma utilizată") == "comision",
  "formula de pret sub eticheta de limita ramane comision")


# --- a treia runda: 24 sept, aceleasi 68 de documente --------------------------
from crawler.parser_pdf import rol_de_conditie  # noqa: E402

# "dobânzii" nu contine "dobând": 13 marje ProCredit si 8 penalizari Nexent
T(categorie("Credite ProGreen", "Marja fixa a dobanzii", "2,10%") == "dobanda",
  "marja dobanzii (ProCredit)")
T(categorie(None, "Rata dobanzii penalizatoare pentru sumele restante", "30% / an")
  == "dobanda", "rata dobanzii (Nexent)")
# ...dar doar in capul etichetei: secțiunea Raiffeisen si produsul BRD nu mută
T(categorie("TARIFE ȘI DOBÂNZI PENTRU ACTIVITATEA DE EMITERE CARDURI",
            "Retragere numerar la ATM", "1,50% min 3 lei") == "comision",
  "dobanzi in secțiune NU face comisionul dobanda")
T(categorie(None, "Linie de credit cu rata dobanzii variabila, acordata in",
            "30 lei") == "comision", "rata dobanzii in coada etichetei NU e dobanda")

# titlul listei din pachet nu e "gratuit" (12 valori false)
T(analizeaza_linie("Produse și Servicii incluse")[0] == []
  and analizeaza_linie("PRODUSE SI SERVICII INCLUSE")[0] == [],
  "titlul listei incluse NU e valoare")
T(analizeaza_linie("Inclus în costul lunar al pachetului")[0] == [("gratuit", 0.0, None, None)],
  "inclus in pachet ramane gratuit")

# "în limita a 5.000 LEI/zi" e limita (ProCredit, 9 valori), dar doar cifra ei
T(rol_de_conditie("România în limita a 5.000 LEI/zi/maxim 10", "Retrageri", 5000.0)
  == "conditie", "in limita a N e conditie")
T(rol_de_conditie("10 LEI în limita a 5.000 LEI", "Retrageri", 10.0) is None,
  "pretul de langa limita ramane pret")

# "Utilizare ATM" fara "numerar" e retragere (BCR 8, Eximbank 2), dar nu la sold
T(canonic({"serviciu": "Utilizare ATM-uri Erste Group***",
           "sectiune": "Tranzacţii Internaţionale"})[0] == "retragere_numerar",
  "utilizare ATM-uri Erste Group")
CN("Utilizare ATM pentru interogare sold", "interogare_sold", "utilizare ATM la sold")
# plata sub "Standing order" e plata programata (BCR, 4 valori)
T(canonic({"serviciu": "Plăți - alte conturi 0 - 50.000 LEI, exclusiv",
           "sectiune": "Standing order (plată programată)"})[0] == "plata_programata",
  "plata sub standing order")
T(canonic({"serviciu": "Plăți - alte conturi 0 - 50.000 LEI, exclusiv",
           "sectiune": "Operațiuni prin ordin de plată"})[0] == "transfer_credit",
  "aceeasi plata sub ordin de plata ramane transfer")

# pachetul care isi enumera continutul nu e primul serviciu din lista (BCR, 16)
CN("George, conţinȃnd: - administrarea Cont curent în lei; - furnizarea unui Card de debit",
   "administrare_cont", "George continand e pretul pachetului, NU emitere_card")
CN("Pachetul Servicii de Bază pentru persoane nevulnerabile, conţinȃnd: - Furnizarea "
   "unui Card de debit", "administrare_cont", "pachetul continand e pretul pachetului")
# numele pachetului singur e pretul lui (20 de valori), componenta nu
CN("Pachet Gold", "administrare_cont", "pachet Raiffeisen")
CN("Pachet de servicii", "administrare_cont", "pachet ProCredit PAD")
CN("Pachet • comision de mentenanță card", "administrare_card", "componenta pachetului")


# --- a patra runda: 24 sept, aceleasi 68 de documente --------------------------
from crawler.parser_tarife import _celula_din_stanga  # noqa: E402

# nota de subsol lipita de moneda nu mai pierde suma (28 de celule)
T([(v[1], v[2]) for v in analizeaza_linie("2 RON2")[0]] == [(2.0, "LEI")],
  "suma cu nota lipita de moneda")
T(analizeaza_linie("10 EURIBOR")[0] == [], "EURIBOR nu e suma in euro")


def _w(text, x0, top):
    return {"text": text, "x0": x0, "x1": x0 + 6 * len(text), "top": top, "bottom": top + 8}


# BCR: serviciul in stanga, canalul in dreapta, in aceeasi celula cu bordura
GEOM = ([(95, 36, 239), (120, 36, 239), (132, 36, 239)],
        [_w("Depunere", 54, 99), _w("numerar", 110, 99), _w("Clientului", 54, 111),
         _w("MFM", 287, 124), _w("Alt", 54, 124)])
T(_celula_din_stanga(GEOM, 36, 239, 105, 113) == "Depunere numerar Clientului",
  "parintele din celula cu bordura din stanga")
T(_celula_din_stanga(GEOM, 36, 239, 124, 132) == "Alt", "celula vecina NU se amesteca")
T(_celula_din_stanga(([], GEOM[1]), 36, 239, 105, 113) is None,
  "fara borduri nu se ghiceste parintele")
T(_celula_din_stanga(([(95, 36, 239), (120, 36, 239)], [_w("Utilizare", 54, 99),
                                                        _w("5 lei", 120, 99)]),
                     36, 239, 105, 113) is None, "celula cu pret NU e parinte")

# "PLATI" e titlu (Vista), "SEPA" nu
T(_e_titlu(["PLATI"], [0], [0, 500], 500) == (None, "PLATI"), "PLATI e titlu scurt")
T(_e_titlu(["SEPA"], [0], [0, 500], 500) is None, "SEPA ramane respins")

# alertele SMS au un singur concept, indiferent de produsul atasat (22 de valori)
CN("Administrare Serviciu Alerte SMS Card", "alerta_sms", "alerta SMS pe card")
CN("Serviciul Info SMS – încasări și tranzacții cu cardul", "alerta_sms", "info SMS")
CN("Anulare serviciu SMS Alert", "modificare_anulare", "anularea ramane anulare")
# "cu încasare venit" e conditia creditului, nu o incasare (BRD, 8)
CN("Oferta standard / Oferta cu incasare venit in contul BRD", None,
   "incasare venit NU e incasare")
CN("Suma minimă de plata de rambursat lunar", None, "plata de rambursat NU e transfer")
CN("Retragere de de la ATM-uri si Ghiseele (POS-urile)", "retragere_numerar",
   "retragere de la ATM fara numerar")
CN("Extras suplimentar de cont", "extras_de_cont", "extras suplimentar")
CN("Extras ONRC", None, "extras ONRC NU e extras de cont")
CN("Administrare lunara Principal", "administrare_card", "cardul principal")
# banda de suma ia serviciul din secțiune; stramosul apropiat inaintea celui de sus
T(canonic({"serviciu": "≥ 50.000 LEI si urgente (orice suma)",
           "sectiune": "PLATI"})[0] == "transfer_credit", "banda ia sectiunea")
T(canonic({"serviciu": "Optiune “All Fees on You” 5",
           "sectiune": "ÎNCASĂRI ȘI PLĂȚI > PLĂȚI ÎN ALTE VALUTE"})[0] == "transfer_credit",
  "sectiunea cea mai adanca decide")
T(canonic({"serviciu": "Comision", "sectiune": "Transfer credit - plăți > Alte instrumente",
           "coloana": "Debitare directă (intrabancară/interbancară)"})[0]
  == "debitare_directa", "coloana matricei inaintea sectiunii")
# refuzul "la plata" (Nexent, BRD, Vista: ~45 de valori ieseau transfer_credit)
CN("Refuz la plata nejustificat", "refuz_plata", "refuz la plata")
CN("Taxa pentru initiere nejustificata de refuz la plata la POS", "refuz_plata",
   "initiere refuz la plata")
CN("Plăți POS România sau internațional", "tranzactie_card", "plati POS")
CN("Comision tranzacțional Prin intermediul EPOS", "tranzactie_card", "EPOS")
CN("Cost utilizare mijloc de plată la ATM-ul altor bănci din străinătate",
   "retragere_numerar", "mijloc de plata la ATM")
CN("Administarea contului curent", "administrare_cont", "greseala de tipar")
CN("Abonament lunar Garanti BBVA Online", "administrare_banking_distanta",
   "abonament internet banking")
CN("Cont curent în USD sau GBP", "administrare_cont", "contul singur")
CN("Cont curent sold creditor", None, "dobanda la sold NU e administrare")
# cerintele si plafoanele spuse in eticheta ies din preturi
T(rol_de_conditie("100 EUR", "Suma minimă pentru deschiderea contului de card", 100.0)
  == "conditie", "suma minima e conditie")
T(rol_de_conditie("9.000 RON", "Suma maxima zilnica de retragere numerar", 9000.0)
  == "conditie", "suma maxima e conditie")
T(rol_de_conditie("50.000 lei", "Valoarea maximă a limitei de credit", 50000.0)
  == "conditie", "plafonul cardului de credit e conditie")
# serviciul numit dar fara concept nu ia secțiunea (Vista: investigatii sub PLATI)
T(canonic({"serviciu": "Investigatii telefonice/ email/ SWIFT", "sectiune": "PLATI"})[0]
  is None, "investigatii NU iau conceptul sectiunii")
T(canonic({"serviciu": "Confirmare", "sectiune": "ACREDITIVE DE EXPORT"})[0]
  == "documentar", "confirmarea acreditivului ramane documentar")
CN("Comision de emitere plastic", "emitere_card", "emitere plastic")
T(canonic({"serviciu": "Fila", "sectiune": "Emitere carnet cec in lei"})[0] == "file_cec",
  "carnet cec fara de")
# banda din coloana din dreapta: celula din stanga inaintea parintelui de deasupra
BL = [(127, 135, "Depuneri de numerar", True, 36), (145, 153, "FX", False, 140),
      (151, 159, "Retrageri de numerar", True, 36)]
T(_eticheta_pentru(145, 153, BL, lambda xv: "Retrageri de numerar")
  == "Retrageri de numerar FX", "banda ia celula din stanga (Nexent)")
T(_eticheta_pentru(145, 153, BL) == "Depuneri de numerar FX",
  "fara geometrie ramane parintele de deasupra")
# "% p.a." e dobanda doar sub descoperit/restanta (Salt 6); caseta ramane comision
T(categorie(None, "neautorizat", "20 % p.a. (LEI) / 15% p.a. (valuta)") == "dobanda",
  "procent pe an la descoperit neautorizat")
T(categorie(None, "Caseta tip 2", "1,50%/ an, min. 56,5 lei/luna + TVA") == "comision",
  "procent pe an la caseta ramane comision")
# titlul cu index lung nu e proza; nota numerotata ramane nota
from crawler.parser_tarife import _e_titlu_cu_index  # noqa: E402
T(_e_titlu_cu_index("6. Taxe și comisioane aferente cardurilor de debit "
                    "principale/suplimentare în lei și valută"), "titlu cu index lung")
T(not _e_titlu_cu_index("1. Comisionul se percepe pentru fiecare operatiune efectuata."),
  "nota numerotata NU e titlu")


# --- valori false (reparatia «false»): ce nu e comision iese din comisioane -----
from crawler.parser_tarife import (RE_INDEX_LA_SFARSIT, RE_MARCAJ_NOTA,  # noqa: E402
                                   _bordura_intre, _e_nota, _fara_cifre, _nota_dupa)


def G(text, gratuit, eticheta):
    got = [v[0] for v in analizeaza_linie(text)[0]] == ["gratuit"]
    T(got == gratuit, f"inclus: {eticheta}")


# "inclus" e pret zero doar cand e predicatul celulei
G("Inclus în costul lunar al pachetului", True, "celula de pret ProCredit")
G("*Inclus în costul lunar al", True, "cu nota si rupt")
G("• Business debit card inclus în Pachet", True, "lista incluse gratuit BCR")
G("suplimentar LEI/ Valută, inclus în Pachet", True, "continuarea elementului din lista")
G("Taxe și comisioane pentru cardurile de debit incluse în pachetele de Cont Curent", False,
  "titlu / cuprins")
G("OPERATIUNI GRATUITE INCLUSE IN OFERTA (DIFERITE DE OFERTA STANDARD)", False, "titlu Vista")
G("*TVA inclus", False, "TVA inclus")
G("valabilitate, speze SWIFT incluse", False, "speze incluse in pret")
G("Operațiuni prin conturile curente incluse în pachet:", False, "antet cu doua puncte")
G("tranzacţiilor care depășesc numărul de plăţi incluse in pachet)**", False, "paranteza")
G("inclusa in", False, "forma noua NU produce valori noi")
G("Gratuit", True, "gratuit ramane gratuit")

# indicele de referinta e dobanda; pe eticheta nu decide (BRD "IRCC + 5,10 pp")
T(categorie("descoperit_de_cont", "Descoperitul de cont", "IRCC + 13,99%",
            "IRCC + 13,99%") == "dobanda", "IRCC plus marja in celula")
T(categorie("Credite", "Valoare", "5,56% IRCC", "5,56%", "IRCC") == "dobanda",
  "valoarea indicelui sub coloana IRCC")
T(categorie("Credite", "Comision de analiza dosar", "1% IRCC", "1%", "IRCC") == "comision",
  "comisionul din coloana IRCC ramane comision")
T(categorie("CREDITE", "ofertă standard IRCC + 5,10 pp clădire viitoare – evaluare",
            "600 lei", "600 lei") == "comision", "IRCC in eticheta NU decide")
# limitele fara cuvantul "limita" in eticheta
T(categorie("LIMITELE BANCII PENTRU TRANZACȚIILE EFECTUATE CU CARDUL DE DEBIT",
            "zilnică și per tranzacție", "6.000 LEI", "6.000 LEI") == "limita",
  "sectiunea de limite")
T(categorie(None, "Plăți Contactless (fără PIN) limită per tranzacție", "100 LEI",
            "100 LEI") == "limita", "limita per tranzactie")
T(categorie("Carduri", "Sumă per tranzacție top-up", "5.000 LEI /1.000 EUR",
            "5.000 LEI /1.000 EUR") == "limita", "top-up ProCredit")
T(categorie("Parametri", "Valoarea maximă a limitei de credit", "50.000 lei",
            "50.000 lei") == "limita", "valoarea maxima a limitei")
T(categorie(None, "Comision lunar de administrare credit", "Suma creditului: max. 15.000 lei",
            "Suma creditului: max. 15.000 lei") == "limita", "suma creditului")
# pretul spus fata de plafon e pret; plafonul insusi ramane limita
T(categorie("Comision de analiză dosar", "-comision de analiză pentru acordări ulterioare "
            "de plafon:", "25 LEI", "25 LEI") == "comision", "analiza pentru acordare de plafon")
T(categorie(None, "Retrageri de numerar - retrageri sub plafonul stabilit",
            "2,5% minim 30 LEI", "2,5% minim 30 LEI") == "comision", "retragere sub plafon")
T(categorie(None, "Comision suplimentar de eliberare numerar ce depaseste plafonul de",
            "20.000 lei, care nu a fost si se percepe aditional sumei",
            "20.000 lei, care nu a fost si se percepe aditional sumei") == "limita",
  "cifra plafonului din fraza ramane limita")
T(categorie(None, "Eliberare", "ridicarea sumelor ce depasesc plafonul de 20.000 lei",
            "ridicarea sumelor ce depasesc plafonul de 20.000 lei") == "limita",
  "plafonul spus in celula")
# taxa de stat din antetul coloanei (AEGRM), nu din numele serviciului
T(categorie(None, "AVIZ DE GARANŢIE INIŢIAL", "30 lei", "30 lei",
            "Taxa către bugetul de stat (Ministerul Justiţiei)") == "taxa_stat", "taxa de stat")
T(categorie(None, "AVIZ DE GARANŢIE INIŢIAL", "50 lei + TVA", "50 lei + TVA",
            "Tarif BCR pentru efectuare operatiuni la AEGRM") == "comision", "tariful bancii")
T(categorie(None, "Plata impozite si taxe catre bugetul de stat", "2 lei", "2 lei")
  == "comision", "serviciul de plata catre buget ramane comision")
# conditii, nu preturi
T(rol_de_conditie("40.000 EUR", "Conditie pachet", 40000.0) == "conditie", "conditie pachet")
T(rol_de_conditie("15 lei/luna", "Pret pachet/luna fara indeplinirea conditie de pachet",
                  15.0) is None, "pretul pachetului NU e conditie")
T(rol_de_conditie("3% din Valoarea tranzacțiilor efectuate cu Cardul, la care se",
                  "Suma minimă de plata de rambursat lunar", 3.0) == "conditie",
  "suma minima de plata")
T(rol_de_conditie("cu 20% pentru clienții care dețin un pachet",
                  "Comisionul de analiză dosar este redus astfel:", 20.0) == "conditie",
  "reducerea din eticheta")
T(rol_de_conditie("cu 20% pentru clienții care dețin un pachet",
                  "Comision de analiză dosar", 20.0) is None, "fara reducere NU e conditie")
# data de la coada etichetei ramane; indexul lipit se taie
T(RE_INDEX_LA_SFARSIT.sub("", "pe adresa BCR 3.2.7.") == "pe adresa BCR", "index taiat")
T(RE_INDEX_LA_SFARSIT.sub("", "Cu token cumpărat începând cu 05.04.2019")
  == "Cu token cumpărat începând cu 05.04.2019", "data ramane")
T(RE_INDEX_LA_SFARSIT.sub("", "Plăți instant ≤ LEI 5.000") == "Plăți instant ≤ LEI 5.000",
  "suma ramane")
T(_fara_cifre("PAGINA 3") == _fara_cifre("PAGINA 14"), "subsolul numerotat se repeta")
# marcajul notei; randul numerotat al tabelului nu e nota
for t in ["*Comisionul Transfond de 0,51 LEI", "NOTE:", "Nota bene: Nu se percepe",
          "4Clienti vulnerabili", "17Financially", "1În"]:
    T(RE_MARCAJ_NOTA.match(t), f"marcaj de nota: {t}")
for t in ["1 Comision administrare", "3D Secure", "Notificare prin SMS", "Nota de debit"]:
    T(not RE_MARCAJ_NOTA.match(t), f"NU e marcaj de nota: {t}")
# bordura: umplerile alaturate si sublinierea NU sunt borduri
T(not _bordura_intre([(84.7, 38.8, 563.5), (84.7, 38.8, 563.5)], 83, 87, 44),
  "doua umpleri alaturate (Vista)")
T(_bordura_intre([(445.1, 54.4, 331.2), (445.6, 54.4, 331.2)], 443, 450, 60),
  "dreptunghi subtire (ProCredit)")
T(_bordura_intre([(445.1, 54.4, 331.2)], 443, 450, 60), "linie singura")
T(not _bordura_intre([(605.4, 46.6, 70.0), (606.0, 46.6, 70.0)], 604, 608, 47),
  "sublinierea lui NOTE:")
# zona notei: marcaj, continuare, sfarsit
Z = _nota_dupa(None, 5, 41, 75, 84, ["*Comisionul Transfond de 0,51 LEI"], False, [])
T(Z and Z[:2] == (5, 41), "marcajul deschide nota")
T(_nota_dupa(Z, 5, 44, 87, 96, ["6 LEI pentru platile ≥ 50.000 LEI sunt incluse."],
             False, []), "randul de sub marcaj continua nota")
T(_nota_dupa(Z, 5, 44, 87, 96, ["Avizare", "50 EUR"], False, []) is None,
  "randul de tabel cu doua celule o inchide")
T(_nota_dupa(Z, 5, 410, 87, 96, ["250 EUR + TVA"], False, []) is None,
  "pretul din alta coloana o inchide")
T(_nota_dupa(Z, 5, 44, 87, 96, ["Depuneri de numerar"], False,
             [(85.0, 38.8, 563.5)]) is None, "bordura o inchide")
T(_nota_dupa(Z, 6, 41, 87, 96, ["ceva"], False, []) is None, "pagina noua o inchide")
Z = _nota_dupa(None, 4, 44, 634, 642, ["17Financially"], False, [])
T(_nota_dupa(Z, 4, 100, 635, 643, ["non-vulnerable customers"], False, []),
  "restul randului rupt de exponent")
Z = _nota_dupa(None, 4, 234, 994, 1030, ["Extraoptiune IMM Retrageri numerar ..."], True, [])
T(_nota_dupa(Z, 4, 2726, 996, 1030, ["12 lei"], False, []) is None,
  "pretul de pe randul prozei NU intra in nota")
# proza si antetul firmei
T(_e_nota("gratuit", "neacceptarea modificarii (caz in care are dreptul sa denunte "
          "unilateral Contractul, imediat si gratuit inainte de data propusa"), "gratuit in proza")
T(not _e_nota("gratuit", "Gratuit"), "gratuit in celula")
T(_e_nota("comision_suma", "Capital Social: 1.625.341.625,40 lei"), "capitalul social")
T(_e_nota("gratuit", "gratuit din orice reţea naţională;"), "telefonul gratuit")
T(not _e_nota("comision_suma", "35 lei + TVA"), "pretul NU e nota")


print(f"\n{TRECUTE} trecute, {ESUATE} eșuate")
sys.exit(1 if ESUATE else 0)
