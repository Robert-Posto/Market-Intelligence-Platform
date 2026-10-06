#!/usr/bin/env python3
"""
descopera_surse_libra.py — pentru fiecare produs din `produse_libra`, unde îl
găsim (sau echivalentul lui) la o bancă. Scrie în `surse_libra`.

    python descopera_surse_libra.py --banca bcr
    python descopera_surse_libra.py --banca bcr --prioritare          # doar cele 8
    python descopera_surse_libra.py --banca bcr --produse DEPOZIT_TERMEN,CONT_ECONOMII
    python descopera_surse_libra.py --banca bcr --simulare            # planul, fără cost
    python descopera_surse_libra.py --banca bcr --paralel 3 --forteaza

Bucla e cea din targetedCrawl.py (web_fetch de bază, citat verificat în
textul primit, reparațiile pentru `surse` trimis ca șir); aici diferă ce se
caută: nu „produsul X din catalogul v2", ci ECHIVALENTUL unui produs Libra.
La banca `libra` se caută chiar produsul.

Modelul primește doar codul, denumirea, segmentul și descrierea produsului
Libra — nu criteriile de eligibilitate sau „când să recomand" din catalog,
care sunt informații interne de vânzare.

Rezultate:
    surse_libra (Postgres, MIP_DSN)              upsert pe (banca, produs, url)
    inventare-libra/<banca>/<cod>.json           rularea completă, cu golurile
                                                 și potrivirea (echivalent/similar)

Un produs care are deja fișier e sărit (reluare gratuită), cu excepția --forteaza.

Termen: --timeout secunde pe produs (implicit 180, 0 = fără), numărate de când
produsul începe să ruleze, nu de când așteaptă în coadă. Un produs negăsit în
termen e socotit blocat: eroare în jobs_error, fără JSON, deci rerularea îl reia.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from urllib.parse import quote

import psycopg2

import preturi
import targetedCrawl as T
from jurnal_joburi import FaraJurnal, Job

AICI = Path(__file__).parent
IESIRE = AICI / "inventare-libra"
DSN = os.environ.get("MIP_DSN", "host=localhost port=5432 dbname=mip user=mip password=mip")
CUVINTE_MIN_CITAT = T.CUVINTE_MIN_CITAT
PRAG_INCREDERE = 0.6
_tipar = threading.Lock()


def spune(msg: str) -> None:
    with _tipar:
        print(msg, file=sys.stderr, flush=True)


# ── produsele și banca, din bază ──────────────────────────────────

def produse_libra(conn, coduri: list[str] | None, prioritare: bool) -> list[dict]:
    q = "SELECT id, cod, denumire, descriere, segment FROM produse_libra WHERE activ"
    args: list = []
    if prioritare:
        q += " AND prioritar"
    if coduri:
        q += " AND cod = ANY(%s)"
        args.append(coduri)
    with conn.cursor() as cur:
        cur.execute(q + " ORDER BY prioritar DESC, cod", args)
        rez = [dict(zip(("id", "cod", "denumire", "descriere", "segment"), r)) for r in cur.fetchall()]
    if coduri:
        lipsa = set(coduri) - {p["cod"] for p in rez}
        if lipsa:
            sys.exit(f"Coduri necunoscute sau inactive: {', '.join(sorted(lipsa))}")
    return rez


def id_banca(conn, slug: str) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT id, acces_restricted FROM banci WHERE slug = %s", (slug,))
        r = cur.fetchone()
    if not r:
        sys.exit(f"Banca {slug} nu e în tabela banci.")
    if r[1]:
        sys.exit(f"{slug} are acces_restricted = TRUE. Regula echipei: nu se accesează prin alt canal.")
    return r[0]


# ── prompt și unealtă ─────────────────────────────────────────────

SEGMENT = {"PF": "persoane fizice", "PJ": "persoane juridice (firme, PFA)", "PF+PJ": "persoane fizice și juridice"}


def sistem(p: dict, e_libra: bool) -> str:
    sarcina = (
        "Aceasta este chiar Libra Bank: găsește pe site pagina produsului și documentele cu datele lui."
        if e_libra else
        "Găsește la această bancă produsul ECHIVALENT (același tip de produs, același segment de "
        "clienți) sau, dacă nu există, cel mai apropiat SIMILAR. Banca îl numește, aproape sigur, "
        "altfel decât Libra — caută după ce este produsul, nu după nume."
    )
    return f"""Construiești o comparație între Libra Bank și concurență: pentru fiecare produs Libra, unde se găsesc datele produsului corespunzător la o altă bancă. Pe adresele raportate va rula zilnic un extractor de valori (dobânzi, comisioane, sume, termene).

