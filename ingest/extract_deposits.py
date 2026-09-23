"""
Extrage tipurile de depozit oferite de fiecare banca, folosind aceleasi
reguli de politeness ca scraper.py (robots.txt, User-Agent onest, delay).

Fara LLM: euristica pe HTML (headinguri, linkuri de meniu, regex pe text)
pentru a identifica nume de produse de tip depozit/cont de economii.
Best-effort -- pe site-uri foarte dinamice (JS-heavy) sau cu machete
neconventionale poate rata produse sau poate prinde fals-pozitive; de-aia
fiecare intrare vine cu URL-ul sursa, ca sa poata fi verificata manual.
"""

import argparse
import json
import os
import re
import sys
import time

from bs4 import BeautifulSoup

RADACINA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATE = os.path.join(RADACINA, "date")
sys.path.insert(0, RADACINA)

from banks import BANKS
from crawler.parser_rate import parseaza_linie
from scraper import (
    DELAY_BETWEEN_REQUESTS,
    crawl_bfs,
    fetch_page,
    known_block_reason,
    robots_allowed,
    strip_diacritics,
)

DEPOSIT_LINK_KEYWORDS = [
    "depozit", "depozite", "economii", "economisire", "saving", "savings",
]

# implicit: 2 niveluri de crawl BFS, max 18 pagini/banca (acelasi implicit ca
# in fetch_deposit_pages.py) -- suprascriere cu --max-depth / --max-pages.
DEFAULT_MAX_DEPTH = 2
DEFAULT_MAX_PAGES = 18

# regex-uri pentru nume de produs gen "Depozitul la Termen", "Cont de Economii Smart"
NAME_PATTERNS = [
    re.compile(
        r"Depozit(?:ul|ele|)?\s+(?:la\s+Termen|Online|Simplu|"
        r"[A-ZȚȘĂÂÎ][\wĂÂÎȚȘăâîțș]*(?:\s+[A-ZȚȘĂÂÎ0-9][\wĂÂÎȚȘăâîțș0-9+]*){0,3})",
        re.UNICODE,
    ),
    re.compile(
        r"Cont(?:ul)?\s+de\s+Economii(?:\s+[A-ZȚȘĂÂÎ][\wĂÂÎȚȘăâîțș]*){0,3}",
        re.UNICODE,
    ),
]

GENERIC_BLOCKLIST = {
    "depozit", "depozite", "depozitul", "depozitele", "cont de economii",
    "contul de economii",
}

# candidatii care sunt de fapt intrebari de FAQ sau firimituri de meniu/breadcrumb,
# nu nume de produs -- gasiti prin comparatie cu cercetarea independenta (vezi
# comparatie_scraper_vs_websearch.md). Verificam INCEPUTUL numelui normalizat: un nume
# de produs real nu incepe niciodata cu "cum ", "ce ", "mergi la" etc.
NOISE_START_PHRASES = (
    "mergi la", "vreau ", "cum ", "ce ", "de ce", "care este", "care sunt",
    "detalii despre", "detalii ", "aplica pentru", "cat ", "in ce", "pe ce",
    "unde ", "cine ", "daca ", "prin ce", "cati ", "cate ", "cum pot", "cum imi",
)
MAX_CUVINTE_NUME_PRODUS = 7


def is_noise_candidate(name: str) -> bool:
    if "?" in name:
        return True
    if len(name.split()) > MAX_CUVINTE_NUME_PRODUS:
        return True
    norm = strip_diacritics(name.lower()).strip()
    return norm.startswith(NOISE_START_PHRASES)


