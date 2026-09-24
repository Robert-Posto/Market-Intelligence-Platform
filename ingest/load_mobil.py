"""Track mobil iOS: versiuni, rating, capturi, recenzii — pentru toate băncile.

Înlocuiește `load_appstore.py`, care avea trei bănci scrise în cod și citea un
fișier fix. Aici lista vine din `date/app_id_gasite.json`, produs de
`cauta_app_id.py`, deci o bancă nouă nu cere nicio modificare de cod.

Umple secțiunile 2.3 (aplicații mobile) și 2.7 (sentiment) dintr-o rulare.
Stăteau amândouă la trei bănci nu din vreo limită tehnică, ci fiindcă nimeni
nu adăugase decât trei id-uri, de mână.

PSEUDONIMIZARE, obligatorie: feed-ul RSS al Apple întoarce numele real de
afișare al autorului. Nu se stochează niciodată brut — doar un hash cu sare
(`autor_hash`). Sarea vine din `MIP_SALT`; fără ea scriptul se oprește, pentru
că o sare implicită ar face hash-urile reversibile printr-un dicționar de
nume, adică pseudonimizare doar de formă.

Idempotent, cu o distincție care contează: versiunea și capturile descriu
STAREA de acum, deci se rescriu. Recenziile sunt ISTORIC, deci se acumulează
și nu se șterg niciodată — feed-ul Apple e capricios de la un apel la altul,
iar o recenzie colectată o dată nu trebuie să dispară pentru că a doua
cerere n-a răspuns.

Rulare:  python ingest/load_mobil.py
         python ingest/load_mobil.py --banca ing
"""

import argparse
import collections
import hashlib
import io
import json
import os
import sys
import time

import psycopg2
import psycopg2.extras
import requests

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AICI))
sys.path.insert(0, AICI)
import config                      # noqa: E402
import normalizeaza as N           # noqa: E402
import flux                        # noqa: E402
from crawler import UA as UA_ECHIPA  # noqa: E402

FISIER_ID = os.path.join(os.path.dirname(AICI), "date", "app_id_gasite.json")

# O singură vitrină, `ro`: colegul a măsurat că recenziile din vitrina `us`
# ale Citibank și Revolut sunt 0% în română (aplicații globale, clienți străini).
STOREFRONT = "ro"

UA = {"User-Agent": UA_ECHIPA}
PAUZA = 3.0          # o cerere la 3 s spre Apple


def hash_autor(nume, sare):
    return hashlib.sha256((sare + "|" + (nume or "")).encode("utf-8")).hexdigest()[:32]


def lookup(app_id):
    # `/lookup?` e permis; doar `/*/lookup?` (cu țara în cale) e interzis.
    r = requests.get("https://itunes.apple.com/lookup",
                     params={"id": app_id, "country": "ro"}, headers=UA, timeout=25)
    r.raise_for_status()
    rez = r.json().get("results") or []
    return rez[0] if rez else None