PRODUSUL LIBRA
- cod: {p['cod']}
- denumire: {p['denumire']}
- pentru: {SEGMENT.get(p['segment'] or '', 'nespecificat')}
- descriere: {p['descriere'] or '— (doar denumirea; deduce din ea ce fel de produs este)'}

SARCINA
{sarcina}
Ignoră orice alt produs. Dacă o pagină acoperă mai multe produse, raportează doar partea despre produsul corespunzător.

CE CAUȚI, în ordinea valorii
1. Pagina dedicată produsului, dacă are cifre în text.
2. Lista sau grila de dobânzi care îl acoperă.
3. Documentul de tarife și comisioane (de obicei PDF, legat din footer: „Tarife și comisioane", „Documente utile"). Doar dacă produsul chiar apare în el.
4. Documentele de condiții: FIPC / fișa cu informații precontractuale, fișa produsului, regulamentul.
De obicei 1-4 surse. Nu raporta hub-uri, bloguri, știri sau campanii expirate.

NAVIGARE
- Pornești de la pagina principală. Deschizi doar adrese care apar ca linkuri în ce ai citit sau în rezultatele `web_search`.
- `web_search` e util pentru un salt direct. Ai puține căutări.
- Produsele pentru firme stau de obicei sub „Companii", „IMM", „Business", „Persoane juridice".
- Nu deschide internet banking, cariere, contact, cookies. O pagină care nu se încarcă poate fi blocată prin robots.txt: mergi mai departe.

POTRIVIREA — fii strict; un „nu are" corect e mai util decât o potrivire forțată
- `tip_potrivire = echivalent`: același tip de produs, același segment de clienți, termeni comparabili.
- `tip_potrivire = similar`: ACELAȘI tip de produs și ACELAȘI segment, dar diferă o caracteristică importantă (termen, garanție, monedă, canal). Scrie ce diferă în `motiv_potrivire`.
- NU e nici echivalent, nici similar, deci `surse` gol și `gol.motiv = produs_inexistent`:
  - alt tip de produs (transport de numerar nu e un seif la client; Open Banking nu e o integrare pentru contabili);
  - alt segment (un produs doar pentru persoane fizice nu acoperă unul pentru firme, și invers);
  - un produs GENERAL în locul unuia DEDICAT: dacă produsul Libra e făcut pentru o profesie, o industrie sau un program anume (medici, juriști, agricultură, dezvoltatori imobiliari, un garant anume ca BERD sau BID) și banca nu are o variantă dedicată, rezultatul e produs_inexistent — chiar dacă banca are un credit general pentru firme. Pomenește produsul general în `gol.nota`.
- Nu folosi același produs al băncii drept corespondent pentru produse Libra diferite doar fiindcă e cel mai apropiat.

CITATUL — partea cea mai importantă
`citat` e fragmentul pe care un om îl caută cu Ctrl+F în pagină ca să verifice. De aceea:
- se copiază LITERAL din conținutul primit, fără parafrazare, fără „...";
- 1-3 propoziții consecutive, minim {CUVINTE_MIN_CITAT} de cuvinte;
- numește produsul ȘI conține cifrele: procent, comision, sumă, termen;
- la un tabel, copiază rândul cu antetul lui, așa cum apare în text.

ÎNCREDEREA
`incredere` — cât de sigur ești că adresa conține date despre produsul corespunzător:
- 0.9+: pagină dedicată sau document cu cifrele produsului
- 0.7-0.85: document general (tarife, dobânzi) în care produsul apare explicit cu valori
- 0.5-0.7: produsul e menționat, dar cifrele sunt parțiale sau ambigue
- sub 0.5: nu raporta
`explicatie_incredere`: o propoziție concretă.

