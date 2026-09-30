"""Colectorul de campanii și de comunicate de presă (pagina 2.4), de pe
site-urile băncilor. Planul e al lui Nicolae (NICOLAE_CHERASCU_MARKETING.md,
§4.1 și §4.3); configurația pe bancă e în `campanii_config.py`.

Doar site-urile băncilor: fără Wayback, Common Crawl, agregatoare sau presă.
Fără LLM: extracția e deterministă (`campanii_extractie.py`), iar ce nu se
citește sigur ajunge „de verificat" (`normalizeaza_campanii.py`).

TOATE cererile trec prin `transport.adu`, care aplică deja, înainte de orice
cerere: curățarea URL-ului, excluderile (câștigători, onboarding,
previzualizare, recomandări), robots.txt pe fiecare pas de redirect, BLOCAT
pe origine, coada pe origine și Crawl-delay. Aici nu există alt canal.

Componentele, în ordinea din §4.1 (cererile sunt ale componentei):
  1. Bronze — documentele de campanie deja aduse de popularea de prețuri: 0
  2. sitemap — adresele cu cuvinte de campanie (BRD: rădăcina recentă)
  3. huburi și indexuri de regulamente, din config
  4. legăturile de conținut din pagina principală și din paginile de segment
  5. paginile-listă găsite în sitemap, pe huburi sau în `surse`, citite ca hub
  (6, sitemap cu lastmod în 90 de zile: neimplementat, experiment separat)

Filtrele: treapta A — nu se cer huburile de arhivă, adresele cu „încheiat /
arhivă" în cale și adresele din sitemap cu lastmod mai vechi de 12 luni (se
jurnalizează în loguri/campanii/, nu se pierd). Treapta B e în normalizare.

Ce se scrie: `campanii`, `campanii_surse`, `comunicate` (migrarea 019) și
sursele documentelor în `surse`, cu rol 'campanie' / 'comunicat'. Octeții în
`bronze/campanii/` și `bronze/comunicate/`, amprenta în `campanii_surse` /
`comunicate`, NU în `hashes` (condiția din §4.3). Nimic în `observations`.

Rulare (din rădăcina repo-ului):
    python ingest/campanii.py --simulare                   # fără nicio cerere
    python ingest/campanii.py --simulare --newsroom
    python ingest/campanii.py --doar-bronze                # fără rețea
    python ingest/campanii.py --banca raiffeisen           # o bancă, cu rețea
    python ingest/campanii.py                              # toate băncile
    python ingest/campanii.py --newsroom [--banca bcr] [--corp-luni 24]
"""

import argparse
import collections
import datetime
import glob
import gzip
import hashlib
import io
import json
import os
import re
import sys
from urllib.parse import unquote, urljoin, urlparse

AICI = os.path.dirname(os.path.abspath(__file__))
RADACINA = os.path.dirname(AICI)
sys.path.insert(0, RADACINA)
sys.path.insert(0, AICI)

import campanii_config as K        # noqa: E402
import campanii_extractie as E     # noqa: E402
import flux                        # noqa: E402
import normalizeaza_campanii as NC  # noqa: E402
import transport                   # noqa: E402

LOGURI = os.path.join(RADACINA, "loguri", "campanii")
BRONZE_CAMPANII = os.path.join(flux.BRONZE, "campanii")
BRONZE_COMUNICATE = os.path.join(flux.BRONZE, "comunicate")

# Plasă de siguranță, nu plafon de acoperire: Nicolae a scos plafonul de 600
# (§4.1), fiindcă după treapta A descărcările BCR scad de la 370 la 170. Dacă
# o bancă îl atinge, se scrie în jurnal și în raport — nicio limită tăcută.
MAX_CERERI_BANCA = 400
MAX_COPII_SITEMAP = 25
MAX_LISTE = 10
ZILE_TREAPTA_A = 365
PAUZA_IMPLICITA = 2       # RegulliRobots.delay_implicit; transport nu coboară sub 1,5 s

# Cuvintele de campanie din cale: aceleași ca în vederea `observatii_din_campanii`
# (migrările 023 și 025), plus paginile ING `/lp/`.
RE_CAMPANIE_URL = re.compile(
    r"campani|campaign|campain|promoti|\bpromo\b|concurs|oferta-special|oferte-special"
    r"|castig[ai]\b|premii\b|premiaz|bonus-\d|rate-fara-dobanda|tombol|regulament"
    r"|landing-pages/lcp-|/lp/")
RE_CAMPANIE_TEXT = re.compile(
    r"campani|promoti|\bpromo\b|concurs|tombol|castig[ai]\b|castigi\b|premii\b|premiaz|cashback"
    r"|\bbonus\b|voucher|reducere|discount|rate\s+fara\s+dobanda|fara\s+comision"
    r"|dobanda\s+promotional|oferta\s+special|cadou|\bgratuit")
RE_REGULAMENT = re.compile(r"regulament|act[-_ ]?aditional|addendum|termeni[-_ ]si[-_ ]conditii[-_ ]campani")
RE_ACT = re.compile(r"act[-_ ]?aditional|addendum|prelungire|\baa\d")
RE_ARHIVA = re.compile(r"incheiat|finalizat|arhiv|ended|closed|expirat")
# O pagină-listă are un nume scurt („campanii-in-parteneriat", „promotii-carduri-
# business"); „oferte-de-black-friday-la-creditele-de-consum-..." (BRD) e un articol.
RE_LISTA = re.compile(r"(?:^|/)(?:campanii|campaigns?|promotii|promotions|oferte|ofertele)"
                      r"(?:-[a-z0-9]+){0,4}(?:\.html)?/?$")
