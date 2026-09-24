"""Extractoarele: fiecare produce înregistrări brute, niciunul nu știe de bază.

ATENȚIE la numele `din_playwright`: NU extrage din PDF. Citește JSON-ul pe care
pachetul colegului l-a produs deja. Extracția dintr-un PDF nou o face
`din_pdf`, mai jos. Diferența contează: până a existat `din_pdf`, pipeline-ul
nu putea procesa niciun document nou, iar 16 bănci (printre care ING, Banca
Transilvania, UniCredit, CEC) aveau zero comisioane în bază — nu din vina
băncilor, ci fiindcă nimic nu citea PDF-uri.

Regula care ține pipeline-ul curat: un extractor răspunde doar la „ce am găsit
pe sursa asta". Nu cunoaște tabele, nu cunoaște slug-uri de produs, nu decide
unități și nu aplică praguri. Toate acelea sunt în `normalizeaza.py`, o singură
dată. Așa, o sursă nouă înseamnă o funcție nouă aici, nu un loader nou cu încă
o copie a regulilor de traducere.

Trei extractoare, pentru cele trei variante de colectare:

  din_playwright()        PDF-uri + HTML, pachetul colegului (21 sept).
                          Singurul care are comisioane din documente oficiale
                          și singurul care aduce datare de document.
  din_bs4_depozite()      HTML, scraperul propriu. Singurul care acoperă
                          depozitele și numele de produse de economisire.
  din_html_live(url, ...) HTML, live. Același extractor ca al doilea, dar pe
                          URL-uri primite din afară — pentru sursele găsite de
                          discovery-ul LLM, pe care nimeni nu le rulase.

Al treilea e veriga care lipsea. Măsurat înainte de el: banca-transilvania avea
13 surse descoperite și 0 observații; la fel unicredit (18), intesa (18),
cec (15), citibank (14), bankofchina (17), bid, pko, bnpparibas.
"""

import io
import json
import os
import re
import sys
import urllib.parse

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AICI))

from normalizeaza import brut                                       # noqa: E402

PACHET = os.path.join(os.path.dirname(AICI), "date", "pachet")
FISIER_BS4 = os.path.join(os.path.dirname(AICI), "date", "rezultate_depozite.json")

# Stiva proprie de colectare (scraper.py: robots.txt, User-Agent onest, delay,
# detecție de encoding) se importă la cerere: extractoarele din fișier nu au
# nevoie de rețea și nu trebuie să depindă de ea.


def _citeste(cale):
    with io.open(cale, encoding="utf-8") as f:
        return json.load(f)


# ==========================================================================
# 1. Playwright (pachetul colegului): comisioane din PDF + rate din HTML
# ==========================================================================

def din_playwright():
    """Comisioane (PDF) + rate (HTML) + datarea documentelor.

    Spre deosebire de prima versiune, NU filtrează `stare_data`. Versiunile
    istorice se încarcă și se marchează; filtrul e al afișării. Altfel se
    pierdeau 27 de schimbări reale de preț (BCR, transfer intrabancar la
    ghișeu: 15 lei la 2024-06-14 -> 30 lei la 2024-06-19).
    """
    comisioane = _citeste(os.path.join(PACHET, "comisioane_unificate.json"))
    rate = _citeste(os.path.join(PACHET, "rate_validate.json"))
    documente = _citeste(os.path.join(PACHET, "date_documente.json"))
    amprente = {
        k.replace("\\", "/"): v.get("amprenta")
        for k, v in documente.items() if v.get("amprenta")
    }

    for c in comisioane:
        cale = (c.get("sursa_pdf") or "").replace("\\", "/")
        if not cale:
            continue
        yield brut(
            banca=cale.split("/")[0], sursa=cale,
            tip_sursa="document", format="pdf", frecventa_sursa="lunar",
            amprenta=amprente.get(cale),
            concept=c.get("concept") or "comision", tip=c.get("tip"), rol=c.get("rol"),
            valoare=c.get("valoare"), moneda=c.get("moneda"),
            serviciu=c.get("serviciu"), sectiune=c.get("sectiune"),
            conditie=c.get("conditie"), frecventa=c.get("frecventa"),
            detaliu=c.get("detaliu"), pagina=c.get("pagina"),
            segment=c.get("segment"), canal=c.get("canal"),
            destinatie=c.get("destinatie"),
            citat=c.get("text_sursa"),
            incredere=0.7 if c.get("stare_data") == "DATA_NECUNOSCUTA" else 0.9,
            ambiguu=c.get("ambiguu"), motiv_ambiguu=c.get("motiv_ambiguu"),
            data_vigoare=c.get("data_vigoare"), stare_data=c.get("stare_data"),
            produs="comisioane",
        )

    for r in rate:
        url = r.get("sursa_url")
        if not url:
            continue
        yield brut(
            banca=r.get("banca"), sursa=url, tip_sursa="url", format="html",
            frecventa_sursa="zilnic",
            concept=r.get("tip_rata"), tip="rata",
            valoare=r.get("valoare"), moneda=r.get("moneda"),
            # `produs` din pachet e titlul paginii — cel mai apropiat lucru de
            # „la ce se referă rata asta"
            serviciu=r.get("produs"), sectiune=r.get("categorie"),
            frecventa=r.get("perioada"),
            categorie=r.get("categorie"), perioada=r.get("perioada"),
            nr_rate=r.get("nr_rate"),
            citat=r.get("text_sursa"), incredere=r.get("incredere"),
        )


