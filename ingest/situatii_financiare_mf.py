"""Situațiile financiare anuale ale instituțiilor de credit, din datele deschise ale MF.

Sursa: setul „Situații financiare <an>” al Ministerului Finanțelor pe data.gov.ro (API CKAN,
fără cheie), fișierul instituțiilor de credit (`WEB_Inst_de_credit_<an>.txt`): un rând pe CUI,
cu indicatorii I1–I23 din bilanț și din contul de profit. Denumirile vin de la ANAF (API-ul public
de verificare a plătitorilor, max. 100 de CUI pe cerere). Măsurat pe 09.10.2026: 2012–2025,
101 CUI distincte (30 dintre ele sunt băncile monitorizate, 48 sunt bănci cooperatiste).

De ce o mapare pe ani: coloanele I1–I23 nu înseamnă același lucru în toți anii. Trei forme:
  - 2012–2013, 19 indicatori: fără „investiții în filiale”, profitul pe I16–I19;
  - 2014–2017, 21 de indicatori, schema dinainte de IFRS 9 (I4 active disponibile pentru vânzare,
    I5 credite și creanțe);
  - 2018–2025, schema IFRS 9 (I6 active la cost amortizat); din 2023 apare „Venituri totale din
    exploatare” pe I18, deci profitul se mută cu o coloană.
Pozițiile vechi (fără dicționar publicat înainte de 2019) au fost verificate pe cifre publice:
profitul net BT 1,23 mld lei (2016), 1,19 mld (2017), 1,22 mld (2018); capitalul social Libra
202 mil. (2012), 231 mil. (2014), 506 mil. (2018). Anul 2011 iese: fișierul amestecă băncile cu
IFN-urile (CAEN 6491/6492, 304 rânduri) și are altă schemă.

„Active totale” nu e o coloană: e suma posturilor de activ publicate (numerar, active financiare,
participații, imobilizări). Alte active (creanțe fiscale, alte active) lipsesc din fișier, deci
cifra e o aproximare consecventă de la an la an, nu totalul din bilanț.

Rulare:
    python ingest/situatii_financiare_mf.py            # descarcă ce lipsește + refă JSON-ul
    python ingest/situatii_financiare_mf.py --toate    # descarcă din nou toți anii
    python ingest/situatii_financiare_mf.py --offline  # doar refă JSON-ul din fișierele salvate
Ieșiri: date/situatii_financiare/inst_credit_<an>.txt (brute, neschimbate), cui_anaf.json,
și date/situatii_financiare.json (citit de /api/situatii_banci).
"""
import argparse
import datetime
import json
import os
import re
import sys
import time
import urllib.request

AICI = os.path.dirname(os.path.abspath(__file__))
RADACINA = os.path.dirname(AICI)
sys.path[:0] = [RADACINA, AICI]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from crawler import UA             # noqa: E402

CKAN = "https://data.gov.ro/api/3/action/"
ANAF = "https://webservicesp.anaf.ro/api/PlatitorTvaRest/v9/tva"
DOSAR = os.path.join(RADACINA, "date", "situatii_financiare")
IESIRE = os.path.join(RADACINA, "date", "situatii_financiare.json")
PRIMUL_AN = 2012

# CUI -> slug-ul băncii monitorizate (tabela `banci`). Verificat pe denumirile ANAF din 09.10.2026.
# Patria are două CUI: 4786360 e banca absorbită în 2017 (fosta Nextebank), 11447021 cea de azi.
SLUG = {
    5022670: "banca-transilvania", 41819399: "bankofchina", 22385331: "banorient", 361757: "bcr",
    23739062: "bcr-locuinte", 49176892: "bid", 37928029: "bnpparibas", 1596646: "brci", 361579: "brd",
    361897: "cec", 38627806: "cetelem", 24882493: "citibank", 16489311: "credex", 361323: "creditcoop",
    361560: "exim", 25394008: "garanti", 6151100: "ing", 8145422: "intesa", 8119644: "libra",
    50637620: "nexent", 11447021: "patria", 45978630: "pko", 14622194: "procredit", 361820: "raiffeisen",
    48273978: "revolut", 10318789: "salt", 30771201: "tbi", 25263452: "techventures", 361536: "unicredit",
    10556861: "vista",
}

