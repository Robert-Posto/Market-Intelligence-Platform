"""Canalele oficiale de YouTube ale băncilor (2.4 „Campanii & marketing”), prin YouTube Data API v3.

Două etape, separate intenționat:

1. `--descopera` (OFFLINE, fără nicio cerere și fără bază): caută linkurile de
   canal (`youtube.com/@…`, `/channel/UC…`, `/c/…`, `/user/…`) în paginile
   HTML deja aduse în Bronze (`bronze/` și arhivele `bronze_arhiva_*`) și
   scrie `date/youtube_canale.csv` (versionat: e configurare, nu date YouTube).
   Un canal se acceptă doar dacă linkul apare într-o pagină de pe site-ul
   oficial al băncii (adresa declarată de pagină, `DOMENII`); dovada (adresa
   și fișierul Bronze) rămâne în CSV. Băncile fără link rămân `NEGASIT`, cu
   motiv — canalul nu se caută după nume (`search.list` ar ghici).

2. Extragerea, cu cheie API (`YOUTUBE_API_KEY` din `.env`, prin `config`):
   `channels.list` (statistici + playlist-ul de uploads), `playlistItems.list`
   (paginare, 50 pe pagină) și `videos.list` pe loturi de 50 (titlu, dată,
   durată, vizualizări, like-uri, comentarii). Rezultatul merge într-UN fișier
   local, `output/youtube/youtube_<AAAA-LL-ZZ>.json` (ignorat de git), salvat
   după fiecare bancă, cu reluare în aceeași zi. NU în bază.

Eticheta „nou”: fiecare videoclip primește `nou` = nu exista în extragerea
anterioară. Referința e cel mai recent `youtube_<data>.json` cu data strict
dinaintea zilei de azi și încă în retenție (`metoda_nou: "id-uri"`); o bancă
absentă din el (sau cu eroare acolo) cade pe regula de dată. Fără un astfel de
fișier, rezerva e doar data rulării anterioare din `output/youtube/extrageri.txt`
(jurnal local cu datele rulărilor, nimic de la YouTube, deci poate rămâne peste
30 de zile): „nou” = publicat după acea zi (`metoda_nou: "data"`). Prima rulare
vreodată: toate `nou: false`, `nou_fata_de: null`. Reluarea din aceeași zi
păstrează referința (fișierul de azi nu e niciodată referință).

Costul, din documentația oficială
(https://developers.google.com/youtube/v3/determine_quota_cost, citită 30.09.2026):
„Projects that enable the YouTube Data API have a default quota allocation of
100 search.list calls, 100 videos.insert calls, and 10,000 units per day
combined for all other endpoints.” `channels.list`, `playlistItems.list` și
`videos.list` costă câte 1 unitate („A call to this method has a quota cost of
1 unit”), oricâte `part` și oricât `maxResults`; „Every API request, even if
invalid, will cost at least one quota point.” `search.list` nu se folosește.
Pe bancă: 1 (canalul) + ⌈(N+1)/50⌉ (paginile de uploads, ultima e cea care
trece de limită) + ⌈N/50⌉ (loturile de videoclipuri), N = videoclipurile din
fereastră. `--simulare` face socoteala pe trei ipoteze de volum.

Regulile de stocare (YouTube API Services Developer Policies,
https://developers.google.com/youtube/terms/developer-policies, citite 30.09.2026):
  - III.E.4.d: „API Clients may temporarily store limited amounts of
    Non-Authorized Data for as long as is necessary for the purposes of the
    API Client but not longer than 30 calendar days.” Tot ce aduce scriptul e
    Non-Authorized Data (cheie API, fără OAuth; definiția: „API Data accessible
    by an API Client without User Credentials”). De aici `RETENTIE_ZILE = 30`:
    la fiecare pornire și cu `--curata`, fișierele din `output/youtube/` cu
    data extragerii de acum 30 de zile sau mai mult se șterg. Excepția din
    III.E.4.b (statistici păstrate „for as long as is necessary”) e doar pentru
    Authorized Data, deci nu ne acoperă.
  - III.E.4.e: „API Clients must use reasonable efforts to ensure that their
    stored API Data is consistent with the current data available through
    YouTube API Services.” Reîmprospătarea = o rulare nouă, alt fișier.
  - III.E.2.a: „Do not aggregate API Data except that you may only aggregate
    API Data relating to YouTube channels that are under the same content
    owner as recognized by YouTube pursuant to content licensing agreement(s)
    between YouTube and such content owner. Such aggregated API Data must only
    be viewable by that content owner.” III.E.2.b: „Do not aggregate API Data
    or otherwise use API Data or YouTube API Services to gain insights into
    YouTube's usage, revenue, or any other aspects of YouTube's business.”
    Scriptul nu adună nimic peste bănci (fără totaluri, medii sau clasamente
    pe piață): fiecare canal stă separat, cu cifrele lui. Cum se arată
    comparația în 2.4 rămâne de decis la aviz (Nicolae, §4.2).
  - III.E.4.f: aplicația arată cele mai noi date API; datele vechi doar cu
    data lor. III.E.4.h: ce nu vine din YouTube, afișat lângă datele API,
    cere o mențiune clară că nu e de la YouTube.
Conformitatea din `CLAUDE.md` rămâne: fiecare adresă trece prin `flux.permite`
(robots.txt al gazdei API-ului), cu `crawler.UA`; fără scraping pe youtube.com.
Cheia nu apare niciodată în jurnal, în fișier sau pe ecran: `masca` înlocuiește
valoarea lui `key=` în tot ce iese din `Client.cere`.

Rulare (din rădăcina repo-ului):
  python ingest/youtube_api.py --descopera            # offline, scrie date/youtube_canale.csv
  python ingest/youtube_api.py --simulare             # ce s-ar cere și cât costă, fără cereri
  python ingest/youtube_api.py [--banca bcr] [--luni 12]
  python ingest/youtube_api.py --curata               # doar retenția de 30 de zile
"""
import argparse
import calendar
import collections
import csv
import datetime
import glob
import json
import math
import os
import re
import sys
import time
from urllib.parse import unquote, urlparse