RE_FISIER_NEUTIL = re.compile(r"\.(jpe?g|png|gif|svg|webp|zip|docx?|xlsx?|mp4|css|js)$")
RE_COPIL_SITEMAP_INUTIL = re.compile(r"image|video|author|tag|categor|attachment|product")
RE_URLSET = re.compile(r"<url>(.*?)</url>", re.S | re.I)
RE_LOC = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.I)
RE_LASTMOD = re.compile(r"<lastmod>\s*(\d{4}-\d{2}-\d{2})", re.I)


def normalizeaza_url(url):
    """Aceeași formă ca adresele din `surse` (descoperire.normalizeaza_url),
    ca documentele din Bronze să se regăsească."""
    import descoperire
    return descoperire.normalizeaza_url(url)


def cale_norm(url):
    """Calea, decodată, fără diacritice, cu litere mici — pe ea rulează tiparele."""
    return E._fara_diacritice_1la1(unquote(unquote(urlparse(url).path or "/")))


def e_document(url):
    c = cale_norm(url) + "?" + urlparse(url).query.lower()
    return bool(re.search(r"\.pdf(\?|$)|/dam/|displaydocumentlibraryfile|/upload/media/document/", c))


def origine(url):
    return flux.origine_din(url)


class Context:
    """Ce se știe despre o bancă, fără stare de rulare (folosit și offline)."""

    def __init__(self, slug, cfg):
        self.slug, self.cfg = slug, cfg
        self.baza = normalizeaza_url(cfg["baza"])
        gazde = cfg.get("gazde") or [urlparse(cfg["baza"]).netloc.lower()]
        self.gazde = set(gazde) | {g[4:] if g.startswith("www.") else "www." + g for g in gazde}
        self.gazde_doc = set(cfg.get("gazde_doc", []))
        self.sari = [re.compile(x) for x in K.SARI_IMPLICIT]
        self.nume = cfg.get("nume", ())
        self.grup = cfg.get("grup", ())
        # paginile din config nu sunt campanii, chiar dacă un hub le leagă
        # (Raiffeisen: hub-ul leagă /campanii-promotionale/2026.html)
        self.pagini_config = {normalizeaza_url(u) for u in [cfg["baza"]] + [
            x for k in ("segmente", "huburi", "regulamente", "arhive") for x in cfg.get(k, [])]}

    def pe_site(self, url, doc=False):
        g = urlparse(url).netloc.lower()
        return g in self.gazde or (doc and g in self.gazde_doc)

    def sarit(self, url):
        c = cale_norm(url)
        return any(r.search(c) for r in self.sari)


def _prefix(url):
    c = re.sub(r"\.html?$", "", cale_norm(url).rstrip("/"))
    return c + "/" if len(c) > 1 else None


def candidati_din_pagina(octeti, url_pagina, ctx, provenienta, strict=False):
    """(candidați, pagini-listă) dintr-o pagină deja adusă.

    Pe un hub (strict=False) intră copiii căii hub-ului, orice adresă sau
    text cu cuvinte de campanie și regulamentele. Pe pagina principală și pe
    segmente (strict=True), doar adresele și textele de campanie din conținut,
    fără meniu: altfel meniul ar aduce toate produsele băncii.
    """
    prefix = None if strict else _prefix(url_pagina)
    proprie = normalizeaza_url(url_pagina)
    cand, liste = [], []
    for u, text in E.linkuri(octeti, url_pagina, doar_continut=strict):
        u = normalizeaza_url(u)
        cale, t = cale_norm(u), E._fara_diacritice_1la1(text)
        doc = e_document(u)
        if u == proprie or u in ctx.pagini_config or RE_FISIER_NEUTIL.search(cale):
            continue
        if not ctx.pe_site(u, doc) or ctx.sarit(u):
            continue
        if doc:
            ok = bool(RE_REGULAMENT.search(cale + " " + t) or RE_CAMPANIE_URL.search(cale)
                      or RE_CAMPANIE_TEXT.search(t))
        else:
            if RE_LISTA.search(cale) and not RE_ARHIVA.search(cale):
                liste.append(u)
                continue
            ok = bool((prefix and cale.startswith(prefix)) or RE_CAMPANIE_URL.search(cale)
                      or RE_CAMPANIE_TEXT.search(t))
        if ok:
            rol = ("act_aditional" if RE_ACT.search(cale + " " + t) else "regulament") if doc else "landing"
            cand.append({"url": u, "rol": rol, "eticheta": text or None,
                         "url_hub": proprie, "provenienta": provenienta})
    return cand, liste


def parseaza_sitemap(corp):
    """(copii, [(loc, lastmod)]) — copiii dacă e index, intrările dacă e urlset."""
    if corp[:2] == b"\x1f\x8b":
        corp = gzip.decompress(corp)
    # decodare tolerantă: sitemap-ul Raiffeisen nu e UTF-8 valid (descoperire.py)
    text = corp.decode("utf-8", errors="replace")
    if "<sitemapindex" in text.lower():
        return RE_LOC.findall(text), []
    intrari = []
    for bloc in RE_URLSET.findall(text):
        loc = RE_LOC.search(bloc)
        if loc:
            lm = RE_LASTMOD.search(bloc)
            intrari.append((loc.group(1), datetime.date.fromisoformat(lm.group(1)) if lm else None))
    return [], intrari


def alege_din_sitemap(intrari, ctx, data_rulare):
    """(candidați, pagini-listă, amânate) după filtrul băncii și treapta A."""
    filtru = ctx.cfg.get("filtru_sitemap", "campanie")
    limita = data_rulare - datetime.timedelta(days=ZILE_TREAPTA_A)
    cand, liste, amanate = [], [], []
    for loc, lastmod in intrari:
        u = normalizeaza_url(loc)
        doc = e_document(u)
        if not ctx.pe_site(u, doc) or ctx.sarit(u):
            continue
        cale = cale_norm(u)
        if RE_LISTA.search(cale) and not RE_ARHIVA.search(cale) and not doc:
            liste.append(u)
            continue
        radacina = cale.strip("/") and "/" not in cale.strip("/")
        potrivit = RE_CAMPANIE_URL.search(cale) or (
            filtru == "radacina_recenta" and radacina and lastmod and lastmod >= limita)
        if not potrivit:
            continue
        if RE_ARHIVA.search(cale):
            amanate.append((u, "arhivă în cale (treapta A)"))
        elif lastmod and lastmod < limita:
            amanate.append((u, f"lastmod {lastmod} mai vechi de 12 luni (treapta A)"))
        else:
            rol = ("act_aditional" if RE_ACT.search(cale) else "regulament") if doc else "landing"
            cand.append({"url": u, "rol": rol, "eticheta": None, "url_hub": None,
                         "provenienta": "sitemap"})
    return cand, liste, amanate