def extract_candidate_names(html: str, page_title: str | None) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(separator=" ", strip=True)

    candidates: dict[str, str] = {}

    # 1. headinguri h1-h4 care mentioneaza depozit/economii
    for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
        t = tag.get_text(strip=True)
        norm = strip_diacritics(t.lower())
        if t and 3 < len(t) < 80 and ("depozit" in norm or "economii" in norm):
            candidates.setdefault(t, "")

    # 2. linkuri de meniu/lista cu text scurt care mentioneaza depozit/economii
    for a in soup.find_all("a"):
        t = a.get_text(strip=True)
        norm = strip_diacritics(t.lower())
        if t and 3 < len(t) < 60 and ("depozit" in norm or "economii" in norm):
            candidates.setdefault(t, "")

    # 3. regex pe tot textul vizibil, pentru nume gen "Depozitul VISTA KIDS"
    for pattern in NAME_PATTERNS:
        for m in pattern.finditer(text):
            name = m.group(0).strip()
            if name:
                candidates.setdefault(name, "")

    # filtrare: elimina generice, elimina duplicate case-insensitive
    cleaned: dict[str, str] = {}
    for name in candidates:
        norm = strip_diacritics(name.lower()).strip()
        if norm in GENERIC_BLOCKLIST or is_noise_candidate(name):
            continue
        key = norm
        if key not in cleaned or len(name) > len(cleaned[key]):
            cleaned[key] = name

    results = []
    for norm_key, name in cleaned.items():
        idx = text.find(name)
        snippet = ""
        if idx != -1:
            start = max(0, idx)
            snippet = text[start: start + 220].strip()
        results.append({"nume": name, "context": snippet})

    if page_title:
        norm_title = strip_diacritics(page_title.lower())
        if ("depozit" in norm_title or "economii" in norm_title) and not any(
            strip_diacritics(r["nume"].lower()) == strip_diacritics(page_title.lower())
            for r in results
        ):
            results.insert(0, {"nume": page_title.strip(), "context": text[:220]})

    return results


def extract_rate_lines(html: str) -> list[str]:
    """Reconstruieste 'linii' de text pe care le poate citi parser_rate.py: un rand
    de tabel = celulele lui unite prin tab (asa cum se astepta parser-ul, ca sa
    poata citi si coloanele suplimentare de pe acelasi rand), plus restul textului
    vizibil, o linie pe bloc. get_text() cu un singur separator ar amesteca cele
    doua -- un rand de tabel ajuns text simplu isi pierde tab-urile dintre coloane.
    """
    soup = BeautifulSoup(html, "lxml")
    linii = []
    for tr in soup.find_all("tr"):
        celule = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        celule = [c for c in celule if c]
        if celule:
            linii.append("\t".join(celule))
    for bloc in soup.get_text(separator="\n").split("\n"):
        bloc = bloc.strip()
        if bloc:
            linii.append(bloc)
    return linii


def extract_rates(html: str, banca: str, url: str, page_title: str | None) -> list[dict]:
    gasite = []
    for linie in extract_rate_lines(html):
        if "%" not in linie:
            continue
        inregistrari, _problema = parseaza_linie(linie, banca, "depozite", url, page_title)
        gasite.extend(inregistrari)
    return gasite