AICI = os.path.dirname(os.path.abspath(__file__))
RADACINA = os.path.dirname(AICI)
sys.path[:0] = [RADACINA, AICI]

import requests                     # noqa: E402
import config                       # noqa: E402
import flux                         # noqa: E402
from crawler import UA              # noqa: E402

BAZA = "https://www.googleapis.com/youtube/v3/"
POLITICA = "https://developers.google.com/youtube/terms/developer-policies"
# III.E.4.d: Non-Authorized Data „not longer than 30 calendar days”.
RETENTIE_ZILE = 30
DIR_IESIRE = os.path.join(RADACINA, "output", "youtube")
CSV_CANALE = os.path.join(RADACINA, "date", "youtube_canale.csv")
# Arhiva de la pornirea de la zero (23.09) intră și ea: acolo sunt singurele
# pagini BT, Intesa, UniCredit și Revolut din Bronze (0 în `bronze/` la 30.09).
DIRS_BRONZE = [os.path.join(RADACINA, "bronze")] + sorted(
    glob.glob(os.path.join(RADACINA, "bronze_arhiva_*")))
# 1 s între cereri: limita reală e cota zilnică, nu ritmul; pauza doar nu
# trimite rafale spre API.
PAUZA = 1.0
# Plafon de siguranță pe bancă: 40 de pagini = 2.000 de videoclipuri, 81 de
# unități. Un canal care publică mai mult într-un an e ceva ce vrem să vedem
# înainte să consumăm cota pe el.
MAX_PAGINI = 40
LOT = 50                            # maxResults maxim la playlistItems.list și videos.list
H = {"User-Agent": UA, "Accept": "application/json"}
CAMPURI_CSV = ["slug", "stare", "canal", "tip", "nivel", "pagini", "url_dovada",
               "fisier_bronze", "alte_canale", "nota"]

RE_CANAL = re.compile(
    rb"youtube\.com/(@[A-Za-z0-9._\-%]+|channel/UC[A-Za-z0-9_\-]{22}"
    rb"|c/[A-Za-z0-9._\-%]+|user/[A-Za-z0-9._\-]+)", re.I)
RE_VIDEO = re.compile(rb"(?:youtube\.com/(?:embed/|watch\?v=)|youtu\.be/)([A-Za-z0-9_\-]{11})")
RE_CHEIE = re.compile(r"(key=)[^&\s\"']+", re.I)


def masca(text):
    """Orice text care iese spre jurnal sau ecran, fără valoarea cheii."""
    return RE_CHEIE.sub(r"\1***", str(text))


# ---------------------------------------------------------------- descoperire

