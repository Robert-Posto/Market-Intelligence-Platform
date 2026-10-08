"""Rulările manuale (pagina „Rulare manuală”, grupul Jobs; până pe 06.10.2026 în
Overview): o listă fixă de scripturi de colectare și cele trei joburi ale fluxului
de comparație cu Libra (`JOBURI`), pornite la cerere din interfață.

De ce: scripturile ar rula în mod normal automat (stratul autonom, încă
înghețat); până atunci, Robert vrea „doar opțiunea să actualizeze manual”, de
pe laptopul lui. Funcția e activă NUMAI cu `MIP_PERMITE_RULARI=1` în `.env`;
fără ea, pe serverul comun, Overview rămâne doar-citire, ca înainte.

Serverul devine astfel capabil să pornească procese, deci regulile sunt
strânse, toate aici:
  - lista e fixă (`COMENZI`): id → argumente scrise în cod, fără shell; din
    cerere vin doar id-ul (căutat în listă) și, unde scriptul îl suportă,
    slug-ul unei bănci (căutat în lista de slug-uri); nimic altceva din cerere
    nu ajunge în linia de comandă;
  - o singură rulare odată (a doua primește „rulează deja …”); mai multe bănci
    alese odată (sau „toate”) stau la coadă, fiecare cu propriul proces, jurnal
    și rând în istoric. Pornesc una după alta, cu excepția comenzilor cu
    `paralel_banci`, unde rulează atâtea bănci simultan (vezi JOBURI);
  - cererile de scriere trec prin `verifica_cerere` (Host, Origin, token).

Fără TikTok (neaprobat), Google (exportul manual al colegului), fără
`--de-la-zero` sau alt pas care golește date și fără migrări.

Jurnalele: `loguri/rulari/<id>_<AAAAMMZZ_HHMMSS>.log`, iar la final un rând
în `loguri/rulari/istoric.jsonl`, din care se calculează estimarea (mediana
duratelor reale, pe aceeași bancă dacă există).
"""

import datetime
import hmac
import json
import os
import secrets
import statistics
import subprocess
import sys
import threading
import time

RADACINA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_RULARI = os.path.join(RADACINA, "loguri", "rulari")

# Rezerva LLM a extracției de prețuri doar din răspunsurile deja plătite
# (`ingest/llm_rezerva.py`): fără ea, `--llm-rezerva` ar face apeluri noi,
# plătite, pornite dintr-un clic.
FARA_LLM_PLATIT = {"MIP_LLM_DOAR_CACHE": "1"}

