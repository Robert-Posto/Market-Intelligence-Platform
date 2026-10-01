"""Test: reclamele băncilor din Microsoft Advertising Ad Library (Bing), livrate în România.

API public (fără cont), documentat la
learn.microsoft.com/en-us/advertising/guides/ad-library-api. Reguli:
  - fiecare adresă trece întâi prin `flux.permite` (robots.txt), cu UA-ul proiectului;
  - pauză între cereri; la 429 sau 5xx repetat, oprire (fără reîncercări agresive);
  - rezultatul merge într-UN fișier local, în `output/reclame/` (ignorat de git),
    NU în bază: tabela de reclame vine cu migrarea 019, după avizul juridic;
  - nu se descarcă imagini (AssetJson rămâne text, cum vine).

Rulare (din rădăcina repo-ului):
    python ingest/microsoft_ad_library.py [--banca ing]

Se pornește și din Overview („Rulări”), doar cu `MIP_PERMITE_RULARI=1`.
"""
import argparse
import datetime
import json
import os
import re
import sys
import time
import unicodedata

# Rădăcina repo-ului, relativ la fișier: scriptul a stat întâi în afara
# repo-ului, cu calea laptopului scrisă în cod.
MIP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(MIP, "ingest"), MIP]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import requests                     # noqa: E402
import flux                         # noqa: E402
from crawler import UA              # noqa: E402

BAZA = "https://adlibrary.api.bingads.microsoft.com/api/v1/"
RO = 226                            # codul României în tabelul oficial al documentației
PAUZA = 10.0                        # ~10 cereri pe minut: fără cont, limita e mică (429 după 10 cereri rapide)
H = {"User-Agent": UA, "Accept": "application/json"}

# Ce căutăm pentru fiecare bancă (numele advertiserilor diferă: ING apare ca
# „ING BANK N.V.AMSTERDAM SUCURSALA BUCURESTI", Raiffeisen ca „Raiffeisen Bank
# International"). `potrivire` = cuvintele care trebuie să apară în numele
# advertiserului ca să-l atribuim băncii.
BANCI = {
    "banca-transilvania": (["Banca Transilvania", "BT Pay"], ["transilvania"]),
    "bankofchina": (["Bank of China"], ["bank of china"]),
    "banorient": (["Banorient"], ["banorient"]),
    "bcr": (["Banca Comerciala Romana", "BCR"], ["banca comerciala romana", "bcr"]),
    "bcr-locuinte": (["BCR Banca pentru Locuinte"], ["locuinte"]),
    "bid": (["Banca de Investitii si Dezvoltare"], ["investitii si dezvoltare"]),
    "bnpparibas": (["BNP Paribas"], ["bnp paribas"]),
    "brci": (["Banca Romana de Credite si Investitii", "BRCI"], ["credite si investitii", "brci"]),
    "brd": (["BRD Groupe Societe Generale", "BRD"], ["brd"]),
    "cec": (["CEC Bank"], ["cec bank"]),
    "cetelem": (["Cetelem", "BNP Paribas Personal Finance"], ["cetelem", "personal finance"]),
    "citibank": (["Citibank"], ["citibank", "citigroup"]),
    "credex": (["Credex"], ["credex"]),
    "creditcoop": (["Creditcoop", "Banca Centrala Cooperatista"], ["creditcoop", "cooperatista"]),
    "exim": (["Exim Banca Romaneasca", "EximBank"], ["exim"]),
    "garanti": (["Garanti BBVA", "Garanti Bank"], ["garanti"]),
    "ing": (["ING Bank"], ["ing bank"]),
    "intesa": (["Intesa Sanpaolo"], ["intesa"]),
    "libra": (["Libra Internet Bank"], ["libra internet"]),
    "nexent": (["Nexent Bank"], ["nexent"]),
    "patria": (["Patria Bank"], ["patria bank"]),
    "pko": (["PKO Bank Polski"], ["pko"]),
    "procredit": (["ProCredit"], ["procredit"]),
    "raiffeisen": (["Raiffeisen Bank"], ["raiffeisen"]),
    "revolut": (["Revolut"], ["revolut"]),
    "salt": (["Salt Bank"], ["salt bank"]),
    "tbi": (["tbi bank"], ["tbi bank"]),
    "techventures": (["TechVentures Bank"], ["techventures"]),
    "unicredit": (["UniCredit Bank", "UniCredit"], ["unicredit"]),
    "vista": (["Vista Bank"], ["vista bank"]),
}


