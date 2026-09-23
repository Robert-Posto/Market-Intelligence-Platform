"""
Interogheaza iTunes Lookup API (itunes.apple.com/lookup) pentru metadate publice
despre o aplicatie din App Store: versiune, rating, numar de review-uri,
screenshot-uri, data ultimei lansari.

Fara autentificare, fara scraping de HTML -- e API-ul oficial Apple. Numele e
istoric ("itunes"), dar acopera App Store-ul (nu doar muzica) prin parametrul
entity=software, folosit implicit de lookup cand dai un id de aplicatie.

Politeness: Apple documenteaza ~20 cereri/minut/IP ca limita implicita
(developer.apple.com/forums/thread/68923). Delay-ul de mai jos e conservator
sub limita, nu la limita.
"""

import json
import os
import time

import requests

USER_AGENT = (
    "LibraBank-MarketIntel-Test/0.1 "
    "(test personal, doar date publice; contact: robert.postolache@librabank.ro)"
)
LOOKUP_URL = "https://itunes.apple.com/lookup"
DELAY_BETWEEN_REQUESTS = 3.0
DATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "date")

# id-urile confirmate de cauta_app_id.py (slug din `banci` -> app), nu ghicite;
# aplicatiile altor piete ale grupului sunt deja respinse acolo
with open(os.path.join(DATE, "app_id_gasite.json"), encoding="utf-8") as _f:
    APPS = [{"slug": s, "ios_app_id": a["ios_app_id"]} for s, a in json.load(_f).items()]

CAMPURI_UTILE = [
    "trackName", "sellerName", "version", "currentVersionReleaseDate",
    "releaseNotes", "averageUserRating", "userRatingCount",
    "averageUserRatingForCurrentVersion", "userRatingCountForCurrentVersion",
    "price", "currency", "minimumOsVersion", "screenshotUrls",
    "artworkUrl512", "trackViewUrl",
]


def lookup_app(app_id: int, country: str = "ro") -> dict:
    resp = requests.get(
        LOOKUP_URL,
        params={"id": app_id, "country": country},
        headers={"User-Agent": USER_AGENT},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("resultCount", 0) == 0:
        return {"gasit": False}
    rezultat = data["results"][0]
    extras = {c: rezultat.get(c) for c in CAMPURI_UTILE}
    extras["gasit"] = True
    return extras


def main():
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    toate = []
    for i, app in enumerate(APPS, 1):
        print(f"[{i}/{len(APPS)}] {app['slug']} (id={app['ios_app_id']})")
        info = lookup_app(app["ios_app_id"])
        info["slug"] = app["slug"]
        info["ios_app_id"] = app["ios_app_id"]
        if info.get("gasit"):
            print(
                f"    {info.get('trackName')} v{info.get('version')} · "
                f"{info.get('averageUserRating')}★ ({info.get('userRatingCount')} review-uri) · "
                f"lansat {info.get('currentVersionReleaseDate')}"
            )
        else:
            print("    NEGASIT")
        toate.append(info)
        time.sleep(DELAY_BETWEEN_REQUESTS)

    iesire = os.path.join(DATE, "rezultate_app_store.json")
    with open(iesire, "w", encoding="utf-8") as f:
        json.dump(toate, f, ensure_ascii=False, indent=2)
    print("\nDone. Vezi date/rezultate_app_store.json")


if __name__ == "__main__":
    main()