# `banca`: None = scriptul nu primește bancă; "optional" = toate băncile sau
# una; "obligatoriu" = doar pe o bancă (rularea pe toate e o populare de la
# zero, care nu stă aici).
# Estimările implicite sunt măsurate (datele în comentariu); după primele
# rulări din Overview, contează mediana din istoric.
COMENZI = [
    {"id": "bnr", "nume": "Indicii BNR",
     "ce": "Citește ROBOR, ROBID și IRCC de pe bnr.ro (Playwright) și adaugă zilele noi; istoricul din bază rămâne.",
     "argumente": ["ingest/load_bnr.py"], "banca": None, "internet": True,
     "estimare_min": 1},
    # 01.10.2026: 51 de cereri, 10:49:21 → 10:51:24
    {"id": "youtube", "nume": "YouTube",
     "ce": "Canalele oficiale și videoclipurile din ultimele 12 luni, prin YouTube Data API, într-un fișier local din output/youtube/ (nu în bază).",
     "argumente": ["ingest/youtube_api.py", "--luni", "12"], "banca": None, "internet": True,
     "estimare_min": 2},
    # 19 aplicații: un Lookup grupat + o pagină pe aplicație, la 3 s
    {"id": "mobil", "nume": "Aplicații iOS",
     "ce": "Versiunea, nota, distribuția pe stele, capturile și recenziile din App Store; recenziile se adună, nu se șterg.",
     "argumente": ["ingest/load_mobil.py"], "banca": None, "internet": True,
     "estimare_min": 2},
    # 30.09.2026, toate băncile: 14:36 → 15:37 (61 min); Raiffeisen singură ~13 min
    {"id": "campanii", "nume": "Campanii de pe site-uri",
     "ce": "Caută campaniile pe site-urile băncilor (sitemap, huburi, pagina principală) și rescrie campaniile băncii; robots.txt și pauzele se respectă.",
     "argumente": ["ingest/campanii.py"], "banca": "optional", "internet": True,
     "estimare_min": 60, "estimare_banca_min": 5},
    # 30.09.2026, toate băncile, fără corpul comunicatelor: 15:37:01 → 15:38:15
    {"id": "newsroom", "nume": "Comunicate de presă",
     "ce": "Lista comunicatelor din newsroom-ul fiecărei bănci (titlu, dată, adresă), fără corpul lor.",
     "argumente": ["ingest/campanii.py", "--newsroom"], "banca": "optional", "internet": True,
     "estimare_min": 2, "estimare_banca_min": 1},
    # 29.09.2026: 706 cereri la ~11 s (pauza de 10 s + răspunsul), ~140 min
    # cumulat pe cele trei porniri; băncile deja luate în aceeași zi se sar
    {"id": "bing", "nume": "Reclame Bing",
     "ce": "Reclamele livrate în România, din Microsoft Ad Library (API public), într-un fișier local din output/reclame/ (nu în bază); se oprește singur la refuzuri repetate (429).",
     "argumente": ["ingest/microsoft_ad_library.py"], "banca": None, "internet": True,
     "estimare_min": 140},
    # Fără --din-bronze: amprentele băncii se șterg, descoperirea rulează din
    # nou și fiecare sursă se descarcă iar (`ruleaza_banca`); valorile
    # `populare` ale băncii se înlocuiesc cu ce iese acum.
    {"id": "preturi", "nume": "Prețuri și dobânzi",
     "ce": "Descoperă din nou sursele băncii, le descarcă pe toate și îi rescrie prețurile și dobânzile; rezerva LLM doar din cache, fără apeluri plătite.",
     "argumente": ["ingest/populare_initiala.py", "--llm-rezerva"], "banca": "obligatoriu", "internet": True,
     "mediu": FARA_LLM_PLATIT, "estimare_banca_min": 20},
    {"id": "refacere", "nume": "Refacere din Bronze",
     "ce": "Reextrage prețurile și dobânzile băncii din documentele deja salvate în Bronze, fără nicio cerere; rezerva LLM doar din cache.",
     "argumente": ["ingest/populare_initiala.py", "--din-bronze", "--llm-rezerva"], "banca": "obligatoriu", "internet": False,
     "mediu": FARA_LLM_PLATIT, "estimare_banca_min": 10},
]

