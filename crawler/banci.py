"""Configuratia surselor: bancile accesibile, verificate prin diagnosticul din scripts/.

Excluse deliberat (vezi output/SUMAR_ACCESIBILITATE.md):
  - banorientfrance.com : robots.txt are "User-agent: * / Disallow: /" -> interzis explicit
  - bancatransilvania.ro, unicredit.ro, intesasanpaolobank.ro : WAF 403
  - pkobp.pl : inaccesibil public (timeout TCP)
  - www.bnr.ro : blocheaza automatizarea de browser (folosim doar feedul curs.bnr.ro)
  - credexbank.ro : domeniu nefuncstional (domeniul real e credex.ro)
"""

# Banci cu date retail bogate, structura verificata manual
BANCI = [
    {"id": "bcr", "nume": "Banca Comerciala Romana", "base": "https://www.bcr.ro",
     "sitemap": "https://www.bcr.ro/sitemap.xml", "delay": 2},

    {"id": "brd", "nume": "BRD - Groupe Societe Generale", "base": "https://www.brd.ro",
     "sitemap": "https://www.brd.ro/sitemap.xml", "delay": 2},

    {"id": "raiffeisen", "nume": "Raiffeisen Bank", "base": "https://www.raiffeisen.ro",
     "sitemap": "https://www.raiffeisen.ro/ro/sitemap.xml", "delay": 2},

    {"id": "ing", "nume": "ING Bank Romania", "base": "https://ing.ro",
     "sitemap": None, "delay": 2,
     # robots.txt da 403; RFC 9309: 4xx => fara restrictii declarate
     "nota": "robots.txt inaccesibil (403)"},

    {"id": "libra", "nume": "Libra Internet Bank", "base": "https://www.librabank.ro",
     "sitemap": "https://www.librabank.ro/sitemap.xml", "delay": 2},

    {"id": "patria", "nume": "Patria Bank", "base": "https://www.patriabank.ro",
     "sitemap": "https://www.patriabank.ro/sitemap.xml", "delay": 5,
     # robots.txt: Crawl-delay 5 + interzice /d/, /r/, /content/, /nav/
     "nota": "Crawl-delay 5 impus de robots.txt"},

    {"id": "garanti", "nume": "Garanti BBVA", "base": "https://www.garantibbva.ro",
     "sitemap": "https://www.garantibbva.ro/sitemap.xml", "delay": 2},

    {"id": "nexent", "nume": "Nexent Bank (ex-Credit Europe)", "base": "https://www.nexentbank.ro",
     "sitemap": "https://www.nexentbank.ro/sitemap.xml", "delay": 2},

    {"id": "eximbank", "nume": "Exim Banca Romaneasca", "base": "https://www.eximbank.ro",
     "sitemap": "https://www.eximbank.ro/sitemap.xml", "delay": 2},

    {"id": "vista", "nume": "Vista Bank", "base": "https://www.vistabank.ro",
     "sitemap": "https://www.vistabank.ro/sitemap.xml", "delay": 2},

    {"id": "procredit", "nume": "ProCredit Bank", "base": "https://www.procreditbank.ro",
     "sitemap": "https://www.procreditbank.ro/sitemap.xml", "delay": 2},

    {"id": "salt", "nume": "Salt Bank", "base": "https://salt.bank",
     "sitemap": "https://salt.bank/sitemap.xml", "delay": 2},

    {"id": "tbi", "nume": "tbi bank", "base": "https://tbibank.ro",
     "sitemap": "https://tbibank.ro/sitemap.xml", "delay": 2},

    {"id": "techventures", "nume": "TechVentures Bank", "base": "https://www.techventures.bank",
     "sitemap": "https://www.techventures.bank/sitemap.xml", "delay": 2},

    {"id": "brci", "nume": "Banca Romana de Credite si Investitii", "base": "https://www.brci.ro",
     "sitemap": "https://www.brci.ro/sitemap.xml", "delay": 2},

    {"id": "bcrlocuinte", "nume": "BCR Banca pentru Locuinte", "base": "https://www.bcrlocuinte.ro",
     "sitemap": "https://www.bcrlocuinte.ro/sitemap.xml", "delay": 2},

    {"id": "creditcoop", "nume": "CREDITCOOP", "base": "https://www.creditcoop.ro",
     "sitemap": "https://www.creditcoop.ro/sitemap.xml", "delay": 2},

    {"id": "bid", "nume": "Banca de Investitii si Dezvoltare", "base": "https://www.bidromania.eu",
     "sitemap": "https://www.bidromania.eu/sitemap.xml", "delay": 2},

    # atentie: revolut.com fara /en-RO/ serveste versiunea din UK, nu cea romaneasca
    {"id": "revolut", "nume": "Revolut Bank UAB - Sucursala Bucuresti",
     "base": "https://www.revolut.com/en-RO/", "sitemap": None, "delay": 2,
     "nota": "site in engleza; extractorul acopera si termenii englezi"},

    {"id": "cetelem", "nume": "BNP Paribas Personal Finance (Cetelem)", "base": "https://www.cetelem.ro",
     "sitemap": None, "delay": 2,
     "nota": "WAF respinge cereri non-browser; robots.txt citit prin browser, permisiv"},

    {"id": "credex", "nume": "Credex IFN", "base": "https://credex.ro",
     "sitemap": "https://credex.ro/page-sitemap.xml", "delay": 2,
     "nota": "IFN, nu banca"},

    # Sucursale corporate: accesibile, dar practic fara date retail publicate
    {"id": "bnpparibas", "nume": "BNP Paribas SA Paris - Sucursala Bucuresti",
     "base": "https://www.romania.bnpparibas.com",
     # robots.txt-ul lor declara sitemap-ul filialei din LUXEMBURG
     # (bnpparibas.lu, 418 adrese straine). Cel romanesc nu e declarat
     # nicaieri, dar exista la calea standard — de aceea e scris aici.
     "sitemap": "https://www.romania.bnpparibas.com/sitemap.xml", "delay": 2,
     "nota": "corporate banking, randament mic"},

    {"id": "bankofchina", "nume": "Bank of China (CEE) - Sucursala Bucuresti",
     "base": "https://www.bankofchina.com/ro/en", "sitemap": None, "delay": 2,
     "nota": "corporate banking, randament mic"},
]

