"""
Pasul 1 dintr-un pipeline de extractie mai robust pentru tipuri de depozit.

Nu mai incearca sa "ghiceasca" nume de produse prin regex/headinguri (asta
producea multe fals-pozitive -- orice mentiune a cuvantului "depozit" intr-un
meniu, FAQ sau footer era prinsa ca "produs"). In schimb:

  1. Gaseste paginile relevante pentru depozite, cu un crawl BFS pe mai multe
     niveluri (nu doar linkuri de pe homepage -- vezi crawl_bfs in scraper.py).
  2. Descarca fiecare pagina, respectand robots.txt + politeness (ca in
     scraper.py).
  3. Curata HTML-ul: scoate nav/header/footer/script/style/form/svg/iframe
     (zgomot de meniu, cookie-banner, formulare de lead) INAINTE de a extrage
     textul, nu dupa.
  4. Salveaza textul curat, complet (nu trunchiat), intr-un JSON.

Pasul 2 (structurarea reala -- nume de produs, conditii, dobanzi) se face de
catre Claude citind acest JSON, nu de un regex. Asta e partea "cu Claude in
spate" ceruta initial: intelegerea semantica e facuta de model, nu de pattern
matching pe text brut.
"""

import argparse
import json
import os
import sys
import time

from bs4 import BeautifulSoup

from banks import BANKS
from scraper import DELAY_BETWEEN_REQUESTS, crawl_bfs, fetch_page, known_block_reason, robots_allowed

sys.stdout.reconfigure(encoding="utf-8")

DEPOSIT_LINK_KEYWORDS = [
    "depozit", "depozite", "economii", "economisire", "saving", "savings",
]

NOISE_TAGS = ["script", "style", "noscript", "nav", "header", "footer", "svg", "iframe", "form", "button"]

# implicit: 2 niveluri de crawl BFS, max 18 pagini/banca -- suprascriere cu
# --max-depth / --max-pages daca o banca are nevoie de acoperire diferita.
DEFAULT_MAX_DEPTH = 2
DEFAULT_MAX_PAGES = 18


def clean_main_text(html: str) -> str:
    import re
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(NOISE_TAGS):
        tag.decompose()
    # NOTA: am incercat initial sa eliminam si div-uri cu "cookie"/"gdpr" in id
    # (cookie-banner) dar unele site-uri (ex. Nexent Bank) au un div numit
    # "cookie-block-new" care contine de fapt tot continutul real al paginii --
    # filtrul acela stergea aproape tot. Ne limitam la tag-urile semantice de
    # mai sus, care sunt un semnal mult mai sigur.
    main = soup.find("main") or soup.find(attrs={"role": "main"}) or soup.find("article") or soup.body or soup
    text = main.get_text(separator=" ", strip=True)
    text = re.sub(r"\s{2,}", " ", text)
    return text


def process_bank(bank: dict, max_depth: int = DEFAULT_MAX_DEPTH, max_pages: int = DEFAULT_MAX_PAGES) -> dict:
    name = bank["name"]
    base_url = bank["url"]
    out = {"name": name, "url": base_url, "status": None, "eroare": None, "pagini": [], "robots_note": None}

    known_reason = known_block_reason(bank)
    if known_reason:
        out["status"] = "SKIP_KNOWN_BLOCKED"
        out["eroare"] = known_reason
        return out

    robots_status, reason, crawl_delay = robots_allowed(base_url)
    if robots_status == "disallow":
        out["status"] = "BLOCKED_ROBOTS"
        out["eroare"] = reason
        return out
    if robots_status == "unknown_waf":
        out["robots_note"] = reason

    # respectam Crawl-delay declarat de sursa, daca e mai mare decat implicitul
    effective_delay = max(DELAY_BETWEEN_REQUESTS, crawl_delay or 0)

    home = fetch_page(base_url)
    if not home["ok"]:
        out["status"] = "ERROR"
        out["eroare"] = home["error"]
        return out

    home_soup = BeautifulSoup(home["html"], "lxml")
    pages = crawl_bfs(
        home_soup, home["final_url"], DEPOSIT_LINK_KEYWORDS,
        max_depth=max_depth, max_pages=max_pages, delay=effective_delay,
    )

    for page in pages:
        title = page["soup"].title.get_text(strip=True) if page["soup"].title else None
        clean_text = clean_main_text(page["html"])
        out["pagini"].append({"url": page["url"], "titlu": title, "text_curat": clean_text})

    out["status"] = "OK" if out["pagini"] else "OK_FARA_PAGINI_GASITE"
    return out


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH,
                         help=f"adancime crawl BFS per banca (implicit {DEFAULT_MAX_DEPTH})")
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES,
                         help=f"nr. maxim de pagini gasite per banca (implicit {DEFAULT_MAX_PAGES})")
    return parser.parse_args()


def main():
    args = parse_args()
    all_results = []
    for i, bank in enumerate(BANKS, 1):
        print(f"[{i}/{len(BANKS)}] {bank['name']}")
        try:
            res = process_bank(bank, max_depth=args.max_depth, max_pages=args.max_pages)
        except Exception as exc:
            res = {"name": bank["name"], "url": bank["url"], "status": "ERROR",
                   "eroare": f"{exc.__class__.__name__}: {exc}", "pagini": [], "robots_note": None}
        n_pages = len(res.get("pagini", []))
        total_chars = sum(len(p["text_curat"]) for p in res.get("pagini", []))
        print(f"    status={res['status']} · pagini={n_pages} · caractere_totale={total_chars}")
        all_results.append(res)
        time.sleep(DELAY_BETWEEN_REQUESTS)

    iesire = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "date", "pagini_depozite_raw.json")
    with open(iesire, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print("\nDone. Vezi date/pagini_depozite_raw.json -- urmatorul pas e citirea/structurarea de catre Claude.")


if __name__ == "__main__":
    main()