# Joburile fluxului de comparație cu Libra (pagina „Rulare manuală”, grupul Jobs): id-ul e
# codul din `job_types`, ca estimarea să se ia din `jobs`. SPRE DEOSEBIRE de cele de mai sus,
# cheamă modelul, deci costă (06.10.2026: discovery $0,04–0,53 pe produs, extragere
# $0–0,37); pagina arată estimarea de cost înainte de pornire, iar pornirea e un clic
# explicit după ea. Băncile sunt cele din `extragere_produse_bancare/banci.json` (30), nu
# cele din `ingest/banks.py`; produsul e un cod din `produse_libra`, verificat pe listă.
# Fiecare script își scrie singur jobul în `jobs` / `jobs_error` (jurnal_joburi.py).
# `fara_mediu`: cheia API vine din `extragere_produse_bancare/.env`, citită de scripturi cu
# load_dotenv, care NU suprascrie o variabilă existentă. Serverul pune în mediu `.env`-ul din
# rădăcină (config.py), unde ANTHROPIC_API_KEY e un placeholder: jobul #172 (06.10.2026) a
# moștenit-o și a primit 401 „API key is invalid”. Fără ea în mediu, ca din terminal.
FARA_CHEIA_SERVERULUI = ["ANTHROPIC_API_KEY"]
# `paralel_banci`: la mai multe bănci, câte rulează simultan (07.10.2026). Fiecare bancă își
# scrie fișierele ei (inventare-libra/<banca>/, valori-<banca>.json, produse-<banca>.json) și
# rândurile ei în bază, deci procesele nu se calcă. Fiecare are deja 3–4 cereri la model în
# paralel: 3 bănci înseamnă ~9–12, cât încape fără 429 de la API. Aplicațiile mobile rămân pe
# rând: `scrie_brief` rescrie un fișier comun tuturor băncilor, iar App Store dă 429 (06.10.2026).
PARALEL_BANCI = 3
JOBURI = [
    {"id": "discovery", "nume": "Discovery surse",
     "ce": "Caută pe site-ul băncii echivalentul produsului Libra și îi salvează sursele (surse_libra); refăcut chiar dacă există deja, cu limita de 3 minute.",
     "argumente": ["extragere_produse_bancare/descopera_surse_libra.py", "--forteaza"],
     "banca": "obligatoriu", "produs": "obligatoriu", "banci": "extragere", "grup": "joburi", "platit": True,
     "internet": True, "estimare_banca_min": 1, "fara_mediu": FARA_CHEIA_SERVERULUI,
     "paralel_banci": PARALEL_BANCI},
    {"id": "extragere", "nume": "Extragere date",
     "ce": "Descarcă sursele găsite la discovery și extrage valorile produsului (comparatie_libra); documentele neschimbate nu se plătesc din nou.",
     "argumente": ["extragere_produse_bancare/extrage_comparatie_libra.py"],
     "banca": "obligatoriu", "produs": "obligatoriu", "banci": "extragere", "grup": "joburi", "platit": True,
     "internet": True, "estimare_banca_min": 1, "fara_mediu": FARA_CHEIA_SERVERULUI,
     "paralel_banci": PARALEL_BANCI},
    {"id": "produse_noi", "nume": "Produse pe care Libra nu le are",
     "ce": "Parcurge site-ul băncii (sitemap, meniuri) și clasifică paginile de produs fără echivalent în catalogul Libra (products_discovery).",
     "argumente": ["extragere_produse_bancare/descopera_produse.py"],
     "banca": "obligatoriu", "produs": None, "banci": "extragere", "grup": "joburi", "platit": True,
     "internet": True, "estimare_banca_min": 15, "fara_mediu": FARA_CHEIA_SERVERULUI,
     "paralel_banci": PARALEL_BANCI},
    # 07.10.2026, ING: 27 s, din care ~16 s brief-ul (iOS și Android în paralel), $0,074
    {"id": "aplicatii_mobile", "nume": "Aplicații mobile",
     "ce": "Nota, numărul de note și de descărcări, capturile și recenziile din App Store și Google Play, apoi brief-ul AI al recenziilor; brief-ul se sare dacă recenziile n-au schimbat.",
     "argumente": ["ingest/actualizeaza_aplicatii.py"],
     "banca": "obligatoriu", "produs": None, "banci": "aplicatii", "grup": "joburi", "platit": True,
     "internet": True, "estimare_banca_min": 1, "fara_mediu": FARA_CHEIA_SERVERULUI},
]
COMENZI = COMENZI + JOBURI
CALE_BANCI_EXTRAGERE = os.path.join(RADACINA, "extragere_produse_bancare", "banci.json")
# băncile cu aplicație: iOS confirmat de cauta_app_id.py sau colectat din Google Play
CALE_IOS = os.path.join(RADACINA, "date", "app_id_gasite.json")
CALE_PLAY = os.path.join(RADACINA, "date", "google_play.json")

GAZDE = ("localhost", "127.0.0.1", "[::1]")
RANDURI_JURNAL = 30
RANDURI_JURNAL_PARALEL = 8   # cu mai multe bănci în lucru, câte rânduri din jurnalul fiecăreia
RANDURI_ISTORIC = 10
ORICE_BANCA = "*"     # estimarea „pe o bancă oarecare”; niciun slug nu e „*”


def activ():
    """Doar pe laptopul lui Robert: `.env` cu `MIP_PERMITE_RULARI=1`."""
    return os.environ.get("MIP_PERMITE_RULARI", "").strip() == "1"


class Respins(Exception):
    """Cerere care nu trece de lista albă (HTTP 400)."""


class Ocupat(Exception):
    """Rulează deja ceva (HTTP 409)."""


