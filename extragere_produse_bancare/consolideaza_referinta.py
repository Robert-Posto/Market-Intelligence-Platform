#!/usr/bin/env python3
"""
consolideaza_referinta.py — valorile de referință, din comparatie_libra în valori_referinta.

    python consolideaza_referinta.py                    # toate băncile, din comparatie_libra (baza „curent”)
    python consolideaza_referinta.py --baza v1          # din copia fluxului vechi (comparatie_libra_v1)
    python consolideaza_referinta.py --banca bcr --produse CARD_DEBIT_FREE,CONT_ONLINE_PERSONAL
    python consolideaza_referinta.py --simulare         # bilanțul, fără scriere

Fără model și fără descărcări: doar regulile din referinta.py peste ce s-a extras deja, deci se
poate rula oricând (după o extragere, după o schimbare în fise_produse.json). Rândurile bazei
rulate se înlocuiesc; ce nu e în filtru rămâne.

Intră perechile bancă × produs pe care discovery le-a găsit (surse_libra fără not_found): o
pereche fără nicio valoare la un câmp apare cu starea `lipsa`, ca acoperirea să se vadă.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import psycopg2
import psycopg2.extras

AICI = Path(__file__).parent
sys.path.insert(0, str(AICI))
from referinta import Fise, alege   # noqa: E402

DSN = os.environ.get("MIP_DSN", "host=localhost port=5432 dbname=mip user=mip password=mip")
TABELE = {"curent": ("comparatie_libra", "surse_libra"), "v1": ("comparatie_libra_v1", "surse_libra_v1")}


def citeste(cur, baza: str, banca: str | None, produse: list[str] | None) -> tuple[list[tuple], dict]:
    """Perechile găsite la discovery și rândurile lor, grupate pe (id_banca, id_produs_libra)."""
    comp, surse = TABELE[baza]
    filtru, p = "", []
    if banca:
        filtru += " AND b.slug = %s"
        p.append(banca)
    if produse:
        filtru += " AND pl.cod = ANY(%s)"
        p.append(produse)
    cur.execute(f"""SELECT DISTINCT s.id_banca, s.id_produs_libra, b.slug, pl.cod
                      FROM {surse} s JOIN banci b ON b.id = s.id_banca
                      JOIN produse_libra pl ON pl.id = s.id_produs_libra AND pl.activ
                     WHERE NOT s.not_found{filtru}""", p)
    perechi = cur.fetchall()
    cur.execute(f"""SELECT c.id, c.id_banca, c.id_produs_libra, c.id_sursa, c.camp, c.valoare_num, c.unitate,
                           c.moneda, c.conditie, c.citat, c.link_live, c.incredere, c.ambiguu, c.scenariu,
                           s.rol, s.url
                      FROM {comp} c JOIN {surse} s ON s.id = c.id_sursa
                      JOIN banci b ON b.id = c.id_banca JOIN produse_libra pl ON pl.id = c.id_produs_libra
                     WHERE TRUE{filtru}""", p)
    pe = defaultdict(list)
    for r in cur.fetchall():
        pe[(r["id_banca"], r["id_produs_libra"])].append(dict(r))
    return perechi, pe


def main() -> int:
    for f in (sys.stdout, sys.stderr):
        f.reconfigure(encoding="utf-8")
    a = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    a.add_argument("--baza", choices=sorted(TABELE), default="curent")
    a.add_argument("--banca")
    a.add_argument("--produse", help="coduri Libra separate prin virgulă")
    a.add_argument("--simulare", action="store_true")
    arg = a.parse_args()
    produse = arg.produse.split(",") if arg.produse else None
    fise = Fise()

    with psycopg2.connect(DSN) as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        perechi, pe = citeste(cur, arg.baza, arg.banca, produse)
        rezultate = []
        for p in perechi:
            for k in fise.campuri_cheie(p["cod"]):
                r = alege(fise, p["cod"], k, pe.get((p["id_banca"], p["id_produs_libra"]), []))
                rezultate.append({**r, "id_banca": p["id_banca"], "id_produs_libra": p["id_produs_libra"]})
        stari = Counter(r["stare"] for r in rezultate)
        brute = sum(r["n_brut"] for r in rezultate)
        print(f"baza {arg.baza}: {len(perechi)} perechi bancă × produs, {len(rezultate)} câmpuri cheie; "
              f"{brute} valori brute -> {stari['referinta'] + stari['aproximativ'] + stari['conflict']} cu valoare")
        for s in ("referinta", "aproximativ", "conflict", "doar_variante", "lipsa"):
            print(f"  {s:14} {stari[s]:5}")
        if arg.simulare:
            return 0
        ids = sorted({(r["id_banca"], r["id_produs_libra"]) for r in rezultate} | {(p["id_banca"], p["id_produs_libra"]) for p in perechi})
        cur.execute("""DELETE FROM valori_referinta WHERE baza = %s
                         AND (id_banca, id_produs_libra) IN (SELECT * FROM unnest(%s::bigint[], %s::bigint[]))""",
                    (arg.baza, [i for i, _ in ids], [j for _, j in ids]))
        psycopg2.extras.execute_values(cur, """
            INSERT INTO valori_referinta (baza, id_banca, id_produs_libra, camp_cheie, stare, valoare_num, unitate,
                moneda, camp_sursa, derivat, id_comparatie, surse, variante, alternative, n_brut, n_unice, motiv)
            VALUES %s""", [(arg.baza, r["id_banca"], r["id_produs_libra"], r["camp_cheie"], r["stare"], r["valoare_num"],
                            r["unitate"], r["moneda"], r["camp_sursa"], r["derivat"], r["id_comparatie"],
                            json.dumps(r["surse"], ensure_ascii=False, default=str),
                            json.dumps(r["variante"], ensure_ascii=False, default=str),
                            json.dumps(r["alternative"], ensure_ascii=False, default=str),
                            r["n_brut"], r["n_unice"], r["motiv"]) for r in rezultate])
        print(f"scrise {len(rezultate)} rânduri în valori_referinta (baza {arg.baza})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
