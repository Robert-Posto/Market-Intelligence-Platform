"""
Scraper simplu, fara LLM, pentru testarea a ce informatii publice se pot
obtine de pe site-urile bancilor din Romania listate in banks.py.

Spike personal de test, NELEGAT de proiectul oficial "Market Intelligence
Platform" (documentul intern Libra). Reguli de politeness aplicate, in
spiritul sectiunii 1 din document:
  - doar pagini publice, fara autentificare
  - robots.txt verificat per sursa; daca interzice -> nu se face fetch
  - User-Agent onest, cu contact
  - o singura cerere pe banca (homepage) + fallback pe linkuri relevante
    gasite pe homepage (max cateva), cu delay intre cereri
  - fara rezolvare de captcha/WAF, fara proxy, fara spoofing de browser
  - daca sursa blocheaza (403/429/etc.) -> marcam BLOCKED si ne oprim, nu ocolim
"""

import json
import os
import re
import sys
import time
import unicodedata
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from banks import BANKS
from robots_matcher import can_fetch, get_crawl_delay, parse as parse_robots

# consola Windows foloseste cp1252 by default, care nu are diacritice RO
sys.stdout.reconfigure(encoding="utf-8")

USER_AGENT = (
    "LibraBank-MarketIntel-Test/0.1 "
    "(test personal, doar date publice; contact: robert.postolache@librabank.ro)"
)
REQUEST_TIMEOUT = 10
DELAY_BETWEEN_REQUESTS = 1.5
MAX_RELEVANT_LINKS_TO_FOLLOW = 2
SNIPPET_LENGTH = 500
DATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "date")

KEYWORDS = [
    "dobanzi", "dobinzi", "tarife", "comisioane", "comision", "credit",
    "credite", "depozit", "depozite", "economii", "dae", "rate",
    "cont-curent", "contul-curent", "card", "ipotecar", "refinantare",
]

HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "ro,en;q=0.8"}