# ==========================================================================
# 2. BS4 propriu: depozite + nume de produse de economisire
# ==========================================================================

MAPARE_BS4 = {
    "nominala": "depozite", "dae": "dae", "marja_ircc": "marja-ircc",
    "euribor_valoare": "robor-euribor", "comision_procent": "comisioane",
    "rate_fara_dobanda": "card-de-credit",
}


def din_bs4_depozite():
    """Dobânzi de depozit + nume de produse, din rularea proprie.

    Numele de produse se păstrează cu încredere mică (0,5): extracția de nume
    e euristică, cu fals-pozitive cunoscute (întrebări de FAQ, firimituri de
    meniu). „Ce produse de economisire are banca X" e informație competitivă
    în sine, dar nu are valoarea unui preț citit din tabel.
    """
    if not os.path.exists(FISIER_BS4):
        return
    for b in _citeste(FISIER_BS4):
        for r in b.get("dobanzi") or []:
            if not r.get("sursa_url"):
                continue
            yield brut(
                banca=b["name"], sursa=r["sursa_url"], frecventa_sursa="zilnic",
                concept=r.get("tip_rata"), tip="rata",
                produs=MAPARE_BS4.get(r.get("tip_rata")),
                valoare=r.get("valoare"), moneda=r.get("moneda"),
                serviciu=r.get("produs"), sectiune=r.get("categorie"),
                frecventa=r.get("perioada"),
                categorie=r.get("categorie"), perioada=r.get("perioada"),
                citat=r.get("text_sursa"), incredere=r.get("incredere"),
            )
        for p in b.get("produse") or []:
            if not (p.get("nume") and p.get("sursa")):
                continue
            yield brut(
                banca=b["name"], sursa=p["sursa"], frecventa_sursa="zilnic",
                concept="nume_produs", produs="depozite",
                valoare_text=p["nume"], serviciu=p["nume"],
                categorie="depozite", citat=p.get("context"), incredere=0.5,
            )


# ==========================================================================
# 3. HTML live: sursele descoperite de discovery-ul LLM
# ==========================================================================