def amprenta(octeti):
    """sha256 pe octeți (PDF) sau pe textul sanitizat (HTML), ca la prețuri:
    un token de sesiune nu schimbă amprenta. Stă în `campanii_surse`, nu în
    `hashes`."""
    import sanitizare
    date = octeti if octeti.startswith(b"%PDF") else sanitizare.text_sanitizat(octeti).encode("utf-8")
    return hashlib.sha256(date).hexdigest()


def scrie_bronze(director, url, octeti):
    os.makedirs(director, exist_ok=True)
    cale = os.path.join(director, os.path.basename(flux.cale_bronze(url)))
    with open(cale, "wb") as f:
        f.write(octeti)
    return os.path.relpath(cale, RADACINA)


# ==========================================================================
# Datele offline: Bronze și `surse` (doar citire)
# ==========================================================================

def documente_bronze(cur, slug):
    """Documentele de campanie aduse deja de popularea de prețuri (componenta
    1): URL cu cuvânt de campanie, amprentă în `hashes`, fișier în Bronze."""
    cur.execute(
        """SELECT s.sursa, max(h.created_at) FROM surse s
           JOIN banci b ON b.id = s.id_banca JOIN hashes h ON h.id_sursa = s.id
           WHERE b.slug = %s AND s.tip_sursa = 'url' GROUP BY s.sursa ORDER BY s.sursa""", (slug,))
    iesire = []
    for url, vazut in cur.fetchall():
        if RE_CAMPANIE_URL.search(cale_norm(url)) and not re.search(r"^/en(/|$)", cale_norm(url)):
            cale = flux.cale_bronze(url)
            if os.path.exists(cale):
                iesire.append((url, vazut, cale))
    return iesire


def liste_din_surse(cur, slug):
    """Paginile-listă de campanii deja știute în `surse` (componenta 5)."""
    cur.execute("""SELECT s.sursa FROM surse s JOIN banci b ON b.id = s.id_banca
                   WHERE b.slug = %s AND s.tip_sursa = 'url' ORDER BY length(s.sursa)""", (slug,))
    return [u for (u,) in cur.fetchall()
            if RE_LISTA.search(cale_norm(u)) and not RE_ARHIVA.search(cale_norm(u))
            and not e_document(u)]


# ==========================================================================
# O bancă, cu rețea (sau doar din Bronze)
# ==========================================================================

