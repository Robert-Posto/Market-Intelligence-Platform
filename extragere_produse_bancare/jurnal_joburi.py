#!/usr/bin/env python3
"""
jurnal_joburi.py — fiecare rulare în `jobs`, fiecare eroare în `jobs_error`
(migrarea 032). Pagina /logging citește de acolo.

    from jurnal_joburi import Job

    with Job("discovery", banca="bcr", parametri=vars(arg)) as job:
        job.consum(MODEL, usage)                     # tokenii unui apel, sau ai unui lot
        job.eroare("timeout la fetch", context="DEPOZIT_TERMEN")
        job.rezumat = "41/57 produse cu surse"

La ieșirea din `with` se scriu ended_at, consumul final și starea:
  reusit     fără nicio eroare
  cu_erori   a terminat, dar cu cel puțin o eroare în jobs_error
  esuat      a ieșit pe o excepție (sau pe sys.exit cu mesaj); excepția se
             salvează ca eroare, cu traceback, și merge mai departe neatinsă
  intrerupt  Ctrl+C

`jobs.errors` nu se numără aici: trigger-ul din migrare îl crește la fiecare
rând din jobs_error, deci nu poate diverge de erorile salvate.

JURNALUL NU OPREȘTE NICIODATĂ UN JOB

  Dacă baza nu răspunde sau migrarea 032 nu e aplicată, se spune o dată pe
  stderr și restul apelurilor nu mai fac nimic. Un job de 4 dolari nu se
  pierde fiindcă nu i s-a putut scrie jurnalul.

  Consumul se scrie la cel mult PAUZA_SCRIERE secunde, nu la fiecare apel: la
  descopera_produse sunt sute de clasificări pe bancă. Erorile se scriu
  imediat, ca să apară în pagină cât timp jobul încă rulează.

Firele: descopera_surse_libra rulează produsele în paralel, deci contorii sunt
sub lacăt, iar fiecare scriere își deschide conexiunea ei (psycopg2 nu
împarte bine o conexiune între fire).
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import traceback

import psycopg2

import preturi

DSN = os.environ.get("MIP_DSN", "host=localhost port=5432 dbname=mip user=mip password=mip")
PAUZA_SCRIERE = 15
# jobs.runed_manually (migrarea 037): app/rulari.py pune variabila doar procesului pornit din
# pagina „Rulare manuală”; din terminal lipsește, deci jobul rămâne „automat”
MANUAL = os.environ.get("MIP_RULARE_MANUALA", "").strip() == "1"
# un traceback întreg e util; un HTML de 2 MB lipit într-o excepție, nu
LUNGIME_MAXIMA = 20_000


def _spune(m: str) -> None:
    print(f"[jurnal] {m}", file=sys.stderr, flush=True)


def _taie(text: str) -> str:
    text = str(text)
    return text if len(text) <= LUNGIME_MAXIMA else text[:LUNGIME_MAXIMA] + f"\n… (tăiat, {len(text)} caractere)"


class Job:
    def __init__(self, tip: str, banca: str | None = None, model: str | None = None,
                 parametri: dict | None = None):
        self.tip, self.banca, self.model = tip, banca, model
        self.parametri = parametri
        self.id: int | None = None
        self.rezumat: str | None = None
        self._lacat = threading.Lock()
        self._activ = True
        self._erori = 0
        self._ultima_scriere = 0.0
        self._consum = {"apeluri": 0, "intrare": 0, "iesire": 0, "citire_cache": 0, "scriere_cache": 0}
        self._cost = 0.0
        self._cost_complet = True
        self._modele_fara_pret: set[str] = set()

    # ── baza ──────────────────────────────────────────────────────

    def _scrie(self, sql: str, args: tuple) -> tuple | None:
        if not self._activ:
            return None
        conn = None
        try:
            # `with conn` doar face commit, nu închide; jurnalul deschide multe conexiuni scurte
            conn = psycopg2.connect(DSN, connect_timeout=5)
            with conn, conn.cursor() as cur:
                cur.execute(sql, args)
                return cur.fetchone() if cur.description else None
        except Exception as e:
            # o singură avertizare: altfel fiecare apel ar repeta-o
            self._activ = False
            _spune(f"nu pot scrie în jobs ({type(e).__name__}: {str(e).strip()[:200]}); "
                   f"jobul continuă fără jurnal. Migrarea 032 e aplicată?")
            return None
        finally:
            if conn is not None:
                conn.close()

    def _scrie_consum(self, final: bool = False, stare: str | None = None) -> None:
        with self._lacat:
            c, cost, complet = dict(self._consum), self._cost, self._cost_complet
            self._ultima_scriere = time.time()
        if self.id is None:
            return
        self._scrie(f"""
            UPDATE jobs SET apeluri = %s, tokeni_intrare = %s, tokeni_iesire = %s,
                   tokeni_cache_citire = %s, tokeni_cache_scriere = %s,
                   cost_usd = %s, cost_complet = %s, model = COALESCE(%s, model),
                   rezumat = COALESCE(%s, rezumat), actualizat_la = now()
                   {", ended_at = now(), stare = %s" if final else ""}
             WHERE id = %s""",
            (c["apeluri"], c["intrare"], c["iesire"], c["citire_cache"], c["scriere_cache"],
             round(cost, 6), complet, self.model, self.rezumat,
             *((stare,) if final else ()), self.id))

    # ── ce cheamă scripturile ─────────────────────────────────────

    def consum(self, model: str | None, usage: dict | None, apeluri: int | None = None) -> None:
        """
        Adună tokenii unui răspuns (sau ai unui lot) în formatul din preturi.py:
        {"intrare", "iesire", "citire_cache", "scriere_cache", "apeluri"}. Cheile
        lipsă sunt 0. `apeluri` lipsă: 1 dacă au fost tokeni, altfel 0.
        """
        u = usage or {}
        intrare, iesire = int(u.get("intrare") or 0), int(u.get("iesire") or 0)
        citire, scriere = int(u.get("citire_cache") or 0), int(u.get("scriere_cache") or 0)
        if apeluri is None:
            apeluri = int(u.get("apeluri") or (1 if intrare or iesire else 0))
        cost = preturi.cost(model, intrare, iesire, citire, scriere) if model else None
        with self._lacat:
            self.model = self.model or model
            for k, v in (("apeluri", apeluri), ("intrare", intrare), ("iesire", iesire),
                         ("citire_cache", citire), ("scriere_cache", scriere)):
                self._consum[k] += v
            if cost is not None:
                self._cost += cost
            elif intrare or iesire:
                # mai bine „cel puțin X $" decât o cifră care pare exactă
                self._cost_complet = False
                if model not in self._modele_fara_pret:
                    self._modele_fara_pret.add(model)
                    _spune(f"{model} nu e în preturi.py: costul jobului e o limită inferioară")
            de_scris = time.time() - self._ultima_scriere >= PAUZA_SCRIERE
        if de_scris:
            self._scrie_consum()

    def eroare(self, mesaj: str, context: str | None = None) -> None:
        """O eroare care nu oprește jobul: un produs, un URL, un candidat."""
        with self._lacat:
            self._erori += 1
        if self.id is None:
            return
        self._scrie("INSERT INTO jobs_error (id_job, eroare, context) VALUES (%s, %s, %s)",
                    (self.id, _taie(mesaj), _taie(context) if context else None))

    @property
    def cost(self) -> float:
        return self._cost

    # ── with ──────────────────────────────────────────────────────

    def __enter__(self) -> "Job":
        params = json.dumps(self.parametri, ensure_ascii=False, default=str) if self.parametri else None
        # coloana doar când e TRUE: pe o bază fără migrarea 037, jurnalul din terminal merge mai departe
        rand = (self._scrie("""
            INSERT INTO jobs (type, banca, model, parametri, runed_manually) VALUES (%s, %s, %s, %s, TRUE)
            RETURNING id""", (self.tip, self.banca, self.model, params)) if MANUAL else
                self._scrie("""
            INSERT INTO jobs (type, banca, model, parametri) VALUES (%s, %s, %s, %s)
            RETURNING id""", (self.tip, self.banca, self.model, params)))
        if rand:
            self.id = rand[0]
            self._ultima_scriere = time.time()
        return self

    def __exit__(self, tip_exc, exc, tb) -> bool:
        if tip_exc is None:
            stare = "cu_erori" if self._erori else "reusit"
        elif issubclass(tip_exc, KeyboardInterrupt):
            stare = "intrerupt"
            self.eroare("întrerupt de utilizator (Ctrl+C)")
        elif issubclass(tip_exc, SystemExit) and exc.code in (0, None):
            stare = "cu_erori" if self._erori else "reusit"
        else:
            stare = "esuat"
            if issubclass(tip_exc, SystemExit):
                # sys.exit("mesaj"): scripturile opresc așa o bancă restricționată sau un cod necunoscut
                self.eroare(str(exc.code), context="sys.exit")
            else:
                self.eroare("".join(traceback.format_exception(tip_exc, exc, tb)),
                            context=f"{tip_exc.__name__} (a oprit jobul)")
        self._scrie_consum(final=True, stare=stare)
        return False   # excepția merge mai departe: jurnalul nu schimbă cum se termină jobul


class FaraJurnal(Job):
    """
    Același API, fără bază. Pentru `--simulare` și `--din-json`: nu cheamă
    modelul și nu descarcă nimic, deci nu sunt joburi de jurnalizat, iar
    scripturile pot chema `job.consum()` / `job.eroare()` fără `if`.
    """

    def __init__(self):
        super().__init__("")
        self._activ = False

    def __enter__(self) -> "FaraJurnal":
        return self

    def __exit__(self, *_) -> bool:
        return False


__all__ = ["Job", "FaraJurnal"]