# Calea URL -> (categorie pentru cod_scenariu, produs din catalog). Ordinea
# contează: prima regulă care se potrivește câștigă, de-aia `ipotec` stă
# înaintea lui `credit`, și `card` înaintea lui `cont` (un card de credit e
# card, nu cont).
REGULI_URL = [
    # Cursul valutar: inclusiv variantele în engleză, fiindcă mai multe bănci
    # (Patria, TBI, Nexent, Citibank) publică doar pagina în engleză.
    (r"curs|exchange[-_]?rate|rate[-_]?de[-_]?schimb",   "curs",            "curs-valutar-propriu"),
    (r"depozit|economi|saving|deposit",                  "depozite",        "depozite"),
    (r"prima[-_]?casa|noua[-_]?casa",                    "credite",         "noua-casa"),
    (r"ipotec|imobiliar|refinantar|mortgage",            "credite",         "ipotecar-refinantare"),
    (r"leasing",                                         "credite",         "leasing"),
    (r"factoring",                                       "credite",         "factoring"),
    (r"robor|euribor|ircc|indici|dobanzi[-_]?referin|money[-_]?market",
                                                         "credite",         "robor-euribor"),
    (r"card",                                            "conturi_carduri", "card-de-credit"),
    # Listele de taxe și condiții generale: aici stau comisioanele, inclusiv
    # `fees-and-interest-rates` (Garanti) și `termeni-si-conditii` (Credex).
    # `comisio`, nu `comision`: „comisioane" NU conține „comision" — după
    # `comisio` vine `a`, nu `n`. Cu forma lungă, o pagină ca
    # `bcr.ro/.../informatii-utile/comisioane` nu se clasifica deloc.
    (r"taxe|comisio|tarif|fee|termeni|conditii|pricing", "comisioane",     "comisioane"),
    (r"overdraft|trezorerie|treasury|garantii|guarantee", "credite",        "dobanda-nominala"),
    (r"credit|imprumut|finantar|nevoi|loan|financ",       "credite",        "dobanda-nominala"),
    (r"cont|abonament|pachet|account|cash[-_]?management|payment|plati",
                                                          "conturi_carduri", "cont-curent"),
]

SEPARATOARE_TITLU = re.compile(r"\s*[|·»—–]\s*")


def _fara_diacritice(t):
    from scraper import strip_diacritics
    return strip_diacritics(t)


def clasifica(url, titlu):
    """Categoria și produsul, din calea URL-ului; titlul e doar rezervă.

    Calea e mai de încredere decât titlul: `/dobanzi-depozite-lei` spune
    categoria fără ambiguitate, în timp ce titlul poate fi un slogan de
    marketing care nu numește produsul.
    """
    cale = _fara_diacritice(urllib.parse.urlparse(url).path.lower())
    for rx, categorie, produs in REGULI_URL:
        if re.search(rx, cale):
            return categorie, produs, "url"
    t = _fara_diacritice((titlu or "").lower())
    for rx, categorie, produs in REGULI_URL:
        if re.search(rx, t):
            return categorie, produs, "titlu"
    return None, None, None


def _nume_produs(soup, titlu):
    """h1, altfel primul segment din <title>.

    Nu regex pe tot textul: URL-ul descoperit E deja pagina unui produs anume
    (`cec.ro/.../credit-ipotecar-prima-casa`), deci titlul paginii e numele
    produsului. Euristica pe text liber, folosită când nu știi pe ce pagină
    ești, producea fals-pozitive de tip întrebare de FAQ.
    """
    h1 = soup.find("h1")
    if h1:
        t = h1.get_text(" ", strip=True)
        if 3 < len(t) < 120:
            return t
    if titlu:
        bucati = [b.strip() for b in SEPARATOARE_TITLU.split(titlu) if len(b.strip()) > 3]
        if bucati:
            return bucati[0][:120]
    return None


# Liniile cu procente pe care parserul nu le-a putut tipiza, pe URL.
# Le consumă `populare_initiala.extrage` când rezerva LLM e pornită.
PROBLEME = {}

RE_PAGINA_PRESA = re.compile(r"/press|/presa|comunicat|/stiri|/news|/noutati|/blog", re.I)


def _continut_principal(octeti):
    """Aceleași tag-uri eliminate ca la amprentă (sanitizare.py)."""
    from bs4 import BeautifulSoup
    from sanitizare import ZGOMOT
    soup = BeautifulSoup(octeti, "lxml")
    for tag in soup.find_all(ZGOMOT):
        tag.decompose()
    return (soup.find("main") or soup.find(attrs={"role": "main"})
            or soup.find("article") or soup.body or soup)


def _linii(soup):
    """Linii pe care le poate citi `parser_rate.py`.

    Un rând de tabel se dă ca celule unite prin TAB, fiindcă parserul se
    bazează pe ele ca să citească coloanele de pe același rând (termen,
    dobândă, monedă). `get_text()` cu un singur separator le-ar amesteca și
    rândul de tabel și-ar pierde structura.
    """
    linii = []
    for tr in soup.find_all("tr"):
        celule = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        celule = [c for c in celule if c]
        if celule:
            linii.append("\t".join(celule))
    for bloc in soup.get_text(separator="\n").split("\n"):
        bloc = bloc.strip()
        if bloc:
            linii.append(bloc)
    return linii


