"""Banda A1: găsește adresele unei bănci și le scrie în `surse`. Nicio cifră.

Figura 2 din artefact: descoperirea scrie DOAR în `surse`; extracția pornește
de acolo. Față de crawler/main.py (colegul), trei schimbări măsurate:

  - sitemap ∪ navigare, nu navigare doar când sitemap-ul e gol:
    `patriabank.ro/curs-valutar` există, dar lipsește din sitemap-ul de 624 de
    adrese; cursul valutar era găsit la 5 bănci din 23;
  - TOATE adresele clasificate se salvează, nu doar cele ≤80 vizitate;
  - fără „formular", „contact", „campanii", „atm", „sucursal" printre
    excluderi: prindeau formularul standardizat de comisioane și locatoarele.

Ca să nu extragem 2.565 de pagini la BCR, fiecare produs primește cel mult
MAX_PE_PRODUS pagini `activ`; restul intră `pauza`, vizibile în inventar.
Documentele (tarife) și locatoarele intră toate `activ`.
"""

import collections
import gzip
import re
from urllib.parse import urljoin, urlparse, urlunparse

import psycopg2
from bs4 import BeautifulSoup

import extractoare
import flux
import normalizeaza as N
import transport
from banks import BANKS

MAX_PE_PRODUS = 6
MAX_PAGINI_NAVIGARE = 40
MAX_COPII_SITEMAP = 50
ZGOMOT = ["blog", "news", "/stiri", "presa", "comunicat", "cariere", "csr", "cookie",
          "gdpr", "confidential", "protectia-datelor", "politica-de", "despre-noi",
          "investitori", "arhiva", "login", "autentificare", "fraud", "securitate",
          "reclamat", "sitemap", "rss", "/tag/", "/author/", "search", "?s=",
          "/press", "noutati",
          "mailto:", "tel:", "javascript:"]
RE_LOCATOR = re.compile(r"retea|unitati|agentii|sucursal|locati|harta|\batm\b|bancomat|"
                        r"branch|locator|find-us|puncte-de-lucru", re.I)
RE_DOCUMENT_TEXT = re.compile(r"\bpdf\b|descarc|download|lista de tarife|formular", re.I)
RE_DOCUMENT_URL = re.compile(r"\.pdf($|\?)|/dam/|/download|/documente?/", re.I)
RE_FISIER_NEUTIL = re.compile(r"\.(jpe?g|png|gif|svg|webp|zip|docx?|xlsx?|mp4|css|js)($|\?)", re.I)


def normalizeaza_url(url):
    p = urlparse(url.strip())
    cale = p.path.rstrip("/") or "/"
    interogare = "&".join(q for q in p.query.split("&") if q and not q.startswith("utm_"))
    return urlunparse((p.scheme, p.netloc.lower(), cale, "", interogare, ""))


def clasifica_adresa(url, text_link=""):
    jos = url.lower()
    if any(z in jos for z in ZGOMOT) or RE_FISIER_NEUTIL.search(jos):
        return None
    if RE_LOCATOR.search(urlparse(jos).path):
        return {"rol": "locator", "format": "html", "produs": None}
    e_document = bool(RE_DOCUMENT_URL.search(jos) or RE_DOCUMENT_TEXT.search(text_link or ""))
    categorie, produs, _ = extractoare.clasifica(url, text_link)
    if e_document:
        return {"rol": "conditii", "format": "pdf" if ".pdf" in jos else None,
                "produs": produs or "comisioane"}
    if not categorie:
        return None
    return {"rol": "produs", "format": "html", "produs": produs}


def _radacina(gazda):
    return ".".join((gazda or "").lower().split(".")[-2:])


def _pe_domeniu(url, baza):
    return _radacina(urlparse(url).netloc) == _radacina(urlparse(baza).netloc)


def din_sitemap(baza, slug, stare, raport):
    reguli = flux.reguli_pentru(baza, slug)
    de_citit = list(dict.fromkeys(reguli.sitemapuri + [urljoin(baza, "/sitemap.xml")]))
    vazute, gasite = set(), []
    while de_citit and len(vazute) < MAX_COPII_SITEMAP:
        u = de_citit.pop(0)
        if u in vazute:
            continue
        vazute.add(u)
        rez = transport.adu(u, slug, stare)
        if rez.verdict != "OK":
            raport[f"sitemap_{rez.verdict}"] += 1
            continue
        corp = rez.octeti
        if corp[:2] == b"\x1f\x8b":
            corp = gzip.decompress(corp)
        # Decodare tolerantă: sitemap-ul Raiffeisen nu e UTF-8 valid, iar o
        # decodare strictă întorcea zero adrese (colegul, crawler/main.py).
        text = corp.decode("utf-8", errors="replace")
        locuri = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", text)
        if "<sitemapindex" in text.lower():
            de_citit.extend(l for l in locuri if _pe_domeniu(l, baza))
        else:
            gasite.extend(l for l in locuri if _pe_domeniu(l, baza))
    if de_citit:
        raport["sitemap_copii_necitite"] += len(de_citit)   # nicio limită tăcută
    return [(u, "") for u in gasite]