def verifica_cerere(antete, port, token=None, porturi_extra=()):
    """None dacă cererea vine de pe pagina noastră; altfel motivul refuzului.

    `verify_request` din server oprește deja tot ce nu e de pe loopback, dar
    asta nu oprește browserul de pe același laptop: orice pagină deschisă în el
    poate trimite un POST spre localhost (CSRF), iar un domeniu care se
    rezolvă la 127.0.0.1 ajunge la noi cu propriul nume în Host (DNS
    rebinding). De aceea: Host doar numele de loopback cu portul nostru,
    Origin (când e trimis) exact pagina noastră, iar la scriere un token
    aleator, pe care îl primește doar pagina noastră, prin GET.

    `porturi_extra`: doar pentru Vox, care merge și din `npm run dev`. Proxy-ul
    Vite (forma scurtă din vite.config.ts) rescrie Host-ul la server, dar lasă Origin pe pagina
    Vite: măsurat pe 06.10.2026, Host 127.0.0.1:<țintă>, Origin http://localhost:5174. Deci
    Host-ul rămâne strict, iar porturile în plus se acceptă doar la Origin, tot pe nume de
    loopback. Rulările nu-l primesc, deci pentru ele nu se schimbă nimic.
    """
    gazda = antete.get("Host") or ""
    if gazda not in {f"{g}:{port}" for g in GAZDE}:
        return "Host nepermis"
    origine = antete.get("Origin")
    permise = {f"http://{gazda}"} | {f"http://{g}:{p}" for g in GAZDE for p in porturi_extra}
    if origine is not None and origine not in permise:
        return "Origin nepermis"
    site = antete.get("Sec-Fetch-Site")
    if site is not None and site not in ("same-origin", "none"):
        return "cerere de pe alt site"
    if token is not None:
        primit = antete.get("X-MIP-Token") or ""
        if not hmac.compare_digest(primit.encode("utf-8"), token.encode("utf-8")):
            return "token lipsă sau greșit"
    return None


def _proces_viu(pid):
    """Procesul mai rulează? Doar pentru rularea rămasă de dinaintea unei
    reporniri a serverului (pentru restul avem obiectul `Popen`)."""
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    # pe Windows `os.kill(pid, 0)` ar OPRI procesul (TerminateProcess)
    import ctypes
    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x1000, False, pid)        # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    try:
        cod = ctypes.c_ulong()
        return bool(k.GetExitCodeProcess(h, ctypes.byref(cod))) and cod.value == 259   # STILL_ACTIVE
    finally:
        k.CloseHandle(h)


