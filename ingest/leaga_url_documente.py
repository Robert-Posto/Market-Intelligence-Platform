"""Leaga documentele PDF locale la URL-urile reale descoperite de discovery.

Problema: comisioanele vin din PDF-uri identificate prin calea locala din
pachetul Playwright (`bcr/75f21725_Tarif_standard_de_comisioane_PF.pdf`).
Calea nu e un link, iar URL-ul de origine nu e inregistrat in pachet. Dar
discovery-ul LLM a gasit 40 de URL-uri de PDF, unele pentru aceleasi documente.

Regula: se leaga DOAR la potrivire exacta a numelui normalizat (prefixul de
amprenta scos, punctuatie ignorata, URL-decodat). Motivul e masurat, nu
teoretic: la prag 0.85 apar potriviri gresite - `Ghid_tarife_comisioane.pdf`
se lega la `Ghid_dobanzi_si_comisioane_credite.pdf`, alt document, iar doua
documente locale diferite pretindeau acelasi URL. Un link greșit trimite pe
cineva la alt document decat cel din care vine cifra, adica exact opusul unei
dovezi. Mai bine 9 linkuri sigure decat 22 din care unele mint.

Rularea e idempotenta.
"""

import difflib
import io
import os
import re
import sys
import urllib.parse

import psycopg2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402

PRAG = 0.95


def norm(s):
    s = urllib.parse.unquote(os.path.basename(s)).lower()
    s = re.sub(r"^[0-9a-f]{8}_", "", s)            # prefixul de amprenta din pachet
    return re.sub(r"[^a-z0-9]+", "", s.replace(".pdf", ""))


def main():
    config.incarca()
    err = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
    dsn = os.environ.get("MIP_DSN", "host=localhost port=5432 dbname=mip user=mip password=mip")

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT s.id, b.slug, s.sursa FROM surse s
                           JOIN banci b ON b.id = s.id_banca
                           WHERE s.tip_sursa = 'document'""")
            docs = cur.fetchall()
            cur.execute("""SELECT b.slug, s.sursa FROM surse s
                           JOIN banci b ON b.id = s.id_banca
                           WHERE s.tip_sursa = 'url' AND s.format = 'pdf'""")
            urls = cur.fetchall()

            legate, nelegate = 0, []
            for id_doc, slug, cale in docs:
                cand = [u for s2, u in urls if s2 == slug]
                n = norm(cale)
                best, score = None, 0.0
                for u in cand:
                    r = difflib.SequenceMatcher(None, n, norm(u)).ratio()
                    if r > score:
                        best, score = u, r
                if best and score >= PRAG:
                    cur.execute("UPDATE surse SET url_public = %s WHERE id = %s", (best, id_doc))
                    legate += 1
                    err.write(f"OK   {score:.2f}  {os.path.basename(cale)[:44]:46s}\n")
                else:
                    nelegate.append((slug, os.path.basename(cale), round(score, 2)))

    err.write(f"\n{legate} documente legate la URL public, {len(nelegate)} rămase fără link.\n")
    err.write("Cele fără link păstrează numele fișierului și pagina — verificabile manual,\n"
              "dar URL-ul nu e inregistrat in pachetul sursa.\n")
    err.flush()


if __name__ == "__main__":
    main()
