"""Sucursale și ATM-uri din Overture Maps Places -> tabela `locatii`.

Înlocuiește datele mock ale hărții (66 de locații și 177 de recenzii
inventate) cu puncte reale.

De unde: depozitul public Overture (S3), ultima versiune, doar categoriile
`atms`, `banks`, `bank_credit_union`, doar România. DuckDB citește numai
bucățile de fișier necesare. Extrasul brut se păstrează în
`bronze/overture/`, ca dovadă a ce s-a încărcat.

Legarea de bancă se face doar pe nume sau brand ACTUAL. Brandurile vechi
(Alpha Bank, Bancpost, Banca Românească, OTP, Credit Europe, Carpatica…) NU
se atribuie băncii care le-a preluat: datele nu spun dacă punctul mai există
sub noul nume, deci ar fi o presupunere. Se numără în raport.

Măsurat pe versiunea 2026-08-19: 1.340 de puncte în România, dintre care doar
126 de ATM-uri — acoperirea la ATM-uri e slabă. Locatoarele băncilor, care
vin cu descoperirea, sunt sursa principală pe termen lung.

Rulare:
    python ingest/load_locatii_overture.py            # descarcă și încarcă
    python ingest/load_locatii_overture.py --uscat    # doar raportul, fără scriere
"""

import argparse
import collections
import os
import re
import sys
import unicodedata

import psycopg2
import psycopg2.extras

AICI = os.path.dirname(os.path.abspath(__file__))
RADACINA = os.path.dirname(AICI)
sys.path.insert(0, RADACINA)
sys.path.insert(0, AICI)

import config                      # noqa: E402
import normalizeaza as N           # noqa: E402
from crawler import UA             # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEPOZIT = "overturemaps-us-west-2"
DOSAR = os.path.join(RADACINA, "bronze", "overture")
CATEGORII = ("atms", "banks", "bank_credit_union")
# Sub pragul ăsta Overture însuși consideră punctul nesigur (poate să nu
# existe). Se sare, dar se numără.
PRAG_INCREDERE = 0.5

# Ordinea contează: BCR Banca pentru Locuințe înaintea BCR.
# Acronimele scurte (ING, BRD, BCR, CEC, BT) se potrivesc doar ca majuscule,
# ca „ING" să nu prindă cuvinte care conțin „ing".
TIPARE = [
    ("bcr-locuinte", re.compile(r"bcr\s*(banca\s*pentru\s*)?locuinte", re.I)),
    ("bcr", re.compile(r"\bBCR\b|banca comerciala romana", re.I)),
    ("banca-transilvania", re.compile(r"(?i:banca transilvania)|^BT\b")),
    ("brd", re.compile(r"\bBRD\b")),
    ("cec", re.compile(r"\bC\.?E\.?C\.?(\s|$)|\bCEC\b", re.I)),
    ("raiffeisen", re.compile(r"raiffeisen", re.I)),
    ("ing", re.compile(r"\bING\b")),
    ("unicredit", re.compile(r"unicredit", re.I)),
    ("garanti", re.compile(r"garanti", re.I)),
    ("tbi", re.compile(r"\btbi bank\b", re.I)),
    ("libra", re.compile(r"libra (internet )?bank", re.I)),
    ("patria", re.compile(r"patria bank", re.I)),
    ("intesa", re.compile(r"intesa sanpaolo", re.I)),
    ("exim", re.compile(r"exim\s*banca|eximbank", re.I)),
    ("creditcoop", re.compile(r"creditcoop", re.I)),
    ("procredit", re.compile(r"procredit", re.I)),
    ("vista", re.compile(r"vista bank", re.I)),
    ("salt", re.compile(r"salt bank", re.I)),
    ("brci", re.compile(r"\bBRCI\b|banca romana de credite", re.I)),
    ("citibank", re.compile(r"citibank", re.I)),
    ("techventures", re.compile(r"techventures", re.I)),
]
RE_ATM = re.compile(r"\bATM\b|bancomat", re.I)
RE_CRIPTO = re.compile(r"bitcoin|crypto|bitomat|shitcoins", re.I)


def fara_diacritice(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s or "")
                   if not unicodedata.combining(c))


def banca_pentru(nume, brand):
    """Slug-ul băncii, sau None. Brandul are prioritate față de nume."""
    for text in (brand, nume):
        t = fara_diacritice(text)
        if not t:
            continue
        for slug, tipar in TIPARE:
            if tipar.search(t):
                return slug
    return None


