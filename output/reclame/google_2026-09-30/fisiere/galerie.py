"""Construiește galeria de reclame (prototip) dintr-o fotografie Google Ads
Transparency: pune datele în galerie_sablon.html și scrie pagina de publicat.
Merge și cu JSON-ul din 29.09, și cu CSV-ul din fotografie.sql (30.09 încoace).

    python output/reclame/galerie.py output/reclame/atc_ro_2026-09-30.csv <pagina.html>
"""
import collections
import csv
import datetime
import json
import os
import sys

AICI = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding="utf-8")
csv.field_size_limit(10 ** 7)
INT64_MAX = 2 ** 63 - 1
FORMATE = {"TEXT": 0, "IMAGE": 1, "VIDEO": 2}
NUME = {"bt": "Banca Transilvania", "ing": "ING", "bcr": "BCR", "raiffeisen": "Raiffeisen",
        "revolut": "Revolut", "nexent": "Nexent", "cec": "CEC Bank", "tbi": "TBI Bank",
        "salt": "Salt Bank", "libra": "Libra", "unicredit": "UniCredit", "garanti": "Garanti BBVA",
        "patria": "Patria Bank", "intesa": "Intesa Sanpaolo", "brd": "BRD"}
# BT, CEC și UniCredit ne blochează site-ul (WAF), deci pentru ele reclamele sunt
# singura sursă automată; la Revolut, ~20% din reclame erau în română (29.09);
# Intesa publică doar prin WPP Media Romania (42 de reclame, 30.09).
ETICHETE = {"bt": "site blocat", "cec": "site blocat", "unicredit": "site blocat",
            "revolut": "limbă mixtă", "intesa": "prin agenție"}
TEME = {"Finance": "Finanțe", "Business & Industrial": "Afaceri și industrie",
        "Computers & Consumer Electronics": "Electronice", "Apparel": "Îmbrăcăminte",
        "Hobbies, Games & Leisure": "Timp liber", "Home & Garden": "Casă și grădină",
        "Autos & Vehicles": "Auto", "Internet & Telecom": "Internet și telecom",
        "Travel & Tourism": "Călătorii", "Family & Community": "Familie și comunitate",
        "Sports & Fitness": "Sport", "Arts & Entertainment": "Artă și divertisment",
        "Law & Government": "Juridic și administrație", "Jobs & Education": "Joburi și educație",
        "Occasions & Gifts": "Ocazii și cadouri", "Real Estate": "Imobiliare", "Commercial": "Comercial",
        "Health": "Sănătate", "Food & Groceries": "Alimente", "Beauty & Personal Care": "Frumusețe",
        "Retailers & General Merchandise": "Comerț", "Dining & Nightlife": "Restaurante",
        "News, Books & Publications": "Știri și publicații"}
AGENTII = {"DQ&A Technology NL BV": "DQ&A Technology", "DENTSU BUCURESTI S.R.L.": "Dentsu București",
           "WPP Media Romania S.R.L": "WPP Media Romania"}
PLATFORME = {"YOUTUBE": 1, "SEARCH": 2, "MAPS": 4, "PLAY": 8, "SHOPPING": 16}
CRITERII = ("demographic_info", "geo_location", "contextual_signals", "customer_lists", "topics_of_interest")
CODURI = {"CRITERIA_UNUSED": "u", "CRITERIA_INCLUDED": "i", "CRITERIA_EXCLUDED": "e",
          "CRITERIA_INCLUDED_AND_EXCLUDED": "b"}


def citeste(cale):
    with open(cale, encoding="utf-8", newline="") as f:
        if cale.lower().endswith(".csv"):
            # În CSV-ul din consolă, valorile lipsă vin ca șir gol.
            return [{k: (v if v != "" else None) for k, v in r.items()} for r in csv.DictReader(f)]
        return json.load(f)