# slug -> gazdele site-ului oficial (domeniile din `banks.py`, plus cele pe care
# stau efectiv paginile din Bronze: Credex e și pe credexbank.ro). BNP Paribas
# și Cetelem sunt separate: bnpparibas.com singur ar prinde grupul.
DOMENII = {
    "banca-transilvania": ["bancatransilvania.ro"], "bankofchina": ["bankofchina.com"],
    "banorient": ["banorientfrance.com"], "bcr": ["bcr.ro"], "bcr-locuinte": ["bcrlocuinte.ro"],
    "bid": ["bidromania.eu"], "bnpparibas": ["romania.bnpparibas.com"], "brci": ["brci.ro"],
    "brd": ["brd.ro"], "cec": ["cec.ro"], "cetelem": ["cetelem.ro"],
    "citibank": ["citibank.com"], "credex": ["credex.ro", "credexbank.ro"],
    "creditcoop": ["creditcoop.ro"], "exim": ["eximbank.ro"], "garanti": ["garantibbva.ro"],
    "ing": ["ing.ro"], "intesa": ["intesasanpaolobank.ro"], "libra": ["librabank.ro"],
    "nexent": ["nexentbank.ro"], "patria": ["patriabank.ro"], "pko": ["pkobp.pl"],
    "procredit": ["procreditbank.ro"], "raiffeisen": ["raiffeisen.ro"], "revolut": ["revolut.com"],
    "salt": ["salt.bank"], "tbi": ["tbibank.ro"], "techventures": ["techventures.bank"],
    "unicredit": ["unicredit.ro"], "vista": ["vistabank.ro"],
}

# Adnotări puse de om după citirea dovezilor (30.09.2026). `nivel` = „grup”:
# canalul grupului sau cel global, nu al băncii din România; nu se extrage, din
# același motiv pentru care aplicațiile de pe altă piață nu se încarcă (CLAUDE.md).
NOTE = {
    "pko": {"nivel": "grup", "nota": "paginile sunt pe pkobp.pl (PKO Bank Polski, Polonia): "
            "canalul băncii-mamă, în polonă; sucursala din România n-are canal legat"},
    "revolut": {"nivel": "grup", "nota": "@RevolutApp e canalul global Revolut, legat de pe "
                "revolut.com/en-RO; niciun canal pentru România"},
    "bnpparibas": {"nivel": "grup", "nota": "canalul grupului BNP Paribas (Paris), legat din "
                   "subsolul romania.bnpparibas.com"},
    "brci": {"nota": "o singură pagină (arhiva 23.09), link /channel/…/featured; de verificat "
             "titlul la prima rulare"},
    # Băncile blocate (WAF / F5): paginile din Bronze și din arhiva din 23.09 au fost
    # aduse după refuz (cascada trecea atunci la Playwright), deci nu sunt o dovadă
    # folosibilă — aceeași decizie ca la id-ul App Store al CEC. Nu se extrag.
    "banca-transilvania": {"nivel": "blocat", "nota": "dovada vine din pagini aduse după "
                           "blocajul WAF (arhiva 23.09); nu se extrage"},
    "intesa": {"nivel": "blocat", "nota": "dovada vine din pagini aduse după blocajul WAF "
               "(arhiva 23.09); handle generat automat (-g4m); nu se extrage"},
    "unicredit": {"nivel": "blocat", "nota": "dovada vine din pagini aduse după blocajul WAF "
                  "(arhiva 23.09); nu se extrage"},
    "cetelem": {"nivel": "blocat", "nota": "dovada vine din paginile aduse prin Playwright după "
                "respingerea F5 (23.09; Nicolae §9.14); nu se extrage"},
    "banorient": {"nota": "robots.txt interzice tot (banks.py): nicio pagină în Bronze"},
    "citibank": {"nota": "domeniu abandonat (banks.py), fără retail în România: nicio pagină în Bronze"},
}

RE_PROPRIE = re.compile(
    rb"<link[^>]+rel=[\"']canonical[\"'][^>]*>|<meta[^>]+property=[\"']og:url[\"'][^>]*>", re.I)
RE_ABSOLUT = re.compile(rb"(?:href|content)=[\"'](https?://[^\"'\s>]+)", re.I)
PREFERINTA_TIP = {"id": 0, "handle": 1, "user": 2, "custom": 3}


def banca_din_gazda(gazda):
    gazda = (gazda or "").lower()
    for slug, domenii in DOMENII.items():
        if any(gazda == d or gazda.endswith("." + d) for d in domenii):
            return slug
    return None


