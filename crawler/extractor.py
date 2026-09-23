"""Extragerea datelor dintr-o pagina de produs bancar."""
import re

# Termeni care marcheaza o linie cu informatie de pret/rata.
# Include si termeni in engleza: unele banci prezente in Romania publica in engleza
# (ex. Revolut pe /en-RO/ foloseste "fee", "cashback", "interest", "APY").
TERMENI_RATA = [
    # romana
    "dae", "dobând", "dobanda", "ircc", "robor", "euribor", "marj",
    "comision", "taxa", "taxă", "tarif", "rata", "rată", "valoare total",
    "cost total", "avans", "perioada", "scadent", "cashback",
    # engleza
    "fee", "interest", "apy", "apr", "p.a.", "per annum", "charge",
    "commission", "withdrawal", "exchange rate", "discount", "per month",
    "monthly", "annual",
]

RE_PROCENT = re.compile(r"(?<![\d.,])\d{1,3}(?:[,.]\d+)?\s*%")
RE_SUMA = re.compile(r"\d[\d.\s]{2,}(?:,\d+)?\s*(?:lei|RON|EUR|euro|USD)\b", re.IGNORECASE)

JS_TABELE = """
els => els.map(t => {
    const rows = Array.from(t.querySelectorAll('tr'))
        .map(r => Array.from(r.querySelectorAll('th,td'))
            .map(c => c.innerText.trim().replace(/\\s+/g, ' ')))
        .filter(r => r.some(c => c.length > 0));
    return {numar_randuri: rows.length, randuri: rows.slice(0, 40)};
}).filter(t => t.numar_randuri > 1)
"""

JS_PDF = """
els => els.map(a => ({
    text: a.innerText.trim().replace(/\\s+/g, ' ').slice(0, 120),
    href: a.href
}))
"""


def extrage(page, url, categorie):
    """Extrage datele structurate din pagina incarcata."""
    body = page.inner_text("body")

    tabele = page.eval_on_selector_all("table", JS_TABELE)

    pdfs_brut = page.eval_on_selector_all("a[href*='.pdf']", JS_PDF)
    vazute, pdfs = set(), []
    for d in pdfs_brut:
        href = d["href"].split("?")[0]
        if href not in vazute:
            vazute.add(href)
            pdfs.append({"text": d["text"], "url": d["href"]})

    linii_rata = []
    for linie in body.split("\n"):
        linie = linie.strip()
        if not linie or len(linie) > 300:
            continue
        jos = linie.lower()
        if any(t in jos for t in TERMENI_RATA) and (
                RE_PROCENT.search(linie) or RE_SUMA.search(linie)):
            linii_rata.append(linie)

    return {
        "url": url,
        "categorie": categorie,
        "titlu": page.title()[:150],
        "lungime_text": len(body),
        "numar_tabele": len(tabele),
        "tabele": tabele,
        "pdfs": pdfs,
        "linii_rata": linii_rata[:40],
        "procente": sorted(set(m.group().strip() for m in RE_PROCENT.finditer(body)))[:30],
    }


def clasifica(url, categorii, exclude):
    """Returneaza categoria unui URL, sau None daca trebuie ignorat."""
    jos = url.lower()
    # documentele se descarca, nu se navigheaza
    if jos.split("?")[0].endswith((".pdf", ".doc", ".docx", ".xls", ".xlsx")):
        return None
    # versiunile in alte limbi dubleaza conținutul romanesc
    if "/en/" in jos or jos.endswith("/en") or "/english/" in jos:
        return None
    if any(x in jos for x in exclude):
        return None
    for categorie, chei in categorii.items():
        if any(k in jos for k in chei):
            return categorie
    return None


# Semnale care indica o pagina reala de produs, pe categorie
SEMNALE_PRODUS = {
    "conturi_carduri": ["cont-curent", "conturi-curente", "pachete", "pachet-",
                        "carduri-de-debit", "card-de-debit", "cardul-", "carduri",
                        "cont-online", "cont-de-baza", "conturi-si-operatiuni"],
    "credite": ["nevoi-personale", "credit-ipotecar", "ipotecar", "noua-casa",
                "prima-casa", "refinantare", "descoperit-de-cont", "overdraft",
                "card-de-credit", "credit-auto", "credit-de-consum", "credite-pentru",
                "credite/"],
    "depozite": ["depozit", "cont-de-economii", "conturi-de-economii", "economisire"],
    "comisioane": ["comisioane", "comision", "tarif", "taxe", "documente-contractuale",
                   "pricing", "our-pricing-plans", "fees"],
    "curs_valutar": ["curs-valutar", "curs-de-schimb", "currency-converter",
                     "exchange-rates"],
    "business": ["imm", "afaceri-mici", "micro", "companii", "corporate", "business"],
}

# Pagini informative/juridice: exista, dar nu conțin prețuri
SEMNALE_SLABE = [
    "fondul-de-garantare", "birou-de-credit", "prelucrare", "informare",
    "reglementari", "glosar", "ghid", "tutorial", "proceduri", "plati-sepa",
    "swift", "/crs", "popriri", "acord", "open-banking", "procuri", "mobilitate",
    "pin-prin", "3d-secure", "restructurare", "darea-in-plata", "amana",
    "asigurar", "pensii", "obligatiuni", "titluri-de-stat", "broker", "actiuni",
    "dividend", "serviciul-de-", "servicii-de-baza", "drepturi", "status",
]

CATEGORII_RETAIL = ("conturi_carduri", "credite", "depozite")


def scor_url(url, categorie):
    """Scor de prioritate: paginile de produs trebuie vizitate inaintea celor informative."""
    from urllib.parse import urlparse

    jos = url.lower()
    scor = 0
    if any(s in jos for s in SEMNALE_PRODUS.get(categorie, [])):
        scor += 4
    scor -= sum(1 for s in SEMNALE_SLABE if s in jos)
    if categorie in CATEGORII_RETAIL:
        if "persoane-fizice" in jos or "retail" in jos:
            scor += 2
        if any(b in jos for b in ("/imm", "business", "juridice", "corporate",
                                  "companii", "afaceri")):
            scor -= 3
    # paginile prea adanci sunt de obicei detalii marginale
    adancime = (urlparse(jos).path or "/").strip("/").count("/")
    scor -= max(0, adancime - 3)
    return scor