class Colector:
    def __init__(self, slug, cfg, moment, jurnal, max_cereri=MAX_CERERI_BANCA, retea=True):
        self.ctx = Context(slug, cfg)
        self.slug, self.cfg, self.moment = slug, cfg, moment
        self.data = moment.date()
        self.jurnal, self.max_cereri, self.retea = jurnal, max_cereri, retea
        self.stare = {}
        self.cereri = 0
        self.docs = {}
        self.membri = collections.defaultdict(list)
        self.provenienta = {}
        self.semnal = {}
        self.raport = collections.Counter()

    # ---------------------------------------------------------------- jurnal
    def noteaza(self, **kw):
        kw = {"data": self.moment.isoformat(timespec="seconds"), "banca": self.slug, **kw}
        self.jurnal.write(json.dumps(kw, ensure_ascii=False, default=str) + "\n")
        if kw.get("decizie"):
            self.raport[kw["decizie"]] += 1

    def blocata(self):
        return bool(flux.blocat(self.ctx.baza))

    def adu(self, url, componenta):
        if not self.retea:
            return None
        if self.cereri >= self.max_cereri:
            self.noteaza(componenta=componenta, url=url, decizie="plafon",
                         nota=f"plafonul de {self.max_cereri} cereri atins")
            return None
        self.cereri += 1
        rez = transport.adu(url, self.slug, self.stare)
        if rez.verdict != "OK":
            self.noteaza(componenta=componenta, url=url, decizie=rez.verdict.lower(),
                         verdict=rez.verdict, nota=rez.nota)
        return rez

    # ------------------------------------------------------- descoperirea
    def pagina(self, url, componenta, strict):
        """Hub, index de regulamente, pagină principală sau de segment."""
        rez = self.adu(url, componenta)
        if not rez or rez.verdict != "OK" or rez.octeti.startswith(b"%PDF"):
            self.semnal[url] = 0
            return [], []
        self.docs[normalizeaza_url(url)] = {
            "verdict": "OK", "format": "html", "transport": rez.transport,
            "amprenta": amprenta(rez.octeti), "observat_la": self.moment,
            "cale_bronze": scrie_bronze(BRONZE_CAMPANII, url, rez.octeti)}
        cand, liste = candidati_din_pagina(rez.octeti, rez.url_final, self.ctx, componenta, strict)
        for c in cand:
            c["url_hub"] = normalizeaza_url(url)       # adresa cerută, nu cea finală
        self.semnal[url] = len(cand)
        self.noteaza(componenta=componenta, url=url, decizie="pagina_citita",
                     nota=f"{len(cand)} candidați, {len(liste)} pagini-listă")
        return cand, liste

    def intrari_sitemap(self, componenta):
        """[(loc, lastmod)] din sitemap-urile băncii; None dacă e interzis."""
        s = self.cfg.get("sitemap")
        if s is False:
            self.noteaza(componenta=componenta, decizie="sarit",
                         nota="sitemap interzis de robots.txt (config)")
            return None
        if s is None:
            # robots.txt se citește prin flux, ca la orice cerere din transport
            reguli = flux.reguli_pentru(self.ctx.baza, self.slug)
            s = list(dict.fromkeys(reguli.sitemapuri + [origine(self.ctx.baza) + "/sitemap.xml"]))
        de_citit, vazute, intrari = list(s), set(), []
        while de_citit and len(vazute) < MAX_COPII_SITEMAP:
            u = de_citit.pop(0)
            if u in vazute:
                continue
            vazute.add(u)
            rez = self.adu(u, componenta)
            if not rez or rez.verdict != "OK":
                continue
            copii, noi = parseaza_sitemap(rez.octeti)
            de_citit += [c for c in copii if self.ctx.pe_site(c) and not RE_COPIL_SITEMAP_INUTIL.search(c)]
            intrari += noi
        if de_citit:
            self.noteaza(componenta=componenta, decizie="sitemap_necitit",
                         nota=f"{len(de_citit)} sitemap-uri copil necitite (peste {MAX_COPII_SITEMAP})")
        return intrari

    def sitemap(self):
        intrari = self.intrari_sitemap("sitemap")
        if intrari is None:
            return [], []
        cand, liste, amanate = alege_din_sitemap(intrari, self.ctx, self.data)
        for u, motiv in amanate:
            self.noteaza(componenta="sitemap", url=u, decizie="amanat", nota=motiv)
        self.noteaza(componenta="sitemap", decizie="sitemap_citit",
                     nota=f"{len(intrari)} adrese, {len(cand)} candidați, {len(amanate)} amânate")
        return cand, liste

    # ----------------------------------------------------- documentele
    def adauga(self, cand, cheie=None, adancime=0):
        """Un candidat intră într-o campanie: a lui (cheie = propria adresă)
        sau a paginii care l-a legat (regulamentul unei pagini de campanie)."""
        u = cand["url"]
        cheie = cheie or u
        membru = {"url": u, "rol_document": cand["rol"], "eticheta": cand.get("eticheta"),
                  "url_hub": cand.get("url_hub")}
        motiv = flux.motiv_excludere(u)
        if motiv:
            self.noteaza(componenta=cand["provenienta"], url=u, decizie="exclus", nota=motiv)
            return
        if RE_ARHIVA.search(cale_norm(u)) and cand["provenienta"] != "bronze":
            self.noteaza(componenta=cand["provenienta"], url=u, decizie="amanat",
                         nota="arhivă în cale (treapta A)")
            return
        self.membri[cheie].append(membru)
        self.provenienta.setdefault(cheie, cand["provenienta"])
        if u in self.docs:
            return
        rez = self.adu(u, cand["provenienta"])
        d = {"verdict": rez.verdict if rez else ("PLAFON" if self.retea else None),
             "nota": rez.nota if rez else None, "transport": rez.transport if rez else None}
        self.docs[u] = d
        if not rez or rez.verdict != "OK":
            if rez and rez.verdict == "EXCLUS":
                self.membri[cheie].remove(membru)
            return
        self._citeste(u, rez.octeti, d, self.moment,
                      scrie_bronze(BRONZE_CAMPANII, u, rez.octeti))
        self.noteaza(componenta=cand["provenienta"], url=u, decizie="descarcat",
                     transport=rez.transport)
        if adancime == 0 and d["format"] == "html" and cand["rol"] == "landing":
            self._regulamente_din(u, rez.url_final, rez.octeti, cheie, cand["provenienta"])

    def _citeste(self, u, octeti, d, observat_la, cale_rel):
        cale = os.path.join(RADACINA, cale_rel)
        d.update(E.document(octeti, u, cale=cale, nume_banca=self.ctx.nume, nume_grup=self.ctx.grup))
        d.update(amprenta=amprenta(octeti), observat_la=observat_la, cale_bronze=cale_rel)

    def _regulamente_din(self, u, url_final, octeti, cheie, provenienta, doar=None):
        """Regulamentele și actele adiționale legate din pagina campaniei: la
        62 din 74 de campanii stricte, perioada stătea într-un document (§4.1)."""
        for l, text in E.linkuri(octeti, url_final):
            l = normalizeaza_url(l)
            c, t = cale_norm(l), E._fara_diacritice_1la1(text)
            if l == u or not RE_REGULAMENT.search(c + " " + t):
                continue
            if not self.ctx.pe_site(l, doc=True) or self.ctx.sarit(l):
                continue
            if doar is not None and l not in doar:
                continue
            rol = "act_aditional" if RE_ACT.search(c + " " + t) else "regulament"
            self.adauga({"url": l, "rol": rol, "eticheta": text or None, "url_hub": None,
                         "provenienta": provenienta}, cheie=cheie, adancime=1)

    def din_bronze(self, bronze):
        """Componenta 1: documentele din Bronze pe care rețeaua nu le-a adus
        acum. 0 cereri; `observat_la` e data la care le-a adus popularea."""
        de_bronze = {normalizeaza_url(u): (vazut, cale) for u, vazut, cale in bronze}
        for u, (vazut, cale) in de_bronze.items():
            if u in self.docs or flux.motiv_excludere(u):
                continue
            octeti = open(cale, "rb").read()
            if RE_LISTA.search(cale_norm(u)) and not octeti.startswith(b"%PDF"):
                # un index (Salt, „campanii-si-promotii"): nu e o campanie, dar
                # dă etichetele documentelor din Bronze pe care le leagă
                cand, _ = candidati_din_pagina(octeti, u, self.ctx, "bronze")
                for c in cand:
                    if c["url"] in de_bronze and c["url"] not in self.docs:
                        self._din_fisier(c, *de_bronze[c["url"]])
                continue
            doc = e_document(u)
            rol = ("act_aditional" if RE_ACT.search(cale_norm(u)) else "regulament") if doc else "landing"
            self._din_fisier({"url": u, "rol": rol, "eticheta": None, "url_hub": None,
                              "provenienta": "bronze"}, vazut, cale, de_bronze)

    def _din_fisier(self, cand, vazut, cale, de_bronze=None):
        u = cand["url"]
        self.membri[u].append({"url": u, "rol_document": cand["rol"], "eticheta": cand.get("eticheta"),
                               "url_hub": cand.get("url_hub")})
        self.provenienta.setdefault(u, "bronze")
        octeti = open(cale, "rb").read()
        d = {"verdict": "OK", "transport": "bronze"}
        self.docs[u] = d
        self._citeste(u, octeti, d, vazut, os.path.relpath(cale, RADACINA))
        self.noteaza(componenta="bronze", url=u, decizie="bronze")
        if de_bronze and d["format"] == "html" and cand["rol"] == "landing":
            # doar regulamentele aflate și ele în Bronze: componenta 1 nu cere nimic
            for l, text in E.linkuri(octeti, u):
                l = normalizeaza_url(l)
                if l in de_bronze and l not in self.docs and RE_REGULAMENT.search(
                        cale_norm(l) + " " + E._fara_diacritice_1la1(text)):
                    self.membri[u].append({"url": l, "rol_document": "regulament",
                                           "eticheta": text or None, "url_hub": None})
                    dl = {"verdict": "OK", "transport": "bronze"}
                    self.docs[l] = dl
                    self._citeste(l, open(de_bronze[l][1], "rb").read(), dl, de_bronze[l][0],
                                  os.path.relpath(de_bronze[l][1], RADACINA))

    def uneste(self):
        """Un document care e și campanie proprie, și document al altei campanii
        (regulamentul găsit în index ȘI legat din pagina campaniei) rămâne doar
        la campania paginii; eticheta din index trece acolo, ca hub."""
        copii = {m["url"]: k for k, ms in self.membri.items() for m in ms if m["url"] != k}
        for cheie in list(self.membri):
            parinte = copii.get(cheie)
            if parinte and parinte != cheie and all(m["url"] == cheie for m in self.membri[cheie]):
                for m in self.membri.pop(cheie):
                    if m.get("url_hub") or m.get("eticheta"):
                        self.membri[parinte].append(m)

    # ------------------------------------------------------------ rularea
    def colecteaza(self, bronze, liste_cunoscute):
        cfg, cand, liste = self.cfg, [], list(liste_cunoscute)
        if self.retea:
            for u in cfg.get("arhive", []):
                self.noteaza(componenta="hub", url=u, decizie="amanat",
                             nota="hub de arhivă: nu intră în fotografie (treapta A)")
            for u in [self.ctx.baza] + cfg.get("segmente", []):
                c, l = self.pagina(u, "acasa", strict=True)
                cand, liste = cand + c, liste + l
            for u in cfg.get("huburi", []):
                c, l = self.pagina(u, "hub", strict=False)
                cand, liste = cand + c, liste + l
            for u in cfg.get("regulamente", []):
                c, l = self.pagina(u, "regulamente", strict=False)
                cand += c
            if not self.blocata():
                c, l = self.sitemap()
                cand, liste = cand + c, liste + l
            deja = {normalizeaza_url(x) for x in cfg.get("huburi", []) + cfg.get("arhive", [])
                    + cfg.get("regulamente", [])}
            liste = [x for x in dict.fromkeys(liste) if x not in deja
                     and self.ctx.pe_site(x) and not self.ctx.sarit(x)]
            if len(liste) > MAX_LISTE:
                self.noteaza(componenta="lista", decizie="liste_necitite",
                             nota=f"{len(liste) - MAX_LISTE} pagini-listă peste {MAX_LISTE}: "
                                  + ", ".join(liste[MAX_LISTE:])[:500])
            for u in liste[:MAX_LISTE]:
                if self.blocata():
                    break
                c, _ = self.pagina(u, "lista", strict=False)
                cand += c
            vazute = set()
            for c in cand:
                if self.blocata():
                    self.noteaza(componenta="rulare", url=self.ctx.baza, decizie="oprit",
                                 nota=f"origine BLOCAT: {flux.blocat(self.ctx.baza)}")
                    break
                # același URL de pe mai multe huburi: o singură cerere, toate etichetele
                if (c["url"], c.get("url_hub")) in vazute:
                    continue
                vazute.add((c["url"], c.get("url_hub")))
                self.adauga(c)
        self.din_bronze(bronze)
        self.uneste()

    def campanii(self):
        """Rândurile normalizate. Nu devin campanii: huburile și paginile-listă,
        documentele excluse și adresele moarte fără etichetă (nu știm nimic
        despre ele în afară de URL)."""
        randuri = []
        for cheie, membri in self.membri.items():
            if not membri:
                continue
            d = self.docs.get(cheie) or {}
            if RE_LISTA.search(cale_norm(cheie)) and d.get("format") != "pdf":
                continue
            adusi = [m for m in membri if (self.docs.get(m["url"]) or {}).get("verdict") == "OK"]
            if not adusi and not any(m.get("eticheta") for m in membri) and not E.perioada_din_url(cheie):
                self.noteaza(componenta="normalizare", url=cheie, decizie="fara_informatie",
                             nota="document neadus, fără etichetă și fără perioadă în URL")
                continue
            randuri.append(NC.campanie(cheie, membri, self.docs, self.data, self.provenienta[cheie]))
        return randuri

    def scrie(self, randuri):
        import psycopg2
        import normalizeaza as N
        with psycopg2.connect(N.dsn()) as conn, conn.cursor() as cur:
            if not NC.migrarea_aplicata(cur):
                raise SystemExit("tabelele lipsesc: rulează întâi db/migration_019_campanii.sql")
            folosite = {leg["url"] for _, legs in randuri for leg in legs}
            for u in folosite:
                d = self.docs.get(u) or {}
                if d.get("verdict") in ("OK", "ROBOTS", "BLOCAT", "DISPARUT"):
                    d["id_sursa"] = NC.inregistreaza_sursa(
                        cur, self.slug, u, "campanie", d.get("format") or ("pdf" if e_document(u) else "html"),
                        d.get("transport"), d["verdict"], d.get("nota"))
            for rand, legs in randuri:
                for leg in legs:
                    leg["id_sursa"] = (self.docs.get(leg["url"]) or {}).get("id_sursa")
            return NC.scrie_campanii(cur, self.slug, randuri, self.moment)

    def semnal_de_control(self, err):
        """Numărul de candidați pe fiecare hub, față de rularea anterioară: pe
        BCR, scriptul generic a dat 5 candidați în loc de 260, fără nicio
        eroare (§4.1). Un hub care cade la 0 sau la sub jumătate se semnalează."""
        cale = os.path.join(LOGURI, f"semnal_{self.slug}.json")
        try:
            with open(cale, encoding="utf-8") as f:
                vechi = json.load(f)
        except (OSError, ValueError):
            vechi = {}
        for hub, n in self.semnal.items():
            inainte = vechi.get(hub)
            if n == 0 or (inainte and n < inainte / 2):
                err.write(f"  ATENȚIE {hub}: {n} candidați (rularea anterioară: {inainte})\n")
        with open(cale, "w", encoding="utf-8") as f:
            json.dump(self.semnal, f, ensure_ascii=False, indent=1)

    # ---------------------------------------------------------- newsroom
    def pagini_newsroom(self, nr):
        n_start = nr.get("n_start", 2)
        return [nr["url"]] + [urljoin(nr["url"].rstrip("/") + "/", nr["paginare"].format(n=n_start + i))
                              if not nr["paginare"].startswith("?")
                              else nr["url"] + nr["paginare"].format(n=n_start + i)
                              for i in range(nr.get("pagini", 1) - 1)]

    def newsroom(self, corp_luni=0):
        nr = self.cfg.get("newsroom")
        if not nr:
            return []
        items = {}
        if nr["tip"] == "sitemap":
            for loc, lastmod in self.intrari_sitemap("newsroom") or []:
                u = normalizeaza_url(loc)
                if urlparse(u).path.startswith(nr["prefix"]) and urlparse(u).path.rstrip("/") != nr["prefix"].rstrip("/"):
                    data = E.data_din_url(u)
                    items[u] = {"url": u, "titlu": E.titlu_din_url(u), "titlu_din": "url",
                                "data": data, "data_din": "url" if data else None,
                                "provenienta": "sitemap", "_lastmod": lastmod}
        else:
            for pag in self.pagini_newsroom(nr):
                rez = self.adu(pag, "newsroom")
                if not rez or rez.verdict != "OK":
                    break
                for it in comunicate_din_lista(rez.octeti, rez.url_final, self.ctx, nr.get("prefix")):
                    items.setdefault(it["url"], it)
        if corp_luni:
            self._corpuri(list(items.values()), corp_luni)
        return list(items.values())

    def _corpuri(self, items, luni):
        limita = self.data - datetime.timedelta(days=int(luni * 30.5))
        for it in items:
            data = it.get("data") or it.get("_lastmod")
            if not data or data < limita or flux.motiv_excludere(it["url"]):
                continue
            rez = self.adu(it["url"], "newsroom")
            it["verdict"] = rez.verdict if rez else None
            it["transport"] = rez.transport if rez else None
            if not rez or rez.verdict != "OK" or rez.octeti.startswith(b"%PDF"):
                continue
            it["cale_bronze"] = scrie_bronze(BRONZE_COMUNICATE, it["url"], rez.octeti)
            it["amprenta"] = amprenta(rez.octeti)
            _, meta = E.text_html(rez.octeti)
            t = E.titlu_html(meta)
            if t:
                it["titlu"], it["titlu_din"] = t, "pagina"
            if not it.get("data"):
                d = data_publicarii(rez.octeti)
                if d:
                    it["data"], it["data_din"] = d, "pagina"

    def scrie_comunicate(self, items):
        import psycopg2
        import normalizeaza as N
        with psycopg2.connect(N.dsn()) as conn, conn.cursor() as cur:
            if not NC.migrarea_aplicata(cur):
                raise SystemExit("tabelele lipsesc: rulează întâi db/migration_019_campanii.sql")
            for it in items:
                if it.get("verdict"):
                    it["id_sursa"] = NC.inregistreaza_sursa(cur, self.slug, it["url"], "comunicat", "html",
                                                            it.get("transport"), it["verdict"], None)
            return NC.scrie_comunicate(cur, self.slug, [NC.comunicat(it) for it in items], self.moment)


