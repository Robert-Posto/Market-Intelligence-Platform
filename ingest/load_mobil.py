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

Idempotent, fără ștergeri: nimic din ce s-a colectat nu dispare la rularea
următoare. Versiunile și capturile se actualizează (upsert) și poartă
`vazut_ultima`; starea de acum e în vederile `app_release_curente` și
`app_screenshot_curente` (migrarea 026). Recenziile se acumulează — feed-ul
Apple e capricios de la un apel la altul, iar o recenzie colectată o dată nu
trebuie să dispară pentru că a doua cerere n-a răspuns.

Rețea: fiecare cerere trece prin `transport.adu` (robots.txt pe fiecare
adresă și pe fiecare redirect, origine BLOCAT, coada pe origine, oprire la
429), ca restul colectării. Lookup-ul e UN singur apel grupat pentru toate
aplicațiile (19 id-uri întorc resultCount 19, Nicolae §4.5), nu câte unul.

Cere migrarea 026 (`descriere`, `vazut_ultima`).

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

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AICI))
sys.path.insert(0, AICI)
import config                      # noqa: E402
import normalizeaza as N           # noqa: E402
import transport                   # noqa: E402

FISIER_ID = os.path.join(os.path.dirname(AICI), "date", "app_id_gasite.json")

# O singură vitrină, `ro`: colegul a măsurat că recenziile din vitrina `us`
# ale Citibank și Revolut sunt 0% în română (aplicații globale, clienți străini).
STOREFRONT = "ro"

PAUZA = 3.0          # o cerere la 3 s spre Apple
# Identitatea din jurnalul robots.txt (`flux.salveaza_robots`): originile
# Apple nu sunt ale vreunei bănci.
PROPRIETAR = "apple"


def hash_autor(nume, sare):
    return hashlib.sha256((sare + "|" + (nume or "")).encode("utf-8")).hexdigest()[:32]


class Refuzat(Exception):
    """Transportul n-a adus octeții: robots.txt, origine BLOCAT, 4xx/5xx."""


def _adu(url, stare):
    r = transport.adu(url, PROPRIETAR, stare)
    if r.verdict != "OK":
        raise Refuzat(f"{r.verdict}: {r.nota}")
    return r.octeti


def lookup_grupat(id_uri, stare):
    """Toate aplicațiile într-un singur apel Lookup: {id (text): rezultat}.

    `/lookup?` e permis; doar `/*/lookup?` (cu țara în cale) e interzis.
    Un id care lipsește din răspuns nu mai există în magazin.
    """
    if not id_uri:
        return {}
    url = ("https://itunes.apple.com/lookup?id=" + ",".join(str(i) for i in id_uri)
           + f"&country={STOREFRONT}")
    rez = json.loads(_adu(url, stare)).get("results") or []
    return {str(x.get("trackId")): x for x in rez if x.get("trackId")}


def pagina_app(app_id, stare):
    """Recenziile afișate și distribuția pe stele, de pe pagina publică.

    Nu din feed-ul RSS: robots.txt al itunes.apple.com îl interzice
    (`Disallow: /*/rss/*`, verificat 24.09.2026). Pagina `apps.apple.com` e
    permisă și conține datele serializate ale paginii (`serialized-server-data`):
    ~8 recenzii alese de Apple (nu neapărat cele mai recente) și numărul de
    note pe fiecare stea — o informație pe care feed-ul nici nu o avea.
    """
    import re
    url = f"https://apps.apple.com/{STOREFRONT}/app/id{app_id}"
    try:
        octeti = _adu(url, stare)
    except Refuzat as exc:
        return None, None, str(exc)[:80]
    m = re.search(r'<script[^>]*id="serialized-server-data"[^>]*>(.*?)</script>',
                  octeti.decode("utf-8"), re.S)
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


def scrie_versiune(cur, id_banca, app_id, app):
    """Upsert pe (id_banca, platforma, versiune); întoarce id-ul rândului.

    Versiunea de ieri rămâne, cu ultimele valori văzute (rating, volum), iar
    `vazut_ultima` spune până când a fost cea din magazin. Înainte, un DELETE
    pe toate rândurile iOS la fiecare rulare ștergea istoricul (Nicolae,
    §10.1 punctul 5).
    """
    cur.execute(
        """INSERT INTO app_release (id_banca, platforma, app_id, versiune, note_lansare,
                                    descriere, rating_agregat, volum_rating, vazut_ultima)
           VALUES (%s, 'ios', %s, %s, %s, %s, %s, %s, now())
           ON CONFLICT (id_banca, platforma, versiune) DO UPDATE SET
               app_id         = EXCLUDED.app_id,
               note_lansare   = COALESCE(EXCLUDED.note_lansare, app_release.note_lansare),
               descriere      = COALESCE(EXCLUDED.descriere, app_release.descriere),
               rating_agregat = COALESCE(EXCLUDED.rating_agregat, app_release.rating_agregat),
               volum_rating   = COALESCE(EXCLUDED.volum_rating, app_release.volum_rating),
               vazut_ultima   = now()
           RETURNING id""",
        (id_banca, app_id, app.get("version"), app.get("releaseNotes"),
         app.get("description"), app.get("averageUserRating"), app.get("userRatingCount")),
    )
    return cur.fetchone()[0]