def platforma(s):
    """(platformele principale ca mască, cod): cod 1 = sub 1.000 pe fiecare, 2 = fără date.
    Fiecare reclamă cu date le are pe toate cinci (9.670 din 9.670 la 30.09), deci
    contează doar platforma cu cea mai mare treaptă de afișări."""
    if not s:
        return 0, 2
    trepte = []
    for bucata in s.split(";"):
        if bucata:
            nume, rest = bucata.split(":", 1)
            jos = rest.split("-")[0]
            trepte.append((nume, int(jos) if jos else 0))
    maxim = max(v for _, v in trepte)
    if maxim == 0:
        return 0, 1
    return sum(PLATFORME.get(n, 0) for n, v in trepte if v == maxim), 0


def tintire(s):
    if not s or s == "null":
        return None
    d = json.loads(s)
    return "".join(CODURI.get(d.get(k), "u") for k in CRITERII)


def main(cale_date, cale_pagina):
    reclame = citeste(cale_date)
    with open(os.path.join(AICI, "google_advertiseri.csv"), encoding="utf-8") as f:
        ids = {r["advertiser_id"]: r for r in csv.DictReader(f)}
    ultima = max(datetime.date.fromisoformat(r["last_shown"]) for r in reclame)

    banci, advertiseri, teme, agentii, randuri = [], [], [], [], []
    sarite = collections.Counter()
    for r in reclame:
        x = ids.get(r["advertiser_id"])
        if x is None:
            sarite["ID neclasificat în google_advertiseri.csv"] += 1
            continue
        platitor = (r.get("ad_funded_by") or "").strip()
        if x["rol"] == "banca":
            banca, agentie = x["banca"], platitor or None
        elif x["rol"] == "agentie" and platitor and NUME.get(x["banca"], x["banca"]).split()[0].upper() in platitor.upper():
            # Reclama e publicată de agenție, dar plătită de bancă (Intesa prin WPP).
            banca, agentie = x["banca"], r.get("advertiser_disclosed_name") or x["advertiser"]
        else:
            sarite[f"rol {x['rol']}"] += 1
            continue
        for lista, valoare in ((banci, banca), (advertiseri, r["advertiser_id"])):
            if valoare not in lista:
                lista.append(valoare)
        tema = TEME.get(r["topic"], r["topic"] or "nespecificată")
        if tema not in teme:
            teme.append(tema)
        ag = None
        if agentie:
            agentie = AGENTII.get(agentie.strip(), agentie.strip())
            if agentie not in agentii:
                agentii.append(agentie)
            ag = agentii.index(agentie)
        masca, cod = platforma(r.get("platforme"))
        jos, sus = r["times_shown_lower_bound"], r["times_shown_upper_bound"]
        nr_tari = r.get("nr_tari")
        randuri.append([banci.index(banca), advertiseri.index(r["advertiser_id"]), r["creative_id"],
                        FORMATE[r["ad_format_type"]], teme.index(tema), r["first_shown"], r["last_shown"],
                        int(jos) if jos is not None else None,
                        (-1 if int(sus) == INT64_MAX else int(sus)) if sus is not None else None,
                        masca, cod, tintire(r.get("tintire")), ag,
                        # Nicio reclamă n-are sub 2 intrări de țară (30.09), deci una pare
                        # un total: 2 înseamnă doar România.
                        (1 if int(nr_tari) == 2 else 0) if nr_tari is not None else None,
                        r.get("times_shown_availability_date")])

    date = {"ultima": ultima.isoformat(),
            "prag7": (ultima - datetime.timedelta(days=6)).isoformat(),
            "prag30": (ultima - datetime.timedelta(days=29)).isoformat(),
            "banci": [{"nume": NUME.get(b, b), "tag": ETICHETE.get(b)} for b in banci],
            "advertiseri": advertiseri, "teme": teme, "agentii": agentii, "r": randuri}
    with open(os.path.join(AICI, "galerie_sablon.html"), encoding="utf-8") as f:
        sablon = f.read()
    assert sablon.count("__DATE__") == 1
    pagina = sablon.replace("__DATE__", json.dumps(date, ensure_ascii=False, separators=(",", ":")))
    with open(cale_pagina, "w", encoding="utf-8") as f:
        f.write(pagina)
    print(f"{len(randuri)} reclame în galerie, {len(banci)} bănci, ultima zi {ultima}; "
          f"{len(pagina.encode()) / 1e6:.2f} MB; agenții: {agentii}; sărite: {dict(sarite)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