METODA — estimare, nu măsurătoare
Primești text extras, nu marcaj. `http` când cifrele apar în conținut, sau e PDF/XML (întotdeauna `http`). `playwright` când e clar pagina produsului dar nu conține nicio cifră, menționează un simulator care „se încarcă", sau cere JavaScript.

ALTE REGULI
- `tip` din ce ai primit efectiv, nu din extensia adresei.
- La `url` pui adresa exactă pe care ai deschis-o. Nu o reconstrui.

Ai maximum {T.MAX_PAGINI} deschideri de pagini. Încheie apelând `gata` o singură dată."""


GATA = {
    "name": "gata",
    "description": "Returnează sursele găsite. Se apelează o singură dată, la sfârșit.",
    "input_schema": {
        "type": "object",
        "properties": {
            "surse": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "tip": {"type": "string", "enum": ["html", "pdf", "xml"]},
                        "metoda": {"type": "string", "enum": ["http", "playwright"]},
                        "incredere_metoda": {"type": "number", "minimum": 0, "maximum": 1},
                        "dovada_metoda": {"type": "string"},
                        "rol": {"type": "string", "enum": ["pagina-produs", "tarife", "dobanzi", "conditii", "simulator"]},
                        "denumire_la_banca": {"type": "string", "description": "Numele comercial al produsului la această bancă."},
                        "tip_potrivire": {"type": "string", "enum": ["echivalent", "similar"]},
                        "motiv_potrivire": {"type": "string"},
                        "incredere": {"type": "number", "minimum": 0, "maximum": 1},
                        "explicatie_incredere": {"type": "string"},
                        "citat": {"type": "string", "description": f"Fragment LITERAL, 1-3 propoziții, minim {CUVINTE_MIN_CITAT} de cuvinte, cu cifre."},
                        "pagina_pdf": {"type": "integer", "description": "La PDF: pagina pe care e citatul, dacă o știi."},
                    },
                    "required": ["url", "tip", "metoda", "rol", "denumire_la_banca", "tip_potrivire",
                                 "motiv_potrivire", "incredere", "explicatie_incredere", "citat"],
                },
            },
            "gol": {
                "type": "object",
                "description": "Completează DOAR dacă `surse` e gol.",
                "properties": {
                    "motiv": {"type": "string", "enum": ["produs_inexistent", "nu_am_gasit", "nepublicat",
                                                         "necesita_alt_domeniu", "blocat_de_robots"],
                              "description": "nepublicat: produsul pare să existe, dar banca nu-l descrie public pe site."},
                    "nota": {"type": "string"},
                },
                "required": ["motiv", "nota"],
            },
        },
        "required": ["surse"],
    },
}


# ── linkul care derulează la paragraf ─────────────────────────────

def _fragment(s: str) -> str:
    # Text Fragments cer „-", „," și „&" codate; quote() lasă „-" necodat.
    return quote(s, safe="").replace("-", "%2D")


def link_live(url: str, citat: str) -> str:
    """url#:~:text=inceput,sfarsit — Chrome/Edge/Safari derulează și evidențiază."""
    cuv = citat.split()
    if len(cuv) <= 8:
        frag = _fragment(" ".join(cuv))
    else:
        frag = _fragment(" ".join(cuv[:5])) + "," + _fragment(" ".join(cuv[-5:]))
    return url.split("#")[0] + "#:~:text=" + frag


# ── un produs ─────────────────────────────────────────────────────