def strip_diacritics(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


_KNOWN_BLOCK_LABELS = {
    "waf_blocat": "blocat integral de WAF",
    "timeout": "timeout la conectare",
    "robots_disallow_all": "robots.txt interzice tot accesul",
    "domeniu_abandonat": "domeniu abandonat/neactualizat",
}


def known_block_reason(bank: dict) -> str | None:
    """Daca banca are un `acces_cunoscut` deja confirmat in banks.py (WAF,
    timeout, robots disallow all etc.), returneaza un motiv lizibil pentru
    status SKIP_KNOWN_BLOCKED -- altfel None.

    Scopul e sa nu mai irosim cereri (si buget de politeness) pe surse deja
    stiute ca inaccesibile prin fetch simplu.
    """
    acces = bank.get("acces_cunoscut")
    if not acces:
        return None
    motiv = _KNOWN_BLOCK_LABELS.get(acces, acces)
    sursa = bank.get("sursa_info")
    return f"{motiv} ({sursa})" if sursa else motiv


def robots_allowed(url: str) -> tuple[str, str, float | None]:
    """Returneaza (status, motiv, crawl_delay). status e unul din:
    - "allow": robots.txt citit cu succes, permite fetch-ul
    - "disallow": robots.txt citit cu succes, interzice explicit fetch-ul
    - "unknown_waf": nu s-a putut CITI robots.txt (ex. 401/403 de la un WAF) --
      nu e o interdictie de continut, e o blocare de retea pe cererea catre
      robots.txt insasi. Tratam implicit 401/403 ca "disallow all" ar fi
      inselator -- de-aia facem fetch-ul manual aici, cu requests + acelasi
      User-Agent onest, ca sa distingem cele doua cazuri.

    Potrivirea tiparelor Allow/Disallow foloseste robots_matcher (RFC 9309),
    nu urllib.robotparser din biblioteca standard -- acesta din urma face doar
    potrivire pe prefix simplu si rateaza complet tipare cu wildcard, ex.
    `Disallow: *.pdf` (vezi test_robots_matcher.py).

    crawl_delay e valoarea declarata explicit de sursa in directiva
    "Crawl-delay" (dacã exista), altfel None -- apelantul decide cum o combina
    cu propriul delay implicit (de obicei max(implicit, crawl_delay)).
    """
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        resp = requests.get(robots_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.RequestException as exc:
        return "allow", f"robots.txt inaccesibil ({exc.__class__.__name__}), presupunem allow", None

    if resp.status_code in (401, 403):
        return "unknown_waf", f"robots.txt nu a putut fi citit (HTTP {resp.status_code}, posibil WAF) -- nu e o interdictie explicita de continut", None
    if resp.status_code == 404:
        return "allow", "robots.txt inexistent (404), presupunem allow", None
    if not resp.ok:
        return "allow", f"robots.txt inaccesibil (HTTP {resp.status_code}), presupunem allow", None

    try:
        rules = parse_robots(resp.text)
        allowed = can_fetch(rules, USER_AGENT, parsed.path or "/")
        crawl_delay = get_crawl_delay(rules, USER_AGENT)
    except Exception:
        allowed = True
        crawl_delay = None
    return (
        ("allow" if allowed else "disallow"),
        ("ok" if allowed else "interzis explicit de robots.txt"),
        crawl_delay,
    )


def find_relevant_links(soup: BeautifulSoup, base_url: str, keywords: list[str] | None = None) -> list[str]:
    keywords = keywords if keywords is not None else KEYWORDS
    found = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = strip_diacritics((a.get_text() or "").lower())
        href_lower = strip_diacritics(href.lower())
        if any(kw in href_lower or kw in text for kw in keywords):
            absolute = urljoin(base_url, href)
            if absolute not in seen and absolute.startswith("http"):
                seen.add(absolute)
                found.append(absolute)
    return found


def fetch_page(url: str) -> dict:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
    except requests.exceptions.RequestException as exc:
        return {"ok": False, "error": f"{exc.__class__.__name__}: {exc}"}

    if resp.status_code in (403, 429, 401, 503):
        return {"ok": False, "error": f"HTTP {resp.status_code} (posibil bloc WAF/anti-bot)"}
    if not resp.ok:
        return {"ok": False, "error": f"HTTP {resp.status_code}"}

    content_type = resp.headers.get("Content-Type", "")
    if "html" not in content_type and "text" not in content_type:
        return {"ok": False, "error": f"Content-Type neasteptat: {content_type}"}

    # requests presupune ISO-8859-1 cand header-ul Content-Type nu declara
    # explicit charset-ul (cazul frecvent la site-uri RO care il declara doar
    # in <meta charset> din HTML). apparent_encoding detecteaza din bytes, e
    # mult mai de incredere aici -- fara asta ies pagini cu text corupt
    # (mojibake), ex. Garanti BBVA, Bank of China.
    if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = resp.apparent_encoding

    return {"ok": True, "status_code": resp.status_code, "final_url": resp.url, "html": resp.text}


def crawl_bfs(
    home_soup: BeautifulSoup,
    home_url: str,
    keywords: list[str],
    max_depth: int = 2,
    max_pages: int = 18,
    delay: float = DELAY_BETWEEN_REQUESTS,
    fetch=fetch_page,
    check_robots=robots_allowed,
    sleep=time.sleep,
) -> list[dict]:
    """BFS pe mai multe niveluri, pornind de la pagina principala (deja
    descarcata de apelant -- nu o cerem a doua oara aici). Urmareste doar
    linkuri al caror text/href contine unul din `keywords`, respecta
    robots.txt si `delay` intre cereri, si se opreste la `max_depth` niveluri
    sau `max_pages` pagini gasite (ce vine primul).

    Inainte, fiecare script (scraper.py, fetch_deposit_pages.py,
    extract_deposits.py) se uita doar la linkurile de pe homepage (1 nivel) --
    asta e cea mai mare lacuna de descoperire semnalata pe site-urile fara
    sitemap. crawl_bfs inlocuieste acele bucle 1-nivel duplicate.

    Returneaza paginile descarcate cu succes, in ordinea descoperirii (BFS):
    [{"url", "final_url", "html", "soup"}, ...]. Pagina principala nu e
    inclusa -- apelantul o are deja.
    """
    visited = {home_url}
    found: list[dict] = []
    frontier = find_relevant_links(home_soup, home_url, keywords)
    depth = 1

    while frontier and depth <= max_depth and len(found) < max_pages:
        next_frontier: list[str] = []
        for link in frontier:
            if link in visited:
                continue
            visited.add(link)

            sleep(delay)
            status, _reason, _crawl_delay = check_robots(link)
            if status == "disallow":
                continue
            fetched = fetch(link)
            if not fetched["ok"]:
                continue

            soup = BeautifulSoup(fetched["html"], "lxml")
            found.append({
                "url": link,
                "final_url": fetched["final_url"],
                "html": fetched["html"],
                "soup": soup,
            })
            if len(found) >= max_pages:
                break
            if depth < max_depth:
                next_frontier.extend(find_relevant_links(soup, fetched["final_url"], keywords))

        frontier = next_frontier
        depth += 1

    return found[:max_pages]


def scrape_bank(bank: dict) -> dict:
    name = bank["name"]
    url = bank["url"]
    result = {
        "name": name,
        "url": url,
        "note_initiala": bank.get("note", ""),
        "status": None,
        "titlu": None,
        "meta_descriere": None,
        "linkuri_relevante": [],
        "pagini_secundare": [],
        "fragment_text": None,
        "eroare": None,
        "robots_note": None,
        "crawl_delay_folosit": None,
    }

    reason = known_block_reason(bank)
    if reason:
        result["status"] = "SKIP_KNOWN_BLOCKED"
        result["eroare"] = reason
        return result

    robots_status, robots_reason, robots_crawl_delay = robots_allowed(url)
    if robots_status == "disallow":
        result["status"] = "BLOCKED_ROBOTS"
        result["eroare"] = robots_reason
        return result
    if robots_status == "unknown_waf":
        # robots.txt insusi n-a putut fi citit (WAF) -- nu inseamna interdictie
        # de continut; incercam totusi fetch-ul paginii, care isi va da singur
        # verdictul (posibil acelasi WAF blocheaza si pagina, ceea ce e ERROR
        # legitim, nu BLOCKED_ROBOTS).
        result["robots_note"] = robots_reason

    # daca sursa declara explicit un Crawl-delay mai mare decat implicitul
    # nostru, il respectam -- politeness real, nu doar de forma
    effective_delay = max(DELAY_BETWEEN_REQUESTS, robots_crawl_delay or 0)
    result["crawl_delay_folosit"] = effective_delay

    fetched = fetch_page(url)
    if not fetched["ok"]:
        result["status"] = "ERROR"
        result["eroare"] = fetched["error"]
        return result

    soup = BeautifulSoup(fetched["html"], "lxml")
    result["status"] = "OK"
    result["titlu"] = soup.title.get_text(strip=True) if soup.title else None
    meta = soup.find("meta", attrs={"name": "description"})
    result["meta_descriere"] = meta.get("content", "").strip() if meta else None
    text = soup.get_text(separator=" ", strip=True)
    result["fragment_text"] = text[:SNIPPET_LENGTH]

    relevant_links = find_relevant_links(soup, fetched["final_url"])
    result["linkuri_relevante"] = relevant_links[:10]

    for sub_url in relevant_links[:MAX_RELEVANT_LINKS_TO_FOLLOW]:
        time.sleep(effective_delay)
        sub_status, sub_reason, _sub_crawl_delay = robots_allowed(sub_url)
        if sub_status == "disallow":
            result["pagini_secundare"].append({"url": sub_url, "status": "BLOCKED_ROBOTS", "eroare": sub_reason})
            continue
        sub_fetched = fetch_page(sub_url)
        if not sub_fetched["ok"]:
            result["pagini_secundare"].append({"url": sub_url, "status": "ERROR", "eroare": sub_fetched["error"]})
            continue
        sub_soup = BeautifulSoup(sub_fetched["html"], "lxml")
        sub_text = sub_soup.get_text(separator=" ", strip=True)
        result["pagini_secundare"].append({
            "url": sub_url,
            "status": "OK",
            "titlu": sub_soup.title.get_text(strip=True) if sub_soup.title else None,
            "fragment_text": sub_text[:SNIPPET_LENGTH],
        })

    return result


def main():
    results = []
    for i, bank in enumerate(BANKS, 1):
        print(f"[{i}/{len(BANKS)}] {bank['name']} -> {bank['url']}")
        try:
            res = scrape_bank(bank)
        except Exception as exc:
            res = {
                "name": bank["name"], "url": bank["url"], "note_initiala": bank.get("note", ""),
                "status": "ERROR", "eroare": f"Exceptie neprevazuta: {exc.__class__.__name__}: {exc}",
                "titlu": None, "meta_descriere": None, "linkuri_relevante": [],
                "pagini_secundare": [], "fragment_text": None,
            }
        print(f"    status={res['status']}")
        results.append(res)
        time.sleep(DELAY_BETWEEN_REQUESTS)

    with open(os.path.join(DATE, "rezultate_scraper_banci.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    write_markdown_summary(results)
    print("\nDone. Vezi date/rezultate_scraper_banci.md si date/rezultate_scraper_banci.json")


def write_markdown_summary(results: list[dict]):
    ok = sum(1 for r in results if r["status"] == "OK")
    blocked = sum(1 for r in results if r["status"] == "BLOCKED_ROBOTS")
    error = sum(1 for r in results if r["status"] == "ERROR")

    lines = []
    lines.append("# Rezultate scraper — bănci din România (test spike, fără LLM)\n")
    lines.append(
        "Test personal, exploratoriu — NELEGAT de proiectul oficial "
        "\"Market Intelligence Platform\" (documentul intern DRAFT, nesemnat de "
        "Juridic + DPO). Scop: să vedem ce date publice sunt accesibile printr-un "
        "fetch simplu și respectuos (robots.txt respectat, User-Agent onest, un "
        "request pe secundă pe domeniu, fără evaziune la blocaje).\n"
    )
    lines.append(f"**Total bănci verificate:** {len(results)} · OK: {ok} · Blocate de robots.txt: {blocked} · Erori/blocaje: {error}\n")
    lines.append("---\n")

    for r in results:
        lines.append(f"## {r['name']}\n")
        lines.append(f"- **URL:** {r['url']}")
        lines.append(f"- **Status:** {r['status']}")
        if r.get("note_initiala"):
            lines.append(f"- **Notă inițială:** {r['note_initiala']}")
        if r["status"] != "OK":
            lines.append(f"- **Motiv:** {r.get('eroare', 'necunoscut')}")
            lines.append("")
            continue
        if r.get("titlu"):
            lines.append(f"- **Titlu pagină:** {r['titlu']}")
        if r.get("meta_descriere"):
            lines.append(f"- **Descriere meta:** {r['meta_descriere']}")
        if r.get("linkuri_relevante"):
            lines.append(f"- **Linkuri relevante găsite** (produse/dobânzi/tarife etc.):")
            for link in r["linkuri_relevante"]:
                lines.append(f"  - {link}")
        else:
            lines.append("- **Linkuri relevante găsite:** niciunul (pe baza cuvintelor-cheie folosite)")
        if r.get("fragment_text"):
            snippet = r["fragment_text"].replace("\n", " ")
            lines.append(f"- **Fragment text homepage:** {snippet}...")
        if r.get("pagini_secundare"):
            lines.append("- **Pagini secundare urmărite:**")
            for sub in r["pagini_secundare"]:
                if sub["status"] == "OK":
                    sub_snippet = (sub.get("fragment_text") or "").replace("\n", " ")
                    lines.append(f"  - {sub['url']} — titlu: {sub.get('titlu')}")
                    lines.append(f"    - fragment: {sub_snippet}...")
                else:
                    lines.append(f"  - {sub['url']} — {sub['status']}: {sub.get('eroare')}")
        lines.append("")

    with open(os.path.join(DATE, "rezultate_scraper_banci.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
