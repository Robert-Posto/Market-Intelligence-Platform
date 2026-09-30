"""TikTok: reclamele băncilor livrate în România și postările organice ale conturilor lor.

Două produse TikTok for Developers, cu aprobări SEPARATE (contul poate avea unul,
ambele sau niciunul — scriptul le încearcă pe rând și spune care a refuzat):

  1. Commercial Content API (Ad Library, art. 39 DSA), scope `research.adlib.basic`
     developers.tiktok.com/doc/commercial-content-api-query-advertisers
     developers.tiktok.com/doc/commercial-content-api-query-ads
     developers.tiktok.com/doc/commercial-content-api-get-ad-details
     - POST /v2/research/adlib/advertiser/query/  corp {search_term ≤50 car., max_count ≤50};
       câmpuri business_id, business_name, country_code. Fără paginare documentată.
     - POST /v2/research/adlib/ad/query/  corp {filters, search_term, search_type
       'exact_phrase' | 'fuzzy_phrase', max_count ≤10 (!), search_id}. Filtrul
       obligatoriu `ad_published_date_range` {min, max} YYYYMMDD, cu `min` „în ultimul
       an"; țara prin `country_code_list` (tabelul documentației; exemplul curl scrie
       `country_code`, noi urmăm tabelul). NU există filtru pe advertiser: căutăm după
       numele advertiserului atribuit și păstrăm doar reclamele cu business_id-ul lui.
       Paginare: `has_more` + `search_id` întors de răspuns.
     - POST /v2/research/adlib/ad/detail/  corp {ad_id}: titlu, external_url,
       call_to_action, advertising_objective, reach pe țări/vârste/gen, targeting.
     - Doar țările UE/SEE (RO e în listă: commercial-content-api-supported-countries);
       o reclamă rămâne în bibliotecă până la un an de la ultima afișare.
     - Limită zilnică: nedocumentată pentru adlib (pagina de rate limit listează doar
       /v2/user/info/ etc., 600/min, fereastră glisantă de un minut, 429
       `rate_limit_exceeded`).
  2. Research API, scope `research.data.basic`
     developers.tiktok.com/doc/research-api-specs-query-user-info
     developers.tiktok.com/doc/research-api-specs-query-videos
     developers.tiktok.com/doc/research-api-faq
     - POST /v2/research/user/info/  corp {username}.
     - POST /v2/research/video/query/  corp {query: {and: [{operation, field_name,
       field_values}]}, start_date, end_date YYYYMMDD cu end ≤ start + 30 zile,
       max_count ≤100, cursor, search_id}. Paginare: `cursor` + `has_more` + `search_id`.
     - Cotă: „1000 requests per day … up to 100,000 records per day across our APIs",
       resetată la 00:00 UTC. Videoclipurile noi apar în căutare după până la 48 h,
       statisticile se actualizează în până la 10 zile.

Token: POST https://open.tiktokapis.com/v2/oauth/token/ (form, grant_type=
client_credentials), valabil 2 ore (developers.tiktok.com/doc/client-access-token-management).
Documentația nu spune că răspunsul întoarce scope-urile: le raportăm dacă vin, altfel
accesul pe fiecare produs se află din primul răspuns al endpoint-ului lui.

RETENȚIA (verificat pe 30.09.2026):
  - Research Tools Terms (în vigoare din 22.01.2026), §III.3.e:
    „you agree to regularly refresh TikTok Research Data at least every thirty (30)
    days, and delete data that is not available from the TikTok Research Tools at the
    time of each refresh" — www.tiktok.com/legal/page/global/terms-of-service-research-api/en
  - Developer Terms (actualizați 26.12.2025) nu dau un interval pentru datele CCL
    (Ad Library); cer ștergerea la încetarea accesului, §VI —
    www.tiktok.com/legal/page/global/tik-tok-developer-terms-of-service/en
  Aplicăm 30 de zile ÎNTREGULUI director `output/tiktok/` (un singur fișier pe zi
  ține ambele produse): `curata()` rulează la fiecare pornire.

ATENȚIE, scopul (de citit înainte de rularea reală): ambii termeni leagă datele de
cercetare. Research Terms interzic folosirea „for any commercial or unauthorized
purpose, including beyond the scope of the approved Research", iar datele CCL sunt
permise pentru „CCL Purposes" (supravegherea riscurilor din publicitatea online).
Monitorizarea concurenței pentru marketing trebuie să încapă în proiectul aprobat.

Reguli, ca la microsoft_ad_library.py: fiecare adresă prin `flux.permite`, UA-ul
proiectului, pauză între cereri, la 429 așteptare și oprire după 3 la rând; un singur
fișier `output/tiktok/tiktok_<data>.json` (ignorat de git), salvat după fiecare bancă,
cu jurnalul cererilor; reluarea sare peste băncile făcute azi. Nu se descarcă nicio
imagine sau video: doar linkurile (CDN semnat, expiră) și metadatele. NU în bază.

Rulare:
    python ingest/tiktok_api.py --simulare            # ce s-ar cere, fără nicio cerere
    python ingest/tiktok_api.py [--banca bcr] [--doar-reclame | --doar-organic]
    python ingest/tiktok_api.py --curata              # doar retenția
"""
import argparse
import csv
import datetime
import json
import math
import os
import re
import sys
import time
import unicodedata