def adresa_paginii(octeti):
    """(slug, adresa, cum) pentru o pagină din Bronze, fără bază și fără rețea.

    Numele din Bronze e doar hash + ultimul segment, deci banca se ia din
    pagina însăși: întâi adresa pe care pagina și-o declară (canonical /
    og:url: 804 din 896 de pagini HTML din `bronze/` la 30.09), apoi gazda
    oficială spre care trimit cele mai multe linkuri absolute din pagină."""
    m = RE_PROPRIE.search(octeti)
    if m:
        u = RE_ABSOLUT.search(m.group(0))
        if u:
            adresa = u.group(1).decode("utf-8", "replace")
            slug = banca_din_gazda(urlparse(adresa).hostname)
            if slug:
                return slug, adresa, "canonical"
    voturi = collections.Counter()
    for u in RE_ABSOLUT.findall(octeti):
        slug = banca_din_gazda(urlparse(u.decode("utf-8", "replace")).hostname)
        if slug:
            voturi[slug] += 1
    if voturi:
        (slug, n), = voturi.most_common(1)
        return slug, "", f"linkuri interne spre site ({n})"
    return None, "", ""


def canal_din_link(potrivire):
    """`@BRDGroupe` / `channel/UC…` -> (canal, tip); handle-urile fără %xx."""
    p = unquote(potrivire.decode("ascii", "ignore")).rstrip(".")
    if p.startswith("@"):
        return p, "handle"
    tip, _, nume = p.partition("/")
    return nume, {"channel": "id", "c": "custom", "user": "user"}[tip.lower()]


def descopera(dirs=None):
    """Ce e în Bronze, pe bancă, fără nicio cerere.

    Întoarce {slug: {"canale": [...], "pagini": n, "videoclipuri": Counter}}.
    `canale` = [canal, tip, pagini, dovada, fisier], ordonat după numărul de
    pagini distincte ale băncii care trimit la canal: canalul din subsolul
    site-ului apare pe zeci de pagini (BRD: 89), un link dintr-un articol pe
    una. Aceeași pagină în `bronze/` și în arhivă se numără o dată; dovada e
    fișierul găsit primul, deci din `bronze/` când există acolo."""
    rez = collections.defaultdict(lambda: {"canale": {}, "pagini": set(),
                                           "videoclipuri": collections.Counter()})
    for d in (DIRS_BRONZE if dirs is None else dirs):
        if not os.path.isdir(d):
            continue
        for fisier in sorted(os.listdir(d)):
            cale = os.path.join(d, fisier)
            if not os.path.isfile(cale):
                continue
            # antetul întâi: PDF-urile sunt grosul Bronze-ului și nu le citim întregi
            # (cu citire completă: 15 min pe 2.627 de fișiere; cu antetul: 29 s, 30.09)
            with open(cale, "rb") as f:
                antet = f.read(4)
                if antet == b"%PDF" or antet[:2] == b"PK":
                    continue
                f.seek(0)
                octeti = f.read()
            slug, adresa, cum = adresa_paginii(octeti)
            if not slug:
                continue
            b = rez[slug]
            nou = fisier not in b["pagini"]
            b["pagini"].add(fisier)
            if nou:
                b["videoclipuri"].update(sorted({m.decode() for m in RE_VIDEO.findall(octeti)}))
            rel = os.path.relpath(cale, RADACINA).replace(os.sep, "/")
            for canal, tip in dict.fromkeys(canal_din_link(m) for m in RE_CANAL.findall(octeti)):
                k = (tip, canal.lower())
                if k not in b["canale"]:
                    b["canale"][k] = [canal, tip, set(), adresa or cum, rel]
                b["canale"][k][2].add(fisier)
    return {slug: {"pagini": len(b["pagini"]), "videoclipuri": b["videoclipuri"],
                   "canale": sorted(([c, t, len(p), dov, f] for c, t, p, dov, f in b["canale"].values()),
                                    key=lambda r: (-r[2], PREFERINTA_TIP[r[1]]))}
            for slug, b in rez.items()}


def randuri_csv(gasite, slugs=None, note=None):
    """Un rând pe bancă: canalul legat de cele mai multe pagini, restul în
    `alte_canale` (Libra: /user/ și /@, probabil același canal)."""
    note = NOTE if note is None else note
    randuri = []
    for slug in (DOMENII if slugs is None else slugs):
        b = gasite.get(slug, {"canale": [], "pagini": 0, "videoclipuri": collections.Counter()})
        n = note.get(slug, {})
        if not b["canale"]:
            motiv = n.get("nota") or (
                f"{b['pagini']} pagini HTML ale băncii în Bronze, niciun link de canal"
                if b["pagini"] else "nicio pagină HTML a băncii în Bronze")
            if b["videoclipuri"]:
                ids = [v for v, _ in b["videoclipuri"].most_common(3)]
                motiv += (f"; doar videoclipuri încorporate ({len(b['videoclipuri'])}, ex. "
                          f"{', '.join(ids)}), al căror canal nu e neapărat al băncii")
            randuri.append({"slug": slug, "stare": "NEGASIT", "pagini": b["pagini"], "nota": motiv})
            continue
        canal, tip, pagini, dovada, fisier = b["canale"][0]
        randuri.append({
            "slug": slug, "stare": "GASIT", "canal": canal, "tip": tip,
            "nivel": n.get("nivel", "RO"), "pagini": pagini, "url_dovada": dovada,
            "fisier_bronze": fisier,
            "alte_canale": " ".join(f"{c}:{t}({p})" for c, t, p, _, _ in b["canale"][1:]),
            "nota": n.get("nota", "")})
    return randuri