def ultima_versiune():
    import requests
    r = requests.get(f"https://{DEPOZIT}.s3.us-west-2.amazonaws.com/"
                     "?list-type=2&prefix=release/&delimiter=/",
                     headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    return sorted(re.findall(r"<Prefix>release/([^<]+)/</Prefix>", r.text))[-1]


def descarca(versiune):
    """Extrasul României în Bronze. Nu se reia dacă există deja."""
    import duckdb
    os.makedirs(DOSAR, exist_ok=True)
    cale = os.path.join(DOSAR, f"ro_{versiune}.parquet")
    if os.path.exists(cale):
        return cale
    c = duckdb.connect(config={"custom_user_agent": UA})
    c.execute("LOAD httpfs; SET s3_region='us-west-2';")
    sursa = (f"read_parquet('s3://{DEPOZIT}/release/{versiune}/theme=places/"
             f"type=place/*', hive_partitioning=1)")
    c.execute(f"""COPY (
        SELECT id, names.primary AS nume, brand.names.primary AS brand,
               categories.primary AS categorie, confidence, operating_status,
               addresses[1].freeform AS adresa, addresses[1].locality AS oras,
               addresses[1].region AS regiune, addresses[1].country AS tara,
               bbox.xmin AS lon, bbox.ymin AS lat,
               list_transform(sources, s -> s.dataset) AS surse
        FROM {sursa}
        WHERE bbox.xmin BETWEEN 20.2 AND 29.8 AND bbox.ymin BETWEEN 43.6 AND 48.3
          AND categories.primary IN {CATEGORII}
          AND addresses[1].country = 'RO'
    ) TO '{cale.replace(os.sep, '/')}' (FORMAT parquet)""")
    return cale


def citeste(cale):
    import duckdb
    c = duckdb.connect()
    return c.execute(
        f"SELECT * FROM read_parquet('{cale.replace(os.sep, '/')}') WHERE tara = 'RO'"
    ).fetchall(), [d[0] for d in c.description]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--versiune", help="versiunea Overture (implicit: ultima)")
    ap.add_argument("--uscat", action="store_true", help="doar raportul, fără scriere")
    a = ap.parse_args()
    config.incarca()

    versiune = a.versiune or ultima_versiune()
    cale = descarca(versiune)
    randuri, coloane = citeste(cale)
    raport = collections.Counter()
    puncte = []

    for r in randuri:
        p = dict(zip(coloane, r))
        raport["puncte_ro"] += 1
        if p["operating_status"] and p["operating_status"] != "open":
            raport[f"sarit_{p['operating_status']}"] += 1
            continue
        if (p["confidence"] or 0) < PRAG_INCREDERE:
            raport["sarit_incredere_sub_prag"] += 1
            continue
        text = f"{p['nume'] or ''} {p['brand'] or ''}"
        if RE_CRIPTO.search(text):
            raport["sarit_atm_cripto"] += 1
            continue
        slug = banca_pentru(p["nume"], p["brand"])
        if not slug:
            raport["sarit_banca_nepotrivita"] += 1
            continue
        tip = "atm" if p["categorie"] == "atms" or RE_ATM.search(p["nume"] or "") else "sucursala"
        puncte.append((slug, tip, p))
        raport[f"banca_{slug}_{tip}"] += 1

    print(f"Overture {versiune}: {len(puncte)} puncte legate de o bancă\n")
    for k in sorted(raport):
        print(f"{raport[k]:6d}  {k}")

    if a.uscat:
        return 0

    with psycopg2.connect(N.dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT slug, id FROM banci")
            banci = dict(cur.fetchall())
            # Mock-ul pleacă întâi; recenziile mock se șterg în cascadă.
            cur.execute("DELETE FROM locatii WHERE sursa IN ('mock', 'overture')")
            print(f"\nșterse: {cur.rowcount} locații (mock + Overture anterior)")
            valori = [
                (banci[s], t, p["nume"], p["adresa"], p["oras"], p["regiune"],
                 p["lat"], p["lon"], None, "overture", p["id"],
                 ", ".join(sorted(set(p["surse"] or []))))
                for s, t, p in puncte if s in banci
            ]
            psycopg2.extras.execute_values(
                cur,
                """INSERT INTO locatii (id_banca, tip, nume, adresa, oras, sector,
                       lat, lon, program, sursa, ref_extern, furnizori)
                   VALUES %s ON CONFLICT (id_banca, tip, lat, lon) DO NOTHING""",
                valori,
            )
            cur.execute("SELECT count(*) FROM locatii WHERE sursa = 'overture'")
            print(f"scrise: {cur.fetchone()[0]} locații Overture "
                  f"({len(valori)} trimise; diferența = aceleași coordonate)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
