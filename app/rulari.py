"""Rulările manuale din Overview: o listă fixă de scripturi de colectare,
pornite la cerere din interfață.

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
  - un singur proces odată (al doilea primește „rulează deja …”);
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

GAZDE = ("localhost", "127.0.0.1", "[::1]")
RANDURI_JURNAL = 30
RANDURI_ISTORIC = 10
ORICE_BANCA = "*"     # estimarea „pe o bancă oarecare”; niciun slug nu e „*”


def activ():
    """Doar pe laptopul lui Robert: `.env` cu `MIP_PERMITE_RULARI=1`."""
    return os.environ.get("MIP_PERMITE_RULARI", "").strip() == "1"


class Respins(Exception):
    """Cerere care nu trece de lista albă (HTTP 400)."""


class Ocupat(Exception):
    """Rulează deja ceva (HTTP 409)."""


def verifica_cerere(antete, port, token=None):
    """None dacă cererea vine de pe pagina noastră; altfel motivul refuzului.

    `verify_request` din server oprește deja tot ce nu e de pe loopback, dar
    asta nu oprește browserul de pe același laptop: orice pagină deschisă în el
    poate trimite un POST spre localhost (CSRF), iar un domeniu care se
    rezolvă la 127.0.0.1 ajunge la noi cu propriul nume în Host (DNS
    rebinding). De aceea: Host doar numele de loopback cu portul nostru,
    Origin (când e trimis) exact pagina noastră, iar la scriere un token
    aleator, pe care îl primește doar pagina noastră, prin GET.
    """
    gazda = antete.get("Host") or ""
    if gazda not in {f"{g}:{port}" for g in GAZDE}:
        return "Host nepermis"
    origine = antete.get("Origin")
    if origine is not None and origine != f"http://{gazda}":
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


class Rulari:
    def __init__(self, comenzi=COMENZI, dir_rulari=DIR_RULARI, slugs=lambda: [],
                 interpretor=sys.executable, radacina=RADACINA):
        self.comenzi = {c["id"]: c for c in comenzi}
        self.ordine = [c["id"] for c in comenzi]
        self.dir = dir_rulari
        self._sursa_slugs = slugs
        self._slugs = None
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

    def valideaza(self, id_comanda, banca):
        c = self.comenzi.get(id_comanda) if isinstance(id_comanda, str) else None
        if c is None:
            raise Respins("comandă necunoscută")
        if banca in (None, ""):
            banca = None
        elif not isinstance(banca, str) or banca not in self.slugs():
            raise Respins("bancă necunoscută")
        if banca and c["banca"] is None:
            raise Respins(f"„{c['nume']}” nu se rulează pe o bancă")
        if not banca and c["banca"] == "obligatoriu":
            raise Respins(f"„{c['nume']}” cere o bancă")
        return c, banca

    def argv(self, c, banca):
        return [self.interpretor, "-u"] + list(c["argumente"]) + (["--banca", banca] if banca else [])

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

    def porneste(self, id_comanda, banca=None):
        c, banca = self.valideaza(id_comanda, banca)
        with self.lacat:
            if self.curenta:
                raise Ocupat(f"rulează deja: {self.comenzi.get(self.curenta['id'], {}).get('nume', self.curenta['id'])}")
            os.makedirs(self.dir, exist_ok=True)
            inceput = _acum()
            cale_log = self._cale(f"{c['id']}_{inceput:%Y%m%d_%H%M%S}.log")
            argv = self.argv(c, banca)
            mediu = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1", **c.get("mediu", {}))
            with open(cale_log, "w", encoding="utf-8") as log:
                log.write(f"# {c['nume']}{' · ' + banca if banca else ''} · pornit din Overview la "
                          f"{inceput:%Y-%m-%d %H:%M:%S}\n# {' '.join(argv[1:])}\n")
                log.flush()
                p = subprocess.Popen(argv, cwd=self.radacina, stdout=log, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, env=mediu,
                                     start_new_session=(os.name != "nt"))
            estimare_s, _, _ = self.estimare(c["id"], banca)
            self.curenta = {"id": c["id"], "banca": banca, "inceput": inceput.isoformat(timespec="seconds"),
                            "t0": time.time(), "pid": p.pid, "log": os.path.basename(cale_log),
                            "estimare_s": estimare_s, "oprit": False}
            self._scrie_curenta()
            threading.Thread(target=self._asteapta, args=(p, self.curenta), daemon=True).start()
            return dict(self.curenta)

    def _asteapta(self, p, cur):
        cod = p.wait()
        with self.lacat:
            self._incheie(cur, cod)

    def opreste(self):
        with self.lacat:
            cur = self.curenta
            if not cur:
                raise Respins("nu rulează nimic")
            cur["oprit"] = True
            _opreste_arbore(cur["pid"])
            if cur.get("orfan") and not _proces_viu(cur["pid"]):
                self._incheie(cur, None)
        return {"oprit": cur["id"]}

    def _incheie(self, cur, cod):
        """Rândul din istoric; apelat cu lacătul luat."""
        if self.curenta is not cur:
            return
        sfarsit = _acum()
        rand = {"id": cur["id"], "banca": cur["banca"], "inceput": cur["inceput"],
                "sfarsit": sfarsit.isoformat(timespec="seconds"),
                "durata_s": round(time.time() - cur["t0"]), "cod": cod, "oprit": bool(cur["oprit"]),
                "log": cur["log"], "ultimele": coada_fisier(self._cale(cur["log"]), RANDURI_ISTORIC)}
        if cur.get("orfan"):
            rand["nota"] = "încheiată după o repornire a serverului: codul de ieșire nu se mai știe"
        os.makedirs(self.dir, exist_ok=True)
        with open(self._cale("istoric.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(rand, ensure_ascii=False) + "\n")
        self.curenta = None
        try:
            os.remove(self._cale("curenta.json"))
        except OSError:
            pass

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
        cur["orfan"] = True
        self.curenta = cur
        # peste o zi, PID-ul poate fi deja al altui proces
        if not (time.time() - cur.get("t0", 0) < 86400 and _proces_viu(cur.get("pid", 0))):
            with self.lacat:
                self._incheie(cur, None)

    def _verifica_orfan(self):
        cur = self.curenta
        if cur and cur.get("orfan") and not _proces_viu(cur["pid"]):
            with self.lacat:
                self._incheie(cur, None)

    # ---------------- starea, pentru GET /api/rulari ----------------

    def stare(self):
        self._verifica_orfan()
        ist = self.istoric()
        banci = self.slugs()
        comenzi = []
        for id_c in self.ordine:
            c = self.comenzi[id_c]
            e = {"id": id_c, "nume": c["nume"], "ce": c["ce"], "internet": c["internet"],
                 "banca": c["banca"]}
            if c["banca"] != "obligatoriu":
                e["estimare_s"], e["estimare_sursa"], e["masurate"] = self.estimare(id_c, None, ist)
            if c["banca"]:
                e["estimare_banca_s"], e["estimare_banca_sursa"], _ = self.estimare(id_c, ORICE_BANCA, ist)
                e["estimari_banca"] = {b: self.estimare(id_c, b, ist)[0] for b in banci
                                       if any(r.get("id") == id_c and r.get("banca") == b for r in ist)}
            ale = [r for r in ist if r.get("id") == id_c]
            e["ultima"] = ale[-1] if ale else None
            comenzi.append(e)
        cur = self.curenta
        curenta = None
        if cur:
            curenta = {k: cur[k] for k in ("id", "banca", "inceput", "estimare_s", "oprit", "log")}
            curenta["nume"] = self.comenzi.get(cur["id"], {}).get("nume", cur["id"])
            curenta["scurs_s"] = round(time.time() - cur["t0"])
            curenta["jurnal"] = coada_fisier(self._cale(cur["log"]), RANDURI_JURNAL)
            curenta["dupa_repornire"] = bool(cur.get("orfan"))
        return {"activ": activ(), "comenzi": comenzi, "banci": banci, "curenta": curenta}