def scrie_csv(randuri, cale=CSV_CANALE):
    with open(cale, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPURI_CSV, lineterminator="\n")
        w.writeheader()
        w.writerows(randuri)
    return cale


def citeste_canale(cale=CSV_CANALE):
    """Doar canalele de extras: GASIT și nivel RO."""
    with open(cale, encoding="utf-8", newline="") as f:
        return [r for r in csv.DictReader(f) if r["stare"] == "GASIT" and r["nivel"] == "RO"]


# ------------------------------------------------------------------ retenție

RE_FISIER = re.compile(r"^youtube_(\d{4}-\d{2}-\d{2})\.json$")


def curata(azi=None, director=DIR_IESIRE):
    """Șterge extragerile cu vârsta >= RETENTIE_ZILE (III.E.4.d, „not longer
    than 30 calendar days”). Vârsta vine din data extragerii din nume, nu din
    mtime: reluarea din aceeași zi rescrie fișierul și i-ar reseta ceasul."""
    azi = azi or datetime.date.today()
    sterse = []
    if not os.path.isdir(director):
        return sterse
    for nume in sorted(os.listdir(director)):
        m = RE_FISIER.match(nume)
        if m and (azi - datetime.date.fromisoformat(m.group(1))).days >= RETENTIE_ZILE:
            os.remove(os.path.join(director, nume))
            sterse.append(nume)
    return sterse


# ------------------------------------------------------------- eticheta „nou”

JURNAL_EXTRAGERI = "extrageri.txt"
RE_ZI = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def zile_din_jurnal(director):
    """Datele rulărilor anterioare din `extrageri.txt` (doar date, nimic de la YouTube)."""
    try:
        with open(os.path.join(director, JURNAL_EXTRAGERI), encoding="utf-8") as f:
            return sorted({datetime.date.fromisoformat(r.strip()) for r in f if RE_ZI.match(r.strip())})
    except OSError:
        return []


def noteaza_extragerea(zi, director):
    """Adaugă ziua rulării în jurnal, o singură dată (reluarea din aceeași zi nu o repetă)."""
    if zi in zile_din_jurnal(director):
        return
    os.makedirs(director, exist_ok=True)
    cale = os.path.join(director, JURNAL_EXTRAGERI)
    nou = not os.path.exists(cale)
    with open(cale, "a", encoding="utf-8") as f:
        if nou:
            f.write("# zilele rulărilor ingest/youtube_api.py: doar data, fără date YouTube "
                    "(rezerva etichetei „nou” când lipsește fișierul anterior)\n")
        f.write(zi.isoformat() + "\n")