def un_produs(banca: dict, idb: int, p: dict, timeout_s: float = 0) -> dict:
    e_libra = banca["id"] == "libra"
    produs = {"id": p["cod"], "nume": p["denumire"]}
    cerere = (f"Găsește sursele pentru produsul Libra „{p['denumire']}” ({p['cod']})"
              + ("" if e_libra else " sau echivalentul lui la această bancă") + ", apoi apelează `gata`.")
    start = time.time()
    # un singur termen pe produs: reîncercările și reluarea „fără motiv” intră tot în el
    termen = start + timeout_s if timeout_s else None

    def o_rulare(cer: str) -> dict:
        # La 9 cereri simultane au căzut 7 conexiuni (WinError 10054), iar PLASAMENTE
        # a picat de două ori la rând, la 15 s distanță. Trei încercări, pauză crescătoare.
        for tentativa in (1, 2, 3):
            try:
                return T.ruleaza(banca, produs, prompt_sistem=sistem(p, e_libra), gata=GATA, cerere=cer,
                                 termen=termen)
            except Exception as e:  # conexiune închisă, 529, 5xx
                spune(f"  ! {p['cod']}: {type(e).__name__}: {e} (tentativa {tentativa})")
                pauza = 20 * tentativa ** 2
                if tentativa == 3 or (termen and time.time() + pauza >= termen):
                    return {"surse": [], "_deschise": [], "_texte": {}, "_usage": {},
                            "_eroare": f"{type(e).__name__}: {e}"}
                time.sleep(pauza)

    rez = o_rulare(cerere)
    gol_fara_motiv = lambda r: (not r.get("surse") and not (r.get("gol") or {}).get("motiv")
                                and "_eroare" not in r)
    if gol_fara_motiv(rez):
        # Raiffeisen DEPOZIT_TERMEN, BRD ACREDITIVE, BCR CREDIT_IPOTECAR_PF: `gata` fără
        # surse și fără motiv. Brutul se păstrează pentru diagnostic, apoi o singură
        # reluare cu instrucțiunea explicită; costul primei rulări se adună.
        dosar_err = IESIRE / banca["id"] / "_erori"
        dosar_err.mkdir(parents=True, exist_ok=True)
        (dosar_err / f"{p['cod']}-{int(time.time())}.json").write_text(json.dumps(
            {"brut": rez.get("_brut"), "deschise": rez.get("_deschise")}, ensure_ascii=False, indent=1,
            default=str), encoding="utf-8")
        spune(f"  ! {p['cod']}: gata fără surse și fără motiv — reiau o dată")
        u1 = rez.get("_usage") or {}
        rez = o_rulare(cerere + " Dacă nu găsești nicio sursă potrivită, trimite `surse` gol ȘI completează "
                                "`gol` cu motivul și ce ai verificat. Un `gata` fără surse și fără `gol` nu e valid.")
        for k, v in u1.items():
            if isinstance(v, (int, float)):
                rez.setdefault("_usage", {})[k] = rez["_usage"].get(k, 0) + v

    surse = T.deduplica(rez.get("surse") or [])
    T.verifica(surse, rez["_deschise"], rez["_texte"])
    for s in surse:
        s["link_live"] = (link_live(s["url"], s["citat"])
                          if s.get("citat_verificat") and s["tip"] == "html" else None)
    surse.sort(key=lambda s: -s.get("incredere", 0))

    # Prag: la BCR, potrivirile sub 0,6 erau forțate (credit general pentru
    # medici, transport de numerar pentru un seif). Sub prag, produsul e
    # not_found; candidatul rămâne în JSON, pentru verificare.
    candidati_respinsi = []
    if surse and surse[0].get("incredere", 0) < PRAG_INCREDERE:
        candidati_respinsi, surse = surse, []
        c = candidati_respinsi[0]
        rez["gol"] = {"motiv": "potrivire_slaba",
                      "nota": f"cel mai apropiat: {c.get('denumire_la_banca', '?')} "
                              f"(încredere {c.get('incredere')}) — {c.get('motiv_potrivire', '')}"}

    u = rez.get("_usage") or {}
    cost = preturi.cost(T.MODEL, u.get("intrare", 0), u.get("iesire", 0),
                        u.get("citire_cache", 0), u.get("scriere_cache", 0))
    iesire = {
        "generat": str(date.today()), "banca": banca["id"], "cod": p["cod"],
        "denumire": p["denumire"], "model": T.MODEL, "surse": surse,
        "gol": rez.get("gol") if not surse else None,
        "candidati_respinsi": candidati_respinsi,
        "deschise": rez["_deschise"], "durata_s": round(time.time() - start),
        "consum": {**u, "cost_estimat_usd": cost},
    }
    if "_eroare" in rez:
        iesire["eroare"] = rez["_eroare"]
    elif not surse and not iesire["gol"]:
        # La BCR, CREDIT_IPOTECAR_PF s-a încheiat după 2 căutări, fără nicio
        # pagină deschisă, fără surse și fără motiv. Un gol fără motiv nu e un
        # rezultat: nu se salvează, ca rerularea să-l reia.
        iesire["eroare"] = "încheiat fără surse și fără motiv de gol"

    dosar = IESIRE / banca["id"]
    dosar.mkdir(parents=True, exist_ok=True)
    if "eroare" not in iesire:
        (dosar / f"{p['cod']}.json").write_text(json.dumps(iesire, ensure_ascii=False, indent=2), encoding="utf-8")
        scrie_db(idb, p["id"], surse, iesire["gol"])
    return iesire