def data_publicarii(octeti):
    """Data din metadatele paginii (article:published_time, <time datetime>)."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(octeti, "lxml")
    for el, atr in ((soup.find("meta", property="article:published_time"), "content"),
                    (soup.find("time", datetime=True), "datetime")):
        if el and el.get(atr):
            m = re.match(r"(\d{4})-(\d{2})-(\d{2})", el[atr])
            if m:
                return E._data(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def comunicate_din_lista(octeti, url_lista, ctx, prefix=None):
    """Comunicatele dintr-o pagină-listă: titlul e textul linkului, data e
    prima dată din blocul lui (sau din URL)."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(octeti, "lxml")
    for tag in soup.find_all(["nav", "footer", "header", "script", "style"]):
        tag.decompose()
    lista = normalizeaza_url(url_lista)
    items = {}
    for a in soup.find_all("a", href=True):
        u = normalizeaza_url(urljoin(url_lista, a["href"]).split("#")[0])
        cale = urlparse(u).path
        text = E.colapseaza(a.get_text(" ", strip=True))
        if not u.startswith("http") or not ctx.pe_site(u) or ctx.sarit(u) or u == lista:
            continue
        if prefix and not cale.startswith(prefix):
            continue
        if not prefix and (len(text) < 15 or cale.rstrip("/") in ("", urlparse(lista).path.rstrip("/"))
                           or re.search(r"[?&]page=|/page/\d", u) or e_document(u)):
            continue
        if len(text) < 8:
            continue
        bloc = a.find_parent(["article", "li"]) or a.parent
        data, data_din = E.data_din_text(E.colapseaza(bloc.get_text(" ", strip=True))[:400]), "lista"
        if not data:
            data, data_din = E.data_din_url(u), "url"
        it = items.get(u)
        if it is None or len(text) > len(it["titlu"] or ""):
            items[u] = {"url": u, "titlu": text[:300], "titlu_din": "lista", "data": data,
                        "data_din": data_din if data else None, "provenienta": "lista"}
    return list(items.values())


