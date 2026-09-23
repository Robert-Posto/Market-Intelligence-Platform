# Listă bănci din România + link-uri oficiale, confirmate prin căutare web
# (nu link-uri ghicite). Folosită de scraper.py.
#
# note: câmp opțional pentru bănci semnalate ca "fără pagină ToS identificată" /
# fără prezență web clară de retail — le includem tot, scraper-ul le va marca
# după rezultatul real al fetch-ului.
#
# acces_cunoscut: câmp opțional pentru bănci deja confirmate ca inaccesibile
# prin fetch simplu (WAF integral, timeout, robots.txt care interzice tot),
# ca să nu mai irosim cereri pe ele la fiecare rulare. Valori: "waf_blocat" |
# "timeout" | "robots_disallow_all" | "domeniu_abandonat". sursa_info spune
# de unde vine adnotarea -- e doar o notă informativă (fapt deja verificat),
# nu cod sau date preluate din munca altcuiva.
BANKS = [
    {"name": "Banca Transilvania", "url": "https://www.bancatransilvania.ro/", "acces_cunoscut": "waf_blocat", "sursa_info": "info: coleg, briefing 16-17 sept"},
    {"name": "BCR", "url": "https://www.bcr.ro/"},
    {"name": "CEC Bank", "url": "https://www.cec.ro/"},
    {"name": "ING Bank (Sucursala București)", "url": "https://www.ing.ro/"},
    {"name": "BRD — Groupe Société Générale", "url": "https://www.brd.ro/"},
    {"name": "Raiffeisen Bank", "url": "https://www.raiffeisen.ro/"},
    {"name": "UniCredit Bank", "url": "https://www.unicredit.ro/", "acces_cunoscut": "waf_blocat", "sursa_info": "info: coleg, briefing 16-17 sept"},
    {"name": "Intesa Sanpaolo Bank România", "url": "https://www.intesasanpaolobank.ro/", "acces_cunoscut": "waf_blocat", "sursa_info": "info: coleg, briefing 16-17 sept"},
    {"name": "Vista Bank (Romania)", "url": "https://www.vistabank.ro/"},
    {"name": "Patria Bank", "url": "https://www.patriabank.ro/"},
    {"name": "Exim Banca Românească", "url": "https://www.eximbank.ro/"},
    {"name": "Libra Internet Bank", "url": "https://www.librabank.ro/", "note": "angajator, nu competitor"},
    {"name": "ProCredit Bank", "url": "https://www.procreditbank.ro/"},
    {"name": "Revolut Bank UAB — Sucursala București", "url": "https://www.revolut.com/en-RO/"},
    {"name": "tbi bank EAD Sofia — Sucursala București", "url": "https://tbibank.ro/"},
    {"name": "Garanti BBVA România", "url": "https://www.garantibbva.ro/"},
    {"name": "Salt Bank", "url": "https://salt.bank/"},
    {"name": "Citibank Europe plc — Sucursala România", "url": "https://www.citibank.com/icg/sa/emea/romania/english/about-us.html", "acces_cunoscut": "domeniu_abandonat", "sursa_info": "info: coleg, briefing 16-17 sept"},
    {"name": "BNP Paribas S.A. Paris — Sucursala București", "url": "https://romania.bnpparibas.com/"},
    {"name": "Banca Centrală Cooperatistă CREDITCOOP", "url": "https://www.creditcoop.ro/"},
    {"name": "Banca de Investiții și Dezvoltare (BID)", "url": "https://www.bidromania.eu/"},
    {"name": "Bank of China (CEE) Ltd — Sucursala București", "url": "https://www.bankofchina.com/ro/en/"},
    {"name": "Credex Bank", "url": "https://credex.ro/"},
    {"name": "TechVentures Bank", "url": "https://techventures.bank/", "note": "user a semnalat inițial: fără pagină ToS identificată"},
    {"name": "Banca Română de Credite și Investiții (BRCI)", "url": "https://www.brci.ro/", "note": "user a semnalat inițial: fără pagină ToS identificată"},
    {"name": "BCR Banca pentru Locuințe", "url": "https://www.bcrlocuinte.ro/", "note": "user a semnalat inițial: fără pagină ToS identificată"},
    {"name": "Nexent Bank N.V. Amsterdam – Sucursala București", "url": "https://www.nexentbank.ro/", "note": "user a semnalat inițial: doar politică de cookies găsită"},
    {"name": "BNP Paribas Personal Finance S.A. – Sucursala București / Cetelem", "url": "https://www.cetelem.ro/", "note": "user a semnalat inițial: fără clauză găsită"},
    {"name": "Banque Banorient France S.A. – Sucursala România", "url": "https://www.banorientfrance.com/romanian/romania", "note": "user a semnalat inițial: doar note legale GDPR găsite", "acces_cunoscut": "robots_disallow_all", "sursa_info": "info: coleg, briefing 16-17 sept"},
    {"name": "PKO Bank Polski S.A. – Sucursala București", "url": "https://www.pkobp.pl/ro/filiala-romania", "note": "user a semnalat inițial: fără pagină ToS identificată", "acces_cunoscut": "timeout", "sursa_info": "info: coleg, briefing 16-17 sept"},
]