def scrie_db(idb: int, id_produs: int, surse: list[dict], gol: dict | None = None) -> None:
    """
    Găsit: upsert pe (bancă, produs, url) și se scoate un eventual rând
    not_found rămas de la o rulare anterioară. Negăsit (gol cu motiv): un
    singur rând not_found = TRUE, cu motivul în explicatie_incredere.
    """
    with psycopg2.connect(DSN) as conn, conn.cursor() as cur:
        if not surse and not (gol and gol.get("motiv")):
            return   # rulare eșuată: nu atingem ce exista
        # Rularea nouă înlocuiește propunerile vechi ale perechii; altfel URL-urile
        # pe care modelul nu le mai propune ar rămâne în tabelă. Nu se ating rândurile
        # verificate de un om (stare <> propus) sau folosite deja în comparatie_libra.
        cur.execute("""
            DELETE FROM surse_libra s
             WHERE s.id_banca = %s AND s.id_produs_libra = %s AND s.stare = 'propus'
               AND NOT EXISTS (SELECT 1 FROM comparatie_libra c WHERE c.id_sursa = s.id)
            """, (idb, id_produs))
        if not surse:
            cur.execute("""
                INSERT INTO surse_libra (id_banca, id_produs_libra, not_found, explicatie_incredere, model)
                VALUES (%s, %s, TRUE, %s, %s)
                ON CONFLICT (id_banca, id_produs_libra) WHERE not_found DO UPDATE SET
                    explicatie_incredere = EXCLUDED.explicatie_incredere, model = EXCLUDED.model
                """, (idb, id_produs, f"[{gol['motiv']}] {gol.get('nota') or ''}".strip(), T.MODEL))
            return
        cur.execute("DELETE FROM surse_libra WHERE id_banca = %s AND id_produs_libra = %s AND not_found",
                    (idb, id_produs))
        for s in surse:
            cur.execute("""
                INSERT INTO surse_libra (id_banca, id_produs_libra, url, tip, rol, metoda, pagina_pdf,
                    denumire_la_banca, citat, citat_verificat, link_live, incredere,
                    explicatie_incredere, model)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT ON CONSTRAINT ux_surse_libra DO UPDATE SET
                    tip = EXCLUDED.tip, rol = EXCLUDED.rol, metoda = EXCLUDED.metoda,
                    pagina_pdf = EXCLUDED.pagina_pdf, denumire_la_banca = EXCLUDED.denumire_la_banca,
                    citat = EXCLUDED.citat, citat_verificat = EXCLUDED.citat_verificat,
                    link_live = EXCLUDED.link_live, incredere = EXCLUDED.incredere,
                    explicatie_incredere = EXCLUDED.explicatie_incredere, model = EXCLUDED.model
                """, (idb, id_produs, s["url"], s["tip"], s["rol"], s.get("metoda"), s.get("pagina_pdf"),
                      s.get("denumire_la_banca"), s["citat"], s.get("citat_verificat"), s.get("link_live"),
                      round(float(s["incredere"]), 2),
                      f"[{s.get('tip_potrivire', '?')}] {s.get('explicatie_incredere', '')}"
                      + (f" — {s['motiv_potrivire']}" if s.get("motiv_potrivire") else ""),
                      T.MODEL))


# ── main ──────────────────────────────────────────────────────────