# Clasificarea paginilor pe categorii, dupa cuvinte-cheie din URL.
# Include termeni englezi: Revolut si alte entitati prezente in Romania publica in
# engleza, iar o lista doar in romana rateaza tocmai paginile de preturi.
CATEGORII = {
    "conturi_carduri": ["cont-curent", "conturi", "cont-", "card", "carduri", "pachet",
                        "debit", "credit-card", "operatiuni",
                        "accounts", "current-account", "plans"],
    "credite": ["credit", "imprumut", "ipotec", "nevoi-personale", "refinant",
                "overdraft", "descoperit", "noua-casa", "prima-casa", "leasing",
                "loans", "mortgage", "borrow"],
    "depozite": ["depozit", "economi", "plasament", "investit",
                 "savings", "deposits"],
    "comisioane": ["comision", "tarif", "taxe", "documente-contractuale",
                   "informatii-utile", "documente-importante",
                   "pricing", "fees", "our-pricing", "legal/terms"],
    "curs_valutar": ["curs-valutar", "curs-de-schimb", "schimb-valutar",
                     "currency-converter", "exchange-rates", "currency"],
    "dobanzi": ["dobanzi", "dobanda", "rate-dobanda", "rate-de-dobanda",
                "lista-dobanzi", "interest-rates", "rate-dobanzi"],
    "indici": ["indici-referinta", "indice-de-referinta", "indici-de-referinta",
               "ircc", "robor", "euribor", "indici", "rate-referinta",
               "dobanzi-de-referinta", "reference-rates"],
    "business": ["imm", "business", "corporate", "companii", "afaceri-mici", "micro",
                 "persoane-juridice", "juridice", "factoring", "cash-management",
                 "leasing"],
}