# ==========================================================================
# --simulare: ce s-ar cere, fără nicio cerere
# ==========================================================================

def robots_offline(url, slug):
    """Verdictul din ultima copie robots.txt salvată de `flux.salveaza_robots`
    (date/robots/<gazdă>_<dată>.json). Fără copie: „necunoscut încă" — robots
    se citește la prima cerere reală, înainte de orice pagină."""
    gazda = urlparse(url).netloc.lower().replace(":", "_")
    copii = sorted(glob.glob(os.path.join(flux.DIR_ROBOTS, f"{glob.escape(gazda)}_*.json")))
    if not copii:
        return None, "robots necunoscut încă"
    with open(copii[-1], encoding="utf-8") as f:
        meta = json.load(f)
    if meta.get("cod_http") != 200 or not meta.get("fisier"):
        return None, f"robots: {meta.get('status_reguli')} (copia din {meta.get('data', '')[:10]})"
    from crawler.robots import RegulliRobots
    reguli = RegulliRobots(slug, flux.origine_din(url))
    with open(os.path.join(flux.DIR_ROBOTS, meta["fisier"]), encoding="utf-8", errors="replace") as f:
        reguli._parseaza(f.read())
    verdict = "permis" if reguli.permite(url) else "INTERZIS"
    return reguli, f"robots {verdict} (copia din {meta.get('data', '')[:10]})"