def din_html_live(url, banca, rol_sursa="produs"):
    """Aduce o pagină și extrage ce e pe ea. Nu forțează nimic.

    Întoarce (listă de înregistrări brute, stare, notă). Starea și nota se
    scriu pe sursă: „blocat de robots.txt" și „pagină randată prin JS" cer
    acțiuni diferite, iar fără ele ambele arată identic (sursă fără observații).
    """
    from bs4 import BeautifulSoup
    from crawler.parser_rate import parseaza_linie
    from scraper import DELAY_BETWEEN_REQUESTS, fetch_page, robots_allowed

    stare_robots, motiv, crawl_delay = robots_allowed(url)
    pauza = max(DELAY_BETWEEN_REQUESTS, crawl_delay or 0)
    if stare_robots == "disallow":
        return [], "BLOCAT_ROBOTS", motiv, 0
    nota = motiv if stare_robots == "unknown_waf" else None

    pagina = fetch_page(url)
    if not pagina["ok"]:
        return [], "EROARE", pagina["error"], pauza

    soup = BeautifulSoup(pagina["html"], "lxml")
    titlu = soup.title.get_text(strip=True) if soup.title else None
    final = pagina["final_url"] or url
    categorie, produs, _dupa = clasifica(final, titlu)
    if not categorie:
        return [], "NECLASIFICAT", "nici calea URL, nici titlul nu spun ce produs e", pauza

    randuri = []
    nume = _nume_produs(soup, titlu)
    if nume:
        randuri.append(brut(
            banca=banca, sursa=url, rol_sursa=rol_sursa, frecventa_sursa="lunar",
            concept="nume_produs", produs=produs, valoare_text=nume, serviciu=nume,
            categorie=categorie, citat=titlu, incredere=0.8,
        ))

    vazute = set()
    for linie in _linii(soup):
        if "%" not in linie:
            continue
        inregistrari, _ = parseaza_linie(linie, banca, categorie, final, titlu)
        for r in inregistrari:
            cheie = (r.get("tip_rata"), r.get("valoare"), r.get("moneda"), r.get("perioada"))
            if cheie in vazute:
                continue
            vazute.add(cheie)
            randuri.append(brut(
                banca=banca, sursa=url, rol_sursa=rol_sursa, frecventa_sursa="zilnic",
                concept=r.get("tip_rata"), tip="rata",
                valoare=r.get("valoare"), moneda=r.get("moneda"),
                serviciu=nume or r.get("produs"), sectiune=categorie,
                frecventa=r.get("perioada"),
                categorie=categorie, perioada=r.get("perioada"),
                citat=r.get("text_sursa"), incredere=r.get("incredere"),
            ))

    stare = "OK" if randuri else "OK_GOL"
    if stare == "OK_GOL":
        nota = "pagină accesibilă, fără nume de produs sau procent lizibil (posibil randată prin JS)"
    return randuri, stare, nota, pauza


# ==========================================================================
# 4. PDF: comisioanele din documentele de tarife
# ==========================================================================

# Titlul formularului impus prin Legea 258/2017 (directiva UE 2014/92, PAD).
# Regula e a colegului, refolosită literal: se caută titlul în CONȚINUT, nu în
# numele fișierului, fiindcă numele minte des. Verificat pe documentul BCR de
# cont EUR: parserul de formular dă 25 de înregistrări cu secțiunea completată,
# iar cel de tarife nestandardizate dă 29, dintre care prima e un rând de
# glosar luat drept serviciu. Deci detecția nu e cosmetică: alege parserul care
# nu produce gunoi.
RE_TITLU_PAD = re.compile(
    r"document\w*\s+de\s+informare\s+cu\s+privire\s+la\s+comisioane"
    r"|document\w*\s+privind\s+comisioanele", re.I)


def _abrev(a):
    return rf"(?<![A-Za-z]){a}(?![A-Za-z])"


# Portat din scripts/unifica_comisioane.py: segmentul din NUMELE documentului.
# Fără el, lista PF și lista PJ a aceleiași bănci se unesc la deduplicare.
SEGMENTE = [
    ("pj", rf"{_abrev('PJ')}|persoane[_\s-]?juridice|juridice|legal[_\s-]?entities|corporate"),
    ("imm", rf"{_abrev('IMM')}|profesii[_\s-]?liberale|{_abrev('SME')}"),
    ("pfa", rf"{_abrev('PDAI')}|activit[ăa][țt]i[_\s-]?independente|{_abrev('PFA')}"),
    ("pf", rf"{_abrev('PF')}|persoane[_\s-]?fizice|fizice|private[_\s-]?individuals"),
]


