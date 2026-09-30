"""Extracția deterministă a câmpurilor unei campanii, dintr-un document.

Fără LLM (decizia din 29.09, calea c din §9.6 a lui Nicolae): ce nu se
citește sigur din text rămâne gol și ajunge „de verificat", nu se ghicește.
Funcții pure: primesc octeți sau text, întorc valori cu citatul lor. Nu știu
de baza de date și nu fac cereri (regula extractoarelor din CLAUDE.md).

Textul (§5.2): `ingest/sanitizare.py` rămâne neatins, fiindcă din el se
calculează amprenta prețurilor. Aici se păstrează orele și datele ISO (pe
sanitizare, `RE_ORA` tăia „ora 00:00:01" în 10 citate de perioadă), iar
meta description intră separat, cu sursa ei.
"""

import datetime
import json
import re
import unicodedata
from urllib.parse import unquote, urljoin, urlparse

# ==========================================================================
# Text
# ==========================================================================

# Ca la sanitizare.ZGOMOT, fără `header` (păstrat în <main>/<article>, unde
# stă titlul campaniei) și fără `form`/`button` (bannerele de campanie sunt
# des butoane cu textul ofertei).
ZGOMOT = ["script", "style", "noscript", "nav", "footer", "svg", "iframe"]
# Sub atâtea caractere, un PDF e scanat: pe testul lui Nicolae, 35 de PDF-uri
# distincte fără strat de text, dintre care 3 cu campanii active (§5.5).
TEXT_MINIM_PDF = 50
PAGINI_PDF_MAX = 40


def _fara_diacritice_1la1(text):
    """Litere mici, fără diacritice, cu ACEEAȘI lungime ca originalul, ca
    pozițiile găsite pe textul normalizat să taie citatul din original."""
    iesire = []
    for c in text:
        baza = "".join(x for x in unicodedata.normalize("NFKD", c) if not unicodedata.combining(x))
        iesire.append(baza.lower() if len(baza) == 1 else c.lower()[:1] or c)
    t = "".join(iesire)
    return t.translate(str.maketrans("–—‒−", "----"))


def colapseaza(text):
    return re.sub(r"\s+", " ", (text or "").replace("\xa0", " ")).strip()


def text_html(octeti):
    """(text, meta) pentru o pagină HTML. `meta` are og:title, og:description,
    description, title, h1 — fiecare cu sursa ei, nu amestecate în text."""
    from bs4 import BeautifulSoup
    from sanitizare import radacina_continut
    soup = BeautifulSoup(octeti, "lxml")
    meta = {}
    for m in soup.find_all("meta"):
        cheie = (m.get("property") or m.get("name") or "").lower()
        if cheie in ("og:title", "og:description", "description") and m.get("content"):
            meta.setdefault(cheie, colapseaza(m["content"]))
    if soup.title and soup.title.get_text(strip=True):
        meta["title"] = colapseaza(soup.title.get_text(" ", strip=True))
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        meta["h1"] = colapseaza(h1.get_text(" ", strip=True))
    for tag in soup.find_all(ZGOMOT):
        tag.decompose()
    for tag in soup.find_all("header"):
        if not tag.find_parent(["main", "article"]):
            tag.decompose()
    text = colapseaza(radacina_continut(soup).get_text(" ", strip=True))
    return text, meta


def text_pdf(cale):
    """(text, pagini): textul cu numărul paginii păstrat — o citare dintr-un
    regulament de 12 pagini trebuie să poată fi găsită de om."""
    import pdfplumber
    pagini = []
    with pdfplumber.open(cale) as pdf:
        for i, pg in enumerate(pdf.pages[:PAGINI_PDF_MAX], 1):
            pagini.append((i, colapseaza(pg.extract_text() or "")))
    return " ".join(t for _, t in pagini if t), pagini


def text_document(octeti, cale=None):
    """Formatul din PRIMII OCTEȚI, nu din extensie (regula din artefact)."""
    if octeti.startswith(b"%PDF"):
        if cale is None:
            import io
            cale = io.BytesIO(octeti)
        text, pagini = text_pdf(cale)
        return {"format": "pdf", "text": text, "meta": {}, "pagini": pagini,
                "fara_text": len(text) < TEXT_MINIM_PDF}
    text, meta = text_html(octeti)
    return {"format": "html", "text": text, "meta": meta, "pagini": None,
            "fara_text": len(text) < TEXT_MINIM_PDF}