def simuleaza(banci, newsroom, out, cu_baza=True):
    """Planul de cereri pe bancă, cu durata estimată. Nu face nicio cerere
    și nu citește robots.txt de pe rețea."""
    bronze, liste_cunoscute, pagini_bronze = {}, {}, {}
    if cu_baza:
        try:
            import psycopg2
            import normalizeaza as N
            with psycopg2.connect(N.dsn()) as conn, conn.cursor() as cur:
                for slug in banci:
                    bronze[slug] = documente_bronze(cur, slug)
                    liste_cunoscute[slug] = liste_din_surse(cur, slug)
                    cur.execute("""SELECT s.sursa FROM surse s JOIN banci b ON b.id = s.id_banca
                                   WHERE b.slug = %s AND EXISTS (SELECT 1 FROM hashes h
                                   WHERE h.id_sursa = s.id)""", (slug,))
                    pagini_bronze[slug] = {normalizeaza_url(u) for (u,) in cur.fetchall()}
        except Exception as exc:
            out.write(f"(baza indisponibilă, Bronze și `surse` necunoscute: {type(exc).__name__})\n")
    total, rezumat = 0, []
    for slug in banci:
        stare, motiv = K.stare_banca(slug)
        if stare != "colectat":
            out.write(f"\n═══ {slug}: {stare.upper().replace('_', ' ')} — 0 cereri — {motiv}\n")
            rezumat.append((slug, stare, 0, 0, 0))
            continue
        cfg = K.CONFIG[slug]
        ctx = Context(slug, cfg)
        pauza = cfg.get("pauza_estimata", PAUZA_IMPLICITA)
        plan, nedescoperite = [], 0
        out.write(f"\n═══ {slug}" + (" (reper: banca noastră)" if slug in K.BANCI_REPER else "") + "\n")
        if newsroom:
            nr = cfg.get("newsroom")
            if not nr:
                out.write(f"  newsroom: fără config — {cfg.get('nota_newsroom', 'nicio listă găsită offline')}\n")
            elif nr["tip"] == "sitemap":
                s = cfg.get("sitemap") or ["sitemap-urile din robots.txt (necunoscute încă)"]
                for u in s:
                    plan.append(("newsroom/sitemap", u))
                out.write(f"  newsroom: sitemap, prefixul {nr['prefix']} (+ copiii indexului, "
                          f"cel mult {MAX_COPII_SITEMAP}: necunoscut până la citire)\n")
            else:
                col = Colector(slug, cfg, datetime.datetime.now().astimezone(), io.StringIO(), retea=False)
                for u in col.pagini_newsroom(nr):
                    plan.append(("newsroom/lista", u))
        else:
            for u in [ctx.baza] + cfg.get("segmente", []):
                plan.append(("4 acasă/segment", u))
            for u in cfg.get("huburi", []):
                plan.append(("3 hub", u))
            for u in cfg.get("regulamente", []):
                plan.append(("3 regulamente", u))
            s = cfg.get("sitemap")
            if s is False:
                out.write("  2 sitemap: NU (interzis de robots.txt, config)\n")
            else:
                for u in (s or [origine(ctx.baza) + "/sitemap.xml",
                                "+ sitemap-urile declarate în robots.txt (necunoscute încă)"]):
                    plan.append(("2 sitemap", u))
            for u in cfg.get("arhive", []):
                out.write(f"  3 arhivă, NU se cere (treapta A): {u}\n")
            deja = {normalizeaza_url(x) for x in cfg.get("huburi", []) + cfg.get("arhive", [])
                    + cfg.get("regulamente", [])}
            for u in [x for x in liste_cunoscute.get(slug, []) if x not in deja
                      and ctx.pe_site(x) and not ctx.sarit(x)][:MAX_LISTE]:
                plan.append(("5 listă din surse", u))
            docs = bronze.get(slug, [])
            out.write(f"  1 Bronze: {len(docs)} documente de campanie, 0 cereri\n")
            # din copiile Bronze ale paginilor planificate: câte legături ar urma
            gasite = set()
            for comp, u in plan:
                if u.startswith("http") and normalizeaza_url(u) in pagini_bronze.get(slug, set()):
                    with open(flux.cale_bronze(normalizeaza_url(u)), "rb") as f:
                        c, _ = candidati_din_pagina(f.read(), u, ctx, "sim", strict=comp.startswith("4"))
                    gasite |= {x["url"] for x in c}
            nedescoperite = len(gasite)
        for comp, u in plan:
            if not u.startswith("http"):
                out.write(f"  {comp}: {u}\n")
                continue
            excl = flux.motiv_excludere(u)
            _, rob = robots_offline(u, slug)
            in_bronze = " [în Bronze]" if normalizeaza_url(u) in pagini_bronze.get(slug, set()) else ""
            out.write(f"  {comp}: {u}{in_bronze} — {excl or rob}\n")
        sigure = len([1 for _, u in plan if u.startswith("http")])
        origini = {origine(u) for _, u in plan if u.startswith("http")}
        cereri = sigure + len(origini)
        durata = (cereri + nedescoperite) * pauza
        out.write(f"  cereri sigure: {cereri} ({len(origini)} robots.txt + {sigure} pagini)")
        if not newsroom:
            out.write(f"; plus documentele descoperite la rulare (necunoscute; din copiile Bronze ale "
                      f"paginilor de mai sus: ~{nedescoperite} candidați)")
        out.write(f"\n  pauza: {pauza} s între cereri → ~{durata / 60:.1f} min\n")
        total += durata
        rezumat.append((slug, stare, cereri, nedescoperite, durata))
    out.write("\n═══ Rezumat\n")
    out.write(f"  {'bancă':20s} {'stare':18s} {'sigure':>7s} {'+ din Bronze':>13s} {'durată':>9s}\n")
    for slug, stare, cereri, ned, durata in rezumat:
        out.write(f"  {slug:20s} {stare:18s} {cereri:7d} {ned:13d} {durata / 60:7.1f} m\n")
    out.write(f"  total, secvențial: ~{total / 60:.0f} min (doar cererile știute dinainte și "
              "candidații din copiile Bronze; sitemap-urile adaugă adrese necunoscute acum)\n")
    return rezumat