def segment_din_nume(nume):
    for seg, tipar in SEGMENTE:
        if re.search(tipar, nume or "", re.I):
            return seg
    return None


def _parsere_pdf():
    """Tot ce ține de PDF din pachetul colegului, importat la cerere.

    Se iau patru module, nu două. Cele adăugate rezolvă probleme pe care nu le
    văzusem:

    `data_document` — de când e valabil documentul, citit din TEXTUL lui.
        Fără el, cele 15.230 de valori extrase de mine aveau `data_vigoare`
        NULL, deci nu puteau intra în detectarea schimbărilor: pagina Istoric
        rămânea la 18 schimbări, oricâte documente aș mai fi extras. Colegul
        explică și de ce nu ajunge `Last-Modified`: la multe origini e momentul
        umplerii cache-ului, nu al publicării.

    `ambiguitate` — mai multe valori diferite sub același serviciu, cu același
        tip, monedă și frecvență, și nimic care să le deosebească. Atunci s-a
        pierdut ceva la extragere, iar valorile rămân adevărate dar
        neatribuibile. Eu citeam flagul din JSON-ul lui, dar nu-l calculam pe
        documentele noi.
    """
    from crawler import ambiguitate, data_document, parser_pdf, parser_tarife, vocabular
    return parser_pdf, parser_tarife, vocabular, data_document, ambiguitate


# Documente publicate de bănci care NU sunt liste de prețuri. Măsurat pe
# 24.09.2026: rapoartele de transparență CreditCoop (Reg. 575) și situațiile
# financiare dădeau ~1.000 de „valori", buletinele Libra „Info-Economice" ~700 —
# procente de analiză economică sau prudențială, intrate în bază ca prețuri.
RE_NU_TARIF = re.compile(
    r"raport|cerinte[-_ ]transparenta|reg(ulament)?[-_ ]?575|situati\w*[-_ ]financiar"
    r"|info[-_ ]?economic|psd2|strategi|asigurar|\bKID\b|informatii[-_ ]esentiale"
    r"|prospect|audit|guvernanta|remunerar|pilon|pillar"
    # Vista, 24.09: documentația API PSD2 (`api-website-aisp`) dădea singură
    # 4.911 „valori"; la fel raportul de transparență și clasamentul MiFID al
    # locurilor de execuție.
    r"|(?<![a-z])api(?![a-z])|aisp|pisp|technical|transparen[tț]a[-_ ]si[-_ ]publicare"
    r"|ranking|execution[-_ ]venue|indici[-_ ]referinta",
    re.I)


# Pe titlu, doar formulări fără echivoc: „raport" sau „asigurare" apar și în
# titlul unui contract de servicii bancare sau al termenilor unui card, care pot
# conține comisioane reale.
RE_TITLU_NU_TARIF = re.compile(
    r"informa[țt]ii\s+esen[țt]iale|document\s+de\s+informare\s+privind\s+produsul\s+de\s+asigurare"
    r"|IPID|prospect|situa[țt]ii(le)?\s+financiare|raport(ul)?\s+anual|cerin[țt]e\s+de\s+transparen",
    re.I)


def document_fara_tarife(cale, sursa=None):
    """Motivul pentru care documentul nu e o listă de prețuri, sau None.

    Se uită la numele documentului și la începutul primei pagini (titlul);
    conținutul unui tarif conține oricum „raport" sau „asigurare" pe undeva,
    deci restul textului nu se citește.
    """
    nume = urllib.parse.unquote(os.path.basename(str(sursa or cale)))
    m = RE_NU_TARIF.search(nume)
    if m:
        return f"numele conține „{m.group(0)}”"
    try:
        import pdfplumber
        with pdfplumber.open(cale) as pdf:
            inceput = (pdf.pages[0].extract_text() or "")[:250] if pdf.pages else ""
    except Exception:
        return None
    m = RE_TITLU_NU_TARIF.search(inceput)
    return f"titlul conține „{m.group(0)}”" if m else None


