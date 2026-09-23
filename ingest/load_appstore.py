"""Genereaza SQL pentru track-ul mobil iOS: versiuni, screenshot-uri, review-uri.

Surse:
  rezultate_app_store.json  (Desktop/Scraping) - iTunes Lookup API, 3 banci
  feed RSS de review-uri    - cerut live, per storefront

PSEUDONIMIZARE, obligatorie: feed-ul RSS al Apple intoarce numele real de
afisare al autorului (verificat: "Tiara ... Tiara" la un test de control). Nu
se stocheaza niciodata brut - se scrie doar un hash cu sare (`autor_hash`),
conform regulii din secțiunea 1 a PDF-ului de arhitectura.

Sarea vine din variabila de mediu MIP_SALT. Fara ea scriptul se opreste: o
sare implicita ar face hash-urile reversibile prin dictionar, adica
pseudonimizare doar de forma.

Idempotent: sterge intai randurile iOS pe care le rescrie.
"""

import hashlib
import io
import json
import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402

FISIER_LOOKUP = os.path.join(
    os.path.expanduser("~"), "Desktop", "Scraping", "rezultate_app_store.json"
)

# numele din rezultate_app_store.json -> slug din tabelul `banci`
SLUG_BANCA = {
    "Libra Internet Bank": "libra",
    "ING Bank (HomeBank)": "ing",
    "BCR (George Romania)": "bcr",
}

STOREFRONTS = ("ro", "us")

USER_AGENT = (
    "LibraBank-MarketIntel-Test/0.1 "
    "(test personal, doar date publice; contact: robert.postolache@librabank.ro)"
)
DELAY = 3.0


def sql_text(v):
    if v is None:
        return "NULL"
    return "'" + str(v).replace("'", "''") + "'"


def sql_num(v):
    return "NULL" if v is None else repr(float(v))


def hash_autor(nume, sare):
    return hashlib.sha256((sare + "|" + (nume or "")).encode("utf-8")).hexdigest()[:32]


def review_uri(app_id, storefront):
    url = (
        f"https://itunes.apple.com/{storefront}/rss/customerreviews/"
        f"id={app_id}/sortby=mostrecent/json"
    )
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
    r.raise_for_status()
    entries = (r.json().get("feed") or {}).get("entry") or []
    # cand feed-ul are un singur review, Apple intoarce un obiect, nu o lista;
    # fara normalizare, iterarea da cheile dictionarului, nu review-ul
    if isinstance(entries, dict):
        entries = [entries]
    return entries


def main():
    config.incarca()
    sare = os.environ.get("MIP_SALT")
    if not sare:
        sys.stderr.write(
            "MIP_SALT nu e setat. Opresc: o sare implicita ar face hash-urile "
            "reversibile prin dictionar de nume, adica pseudonimizare doar de forma.\n"
        )
        return 1

    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n")
    err = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

    with io.open(FISIER_LOOKUP, encoding="utf-8") as f:
        apps = json.load(f)

    out.write("BEGIN;\n")
    out.write("DELETE FROM app_screenshot WHERE platforma = 'ios';\n")
    out.write("DELETE FROM app_review     WHERE platforma = 'ios';\n")
    out.write("DELETE FROM app_release    WHERE platforma = 'ios';\n\n")

    n_rel = n_shot = n_rev = 0
    for app in apps:
        if not app.get("gasit"):
            err.write(f"sarit (negasit): {app.get('banca')}\n")
            continue
        slug = SLUG_BANCA.get(app.get("banca"))
        if not slug:
            err.write(f"sarit (slug nemapat): {app.get('banca')}\n")
            continue
        app_id = str(app["ios_app_id"])

        out.write(
            "INSERT INTO app_release (id_banca, platforma, app_id, versiune, "
            "note_lansare, rating_agregat, volum_rating)\n"
            f"SELECT b.id, 'ios', {sql_text(app_id)}, {sql_text(app.get('version'))}, "
            f"{sql_text(app.get('releaseNotes'))}, {sql_num(app.get('averageUserRating'))}, "
            f"{app.get('userRatingCount') or 'NULL'}\n"
            f"FROM banci b WHERE b.slug = {sql_text(slug)}\nON CONFLICT DO NOTHING;\n"
        )
        n_rel += 1

        for url in app.get("screenshotUrls") or []:
            out.write(
                "INSERT INTO app_screenshot (id_banca, platforma, url)\n"
                f"SELECT b.id, 'ios', {sql_text(url)} FROM banci b "
                f"WHERE b.slug = {sql_text(slug)}\nON CONFLICT DO NOTHING;\n"
            )
            n_shot += 1

        for sf in STOREFRONTS:
            try:
                entries = review_uri(app_id, sf)
            except Exception as exc:
                err.write(f"RSS {slug}/{sf} a picat: {exc.__class__.__name__}: {exc}\n")
                continue
            err.write(f"RSS {slug}/{sf}: {len(entries)} review-uri cu text\n")
            for e in entries:
                autor = ((e.get("author") or {}).get("name") or {}).get("label")
                rating = ((e.get("im:rating") or {}).get("label"))
                versiune = ((e.get("im:version") or {}).get("label"))
                text = ((e.get("content") or {}).get("label"))
                titlu = ((e.get("title") or {}).get("label"))
                postat = ((e.get("updated") or {}).get("label"))
                corp = " — ".join(x for x in [titlu, text] if x)
                out.write(
                    "INSERT INTO app_review (id_banca, platforma, storefront, rating, "
                    "versiune, text, autor_hash, postat_la)\n"
                    f"SELECT b.id, 'ios', {sql_text(sf)}, "
                    f"{int(rating) if rating and rating.isdigit() else 'NULL'}, "
                    f"{sql_text(versiune)}, {sql_text(corp[:2000] or None)}, "
                    f"{sql_text(hash_autor(autor, sare))}, "
                    f"{('TIMESTAMPTZ ' + sql_text(postat)) if postat else 'NULL'}\n"
                    f"FROM banci b WHERE b.slug = {sql_text(slug)}\nON CONFLICT DO NOTHING;\n"
                )
                n_rev += 1
            time.sleep(DELAY)

    out.write("COMMIT;\n")
    out.flush()
    err.write(f"\nversiuni: {n_rel} | screenshot-uri: {n_shot} | review-uri: {n_rev}\n")
    err.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
