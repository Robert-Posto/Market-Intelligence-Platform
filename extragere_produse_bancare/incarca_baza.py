#!/usr/bin/env python3
"""
incarca_baza.py — pune în baza MIP datele fluxului, din fișierele din repo.

    python extragere_produse_bancare/incarca_baza.py            # din rădăcina repo-ului

Pentru cine clonează repo-ul: după ce baza MIP există (`banci` populată, vezi
README, „Migrări”), comanda asta face tot restul, fără descărcări și fără model:
  1. migrările fluxului (db/migration_027 … 034), doar dacă tabelele lipsesc;
  2. cele 57 de produse Libra (produse_libra.json, fără descrierile interne);
  3. sursele, din inventare-libra/<banca>/*.json      (descopera_surse_libra --din-json)
  4. valorile, din inventare-libra/valori-<banca>.json (extrage_comparatie_libra --din-json)
  5. produsele concurenței, din inventare-produse/     (descopera_produse --din-json)

Se poate rula de mai multe ori: fiecare pas rescrie doar ce scrie el.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import psycopg2

AICI = Path(__file__).resolve().parent
RADACINA = AICI.parent
DSN = os.environ.get("MIP_DSN", "host=localhost port=5432 dbname=mip user=mip password=mip")
MIGRARI = [f"migration_0{n}_{s}.sql" for n, s in [
    (27, "produse_libra"), (28, "banci_acces_restricted"), (29, "inventar_libra"),
    (30, "surse_comparatie_concurenta"), (31, "surse_libra_not_found"), (32, "hashes_libra"),
    (33, "comparatie_scenariu"), (34, "products_discovery")]]


def spune(m: str) -> None:
    print(m, flush=True)


def exista(cur, tabela: str) -> bool:
    cur.execute("SELECT to_regclass(%s) IS NOT NULL", (f"public.{tabela}",))
    return cur.fetchone()[0]


def migrari(conn) -> None:
    with conn.cursor() as cur:
        if not exista(cur, "banci"):
            sys.exit("Baza n-are tabela `banci`: creează întâi baza MIP (db/schema.sql, seed-urile și "
                     "migrările 002–026, vezi README) sau importă copia bazei (deploy/importa_baza_docker.ps1).")
        # 030 refăcea comparatie_libra de la zero: pe o bază care are deja fluxul,
        # migrările vechi nu se mai rulează, altfel s-ar pierde valorile
        if exista(cur, "comparatie_libra"):
            de_rulat = [] if exista(cur, "products_discovery") else MIGRARI[-1:]
        else:
            de_rulat = MIGRARI
    # fiecare migrare are BEGIN/COMMIT al ei, deci rulează fără tranzacția implicită a psycopg2
    conn.commit()
    conn.autocommit = True
    for f in de_rulat:
        with conn.cursor() as cur:
            cur.execute((RADACINA / "db" / f).read_text(encoding="utf-8"))
        spune(f"  migrare aplicată: {f}")
    if not de_rulat:
        spune("  migrările fluxului erau deja aplicate")


def produse_libra(conn) -> None:
    lista = json.loads((AICI / "produse_libra.json").read_text(encoding="utf-8"))["produse"]
    with conn.cursor() as cur:
        for p in lista:
            cur.execute("""
                INSERT INTO produse_libra (cod, denumire, segment, categorie_cod, prioritar)
                VALUES (%(cod)s, %(denumire)s, %(segment)s, %(categorie_cod)s, %(prioritar)s)
                ON CONFLICT (cod) DO UPDATE SET denumire = EXCLUDED.denumire, segment = EXCLUDED.segment,
                    categorie_cod = EXCLUDED.categorie_cod, prioritar = EXCLUDED.prioritar,
                    activ = TRUE, updated_at = now()""", p)
    conn.commit()
    spune(f"  {len(lista)} produse Libra")


def banci_cu_date(conn, dosar: Path, tipar: str) -> list[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT slug, acces_restricted FROM banci")
        banci = dict(cur.fetchall())
    gasite = sorted({p.stem.split("-", 1)[1] if "-" in p.stem and tipar != "dosar" else p.name
                     for p in (dosar.iterdir() if dosar.exists() else [])
                     if (p.is_dir() if tipar == "dosar" else p.name.startswith(tipar))})
    lipsa = [b for b in gasite if b not in banci]
    if lipsa:
        spune(f"  ! băncile {', '.join(lipsa)} nu sunt în tabela banci: sărite")
    # o bancă marcată acces_restricted n-ar trebui accesată; aici nu se accesează nimic,
    # dar scripturile fluxului refuză oricum banca, deci se sare și la încărcare
    return [b for b in gasite if b in banci and not banci[b]]


def ruleaza(script: str, *argumente: str) -> None:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([sys.executable, str(AICI / script), *argumente], cwd=RADACINA, env=env,
                       capture_output=True, text=True, encoding="utf-8")
    for linie in (r.stdout + r.stderr).splitlines():
        if linie.strip() and not linie.startswith("  !"):
            spune(f"    {linie}")
    if r.returncode:
        sys.exit(f"{script} {' '.join(argumente)} a eșuat (cod {r.returncode})")


def main() -> None:
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass
    with psycopg2.connect(DSN) as conn:
        spune("1. migrări"); migrari(conn)
        spune("2. produsele Libra"); produse_libra(conn)
        surse = banci_cu_date(conn, AICI / "inventare-libra", "dosar")
        valori = banci_cu_date(conn, AICI / "inventare-libra", "valori-")
        concurenta = banci_cu_date(conn, AICI / "inventare-produse", "produse-")
    spune(f"3. surse: {', '.join(surse)}")
    for b in surse:
        ruleaza("descopera_surse_libra.py", "--banca", b, "--din-json")
    spune(f"4. valori: {', '.join(valori)}")
    for b in valori:
        ruleaza("extrage_comparatie_libra.py", "--banca", b, "--din-json")
    spune(f"5. produsele concurenței: {', '.join(concurenta)}")
    if concurenta:
        ruleaza("descopera_produse.py", "--banca", ",".join(concurenta), "--din-json")
    with psycopg2.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("SELECT (SELECT count(*) FROM surse_libra), (SELECT count(*) FROM comparatie_libra), "
                    "(SELECT count(*) FROM products_discovery)")
        s, v, p = cur.fetchone()
    spune(f"\nGATA: {s} surse, {v} valori, {p} produse ale concurenței.")


if __name__ == "__main__":
    main()