# ==========================================================================

def banci_de_rulat(banca):
    if banca:
        return [banca]
    return sorted(set(K.CONFIG) | set(K.BLOCATE) | set(K.IN_AFARA_SCOPULUI) | set(K.FARA_CONFIG))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--banca", help="doar o bancă (slug)")
    ap.add_argument("--simulare", action="store_true", help="listează ce s-ar cere, fără nicio cerere")
    ap.add_argument("--newsroom", action="store_true", help="comunicatele de presă, nu campaniile")
    ap.add_argument("--doar-bronze", action="store_true",
                    help="doar documentele deja în Bronze (componenta 1), fără rețea")
    ap.add_argument("--corp-luni", type=int, default=0,
                    help="cu --newsroom: aduce și corpul comunicatelor din ultimele N luni (implicit 0)")
    ap.add_argument("--max-cereri", type=int, default=MAX_CERERI_BANCA)
    a = ap.parse_args()
    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", write_through=True)
    err = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", write_through=True)
    banci = banci_de_rulat(a.banca)

    import config
    config.incarca()          # doar .env (MIP_DSN), fără rețea
    if a.simulare:
        simuleaza(banci, a.newsroom, out)
        return 0

    import psycopg2
    import normalizeaza as N
    moment = datetime.datetime.now().astimezone()
    os.makedirs(LOGURI, exist_ok=True)
    cale_jurnal = os.path.join(LOGURI, f"{'newsroom' if a.newsroom else 'campanii'}_{moment:%Y%m%d_%H%M}.jsonl")
    with open(cale_jurnal, "a", encoding="utf-8") as jurnal:
        for slug in banci:
            stare, motiv = K.stare_banca(slug)
            if stare != "colectat":
                err.write(f"  {slug:20s} {stare}: 0 cereri — {motiv}\n")
                continue
            col = Colector(slug, K.CONFIG[slug], moment, jurnal, a.max_cereri, retea=not a.doar_bronze)
            try:
                if a.newsroom:
                    if a.doar_bronze:
                        err.write(f"  {slug:20s} newsroom: fără rețea nu există nimic de enumerat\n")
                        continue
                    items = col.newsroom(a.corp_luni)
                    n = col.scrie_comunicate(items) if items else 0
                    e_c = sum(1 for it in items if NC.e_campanie(it.get("titlu"))[0])
                    err.write(f"  {slug:20s} {col.cereri:4d} cereri · {len(items):4d} comunicate "
                              f"({e_c} cu titlu de campanie) · {n} scrise\n")
                    continue
                with psycopg2.connect(N.dsn()) as conn, conn.cursor() as cur:
                    bronze = documente_bronze(cur, slug)
                    liste = liste_din_surse(cur, slug)
                col.colecteaza(bronze, liste if not a.doar_bronze else [])
                randuri = col.campanii()
                n_c, n_l = col.scrie(randuri) if randuri else (0, 0)
                pe_stare = collections.Counter(r["stare"] for r, _ in randuri)
                err.write(f"  {slug:20s} {col.cereri:4d} cereri · {n_c:4d} campanii "
                          f"({dict(pe_stare)}) · {n_l} legături · {dict(col.raport)}\n")
                if col.retea:
                    col.semnal_de_control(err)
            finally:
                transport.inchide(col.stare)
    err.write(f"\njurnal: {os.path.relpath(cale_jurnal, RADACINA)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
