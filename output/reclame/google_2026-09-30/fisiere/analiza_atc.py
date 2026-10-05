"""Rezumatul pe bancă al unei fotografii Google Ads Transparency descărcate din
BigQuery (un rând pe reclamă livrată în RO). Numără doar din fișier: nicio
interogare nouă, nimic scris în bază. Merge și cu JSON-ul din 29.09 (11 coloane),
și cu CSV-ul din fotografie.sql (22 de coloane, din 30.09).

    python output/reclame/analiza_atc.py output/reclame/atc_ro_2026-09-30.csv
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
FORMATE = ("TEXT", "IMAGE", "VIDEO")
INT64_MAX = 2 ** 63 - 1
LUNI = ("ian", "feb", "mar", "apr", "mai", "iun", "iul", "aug", "sep", "oct", "nov", "dec")


def zi(s):
    return datetime.date.fromisoformat(s)


def citeste(cale):
    with open(cale, encoding="utf-8", newline="") as f:
        if cale.lower().endswith(".csv"):
            # În CSV-ul din consolă, valorile lipsă vin ca șir gol.
            return [{k: (v if v != "" else None) for k, v in r.items()} for r in csv.DictReader(f)]
        return json.load(f)


def grup_pentru(adv, reclama):
    if adv["rol"] == "banca":
        return adv["banca"]
    if adv["rol"] == "filiala":
        return f"{adv['banca']} filiale"
    # O agenție contează la bancă doar când „plătit de” o numește: Intesa publică prin
    # WPP Media Romania (42 de reclame, 30.09); la Sense8 (BRD) plătitorul e gol.
    platitor = (reclama.get("ad_funded_by") or "").upper()
    if adv["rol"] == "agentie" and platitor and adv["banca"].upper() in platitor:
        return adv["banca"]
    return None


def platforma_principala(s):
    """Fiecare reclamă cu date are toate cele 5 platforme (9.670 din 9.670, 30.09),
    deci contează doar cea cu treapta de afișări cea mai mare."""
    if not s:
        return "fără date"
    trepte = [(b.split(":")[0], int(b.split(":")[1].split("-")[0] or 0)) for b in s.split(";") if b]
    maxim = max(v for _, v in trepte)
    return "sub 1.000 peste tot" if maxim == 0 else "+".join(n for n, v in trepte if v == maxim)


def main(cale):
    reclame = citeste(cale)
    with open(os.path.join(AICI, "google_advertiseri.csv"), encoding="utf-8") as f:
        ids = {r["advertiser_id"]: r for r in csv.DictReader(f)}
    necunoscute = {r["advertiser_id"] for r in reclame} - set(ids)
    if necunoscute:
        sys.exit(f"ID-uri neclasificate în google_advertiseri.csv: {sorted(necunoscute)}")

    # Setul apare cu ~1 zi întârziere (ultima afișare 28.09 într-o descărcare
    # din 29.09), deci „azi” e ultima zi din date, nu data rulării.
    ultima = max(zi(r["last_shown"]) for r in reclame)
    prag_7, prag_30 = ultima - datetime.timedelta(days=6), ultima - datetime.timedelta(days=29)
    an = ultima.year

    grupe = collections.defaultdict(list)
    excluse = collections.Counter()
    for r in reclame:
        g = grup_pentru(ids[r["advertiser_id"]], r)
        if g:
            grupe[g].append(r)
        else:
            excluse[ids[r["advertiser_id"]]["rol"]] += 1
    ordine = sorted(grupe.items(), key=lambda x: -len(x[1]))

    print(f"# Google Ads Transparency, reclame livrate în RO: {os.path.basename(cale)}\n")
    print(f"{len(reclame)} de reclame în fișier, ultima zi din date {ultima:%d.%m.%Y}; "
          f"lăsate deoparte, pe rol: {dict(excluse) or 'niciuna'}.\n")
    sfarsit_afisari = max((r["times_shown_end_date"] for r in reclame if r["times_shown_end_date"]), default=None)
    print("| bancă | reclame în RO | active în ultimele 7 zile | noi în ultimele 30 de zile "
          f"| text / imagine / video | prima afișare | afișări până la {sfarsit_afisari}, mil. |")
    print("|---|---:|---:|---:|---|---|---:|")
    for g, rs in ordine:
        active = sum(1 for r in rs if zi(r["last_shown"]) >= prag_7)
        noi = sum(1 for r in rs if zi(r["first_shown"]) >= prag_30)
        fmt = collections.Counter(r["ad_format_type"] for r in rs)
        # Intervalele de afișări vin cu 90 de zile întârziere (până la 30.06 în
        # fotografia din 29.09, până la 01.07 în cea din 30.09). Ultima treaptă e
        # „peste 10 milioane”, cu limita de sus INT64 maxim: acolo rămâne doar minimul.
        cu = [r for r in rs if r["times_shown_lower_bound"] is not None]
        jos = sum(int(r["times_shown_lower_bound"]) for r in cu)
        deschise = [r for r in cu if int(r["times_shown_upper_bound"]) == INT64_MAX]
        sus = sum(int(r["times_shown_upper_bound"]) for r in cu if r not in deschise)
        afisari = f"≥ {jos / 1e6:.0f}" if deschise else f"{jos / 1e6:.0f}–{sus / 1e6:.0f}"
        print(f"| {g} | {len(rs)} | {active} | {noi} | "
              f"{' / '.join(str(fmt.get(k, 0)) for k in FORMATE)} | "
              f"{zi(min(r['first_shown'] for r in rs)):%d.%m.%Y} | {afisari} |")
    print("\nAfișările adună intervalele publicate pe fiecare reclamă, pe toată durata ei;"
          " duratele diferă între bănci, deci e un ordin de mărime.\n")

    if "tintire" in reclame[0]:
        print("## Platformă, liste de clienți, țări și agenție (câmpurile din 30.09)\n")
        print("| bancă | YouTube principal | Search principal | fără platformă clară | exclude o listă de clienți "
              "| țintește o listă | doar în România | agenție (plătit de / publicat de) |")
        print("|---|---:|---:|---:|---:|---:|---:|---|")
        for g, rs in ordine:
            n = len(rs)
            plat = collections.Counter(platforma_principala(r.get("platforme")) for r in rs)
            liste = collections.Counter(json.loads(r["tintire"])["customer_lists"] for r in rs if r.get("tintire"))
            # Nicio reclamă n-are sub 2 intrări de țară (30.09): una pare un total.
            doar_ro = sum(1 for r in rs if r.get("nr_tari") and int(r["nr_tari"]) == 2)
            agentii = collections.Counter((r.get("ad_funded_by") or "").strip() for r in rs
                                          if ids[r["advertiser_id"]]["rol"] == "banca" and r.get("ad_funded_by"))
            agentii.update(r.get("advertiser_disclosed_name") for r in rs if ids[r["advertiser_id"]]["rol"] == "agentie")
            neclar = plat["fără date"] + plat["sub 1.000 peste tot"]
            print(f"| {g} | {plat['YOUTUBE']} | {plat['SEARCH']} | {neclar} | "
                  f"{liste['CRITERIA_EXCLUDED'] * 100 // n}% | {liste['CRITERIA_INCLUDED'] * 100 // n}% | "
                  f"{doar_ro * 100 // n}% | {', '.join(f'{a} ({c})' for a, c in agentii.most_common()) or '-'} |")
        print()

    luni = range(1, ultima.month + 1)
    print(f"## Reclame noi pe lună, {an} (după prima afișare în RO)\n")
    print("| bancă | " + " | ".join(LUNI[m - 1] for m in luni) + " |")
    print("|---|" + "---:|" * len(luni))
    for g, rs in ordine:
        pe_luna = collections.Counter(zi(r["first_shown"]).month for r in rs if zi(r["first_shown"]).year == an)
        print(f"| {g} | " + " | ".join(str(pe_luna.get(m, 0)) for m in luni) + " |")

    # Google păstrează doar reclamele afișate în ultimul an: pe 30.09 au ieșit din
    # set 27 de reclame cu ultima afișare pe 28.09.2025, exact la un an. Istoricul
    # mai vechi există doar dacă îl păstrăm noi.
    vechi = [r for r in reclame if zi(r["last_shown"]) < ultima - datetime.timedelta(days=365)]
    print(f"\nUltima afișare cu peste un an înainte de {ultima:%d.%m.%Y}: {len(vechi)} reclame, "
          f"{dict(collections.Counter(ids[r['advertiser_id']]['advertiser'] for r in vechi))}.")


if __name__ == "__main__":
    main(sys.argv[1])