def _opreste_arbore(pid):
    """Tot arborele: `populare_initiala.py` și Playwright pornesc procese-copil,
    care altfel ar rămâne să descarce după „Oprește”."""
    if os.name == "nt":
        taskkill = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "taskkill.exe")
        subprocess.run([taskkill, "/T", "/F", "/PID", str(pid)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    else:
        import signal
        try:
            os.killpg(pid, signal.SIGKILL)
        except OSError:
            pass


def coada_fisier(cale, n):
    """Ultimele n rânduri nevide din jurnal (doar ultimii 64 KB din fișier)."""
    try:
        with open(cale, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 65536))
            text = f.read().decode("utf-8", errors="replace")
    except OSError:
        return []
    return [r for r in text.splitlines() if r.strip()][-n:]


def _acum():
    return datetime.datetime.now().astimezone()


def _slugs_extragere():
    with open(CALE_BANCI_EXTRAGERE, encoding="utf-8") as f:
        return [b["id"] for b in json.load(f)["banci"]]


def _slugs_aplicatii():
    """Băncile cu aplicație pe cel puțin o platformă; citite la fiecare cerere, fișierele se schimbă la colectare."""
    slugs = set()
    for cale, cheie in ((CALE_IOS, None), (CALE_PLAY, "aplicatii")):
        try:
            with open(cale, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue
        slugs |= set(d.get(cheie, {}) if cheie else d)
    return sorted(slugs)


class Rulari:
    def __init__(self, comenzi=COMENZI, dir_rulari=DIR_RULARI, slugs=lambda: [],
                 interpretor=sys.executable, radacina=RADACINA, produse=lambda: [],
                 slugs_extragere=_slugs_extragere):
        self.comenzi = {c["id"]: c for c in comenzi}
        self.ordine = [c["id"] for c in comenzi]
        self.dir = dir_rulari
        self._sursa_slugs = slugs
        self._slugs = None
        self._sursa_produse = produse
        self._produse = None
        self._sursa_slugs_extragere = slugs_extragere
        self._slugs_extragere = None
        self.interpretor = interpretor
        self.radacina = radacina
        self.token = secrets.token_urlsafe(32)
        self.lacat = threading.Lock()
        self.curenta = None
        self._reia_dupa_repornire()

    # ---------------- lista albă ----------------

    def slugs(self):
        # o conexiune nouă la Postgres costă ~2 s pe Windows, iar pagina
        # întreabă la 2 s cât timp rulează ceva: lista se ia o singură dată
        if not self._slugs:
            try:
                self._slugs = sorted(set(self._sursa_slugs()))
            except Exception:
                return []
        return self._slugs

    def slugs_extragere(self):
        if not self._slugs_extragere:
            try:
                self._slugs_extragere = sorted(set(self._sursa_slugs_extragere()))
            except Exception:
                return []
        return self._slugs_extragere

    def produse(self):
        """Codurile active din `produse_libra`: singurele care pot ajunge în `--produse`."""
        if not self._produse:
            try:
                self._produse = sorted(set(self._sursa_produse()))
            except Exception:
                return []
        return self._produse

    def banci_comanda(self, c):
        """Băncile pe care se poate rula comanda: lista ei, nu neapărat cea a colectării generale."""
        if c.get("banci") == "extragere":
            return self.slugs_extragere()
        if c.get("banci") == "aplicatii":
            return _slugs_aplicatii()
        return self.slugs()

    def valideaza(self, id_comanda, banca, produs=None):
        c = self.comenzi.get(id_comanda) if isinstance(id_comanda, str) else None
        if c is None:
            raise Respins("comandă necunoscută")
        banci = self.banci_comanda(c)
        if banca in (None, ""):
            banca = None
        elif not isinstance(banca, str) or banca not in banci:
            raise Respins("bancă necunoscută")
        if banca and c["banca"] is None:
            raise Respins(f"„{c['nume']}” nu se rulează pe o bancă")
        if not banca and c["banca"] == "obligatoriu":
            raise Respins(f"„{c['nume']}” cere o bancă")
        if produs in (None, ""):
            produs = None
        elif not isinstance(produs, str) or produs not in self.produse():
            raise Respins("produs necunoscut")
        if produs and c.get("produs") is None:
            raise Respins(f"„{c['nume']}” nu se rulează pe un produs")
        if not produs and c.get("produs") == "obligatoriu":
            raise Respins(f"„{c['nume']}” cere un produs")
        return c, banca, produs

    def argv(self, c, banca, produs=None):
        return ([self.interpretor, "-u"] + list(c["argumente"]) + (["--banca", banca] if banca else [])
                + (["--produse", produs] if produs else []))

    # ---------------- istoric și estimare ----------------

    def _cale(self, nume):
        return os.path.join(self.dir, nume)

    def istoric(self):
        randuri = []
        try:
            with open(self._cale("istoric.jsonl"), encoding="utf-8") as f:
                for r in f:
                    try:
                        randuri.append(json.loads(r))
                    except ValueError:
                        pass
        except OSError:
            pass
        return randuri

    def estimare(self, id_comanda, banca=None, istoric=None):
        """Secunde: mediana rulărilor încheiate cu succes (cod 0, neoprite) ale
        aceleiași comenzi, pe aceeași bancă dacă există; altfel implicitul."""
        c = self.comenzi[id_comanda]
        reusite = [r for r in (self.istoric() if istoric is None else istoric)
                   if r.get("id") == id_comanda and r.get("cod") == 0 and not r.get("oprit")
                   and isinstance(r.get("durata_s"), (int, float))]
        if banca:
            # pe bancă diferă mult (BCR are de zece ori sursele Vistei), deci
            # aceeași bancă întâi, apoi orice bancă, apoi implicitul
            for grup in ([r for r in reusite if r.get("banca") == banca],
                         [r for r in reusite if r.get("banca")]):
                if grup:
                    return round(statistics.median(r["durata_s"] for r in grup)), "istoric", len(grup)
            return c.get("estimare_banca_min", c.get("estimare_min", 5)) * 60, "implicit", 0
        grup = [r for r in reusite if not r.get("banca")]
        if grup:
            return round(statistics.median(r["durata_s"] for r in grup)), "istoric", len(grup)
        return (c.get("estimare_min") or c.get("estimare_banca_min") or 5) * 60, "implicit", 0

    # ---------------- pornire / oprire ----------------

    def porneste(self, id_comanda, banca=None, produs=None, banci=None, toate=False):
        """O bancă (`banca`), mai multe (`banci`, la coadă) sau toate (`toate`).

        „Toate” la o comandă cu banca opțională e o singură rulare fără --banca (scriptul
        își parcurge singur băncile); la una cu banca obligatorie, coada tuturor băncilor ei.
        Coada pornește pe rând sau, la o comandă cu `paralel_banci`, câte atâtea bănci odată.
        """
        if banci is not None and (not isinstance(banci, list) or not all(isinstance(b, str) for b in banci)):
            raise Respins("lista de bănci nu e validă")
        if toate or banci:
            c = self.comenzi.get(id_comanda) if isinstance(id_comanda, str) else None
            if c is None:
                raise Respins("comandă necunoscută")
            if c["banca"] is None:
                raise Respins(f"„{c['nume']}” nu se rulează pe o bancă")
            if toate and c["banca"] == "optional":
                banci = []
            elif toate:
                banci = self.banci_comanda(c)
            # aceeași bancă de două ori ar plăti de două ori același job
            banci = list(dict.fromkeys(banci))
            for b in banci:
                self.valideaza(id_comanda, b, produs)
            if len(banci) > 1:
                c, _, produs = self.valideaza(id_comanda, banci[0], produs)
                with self.lacat:
                    self._liber()
                    return self._lanseaza(c, banci[0], produs,
                                          {"total": len(banci), "ramase": banci[1:], "facute": [], "pornite": 0})
            banca = banci[0] if banci else None
        c, banca, produs = self.valideaza(id_comanda, banca, produs)
        with self.lacat:
            self._liber()
            return self._lanseaza(c, banca, produs)

    def _liber(self):
        if self.curenta:
            raise Ocupat(f"rulează deja: {self.comenzi.get(self.curenta['id'], {}).get('nume', self.curenta['id'])}")

    @staticmethod
    def locuri(c):
        """Câte bănci ale cozii rulează simultan: 1, în afară de comenzile cu `paralel_banci`."""
        return max(1, int(c.get("paralel_banci") or 1))

    def _lanseaza(self, c, banca, produs, coada=None):
        """Pornește rularea: prima bancă și, la o comandă cu `paralel_banci`, încă atâtea
        din coadă cât încap. Apelat cu lacătul luat."""
        cur = {"id": c["id"], "produs": produs, "inceput": _acum().isoformat(timespec="seconds"),
               "t0": time.time(), "oprit": False, "coada": coada, "procese": []}
        prim = self._porneste_proces(cur, c, banca)
        self.curenta = cur
        self._umple(cur)
        self._scrie_curenta()
        return {"id": cur["id"], "produs": produs, "inceput": cur["inceput"], "banca": banca,
                "pid": prim["pid"], "log": prim["log"], "coada": coada,
                "procese": [{k: p[k] for k in ("banca", "pid", "log")} for p in cur["procese"]]}

    def _porneste_proces(self, cur, c, banca):
        """Procesul unei bănci din rularea `cur`; apelat cu lacătul luat."""
        os.makedirs(self.dir, exist_ok=True)
        inceput = _acum()
        coada = cur.get("coada")
        produs = cur["produs"]
        # la coadă, mai multe bănci pot porni în aceeași secundă: banca intră în numele jurnalului
        cale_log = self._cale(f"{c['id']}_{inceput:%Y%m%d_%H%M%S}{'_' + banca if banca and coada else ''}.log")
        argv = self.argv(c, banca, produs)
        # MIP_RULARE_MANUALA: jurnal_joburi.py scrie jobul cu runed_manually = TRUE (migrarea 038)
        mediu = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1", MIP_RULARE_MANUALA="1",
                     **c.get("mediu", {}))
        for k in c.get("fara_mediu", ()):
            mediu.pop(k, None)
        pozitie = coada["pornite"] + 1 if coada else None
        text_pozitie = f" · {pozitie}/{coada['total']}" if coada else ""
        with open(cale_log, "w", encoding="utf-8") as log:
            log.write(f"# {c['nume']}{' · ' + banca if banca else ''}{' · ' + produs if produs else ''}{text_pozitie} · pornit manual la "
                      f"{inceput:%Y-%m-%d %H:%M:%S}\n# {' '.join(argv[1:])}\n")
            log.flush()
            p = subprocess.Popen(argv, cwd=self.radacina, stdout=log, stderr=subprocess.STDOUT,
                                 stdin=subprocess.DEVNULL, env=mediu,
                                 start_new_session=(os.name != "nt"))
        if coada:
            coada["pornite"] = pozitie
        estimare_s, _, _ = self.estimare(c["id"], banca)
        proc = {"banca": banca, "pid": p.pid, "log": os.path.basename(cale_log),
                "inceput": inceput.isoformat(timespec="seconds"), "t0": time.time(),
                "estimare_s": estimare_s, "pozitie": pozitie}
        cur["procese"].append(proc)
        threading.Thread(target=self._asteapta, args=(p, cur, proc), daemon=True).start()
        return proc

    def _umple(self, cur):
        """Pornește din coadă bănci până la `paralel_banci` în lucru; apelat cu lacătul luat.
        După „Oprește” sau după o repornire a serverului nu mai pornește nimic."""
        coada = cur.get("coada")
        c = self.comenzi.get(cur["id"])
        if not coada or not c or cur["oprit"] or cur.get("orfan"):
            return
        while coada["ramase"] and len(cur["procese"]) < self.locuri(c):
            urmatoarea = coada["ramase"].pop(0)
            try:
                self._porneste_proces(cur, c, urmatoarea)
            except OSError as exc:
                self._in_istoric({"id": cur["id"], "banca": urmatoarea, "sfarsit": _acum().isoformat(timespec="seconds"),
                                  "cod": None, "nota": f"coada oprită: nu s-a putut porni ({exc})"})
                coada["ramase"].clear()

    def _asteapta(self, p, cur, proc):
        cod = p.wait()
        with self.lacat:
            self._incheie(cur, proc, cod)

    def opreste(self):
        with self.lacat:
            cur = self.curenta
            if not cur:
                raise Respins("nu rulează nimic")
            cur["oprit"] = True
            # „Oprește” oprește tot: băncile în lucru și cele rămase la coadă
            anulate = len((cur.get("coada") or {}).get("ramase") or [])
            for proc in list(cur["procese"]):
                _opreste_arbore(proc["pid"])
                if cur.get("orfan") and not _proces_viu(proc["pid"]):
                    self._incheie(cur, proc, None)
        return {"oprit": cur["id"], "anulate": anulate}

    def _incheie(self, cur, proc, cod):
        """Rândul din istoric al unei bănci, apoi următoarea din coadă; apelat cu lacătul luat."""
        if self.curenta is not cur or proc not in cur["procese"]:
            return
        cur["procese"].remove(proc)
        rand = {"id": cur["id"], "banca": proc["banca"], "produs": cur.get("produs"), "inceput": proc["inceput"],
                "sfarsit": _acum().isoformat(timespec="seconds"),
                "durata_s": round(time.time() - proc["t0"]), "cod": cod, "oprit": bool(cur["oprit"]),
                "log": proc["log"], "ultimele": coada_fisier(self._cale(proc["log"]), RANDURI_ISTORIC)}
        coada = cur.get("coada")
        if coada:
            rand["coada"] = f"{proc['pozitie']}/{coada['total']}"
            coada["facute"].append({"banca": proc["banca"], "cod": cod})
        if cur.get("orfan"):
            rand["nota"] = "încheiată după o repornire a serverului: codul de ieșire nu se mai știe"
            if coada and coada["ramase"] and not cur["procese"]:
                # nu se reia singură la pornirea serverului: acum n-a cerut-o nimeni
                rand["nota"] += f"; coada rămasă ({', '.join(coada['ramase'])}) nu s-a mai pornit"
        os.makedirs(self.dir, exist_ok=True)
        self._in_istoric(rand)
        # o bancă eșuată nu oprește coada (o bancă blocată nu e motiv să nu rulezi restul); „Oprește” da
        self._umple(cur)
        if cur["procese"]:
            self._scrie_curenta()
            return
        self.curenta = None
        try:
            os.remove(self._cale("curenta.json"))
        except OSError:
            pass

    def _in_istoric(self, rand):
        with open(self._cale("istoric.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(rand, ensure_ascii=False) + "\n")

    # Rularea curentă stă și pe disc: dacă serverul e repornit cât rulează un
    # script de o oră, scriptul merge mai departe, iar fără fișierul ăsta
    # serverul nou ar crede că nu rulează nimic și ar lăsa să pornească al doilea.
    def _scrie_curenta(self):
        with open(self._cale("curenta.json"), "w", encoding="utf-8") as f:
            json.dump({k: v for k, v in self.curenta.items() if k != "orfan"}, f, ensure_ascii=False)

    def _reia_dupa_repornire(self):
        try:
            with open(self._cale("curenta.json"), encoding="utf-8") as f:
                cur = json.load(f)
        except (OSError, ValueError):
            return
        if "procese" not in cur:
            # scris înainte de 07.10.2026: un singur proces, cu datele lui pe rulare
            coada = cur.get("coada")
            cur["procese"] = [{"banca": cur.get("banca"), "pid": cur.get("pid", 0), "log": cur.get("log", ""),
                               "inceput": cur.get("inceput"), "t0": cur.get("t0", 0), "estimare_s": cur.get("estimare_s"),
                               "pozitie": len(coada["facute"]) + 1 if coada else None}]
        cur["orfan"] = True
        self.curenta = cur
        # peste o zi, PID-ul poate fi deja al altui proces
        vechi = time.time() - cur.get("t0", 0) >= 86400
        with self.lacat:
            for proc in list(cur["procese"]):
                if vechi or not _proces_viu(proc.get("pid", 0)):
                    self._incheie(cur, proc, None)
            if self.curenta is cur and not cur["procese"]:
                self.curenta = None

    def _verifica_orfan(self):
        cur = self.curenta
        if cur and cur.get("orfan"):
            with self.lacat:
                for proc in list(cur["procese"]):
                    if not _proces_viu(proc["pid"]):
                        self._incheie(cur, proc, None)

    # ---------------- starea, pentru GET /api/rulari ----------------

    def stare(self):
        self._verifica_orfan()
        ist = self.istoric()
        banci = self.slugs()
        comenzi = []
        for id_c in self.ordine:
            c = self.comenzi[id_c]
            e = {"id": id_c, "nume": c["nume"], "ce": c["ce"], "internet": c["internet"],
                 "banca": c["banca"], "produs": c.get("produs"), "grup": c.get("grup"),
                 "platit": bool(c.get("platit")), "paralel_banci": self.locuri(c)}
            if c["banca"] != "obligatoriu":
                e["estimare_s"], e["estimare_sursa"], e["masurate"] = self.estimare(id_c, None, ist)
            if c["banca"]:
                e["estimare_banca_s"], e["estimare_banca_sursa"], _ = self.estimare(id_c, ORICE_BANCA, ist)
                lista = self.banci_comanda(c)
                e["estimari_banca"] = {b: self.estimare(id_c, b, ist)[0] for b in lista
                                       if any(r.get("id") == id_c and r.get("banca") == b for r in ist)}
            ale = [r for r in ist if r.get("id") == id_c]
            e["ultima"] = ale[-1] if ale else None
            comenzi.append(e)
        return {"activ": activ(), "comenzi": comenzi, "banci": banci, "banci_joburi": self.slugs_extragere(),
                "curenta": self._vedere(self.curenta)}

    def _vedere(self, cur):
        """Rularea curentă pentru pagină. Cu o singură bancă în lucru, câmpurile de sus sunt
        ale ei (ca înainte); cu mai multe, fiecare are bara și jurnalul ei în `procese`."""
        if not cur:
            return None
        acum = time.time()
        procese = list(cur["procese"])
        unul = procese[0] if len(procese) == 1 else None
        v = {"id": cur["id"], "nume": self.comenzi.get(cur["id"], {}).get("nume", cur["id"]),
             "produs": cur.get("produs"), "oprit": cur["oprit"], "dupa_repornire": bool(cur.get("orfan"))}
        if unul:
            v.update(banca=unul["banca"], inceput=unul["inceput"], scurs_s=round(acum - unul["t0"]),
                     estimare_s=unul["estimare_s"], log=unul["log"],
                     jurnal=coada_fisier(self._cale(unul["log"]), RANDURI_JURNAL))
        else:
            v.update(banca=None, inceput=cur["inceput"], scurs_s=round(acum - cur["t0"]), estimare_s=None,
                     log=procese[0]["log"] if procese else "", jurnal=[])
        v["procese"] = [{"banca": p["banca"], "inceput": p["inceput"], "scurs_s": round(acum - p["t0"]),
                         "estimare_s": p["estimare_s"], "log": p["log"],
                         "jurnal": coada_fisier(self._cale(p["log"]), RANDURI_JURNAL_PARALEL)}
                        for p in procese] if len(procese) > 1 else []
        coada = cur.get("coada")
        v["coada"] = ({"total": coada["total"], "pozitie": coada.get("pornite") or len(coada["facute"]) + 1,
                       "in_lucru": len(procese), "ramase": list(coada["ramase"]), "facute": list(coada["facute"])}
                      if coada else None)
        return v