def simplu(t):
    t = unicodedata.normalize("NFD", t or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


class Oprire(Exception):
    pass


JURNAL = []


def cere(cale, params):
    url = BAZA + cale
    if not flux.permite(url, "microsoft_adlibrary"):
        raise Oprire(f"robots.txt interzice {url}")
    # Respectăm limita: la 429 așteptăm 90 s și încercăm o dată; trei 429 la rând = oprire.
    for incercare in range(2):
        time.sleep(PAUZA if incercare == 0 else 90)
        r = requests.get(url, params=params, headers=H, timeout=40)
        JURNAL.append({"url": r.url, "status": r.status_code, "la": datetime.datetime.now().isoformat(timespec="seconds")})
        if r.status_code != 429:
            cere.la_rand = 0
            break
        cere.la_rand = getattr(cere, "la_rand", 0) + 1
        if cere.la_rand >= 3:
            raise Oprire(f"trei răspunsuri 429 la rând ({r.url}) — ne oprim")
    if r.status_code == 429 or r.status_code >= 500:
        raise Oprire(f"HTTP {r.status_code} la {r.url} — ne oprim")
    if r.status_code != 200:
        # o cerere respinsă (400) nu oprește tot: se jurnalizează și se trece mai departe
        return {"value": [], "eroare": f"HTTP {r.status_code}: {r.text[:200]}"}
    return r.json()


def advertiseri(slug):
    cautari, potrivire = BANCI[slug]
    gasiti = {}
    for c in cautari:
        for a in cere("Advertisers", {"searchText": c, "top": 24}).get("value", []):
            nume = simplu(a["AdvertiserName"])
            if any(re.search(rf"\b{re.escape(p)}\b", nume) for p in potrivire):
                gasiti[a["AdvertiserId"]] = a
    return list(gasiti.values())


def reclame_ro(adv_id, max_reclame=200):
    tot, skip = [], 0
    while len(tot) < max_reclame:
        d = cere("Ads", {"advertiserId": adv_id, "countryCodes": RO, "top": 24, "skip": skip})
        v = d.get("value", [])
        tot += v
        if len(v) < 24:
            break
        skip += 24
    return tot


def detalii(ad_id):
    return cere(f"Ads/{ad_id}", {"$expand": "AdDetails($expand=ImpressionsByCountry,Targets)"}).get("AdDetails")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--banca", help="doar o bancă (slug)")
    a = ap.parse_args()
    azi = datetime.date.today().isoformat()
    rez = {"sursa": "Microsoft Advertising Ad Library API", "baza": BAZA, "tara": "RO (226)",
           "fotografie": azi, "ua": UA, "banci": {}}
    # completare: băncile deja extrase azi nu se mai cer din nou (fișierul rămâne unul singur)
    vechi = os.path.join(MIP, "output", "reclame", f"microsoft_{azi}.json")
    if os.path.exists(vechi):
        v = json.load(open(vechi, encoding="utf-8"))
        rez["banci"] = v.get("banci", {})
        JURNAL.extend(v.get("cereri", []))
        rez.pop("oprit", None)
    try:
        for slug in ([a.banca] if a.banca else [s for s in BANCI if s not in rez["banci"]]):
            advs = advertiseri(slug)
            intrare = {"advertiseri": advs, "reclame": []}
            for adv in advs:
                for r in reclame_ro(adv["AdvertiserId"]):
                    r["AdDetails"] = detalii(r["AdId"])
                    r["link_biblioteca"] = f"https://adlibrary.ads.microsoft.com/ad/{r['AdId']}"
                    intrare["reclame"].append(r)
            rez["banci"][slug] = intrare
            print(f"{slug:20} advertiseri {len(advs):2}  reclame RO {len(intrare['reclame']):3}", flush=True)
            salveaza(rez)
    except Oprire as e:
        rez["oprit"] = str(e)
        print("OPRIT:", e)
    print(f"{len(JURNAL)} cereri · scris {salveaza(rez)}")


def salveaza(rez):
    rez["cereri"] = JURNAL
    d = os.path.join(MIP, "output", "reclame")
    os.makedirs(d, exist_ok=True)
    cale = os.path.join(d, f"microsoft_{rez['fotografie']}.json")
    with open(cale, "w", encoding="utf-8") as f:
        json.dump(rez, f, ensure_ascii=False, indent=1)
    return cale


if __name__ == "__main__":
    main()