AICI = os.path.dirname(os.path.abspath(__file__))
RADACINA = os.path.dirname(AICI)
sys.path[:0] = [AICI, RADACINA]
import requests                     # noqa: E402
import config                       # noqa: E402
import flux                         # noqa: E402
from banks import BANKS             # noqa: E402
from crawler import UA              # noqa: E402

BAZA = "https://open.tiktokapis.com/v2/"
URL_TOKEN = BAZA + "oauth/token/"
DIR = os.path.join(RADACINA, "output", "tiktok")
CSV_RETELE = os.path.join(RADACINA, "date", "retele_sociale.csv")
ID_FLUX = "tiktok_api"

# Research Tools Terms §III.3.e: „refresh … at least every thirty (30) days".
RETENTIE_ZILE = 30
# Fără limită documentată pentru adlib: 3 s țin rularea sub 20 de cereri pe minut,
# departe de orice fereastră de un minut, și 1000 de cereri (cota Research) în ~50 min.
PAUZA = 3.0
ASTEPTARE_429 = 60.0
TARA = "RO"
ZILE_RECLAME = 364          # `min` trebuie să fie „within one year"
ZILE_ORGANIC = 90           # trei ferestre de 30 de zile, maximul pe cerere
FEREASTRA = 30
MAX_RECLAME = 200           # pe bancă, ca la Microsoft
MAX_PAGINI = 50             # plasă de siguranță pe o singură căutare

CAMPURI_ADVERTISER = "business_id,business_name,country_code"
CAMPURI_RECLAMA = ("ad.id,ad.first_shown_date,ad.last_shown_date,ad.status,ad.status_statement,"
                   "ad.videos,ad.image_urls,ad.reach,advertiser.business_id,"
                   "advertiser.business_name,advertiser.paid_for_by")
CAMPURI_DETALIU = ("ad.id,ad.title,ad.external_url,ad.call_to_action,ad.advertising_objective,"
                   "ad.reach,ad.rejection_info,advertiser.country_code,advertiser.profile_url,"
                   "advertiser.follower_count,ad_group.targeting_info")
CAMPURI_PROFIL = ("display_name,bio_description,avatar_url,is_verified,follower_count,"
                  "following_count,likes_count,video_count,bio_url")
CAMPURI_VIDEO = ("id,create_time,username,region_code,video_description,hashtag_names,"
                 "view_count,like_count,comment_count,share_count,favorites_count,video_duration")

# Codurile TikTok care înseamnă „produsul nu e aprobat pentru tokenul ăsta".
COD_REFUZ = {"scope_not_authorized", "scope_permission_missed", "access_token_invalid",
             "permission_denied", "unauthorized"}

