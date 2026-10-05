#!/usr/bin/env python3
"""
descopera_produse.py — produsele concurenței pe care Libra nu le are în catalog.

    python descopera_produse.py --banca bcr --simulare            # doar candidații: fără model, fără bază
    python descopera_produse.py --banca bcr,ing --limita 60       # pilot: primii 60 de candidați pe bancă
    python descopera_produse.py --banca bcr                       # tot
    python descopera_produse.py --banca bcr --din-json            # rescrie baza din JSON, fără rețea și model

Pașii (vezi rezumatul fluxului):
  1–2  candidati_produse.py  sitemap + meniuri -> pagini de produs, filtrate prin reguli
  3–5  clasifica_produse.py  începutul paginii -> model -> citat verificat -> echivalent Libra?
  6    aici                  „nou” -> products_discovery; restul doar în JSON

Rulat pe Libra, același flux găsește produsele de pe librabank.ro care nu sunt
printre cele 57 („Libra îl are, dar nu e în catalog”).

Rezultate:
  products_discovery (Postgres, MIP_DSN)              produsele fără echivalent
  inventare-produse/candidati-<banca>.json            --simulare: candidații
  inventare-produse/produse-<banca>.json              tot: noi, echivalente, de verificat, respinse
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

AICI = Path(__file__).parent
sys.path.insert(0, str(AICI))

import psycopg2                                         # noqa: E402
from dotenv import load_dotenv                          # noqa: E402

load_dotenv(AICI / ".env")

import preturi                                          # noqa: E402
from candidati_produse import Blocat, candidati         # noqa: E402
from clasifica_produse import MODEL, clasifica          # noqa: E402

DSN = os.environ.get("MIP_DSN", "host=localhost port=5432 dbname=mip user=mip password=mip")
IESIRE = AICI / "inventare-produse"


def spune(m: str) -> None:
    print(m, file=sys.stderr, flush=True)


def banca_db(slug: str) -> int:
    with psycopg2.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("SELECT id, acces_restricted FROM banci WHERE slug = %s", (slug,))
        rand = cur.fetchone()
    if not rand:
        sys.exit(f"{slug}: nu e în tabela banci")
    if rand[1]:
        sys.exit(f"{slug} are acces_restricted = TRUE: nu se accesează.")
    return rand[0]


def catalog_libra() -> list[dict]:
    # fără `descriere`: conține prețurile Libra, care nu intră în prompturile despre concurență
    with psycopg2.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("SELECT cod, denumire, segment, categorie_cod FROM produse_libra WHERE activ ORDER BY cod")
        return [dict(zip(("cod", "denumire", "segment", "categorie_cod"), r)) for r in cur.fetchall()]


def scrie_db(idb: int, noi: list[dict]) -> int:
    """Produsele noi intră; cele deja văzute își actualizează numele, descrierea și vazut_la."""
    with psycopg2.connect(DSN) as conn, conn.cursor() as cur:
        n = 0
        for p in noi:
            cur.execute("""
                INSERT INTO products_discovery (id_banca, denumire_produs, descriere_produs, link, segment, categorie)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT ON CONSTRAINT ux_products_discovery DO UPDATE SET
                    denumire_produs = EXCLUDED.denumire_produs,
                    descriere_produs = COALESCE(EXCLUDED.descriere_produs, products_discovery.descriere_produs),
                    segment = EXCLUDED.segment, categorie = EXCLUDED.categorie,
                    vazut_la = now()                -- created_at rămâne: așa știm ce e „nou”
                """, (idb, p["denumire_produs"], p.get("descriere_produs"), p["url"], p.get("segment"), p.get("categorie")))
            n += cur.rowcount
    return n


async def o_banca(slug: str, arg) -> None:
    idb = banca_db(slug)
    IESIRE.mkdir(exist_ok=True)
    cale = IESIRE / f"produse-{slug}.json"

    if arg.din_json:
        noi = json.loads(cale.read_text(encoding="utf-8"))["nou"]
        spune(f"{slug}: din JSON — {scrie_db(idb, noi)} rânduri în products_discovery")
        return

    start = time.time()
    c = await candidati(slug)
    if c.get("blocat"):
        spune(f"{slug}: BLOCAT — {c['blocat']}. Se documentează ca blocat, nu se ocolește.")
        return
    lista = c["candidati"]
    spune(f"{slug}: {c['statistica']['adrese_brute']} adrese, {len(lista)} candidați; "
          f"scoase: {c['statistica']['scoase']}")
    if arg.simulare:
        (IESIRE / f"candidati-{slug}.json").write_text(json.dumps(
            {"banca": slug, "generat": str(date.today()), **c}, ensure_ascii=False, indent=1), encoding="utf-8")
        for x in lista[:arg.arata]:
            spune(f"  [{x['din']:7}] {x['url']}  {x['titlu'][:60]}")
        if len(lista) > arg.arata:
            spune(f"  ... încă {len(lista) - arg.arata} (toți în inventare-produse/candidati-{slug}.json)")
        return

    if arg.limita:
        # pe rând din fiecare secțiune, nu primii N alfabetic: la pilotul BCR, primii 60
        # erau toți din /business și /asigurari, iar conturile, investițiile și cardurile
        # (0 din 98) n-au fost văzute deloc
        pe_sectiune: dict[str, list] = {}
        for x in lista:
            pe_sectiune.setdefault("/".join(x["url"].split("/")[3:6]), []).append(x)
        grupe, lista = list(pe_sectiune.values()), []
        while len(lista) < arg.limita and any(grupe):
            for g in grupe:
                if g and len(lista) < arg.limita:
                    lista.append(g.pop(0))
    from anthropic import AsyncAnthropic
    ai = AsyncAnthropic()
    catalog = catalog_libra()
    coduri = {p["cod"] for p in catalog}
    sem = asyncio.Semaphore(arg.paralel)
    blocaj: list[str] = []

    async def unul(x):
        async with sem:
            if blocaj:
                return {**x, "rezultat": "nerulat", "motiv": "banca s-a blocat între timp"}
            try:
                return await clasifica(ai, x, catalog, coduri)
            except Blocat as e:
                blocaj.append(str(e))
                return {**x, "rezultat": "nerulat", "motiv": f"blocat: {e}"}
            except Exception as e:
                return {**x, "rezultat": "respins", "motiv": f"{type(e).__name__}: {e}"}

    rez = await asyncio.gather(*(unul(x) for x in lista))
    # același produs pe două adrese ale băncii (la Raiffeisen, „Welcome Home” avea două pagini):
    # rămâne cea cu adresa mai scurtă, celelalte trec la `dubluri`
    vazute: dict[str, dict] = {}
    for r in sorted((r for r in rez if r["rezultat"] == "nou"), key=lambda r: len(r["url"])):
        k = " ".join((r.get("denumire_produs") or "").lower().split())
        if k in vazute:
            r["rezultat"], r["motiv"] = "dublura", f"același produs ca {vazute[k]['url']}"
        else:
            vazute[k] = r
    pe = {k: [r for r in rez if r["rezultat"] == k]
          for k in ("nou", "echivalent", "de_verificat", "respins", "nerulat", "dublura")}
    tok = Counter()
    for r in rez:
        tok.update(r.get("tokeni") or {})
    cost = preturi.cost(MODEL, tok["intrare"], tok["iesire"], tok["citire_cache"], tok["scriere_cache"]) or 0
    cale.write_text(json.dumps({
        "banca": slug, "generat": str(date.today()), "model": MODEL, "statistica": c["statistica"],
        "limita": arg.limita, "blocat": blocaj[0] if blocaj else None,
        "cost_estimat_usd": round(cost, 4), "tokeni": dict(tok),
        **pe}, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    scrise = scrie_db(idb, pe["nou"]) if not arg.fara_db else 0
    spune(f"{slug}: {len(pe['nou'])} noi, {len(pe['echivalent'])} cu echivalent Libra, "
          f"{len(pe['de_verificat'])} de verificat, {len(pe['respins'])} respinse"
          + (f", {len(pe['nerulat'])} nerulate (BLOCAT: {blocaj[0]})" if blocaj else "")
          + f"; {scrise} rânduri în products_discovery; ${cost:.2f}; {round(time.time() - start)}s")


async def main() -> None:
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass
    a = argparse.ArgumentParser(description="Produsele concurenței fără echivalent în catalogul Libra.")
    a.add_argument("--banca", required=True, help="una sau mai multe, separate prin virgulă")
    a.add_argument("--simulare", action="store_true", help="doar candidații: fără model, fără bază")
    a.add_argument("--limita", type=int, help="clasifică doar primii N candidați pe bancă (pilot)")
    a.add_argument("--paralel", type=int, default=3)
    a.add_argument("--arata", type=int, default=40, help="la --simulare: câți candidați se afișează")
    a.add_argument("--din-json", action="store_true", help="rescrie products_discovery din produse-<banca>.json")
    a.add_argument("--fara-db", action="store_true", help="clasifică și scrie JSON, dar nu în bază")
    arg = a.parse_args()
    for slug in [s.strip() for s in arg.banca.split(",") if s.strip()]:
        await o_banca(slug, arg)


if __name__ == "__main__":
    asyncio.run(main())