def e_formular_standardizat(cale):
    """Titlul PAD apare în primele trei pagini?

    Se citește conținutul, nu numele. Un document numit „informare comisioane"
    poate fi altceva, iar unul numit oricum poate fi formularul.
    """
    import pdfplumber
    try:
        with pdfplumber.open(str(cale)) as pdf:
            text = "".join((p.extract_text() or "") for p in pdf.pages[:3])
    except Exception:
        return False
    return bool(RE_TITLU_PAD.search(text))


def din_pdf(cale, banca, sursa=None, amprenta=None):
    """Comisioanele dintr-un PDF de tarife, ca înregistrări brute.

    Alege între cele două parsere ale colegului după CE ESTE documentul:

      formular standardizat (Legea 258/2017) -> parser_pdf.extrage
          Terminologie impusă prin lege, identică la toate băncile. De-aia
          comparația între bănci are sens aici și nu are pe paginile web, unde
          fiecare bancă își numește serviciile altfel.

      listă de tarife nestandardizată       -> parser_tarife.extrage_tarife
          Geometrie liberă, deci parser separat. Mai zgomotos, dar singurul
          care citește documentele care nu urmează formularul.

    `sursa` e identificatorul care ajunge în baza de date. Se dă explicit (URL-ul
    public de la care s-a descărcat), nu se deduce din calea temporară: altfel
    sursa ar fi un nume de fișier din cache, care nu spune nimic nimănui.
    """
    parser_pdf, parser_tarife, vocabular, data_document, ambiguitate = _parsere_pdf()
    motiv = document_fara_tarife(cale, sursa)
    if motiv:
        return [], f"document fără tarife ({motiv}): nu se extrag prețuri"
    standardizat = e_formular_standardizat(cale)
    fn = parser_pdf.extrage if standardizat else parser_tarife.extrage_tarife
    try:
        inregistrari = fn(cale, banca)
    except Exception as exc:
        return [], f"parser {'PAD' if standardizat else 'tarife'} a eșuat: " \
                   f"{type(exc).__name__}: {exc}"[:200]

    # Data de vigoare, citită din TEXTUL documentului — o dată per document,
    # fiindcă e o proprietate a documentului, nu a valorii. Fără ea, valorile
    # extrase nu pot intra în detectarea schimbărilor: toate cele 15.230 pe
    # care le extrăsesem aveau `data_vigoare` NULL, deci pagina Istoric
    # rămânea blocată la schimbările din pachetul colegului.
    try:
        dd = data_document.data_documentului(cale) or {}
    except Exception:
        dd = {}
    data_vig, stare_dat = dd.get("data_vigoare"), dd.get("stare")

    # Ambiguitatea se calculează pe TOATE valorile documentului împreună:
    # semnalul e „mai multe valori diferite sub același serviciu, fără nimic
    # care să le deosebească", deci nu se poate decide privind un rând singur.
    #
    # `marcheaza` modifică lista PE LOC și întoarce (nr_valori, nr_grupuri) —
    # nu lista. Prima încercare a atribuit rezultatul înapoi în `inregistrari`
    # și a înlocuit lista cu un tuplu de numere.
    n_amb = 0
    try:
        n_amb, _ = ambiguitate.marcheaza(inregistrari)
    except Exception:
        pass

    brute, nemapate = [], 0
    seg_doc = segment_din_nume(sursa or str(cale))
    for c in inregistrari:
        if c.get("valoare") is None:
            continue
        # Maparea la vocabularul canonic. Parserele întorc denumirea băncii
        # („Comision de administrare cont curent lei"), nu conceptul — iar fără
        # concept valoarea ajunge în găleata generică `comision` și NU apare în
        # nicio comparație. Măsurat pe prima rulare la ING: 1.603 valori
        # extrase corect, toate invizibile pe 2.1 exact din motivul ăsta.
        #
        # Maparea e singurul pas din lanț care ține de judecată, nu de
        # geometrie — de aceea ce nu se potrivește rămâne `comision`, nu se
        # ghicește, iar denumirea originală se păstrează în `serviciu`.
        concept, canal, destinatie = vocabular.canonic(c)
        if concept is None:
            nemapate += 1
        c = dict(c, concept=concept or c.get("concept"),
                 canal=canal or c.get("canal"),
                 destinatie=destinatie or c.get("destinatie"))
        brute.append(brut(
            banca=banca, sursa=sursa or os.path.basename(str(cale)),
            tip_sursa="document", format="pdf", frecventa_sursa="lunar",
            amprenta=amprenta,
            concept=c.get("concept") or "comision", tip=c.get("tip"),
            rol=c.get("rol"),
            valoare=c.get("valoare"), moneda=c.get("moneda"),
            serviciu=c.get("serviciu"), sectiune=c.get("sectiune"),
            conditie=c.get("conditie"), frecventa=c.get("frecventa"),
            detaliu=c.get("detaliu"), pagina=c.get("pagina"),
            segment=c.get("segment") or seg_doc, canal=c.get("canal"),
            destinatie=c.get("destinatie"), coloana=c.get("coloana"),
            categorie=c.get("categorie"),
            citat=c.get("text_sursa"),
            # Data de vigoare vine din TEXTUL documentului. Fără ea, valoarea
            # nu poate intra în detectarea schimbărilor — iar toate cele 15.230
            # de valori extrase de mine aveau `data_vigoare` NULL.
            data_vigoare=c.get("data_vigoare") or data_vig,
            stare_data=c.get("stare_data") or stare_dat,
            # Formularul standardizat merită mai multă încredere decât o listă
            # liberă: secțiunile și terminologia sunt impuse, deci parserul are
            # pe ce să se sprijine.
            incredere=0.9 if standardizat else 0.7,
            ambiguu=c.get("ambiguu"), motiv_ambiguu=c.get("motiv_ambiguu"),
            produs="comisioane",
        ))
    eticheta = "formular standardizat (PAD)" if standardizat else "listă de tarife"
    mapate = len(brute) - nemapate
    datat = f", datat {data_vig}" if data_vig else ", nedatat"
    amb = f", {n_amb} ambigue" if n_amb else ""
    return brute, (f"{eticheta}: {len(brute)} valori, {mapate} mapate"
                   f"{datat}{amb}")


