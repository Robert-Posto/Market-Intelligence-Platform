#!/usr/bin/env python3
"""
compara_fluxuri.py — fluxul vechi (copia din 12.10.2026) față de fluxul nou, pe aceleași produse.

    python compara_fluxuri.py --produse CARD_DEBIT_FREE,CONT_ONLINE_PERSONAL
    python compara_fluxuri.py --produse CARD_DEBIT_FREE --banci bcr,brd,ing --de-la 2026-10-12

Întâi reface valorile de referință ale ambelor baze (consolideaza_referinta.py, aceleași reguli),
apoi le compară pe perechile bancă × produs ale produselor alese:

  discovery   câte surse pe pereche și ce fel (lista de tarife, pagina produsului ...)
  extragere   câte valori brute și câte distincte; câte pe câmpuri cheie
  referință   câte câmpuri cheie au o cifră comparabilă, câte conflicte, câte doar variante
  acord       pe câmpurile cu cifră în ambele: aceeași cifră sau alta (cu lista diferențelor)
  cost        joburile de discovery și extragere din `jobs`, de la --de-la încoace (fluxul nou)

Scrie și un raport JSON în date/comparatie_fluxuri_<data>.json, pentru pagina de analiză.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import psycopg2
import psycopg2.extras

AICI = Path(__file__).parent
DSN = os.environ.get("MIP_DSN", "host=localhost port=5432 dbname=mip user=mip password=mip")
BAZE = {"v1": ("comparatie_libra_v1", "surse_libra_v1"), "curent": ("comparatie_libra", "surse_libra")}


def masoara(cur, baza: str, produse: list[str], banci: list[str] | None) -> dict:
    comp, surse = BAZE[baza]
    fb = " AND b.slug = ANY(%(banci)s)" if banci else ""
    p = {"produse": produse, "banci": banci, "baza": baza}
    cur.execute(f"""SELECT count(*) FILTER (WHERE NOT s.not_found) AS surse,
                           count(DISTINCT (s.id_banca, s.id_produs_libra)) FILTER (WHERE NOT s.not_found) AS perechi,
                           count(DISTINCT (s.id_banca, s.id_produs_libra)) FILTER (WHERE s.not_found) AS negasite,
                           count(*) FILTER (WHERE NOT s.not_found AND s.rol = 'tarife') AS din_tarife,
                           count(*) FILTER (WHERE NOT s.not_found AND s.rol = 'pagina-produs') AS din_pagina
                      FROM {surse} s JOIN banci b ON b.id = s.id_banca JOIN produse_libra pl ON pl.id = s.id_produs_libra
                     WHERE pl.cod = ANY(%(produse)s){fb}""", p)
    d = dict(cur.fetchone())
    cur.execute(f"""SELECT count(*) FILTER (WHERE NOT c.ambiguu) AS valori,
                           count(*) FILTER (WHERE c.ambiguu) AS ambigue,
                           count(DISTINCT (c.id_banca, c.id_produs_libra, c.camp, c.valoare_num, c.unitate))
                             FILTER (WHERE NOT c.ambiguu) AS distincte,
                           count(*) FILTER (WHERE c.camp = 'altele') AS altele
                      FROM {comp} c JOIN banci b ON b.id = c.id_banca JOIN produse_libra pl ON pl.id = c.id_produs_libra
                     WHERE pl.cod = ANY(%(produse)s){fb}""", p)
    d.update(cur.fetchone())
    cur.execute(f"""SELECT v.stare, count(*) AS n, sum(v.n_brut) AS brute
                      FROM valori_referinta v JOIN banci b ON b.id = v.id_banca JOIN produse_libra pl ON pl.id = v.id_produs_libra
                     WHERE v.baza = %(baza)s AND pl.cod = ANY(%(produse)s){fb} GROUP BY 1""", p)
    stari = {r["stare"]: r["n"] for r in cur.fetchall()}
    d["stari"] = stari
    d["campuri_cheie"] = sum(stari.values())
    d["cu_cifra"] = sum(stari.get(s, 0) for s in ("referinta", "aproximativ", "conflict"))
    d["acoperire_pct"] = round(100 * d["cu_cifra"] / d["campuri_cheie"], 1) if d["campuri_cheie"] else 0
    d["surse_pe_pereche"] = round(d["surse"] / d["perechi"], 2) if d["perechi"] else 0
    return d


def diferente(cur, produse: list[str], banci: list[str] | None) -> list[dict]:
    fb = " AND b.slug = ANY(%(banci)s)" if banci else ""
    cur.execute(f"""SELECT b.slug AS banca, pl.cod AS produs, n.camp_cheie,
                           o.valoare_num::float8 AS vechi, o.unitate AS u_vechi, o.stare AS stare_vechi,
                           n.valoare_num::float8 AS nou, n.unitate AS u_nou, n.stare AS stare_nou
                      FROM valori_referinta n
                      JOIN valori_referinta o ON o.baza = 'v1' AND o.id_banca = n.id_banca
                       AND o.id_produs_libra = n.id_produs_libra AND o.camp_cheie = n.camp_cheie
                      JOIN banci b ON b.id = n.id_banca JOIN produse_libra pl ON pl.id = n.id_produs_libra
                     WHERE n.baza = 'curent' AND pl.cod = ANY(%(produse)s){fb}
                     ORDER BY 2, 1, 3""", {"produse": produse, "banci": banci})
    return [dict(r) for r in cur.fetchall()]


def cost(cur, de_la: str | None, banci: list[str] | None) -> dict:
    if not de_la:
        return {}
    fb = " AND banca = ANY(%(banci)s)" if banci else ""
    cur.execute(f"""SELECT type, count(*) AS joburi, round(sum(cost_usd)::numeric, 2)::float8 AS cost_usd,
                           sum(tokeni_intrare) AS tokeni_intrare, sum(tokeni_iesire) AS tokeni_iesire
                      FROM jobs WHERE started_at >= %(de_la)s AND type IN ('discovery', 'extragere'){fb}
                     GROUP BY 1""", {"de_la": de_la, "banci": banci})
    return {r["type"]: dict(r) for r in cur.fetchall()}


def main() -> int:
    for f in (sys.stdout, sys.stderr):
        f.reconfigure(encoding="utf-8")
    a = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    a.add_argument("--produse", required=True, help="coduri Libra separate prin virgulă")
    a.add_argument("--banci", help="slug-uri separate prin virgulă (implicit toate)")
    a.add_argument("--de-la", help="AAAA-LL-ZZ: costul joburilor fluxului nou de la data asta")
    arg = a.parse_args()
    produse = arg.produse.split(",")
    banci = arg.banci.split(",") if arg.banci else None

    for baza in BAZE:
        subprocess.run([sys.executable, str(AICI / "consolideaza_referinta.py"), "--baza", baza,
                        "--produse", arg.produse], check=True, capture_output=True)
    with psycopg2.connect(DSN) as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        m = {b: masoara(cur, b, produse, banci) for b in BAZE}
        dif = diferente(cur, produse, banci)
        c = cost(cur, arg.de_la, banci)

    randuri = [("perechi găsite la discovery", "perechi"), ("produs inexistent (perechi)", "negasite"),
               ("surse", "surse"), ("surse pe pereche", "surse_pe_pereche"), ("din lista de tarife", "din_tarife"),
               ("din pagina produsului", "din_pagina"), ("valori brute neambigue", "valori"), ("valori ambigue", "ambigue"),
               ("valori distincte", "distincte"), ("în câmpul „altele”", "altele"), ("câmpuri cheie", "campuri_cheie"),
               ("cu cifră comparabilă", "cu_cifra"), ("acoperire %", "acoperire_pct")]
    print(f"\n{'':32}{'vechi':>10}{'nou':>10}")
    for et, k in randuri:
        print(f"{et:32}{m['v1'][k]:>10}{m['curent'][k]:>10}")
    for s in ("referinta", "aproximativ", "conflict", "doar_variante", "lipsa"):
        print(f"  {s:30}{m['v1']['stari'].get(s, 0):>10}{m['curent']['stari'].get(s, 0):>10}")

    ambele = [x for x in dif if x["vechi"] is not None and x["nou"] is not None]
    acelasi = [x for x in ambele if x["vechi"] == x["nou"] and x["u_vechi"] == x["u_nou"]]
    doar_nou = [x for x in dif if x["vechi"] is None and x["nou"] is not None]
    doar_vechi = [x for x in dif if x["vechi"] is not None and x["nou"] is None]
    print(f"\nacord: {len(acelasi)}/{len(ambele)} câmpuri cu aceeași cifră; {len(doar_nou)} câștigate de fluxul nou, "
          f"{len(doar_vechi)} pierdute")
    for x in [x for x in ambele if x not in acelasi][:25]:
        print(f"  {x['banca']:18} {x['produs']:24} {x['camp_cheie']:24} {x['vechi']:g} {x['u_vechi']} ({x['stare_vechi']}) "
              f"-> {x['nou']:g} {x['u_nou']} ({x['stare_nou']})")
    if c:
        print("\ncost fluxul nou:", ", ".join(f"{t}: {v['joburi']} joburi, ${v['cost_usd']}" for t, v in c.items()))

    iesire = AICI.parent / "date" / f"comparatie_fluxuri_{date.today():%Y%m%d}.json"
    iesire.write_text(json.dumps({"produse": produse, "banci": banci, "de_la": arg.de_la, "masuratori": m,
                                  "acord": {"ambele": len(ambele), "acelasi": len(acelasi), "doar_nou": len(doar_nou),
                                            "doar_vechi": len(doar_vechi)},
                                  "diferente": dif, "cost": c}, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(f"\nraport: {iesire}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