def referinta(azi, director):
    """(data, {slug: id-uri} sau None, metoda) față de care se marchează „nou”.

    Întâi cel mai recent `youtube_<data>.json` cu data < azi și vârsta <
    RETENTIE_ZILE: un fișier expirat nu se folosește, chiar dacă `curata` nu
    l-a șters încă (iar `curata` nu poate șterge unul neexpirat, deci ordinea
    la pornire nu contează). Fișierul de azi nu e referință: reluarea din
    aceeași zi se compară tot cu ziua anterioară. Altfel, ultima zi din jurnal
    < azi (metoda „data”); altfel (None, None, None) = prima rulare."""
    valide = []
    if os.path.isdir(director):
        for nume in os.listdir(director):
            m = RE_FISIER.match(nume)
            if m:
                zi = datetime.date.fromisoformat(m.group(1))
                if zi < azi and (azi - zi).days < RETENTIE_ZILE:
                    valide.append((zi, nume))
    for zi, nume in sorted(valide, reverse=True):
        try:
            with open(os.path.join(director, nume), encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue
        # doar băncile extrase fără eroare: la celelalte nu știm ce videoclipuri erau
        ids = {slug: {v["id"] for v in b.get("videoclipuri") or []}
               for slug, b in (d.get("banci") or {}).items() if b and b.get("canal")}
        return zi.isoformat(), ids, "id-uri"
    zile = [z for z in zile_din_jurnal(director) if z < azi]
    if zile:
        return max(zile).isoformat(), None, "data"
    return None, None, None


def marcheaza_noi(slug, intrare, ref):
    """`nou` pe fiecare videoclip al băncii. Regula de dată: publicat după ziua
    referinței (`publicat_la` e în UTC; ziua referinței însăși nu intră, fiindcă
    jurnalul nu are ora rulării)."""
    zi, ids, _ = ref
    vechi = ids.get(slug) if ids is not None else None
    intrare.pop("metoda_nou", None)
    if ids is not None and vechi is None:
        intrare["metoda_nou"] = "data"      # banca lipsea din extragerea de referință
    for v in intrare.get("videoclipuri") or []:
        if zi is None:
            v["nou"] = False
        elif vechi is not None:
            v["nou"] = v["id"] not in vechi
        else:
            v["nou"] = (v.get("publicat_la") or "")[:10] > zi


# -------------------------------------------------------------------- cereri


class Oprire(Exception):
    pass


class Client:
    """Cererile spre API, cu cheia ascunsă în tot ce se jurnalizează."""

    def __init__(self, cheie, pauza=PAUZA):
        self.cheie = cheie
        self.pauza = pauza
        self.jurnal = []
        self.unitati = 0
        self._robots_verificat = set()

    def cere(self, metoda, params):
        url = BAZA + metoda
        if url not in self._robots_verificat:
            if not flux.permite(url, "youtube_api"):
                raise Oprire(f"robots.txt interzice {url}")
            self.pauza = max(self.pauza, flux.intarziere(url, "youtube_api") or 0)
            self._robots_verificat.add(url)
        r = None
        for incercare in range(2):
            time.sleep(self.pauza if incercare == 0 else 60)
            try:
                r = requests.get(url, params={**params, "key": self.cheie}, headers=H, timeout=30)
            except requests.RequestException as exc:
                # mesajul excepției conține adresa întreagă, deci și cheia
                raise Oprire(f"{metoda}: {type(exc).__name__}: {masca(exc)}") from None
            self.unitati += 1
            self.jurnal.append({"url": masca(r.url), "status": r.status_code,
                                "la": datetime.datetime.now().isoformat(timespec="seconds")})
            if r.status_code != 429 and r.status_code < 500:
                break
        if r.status_code == 429 or r.status_code >= 500:
            raise Oprire(f"HTTP {r.status_code} de două ori la {metoda} — ne oprim")
        if r.status_code == 200:
            return r.json()
        motiv = motiv_eroare(r)
        if r.status_code in (401, 403) or motiv == "keyInvalid" or "api key" in masca(r.text).lower():
            # quotaExceeded, cheie invalidă sau API neactivat în proiect: orice
            # cerere următoare ar eșua la fel și ar consuma cotă degeaba.
            raise Oprire(f"HTTP {r.status_code} {motiv} la {metoda} — ne oprim")
        return {"items": [], "eroare": f"HTTP {r.status_code} {motiv}".strip()}


def motiv_eroare(r):
    try:
        return (r.json()["error"].get("errors") or [{}])[0].get("reason", "")
    except (ValueError, KeyError, AttributeError, TypeError, IndexError):
        return ""


def params_canal(rand):
    p = {"part": "snippet,statistics,contentDetails"}
    if rand["tip"] == "id":
        p["id"] = rand["canal"]
    elif rand["tip"] == "user":
        p["forUsername"] = rand["canal"]
    else:
        # /c/<nume> nu are căutare directă în API; numele personalizat vechi e
        # de regulă și handle, iar potrivirea se verifică pe snippet.customUrl.
        p["forHandle"] = rand["canal"] if rand["canal"].startswith("@") else "@" + rand["canal"]
    return p


def canal(client, rand):
    d = client.cere("channels", params_canal(rand))
    items = d.get("items") or []
    if not items and rand["tip"] == "user" and not d.get("eroare"):
        # numele vechi /user/ poate să nu mai răspundă la forUsername; la Libra
        # site-ul trimite și la /user/LibraInternetBank, și la /@LibraInternetBank
        d = client.cere("channels", params_canal({"canal": "@" + rand["canal"], "tip": "handle"}))
        items = d.get("items") or []
    if not items:
        return None, d.get("eroare") or "canal negăsit de API"
    c = items[0]
    sn = c.get("snippet", {})
    if rand["tip"] == "custom":
        custom = (sn.get("customUrl") or "").lower().lstrip("@")
        if custom != rand["canal"].lower():
            return None, f"/c/{rand['canal']} nu e handle-ul canalului întors (@{custom})"
    st = c.get("statistics", {})
    return {
        "id": c["id"], "titlu": sn.get("title"), "custom_url": sn.get("customUrl"),
        "tara": sn.get("country"), "creat_la": sn.get("publishedAt"),
        "abonati": _int(st.get("subscriberCount")),
        "abonati_ascunsi": st.get("hiddenSubscriberCount"),
        "vizualizari": _int(st.get("viewCount")),
        "videoclipuri": _int(st.get("videoCount")),
        "uploads": c.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads"),
        "link": f"https://www.youtube.com/channel/{c['id']}",
    }, None


def id_uri_din_fereastra(client, playlist, de_la):
    """ID-urile videoclipurilor publicate de la `de_la` încoace.

    Playlist-ul de uploads vine de la cel mai nou; ne oprim la pagina care
    conține primul videoclip mai vechi decât fereastra (ea trece de limită),
    la ultima pagină sau la plafon."""
    ids, token = [], None
    for _ in range(MAX_PAGINI):
        p = {"part": "contentDetails", "playlistId": playlist, "maxResults": LOT}
        if token:
            p["pageToken"] = token
        d = client.cere("playlistItems", p)
        items = d.get("items", [])
        in_fereastra = [it["contentDetails"]["videoId"] for it in items
                        if (it["contentDetails"].get("videoPublishedAt") or "")[:10] >= de_la]
        ids += in_fereastra
        token = d.get("nextPageToken")
        if not token or len(in_fereastra) < len(items):
            break
    return list(dict.fromkeys(ids))


def videoclipuri(client, ids):
    rez = []
    for i in range(0, len(ids), LOT):
        d = client.cere("videos", {"part": "snippet,contentDetails,statistics",
                                   "id": ",".join(ids[i:i + LOT]), "maxResults": LOT})
        for v in d.get("items", []):
            st = v.get("statistics", {})
            durata = v.get("contentDetails", {}).get("duration")
            rez.append({
                "id": v["id"], "titlu": v.get("snippet", {}).get("title"),
                "publicat_la": v.get("snippet", {}).get("publishedAt"),
                "durata": durata, "durata_sec": secunde(durata),
                "vizualizari": _int(st.get("viewCount")),
                "likeuri": _int(st.get("likeCount")),
                "comentarii": _int(st.get("commentCount")),
                "link": f"https://www.youtube.com/watch?v={v['id']}",
            })
    return rez


def secunde(durata):
    """ISO 8601 (`PT1H2M3S`, `P1DT2H`) -> secunde; None dacă lipsește."""
    m = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?", durata or "")
    if not m or durata in ("P", "PT"):
        return None
    z, h, mi, s = (int(x or 0) for x in m.groups())
    return ((z * 24 + h) * 60 + mi) * 60 + s


def _int(v):
    return int(v) if v not in (None, "") else None


def minus_luni(zi, luni):
    an, luna = divmod(zi.year * 12 + zi.month - 1 - luni, 12)
    return datetime.date(an, luna + 1, min(zi.day, calendar.monthrange(an, luna + 1)[1]))


# ---------------------------------------------------------------------- rulare


def cale_iesire(zi):
    return os.path.join(DIR_IESIRE, f"youtube_{zi.isoformat()}.json")


def salveaza(rez, client):
    rez["cereri"] = client.jurnal
    rez["unitati_consumate"] = client.unitati
    os.makedirs(DIR_IESIRE, exist_ok=True)
    zi = datetime.date.fromisoformat(rez["data_extragerii"])
    cale = cale_iesire(zi)
    with open(cale, "w", encoding="utf-8") as f:
        json.dump(rez, f, ensure_ascii=False, indent=1)
    noteaza_extragerea(zi, DIR_IESIRE)
    return cale


def extrage(client, randuri, luni, azi=None):
    azi = azi or datetime.date.today()
    de_la = minus_luni(azi, luni).isoformat()
    cale = cale_iesire(azi)
    # referința se citește înainte de orice scriere de azi; e aceeași și la reluare
    ref = referinta(azi, DIR_IESIRE)
    rez = {"sursa": "YouTube Data API v3", "baza": BAZA, "politica": POLITICA,
           "data_extragerii": azi.isoformat(),
           "extras_la": datetime.datetime.now().isoformat(timespec="seconds"),
           "retentie_zile": RETENTIE_ZILE,
           "sterge_la": (azi + datetime.timedelta(days=RETENTIE_ZILE)).isoformat(),
           "luni": luni, "de_la": de_la, "ua": UA,
           "nou_fata_de": ref[0], "metoda_nou": ref[2], "banci": {}}
    if os.path.exists(cale):
        # reluare: băncile extrase azi fără eroare, pe aceeași fereastră, nu se mai cer
        with open(cale, encoding="utf-8") as f:
            vechi = json.load(f)
        if vechi.get("de_la") == de_la:
            rez["banci"] = {s: b for s, b in vechi.get("banci", {}).items() if not b.get("eroare")}
            client.jurnal[:0] = vechi.get("cereri", [])
            client.unitati += vechi.get("unitati_consumate", 0)
    for slug, intrare in rez["banci"].items():
        marcheaza_noi(slug, intrare, ref)
    try:
        for rand in randuri:
            slug = rand["slug"]
            if slug in rez["banci"]:
                continue
            inainte = client.unitati
            info, eroare = canal(client, rand)
            intrare = {"canal_csv": rand["canal"], "tip": rand["tip"], "dovada": rand["url_dovada"]}
            if eroare:
                intrare["eroare"] = eroare
            else:
                ids = id_uri_din_fereastra(client, info["uploads"], de_la) if info["uploads"] else []
                intrare.update(canal=info, videoclipuri=videoclipuri(client, ids))
                marcheaza_noi(slug, intrare, ref)
            intrare["unitati"] = client.unitati - inainte
            rez["banci"][slug] = intrare
            print(f"{slug:20} {rand['canal'][:28]:28} "
                  f"{eroare or str(len(intrare['videoclipuri'])) + ' videoclipuri'}  "
                  f"({intrare['unitati']} unități)", flush=True)
            salveaza(rez, client)
        rez.pop("oprit", None)
    except Oprire as e:
        rez["oprit"] = masca(e)
        print("OPRIT:", masca(e))
    return rez, salveaza(rez, client)


def unitati_pe_banca(n):
    """channels.list + paginile de uploads (ultima trece de limită) + loturile."""
    return 1 + min(MAX_PAGINI, math.ceil((n + 1) / LOT)) + math.ceil(n / LOT)


def simulare(randuri, luni, pe_an=(12, 50, 150)):
    """Ce s-ar cere, fără nicio cerere; costul pe trei ipoteze de volum."""
    print(f"{len(randuri)} canale de extras, fereastră {luni} luni, pauză {PAUZA:g} s:")
    for r in randuri:
        print(f"  {r['slug']:20} channels.list {json.dumps(params_canal(r), ensure_ascii=False)}")
    for v in pe_an:
        u = unitati_pe_banca(math.ceil(v * luni / 12))
        tot = u * len(randuri)
        print(f"  la {v:3} videoclipuri/an pe canal: {u} unități/bancă, {tot} în total "
              f"({tot / 10000:.1%} din cota zilnică de 10.000), ~{tot * (PAUZA + 0.5) / 60:.0f} min")
    print(f"  plafon: {1 + 2 * MAX_PAGINI} unități/bancă ({MAX_PAGINI} pagini de uploads)")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--descopera", action="store_true", help="offline: canalele din Bronze -> date/youtube_canale.csv")
    ap.add_argument("--banca", help="doar o bancă (slug)")
    ap.add_argument("--luni", type=int, default=12)
    ap.add_argument("--simulare", action="store_true", help="fără nicio cerere")
    ap.add_argument("--curata", action="store_true", help="doar retenția de 30 de zile")
    a = ap.parse_args()

    # curățarea întâi: șterge doar fișiere expirate, pe care `referinta` (din
    # `extrage`) oricum nu le-ar folosi; `extrageri.txt` nu e atins
    sterse = curata()
    if sterse or a.curata:
        print(f"retenție {RETENTIE_ZILE} de zile (III.E.4.d): {len(sterse)} fișiere șterse "
              f"din {DIR_IESIRE} {' '.join(sterse)}")
    if a.curata:
        return
    if a.descopera:
        randuri = randuri_csv(descopera())
        for r in randuri:
            print(f"{r['slug']:20} {r['stare']:8} {r.get('canal') or '':28} "
                  f"{r.get('nivel') or '':5} {r.get('pagini')}")
        print(f"scris {scrie_csv(randuri)}")
        return

    randuri = citeste_canale()
    if a.banca:
        randuri = [r for r in randuri if r["slug"] == a.banca]
        if not randuri:
            sys.exit(f"{a.banca}: niciun canal GASIT cu nivel RO în {CSV_CANALE}")
    if a.simulare:
        simulare(randuri, a.luni)
        return
    client = Client(config.cere("YOUTUBE_API_KEY"))
    _, cale = extrage(client, randuri, a.luni)
    print(f"{len(client.jurnal)} cereri · {client.unitati} unități · scris {cale}")


if __name__ == "__main__":
    main()