# ==========================================================================
# 5. HTML live: dobânzi + nume de produs, din octeții aduși de flux
# ==========================================================================

def din_html(octeti, url, slug, rol=None):
    """Dobânzi + nume de produs din HTML, cu parserul propriu și al colegului."""
    from bs4 import BeautifulSoup
    from crawler.parser_rate import parseaza_linie

    # Octeți, nu text: BeautifulSoup citește charset-ul din <meta>. Decodarea
    # forțată în UTF-8 strica diacriticele paginilor servite în windows-1250.
    soup = BeautifulSoup(octeti, "lxml")
    titlu = soup.title.get_text(strip=True) if soup.title else None
    if RE_PAGINA_PRESA.search(url):
        return [], "pagină de presă/știri: prețurile din comunicate nu sunt oferta paginii"
    categorie, produs, _ = clasifica(url, titlu)
    if not categorie:
        return [], "nici calea URL, nici titlul nu spun ce produs e"

    brute = []
    nume = _nume_produs(soup, titlu)
    if nume:
        # Citatul e numele însuși când apare în pagină (h1), nu <title>: titlul
        # tab-ului nu e în conținut, deci evidențierea la click nu-l găsea
        # (409 din 604 nume de produs, 24.09).
        brute.append(brut(
            banca=slug, sursa=url, rol_sursa=rol or "produs",
            concept="nume_produs", produs=produs, valoare_text=nume,
            serviciu=nume, categorie=categorie,
            citat=nume if soup.find("h1") else titlu, incredere=0.8,
        ))

    vazute = set()
    # Liniile se iau DOAR din conținutul principal. Măsurat pe 23.09: 201 din
    # 643 de citate de dobânzi (31%) veneau din meniu, antet sau subsol (ex.
    # bannerul ING „4,79%/an" din meniu), atribuite paginii curente — iar
    # cine deschidea pagina nu găsea citatul în conținut.
    for linie in _linii(_continut_principal(octeti)):
        if "%" not in linie:
            continue
        inreg, problema = parseaza_linie(linie, slug, categorie, url, titlu)
        if problema and not inreg:
            # candidat pentru rezerva LLM (llm_rezerva.py), nu aruncat
            PROBLEME.setdefault(url, []).append(linie)
        for r in inreg:
            k = (r.get("tip_rata"), r.get("valoare"), r.get("moneda"),
                 r.get("perioada"))
            if k in vazute:
                continue
            vazute.add(k)
            brute.append(brut(
                banca=slug, sursa=url, rol_sursa=rol or "produs",
                frecventa_sursa="zilnic", concept=r.get("tip_rata"), tip="rata",
                valoare=r.get("valoare"), moneda=r.get("moneda"),
                serviciu=nume or r.get("produs"), sectiune=categorie,
                frecventa=r.get("perioada"), categorie=categorie,
                perioada=r.get("perioada"), citat=r.get("text_sursa"),
                incredere=r.get("incredere"),
                # dicționarul parserului, pentru validator (validare.py)
                _rec=r,
            ))
    return brute, f"HTML: {len(brute)} valori"


