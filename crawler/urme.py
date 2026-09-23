"""Detecția schimbării: ce a publicat altfel banca de la ultima rulare.

Amprenta se ia pe OCTEȚII documentului, niciodata pe valorile extrase. Motivul e
o eroare masurabila: intre 17 si 18 septembrie, comisioane_pdf.json a scazut de
la 430 la 427 de valori. Un diff pe valori ar fi raportat "au dispărut trei
comisioane la bănci". Nu dispăruse nimic — eu schimbasem regexul de bandă.

Un sistem care nu separa "banca a schimbat" de "parserul meu a schimbat"
fabrica constatari false, iar o constatare falsa arata exact ca o descoperire.
Octeții nu depind de versiunea parserului; de-aia amprenta sta pe ei.

Versiunea parserului se pastreaza oricum, in fiecare rulare, dar cu alt rol:
spune DACA o comparatie de valori are voie sa fie facuta. Daca amprenta
parserului difera intre doua rulari, diferenta de valori nu e interpretabila si
trebuie spusa ca atare, nu prezentata ca o schimbare de piata.

Stari, si de ce sunt sapte si nu doua:

  NOU          URL-ul nu fusese vazut niciodata
  NESCHIMBAT   aceiasi octeti
  SCHIMBAT     octeti diferiti — asta e constatarea
  LIPSA        banca A fost recrawlata si nu mai referă documentul
  NEVERIFICAT  banca NU a fost recrawlata, deci absenta nu dovedeste nimic
  AMBIGUU      mai multe URL-uri scriu in acelasi fisier local, deci octeții de
               pe disc aparțin celui descarcat ultimul
  NEDESCARCAT  referit, dar deliberat neluat (interzis de robots.txt, ori nu e
               document de tarife)

Trei dintre ele — NEVERIFICAT, AMBIGUU si NEDESCARCAT — spun toate acelasi
lucru din trei motive diferite: NU SE POATE SPUNE. E disciplina din cele patru
stari ale validatorului: o verificare care nu s-a putut face nu e un rezultat.
Fara NEVERIFICAT, o rulare in care un site a picat ar raporta ca banca si-a
retras tarifele.

AMBIGUU a fost adaugata dupa ce a produs o constatare falsa, nu inainte.
Sistemul fusese construit ca sa separe "banca a schimbat" de "parserul meu a
schimbat"; al treilea caz, "doua URL-uri isi impart un fisier", scapase. Crawlul
numeste fisierele locale dupa basename, iar doua adrese TBI ("/2023/09/" si
"/2022/09/") servesc fisiere de 68.548 si 68.572 octeți in acelasi loc — de unde
"TBI si-a schimbat documentul", care nu se intamplase. Erau 8 cai folosite de 16
URL-uri. Reparat cu cale_unica(), care da fiecarui URL fisierul lui.
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

RADACINA = Path(__file__).resolve().parent.parent
CALE_URME = RADACINA / "output" / "urme.json"
CRAWL = RADACINA / "output" / "crawl"
ROBOTS = RADACINA / "output" / "robots"

# Modulele care decid ce valori ies din documente. Amprenta lor e versiunea
# parserului. Se calculeaza din surse, nu dintr-un numar scris de mana: un numar
# de versiune pus manual se uita exact cand conteaza.
MODULE_EXTRAGERE = ["parser_pdf.py", "parser_tarife.py", "parser_rate.py",
                    "vocabular.py", "validator.py",
                    # data_document decide CARE documente au voie sa contribuie
                    # cu valori (`ISTORIC`, `DUBLURA`). O schimbare aici misca
                    # mediane fara ca vreun parser sa se fi atins — exact felul
                    # de schimbare proprie pe care amprenta exista s-o prinda.
                    "data_document.py"]

STARI_CU_DOCUMENT = ("NOU", "NESCHIMBAT", "SCHIMBAT")


def acum():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def amprenta_octeti(cale):
    """sha256 pe conținutul fișierului, citit in bucati ca sa nu incarce tot."""
    h = hashlib.sha256()
    with open(cale, "rb") as f:
        for bucata in iter(lambda: f.read(1 << 20), b""):
            h.update(bucata)
    return h.hexdigest()


def amprenta_parser():
    """Versiunea parserului: sha256 peste modulele care decid extragerea.

    Numele intra in amprenta pe langa conținut, ca redenumirea unui modul sa se
    vada. Ordinea e sortata, ca amprenta sa nu depinda de ordinea din lista.
    """
    h = hashlib.sha256()
    for nume in sorted(MODULE_EXTRAGERE):
        cale = RADACINA / "crawler" / nume
        h.update(nume.encode("utf-8"))
        h.update(cale.read_bytes() if cale.exists() else b"<lipsa>")
    return h.hexdigest()[:16]


def origine(url):
    return urlparse(url).netloc.lower()


def robots_pe_origini():
    """Ce origini au robots.txt citit si pastrat.

    Cheia e originea, nu banca: robots.txt e per origine prin standard, iar
    documentele bancilor stau des pe alt domeniu (cdn.erstegroup.com pentru BCR,
    assets.revolut.com pentru Revolut). O regula citita pentru www.bcr.ro nu
    spune nimic despre ce se poate lua de pe cdn.erstegroup.com.
    """
    verificate = {}
    for f in sorted(CRAWL.glob("*.json")):
        if f.name == "consolidat.json":
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        baza = origine(d.get("base_url") or "")
        if baza and (d.get("robots") or {}).get("status"):
            verificate[baza] = d["robots"]["status"]

    # Originile terțe verificate separat intra si ele aici, altfel avertismentul
    # ar suna la fiecare rulare dupa ce problema a fost deja rezolvata — iar o
    # alarma care nu se stinge niciodata inceteaza sa fie citita. Cu fisierul
    # citit, avertismentul revine exact pentru originile NOI de maine.
    #
    # Se accepta numai verdictele care s-au putut da: un cod 4xx e un raspuns
    # prin RFC 9309 (originea nu declara restricții), dar o eroare de rețea nu e.
    cale = RADACINA / "output" / "robots_origini.json"
    if cale.exists():
        try:
            for o, r in json.loads(cale.read_text(encoding="utf-8")).items():
                stare = r.get("status") or ""
                if stare.startswith("citit") or "inaccesibil" in stare:
                    verificate[o] = stare
        except (json.JSONDecodeError, OSError):
            pass
    return verificate


def _observa_documentele():
    """Ce refera crawlul acum: URL -> banca, cale locala, motivul saririi."""
    pe_url, momente = {}, {}
    for f in sorted(CRAWL.glob("*.json")):
        if f.name == "consolidat.json":
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        bid = d.get("banca_id") or f.stem
        momente[bid] = d.get("moment_crawl")
        for p in d.get("pagini", []):
            for q in (p.get("pdfs") or []):
                if not isinstance(q, dict) or not q.get("url"):
                    continue
                # prima referinta castiga: acelasi document e legat de pe mai
                # multe pagini, iar cheia e URL-ul, nu pagina care il leaga
                pe_url.setdefault(q["url"], {
                    "banca": bid,
                    "cale": q.get("fisier_local"),
                    "sarit": q.get("sarit"),
                })
    return pe_url, momente


def nume_din_url(url):
    """Nume de fisier local derivat din URL-ul INTREG, nu din ultimul segment.

    Cauza coliziunii: crawlul numea fisierele numai dupa ultimul segment al
    URL-ului, deci doua adrese diferite cu acelasi nume de fisier ajungeau in
    acelasi loc. Masurat: 8 cai folosite de 16 URL-uri — doua adrese TBI
    ("/2023/09/" si "/2022/09/") servesc fisiere de 68.548 si 68.572 octeți.

    Prefixul face numele stabil si unic pentru un URL dat, iar numele original
    rămâne in coada, ca fisierul sa fie recunoscibil de om.
    """
    baza = re.sub(r"[^A-Za-z0-9._-]", "_", urlparse(url).path.split("/")[-1])[:112]
    if not baza.lower().endswith(".pdf"):
        baza += ".pdf"
    return f"{hashlib.sha1(url.encode()).hexdigest()[:8]}_{baza}"


def cale_unica(url, cale):
    """Calea locala a unui document, cu numele derivat din URL."""
    return str(Path(cale).with_name(nume_din_url(url)))


def observa():
    """Starea de acum a fiecarui document referit, cu amprenta unde exista.

    Cand mai multe URL-uri trimit la acelasi fisier local, octeții de pe disc
    aparțin URL-ului descarcat ultimul, iar comparatia nu mai spune nimic despre
    niciunul. Se marcheaza, si starea devine AMBIGUU pana cand fiecare URL isi
    are propriul fisier — pentru aceeasi disciplina ca LIPSA/NEVERIFICAT: ce nu
    se poate verifica nu se raporteaza ca verificat.
    """
    pe_url, momente = _observa_documentele()
    robots = robots_pe_origini()

    folosinte = {}
    for url, v in pe_url.items():
        if v["cale"]:
            folosinte.setdefault(v["cale"], []).append(url)
    partajate = {c for c, us in folosinte.items() if len(us) > 1}

    out = {}
    for url, v in pe_url.items():
        o = origine(url)
        rand = {
            "banca": v["banca"],
            "origine": o,
            "origine_proprie": o in robots,
            "robots_origine": robots.get(o),
            "cale": v["cale"],
            "cale_partajata": v["cale"] in partajate,
        }
        # daca URL-ul si-a primit deja fisierul propriu, el are prioritate
        proprie = cale_unica(url, v["cale"]) if v["cale"] else None
        if proprie and (RADACINA / proprie).exists():
            rand["cale"] = proprie
            rand["cale_partajata"] = False
            v = dict(v, cale=proprie)
        cale = RADACINA / v["cale"] if v["cale"] else None
        if cale and cale.exists():
            rand["amprenta"] = amprenta_octeti(cale)
            rand["octeti"] = cale.stat().st_size
        else:
            rand["amprenta"] = None
            rand["motiv"] = v["sarit"] or "nu s-a descarcat"
        out[url] = rand
    return out, momente


def citeste_urme():
    if not CALE_URME.exists():
        return {"rulari": [], "documente": {}, "banci": {}}
    return json.loads(CALE_URME.read_text(encoding="utf-8"))


def compara(urme, observat, momente):
    """Starea fiecarui document, plus documentele din registru care n-au aparut.

    Absenta se judeca pe banca, nu pe document: daca banca nu a fost recrawlata
    de la ultima rulare, documentele ei lipsa sunt NEVERIFICAT, nu LIPSA.
    """
    vechi = urme.get("documente", {})
    momente_vechi = urme.get("banci", {})
    stari = {}

    for url, r in observat.items():
        v = vechi.get(url)
        if r["amprenta"] is None:
            stare = "NEDESCARCAT"
        elif r.get("cale_partajata"):
            # octeții de pe disc aparțin altui URL: nu se poate spune nimic
            stare = "AMBIGUU"
        elif v is None or not v.get("amprenta"):
            stare = "NOU"
        elif v["amprenta"] == r["amprenta"]:
            stare = "NESCHIMBAT"
        else:
            stare = "SCHIMBAT"
        stari[url] = dict(r, stare=stare,
                          amprenta_veche=(v or {}).get("amprenta"))

    for url, v in vechi.items():
        if url in stari:
            continue
        banca = v.get("banca")
        recrawlat = (momente.get(banca)
                     and momente[banca] != momente_vechi.get(banca))
        stari[url] = dict(v, stare="LIPSA" if recrawlat else "NEVERIFICAT",
                          amprenta_veche=v.get("amprenta"))
    return stari


def actualizeaza(urme, stari, momente, versiune):
    """Registrul nou. Pastreaza istoricul amprentelor pentru ce s-a schimbat.

    Cladeste pe registrul vechi, NU un obiect nou cu trei chei. Prima versiune
    intorcea `{"rulari", "banci", "documente"}` si arunca in tacere tot restul:
    `origini` (ce validator a fost prins mințind la ce origine), `sonde`
    (istoricul sondajelor) si, pe fiecare document, `semnale` (ETag-ul si
    Last-Modified fara de care sonda urmatoare o ia de la zero si descarca inutil
    zeci de documente).

    Garda din scrie_urme nu prindea nimic: numara documentele, iar ele erau
    toate acolo. O scriere poate fi "plina" si totusi sa piarda ce stie
    sistemul.
    """
    moment = acum()
    documente = dict(urme.get("documente", {}))
    for url, s in stari.items():
        if s["stare"] == "NEVERIFICAT":
            continue                      # nu atinge ce n-a fost verificat
        vechi = documente.get(url, {})
        istoric = list(vechi.get("istoric", []))
        if s["stare"] == "SCHIMBAT":
            istoric.append({"moment": moment,
                            "de_la": s.get("amprenta_veche"),
                            "la": s.get("amprenta"),
                            "versiune_parser": versiune})
        documente[url] = {
            "banca": s.get("banca"),
            "origine": s.get("origine"),
            "origine_proprie": s.get("origine_proprie"),
            "cale": s.get("cale"),
            "amprenta": s.get("amprenta"),
            "octeti": s.get("octeti"),
            "motiv": s.get("motiv"),
            "prima_vedere": vechi.get("prima_vedere", moment),
            "ultima_vedere": moment,
            "verificari": vechi.get("verificari", 0) + 1,
            "istoric": istoric,
            # semnalele HTTP nu se recalculeaza aici — se pastreaza de la sonda
            "semnale": vechi.get("semnale"),
        }
    rulari = list(urme.get("rulari", []))
    rulari.append({"moment": moment, "versiune_parser": versiune,
                   "documente": len(documente)})
    nou = dict(urme)                      # tot ce nu atingem rămâne
    nou.update(rulari=rulari, banci=dict(momente), documente=documente)
    return nou


def scrie_urme(nou):
    """Scrie registrul, dar NU peste unul bun cu unul gol.

    Pe 18 septembrie am pierdut zece zile de ROBOR fiindca un script a scris un
    obiect de eroare peste seriile intregi si n-a spus nimic. Aceeasi greseala
    aici ar sterge istoricul de amprente, care nu se poate reface: octeții de
    ieri nu mai exista nicaieri.
    """
    vechi = citeste_urme()
    n_vechi = len(vechi.get("documente", {}))
    n_nou = len(nou.get("documente", {}))
    if n_vechi and not n_nou:
        return False, (f"registrul are {n_vechi} documente, iar rularea a produs 0 "
                       f"— NU s-a scris nimic, istoricul de amprente e pastrat")

    # Numararea documentelor nu e de ajuns. O scriere poate fi "plina" — toate
    # cele 1.185 de documente la locul lor — si totusi sa arunce ce a INVATAT
    # sistemul: ce validator minte la ce origine, istoricul sondajelor, si
    # ETag-urile fara de care sonda urmatoare descarca inutil zeci de fisiere.
    # S-a intamplat: actualizeaza() intorcea un obiect nou cu trei chei.
    pierdute = []
    for cheie in ("origini", "sonde"):
        if vechi.get(cheie) and not nou.get(cheie):
            pierdute.append(f"{cheie} ({len(vechi[cheie])})")
    sem_vechi = sum(1 for v in vechi.get("documente", {}).values()
                    if v.get("semnale"))
    sem_nou = sum(1 for v in nou.get("documente", {}).values() if v.get("semnale"))
    if sem_vechi and sem_nou < sem_vechi // 2:
        pierdute.append(f"semnale HTTP ({sem_vechi} -> {sem_nou})")
    if pierdute:
        return False, ("NU s-a scris: registrul nou pierde "
                       + ", ".join(pierdute)
                       + ". Numarul de documente era in regula, dar cunoasterea "
                         "acumulata nu — vezi actualizeaza().")

    CALE_URME.parent.mkdir(parents=True, exist_ok=True)
    CALE_URME.write_text(json.dumps(nou, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    return True, f"{n_nou} documente in registru (erau {n_vechi})"


# --- semnalele HTTP: filtru ieftin, nu dovada -------------------------------
# ETag se poate schimba fara ca fisierul sa se schimbe (rescriere, alt nod de
# CDN), si un fisier se poate schimba pastrand aceeasi lungime. Deci semnalul
# decide DACA merita sa ne uitam; octeții decid DACA s-a schimbat.
#
# "DE_CITIT" nu e o stare finala — e instrucțiunea de a descarca si confirma.
# "NESCHIMBAT_PROBABIL" e o stare finala, dar NU o confirmare, si nu trebuie
# raportata ca una: a patra oara in proiect cand distincția conteaza, dupa cele
# patru stari ale validatorului, LIPSA/NEVERIFICAT de mai sus, si 4xx fața de
# eroare-de-rețea la verificarea robots.


def data_http(valoare):
    """Data dintr-un antet HTTP, ori None daca lipsește sau e nevalida."""
    try:
        return parsedate_to_datetime(valoare)
    except (TypeError, ValueError):
        return None


def baza_de_timp(rand):
    """Momentul la care au fost luați octeții pe care ii avem."""
    for cheie in ("ultima_vedere", "prima_vedere"):
        if rand.get(cheie):
            try:
                return datetime.fromisoformat(rand[cheie])
            except ValueError:
                pass
    return None


# Sub atâtea secunde fața de ceasul nostru, Last-Modified nu e o informație
# despre document, e o ștampila pusa de server la cerere. Raiffeisen raspunde
# "Last-Modified: <ora cererii>" pentru 11 documente: comparat cu valoarea
# precedenta difera mereu, deci ar cere descarcare la fiecare rulare pe vecie.
# Un validator care se schimba singur nu e un validator.
SECUNDE_STAMPILA = 900


def validator_de_incredere(urme, o, nume):
    """Validatorul `nume` al originii `o` a fost prins mințind?

    Regula generala, si e cea care a inlocuit trei reguli speciale: ORICE antet
    care arata ca un validator poate sa nu fie unul, iar singurul mod de a afla
    e sa-l prinzi. Cand o descarcare de confirmare nu gaseste nicio schimbare
    desi validatorul acela spusese "altfel", validatorul e nesigur LA ORIGINEA
    ACEEA, si nu se mai foloseste acolo. Se cade pe urmatorul.

    Doua feluri de minciuna, amandoua masurate:

    - ETag: cele sase cazuri din prima sonda erau ETag-uri TARI (fara "W/"),
      care prin standard garanteaza egalitatea octeților. Formatul le explica:
      `"269c4-6482c041c7a40"` e `marime-mtime` de Apache, iar intr-o ferma de
      servere mtime difera de la nod la nod pentru acelasi fișier.
    - Last-Modified: Raiffeisen si ProCredit raspund cu ora umplerii cache-ului,
      nu cu data documentului. Nu e nici ora cererii — masurat, valoarea era cu
      640 de secunde in urma — deci pragul SECUNDE_STAMPILA o rateaza uneori.
      Sa-l ridic ar fi arbitrar si ar arunca un document chiar proaspat.

    De ce per origine si nu global: la Garanti, numele fisierului confirma
    Last-Modified la trei zile, deci acolo antetul e bun. Un prag global ar fi
    stricat semnalul unde el functioneaza.
    """
    return not ((urme.get("origini") or {}).get(o) or {}).get(f"{nume}_nesigur")


def etag_de_incredere(urme, o):
    """Pastrat pentru apelanții care intreaba doar de ETag."""
    return validator_de_incredere(urme, o, "etag")


def clasifica_semnal(rand, antete, acum_dt=None, foloseste_etag=True,
                     foloseste_lm=True):
    """(stare, semnale, motiv) din anteturile HTTP, fara a deschide fișierul.

    La prima rulare nu exista ETag stocat — nu a fost inregistrat la crawlul din
    16 septembrie — deci se compara ce se poate compara imediat: Content-Length
    fața de octeții stocați, si Last-Modified fața de momentul in care i-am luat.
    De la rularea a doua, ETag-ul stocat face comparatia direct.
    """
    cap = {k.lower(): v for k, v in (antete or {}).items()}
    etag = cap.get("etag") if foloseste_etag else None
    lm = data_http(cap.get("last-modified"))

    # Last-Modified se arunca in doua cazuri, la fel ca o lungime comprimata:
    # cand e pus la ora cererii (se vede din ceas), si cand originea a fost deja
    # prinsa raspunzand cu ora cache-ului si nu cu data documentului (se afla din
    # masuratoare — vezi validator_de_incredere).
    if lm is not None and not foloseste_lm:
        cap.pop("last-modified", None)
        lm = None
    if lm is not None:
        referinta = acum_dt or datetime.now(timezone.utc)
        if abs((referinta - lm).total_seconds()) < SECUNDE_STAMPILA:
            cap.pop("last-modified", None)
            lm = None

    # Content-Length se compara cu marimea fisierului de pe disc, deci trebuie sa
    # fie marimea ENTITATII, nu a corpului comprimat. Masurat pe Raiffeisen:
    # HEAD implicit da "Content-Encoding: gzip" si "Content-Length: 91.339", in
    # timp ce fisierul are 105.454 octeți — cu Accept-Encoding: identity serverul
    # raspunde 105.454, adica exact. Fara asta, filtrul a cerut descarcarea a 58
    # de documente si doar UNUL era schimbat: 57 fals pozitive din 58.
    #
    # Cererea trimite identity, dar nu toate serverele o respecta, deci lungimea
    # se ignora oricum daca raspunsul vine comprimat. Si 0 se trateaza ca absenta:
    # un PDF de zero octeți nu exista.
    lungime = cap.get("content-length")
    lungime = int(lungime) if (lungime or "").isdigit() else None
    if cap.get("content-encoding") or lungime == 0:
        lungime = None

    semnale = {"etag": etag, "last_modified": cap.get("last-modified"),
               "content_length": lungime}
    vechi = rand.get("semnale") or {}

    if etag and vechi.get("etag"):
        identic = etag == vechi["etag"]
        return ("NESCHIMBAT_PROBABIL" if identic else "DE_CITIT", semnale,
                f"ETag {'identic' if identic else 'diferit'}")

    # Last-Modified se compara cu ce a spus serverul ULTIMA DATA, nu cu ceasul
    # nostru. 20 de documente au raspuns "Last-Modified: azi" — pentru ele
    # comparatia cu momentul descarcarii cerea o descarcare la fiecare rulare, pe
    # vecie. Fața de valoarea precedenta, intrebarea devine cea corecta: s-a
    # schimbat ce spune serverul despre document? Comparatia cu ceasul nostru
    # rămâne doar pentru prima rulare, cand n-avem cu ce altceva sa comparam.
    if cap.get("last-modified") and vechi.get("last_modified"):
        identic = cap["last-modified"] == vechi["last_modified"]
        if identic and (lungime is None
                        or lungime == (vechi.get("content_length") or lungime)):
            return ("NESCHIMBAT_PROBABIL", semnale, "Last-Modified neschimbat")
        if not identic:
            return ("DE_CITIT", semnale,
                    f"Last-Modified {cap['last-modified']} != "
                    f"{vechi['last_modified']}")

    if lungime is not None and rand.get("octeti") is not None:
        semnale["content_length"] = lungime
        if semnale["content_length"] != rand["octeti"]:
            return ("DE_CITIT", semnale,
                    f"Content-Length {semnale['content_length']:,} != "
                    f"{rand['octeti']:,} stocați")
        baza = baza_de_timp(rand)
        if lm and baza and lm > baza:
            return ("DE_CITIT", semnale,
                    f"Last-Modified {lm:%Y-%m-%d} mai nou decat baza "
                    f"{baza:%Y-%m-%d}")
        return ("NESCHIMBAT_PROBABIL", semnale, "aceeasi lungime, nu mai nou")

    if lm:
        baza = baza_de_timp(rand)
        if baza and lm > baza:
            return ("DE_CITIT", semnale, f"Last-Modified {lm:%Y-%m-%d} mai nou")
        return ("NESCHIMBAT_PROBABIL", semnale, "Last-Modified nu mai nou")

    return ("FARA_SEMNAL", semnale,
            "serverul nu trimite ETag/Length/Last-Modified")


def actualizeaza_semnale(urme, semnale, stari_noi=None, amprente_noi=None):
    """Pune in registru semnalele HTTP si, unde s-a confirmat, amprenta noua.

    Semnalele (ETag, Last-Modified, Content-Length) sunt un filtru ieftin, NU o
    dovada: ETag se poate schimba fara ca fisierul sa se schimbe, si invers. De
    aceea se pastreaza separat de `amprenta`, care rămâne sursa de adevar si se
    schimba numai dupa ce octeții au fost cititi.
    """
    documente = dict(urme.get("documente", {}))
    moment = acum()
    for url, s in (semnale or {}).items():
        if url not in documente:
            continue
        r = dict(documente[url])
        r["semnale"] = dict(s, vazut=moment)
        documente[url] = r
    for url, amp in (amprente_noi or {}).items():
        if url not in documente:
            continue
        r = dict(documente[url])
        istoric = list(r.get("istoric", []))
        if r.get("amprenta") and r["amprenta"] != amp["amprenta"]:
            istoric.append({"moment": moment, "de_la": r["amprenta"],
                            "la": amp["amprenta"], "sursa": "sonda",
                            # unde stau octeții de dinainte, ca sa se poata
                            # spune CE s-a schimbat, nu doar CA s-a schimbat
                            "versiune_veche": amp.get("versiune_veche"),
                            "octeti_vechi": r.get("octeti")})
        r.update(amprenta=amp["amprenta"], octeti=amp.get("octeti"),
                 ultima_vedere=moment, istoric=istoric)
        if amp.get("cale"):
            r["cale"] = amp["cale"]
            r["cale_partajata"] = False
        documente[url] = r
    out = dict(urme)
    out["documente"] = documente
    out["sonde"] = list(urme.get("sonde", [])) + [{
        "moment": moment,
        "interogate": len(semnale or {}),
        "stari": dict(stari_noi or {}),
    }]
    return out


def comparatie_de_valori_permisa(urme, versiune):
    """Se pot compara valorile extrase cu cele de la rularea anterioara?

    Numai daca parserul n-a fost atins intre timp. Altfel diferenta amesteca
    schimbarile bancilor cu schimbarile mele si nu spune nimic despre piata.
    """
    rulari = [r for r in urme.get("rulari", []) if r.get("versiune_parser")]
    if not rulari:
        return False, "nu exista o rulare anterioara"
    ultima = rulari[-1]["versiune_parser"]
    if ultima == versiune:
        return True, f"parser neschimbat de la ultima rulare ({versiune})"
    return False, (f"parserul s-a schimbat ({ultima} -> {versiune}); diferența de "
                   f"valori NU e interpretabila ca schimbare de piața")