def scrie_capturi(cur, id_banca, capturi):
    """Upsert pe (id_banca, platforma, url): o captură care nu mai apare
    rămâne, cu `vazut_ultima` de la ultima rulare care a văzut-o."""
    # Același URL de două ori în lot ar opri tot INSERT-ul: ON CONFLICT nu
    # poate atinge un rând de două ori în aceeași comandă.
    capturi = list(dict.fromkeys(capturi))
    if capturi:
        psycopg2.extras.execute_values(
            cur,
            """INSERT INTO app_screenshot (id_banca, platforma, url, vazut_ultima) VALUES %s
               ON CONFLICT (id_banca, platforma, url) DO UPDATE SET vazut_ultima = now()""",
            [(id_banca, "ios", u) for u in capturi],
            template="(%s, %s, %s, now())",
        )
    return len(capturi)


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
    stare = {}
    try:
        with psycopg2.connect(N.dsn()) as conn:
            with conn.cursor() as cur:
                if not _are_migrarea_026(cur):
                    err.write("Lipsește migrarea 026 (db/migration_026_aplicatii.sql). Opresc.\n")
                    return 1
                cur.execute("SELECT slug, id FROM banci")
                banci = dict(cur.fetchall())
                for slug in sorted(set(id_uri) - set(banci)):
                    err.write(f"{slug:20s} -- bancă necunoscută în tabelă\n")
                id_uri = {s: v for s, v in id_uri.items() if s in banci}
                try:
                    aplicatii = lookup_grupat([v["ios_app_id"] for v in id_uri.values()], stare)
                except (Refuzat, ValueError) as exc:
                    # Fără Lookup nu se scrie nimic; ce e în bază rămâne neatins.
                    err.write(f"lookup eșuat: {str(exc)[:200]}\n")
                    raport["lookup_esuat"] += 1
                    id_uri, aplicatii = {}, {}
                time.sleep(PAUZA)
                for slug, info in sorted(id_uri.items()):
                    _o_banca(cur, err, raport, stare, sare, slug, banci[slug],
                             str(info["ios_app_id"]), aplicatii)
    finally:
        transport.inchide(stare)

    N.raporteaza(raport, sys.stderr)
    return 0


def _are_migrarea_026(cur):
    cur.execute("""SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'app_release' AND column_name = 'descriere'""")
    return cur.fetchone() is not None


def _o_banca(cur, err, raport, stare, sare, slug, id_banca, app_id, aplicatii):
    app = aplicatii.get(app_id)
    if not app:
        err.write(f"{slug:20s} -- id {app_id} nu mai există în store\n")
        raport["id_inexistent"] += 1
        return
    id_release = scrie_versiune(cur, id_banca, app_id, app)
    raport["versiuni"] += 1
    n_capturi = scrie_capturi(cur, id_banca, (app.get("screenshotUrls") or [])[:10])
    raport["capturi"] += n_capturi

    # Recenziile sunt ISTORIC și se acumulează. Prima versiune le ștergea
    # înainte de reîncărcare și a distrus date: feed-ul RSS al Apple e
    # capricios — Libra și ING returnaseră 50 de recenzii fiecare, iar la
    # reîncărcare zero; totalul a scăzut de la 218 la 112. Constrângerea unică
    # (id_banca, platforma, storefront, autor_hash, postat_la) oprește dublurile.
    try:
        intrari, distributie, motiv = pagina_app(app_id, stare)
    except Exception as exc:
        intrari, distributie, motiv = [], None, type(exc).__name__
    time.sleep(PAUZA)
    if distributie:
        # Doar pe versiunea de acum: cele vechi păstrează distribuția din
        # ultima zi în care au fost văzute.
        cur.execute("UPDATE app_release SET distributie_stele = %s WHERE id = %s",
                    (distributie, id_release))
    valori = []
    for x in intrari or []:
        try:
            nota = int(x.get("rating"))
        except (TypeError, ValueError):
            continue
        text = " — ".join(p for p in (x.get("title"), x.get("contents")) if p)
        valori.append((
            id_banca, "ios", STOREFRONT, nota, text, None,
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
              f"{n_capturi} capturi · {n_rev} recenzii · "
              f"stele {distributie or '-'}\n")


if __name__ == "__main__":
    sys.exit(main())