# ==========================================================================
# 6. Locatoare: sucursale și ATM-uri, din pagina de rețea a băncii
# ==========================================================================

RE_OBIECT_JSON = re.compile(
    r"\{[^{}]*?(?:\"lat(?:itude)?\"|\"lng\"|\"lon(?:gitude)?\")[^{}]*\}", re.S)
CHEI_LAT, CHEI_LON = ("lat", "latitude"), ("lng", "lon", "longitude")
CHEI_NUME = ("name", "nume", "title", "denumire")
CHEI_ADRESA = ("address", "adresa", "street")
CHEI_PROGRAM = ("schedule", "program", "hours", "orar", "opening_hours")


def _in_romania(lat, lon):
    return 43.6 <= lat <= 48.3 and 20.2 <= lon <= 29.8


# ATM-uri ale altei rețele, afișate de bancă pentru clienții ei (Patria:
# 617 ATM-uri Euronet în locatorul propriu). Nu sunt rețeaua băncii.
RE_PARTENER = re.compile(r"euronet|partener|parteneri|bancomat\s+partener", re.I)


def _tip_locatie(text):
    # Agenția întâi: Patria marchează agențiile „agency,atm" (au și ATM), iar
    # regula veche le trecea pe toate 45 drept ATM-uri.
    if re.search(r"agenc|agenti|branch|sucursal|filial", text or "", re.I):
        return "sucursala"
    return "atm" if re.search(r"\batm\b|bancomat", text or "", re.I) else "sucursala"


def _primul(d, chei):
    for k in chei:
        if d.get(k) not in (None, ""):
            return d[k]
    return None


def din_locator(octeti, url, slug):
    """Coordonate din JSON-ul inclus în pagină sau din atribute `data-lat`.

    Locatorul băncii e sursa oficială a rețelei: are și programul, pe care
    Overture nu-l are. Punctele din afara României se aruncă: unele locatoare
    listează și rețeaua grupului din alte țări.
    """
    import json
    from bs4 import BeautifulSoup
    text = octeti.decode("utf-8", errors="replace")
    puncte = []
    for m in RE_OBIECT_JSON.finditer(text):
        try:
            d = json.loads(m.group(0))
            lat, lon = float(_primul(d, CHEI_LAT)), float(_primul(d, CHEI_LON))
        except (ValueError, TypeError):
            continue
        tip = _tip_locatie(" ".join(str(d.get(k, "")) for k in ("type", "tip", "category", "name")))
        puncte.append({"tip": tip, "nume": _primul(d, CHEI_NUME), "adresa": _primul(d, CHEI_ADRESA),
                       "lat": lat, "lon": lon, "program": _primul(d, CHEI_PROGRAM)})
    for el in BeautifulSoup(octeti, "lxml").select("[data-lat]"):
        try:
            lat = float(el["data-lat"])
            lon = float(el.get("data-lng") or el.get("data-lon"))
        except (ValueError, TypeError):
            continue
        eticheta = " ".join(el.get("class", [])) + " " + el.get_text(" ", strip=True)
        puncte.append({"tip": _tip_locatie(eticheta), "nume": el.get_text(" ", strip=True)[:120] or None,
                       "adresa": None, "lat": lat, "lon": lon, "program": None})
    unice = {}
    for p in puncte:
        if _in_romania(p["lat"], p["lon"]):
            p.update(banca=slug, sursa=url, _locatie=True,
                     retea="partener" if RE_PARTENER.search(p.get("nume") or "") else "proprie")
            unice.setdefault((p["tip"], round(p["lat"], 6), round(p["lon"], 6)), p)
    return list(unice.values()), f"locator: {len(unice)} puncte"