# slug -> (domeniul din banks.py, căutări, `contine`, `nume`).
# Atribuirea e strictă, pe cuvinte întregi: la Bing, căutarea „BCR"/„BRD" a prins
# firme fără legătură. `contine` = numele juridic sau o sintagmă care apare doar la
# banca din România; `nume` = numele întreg al advertiserului, după ce se taie forma
# juridică de la coadă (S.A., EAD, N.V., UAB...). Restul advertiserilor găsiți merg
# în `advertiseri_neatribuiti`, pentru verificare umană: „ING Bank" simplu poate fi
# ING Bank Śląski, „Intesa Sanpaolo Bank" e și banca din Slovenia.
BANCI = {
    "banca-transilvania": ("bancatransilvania.ro", ["Banca Transilvania"], ["banca transilvania"], ["bt"]),
    "bankofchina": ("bankofchina.com", ["Bank of China"], ["bank of china cee"], []),
    "banorient": ("banorientfrance.com", ["Banorient"], ["banorient"], []),
    "bcr": ("bcr.ro", ["Banca Comerciala Romana", "BCR"], ["banca comerciala romana"], ["bcr"]),
    "bcr-locuinte": ("bcrlocuinte.ro", ["BCR Banca pentru Locuinte"], ["banca pentru locuinte"], []),
    "bid": ("bidromania.eu", ["Banca de Investitii si Dezvoltare"], ["banca de investitii si dezvoltare"], []),
    "bnpparibas": ("romania.bnpparibas.com", ["BNP Paribas"], ["bnp paribas s a paris sucursala bucuresti"], []),
    "brci": ("brci.ro", ["Banca Romana de Credite si Investitii", "BRCI"], ["banca romana de credite si investitii"], ["brci"]),
    "brd": ("brd.ro", ["BRD Groupe Societe Generale", "BRD"], ["brd groupe societe generale"], ["brd"]),
    "cec": ("cec.ro", ["CEC Bank"], ["cec bank"], ["cec"]),
    "cetelem": ("cetelem.ro", ["Cetelem", "BNP Paribas Personal Finance"],
                ["cetelem romania", "bnp paribas personal finance s a paris sucursala bucuresti"], []),
    "citibank": ("citibank.com", ["Citibank Europe"], ["citibank europe"], []),
    "credex": ("credex.ro", ["Credex"], ["credex bank"], []),
    "creditcoop": ("creditcoop.ro", ["Creditcoop", "Banca Centrala Cooperatista"],
                   ["banca centrala cooperatista", "creditcoop"], []),
    "exim": ("eximbank.ro", ["Exim Banca Romaneasca", "EximBank"], ["exim banca romaneasca"], []),
    "garanti": ("garantibbva.ro", ["Garanti BBVA"], ["garanti bbva romania", "garanti bank romania"], []),
    "ing": ("ing.ro", ["ING Bank"], ["ing bank n v amsterdam sucursala bucuresti", "ing bank romania"], ["ing romania"]),
    "intesa": ("intesasanpaolobank.ro", ["Intesa Sanpaolo"], ["intesa sanpaolo bank romania"], []),
    "libra": ("librabank.ro", ["Libra Internet Bank"], ["libra internet bank"], []),
    "nexent": ("nexentbank.ro", ["Nexent Bank"], ["nexent bank"], []),
    "patria": ("patriabank.ro", ["Patria Bank"], ["patria bank"], []),
    "pko": ("pkobp.pl", ["PKO Bank Polski"], ["pko bank polski s a sucursala bucuresti", "pko bank polski sucursala"], []),
    "procredit": ("procreditbank.ro", ["ProCredit Bank"], ["procredit bank romania"], []),
    "raiffeisen": ("raiffeisen.ro", ["Raiffeisen Bank"], ["raiffeisen bank romania"], ["raiffeisen bank"]),
    "revolut": ("revolut.com", ["Revolut"], [], ["revolut", "revolut bank"]),
    "salt": ("salt.bank", ["Salt Bank"], ["salt bank"], []),
    "tbi": ("tbibank.ro", ["tbi bank"], [], ["tbi bank"]),
    "techventures": ("techventures.bank", ["TechVentures Bank"], ["techventures bank"], []),
    "unicredit": ("unicredit.ro", ["UniCredit Bank"], ["unicredit bank romania"], ["unicredit bank"]),
    "vista": ("vistabank.ro", ["Vista Bank"], ["vista bank romania"], ["vista bank"]),
}
FORME_JURIDICE = {"sa", "s", "a", "srl", "ead", "nv", "n", "v", "uab", "plc", "ltd"}


