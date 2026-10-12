#!/usr/bin/env python3
"""
consolideaza_referinta.py — valorile de referință, din comparatie_libra în valori_referinta.

    python consolideaza_referinta.py                    # toate băncile, din comparatie_libra (baza „curent”)
    python consolideaza_referinta.py --baza v1          # din copia fluxului vechi (comparatie_libra_v1)
    python consolideaza_referinta.py --banca bcr --produse CARD_DEBIT_FREE,CONT_ONLINE_PERSONAL
    python consolideaza_referinta.py --simulare         # bilanțul, fără scriere

Fără model și fără descărcări: doar regulile din referinta.py peste ce s-a extras deja, deci se
poate rula oricând (după o extragere, după o schimbare în fise_produse.json). Istoricul ține doar
schimbările (migrarea 044, `scrie_istoric`): rând nou când referința unei chei se schimbă, altfel
doar `confirmat_la` pe ultimul rând; paginile citesc ultimul rând pe cheie din vederea
valori_referinta_curente, iar evoluția stă în vederea schimbari_referinta. Fiecare rând poartă data
extragerii, data de la citat și data documentului, de pe rândul ales din comparatie_libra.

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
                           c.data_colectare, c.valabil_de_la, c.data_document, c.data_document_sursa,
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
            randuri = pe.get((p["id_banca"], p["id_produs_libra"]), [])
            pe_id = {x["id"]: x for x in randuri}
            for k in fise.campuri_cheie(p["cod"]):
                r = alege(fise, p["cod"], k, randuri)
                ales = pe_id.get(r["id_comparatie"]) or {}
                rezultate.append({**r, "id_banca": p["id_banca"], "id_produs_libra": p["id_produs_libra"],
                                  "data_extragere": ales.get("data_colectare"), "data_citat": ales.get("valabil_de_la"),
                                  "data_document": ales.get("data_document"),
                                  "data_document_sursa": ales.get("data_document_sursa")})
        stari = Counter(r["stare"] for r in rezultate)
        brute = sum(r["n_brut"] for r in rezultate)
        print(f"baza {arg.baza}: {len(perechi)} perechi bancă × produs, {len(rezultate)} câmpuri cheie; "
              f"{brute} valori brute -> {stari['referinta'] + stari['aproximativ'] + stari['conflict']} cu valoare")
        for s in ("referinta", "aproximativ", "conflict", "doar_variante", "lipsa"):
            print(f"  {s:14} {stari[s]:5}")
        if arg.simulare:
            return 0
        noi, confirmate, scoase = scrie_istoric(cur, arg.baza, rezultate, arg.banca, produse)
        print(f"istoric (baza {arg.baza}): {sum(1 for x in noi if x['_motiv'] == 'nou')} chei noi, "
              f"{sum(1 for x in noi if x['_motiv'] == 'schimbat')} schimbate, {confirmate} neschimbate (confirmate), "
              f"{scoase} scoase (rând `lipsa`)")
    return 0


def _semnatura(stare, valoare, unitate, moneda) -> tuple:
    """Ce înseamnă „altă referință”: altă stare, altă cifră, altă unitate sau monedă. Sursele, citatul
    și variantele se pot schimba fără ca cifra comparată să se schimbe."""
    return (stare, None if valoare is None else round(float(valoare), 6), unitate, moneda)


def scrie_istoric(cur, baza: str, rezultate: list[dict], banca: str | None, produse: list[str] | None):
    """
    Istoricul doar cu schimbări (migrarea 044). Pe fiecare cheie bancă × produs × câmp cheie:
      - prima dată, sau altă referință decât ultimul rând: rând nou (generat_la = acum);
      - aceeași referință: ultimul rând primește confirmat_la = acum, fără rând nou;
      - o cheie care avea rând, dar nu mai e evaluată (câmp scos din fișă, produs negăsit la bancă,
        în filtrul rulării): rând `lipsa`, ca cifra veche să nu rămână curentă.
    Întoarce (rândurile noi, câte confirmate, câte scoase). Toate în tranzacția apelantului, cu același
    now(): o rulare = un singur generat_la.
    """
    filtru, p = "", [baza]
    if banca:
        filtru += " AND b.slug = %s"
        p.append(banca)
    if produse:
        filtru += " AND pl.cod = ANY(%s)"
        p.append(produse)
    cur.execute(f"""SELECT v.id, v.id_banca, v.id_produs_libra, v.camp_cheie, v.stare, v.valoare_num, v.unitate, v.moneda
                      FROM valori_referinta_curente v JOIN banci b ON b.id = v.id_banca
                      JOIN produse_libra pl ON pl.id = v.id_produs_libra
                     WHERE v.baza = %s{filtru}""", p)
    ultime = {(r["id_banca"], r["id_produs_libra"], r["camp_cheie"]): r for r in cur.fetchall()}

    noi, de_confirmat, vazute = [], [], set()
    for r in rezultate:
        k = (r["id_banca"], r["id_produs_libra"], r["camp_cheie"])
        vazute.add(k)
        u = ultime.get(k)
        if u and _semnatura(u["stare"], u["valoare_num"], u["unitate"], u["moneda"]) == \
                _semnatura(r["stare"], r["valoare_num"], r["unitate"], r["moneda"]):
            de_confirmat.append((u["id"], r))
        else:
            noi.append({**r, "_motiv": "schimbat" if u else "nou"})
    scoase = 0
    for k, u in ultime.items():
        if k in vazute or u["stare"] == "lipsa":
            continue
        scoase += 1
        noi.append({"id_banca": k[0], "id_produs_libra": k[1], "camp_cheie": k[2], "stare": "lipsa",
                    "valoare_num": None, "unitate": None, "moneda": None, "camp_sursa": None, "derivat": False,
                    "id_comparatie": None, "surse": [], "variante": [], "alternative": [], "n_brut": 0, "n_unice": 0,
                    "motiv": "nu mai e evaluată: câmp scos din fișa produsului sau produs negăsit la bancă",
                    "data_extragere": None, "data_citat": None, "data_document": None, "data_document_sursa": None,
                    "_motiv": "scos"})

    if de_confirmat:
        # aceeași referință: nu e o schimbare, deci niciun rând nou; rândul curent primește însă detaliile
        # proaspete (surse, variante, motiv, date), ca sertarul să arate ce a găsit ultima extragere
        psycopg2.extras.execute_batch(cur, """
            UPDATE valori_referinta SET confirmat_la = now(), surse = %s, variante = %s, alternative = %s,
                   motiv = %s, n_brut = %s, n_unice = %s, id_comparatie = %s,
                   data_extragere = %s, data_citat = %s, data_document = %s, data_document_sursa = %s
             WHERE id = %s""", [(json.dumps(r["surse"], ensure_ascii=False, default=str),
                                 json.dumps(r["variante"], ensure_ascii=False, default=str),
                                 json.dumps(r["alternative"], ensure_ascii=False, default=str),
                                 r["motiv"], r["n_brut"], r["n_unice"], r["id_comparatie"], r["data_extragere"],
                                 r["data_citat"], r["data_document"], r["data_document_sursa"], i)
                                for i, r in de_confirmat])
    if noi:
        psycopg2.extras.execute_values(cur, """
            INSERT INTO valori_referinta (baza, id_banca, id_produs_libra, camp_cheie, stare, valoare_num, unitate,
                moneda, camp_sursa, derivat, id_comparatie, surse, variante, alternative, n_brut, n_unice, motiv,
                data_extragere, data_citat, data_document, data_document_sursa)
            VALUES %s""", [(baza, r["id_banca"], r["id_produs_libra"], r["camp_cheie"], r["stare"], r["valoare_num"],
                            r["unitate"], r["moneda"], r["camp_sursa"], r["derivat"], r["id_comparatie"],
                            json.dumps(r["surse"], ensure_ascii=False, default=str),
                            json.dumps(r["variante"], ensure_ascii=False, default=str),
                            json.dumps(r["alternative"], ensure_ascii=False, default=str),
                            r["n_brut"], r["n_unice"], r["motiv"], r["data_extragere"], r["data_citat"],
                            r["data_document"], r["data_document_sursa"]) for r in noi])
    return noi, len(de_confirmat), scoase


if __name__ == "__main__":
    sys.exit(main())