# ==========================================================================
# Legăturile unei pagini, inclusiv cele din JSON-ul declarat în pagină
# ==========================================================================

# Tema Erste (GEM, BCR și BCR Locuințe) ține legăturile în
# <script type="application/gem+json">, nu în <a>: pe BCR, scriptul generic
# de hub dădea 5 candidați în loc de 260, fără nicio eroare (§4.1).
CHEI_LINK = ("link", "linkpath", "url", "href", "path", "target", "linkurl")
CHEI_ETICHETA = ("label", "title", "text", "name", "linktext", "headline", "description")


def _din_json(nod, iesire):
    if isinstance(nod, dict):
        eticheta = next((str(nod[k]) for k in nod if k.lower() in CHEI_ETICHETA
                         and isinstance(nod[k], str) and nod[k].strip()), "")
        for k, v in nod.items():
            if k.lower() in CHEI_LINK and isinstance(v, str) and v.startswith(("/", "http")):
                iesire.append((v, eticheta))
            else:
                _din_json(v, iesire)
    elif isinstance(nod, list):
        for x in nod:
            _din_json(x, iesire)


def linkuri(octeti, url_baza, doar_continut=False):
    """[(url, text)] fără fragment, în ordinea din pagină, fără dubluri.
    `doar_continut`: fără meniu și subsol (paginile de segment, unde meniul
    ar aduce toate produsele băncii)."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(octeti, "lxml")
    brute = []
    for s in soup.find_all("script", type=re.compile(r"json", re.I)):
        try:
            _din_json(json.loads(s.string or s.get_text() or ""), brute)
        except ValueError:
            continue
    if doar_continut:
        for tag in soup.find_all(["nav", "footer", "header"]):
            tag.decompose()
    for a in soup.find_all(["a", "area"], href=True):
        brute.append((a["href"], colapseaza(a.get_text(" ", strip=True)) or a.get("title", "")))
    iesire, vazute = [], {}
    for href, text in brute:
        href = href.strip()
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        u = urljoin(url_baza, href).split("#")[0]
        if not u.startswith("http"):
            continue
        if u in vazute:
            # același URL cu mai multe texte: rămâne cel mai lung („Află mai
            # multe" e mai puțin util decât titlul campaniei)
            if len(text) > len(iesire[vazute[u]][1]):
                iesire[vazute[u]] = (u, text)
            continue
        vazute[u] = len(iesire)
        iesire.append((u, text))
    return iesire


# ==========================================================================
# Perioada
# ==========================================================================

LUNI = {"ianuarie": 1, "ian": 1, "februarie": 2, "feb": 2, "martie": 3, "aprilie": 4,
        "apr": 4, "mai": 5, "iunie": 6, "iun": 6, "iulie": 7, "iul": 7, "august": 8,
        "aug": 8, "septembrie": 9, "sept": 9, "octombrie": 10, "oct": 10,
        "noiembrie": 11, "nov": 11, "decembrie": 12, "dec": 12}
# Fără „mar", „sep", „noi": „noi" e și cuvânt („2 noi produse").
RE_LUNA = "(" + "|".join(sorted(LUNI, key=len, reverse=True)) + r")\b\.?"

# Datele, pe textul normalizat (litere mici, fără diacritice, liniuțe → „-").
RE_DATA_NUM = re.compile(r"(?<![\d.,/])(\d{1,2})([./-])(\d{1,2})\2(\d{4})(?!\d)")
# Zi.lună fără an doar cu câte DOUĂ cifre („09.07"): „8.1 și 8.2 de mai sus" din
# regulamentul BCR Depozitul Promo erau numere de articol, citite ca interval.
RE_DATA_ZL = re.compile(r"(?<![\d.,/])(\d{2})\.(\d{2})(?![\d]|[.,/]\d)")
RE_DATA_TXT = re.compile(r"(?<![\d.,])(\d{1,2})\s+" + RE_LUNA + r"(?:\s+(\d{4})(?!\d))?")
# „1 - 31 august 2026", „14-16 august", „01-08 martie": doar ziua, înaintea
# unei date cu luna
RE_DOAR_ZI = re.compile(r"(?<![\d.,])(\d{1,2})\s*(?:-|si|și)\s*(?=\d{1,2}(?:\s+[a-z]|\.\d))")
# Ce poate sta ÎNTRE capetele unui interval
RE_SEPARATOR = re.compile(
    r"^\s*(?:-|pana\s+(?:la|in|pe)|si(?:\s+pana\s+(?:la|in))?|la)\s*"
    r"(?:data\s+de\s*)?(?:ora\s+\d{1,2}[:.]\d{2}(?:[:.]\d{2})?\s*)?$")
# Ce poate sta după primul capăt, înainte de separator („01.07.2026 ora 00:00 –")
# Fără „^": se aplică cu .match(text, poziție), iar acolo „^" nu se potrivește
# (BCR Depozitul Promo, „15.09.2026 ora 00:00 AM – 31.12.2026", se pierdea).
RE_DUPA_CAPAT = re.compile(r"\s*(?:,?\s*ora\s+\d{1,2}[:.]\d{2}(?:[:.]\d{2})?(?:\s*[ap]m)?"
                           r"(?:,?\s*ora\s+romaniei)?|\(inclusiv\))?")
# Cuvintele care ancorează o dată de campanie. O dată fără ancoră (numărul
# unui contract, data împuternicirii din antetul regulamentului TBI) nu e
# perioada campaniei.
RE_ANCORA = re.compile(
    r"perioad|desfasoar|deruleaz|valabil|durata|intre|intervalul|incepand|campani|promoti"
    r"|oferta|editia|concurs|tombol|participa")
FEREASTRA_ANCORA = 120
RE_PANA_LA = re.compile(r"(?:pana\s+(?:la|in|pe)|valabil[aă]?\s+pana\s+(?:la|in|pe))\s+(?:data\s+de\s+)?$")
RE_INCEPAND = re.compile(r"incepand\s+(?:cu|din)\s+(?:data\s+de\s+)?$")
RE_EXEMPLU = re.compile(r"exemplu|reprezentativ")
# Un act adițional EXISTENT, nu posibilitatea lui: aproape orice regulament
# spune „modificarea duratei se face prin act adițional" (BRD, 2024), iar cu
# forma scurtă aproape toate campaniile ajungeau „de verificat".
RE_ACT_ADITIONAL = re.compile(
    # „se va încheia un act adițional la regulament" (BRD) e doar posibilitatea;
    # „actul adițional la regulament" sau antetul „ACT ADIȚIONAL" e actul însuși
    r"\bact(?:ul)?\s+aditional(?:ul)?\s+(?:nr\.?|numarul|no\.?)\s*\d|\bactul\s+aditional\s+la\s+regulament"
    r"|^\s*act\s+aditional"
    r"|\bse\s+prelunge(?:ste|sc)\b|\bprelungirea\s+(?:campaniei|perioadei|duratei|programului)|\baddendum\b")
RE_NEDETERMINAT = re.compile(
    r"perioad[ae]\s+nedeterminat|durat[ae]\s+nedeterminat|pana\s+la\s+(?:noi\s+dispozitii|incetarea|modificarea)")
MAX_ZILE_FEREASTRA = 3 * 366


def _data(an, luna, zi):
    try:
        if not 2000 <= an <= 2100:
            return None
        return datetime.date(an, luna, zi)
    except ValueError:
        return None


def _capete(norm):
    """Toate datele din text, cu pozițiile lor: (start, end, an|None, luna, zi)."""
    gasite = []
    for m in RE_DATA_NUM.finditer(norm):
        gasite.append((m.start(), m.end(), int(m.group(4)), int(m.group(3)), int(m.group(1))))
    ocupat = [(a, b) for a, b, *_ in gasite]

    def liber(a, b):
        return not any(a < y and x < b for x, y in ocupat)

    for m in RE_DATA_TXT.finditer(norm):
        if liber(m.start(), m.end()):
            an = int(m.group(3)) if m.group(3) else None
            gasite.append((m.start(), m.end(), an, LUNI[m.group(2)], int(m.group(1))))
            ocupat.append((m.start(), m.end()))
    for m in RE_DATA_ZL.finditer(norm):
        if liber(m.start(), m.end()) and 1 <= int(m.group(2)) <= 12:
            gasite.append((m.start(), m.end(), None, int(m.group(2)), int(m.group(1))))
            ocupat.append((m.start(), m.end()))
    for m in RE_DOAR_ZI.finditer(norm):
        if liber(m.start(1), m.end(1)):
            gasite.append((m.start(1), m.end(1), None, None, int(m.group(1))))
            ocupat.append((m.start(1), m.end(1)))
    return sorted(gasite)


def _completeaza(a, b, an_implicit):
    """Capetele unui interval, cu anul și luna luate de la capătul complet:
    „21 septembrie – 31 decembrie 2026", „1 - 31 august 2026"."""
    (_, _, an_a, luna_a, zi_a), (_, _, an_b, luna_b, zi_b) = a, b
    an_dedus = False
    if an_b is None:
        if an_implicit is None:
            return None, None, False
        an_b, an_dedus = an_implicit, True
    if luna_a is None:
        luna_a = luna_b
    if luna_b is None:
        return None, None, an_dedus
    if an_a is None:
        an_a = an_b if (luna_a, zi_a) <= (luna_b, zi_b) else an_b - 1
    return _data(an_a, luna_a, zi_a), _data(an_b, luna_b, zi_b), an_dedus


def _ancorat(norm, poz):
    return bool(RE_ANCORA.search(norm[max(0, poz - FEREASTRA_ANCORA):poz + 20]))


def _citat(orig, a, b, margine=60):
    """Fraza din jurul datelor, tăiată la margini de propoziție când se poate."""
    st = max(0, a - margine)
    dr = min(len(orig), b + margine)
    punct = orig.rfind(". ", st, a)
    if punct != -1:
        st = punct + 2
    punct = orig.find(". ", b, dr)
    if punct != -1:
        dr = punct + 1
    return orig[st:dr].strip()


def perioada(text, an_implicit=None, eticheta=False):
    """Perioada campaniei, cu citatul exact; None dacă nu există una clară.

    Întoarce {start, sfarsit, citat, ancorata, an_dedus, o_singura_zi}.
    `eticheta`: textul scurt al unui link de pe hub („Cursa Plăților 50 lei –
    15-17 Octombrie 2025"): acolo nu e nevoie de ancoră, iar o singură dată e
    ziua campaniei (se marchează, fiindcă poate fi și data publicării).
    `an_implicit`: anul din calea documentului (/2026/08/), pentru capete fără
    an („09.07-30.09"); se marchează `an_dedus`, deci ajunge „de verificat".
    """
    orig = colapseaza(text)
    norm = _fara_diacritice_1la1(orig)
    capete = _capete(norm)
    intervale = []
    for i in range(len(capete) - 1):
        a, b = capete[i], capete[i + 1]
        dupa = RE_DUPA_CAPAT.match(norm, a[1])
        mijloc = norm[dupa.end() if dupa else a[1]:b[0]]
        if not RE_SEPARATOR.match(mijloc):
            continue
        if b[3] is None:          # capătul al doilea e doar o zi: nu e interval
            continue
        start, sfarsit, an_dedus = _completeaza(a, b, an_implicit)
        if not start or not sfarsit:
            continue
        intervale.append({"start": start, "sfarsit": sfarsit,
                          "citat": _citat(orig, a[0], b[1]),
                          "ancorata": eticheta or _ancorat(norm, a[0]),
                          "an_dedus": an_dedus, "o_singura_zi": False, "_poz": a[0]})
    bune = [x for x in intervale if x["start"] <= x["sfarsit"]]
    for x in sorted(bune, key=lambda x: (not x["ancorata"], x["_poz"])):
        x.pop("_poz")
        return x
    # doar sfârșitul („valabilă până la 30.09.2026"), eventual cu un început
    # separat („începând cu 01.07.2026")
    sfarsit = start = None
    for c in capete:
        if c[2] is None or c[3] is None:
            continue
        inainte = norm[max(0, c[0] - 40):c[0]]
        # „Exemplul este valabil până la 31.07.2026" (ING, pagina contului):
        # termenul exemplului de calcul, nu al ofertei
        exemplu = RE_EXEMPLU.search(norm[max(0, c[0] - FEREASTRA_ANCORA):c[0]])
        if sfarsit is None and RE_PANA_LA.search(inainte) and _ancorat(norm, c[0]) and not exemplu:
            sfarsit = (c, _data(c[2], c[3], c[4]))
        if start is None and RE_INCEPAND.search(inainte):
            start = (c, _data(c[2], c[3], c[4]))
    if sfarsit and sfarsit[1]:
        # începutul contează doar în aceeași frază, înaintea sfârșitului (la
        # eMAG Raiffeisen, „începând cu 01.11.2023" stătea în alt articol)
        st = start[1] if (start and start[1] and start[1] <= sfarsit[1]
                          and 0 < sfarsit[0][0] - start[0][0] < 300) else None
        a = start[0][0] if st else sfarsit[0][0]
        return {"start": st, "sfarsit": sfarsit[1], "citat": _citat(orig, a, sfarsit[0][1]),
                "ancorata": True, "an_dedus": False, "o_singura_zi": False}
    if eticheta:
        complete = [c for c in capete if c[2] is not None and c[3] is not None]
        if len(complete) == 1:
            c = complete[0]
            zi = _data(c[2], c[3], c[4])
            if zi:
                return {"start": zi, "sfarsit": zi, "citat": _citat(orig, c[0], c[1]),
                        "ancorata": True, "an_dedus": False, "o_singura_zi": True}
    return None


def an_din_url(url):
    """Anul din calea documentului (/wp-content/uploads/2026/08/, /2026/iulie/)."""
    ani = re.findall(r"/(20\d{2})/", urlparse(url).path)
    return int(ani[-1]) if ani else None


def perioada_din_url(url):
    """Perioada din numele fișierului („Regulament ... Youth 07.09-30.11.2026.pdf")."""
    cale = unquote(unquote(urlparse(url).path))
    nume = cale.rsplit("/", 1)[-1]
    nume = re.sub(r"\.(pdf|html?)$", "", nume, flags=re.I).replace("_", " ")
    return perioada(nume, an_implicit=an_din_url(url), eticheta=True)


def datele_complete(text):
    """Toate datele cu an din text (pentru treapta B)."""
    norm = _fara_diacritice_1la1(colapseaza(text))
    return [d for d in (_data(an, luna, zi) for _, _, an, luna, zi in _capete(norm)
                        if an is not None and luna is not None) if d]


def e_nedeterminata(text):
    m = RE_NEDETERMINAT.search(_fara_diacritice_1la1(colapseaza(text)))
    return m.group(0) if m else None


# „În cazul în care Organizatorul va decide prelungirea duratei..." (BRD, 2024):
# condiția, nu prelungirea
RE_CONDITIONAL = re.compile(r"in\s+cazul\s+in\s+care|va\s+decide|poate\s+decide|isi\s+rezerva|\bdaca\b")


def are_act_aditional(text):
    norm = _fara_diacritice_1la1(colapseaza(text or ""))
    return any(not RE_CONDITIONAL.search(norm[max(0, m.start() - 80):m.start()])
               for m in RE_ACT_ADITIONAL.finditer(norm))


# ==========================================================================
# Titlu, beneficiu, segment, organizator
# ==========================================================================

RE_SUFIX_TITLU = re.compile(r"\s+[|–-]\s+[^|–-]{2,60}$")
RE_GHILIMELE = re.compile(r"[„\"“«]\s*([^„\"“”«»]{5,160}?)\s*[”\"“»]")


def titlu_html(meta):
    for cheie in ("og:title", "h1", "title"):
        t = meta.get(cheie)
        if t and len(t) > 3:
            # „Campanie Bankata - Credit Imobiliar - ProCredit Bank": sufixul
            # cu numele site-ului pleacă, restul rămâne
            curat = RE_SUFIX_TITLU.sub("", t) if cheie != "h1" else t
            return (curat or t)[:200]
    return None


def titlu_pdf(text):
    """Numele campaniei din regulament: primul text între ghilimele din
    antet („Deschide Pachetul de cont curent Premium si poti castiga...")."""
    antet = colapseaza(text)[:600]
    for m in RE_GHILIMELE.finditer(antet):
        # „Organizatorul", „Programul": definiții, nu numele campaniei
        if " " in m.group(1).strip():
            return m.group(1).strip()[:200]
    return None


def titlu_din_url(url):
    nume = unquote(unquote(urlparse(url).path)).rstrip("/").rsplit("/", 1)[-1]
    nume = re.sub(r"\.(pdf|html?)$", "", nume, flags=re.I)
    nume = re.sub(r"^[0-9a-f]{8}_|^\d{8}-", "", nume)
    t = re.sub(r"[-_]+", " ", nume).strip()
    return t[:200] or None


RE_BENEFICIU = re.compile(
    r"cashback|bonus|premi(?:u|ul|i|ile|aza)\b|castig|reducer|discount|gratuit|gratis"
    r"|fara\s+comision|zero\s+comision|0\s*comision|comision\s+0|fara\s+dobanda|dobanda\s+0"
    r"|dobanda\s+(?:promotional|preferential|redus|fixa|de\s+\d)|voucher|cadou|puncte"
    r"|rambursa|scutir|primesti|beneficiez|oferim|0\s*%")
RE_SUMA = re.compile(r"\d[\d.,]*\s*(?:lei|ron|eur|euro|usd|%)|\d+\s*rate|gratuit|fara\s+comision"
                     r"|fara\s+dobanda|zero\s+comision")
# Nu e beneficiu: antetul oricărui regulament (capital social, sediu), clauza
# „regulamentul e disponibil gratuit oricărui solicitant" (ieșea ea la 11 din
# 103 documente de campanie din Bronze, 29.09) și exemplul reprezentativ.
RE_NU_BENEFICIU = re.compile(
    r"capital\s+social|sediul|registrul|cod\s+unic|cui\b|impozit|disponibil\w*\s+(?:\w+\s+){0,6}gratuit"
    r"|gratuit\w*\s+oricarui|informatii\s+gratuit|exemplu\w*\s+reprezentativ|\bdae\b"
    r"|caracter\s+personal|copie\s+a\s+datelor")
LUNGIME_BENEFICIU = 300


def _fraze(text):
    for f in re.split(r"(?<=[.!?])\s+|\s+[•·▪✓✔]\S*\s+|\s+\*\s+", colapseaza(text)):
        if 12 <= len(f) <= 600:
            yield f


def beneficiu(text, meta=None, eticheta=None):
    """Prima frază care numește un beneficiu ȘI o valoare (sumă, procent,
    „gratuit"), cu fraza însăși drept citat. Ordinea: descrierea paginii,
    titlul, eticheta linkului, apoi textul."""
    meta = meta or {}
    for f in [meta.get("og:description"), meta.get("description"), meta.get("h1"),
              meta.get("og:title"), eticheta] + list(_fraze(text or "")):
        if not f:
            continue
        n = _fara_diacritice_1la1(f)
        if RE_BENEFICIU.search(n) and RE_SUMA.search(n) and not RE_NU_BENEFICIU.search(n):
            return f[:LUNGIME_BENEFICIU]
    return None


RE_PJ = re.compile(r"companii|/imm|imm-|business|persoane-juridice|juridice|/pj\b|/pj[-/]|[-_]pj\b"
                   r"|corporate|/sme\b|antreprenor|/firme|microintreprinder|pfa\b")
RE_PF = re.compile(r"persoane-fizice|/pf\b|/pf[-/]|[-_]pf\b|individuals|/retail/|fizice")


def segment(url, titlu=None):
    """PF/PJ din calea URL-ului (acord 99,2% cu referința, §5.3), apoi din
    titlu; altfel None — nu se deduce din textul regulamentului."""
    for sursa in (unquote(urlparse(url).path).lower(), _fara_diacritice_1la1(titlu or "")):
        pj, pf = bool(RE_PJ.search(sursa)), bool(RE_PF.search(sursa))
        if pj != pf:
            return "PJ" if pj else "PF"
    return None


RE_ORGANIZATOR = re.compile(r"organizat(?:a|or(?:ul|ii|ul\s+campaniei)?|ori(?:i)?)\b|organizata\s+de")
RE_SCHEMA_CARD = re.compile(r"mastercard|\bvisa\b")
RE_FORMA_JURIDICA = re.compile(r"\b(?:s\.?\s?a\.?|s\.?r\.?l\.?|ifn|ltd|gmbh|n\.v\.|ead|plc)(?![a-z])")
FEREASTRA_ORGANIZATOR = 300


RE_TEXT_GHILIMELE = re.compile(r"[„\"“«][^„\"“”«»]{0,200}[”\"“»]")


def organizator(text, nume_banca=(), nume_grup=()):
    """(categorie, citat) după prima mențiune „organizator" din antet.

    Organizatorul e prima entitate cu formă juridică după cuvânt („... este
    Raiffeisen Bank S.A."); numele campaniei dintre ghilimele nu contează:
    „Câștigă cu cardul tău Mastercard Business de la BRD" e organizată de BRD,
    nu de Mastercard. Fără formă juridică, câștigă prima entitate numită; la
    aceeași poziție, cea mai lungă („BCR Social Finance" e grup, nu BCR).
    Fără nicio mențiune: (None, None) — colectorul pune 'banca', fiindcă
    pagina e pe site-ul băncii și nu numește alt organizator.
    """
    orig = colapseaza(text)[:4000]
    norm = _fara_diacritice_1la1(orig)
    m = RE_ORGANIZATOR.search(norm)
    if not m:
        return None, None
    a, b = m.start(), min(len(norm), m.end() + FEREASTRA_ORGANIZATOR)
    # ghilimelele se înlocuiesc cu spații: pozițiile rămân aceleași
    fereastra = RE_TEXT_GHILIMELE.sub(lambda x: " " * len(x.group(0)), norm[m.end():b])
    f = RE_FORMA_JURIDICA.search(fereastra)
    if f:
        fereastra = fereastra[:f.end()]
    candidati = []
    for categorie, tipare in (("grup", nume_grup), ("banca", nume_banca)):
        for t in tipare:
            for x in re.finditer(t, fereastra):
                candidati.append((x.start(), -(x.end() - x.start()), categorie, x.end()))
    for x in RE_SCHEMA_CARD.finditer(fereastra):
        candidati.append((x.start(), -(x.end() - x.start()), "schema_card", x.end()))
    if candidati:
        _poz, _, categorie, sf = min(candidati)
        return categorie, orig[a:m.end() + max(sf, f.end() if f else 0)].strip()
    if f:
        return "partener", orig[a:m.end() + f.end()].strip()
    return None, None


RE_ZI_URL = re.compile(r"/(20\d{2})/(\d{1,2})/(\d{1,2})(?:/|$)")
RE_ZI_URL_LIPIT = re.compile(r"(?<!\d)(20\d{2})[-_.]?(\d{2})[-_.]?(\d{2})(?!\d)")


def data_din_url(url):
    """Data comunicatului din URL: /2026/09/25/ (WordPress, BCR), sau
    20260921-... (regulamentele Raiffeisen)."""
    cale = urlparse(url).path
    m = RE_ZI_URL.search(cale)
    if m:
        return _data(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = RE_ZI_URL_LIPIT.search(cale.rsplit("/", 1)[-1])
    if m:
        return _data(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def data_din_text(text):
    """Prima dată completă dintr-un text scurt (elementul unei liste de știri)."""
    d = datele_complete(text or "")
    return d[0] if d else None


# ==========================================================================
# Un document, cap-coadă: înregistrarea brută
# ==========================================================================

def document(octeti, url, cale=None, nume_banca=(), nume_grup=()):
    """Câmpurile brute ale unui document de campanie (pagină sau regulament).
    Nimic nu se decide aici: ce document câștigă și ce stare are campania
    decide `normalizeaza_campanii.campanie`."""
    t = text_document(octeti, cale)
    text, meta = t["text"], t["meta"]
    if t["format"] == "html":
        titlu = titlu_html(meta)
    else:
        titlu = titlu_pdf(text)
    date = datele_complete(text)
    org = organizator(text, nume_banca, nume_grup) if not t["fara_text"] else (None, None)
    return {
        "format": t["format"],
        "fara_text": t["fara_text"],
        "titlu": titlu,
        "perioada": None if t["fara_text"] else perioada(text, an_implicit=an_din_url(url)),
        # la regulament, numele campaniei spune des beneficiul („... și poți
        # câștiga un premiu în valoare de 5.000 lei")
        "beneficiu": beneficiu(text, meta if t["format"] == "html" else {"h1": titlu}),
        "organizator": org if org[0] else None,
        "act_aditional": are_act_aditional(text),
        "nedeterminat": e_nedeterminata(text),
        "data_maxima": max(date) if date else None,
        "caractere": len(text),
    }
