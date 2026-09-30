"""Configurația colectorului de campanii, pe bancă (Nicolae, §6.1).

Adresele de aici NU sunt ghicite: fiecare hub, pagină-listă și newsroom a fost
găsit OFFLINE, ca legătură în paginile deja aduse în `bronze/` (29.09.2026),
sau vine din tabelul lui Nicolae (măsurat în testul din 25.09). Unde nu există
nicio dovadă offline, banca are doar pagina principală și sitemap-ul, iar
componentele 4–5 (legăturile din acasă, paginile-listă) găsesc restul.

Chei, pe bancă:
  baza           pagina principală (componenta 4 pornește de aici)
  gazde          gazdele paginilor băncii (implicit: domeniul din `baza`)
  gazde_doc      gazde suplimentare DOAR pentru documente (CDN-ul grupului)
  huburi         paginile-listă de campanii active (componenta 3)
  arhive         huburile de campanii încheiate: NU se cer în fotografie
                 (treapta A; istoricul e o trecere separată, decizia 4 din §9)
  regulamente    indexuri de regulamente (tratate ca huburi de documente)
  segmente       paginile de segment citite ca pagina principală (componenta 4)
  sitemap        listă explicită | None = din robots.txt, la rulare, plus
                 /sitemap.xml | False = interzis (ING: `Disallow: *.xml`)
  filtru_sitemap 'campanie' (cuvintele de campanie în cale) sau
                 'radacina_recenta' (BRD: campaniile stau la rădăcină, pe
                 adrese scurte fără niciun cuvânt de campanie — /irl,
                 /promotie-multicurrency —, deci se iau adresele cu un singur
                 segment și `lastmod` în ultimele 12 luni)
  newsroom       {'tip': 'sitemap', 'prefix': ...} sau
                 {'tip': 'lista', 'url': ..., 'prefix': ..., 'pagini': N,
                  'paginare': '?page={n}' | 'page/{n}/', 'n_start': numărul
                  paginii a doua (implicit 2)} sau None
  nume, grup     tipare (text fără diacritice, litere mici) pentru organizator
  pauza_estimata secunde între cereri, DOAR pentru estimarea din --simulare
                 (la rulare pauza o dă robots.txt, prin transport)
"""

# Banca noastră: colectată ca reper, marcată ca atare (vederea
# `campanii_curente`, coloana `reper`, are aceeași listă).
BANCI_REPER = frozenset({"libra"})

# 0 cereri, afișate cu dovada. Nu se încearcă alt canal (Playwright, alt UA,
# arhive): regula „o bancă blocată se documentează ca blocată".
BLOCATE = {
    "banca-transilvania": "blocat, HTTP 403 (WAF), 24.09.2026",
    "cec": "blocat, HTTP 403 (WAF), 24.09.2026",
    "unicredit": "blocat, HTTP 403 (WAF), 24.09.2026",
    "intesa": "blocat, HTTP 403 (WAF), 24.09.2026 (robots.txt permite tot, WAF-ul refuză)",
    "banorient": "blocat de robots.txt: „User-agent: * / Disallow: /” (date/robots/banorient.txt, 23.09.2026)",
    "cetelem": "tratată ca blocată (decizia lui Robert, §9.2): robots.txt prin HTTP a întors respingerea "
               "F5 „Request Rejected” (date/robots/cetelem.txt, 23.09.2026)",
}
# `campanie.bancatransilvania.ro` nu se cere: banca e blocată, nu doar originea.

IN_AFARA_SCOPULUI = {
    "citibank": "în afara scopului: fără retail în România (Nicolae, §6.1)",
    "bnpparibas": "în afara scopului: sucursală corporate (Nicolae, §6.1)",
    "bid": "în afara scopului: fără retail (Nicolae, §6.1)",
    "bankofchina": "în afara scopului: corporate (Nicolae, §6.1)",
    "pko": "în afara scopului: piața poloneză (Nicolae, §6.1)",
}