def pagina_app(app_id):
    """Recenziile afișate și distribuția pe stele, de pe pagina publică.

    Nu din feed-ul RSS: robots.txt al itunes.apple.com îl interzice
    (`Disallow: /*/rss/*`, verificat 24.09.2026). Pagina `apps.apple.com` e
    permisă și conține datele serializate ale paginii (`serialized-server-data`):
    ~8 recenzii alese de Apple (nu neapărat cele mai recente) și numărul de
    note pe fiecare stea — o informație pe care feed-ul nici nu o avea.
    """
    import re
    url = f"https://apps.apple.com/{STOREFRONT}/app/id{app_id}"
    if not flux.permite(url, "apple"):
        return None, None, "interzis de robots.txt"
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    m = re.search(r'<script[^>]*id="serialized-server-data"[^>]*>(.*?)</script>',
                  r.content.decode("utf-8"), re.S)
    if not m:
        return [], None, "pagina nu are date serializate"
    recenzii, distributie = {}, None

    def cauta(o):
        nonlocal distributie
        if isinstance(o, dict):
            if o.get("$kind") == "Review" and o.get("id"):
                recenzii[o["id"]] = o
            if isinstance(o.get("ratingCounts"), list) and len(o["ratingCounts"]) == 5:
                distributie = [int(x) for x in o["ratingCounts"]]
            for v in o.values():
                cauta(v)
        elif isinstance(o, list):
            for v in o:
                cauta(v)

    cauta(json.loads(m.group(1)))
    return list(recenzii.values()), distributie, None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--banca", help="doar o bancă (slug)")
    a = ap.parse_args()

    config.incarca()
    err = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", write_through=True)
    sare = os.environ.get("MIP_SALT")
    if not sare:
        err.write("MIP_SALT nu e setat. Opresc: o sare implicită ar face "
                  "hash-urile reversibile prin dicționar de nume.\n")
        return 1

    with io.open(FISIER_ID, encoding="utf-8") as f:
        id_uri = json.load(f)
    if a.banca:
        id_uri = {k: v for k, v in id_uri.items() if k == a.banca}
    err.write(f"{len(id_uri)} bănci cu id de aplicație confirmat\n\n")

    raport = collections.Counter()
    with psycopg2.connect(N.dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT slug, id FROM banci")
            banci = dict(cur.fetchall())

            # Idempotență, dar NU pentru recenzii.
            #
            # Versiunea și capturile descriu STAREA de acum: se rescriu, fiindcă
            # ce era ieri nu mai e adevărat.
            #
            # Recenziile sunt ISTORIC și se acumulează. Prima versiune le
            # ștergea înainte de reîncărcare și a distrus date: feed-ul RSS al
            # Apple e capricios de la un apel la altul — Libra și ING
            # returnaseră 50 de recenzii fiecare, iar la reîncărcare zero.
            # Totalul a scăzut de la 218 la 112. O recenzie colectată o dată nu
            # trebuie să dispară pentru că feed-ul n-a răspuns a doua oară.
            #
            # Se bazează pe constrângerea unică existentă
            # (id_banca, platforma, storefront, autor_hash, postat_la), deci o
            # recenzie deja văzută nu se dublează.
            scop = "AND id_banca = ANY(%s)" if a.banca else ""
            p = ([banci[s] for s in id_uri if s in banci],) if a.banca else ()
            for tabel in ("app_screenshot", "app_release"):
                cur.execute(f"DELETE FROM {tabel} WHERE platforma = 'ios' {scop}", p)
                raport[f"sters_{tabel}"] += cur.rowcount

            for slug, info in sorted(id_uri.items()):
                if slug not in banci:
                    err.write(f"{slug:20s} -- bancă necunoscută în tabelă\n")
                    continue
                app_id = str(info["ios_app_id"])
                try:
                    app = lookup(app_id)
                except Exception as exc:
                    err.write(f"{slug:20s} -- lookup eșuat: {type(exc).__name__}\n")
                    raport["lookup_esuat"] += 1
                    time.sleep(PAUZA)
                    continue
                time.sleep(PAUZA)
                if not app:
                    err.write(f"{slug:20s} -- id {app_id} nu mai există în store\n")
                    raport["id_inexistent"] += 1
                    continue

                cur.execute(
                    """INSERT INTO app_release (id_banca, platforma, app_id, versiune,
                                                note_lansare, rating_agregat, volum_rating)
                       VALUES (%s, 'ios', %s, %s, %s, %s, %s)
                       ON CONFLICT DO NOTHING""",
                    (banci[slug], app_id, app.get("version"),
                     app.get("releaseNotes"), app.get("averageUserRating"),
                     app.get("userRatingCount")),
                )
                raport["versiuni"] += 1

                capturi = (app.get("screenshotUrls") or [])[:10]
                if capturi:
                    psycopg2.extras.execute_values(
                        cur,
                        "INSERT INTO app_screenshot (id_banca, platforma, url) VALUES %s",
                        [(banci[slug], "ios", u) for u in capturi],
                    )
                    raport["capturi"] += len(capturi)

                try:
                    intrari, distributie, motiv = pagina_app(app_id)
                except Exception as exc:
                    intrari, distributie, motiv = [], None, type(exc).__name__
                time.sleep(PAUZA)
                if distributie:
                    cur.execute("""UPDATE app_release SET distributie_stele = %s
                                   WHERE id_banca = %s AND platforma = 'ios'""",
                                (distributie, banci[slug]))
                valori = []
                for x in intrari or []:
                    try:
                        nota = int(x.get("rating"))
                    except (TypeError, ValueError):
                        continue
                    text = " — ".join(p for p in (x.get("title"), x.get("contents")) if p)
                    valori.append((
                        banci[slug], "ios", STOREFRONT, nota, text, None,
                        hash_autor(x.get("reviewerName"), sare), x.get("date"),
                        ((x.get("response") or {}).get("contents") or "").strip() or None,
                    ))
                n_rev = 0
                if valori:
                    psycopg2.extras.execute_values(
                        cur,
                        """INSERT INTO app_review (id_banca, platforma, storefront, rating,
                               text, versiune, autor_hash, postat_la, raspuns_banca)
                           VALUES %s ON CONFLICT DO NOTHING""",
                        valori,
                    )
                    n_rev = cur.rowcount if cur.rowcount >= 0 else len(valori)
                if motiv:
                    raport[f"pagina_{motiv}"] += 1
                raport["recenzii_noi"] += n_rev

                err.write(f"{slug:20s} v{str(app.get('version'))[:12]:14s} "
                          f"{app.get('averageUserRating') or '-'}★ "
                          f"{app.get('userRatingCount') or 0:>8} note · "
                          f"{len(capturi)} capturi · {n_rev} recenzii · "
                          f"stele {distributie or '-'}\n")

    N.raporteaza(raport, sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