def nume_banca(slug):
    domeniu = BANCI[slug][0]
    return next((b["name"] for b in BANKS if domeniu in b["url"]), slug)


def simplu(t):
    t = unicodedata.normalize("NFD", t or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def fara_forma_juridica(nume):
    cuv = nume.split()
    while cuv and cuv[-1] in FORME_JURIDICE:
        cuv.pop()
    return " ".join(cuv)


def atribuie(slug, business_name):
    """Advertiserul e al băncii doar prin numele juridic sau numele întreg, pe cuvinte întregi."""
    _, _, contine, nume = BANCI[slug]
    n = simplu(business_name)
    if any(re.search(rf"(?<![a-z0-9]){re.escape(p)}(?![a-z0-9])", n) for p in contine):
        return True
    return fara_forma_juridica(n) in nume


def conturi_tiktok(cale=CSV_RETELE):
    """slug -> {username, nivel, url}, din rândurile `retea=tiktok`; NEGASIT se ignoră."""
    conturi = {}
    with open(cale, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["retea"] != "tiktok":
                continue
            m = re.search(r"tiktok\.com/@([^/?#\s]+)", r["url"] or "")
            if m:
                conturi[r["slug"]] = {"username": m.group(1), "nivel": r["nivel"], "url": r["url"]}
    return conturi


# ---------------------------------------------------------------- retenția

def curata(azi=None, director=None):
    """Șterge fișierele cu fotografia mai veche de RETENTIE_ZILE (data din nume, altfel mtime)."""
    azi, director = azi or datetime.date.today(), director or DIR
    sterse = []
    if not os.path.isdir(director):
        return sterse
    for f in sorted(os.listdir(director)):
        cale = os.path.join(director, f)
        if not os.path.isfile(cale):
            continue
        m = re.search(r"(\d{4}-\d{2}-\d{2})", f)
        data = (datetime.date.fromisoformat(m.group(1)) if m
                else datetime.date.fromtimestamp(os.path.getmtime(cale)))
        if (azi - data).days >= RETENTIE_ZILE:
            os.remove(cale)
            sterse.append(f)
    return sterse


# ---------------------------------------------------------------- cereri

class Oprire(Exception):
    """Se oprește toată rularea (robots, 429 repetat, 5xx, cotă zilnică, token)."""


class Refuzat(Exception):
    """Produsul nu e aprobat pentru acest token; celălalt produs merge mai departe."""


JURNAL = []
STARE = {"cheie": None, "secret": None, "token": None, "expira": 0.0, "la_rand_429": 0}


def ascunde(text):
    """Nicio valoare secretă nu ajunge în jurnal, în fișier sau pe ecran."""
    text = str(text)
    for s in (STARE["secret"], STARE["token"], STARE["cheie"]):
        if s:
            text = text.replace(s, "***")
    return text


def _eroare(r):
    try:
        j = r.json()
    except ValueError:
        return None, "", None, {}
    e = j.get("error") if isinstance(j, dict) else None
    if isinstance(e, dict):
        return e.get("code"), e.get("message", ""), e.get("log_id"), j
    # răspunsul de la oauth are `error` text + `error_description`
    return e, (j.get("error_description", "") if isinstance(j, dict) else ""), \
        (j.get("log_id") if isinstance(j, dict) else None), j


def _noteaza(r, cod, log_id):
    JURNAL.append({"url": ascunde(r.url), "metoda": "POST", "status": r.status_code,
                   "cod": cod, "log_id": log_id,
                   "la": datetime.datetime.now().isoformat(timespec="seconds")})


def _verifica_robots(url):
    if not flux.permite(url, ID_FLUX):
        raise Oprire(f"robots.txt (sau BLOCAT) interzice {url}")


def token():
    """Tokenul de client, reînnoit cu 5 minute înainte de expirare (valabil 2 ore)."""
    if STARE["token"] and time.time() < STARE["expira"] - 300:
        return STARE["token"]
    _verifica_robots(URL_TOKEN)
    time.sleep(PAUZA)
    r = requests.post(URL_TOKEN, data={"client_key": STARE["cheie"], "client_secret": STARE["secret"],
                                       "grant_type": "client_credentials"},
                      headers={"User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded",
                               "Cache-Control": "no-cache"}, timeout=40)
    cod, mesaj, log_id, j = _eroare(r)
    _noteaza(r, cod, log_id)
    if r.status_code != 200 or not j.get("access_token"):
        raise Oprire(ascunde(f"tokenul a fost refuzat: HTTP {r.status_code} {cod}: {mesaj[:200]}"))
    STARE["token"] = j["access_token"]
    STARE["expira"] = time.time() + float(j.get("expires_in") or 7200)
    return STARE["token"]


def cere(cale, corp, campuri):
    """O cerere POST. Întoarce `data`, sau {'eroare': ...} la un 4xx care nu e refuz de acces."""
    url = BAZA + cale
    _verifica_robots(url)
    for _ in range(3):
        time.sleep(PAUZA if STARE["la_rand_429"] == 0 else ASTEPTARE_429)
        antet = {"User-Agent": UA, "Content-Type": "application/json",
                 "Authorization": f"Bearer {token()}"}
        r = requests.post(url, params={"fields": campuri}, json=corp, headers=antet, timeout=40)
        cod, mesaj, log_id, j = _eroare(r)
        _noteaza(r, cod, log_id)
        if r.status_code != 429:
            STARE["la_rand_429"] = 0
            break
        if cod == "daily_quota_limit_exceeded":
            raise Oprire(f"cota zilnică epuizată la {cale} (se resetează la 00:00 UTC)")
        STARE["la_rand_429"] += 1
        if STARE["la_rand_429"] >= 3:
            raise Oprire(f"trei răspunsuri 429 la rând ({cale}) — ne oprim")
    if r.status_code >= 500:
        raise Oprire(f"HTTP {r.status_code} la {cale} — ne oprim")
    if r.status_code in (401, 403) or cod in COD_REFUZ:
        raise Refuzat(ascunde(f"{cale}: HTTP {r.status_code} {cod}: {mesaj[:200]}"))
    if r.status_code != 200 or (cod and cod != "ok"):
        return {"eroare": ascunde(f"HTTP {r.status_code} {cod}: {mesaj[:200]}")}
    return j.get("data") or {}


# ---------------------------------------------------------------- reclame (Ad Library)

def _id_advertiser(adv):
    # exemplul oficial de răspuns scrie „buisness_id"; acceptăm ambele
    return adv.get("business_id", adv.get("buisness_id"))


def reclame_banca(slug, azi):
    _, cautari, _, _ = BANCI[slug]
    atribuiti, neatribuiti, erori = {}, {}, []
    for c in cautari:
        d = cere("research/adlib/advertiser/query/", {"search_term": c[:50], "max_count": 50},
                 CAMPURI_ADVERTISER)
        if "eroare" in d:
            erori.append(f"advertiser {c!r}: {d['eroare']}")
        for a in d.get("advertisers", []):
            tinta = atribuiti if atribuie(slug, a.get("business_name", "")) else neatribuiti
            tinta[_id_advertiser(a)] = dict(a, cautare=c)
    for k in atribuiti:
        neatribuiti.pop(k, None)

    filtre = {"ad_published_date_range": {
                  "min": (azi - datetime.timedelta(days=ZILE_RECLAME)).strftime("%Y%m%d"),
                  "max": azi.strftime("%Y%m%d")},
              "country_code_list": [TARA]}
    reclame, straine = {}, {}
    for adv in atribuiti.values():
        search_id = None
        for _ in range(MAX_PAGINI):
            corp = {"filters": filtre, "search_term": adv["business_name"][:50],
                    "search_type": "exact_phrase", "max_count": 10}
            if search_id:
                corp["search_id"] = search_id
            d = cere("research/adlib/ad/query/", corp, CAMPURI_RECLAMA)
            if "eroare" in d:
                erori.append(f"reclame {adv['business_name']!r}: {d['eroare']}")
            for x in d.get("ads", []):
                ad_id = (x.get("ad") or {}).get("id")
                # căutarea e după text: o reclamă a altui advertiser care pomenește
                # numele băncii nu e a băncii, dar o păstrăm pentru verificare
                tinta = reclame if _id_advertiser(x.get("advertiser") or {}) in atribuiti else straine
                tinta.setdefault(ad_id, x)
            search_id = d.get("search_id")
            if str(d.get("has_more")).lower() != "true" or not search_id or len(reclame) >= MAX_RECLAME:
                break
    lista = list(reclame.values())[:MAX_RECLAME]
    for x in lista:
        ad_id = x["ad"]["id"]
        x["detaliu"] = cere("research/adlib/ad/detail/", {"ad_id": ad_id}, CAMPURI_DETALIU)
        # construit, nu cerut: pagina publică a reclamei, pentru om
        x["link_biblioteca"] = f"https://library.tiktok.com/ads/detail/?ad_id={ad_id}"
    return {"banca": nume_banca(slug), "advertiseri": list(atribuiti.values()),
            "advertiseri_neatribuiti": list(neatribuiti.values()),
            "reclame": lista, "reclame_neatribuite": list(straine.values()), "erori": erori}


# ---------------------------------------------------------------- organic (Research API)

def ferestre(azi, zile=ZILE_ORGANIC):
    """Intervale de cel mult FEREASTRA zile (end ≤ start + 30), de la azi înapoi."""
    rez, sfarsit = [], azi
    inceput_total = azi - datetime.timedelta(days=zile - 1)
    while sfarsit >= inceput_total:
        inceput = max(inceput_total, sfarsit - datetime.timedelta(days=FEREASTRA - 1))
        rez.append((inceput.strftime("%Y%m%d"), sfarsit.strftime("%Y%m%d")))
        sfarsit = inceput - datetime.timedelta(days=1)
    return rez


def organic_banca(slug, cont, azi):
    u = cont["username"]
    intrare = dict(cont, banca=nume_banca(slug))
    intrare["profil"] = cere("research/user/info/", {"username": u}, CAMPURI_PROFIL)
    videoclipuri = []
    for inceput, sfarsit in ferestre(azi):
        cursor, search_id = 0, None
        for _ in range(MAX_PAGINI):
            corp = {"query": {"and": [{"operation": "EQ", "field_name": "username", "field_values": [u]}]},
                    "start_date": inceput, "end_date": sfarsit, "max_count": 100, "cursor": cursor}
            if search_id:
                corp["search_id"] = search_id
            d = cere("research/video/query/", corp, CAMPURI_VIDEO)
            if "eroare" in d:
                intrare.setdefault("erori", []).append(f"{inceput}-{sfarsit}: {d['eroare']}")
                break
            for v in d.get("videos", []):
                v["link"] = f"https://www.tiktok.com/@{u}/video/{v.get('id')}"   # construit, nu cerut
                videoclipuri.append(v)
            cursor, search_id = d.get("cursor"), d.get("search_id")
            if not d.get("has_more") or cursor is None:
                break
    intrare["videoclipuri"] = videoclipuri
    return intrare


# ---------------------------------------------------------------- rulare

def cale_iesire(azi):
    return os.path.join(DIR, f"tiktok_{azi.isoformat()}.json")


def salveaza(rez, azi):
    rez["cereri"] = JURNAL
    os.makedirs(DIR, exist_ok=True)
    cale = cale_iesire(azi)
    text = ascunde(json.dumps(rez, ensure_ascii=False, indent=1))
    with open(cale, "w", encoding="utf-8") as f:
        f.write(text)
    return cale


def simulare(banci, conturi, fa_reclame, fa_organic, azi):
    n = 0
    print(f"SIMULARE, nicio cerere. Token: POST {URL_TOKEN} (1 cerere, reînnoit la 2 h).")
    if fa_reclame:
        print(f"\nReclame RO ({(azi - datetime.timedelta(days=ZILE_RECLAME)):%Y%m%d}–{azi:%Y%m%d}):")
        for s in banci:
            for c in BANCI[s][1]:
                print(f"  {s:20} POST {BAZA}research/adlib/advertiser/query/  search_term={c!r}")
                n += 1
            n += 1      # cel puțin o pagină de ad/query, dacă apare un advertiser atribuit
        print(f"  + pe advertiser atribuit: ad/query pe pagini de 10, apoi ad/detail pe reclamă "
              f"(≤{MAX_RECLAME} pe bancă)")
    if fa_organic:
        fer = ferestre(azi)
        print(f"\nOrganic, ultimele {ZILE_ORGANIC} de zile în {len(fer)} ferestre:")
        for s in banci:
            if s not in conturi:
                continue
            c = conturi[s]
            print(f"  {s:20} @{c['username']:28} nivel {c['nivel']:5} user/info + "
                  f"{len(fer)}× video/query (100/pagină)")
            n += 1 + len(fer)
        fara = [s for s in banci if s not in conturi]
        print(f"  fără cont TikTok în {os.path.basename(CSV_RETELE)} (NEGASIT): {len(fara)}")
    print(f"\nMinim {n + 1} cereri ≈ {math.ceil((n + 1) * PAUZA / 60)} min la {PAUZA:g} s pauză.")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--banca", choices=sorted(BANCI), help="doar o bancă (slug)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--doar-reclame", action="store_true")
    g.add_argument("--doar-organic", action="store_true")
    ap.add_argument("--simulare", action="store_true", help="fără nicio cerere: listează ce ar cere")
    ap.add_argument("--curata", action="store_true", help="doar retenția, apoi ieșire")
    a = ap.parse_args()

    azi = datetime.date.today()
    sterse = curata(azi)
    print(f"retenție {RETENTIE_ZILE} zile: {len(sterse)} fișiere șterse {sterse if sterse else ''}")
    if a.curata:
        return

    banci = [a.banca] if a.banca else list(BANCI)
    conturi = conturi_tiktok()
    fa_reclame, fa_organic = not a.doar_organic, not a.doar_reclame
    if a.simulare:
        simulare(banci, conturi, fa_reclame, fa_organic, azi)
        return

    rez = {"sursa": "TikTok Commercial Content API + Research API", "baza": BAZA, "tara": TARA,
           "fotografie": azi.isoformat(), "ua": UA, "retentie_zile": RETENTIE_ZILE,
           "sterge_la": (azi + datetime.timedelta(days=RETENTIE_ZILE)).isoformat(),
           "acces": {}, "reclame": {}, "organic": {}}
    if os.path.exists(cale_iesire(azi)):
        with open(cale_iesire(azi), encoding="utf-8") as f:
            v = json.load(f)
        rez["reclame"], rez["organic"] = v.get("reclame", {}), v.get("organic", {})
        JURNAL.extend(v.get("cereri", []))

    STARE["cheie"] = config.cere("TIKTOK_CLIENT_KEY")
    STARE["secret"] = config.cere("TIKTOK_CLIENT_SECRET")
    try:
        token()
        rez["acces"]["token"] = "obținut (valabil 2 ore; răspunsul nu listează scope-urile)"
        print("token: obținut")
        for produs, fa, functie, tinte in (
                ("reclame", fa_reclame, lambda s: reclame_banca(s, azi), banci),
                ("organic", fa_organic, lambda s: organic_banca(s, conturi[s], azi),
                 [s for s in banci if s in conturi])):
            if not fa:
                continue
            rez["acces"][produs] = "ok"
            try:
                for slug in tinte:
                    if slug in rez[produs] and not a.banca:
                        continue
                    rez[produs][slug] = x = functie(slug)
                    if produs == "reclame":
                        print(f"{slug:20} advertiseri {len(x['advertiseri']):2} (neatribuiți "
                              f"{len(x['advertiseri_neatribuiti']):2})  reclame RO {len(x['reclame']):3}",
                              flush=True)
                    else:
                        print(f"{slug:20} @{x['username']:28} videoclipuri {len(x['videoclipuri']):4}",
                              flush=True)
                    salveaza(rez, azi)
            except Refuzat as e:
                rez["acces"][produs] = f"REFUZAT: {e}"
                print(f"{produs}: REFUZAT — {e}")
    except Oprire as e:
        rez["oprit"] = str(e)
        print("OPRIT:", e)
    print("acces:", json.dumps(rez["acces"], ensure_ascii=False))
    print(f"{len(JURNAL)} cereri · scris {salveaza(rez, azi)}")


if __name__ == "__main__":
    main()
