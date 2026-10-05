#!/usr/bin/env python3
"""
extrage_comparatie_libra.py — din surse_libra în comparatie_libra.

    python extrage_comparatie_libra.py --banca bcr
    python extrage_comparatie_libra.py --banca bcr --simulare     # planul, fără cost
    python extrage_comparatie_libra.py --banca bcr --paralel 4 --forteaza

Pentru fiecare URL găsit la discovery (nu și cele not_found) cheamă
`cauta_date` din search_data_by_source.py — descărcare, Bronze, verificarea
formatului din octeți, flow-html / flow-pdf — și scrie valorile în
comparatie_libra.

TREI LUCRURI NOI FAȚĂ DE ruleaza-extractie.py

  Maparea produselor. Flow-urile caută după catalogul v2 (câmpuri, trepte),
  iar produsele Libra au alte coduri. mip/mapare_libra_v2.json le leagă.

  Un apel per URL, nu per produs. Același PDF de tarife acoperă de obicei mai
  multe produse Libra; i se cer toate odată, iar valorile se întorc la fiecare
  produs Libra care a indicat URL-ul.

  Fără fallback după refuz (`fara_fallback`). La 403 sursa e `blocat`, nu
  se încearcă web_fetch: regula echipei MIP.

Rezultate:
    comparatie_libra (Postgres, MIP_DSN)       valorile, stare = propus
    inventare-libra/valori-<banca>.json        raportul complet per URL, cu
                                               respinsele și produsele negăsite;
                                               servește și la reluare
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import psycopg2

AICI = Path(__file__).parent
sys.path.insert(0, str(AICI))

# Pragul de respingere coboară la 0,6; între 0,6 și PRAG_SIGUR (0,85) valoarea
# intră cu încrederea ei, marcată `necesita_verificare` de flow. Comentariul din
# flow-html.py (PRAG_SIGUR) arată de ce: pe 1.203 rânduri, cifra apărea în citat
# în 87-98% din cazuri și la încrederi între 0,5 și 0,85. Cu ambele praguri la
# 0,85, 1.263 de valori erau aruncate pe 5 bănci. Setat înainte de import:
# flow-html citește pragul la încărcare.
os.environ.setdefault("PRAG_INCREDERE", "0.6")

import preturi                            # noqa: E402
import search_data_by_source as S        # noqa: E402
from scenariu_libra import descompune, interval, potrivire   # noqa: E402
import reguli_valori                      # noqa: E402
from descopera_surse_libra import link_live   # noqa: E402

DSN = os.environ.get("MIP_DSN", "host=localhost port=5432 dbname=mip user=mip password=mip")
MAPARE = json.loads((AICI / "mapare_libra_v2.json").read_text(encoding="utf-8"))["mapare"]
IESIRE = AICI / "inventare-libra"

# Ce au respins regulile deterministe (reguli_valori) și axa Libra, cu motivul.
# Se scrie în inventare-libra/respinse-reguli-<banca>.json: nu se pierde nimic.
RESPINSE_REGULI: list[dict] = []

# unitatea din flow -> (unitate, monedă) în comparatie_libra
UNITATI = {"procent": ("%", None), "puncte_procentuale": ("pp", None),
           "lei": ("lei", "RON"), "eur": ("eur", "EUR"), "usd": ("usd", "USD"),
           "luni": ("luni", None), "ani": ("ani", None), "zile": ("zile", None),
           "numar": ("numar", None), "altele": (None, None)}


def spune(m: str) -> None:
    print(m, file=sys.stderr, flush=True)


def surse_de_extras(conn, slug: str) -> tuple[int, list[dict]]:
    """Rândurile găsite din surse_libra, grupate pe URL."""
    with conn.cursor() as cur:
        cur.execute("SELECT id, acces_restricted FROM banci WHERE slug = %s", (slug,))
        idb, restrictionat = cur.fetchone()
        if restrictionat:
            sys.exit(f"{slug} are acces_restricted = TRUE: nu se accesează.")
        cur.execute("""
            SELECT s.id, s.url, s.tip, s.metoda, p.id, p.cod, p.denumire, p.descriere, s.denumire_la_banca
              FROM surse_libra s JOIN produse_libra p ON p.id = s.id_produs_libra
             WHERE s.id_banca = %s AND NOT s.not_found AND s.url IS NOT NULL
             ORDER BY s.url""", (idb,))
        # Un grup = un URL × produsul echivalent găsit la discovery. Fără al doilea
        # termen, un PDF de tarife întorcea toate pachetele de același tip la fiecare
        # produs Libra legat de el (44% din rânduri erau copii). Produsele Libra cu
        # același echivalent (ELITE și PRESTIGE -> „IMM Ultra" la Raiffeisen) împart apelul.
        grupuri: dict[tuple, dict] = {}
        for id_s, url, tip, metoda, id_p, cod, den, desc, la_banca in cur.fetchall():
            if cod not in MAPARE:
                spune(f"  ! {cod} nu e în mapare_libra_v2.json — sărit")
                continue
            la_banca = (la_banca or "").strip()
            cheie = f"{url}||{la_banca.lower()}"
            g = grupuri.setdefault(cheie, {"cheie": cheie, "url": url, "tip": tip, "metoda": metoda,
                                           "denumire_la_banca": la_banca, "legaturi": [], "libra": []})
            # playwright dacă oricare dintre propuneri îl cere: e estimarea mai prudentă
            if metoda == "playwright":
                g["metoda"] = "playwright"
            g["legaturi"].append({"id_sursa": id_s, "id_produs_libra": id_p, "cod": cod, "v2": MAPARE[cod]})
            g["libra"].append((den, desc))
        for g in grupuri.values():
            g["focus"] = focus(g, slug)
    return idb, list(grupuri.values())


def focus(g: dict, slug: str) -> str | None:
    """Instrucțiunea pentru extracție: ce produs anume al băncii se caută în document."""
    if not g["denumire_la_banca"]:
        return None
    # Descrierea Libra conține prețurile noastre („225 lei/lună"). La un concurent
    # ar ancora alegerea dintre cifrele reale ale documentului, deci acolo se dă
    # doar numele; ancora e produsul băncii, găsit la discovery.
    cu_descriere = slug == "libra"
    libra = "; ".join(f"„{d}”" + (f" ({desc})" if desc and cu_descriere else "")
                      for d, desc in dict.fromkeys(g["libra"]))
    cine = "Acesta e produsul Libra" if slug == "libra" else "Corespunde produsului Libra"
    return (f"Produsul băncii: „{g['denumire_la_banca']}”.\n"
            f"{cine}: {libra}.\n"
            "Raportează DOAR valorile acestui produs. Ignoră celelalte pachete, variante, conturi sau "
            "produse din document, chiar dacă sunt de același tip. Dacă documentul are o grilă cu mai "
            "multe pachete, ia doar coloana sau rândul acestui produs. Dacă documentul nu are valori "
            "pentru el, raportează gasit = false.")


def fara_descriere(f: str | None) -> str | None:
    """
    Instrucțiunea `focus`, fără descrierile din catalogul intern Libra, pentru JSON-ul
    salvat. Modelul le primește (la Libra, ca să aleagă cifrele potrivite), dar
    inventarele ajung în repo, iar catalogul e de uz intern: prețuri și condiții interne.
    """
    if not f:
        return f
    return re.sub(r"(„[^”]+”) \((?:[^()]|\([^()]*\))*\)", r"\1", f)


def scenariu_din(o: dict) -> dict | None:
    """
    Scenariul valorii: întâi `trepte` — axele structurate pe care flow-ul le cere
    deja modelului (suma, perioada, valuta), întoarse la ~600 de valori și
    ignorate până acum —, apoi ce se mai poate scoate din codul de scenariu.
    Trepte bat codul: sunt câmpuri cerute explicit, nu text compus de model.
    """
    sc = descompune(o.get("cod_scenariu")) or {}
    for tr in o.get("trepte") or []:
        dim, v = tr.get("dimensiune"), tr.get("valoare")
        de_la, pana_la = tr.get("de_la"), tr.get("pana_la")
        if dim == "suma":
            if v is not None:
                sc["suma"] = v; sc.pop("suma_max", None)
            elif de_la is not None or pana_la is not None:
                sc["suma"], sc["suma_max"] = de_la, pana_la
            sc.setdefault("moneda", "RON")
        elif dim == "perioada":
            if v is not None:
                sc["perioada_luni"] = v
            elif de_la is not None or pana_la is not None:
                sc.setdefault("etichete", []).append(
                    f"perioadă {de_la if de_la is not None else ''}–{pana_la if pana_la is not None else ''} luni")
        elif dim == "perioada_ramasa":
            sc.setdefault("etichete", []).append(
                "perioadă rămasă " + (f"peste {de_la} luni" if de_la is not None else f"sub {pana_la} luni"))
        elif dim == "valuta" and tr.get("valoare_text"):
            sc["valuta"] = tr["valoare_text"].upper()
        sc["din_trepte"] = True
    return sc or None


def _respinge(grup: dict, o: dict, motiv: str, cod: str | None = None) -> None:
    RESPINSE_REGULI.append({"url": grup["url"], "produse": [cod] if cod else sorted({l["cod"] for l in grup["legaturi"]}),
                            "camp": o.get("camp"), "valoare_num": o.get("valoare_num"),
                            "unitate": o.get("unitate"), "citat": o.get("citat"),
                            "incredere": o.get("confidence"), "motiv": motiv})


def randuri_comparatie(idb: int, grup: dict, rez: dict, slug: str | None = None) -> list[tuple]:
    """Observațiile acceptate de flow -> rânduri comparatie_libra, una per produs Libra legat."""
    out = []
    for o in rez.get("observatii") or []:
        if o.get("not_found") or not o.get("camp") or not o.get("citat"):
            continue
        if o.get("valoare_num") is None and not o.get("eticheta_libera"):
            continue
        # reguli deterministe: zero fără dovadă, dobânzi minime/maxime/penalizatoare, ani -> luni
        corectat, motiv_respins = reguli_valori.aplica(o)
        if corectat is None:
            _respinge(grup, o, motiv_respins)
            continue
        o = corectat
        unitate, moneda = UNITATI.get(o.get("unitate"), (o.get("unitate"), None))
        conditii = [c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)
                    for c in (o.get("conditii") or [])]
        sc = scenariu_din(o)
        if sc and sc.get("valuta"):
            # valuta face parte din cheia valorii: EUR și USD nu sunt aceeași condiție
            conditii.insert(0, f"valuta {sc['valuta']}")
        if o.get("cod_scenariu"):
            conditii.insert(0, str(o["cod_scenariu"]))
        for e in o.get("etichete_reguli") or []:
            # „dobândă medie” și dobânda de listă sunt două valori, nu una ambiguă: intră în cheie
            conditii.append(e)
            sc = sc or {}
            sc.setdefault("etichete", []).append(e)
        if o.get("reguli"):
            sc = sc or {}
            sc["reguli"] = o["reguli"]
        if o.get("metoda") == "derivat":
            # metoda_extractie are CHECK (parser/llm/manual/catalog): marcajul stă în scenariu
            sc = sc or {}
            sc["derivat"] = True
        # Ambiguitatea NU se ia de la flow: `conflict_scenariu` marchează orice câmp
        # care apare de mai multe ori fără cod de scenariu, iar doar câteva produse
        # din catalogul v2 au axe de scenariu. Din 145 de valori marcate așa, 48 erau
        # aceeași cifră găsită de două ori și 49 aveau condiții diferite. Se decide
        # în `rezolva`, pe banca întreagă: doar valori DIFERITE pe aceeași cheie.
        # `necesita_verificare` (încredere 0,6-0,85) NU înseamnă ambiguu: valoarea e
        # clară, doar mai puțin sigură, iar încrederea ei rămâne în rând. Ambiguu e
        # un citat scurt găsit de mai multe ori în document: contextul e de la
        # prima apariție și poate fi al altui exemplu.
        n_ap = o.get("citat_aparitii")
        ambiguu = bool(n_ap)
        motiv = (f"citatul „{o.get('citat_original')}” apare de {n_ap} ori în document; "
                 "contextul e de la prima apariție") if ambiguu else None
        link = link_live(grup["url"], o["citat"]) if grup["tip"] == "html" else None
        for leg in grup["legaturi"]:
            if leg["v2"] != o.get("id_produs"):
                continue
            sc_l, cond_l = (dict(sc) if sc else None), list(conditii)
            if slug == "libra":
                # axa Libra: valorile unui produs vin doar din paginile lui (axa_libra.json)
                rol, nota = reguli_valori.axa_libra(grup["url"], leg["cod"])
                if rol == "exclus":
                    _respinge(grup, o, f"axa Libra: {nota}", leg["cod"])
                    continue
                if rol == "varianta":
                    cond_l.append(f"variantă: {nota}")
                    sc_l = sc_l or {}
                    sc_l.setdefault("etichete", []).append(nota)
                    sc_l["varianta"] = nota
            ref = potrivire(leg["cod"], leg["v2"], o["camp"], sc_l, o.get("potrivire_scenariu"))
            if ref:
                sc_l = sc_l or {}
                sc_l["referinta"] = ref
            out.append((idb, leg["id_produs_libra"], leg["id_sursa"], o["camp"],
                        o.get("valoare_num"), None if o.get("valoare_num") is not None else o.get("eticheta_libera"),
                        unitate, moneda, "; ".join(cond_l) or None, o["citat"], link,
                        "llm", round(float(o.get("confidence") or 0), 2), ambiguu, motiv,
                        json.dumps(sc_l, ensure_ascii=False) if sc_l else None, *interval(sc_l)))
    return out


def _fmt(r: tuple) -> str:
    return f"{r[4]:g} {r[6] or ''}".strip() if r[4] is not None else str(r[5])


def rezolva(randuri: list[tuple]) -> list[tuple]:
    """
    Un rând per cheia unică din comparatie_libra (produs, câmp, monedă, condiție).

    - o singură valoare pe cheie, sau aceeași cifră găsită de mai multe ori
      (în pagini diferite, ori de două ori în aceeași pagină): un rând, neambiguu;
    - valori DIFERITE pe aceeași cheie (ex. 4,99% și 5,19%, ambele fără
      condiție): rămâne cea cu încrederea cea mai mare, marcată ambiguu, cu
      alternativele în motiv. Înainte, cealaltă se pierdea în tăcere la ON CONFLICT.
    """
    grupe: dict[tuple, list[tuple]] = defaultdict(list)
    for r in randuri:
        grupe[(r[1], r[3], r[7], r[8] or "")].append(r)
    out = []
    for g in grupe.values():
        g.sort(key=lambda r: -(r[12] or 0))
        ales = list(g[0])
        diferite = {(r[4], r[5], r[6]) for r in g}
        if len(diferite) > 1:
            alte = sorted({_fmt(r) for r in g if (r[4], r[5], r[6]) != (ales[4], ales[5], ales[6])})
            ales[13] = True
            ales[14] = (f"{len(diferite)} valori diferite pe aceeași condiție: "
                        f"{_fmt(tuple(ales))} (păstrată, încredere {ales[12]}) față de {', '.join(alte)}")
        out.append(tuple(ales))
    return out


def rescrie_banca(idb: int, randuri: list[tuple], produse: set[int] | None = None,
                  pastreaza_data: bool = False) -> int:
    """
    Înlocuiește toate propunerile băncii cu rândurile rezolvate; nu atinge ce a validat un om.
    `pastreaza_data`: la o rescriere fără descărcare (reguli noi peste același JSON) data
    colectării rămâne cea a sursei, nu ziua rescrierii.
    """
    with psycopg2.connect(DSN) as conn, conn.cursor() as cur:
        date_vechi = {}
        if pastreaza_data:
            cur.execute("SELECT id_sursa, MIN(data_colectare) FROM comparatie_libra "
                        "WHERE id_banca = %s GROUP BY id_sursa", (idb,))
            date_vechi = dict(cur.fetchall())
        if produse:   # --produse: doar rândurile produselor re-extrase, restul băncii rămâne
            cur.execute("DELETE FROM comparatie_libra WHERE id_banca = %s AND stare = 'propus' "
                        "AND id_produs_libra = ANY(%s)", (idb, list(produse)))
        else:
            cur.execute("DELETE FROM comparatie_libra WHERE id_banca = %s AND stare = 'propus'", (idb,))
        scrise = 0
        for r in rezolva(randuri):
            cur.execute("""
                INSERT INTO comparatie_libra (id_banca, id_produs_libra, id_sursa, camp, valoare_num,
                    valoare_text, unitate, moneda, conditie, citat, link_live, metoda_extractie,
                    incredere, ambiguu, motiv_ambiguu, scenariu, interval_min, interval_max, unitate_interval)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s)
                ON CONFLICT ON CONSTRAINT ux_comparatie_libra DO NOTHING""", r)
            scrise += cur.rowcount
        for id_sursa, data in date_vechi.items():
            cur.execute("UPDATE comparatie_libra SET data_colectare = %s WHERE id_banca = %s AND id_sursa = %s "
                        "AND stare = 'propus'", (data, idb, id_sursa))
    return scrise


def scrie_db(grup: dict, randuri: list[tuple]) -> int:
    ids = [l["id_sursa"] for l in grup["legaturi"]]
    with psycopg2.connect(DSN) as conn, conn.cursor() as cur:
        # reluarea unui URL înlocuiește propunerile lui; nu atinge ce a validat un om
        cur.execute("DELETE FROM comparatie_libra WHERE id_sursa = ANY(%s) AND stare = 'propus'", (ids,))
        scrise = 0
        for r in randuri:
            # aceeași valoare pe aceeași cheie din două surse: rămâne cea cu încredere mai mare
            cur.execute("""
                INSERT INTO comparatie_libra (id_banca, id_produs_libra, id_sursa, camp, valoare_num,
                    valoare_text, unitate, moneda, conditie, citat, link_live, metoda_extractie,
                    incredere, ambiguu, motiv_ambiguu, scenariu, interval_min, interval_max, unitate_interval)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s)
                ON CONFLICT ON CONSTRAINT ux_comparatie_libra DO UPDATE SET
                    id_sursa = EXCLUDED.id_sursa, valoare_num = EXCLUDED.valoare_num,
                    valoare_text = EXCLUDED.valoare_text, citat = EXCLUDED.citat,
                    link_live = EXCLUDED.link_live, incredere = EXCLUDED.incredere,
                    ambiguu = EXCLUDED.ambiguu, motiv_ambiguu = EXCLUDED.motiv_ambiguu,
                    data_colectare = CURRENT_DATE, updated_at = now()
                WHERE comparatie_libra.incredere IS NULL OR comparatie_libra.incredere < EXCLUDED.incredere
                """, r)
            scrise += cur.rowcount
    return scrise


def scrie_respinse(slug: str) -> None:
    """Ce au respins regulile și axa Libra, ca să se poată verifica și, la nevoie, recupera."""
    motive = defaultdict(int)
    for x in RESPINSE_REGULI:
        motive[x["motiv"]] += 1
    (IESIRE / f"respinse-reguli-{slug}.json").write_text(json.dumps(
        {"banca": slug, "total": len(RESPINSE_REGULI), "pe_motiv": dict(sorted(motive.items(), key=lambda m: -m[1])),
         "valori": RESPINSE_REGULI}, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


def hash_anterior(grup: dict) -> str | None:
    """
    Amprenta comună a tuturor legăturilor URL-ului. Dacă o legătură n-are încă
    amprentă (produs Libra nou pe un URL vechi), nu există „anterior": se extrage.
    """
    ids = [l["id_sursa"] for l in grup["legaturi"]]
    with psycopg2.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("SELECT id_sursa, hash FROM hashes_libra WHERE id_sursa = ANY(%s)", (ids,))
        h = dict(cur.fetchall())
    valori = {h.get(i) for i in ids}
    return valori.pop() if len(valori) == 1 and None not in valori else None


def noteaza(idb: int, grup: dict, rez: dict, schimbat: bool) -> None:
    """Amprenta în hashes_libra și starea verificării în surse_libra."""
    stare = rez.get("stare")
    h = rez.get("content_hash")
    cod_http = rez.get("blocaj_http_local")
    motiv = rez.get("motiv") or ""
    status = {"extras": "ok", "neschimbat": "neschimbat", "blocat": "blocat"}.get(stare, "eroare")
    if status == "eroare" and "404" in motiv:
        status, cod_http = "negasit", 404
    with psycopg2.connect(DSN) as conn, conn.cursor() as cur:
        for l in grup["legaturi"]:
            if h and status in ("ok", "neschimbat"):
                cur.execute("""
                    INSERT INTO hashes_libra (id_banca, id_produs_libra, id_sursa, hash)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (id_sursa) DO UPDATE SET
                        hash = EXCLUDED.hash, verificat_la = now(),
                        updated_at = CASE WHEN hashes_libra.hash <> EXCLUDED.hash THEN now()
                                          ELSE hashes_libra.updated_at END
                    """, (idb, l["id_produs_libra"], l["id_sursa"], h))
            cur.execute("""
                UPDATE surse_libra SET ultima_verificare = now(), ultimul_status = %s,
                       ultimul_cod_http = %s, ultimul_hash = COALESCE(%s, ultimul_hash),
                       esecuri_consecutive = CASE WHEN %s IN ('ok', 'neschimbat') THEN 0
                                                  ELSE esecuri_consecutive + 1 END
                 WHERE id = %s""", (status, cod_http, h, status, l["id_sursa"]))


async def un_url(idb: int, slug: str, grup: dict, sem: asyncio.Semaphore,
                 anterior: dict | None, forteaza: bool) -> dict:
    produse_v2 = sorted({l["v2"] for l in grup["legaturi"]})
    # Amprenta se compară doar dacă avem și valorile rulării anterioare: altfel un
    # document neschimbat ar lăsa produsul fără valori la rescrierea băncii.
    are_anterior = bool(anterior and anterior.get("stare") in ("extras", "neschimbat"))
    h_ant = None if forteaza or not are_anterior else hash_anterior(grup)
    async with sem:
        start = time.time()
        try:
            rez = await S.cauta_date({"id": grup["legaturi"][0]["id_sursa"], "id_banca": slug,
                                      "url": grup["url"], "format": grup["tip"], "metoda": grup["metoda"],
                                      "focus": grup.get("focus"),
                                      "produse": produse_v2, "fara_fallback": True,
                                      "hash_anterior": h_ant})
        except Exception as e:
            rez = {"stare": "eroare", "motiv": f"{type(e).__name__}: {e}", "observatii": []}
    neschimbat = rez.get("stare") == "neschimbat"
    noteaza(idb, grup, rez, schimbat=not neschimbat)
    if neschimbat:
        # Documentul e identic cu cel din rularea precedentă: procesul se oprește aici,
        # fără apel la model; valorile rămân cele extrase atunci.
        spune(f"neschimbat  amprentă identică, fără extracție, {round(time.time() - start):3}s  {grup['url'][:90]}")
        return {**anterior, "cheie": grup["cheie"], "legaturi": grup["legaturi"], "stare": "neschimbat",
                "durata_s": round(time.time() - start), "tokeni": {"intrare": 0, "iesire": 0},
                "content_hash": rez.get("content_hash")}
    randuri = randuri_comparatie(idb, grup, rez, slug)
    scrise = scrie_db(grup, randuri) if rez.get("stare") not in ("eroare",) else 0
    gasite = sum(1 for o in rez.get("observatii") or [] if not o.get("not_found"))
    spune(f"{(rez.get('stare') or '?'):10} {gasite:3} valori, {scrise:3} scrise, "
          f"{len(rez.get('respinse') or []):2} respinse, {round(time.time() - start):3}s  {grup['url'][:90]}")
    return {"cheie": grup["cheie"], "url": grup["url"], "tip": grup["tip"], "metoda": grup["metoda"],
            "denumire_la_banca": grup.get("denumire_la_banca"), "focus": fara_descriere(grup.get("focus")),
            "legaturi": grup["legaturi"], "produse_v2": produse_v2,
            "stare": rez.get("stare"), "motiv": rez.get("motiv"), "flow": rez.get("flow"),
            "format_efectiv": rez.get("format_efectiv"), "blocaj_http_local": rez.get("blocaj_http_local"),
            "metoda_sanitizare": rez.get("metoda_sanitizare"), "content_hash": rez.get("content_hash"),
            "observatii": rez.get("observatii") or [], "respinse": rez.get("respinse") or [],
            "scrise": scrise, "durata_s": round(time.time() - start),
            "tokeni": {"intrare": (rez.get("bilant") or {}).get("tokeni_intrare", 0),
                       "iesire": (rez.get("bilant") or {}).get("tokeni_iesire", 0)}}


async def main() -> None:
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass
    a = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    a.add_argument("--banca", required=True)
    a.add_argument("--paralel", type=int, default=4)
    a.add_argument("--forteaza", action="store_true",
                   help="re-extrage tot, ignorând amprentele (documentele neschimbate se plătesc din nou)")
    a.add_argument("--produse", help="coduri Libra separate prin virgulă: re-extrage doar aceste produse")
    a.add_argument("--doar-noi", action="store_true",
                   help="doar URL-urile fără rezultat bun în rularea precedentă (reluare după întrerupere)")
    a.add_argument("--simulare", action="store_true")
    a.add_argument("--din-json", action="store_true",
                   help="rescrie comparatie_libra din valori-<banca>.json, fără descărcări și fără API")
    a.add_argument("--doar-valori", action="store_true",
                   help="cu --din-json: rescrie doar valorile (ex. după o schimbare de reguli), fără să "
                        "atingă amprentele și data ultimei verificări a surselor")
    arg = a.parse_args()

    with psycopg2.connect(DSN) as conn:
        idb, grupuri = surse_de_extras(conn, arg.banca)
    cale = IESIRE / f"valori-{arg.banca}.json"
    if arg.din_json:
        # Legăturile din JSON poartă id-urile bazei pe care s-a extras (id_sursa,
        # id_produs_libra). Pe altă bază (un coleg care clonează repo-ul) id-urile
        # diferă, deci se refac după URL și codul produsului Libra, din surse_libra
        # de acum; rezultatele fără sursă corespondentă se sar.
        pe_cheie = {g["cheie"]: g for g in grupuri}

        def cu_legaturi_actuale(r: dict) -> dict | None:
            g = pe_cheie.get(r.get("cheie") or "")
            if g:
                return {**r, "legaturi": g["legaturi"]}
            coduri = {l["cod"] for l in r.get("legaturi") or []}
            leg = [l for g in grupuri if g["url"] == r["url"] for l in g["legaturi"] if l["cod"] in coduri]
            return {**r, "legaturi": leg} if leg else None

        rez_json = [x for x in (cu_legaturi_actuale(r) for r in json.loads(cale.read_text(encoding="utf-8"))["urluri"]
                                if r.get("stare") not in ("eroare", "blocat", None)) if x]
        toate = [x for r in rez_json for x in randuri_comparatie(idb, r, r, arg.banca)]
        total = rescrie_banca(idb, toate, pastreaza_data=arg.doar_valori)
        scrie_respinse(arg.banca)
        if arg.doar_valori:
            spune(f"{arg.banca}: din JSON — {len(toate)} valori, {total} rânduri după contopirea dublurilor, "
                  f"{len(RESPINSE_REGULI)} respinse de reguli; amprentele neatinse")
            return
        # Amprentele din JSON: fiecare observație poartă `content_hash`, aceeași
        # amprentă pe care o compară flow-urile. Fără ele, prima rulare cu
        # comparație ar re-extrage (și plăti) toate documentele.
        amprente = 0
        for r in json.loads(cale.read_text(encoding="utf-8"))["urluri"]:
            h = r.get("content_hash") or next((o.get("content_hash") for o in r.get("observatii") or []
                                               if o.get("content_hash")), None)
            cheie = r.get("cheie") or r["url"]
            if h and r.get("stare") in ("extras", "neschimbat") and cheie in {g["cheie"] for g in grupuri}:
                g = next(g for g in grupuri if g["cheie"] == cheie)
                noteaza(idb, g, {"stare": "extras", "content_hash": h}, schimbat=True)
                amprente += 1
        spune(f"{arg.banca}: din JSON — {len(toate)} valori, {total} rânduri după contopirea dublurilor, "
              f"{amprente} amprente în hashes_libra")
        return
    # Rularea precedentă: valorile ei se păstrează pentru documentele neschimbate.
    anterioare = {} if not cale.exists() else \
        {(r.get("cheie") or r["url"]): r for r in json.loads(cale.read_text(encoding="utf-8"))["urluri"]}
    actuale = {g["cheie"] for g in grupuri}
    if arg.produse:
        alese = set(arg.produse.split(","))
        grupuri = [g for g in grupuri if alese & {l["cod"] for l in g["legaturi"]}]
    if arg.doar_noi:
        de_facut = [g for g in grupuri if (anterioare.get(g["cheie"]) or {}).get("stare") not in ("extras", "neschimbat")]
    else:
        de_facut = grupuri   # implicit toate: amprenta decide ce se re-extrage
    legaturi = sum(len(g["legaturi"]) for g in grupuri)
    spune(f"{arg.banca}: {len(grupuri)} URL-uri ({legaturi} legături produs Libra), {len(de_facut)} de verificat, "
          f"{'fără comparație de amprentă (--forteaza)' if arg.forteaza else 'cu comparație de amprentă'}, paralel {arg.paralel}")
    if arg.simulare:
        for g in de_facut:
            spune(f"  [simulare] {g['tip']:4} {g['metoda']:10} {','.join(sorted({l['v2'] for l in g['legaturi']})):28} {g['url'][:80]}")
        return

    sem = asyncio.Semaphore(arg.paralel)
    # doar URL-urile care mai sunt în surse_libra; cele scoase la rediscovery dispar
    rezultate = {u: r for u, r in anterioare.items() if u in actuale or arg.produse}
    if arg.produse:
        # Din rezultatele vechi pe același URL (rularea fără produs-țintă, cu cheia doar
        # URL-ul) se scot DOAR legăturile produselor re-extrase; altfel valorile lor ar
        # reveni la rescrierea completă. Nu se scoate rezultatul întreg: un PDF de tarife
        # e legat și de alte produse, iar așa s-au pierdut 166 de valori la BRD și 136 la ING.
        for g in de_facut:
            coduri = {l["cod"] for l in g["legaturi"]}
            for k in [k for k, r in rezultate.items() if r["url"] == g["url"] and k != g["cheie"]]:
                ramase = [l for l in rezultate[k].get("legaturi") or [] if l["cod"] not in coduri]
                if ramase:
                    rezultate[k] = {**rezultate[k], "legaturi": ramase}
                else:
                    del rezultate[k]
    start = time.time()
    for f in asyncio.as_completed([un_url(idb, arg.banca, g, sem, anterioare.get(g["cheie"]), arg.forteaza)
                                   for g in de_facut]):
        r = await f
        rezultate[r["cheie"]] = r
        # scris după fiecare URL: o întrerupere nu pierde ce s-a extras
        cale.write_text(json.dumps({"banca": arg.banca, "urluri": list(rezultate.values())},
                                   ensure_ascii=False, indent=1, default=str), encoding="utf-8")

    # Scrierile per URL de mai sus sunt doar o plasă la întrerupere. Ambiguitatea se
    # decide pe banca întreagă: aceeași cheie poate veni din două URL-uri diferite.
    # Ce nu s-a putut verifica azi (eroare, blocaj) păstrează valorile de data trecută,
    # dacă există; altfel o pană de rețea ar șterge produsul din comparație.
    for u, r in list(rezultate.items()):
        a = anterioare.get(u) or {}
        if r.get("stare") in ("eroare", "blocat", None) and a.get("stare") in ("extras", "neschimbat"):
            rezultate[u] = {**a, "legaturi": r["legaturi"], "verificare_azi": r.get("stare")}
    cale.write_text(json.dumps({"banca": arg.banca, "urluri": list(rezultate.values())},
                               ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    produse_rescrise = ({l["id_produs_libra"] for g in de_facut for l in g["legaturi"]} if arg.produse else None)
    RESPINSE_REGULI.clear()   # scrierile per URL le-au adunat deja o dată; aici se refac pe toată banca
    cheile_rulate = {g["cheie"] for g in de_facut}
    total = rescrie_banca(idb, [x for k, r in rezultate.items()
                                if (not arg.produse or k in cheile_rulate)
                                if r.get("stare") not in ("eroare", "blocat", None)
                                for x in randuri_comparatie(idb, r, r, arg.banca)], produse_rescrise)
    scrie_respinse(arg.banca)
    stari = defaultdict(int)
    for r in rezultate.values():
        stari[r.get("stare") or "?"] += 1
    # doar URL-urile rulate acum: `rezultate` conține și rulările anterioare, păstrate
    # pentru documentele neschimbate, iar suma lor umfla costul (la --produse, ~$2,5 în loc de ~$0,5)
    rulate = [rezultate[k] for k in cheile_rulate if k in rezultate]
    ti = sum((r.get("tokeni") or {}).get("intrare", 0) for r in rulate)
    te = sum((r.get("tokeni") or {}).get("iesire", 0) for r in rulate)
    cost = preturi.cost(S.fh.MODEL, ti, te)
    spune(f"\n{arg.banca}: GATA — {dict(stari)}; {total} rânduri scrise în comparatie_libra; "
          f"cost estimat ${(cost or 0):.2f} ({ti} tokeni in / {te} out, fără cache); "
          f"{round((time.time() - start) / 60)} min")


if __name__ == "__main__":
    asyncio.run(main())