# indicatorii comuni, pe forma fișierului: coloana (1 = I1) sau o listă de coloane de adunat
ACTIVE = {"A": list(range(1, 9)), "B": list(range(1, 10)), "C": list(range(1, 10)), "D": list(range(1, 10))}
# Profitul net e I17 („Profit sau pierdere aferent exercițiului”, din bilanț) în toate formele: coloanele
# contului de profit de după el se mută de la an la an (2022 are deja I18 „Venituri totale”, dar n-are
# încă I22). Verificat: Libra 6,0 mil. (2012), 32,5 (2016), 115,3 (2019), 238,2 (2022), 317,3 (2023).
# „Venituri totale” (I18 din 2022) nu se folosește: la BT dă 108–115 mld lei pe an, de ~15 ori venitul ei.
FORME = {
    # 2012–2013: I5 credite și creanțe, I7–I8 imobilizări (fără participații), I16 profit înainte de impozit
    "A": {"numerar": 1, "credite": 5, "datorii": 12, "capital_social": 14, "profit_brut": 16, "profit_net": 17},
    # 2014–2017 (înainte de IFRS 9): I5 credite și creanțe, I18 profit înainte de impozit
    "B": {"numerar": 1, "credite": 5, "datorii": 12, "capital_social": 14, "profit_brut": 18, "profit_net": 17},
    # 2018–2021 (IFRS 9): I6 active la cost amortizat, I18 profit înainte de impozit
    "C": {"numerar": 1, "credite": 6, "datorii": 12, "capital_social": 14, "profit_brut": 18, "profit_net": 17},
    # 2022–2025: I18 devine „Venituri totale”, profitul înainte de impozit trece pe I19
    "D": {"numerar": 1, "credite": 6, "datorii": 12, "capital_social": 14, "profit_brut": 19, "profit_net": 17},
}


def forma(an):
    return "A" if an <= 2013 else "B" if an <= 2017 else "C" if an <= 2021 else "D"