def din_navigare(baza, slug, stare, raport):
    """BFS pe 2 niveluri. Linkurile se păstrează cu textul lor: „Lista de
    tarife (PDF)" spune ce e un link `/download?id=12`, adresa nu."""
    frontiera, vazute, gasite, pagini = [baza], {baza}, [], 0
    for _adancime in range(2):
        urmatoare = []
        for u in frontiera:
            if pagini >= MAX_PAGINI_NAVIGARE:
                raport["navigare_plafon_atins"] += 1
                break
            rez = transport.adu(u, slug, stare)
            pagini += 1
            if rez.verdict == "BLOCAT" and u == baza:
                stare["dovada_blocaj"] = rez.nota     # codul exact, ca dovadă
                return None                           # banca ne-a blocat
            if rez.verdict != "OK" or rez.octeti.startswith(b"%PDF"):
                continue
            soup = BeautifulSoup(rez.octeti, "lxml")
            for a in soup.find_all("a", href=True):
                l = urljoin(rez.url_final, a["href"]).split("#")[0]
                if not l.startswith("http") or l in vazute:
                    continue
                vazute.add(l)
                text = a.get_text(" ", strip=True)
                gasite.append((l, text))
                c = clasifica_adresa(l, text)
                if _pe_domeniu(l, baza) and c and c["rol"] in ("produs", "hub"):
                    urmatoare.append(l)
        frontiera = urmatoare
    return gasite


def ruleaza(err, raport, banca=None):
    stare = {}
    try:
        with psycopg2.connect(N.dsn()) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT nume, id FROM produse")
                produse = dict(cur.fetchall())
                cur.execute("SELECT nume, slug FROM banci")
                slug_dupa_nume = dict(cur.fetchall())
                for b in BANKS:
                    slug = slug_dupa_nume.get(b["name"])
                    if not slug:
                        raport["descoperire_banca_necunoscuta"] += 1
                        continue
                    if banca and slug != banca:
                        continue
                    ruleaza_banca(cur, slug, b["url"], produse, stare, err, raport)
                    conn.commit()
    finally:
        transport.inchide(stare)


def ruleaza_banca(cur, slug, url_banca, produse, stare, err, raport):
    nav = din_navigare(url_banca, slug, stare, raport)
    if nav is None:
        cur.execute(
            """INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda,
                   status, nota_extractie, frecventa)
               SELECT id, 'url', %s, 'hub', 'html', 'http', 'blocat', %s, 'lunar'
               FROM banci WHERE slug = %s
               ON CONFLICT DO NOTHING""",
            (url_banca, f"blocat de bancă la descoperire: {stare.get('dovada_blocaj')}"[:300],
             slug))
        err.write(f"  {slug:20s} BLOCAT — documentat, fără alt canal\n")
        raport["banci_blocate"] += 1
        return
    candidati = din_sitemap(url_banca, slug, stare, raport) + nav
    alese = {}
    for u, text in candidati:
        # Documentele pot sta pe CDN-ul grupului (BCR: cdn.erstegroup.com);
        # paginile, nu.
        if not _pe_domeniu(u, url_banca) and not RE_DOCUMENT_URL.search(u):
            continue
        c = clasifica_adresa(u, text)
        if c:
            alese.setdefault(normalizeaza_url(u), c)
    pe_produs = collections.Counter()
    for u, c in alese.items():
        activ = c["rol"] != "produs" or pe_produs[c["produs"]] < MAX_PE_PRODUS
        if c["rol"] == "produs" and activ:
            pe_produs[c["produs"]] += 1
        cur.execute(
            """INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda,
                   status, frecventa, nota_extractie)
               SELECT id, 'url', %s, %s, %s, 'http', %s, 'lunar', %s
               FROM banci WHERE slug = %s
               ON CONFLICT DO NOTHING RETURNING id""",
            (u, c["rol"], c["format"], "activ" if activ else "pauza",
             None if activ else "descoperit, peste plafonul pe produs", slug))
        r = cur.fetchone()
        if r and c["produs"] in produse:
            cur.execute("INSERT INTO surse_produse (id_sursa, id_produs) VALUES (%s, %s)",
                        (r[0], produse[c["produs"]]))
    n_activ = sum(1 for c in alese.values() if c["rol"] != "produs") + sum(pe_produs.values())
    err.write(f"  {slug:20s} {len(alese):5d} adrese · {n_activ:4d} active\n")
    raport["surse_descoperite"] += len(alese)
    raport["surse_active"] += n_activ