def process_bank(bank: dict, max_depth: int = DEFAULT_MAX_DEPTH, max_pages: int = DEFAULT_MAX_PAGES) -> dict:
    name = bank["name"]
    base_url = bank["url"]
    out = {"name": name, "url": base_url, "status": None, "eroare": None, "produse": [], "dobanzi": [], "pagini_verificate": [], "robots_note": None}

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

    effective_delay = max(DELAY_BETWEEN_REQUESTS, crawl_delay or 0)

    home = fetch_page(base_url)
    if not home["ok"]:
        out["status"] = "ERROR"
        out["eroare"] = home["error"]
        return out

    home_soup = BeautifulSoup(home["html"], "lxml")

    home_title = home_soup.title.get_text(strip=True) if home_soup.title else None
    home_candidates = extract_candidate_names(home["html"], home_title)
    if home_candidates:
        out["pagini_verificate"].append(base_url)
        for c in home_candidates:
            out["produse"].append({**c, "sursa": base_url})
    out["dobanzi"].extend(extract_rates(home["html"], name, base_url, home_title))

    pages = crawl_bfs(
        home_soup, home["final_url"], DEPOSIT_LINK_KEYWORDS,
        max_depth=max_depth, max_pages=max_pages, delay=effective_delay,
    )
    for page in pages:
        sub_title = page["soup"].title.get_text(strip=True) if page["soup"].title else None
        out["pagini_verificate"].append(page["url"])
        for c in extract_candidate_names(page["html"], sub_title):
            out["produse"].append({**c, "sursa": page["url"]})
        out["dobanzi"].extend(extract_rates(page["html"], name, page["url"], sub_title))

    # dedup final pe nume normalizat (poate apare pe homepage si pe subpagina)
    dedup: dict[str, dict] = {}
    for p in out["produse"]:
        key = strip_diacritics(p["nume"].lower()).strip()
        if key not in dedup or len(p.get("context", "")) > len(dedup[key].get("context", "")):
            dedup[key] = p
    out["produse"] = list(dedup.values())

    # dedup dobanzi pe (tip_rata, valoare, moneda) -- acelasi numar apare des pe
    # homepage SI pe subpagina dedicata, si nu ne intereseaza de doua ori
    dedup_rate: dict[tuple, dict] = {}
    for r in out["dobanzi"]:
        key = (r["tip_rata"], r["valoare"], r.get("moneda"))
        if key not in dedup_rate:
            dedup_rate[key] = r
    out["dobanzi"] = list(dedup_rate.values())

    out["status"] = "OK" if out["produse"] else "OK_FARA_PRODUSE_GASITE"
    return out


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH,
                         help=f"adancime crawl BFS per banca (implicit {DEFAULT_MAX_DEPTH})")
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES,
                         help=f"nr. maxim de pagini gasite per banca (implicit {DEFAULT_MAX_PAGES})")
    return parser.parse_args()


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    args = parse_args()
    all_results = []
    for i, bank in enumerate(BANKS, 1):
        print(f"[{i}/{len(BANKS)}] {bank['name']}")
        try:
            res = process_bank(bank, max_depth=args.max_depth, max_pages=args.max_pages)
        except Exception as exc:
            res = {"name": bank["name"], "url": bank["url"], "status": "ERROR",
                   "eroare": f"{exc.__class__.__name__}: {exc}", "produse": [], "pagini_verificate": []}
        print(f"    status={res['status']} · produse gasite={len(res['produse'])} · dobanzi gasite={len(res.get('dobanzi', []))}")
        all_results.append(res)
        time.sleep(DELAY_BETWEEN_REQUESTS)

    with open(os.path.join(DATE, "rezultate_depozite.json"), "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    write_markdown(all_results)
    print("\nDone. Vezi date/rezultate_depozite.md si date/rezultate_depozite.json")


def write_markdown(results: list[dict]):
    lines = []
    lines.append("# Tipuri de depozite pe bănci din România (extracție euristică, fără LLM)\n")
    lines.append(
        "Extracție best-effort din headinguri, linkuri de meniu și pattern-uri de "
        "text de pe paginile publice. Nu e o listă garantat completă sau 100% "
        "corectă — verifică sursa listată la fiecare produs. Bănci blocate de "
        "robots.txt sau cu erori de fetch nu au fost forțate.\n"
    )
    ok = sum(1 for r in results if r["status"] in ("OK", "OK_FARA_PRODUSE_GASITE"))
    with_products = sum(1 for r in results if r["produse"])
    with_rates = sum(1 for r in results if r.get("dobanzi"))
    lines.append(f"**Total bănci:** {len(results)} · Accesibile: {ok} · Cu cel puțin un produs identificat: {with_products} · Cu cel puțin o dobândă identificată: {with_rates}\n")
    lines.append("---\n")

    for r in results:
        lines.append(f"## {r['name']}\n")
        lines.append(f"- **URL:** {r['url']}")
        if r["status"] in ("BLOCKED_ROBOTS", "ERROR"):
            lines.append(f"- **Status:** {r['status']} — {r.get('eroare')}")
            lines.append("")
            continue
        if not r["produse"]:
            lines.append("- **Status:** accesibil, dar nu s-a identificat niciun tip de depozit prin euristica curentă (posibil pagină needetectată sau conținut încărcat prin JS).")
            lines.append("")
            continue
        lines.append(f"- **Tipuri de depozit identificate ({len(r['produse'])}):**\n")
        lines.append("| Produs | Context (extras de pe pagină) | Sursă |")
        lines.append("|---|---|---|")
        for p in r["produse"]:
            context = (p.get("context") or "").replace("\n", " ").replace("|", "/")
            if len(context) > 180:
                context = context[:180] + "..."
            lines.append(f"| {p['nume']} | {context} | {p['sursa']} |")
        lines.append("")

        if r.get("dobanzi"):
            lines.append(f"- **Dobânzi identificate ({len(r['dobanzi'])}):**\n")
            lines.append("| Tip | Valoare | Monedă | Perioadă | Încredere | Text sursă |")
            lines.append("|---|---|---|---|---|---|")
            for d in sorted(r["dobanzi"], key=lambda d: -d["valoare"]):
                text_sursa = (d.get("text_sursa") or "").replace("\n", " ").replace("\t", " / ").replace("|", "/")
                if len(text_sursa) > 140:
                    text_sursa = text_sursa[:140] + "..."
                lines.append(
                    f"| {d['tip_rata']} | {d['valoare']}% | {d.get('moneda') or '-'} | "
                    f"{d.get('perioada') or '-'} | {d['incredere']} | {text_sursa} |"
                )
            lines.append("")

    with open(os.path.join(DATE, "rezultate_depozite.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