FARA_CONFIG = {
    "revolut": "decizie în așteptare (Nicolae, §9.2): conținut de grup, Next.js; robots.txt "
               "interzice `*?*`, `/api/`, `/*.json$`; fără nicio pagină-listă găsită",
}

# Căi sărite la toate băncile: dublurile în engleză ale acelorași campanii
# (Garanti /en/ended-campains, BRD /en/promotions) și paginile fără ofertă.
SARI_IMPLICIT = (r"^/en(/|$)", r"^/english/", r"login|autentificare|/contact|cookie|gdpr|cariere"
                 r"|/cautare|/search|/tag/|/author/|/feed/?$")

CONFIG = {
    "bcr": {
        "baza": "https://www.bcr.ro/ro",
        "gazde_doc": ["cdn.erstegroup.com", "cdn0.erstegroup.com"],
        # tema GEM: legăturile stau în JSON, citite de campanii_extractie.linkuri
        "huburi": ["https://www.bcr.ro/ro/campanii",
                   "https://www.bcr.ro/ro/persoane-fizice/carduri-de-cumparaturi/campanii"],
        # /ro/business: bonusul de dobândă George Business (c6) nu era pe hub (§4.1)
        "segmente": ["https://www.bcr.ro/ro/business"],
        "sitemap": ["https://www.bcr.ro/sitemap.xml"],
        "newsroom": {"tip": "sitemap", "prefix": "/ro/presa/"},
        "nume": [r"banca comerciala romana", r"\bbcr\b"],
        "grup": [r"bcr social finance", r"bcr leasing", r"bcr pensii", r"bcr banca pentru locuinte",
                 r"erste group", r"\bs[- ]?leasing"],
    },
    "bcr-locuinte": {
        "baza": "https://www.bcrlocuinte.ro/",
        "gazde_doc": ["cdn.erstegroup.com", "cdn0.erstegroup.com"],
        "nume": [r"bcr banca pentru locuinte", r"banca pentru locuinte"],
        "grup": [r"banca comerciala romana", r"\bbcr\b(?! banca pentru)", r"erste group"],
    },
    "brd": {
        "baza": "https://www.brd.ro/",
        "huburi": ["https://www.brd.ro/card-de-credit-oferte",
                   "https://www.brd.ro/companii/informatii-si-documente-utile/promotii-carduri-business"],
        # /promotii: arhivă moartă, 23 de candidați, 0 activi, ani 2020–2022 (§3.5)
        "arhive": ["https://www.brd.ro/promotii"],
        "sitemap": ["https://www.brd.ro/sitemap.xml"],
        "filtru_sitemap": "radacina_recenta",
        "newsroom": {"tip": "lista", "url": "https://www.brd.ro/despre-brd/noutati-si-presa/ultimele-noutati",
                     "prefix": None, "pagini": 5, "paginare": "?page={n}",
                     "n_start": 1},          # Drupal: ?page=1 e a doua pagină
        "nume": [r"\bbrd\b", r"groupe societe generale"],
        "grup": [r"brd finance", r"brd sogelease", r"brd asset management"],
    },
    "raiffeisen": {
        "baza": "https://www.raiffeisen.ro/",
        "huburi": ["https://www.raiffeisen.ro/ro/persoane-fizice/campanii-promotionale.html",
                   "https://www.raiffeisen.ro/ro/persoane-fizice/campanii-promotionale/2026.html",
                   "https://www.raiffeisen.ro/ro/imm/campanii-promotionale.html"],
        "segmente": ["https://www.raiffeisen.ro/ro/imm.html"],
        "sitemap": ["https://www.raiffeisen.ro/ro/sitemap.xml"],
        # JSON-ul declarat în pagină (anul curent) nu e implementat aici, iar
        # sitemap-ul n-are nicio adresă din 2026 (§4.3): newsroom-ul rămâne gol
        "newsroom": None,
        "nota_newsroom": "JSON declarat în pagină, neimplementat; sitemap-ul n-are 2026 (Nicolae, §4.3)",
        "nume": [r"raiffeisen bank"],
        "grup": [r"raiffeisen leasing", r"raiffeisen asset", r"aedificium", r"raiffeisen bank international"],
    },
    "ing": {
        "baza": "https://ing.ro/",
        "huburi": ["https://ing.ro/ing-in-romania/informatii-utile/promotii"],
        # robots.txt: `Disallow: *.xml` (inclusiv sitemap-ul) și `*.pdf` — deci
        # nici regulamentele PDF nu se cer (transport le refuză cu ROBOTS)
        "sitemap": False,
        "newsroom": {"tip": "lista", "url": "https://ing.ro/informatii-utile/newsroom",
                     "prefix": "/informatii-utile/", "pagini": 1},
        "nume": [r"\bing bank\b", r"\bing\b"],
        "grup": [r"ing asigurari", r"ing pensii", r"\bnn\b"],
    },
    "garanti": {
        "baza": "https://www.garantibbva.ro/",
        "huburi": ["https://www.garantibbva.ro/persoane-fizice/campanii",
                   "https://www.garantibbva.ro/persoane-fizice/campanii-online",
                   "https://www.garantibbva.ro/persoane-fizice/campanii-bonus-card",
                   "https://www.garantibbva.ro/imm-si-pfa/campanii"],
        "arhive": ["https://www.garantibbva.ro/campanii-incheiate",
                   "https://www.garantibbva.ro/campanii-incheiate-online"],
        "sitemap": ["https://www.garantibbva.ro/sitemap.xml"],
        "newsroom": {"tip": "sitemap", "prefix": "/comunicate-de-presa/"},
        "nume": [r"garanti bbva", r"garanti bank"],
        "grup": [r"garanti bbva leasing", r"garanti leasing", r"motoractive", r"ralfi"],
    },
    "libra": {
        "baza": "https://www.librabank.ro/",
        "huburi": ["https://www.librabank.ro/campanii"],
        "sitemap": ["https://www.librabank.ro/sitemap.xml"],
        "newsroom": {"tip": "lista", "url": "https://www.librabank.ro/Stiri", "prefix": "/Stiri/", "pagini": 1},
        "nume": [r"libra internet bank", r"\blibra\b"],
    },
    "procredit": {
        "baza": "https://www.procreditbank.ro/",
        "huburi": ["https://www.procreditbank.ro/companii/campanii-pj/"],
        "regulamente": ["https://www.procreditbank.ro/regulamente/"],
        "sitemap": ["https://www.procreditbank.ro/sitemap_index.xml"],
        "newsroom": {"tip": "lista", "url": "https://www.procreditbank.ro/stiri/", "prefix": None,
                     "pagini": 2, "paginare": "page/{n}/"},
        "nume": [r"procredit bank"],
    },
    "exim": {
        "baza": "https://www.eximbank.ro/",
        "huburi": ["https://www.eximbank.ro/persoane-fizice/carduri/promotii-carduri/",
                   "https://www.eximbank.ro/2025/09/30/promotii/"],
        "newsroom": {"tip": "lista", "url": "https://www.eximbank.ro/category/centru-de-presa/comunicate/",
                     "prefix": None, "pagini": 3, "paginare": "page/{n}/"},
        "nume": [r"exim banca romaneasca", r"eximbank", r"banca romaneasca"],
    },
    "patria": {
        "baza": "https://www.patriabank.ro/",
        "huburi": ["https://www.patriabank.ro/persoane-fizice/campanii-in-parteneriat"],
        "sitemap": ["https://www.patriabank.ro/sitemap.xml"],
        # robots.txt: Crawl-delay 5; `/d/`, `/r/`, `/content/`, `/nav/` interzise
        # (și regulamentele, pe /d/) — date/robots/patria.txt, 23.09.2026
        "pauza_estimata": 5,
        "newsroom": {"tip": "lista", "url": "https://www.patriabank.ro/despre-patria/informatii-presa/comunicate-de-presa",
                     "prefix": None, "pagini": 1},
        "nume": [r"patria bank"],
        "grup": [r"patria credit"],
    },
    "salt": {
        "baza": "https://salt.bank/",
        "gazde": ["salt.bank", "www.salt.bank"],
        "huburi": ["https://salt.bank/noutati/campanii-marketing"],
        # indexul de regulamente: perioada stă în textul linkului la 52 din 100 (§6.1)
        "regulamente": ["https://salt.bank/documente/campanii-si-promotii",
                        "https://salt.bank/documente/campanii-si-promotii-persoane-juridice"],
        "newsroom": {"tip": "lista", "url": "https://salt.bank/noutati/news", "prefix": "/noutati-postare/",
                     "pagini": 1},
        "nume": [r"salt bank"],
    },
    "tbi": {
        "baza": "https://tbibank.ro/",
        # pagina campaniilor active negăsită (§6.1); regulamentele vin din sitemap
        "arhive": ["https://tbibank.ro/campanii-incheiate/"],
        "sitemap": ["https://tbibank.ro/sitemap_index.xml"],
        "newsroom": {"tip": "lista", "url": "https://tbibank.ro/news", "prefix": "/news/", "pagini": 1},
        "nume": [r"tbi bank"],
    },
    "credex": {
        # banca, nu Credex IFN (credex.ro, cea din ingest/banks.py): decizia lui
        # Robert (§9.2). Nicio pagină credexbank.ro în Bronze, deci doar acasă + sitemap;
        # robots.txt se citește la prima cerere (transport), înainte de orice pagină.
        "baza": "https://credexbank.ro/",
        "nume": [r"credex bank"],
        "grup": [r"credex ifn"],
    },
    "techventures": {
        "baza": "https://techventures.bank/",
        "gazde": ["techventures.bank", "www.techventures.bank"],
        "huburi": ["https://techventures.bank/persoane-fizice/campanii"],
        "nume": [r"techventures bank", r"techventures"],
    },
    "brci": {
        "baza": "https://www.brci.ro/",
        "newsroom": {"tip": "lista", "url": "https://www.brci.ro/ro/noutati.html", "prefix": None, "pagini": 1},
        "nume": [r"banca romana de credite si investitii", r"\bbrci\b"],
    },
    "nexent": {
        # cardavantaj.ro (campaniile Card Avantaj) abia după ce robots.txt-ul
        # lui e salvat (Nicolae, §6.3): nu intră în `gazde`
        "baza": "https://www.nexentbank.ro/",
        "newsroom": {"tip": "lista", "url": "https://www.nexentbank.ro/biroul-de-presa", "prefix": None,
                     "pagini": 1},
        "nume": [r"nexent bank", r"credit europe bank"],
    },
    "vista": {
        "baza": "https://www.vistabank.ro/",
        "newsroom": {"tip": "lista", "url": "https://www.vistabank.ro/despre-noi/noutati",
                     "prefix": "/despre-noi/noutati/", "pagini": 1},
        "nume": [r"vista bank"],
    },
    "creditcoop": {
        "baza": "https://www.creditcoop.ro/",
        "nume": [r"creditcoop", r"banca centrala cooperatista"],
    },
}


def stare_banca(slug):
    """('colectat' | 'blocat' | 'in_afara_scopului' | 'fara_config', motiv)."""
    if slug in BLOCATE:
        return "blocat", BLOCATE[slug]
    if slug in IN_AFARA_SCOPULUI:
        return "in_afara_scopului", IN_AFARA_SCOPULUI[slug]
    if slug in FARA_CONFIG:
        return "fara_config", FARA_CONFIG[slug]
    if slug in CONFIG:
        return "colectat", "reper (banca noastră)" if slug in BANCI_REPER else ""
    return "fara_config", "fără configurație"