def cere(url, corp=None):
    antete = {"User-Agent": UA}
    if corp is not None:
        antete["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=corp, headers=antete)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def fisiere_pe_ani():
    """{an: url} — fișierul de date al instituțiilor de credit, găsit prin căutarea CKAN.

    Identificatorii seturilor nu urmează un tipar („situatii_financiare2023”, fără „_”), iar
    seturile 2020 și 2021 conțin și anii trecuți: se preferă setul anului, apoi cel mai nou.
    """
    gasite = {}
    rez = json.loads(cere(CKAN + "package_search?q=situatii%20financiare&rows=100"))["result"]["results"]
    ids = {p["name"] for p in rez}
    for an in range(PRIMUL_AN, datetime.date.today().year + 1):
        ids.add(f"situatii_financiare_{an}")
    for i in sorted(ids):
        try:
            p = json.loads(cere(CKAN + "package_show?id=" + i))["result"]
        except Exception:
            continue
        # „Situații financiare 2023”, dar „Situațiile financiare 2024”
        if not re.match(r"Situa\w+ financiare \d{4}\s*$", p.get("title", "")):
            continue
        an_set = p["title"][-4:]
        for x in p["resources"]:
            n = x.get("name") or ""
            m = re.search(r"(20\d\d)", n)
            if not (m and re.search(r"inst.*credit", n, re.I)) or n.lower().endswith(".csv"):
                continue
            an = int(m.group(1))
            if an < PRIMUL_AN:
                continue
            # ordinea de preferință: setul anului > fișierul „actualizat” > setul cel mai nou
            cheie = (an_set == str(an), "actualizat" in n.lower(), an_set)
            if an not in gasite or cheie > gasite[an][0]:
                gasite[an] = (cheie, x["url"], p["name"], n)
    return {an: v[1:] for an, v in sorted(gasite.items())}


def descarca(toate):
    os.makedirs(DOSAR, exist_ok=True)
    for an, (url, setul, nume) in fisiere_pe_ani().items():
        cale = os.path.join(DOSAR, f"inst_credit_{an}.txt")
        if os.path.exists(cale) and not toate:
            continue
        b = cere(url)
        if not b.lstrip(b"\xef\xbb\xbf").startswith(b"CUI,"):
            print(f"{an}: {nume} nu are capul așteptat (CUI,...), sărit")
            continue
        with open(cale, "wb") as f:
            f.write(b)
        print(f"{an}: {nume} ({setul}), {len(b)} octeți")
        time.sleep(1)


def citeste():
    """{an: {cui: [I1, I2, ...]}} din fișierele salvate."""
    date = {}
    for f in sorted(os.listdir(DOSAR)):
        m = re.match(r"inst_credit_(\d{4})\.txt$", f)
        if not m:
            continue
        an = int(m.group(1))
        randuri = open(os.path.join(DOSAR, f), encoding="utf-8", errors="replace").read().lstrip("﻿").splitlines()
        date[an] = {}
        for r in randuri[1:]:
            p = r.split(",")
            if not p or not p[0].strip().isdigit():
                continue
            # p[0] CUI, p[1] CAEN, apoi I1, I2, ...; câmp gol = indicator neraportat
            date[an][int(p[0])] = [float(x) if x.strip() not in ("", "-") else None for x in p[2:]]
    return date


def nume_anaf(cuis):
    """Denumirile de la ANAF, ținute în cui_anaf.json: se cer doar CUI-urile noi."""
    cale = os.path.join(DOSAR, "cui_anaf.json")
    nume = json.load(open(cale, encoding="utf-8")) if os.path.exists(cale) else {}
    lipsa = [c for c in cuis if str(c) not in nume]
    zi = datetime.date.today().isoformat()
    for i in range(0, len(lipsa), 100):
        corp = json.dumps([{"cui": c, "data": zi} for c in lipsa[i:i + 100]]).encode()
        d = json.loads(cere(ANAF, corp))
        for x in d.get("found", []):
            nume[str(x["date_generale"]["cui"])] = x["date_generale"]["denumire"]
        for c in d.get("notFound", []):
            nume[str(c)] = None
        time.sleep(1.2)  # ANAF: cel mult o cerere pe secundă
    with open(cale, "w", encoding="utf-8") as f:
        json.dump(nume, f, ensure_ascii=False, indent=1, sort_keys=True)
    return nume


def tip(nume):
    n = (nume or "").upper()
    if "COOPERATIV" in n:
        return "cooperativa"
    if "SUCURSALA" in n or "SUCURSALĂ" in n:
        return "sucursala"
    return "banca"


def normalizeaza(date, nume):
    banci = {}
    total = {}
    for an, randuri in sorted(date.items()):
        f = forma(an)
        total[an] = {}
        for cui, v in randuri.items():
            val = lambda i: v[i - 1] if i - 1 < len(v) else None   # noqa: E731
            ind = {k: val(i) for k, i in FORME[f].items()}
            active = [val(i) for i in ACTIVE[f]]
            ind["active"] = sum(x for x in active if x) if any(x is not None for x in active) else None
            b = banci.setdefault(cui, {"cui": cui, "nume": nume.get(str(cui)) or f"CUI {cui}",
                                       "slug": SLUG.get(cui), "tip": tip(nume.get(str(cui))), "valori": {}})
            b["valori"][str(an)] = {k: (round(x) if x is not None else None) for k, x in ind.items()}
            for k, x in ind.items():
                if x is not None:
                    total[an][k] = total[an].get(k, 0) + x
    for b in banci.values():
        ani = sorted(int(a) for a in b["valori"])
        b["primul_an"], b["ultimul_an"] = ani[0], ani[-1]
    # Goluri: o bancă prezentă în anul dinainte și în cel de după, dar lipsă din fișierul anului.
    # Măsurat: BRD lipsește din fișierul pe 2021 (~9% din active), deci totalul pe 2021 iese mic și
    # cotele tuturor celorlalte bănci din 2021 sunt umflate (BT sare la 22%). Pagina avertizează.
    goluri = {}
    for b in banci.values():
        for an in sorted(date)[1:-1]:
            if str(an) not in b["valori"] and str(an - 1) in b["valori"] and str(an + 1) in b["valori"]:
                v = b["valori"][str(an - 1)].get("active") or 0
                goluri.setdefault(str(an), []).append({"cui": b["cui"], "nume": b["nume"],
                                                       "cota_estimata": round(100 * v / total[an - 1]["active"], 2)})
    return {
        "sursa": "Ministerul Finanțelor, data.gov.ro — Situații financiare (instituții de credit); denumiri: ANAF",
        "generat_la": datetime.datetime.now().isoformat(timespec="seconds"),
        "ani": sorted(date),
        "forme": {str(an): forma(an) for an in sorted(date)},
        "total": {str(an): {k: round(x) for k, x in t.items()} for an, t in total.items()},
        "goluri": goluri,
        "banci": sorted(banci.values(), key=lambda b: (b["slug"] != "libra", b["nume"])),
    }


def main():
    ap = argparse.ArgumentParser(description="Situațiile financiare ale băncilor, din datele deschise MF")
    ap.add_argument("--toate", action="store_true", help="descarcă din nou toți anii")
    ap.add_argument("--offline", action="store_true", help="doar refă JSON-ul din fișierele salvate")
    a = ap.parse_args()
    if not a.offline:
        descarca(a.toate)
    date = citeste()
    cuis = sorted({c for r in date.values() for c in r})
    nume = nume_anaf(cuis) if not a.offline else json.load(open(os.path.join(DOSAR, "cui_anaf.json"), encoding="utf-8"))
    rez = normalizeaza(date, nume)
    with open(IESIRE, "w", encoding="utf-8") as f:
        json.dump(rez, f, ensure_ascii=False)
    lib = next(b for b in rez["banci"] if b["slug"] == "libra")
    u = str(rez["ani"][-1])
    print(f"{len(rez['ani'])} ani ({rez['ani'][0]}–{rez['ani'][-1]}), {len(rez['banci'])} entități; "
          f"Libra {u}: active {lib['valori'][u]['active'] / 1e9:.2f} mld lei, "
          f"cotă {100 * lib['valori'][u]['active'] / rez['total'][u]['active']:.2f}% → {IESIRE}")


if __name__ == "__main__":
    main()