def main() -> None:
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass

    a = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    a.add_argument("--banca", required=True)
    a.add_argument("--produse", help="coduri separate prin virgulă")
    a.add_argument("--prioritare", action="store_true")
    a.add_argument("--paralel", type=int, default=3)
    a.add_argument("--forteaza", action="store_true")
    a.add_argument("--timeout", type=float, default=180,
                   help="secunde pe produs (implicit 180); după ele produsul e eroare de timeout. 0 = fără termen")
    a.add_argument("--simulare", action="store_true")
    a.add_argument("--din-json", action="store_true",
                   help="rescrie surse_libra din inventare-libra/<banca>/*.json, fără apeluri la API")
    arg = a.parse_args()

    # jurnalul (jobs / jobs_error) doar pentru rularea reală: simularea și
    # rescrierea din JSON nu cheamă modelul
    jurnal = (FaraJurnal() if arg.simulare or arg.din_json
              else Job("discovery", banca=arg.banca, model=T.MODEL, parametri=vars(arg)))
    with jurnal as job:
        ruleaza(arg, job)


def ruleaza(arg, job: Job) -> None:
    banca = T.incarca_banca(arg.banca)
    with psycopg2.connect(DSN) as conn:
        idb = id_banca(conn, arg.banca)
        produse = produse_libra(conn, arg.produse.split(",") if arg.produse else None, arg.prioritare)

    dosar = IESIRE / banca["id"]
    if arg.din_json:
        gasite = negasite = 0
        for p in produse:
            f = dosar / f"{p['cod']}.json"
            if not f.exists():
                continue
            d = json.loads(f.read_text(encoding="utf-8"))
            scrie_db(idb, p["id"], d["surse"], d.get("gol"))
            gasite += bool(d["surse"])
            negasite += bool(not d["surse"] and (d.get("gol") or {}).get("motiv"))
        spune(f"{banca['id']}: din JSON — {gasite} produse găsite, {negasite} not_found")
        return
    de_rulat = [p for p in produse if arg.forteaza or not (dosar / f"{p['cod']}.json").exists()]
    spune(f"{banca['nume']}: {len(de_rulat)} de rulat, {len(produse) - len(de_rulat)} sărite "
          f"(au rezultat), paralel {arg.paralel}, model {T.MODEL}, "
          f"termen {f'{arg.timeout:g} s/produs' if arg.timeout else 'fără'}, domenii {', '.join(T.domenii_permise(banca))}")
    if arg.simulare:
        for p in de_rulat:
            spune(f"  [simulare] {p['cod']:28} {p['segment'] or '':6} {p['denumire']}")
        return

    total, gasite, erori, start = 0.0, 0, [], time.time()
    with ThreadPoolExecutor(max_workers=arg.paralel) as ex:
        viitoare = {ex.submit(un_produs, banca, idb, p, arg.timeout): p for p in de_rulat}
        for f in as_completed(viitoare):
            p = viitoare[f]
            try:
                r = f.result()
            except Exception as e:
                erori.append(p["cod"])
                spune(f"EROARE  {p['cod']:28} {type(e).__name__}: {e}")
                job.eroare("".join(traceback.format_exception(e)), context=p["cod"])
                continue
            c = r["consum"].get("cost_estimat_usd") or 0
            total += c
            job.consum(T.MODEL, r["consum"])
            if r.get("eroare"):
                erori.append(p["cod"])
                spune(f"EROARE  {p['cod']:28} {r['eroare'][:120]}")
                job.eroare(r["eroare"], context=p["cod"])
            elif r["surse"]:
                gasite += 1
                ver = sum(1 for s in r["surse"] if s.get("citat_verificat"))
                pot = r["surse"][0].get("tip_potrivire", "?")
                spune(f"GATA    {p['cod']:28} {len(r['surse'])} surse, {ver} citate verificate, "
                      f"{pot}, ${c:.2f}, {r['durata_s']}s — {r['surse'][0].get('denumire_la_banca', '')}")
            else:
                g = r.get("gol") or {}
                spune(f"GOL     {p['cod']:28} {g.get('motiv', '?')}: {(g.get('nota') or '')[:90]}, ${c:.2f}")

    job.rezumat = f"{gasite}/{len(de_rulat)} produse cu surse, {len(erori)} erori"
    spune(f"\n{banca['id']}: {gasite}/{len(de_rulat)} produse cu surse, {len(erori)} erori, "
          f"cost estimat ${total:.2f}, durata {round((time.time() - start) / 60)} min")
    if erori:
        spune(f"Reia: python descopera_surse_libra.py --banca {banca['id']} --produse {','.join(erori)}")


if __name__ == "__main__":
    main()
