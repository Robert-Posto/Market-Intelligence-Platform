"""
candidati_produse.py — paginile de produs ale unei bănci, fără model (pașii 1–2).

    python candidati_produse.py --banca bcr        # listează candidații, nu scrie nimic

De unde: sitemap-urile băncii (cele din robots.txt și cele din surse_produse.json)
și linkurile din paginile de meniu (`start`). Ce rămâne: pagini pe domeniul băncii,
permise de robots.txt, care nu arată a articol / campanie / suport și care nu sunt
deja surse ale celor 57 de produse Libra (acelea se compară în comparatie_libra).

Regula echipei: 401 / 403 / 429 / 451 la robots.txt sau la o pagină = banca e
blocată, iar colectarea se oprește. Nu se încearcă alt canal.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urldefrag, urlparse
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree

AICI = Path(__file__).parent
sys.path.insert(0, str(AICI))

import search_data_by_source as S                 # noqa: E402  (încarcă flow-html.py)
from targetedCrawl import domenii_permise, incarca_banca   # noqa: E402

fh = S.fh
DSN = os.environ.get("MIP_DSN", "host=localhost port=5432 dbname=mip user=mip password=mip")
SURSE = json.loads((AICI / "surse_produse.json").read_text(encoding="utf-8"))
EXCLUSE = re.compile(SURSE["excluse_comune"], re.I)
EXCLUSE_ORIUNDE = re.compile(SURSE.get("excluse_oriunde") or "(?!)", re.I)
FISIERE = re.compile(r"\.(pdf|jpe?g|png|gif|svg|webp|zip|docx?|xlsx?|mp4|css|js|xml|ico)$", re.I)
COD_BLOCAJ = {401, 403, 429, 451}
MAX_SITEMAPURI = 40           # un sitemapindex poate trimite la sute de fișiere (arhive pe luni)
PAUZA_S = 0.5                 # între cereri către aceeași bancă


class Blocat(Exception):
    """Banca răspunde cu 401/403/429/451: se documentează ca blocată, nu se ocolește."""


def normalizeaza_url(u: str) -> str:
    u = urldefrag(u)[0].split("?")[0]
    return u.rstrip("/") if urlparse(u).path not in ("", "/") else u


async def adu(url: str):
    r = await fh.adu_http(url, timeout=30, follow_redirects=True)
    if r.status_code in COD_BLOCAJ:
        raise Blocat(f"{r.status_code} la {url}")
    await asyncio.sleep(PAUZA_S)
    return r


class Robots:
    """
    robots.txt pe fiecare origine (regula MIP: „inclusiv CDN-ul de documente”), citit o
    dată și consultat ÎNAINTE de orice cerere: sitemap, meniu, pagină. La ING, de
    exemplu, `Disallow: *.xml` interzice chiar sitemap.xml. 404 = totul permis;
    401/403/429/451 = banca e blocată.
    """
    def __init__(self):
        self._rp: dict[str, RobotFileParser] = {}
        self.sitemapuri: list[str] = []

    async def permis(self, url: str) -> bool:
        u = urlparse(url)
        origine = f"{u.scheme}://{u.netloc}"
        if origine not in self._rp:
            rp = RobotFileParser()
            r = await adu(f"{origine}/robots.txt")
            linii = r.text.splitlines() if r.status_code == 200 else []
            rp.parse(linii)
            self._rp[origine] = rp
            self.sitemapuri += [l.split(":", 1)[1].strip() for l in linii if l.lower().startswith("sitemap:")]
        return self._rp[origine].can_fetch(fh.UA, url)


async def din_sitemap(url: str, vazute: set[str], rb: Robots) -> list[tuple[str, str]]:
    """<loc>-urile unui sitemap; un sitemapindex se parcurge recursiv, până la MAX_SITEMAPURI."""
    if url in vazute or len(vazute) >= MAX_SITEMAPURI or not await rb.permis(url):
        return []
    vazute.add(url)
    r = await adu(url)
    if r.status_code != 200:
        return []
    try:
        radacina = ElementTree.fromstring(r.content)
    except ElementTree.ParseError:
        return []
    loc = [e.text.strip() for e in radacina.iter() if e.tag.endswith("loc") and e.text]
    if radacina.tag.endswith("sitemapindex"):
        out = []
        for u in loc:
            out += await din_sitemap(u, vazute, rb)
        return out
    return [(u, "") for u in loc]


class _Linkuri(HTMLParser):
    def __init__(self):
        super().__init__()
        self.linkuri, self._href, self._text = [], None, []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href, self._text = dict(attrs).get("href"), []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href:
            self.linkuri.append((self._href, " ".join("".join(self._text).split())))
            self._href = None


async def din_meniu(url: str, rb: Robots) -> list[tuple[str, str]]:
    """Linkurile dintr-o pagină de meniu, cu textul lor (titlul candidatului)."""
    if not await rb.permis(url):
        return []
    r = await adu(url)
    if r.status_code != 200:
        return []
    p = _Linkuri()
    p.feed(r.text)
    return [(urljoin(url, h), t) for h, t in p.linkuri]


def deja_libra(slug: str) -> set[str]:
    """URL-urile care sunt deja surse ale celor 57 de produse Libra la banca asta."""
    import psycopg2
    with psycopg2.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("""SELECT s.url FROM surse_libra s JOIN banci b ON b.id = s.id_banca
                        WHERE b.slug = %s AND NOT s.not_found AND s.url IS NOT NULL""", (slug,))
        return {normalizeaza_url(u) for (u,) in cur.fetchall()}


async def candidati(slug: str) -> dict:
    """
    @returns {"candidati": [{"url", "titlu", "din"}], "statistica": {...}} sau
             {"blocat": "<motiv>"} când banca refuză accesul.
    """
    banca = incarca_banca(slug)
    conf = SURSE["banci"].get(slug) or {"start": [banca["url"]], "sitemap": [], "sectiuni": []}
    domenii = domenii_permise(banca)
    # domeniul real al băncii e cel din paginile de start: www.ing.ro (din banci.json)
    # răspunde 403, ing.ro răspunde 200 — e același site, nu un alt canal
    u0 = urlparse((conf.get("start") or [banca["url"]])[0])
    baza = f"{u0.scheme}://{u0.netloc}"
    rb = Robots()
    try:
        await rb.permis(f"{baza}/")             # citește robots.txt-ul de bază (și sitemap-urile lui)
        brute: dict[str, tuple[str, str]] = {}
        vazute: set[str] = set()
        for sm in dict.fromkeys(rb.sitemapuri + conf.get("sitemap", [])):
            for u, t in await din_sitemap(sm, vazute, rb):
                brute.setdefault(normalizeaza_url(u), (t, "sitemap"))
        for st in conf.get("start", []):
            for u, t in await din_meniu(st, rb):
                n = normalizeaza_url(u)
                if n not in brute or not brute[n][0]:
                    brute[n] = (t, "meniu")
    except Blocat as e:
        return {"blocat": str(e)}

    libra = deja_libra(slug)
    # sub try: verificarea robots de mai jos poate citi robots.txt-ul unui subdomeniu nou
    try:
        return await _filtreaza(brute, domenii, conf, libra, rb, len(vazute))
    except Blocat as e:
        return {"blocat": str(e)}


async def _filtreaza(brute, domenii, conf, libra, rb, n_sitemapuri) -> dict:
    sectiuni = conf.get("sectiuni") or []
    motive = {"domeniu": 0, "fisier": 0, "exclus": 0, "sectiune": 0, "robots": 0, "deja_libra": 0}
    out = []
    for u, (titlu, din) in brute.items():
        p = urlparse(u)
        host = p.netloc.lower().split(":")[0]
        if not p.scheme.startswith("http") or not any(host == d or host.endswith("." + d) for d in domenii):
            motive["domeniu"] += 1
        elif FISIERE.search(p.path):
            motive["fisier"] += 1
        elif EXCLUSE.search(p.path) or EXCLUSE_ORIUNDE.search(p.path) or p.path.endswith("/pdf"):
            motive["exclus"] += 1
        elif sectiuni and not any(p.path.startswith(s) or (p.path + "/").startswith(s) for s in sectiuni):
            motive["sectiune"] += 1
        elif not await rb.permis(u):
            motive["robots"] += 1
        elif u in libra:
            motive["deja_libra"] += 1
        elif p.path.strip("/").count("/") < 1:
            motive["sectiune"] += 1        # rădăcina și paginile de secțiune nu sunt produse
        else:
            out.append({"url": u, "titlu": titlu, "din": din})
    return {"candidati": sorted(out, key=lambda c: c["url"]),
            "statistica": {"adrese_brute": len(brute), "candidati": len(out), "scoase": motive,
                           "sitemapuri_citite": n_sitemapuri}}


def main() -> None:
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass
    a = argparse.ArgumentParser(description="Paginile de produs ale unei bănci, fără model.")
    a.add_argument("--banca", required=True)
    arg = a.parse_args()
    r = asyncio.run(candidati(arg.banca))
    if r.get("blocat"):
        sys.exit(f"{arg.banca}: blocat — {r['blocat']}")
    print(json.dumps(r["statistica"], ensure_ascii=False))
    for c in r["candidati"]:
        print(f"  [{c['din']:7}] {c['url']}  {c['titlu'][:60]}")


if __name__ == "__main__":
    main()