# Selectia condusa de cerinte: fiecare punct cerut primeste garantat o pagina,
# daca exista una pe site. Fara asta, plafonul pe categorie face imposibila
# acoperirea celor 5 tipuri de credit sau a celor 4 produse de corporate.
CERINTE_TINTA = [
    # (id cerinta, categorie, cuvinte-cheie in URL)
    ("cont_curent", "conturi_carduri",
     ["cont-curent", "conturi-curente", "current-account", "cont-de-baza"]),
    ("pachete", "conturi_carduri",
     ["pachet", "pachete", "our-pricing-plans", "plans", "pricing"]),
    ("card_debit", "conturi_carduri",
     ["card-de-debit", "carduri-de-debit", "debit-card", "carduri-de-debit"]),
    ("card_credit", "conturi_carduri",
     ["card-de-credit", "carduri-de-credit", "credit-card", "carduri-de-cumparaturi"]),

    ("nevoi_personale", "credite",
     ["nevoi-personale", "credit-nevoi", "personal-loan", "credite-pentru-nevoi"]),
    ("ipotecar", "credite",
     ["ipotecar", "mortgage", "credite-pentru-casa", "credit-locuinta", "imobiliar"]),
    ("noua_casa", "credite", ["noua-casa", "prima-casa"]),
    ("refinantare", "credite", ["refinantare", "refinant", "refinanc"]),
    ("overdraft", "credite", ["overdraft", "descoperit-de-cont", "descoperit"]),

    ("depozite", "depozite", ["depozit", "depozite", "deposits", "depozitul"]),
    ("economii", "depozite", ["economi", "savings", "cont-de-economii"]),

    ("comisioane", "comisioane",
     ["comision", "comisioane", "tarif", "taxe", "pricing", "fees"]),
    ("documente", "comisioane",
     ["documente-contractuale", "documente-importante", "informatii-utile"]),

    ("dobanzi", "dobanzi",
     ["dobanzi", "rate-dobanda", "rate-de-dobanda", "lista-dobanzi", "interest-rates"]),
    ("indici_referinta", "indici",
     ["indici-referinta", "indice-de-referinta", "indici-de-referinta", "ircc",
      "robor", "euribor", "rate-referinta", "dobanzi-de-referinta"]),
    ("curs_valutar", "curs_valutar",
     ["curs-valutar", "curs-de-schimb", "currency-converter", "exchange-rates"]),

    ("imm_credite", "business",
     ["imm", "credite-imm", "afaceri-mici", "micro", "credit-firma"]),
    ("factoring", "business", ["factoring"]),
    ("leasing", "business", ["leasing"]),
    ("cash_management", "business",
     ["cash-management", "cash-manag", "managementul-numerarului",
      "management-numerar", "trezorerie"]),
]

# Pagini de ignorat: zgomot editorial si juridic
EXCLUDE = [
    "blog", "news-hub", "/news", "presa", "comunicat", "noutati", "cariere", "csr",
    "cookie", "gdpr", "confidential", "protectia-datelor", "politica", "mentiuni-legale",
    "termeni-si-conditii", "contact", "retea-unitati", "branch", "atm", "sucursal",
    "help-center", "faq", "intrebari", "despre-noi", "despre-patria", "investitori",
    "arhiva", "campanii", "scoala", "educatie", "feedback", "formular", "login",
    "autentificare", "fraud", "securitate", "reclamat", "sitemap", "rss",
]

# Cai interzise explicit de robots.txt, pe banca (dublura de siguranta peste robotparser)
CAI_INTERZISE = {
    "patria": ["/d/", "/r/", "/content/", "/nav/"],
    "bcr": ["/ro/one-bcr/", "/ro/georgeapp/", "/search", "/?s="],
}
