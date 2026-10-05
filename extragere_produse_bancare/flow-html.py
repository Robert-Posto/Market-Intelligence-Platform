#!/usr/bin/env python3
"""
flow-html.py — flowul de extracție pentru documente HTML.

Primește CONȚINUTUL HTML, nu un URL. Descărcarea, hashul pe bytes bruți și
scrierea în Bronze aparțin routerului, fiind comune tuturor tipurilor.
Aici intră doar ce e specific HTML-ului: sanitizarea, fragmentarea pe
secțiuni și extracția per produs.

    from flow_html import proceseaza

    rez = await proceseaza(
        html=continut,                      # string, deja descărcat
        metoda="http",                      # cum a fost obținut; doar metadată
        produse=["comisioane", "cont-curent"],   # din jobul de discovery
        url="https://...",                  # pentru context în prompt
        hash_anterior="a3f9...",            # din url_check, dacă există
    )

Întoarce JSON cu ce a găsit, plus hashul pe textul sanitizat, pe care
routerul îl scrie în url_check.

Pentru testare izolată, CLI-ul poate citi dintr-un fișier sau descărca el
singur o pagină:

    python3 flow-html.py --fisier pagina.html --metoda http --produse comisioane
    python3 flow-html.py --url https://... --metoda http --produse comisioane,dae

    pip install anthropic python-dotenv selectolax trafilatura
    pip install httpx                                  # doar pentru --url
    pip install playwright && playwright install chromium   # doar pentru --url cu playwright
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import trafilatura
from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from selectolax.parser import HTMLParser

load_dotenv(Path(__file__).with_name(".env"))

# Importat DUPĂ load_dotenv, intenționat: `fallback_web_fetch` își citește
# configurația la nivel de modul, deci FALLBACK_WEB_FETCH și WEB_FETCH_* trebuie
# să fie deja în environment când modulul se încarcă. Mutat sus, cu celelalte
# importuri, `FALLBACK_WEB_FETCH=0` din .env ar fi ignorat în silenție.
# Fallbackul prin web_fetch (fallback_web_fetch.py) e scos: când banca refuză
# accesul sau pagina nu se poate citi local, documentul rămâne neextras, nu se
# încearcă alt canal (regula echipei: bancă blocată = stop). Codul de mai jos
# care îl folosea rămâne inactiv prin WEB_FETCH_ACTIV = False.
WEB_FETCH_ACTIV = False


async def adu_text_api(url: str) -> tuple[str, dict]:   # nu se mai apelează
    return "", {"eroare": "fallback web_fetch dezactivat"}

# Identificare onestă. Pune un contact real în .env înainte de producție.
UA = os.getenv("USER_AGENT", "MarketIntelBot/1.0 (+contact@example.org)")

# Antetele standard pe care un client HTTP le omite, dar orice browser le trimite.
# Unele configurații de WAF resping cererile fără ele, indiferent de user-agent.
# Nu e spoofing: user-agentul rămâne al nostru, declarat.
ANTETE = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}
MODEL = os.getenv("MODEL", "claude-sonnet-5")
TIMEOUT = float(os.getenv("TIMEOUT", "30"))
PRAG_INCREDERE = float(os.getenv("PRAG_INCREDERE", "0.85"))

# Peste `PRAG_SIGUR` valoarea intra fara rezerve; intre `PRAG_INCREDERE` si
# `PRAG_SIGUR` intra marcata `necesita_verificare`.
#
# Separarea exista fiindca increderea raportata de model nu prezice
# corectitudinea. Masurat pe 1.203 randuri de la Libra, ING si Raiffeisen, cat
# de des contine citatul cifra revendicata: 92% la increderi peste 0,85, si
# 87-98% peste tot intre 0,5 si 0,85. Curba e plata, deci un prag unic taie la
# intamplare in raport cu masura asta.
#
# Ce filtreaza cu adevarat sunt verificarile pe fapte — citat negasit in sursa
# (74 de cazuri), citat prea scurt (29), valoare in afara intervalului
# plauzibil (19). Alea se declanseaza si la incredere mare.
#
# Rezerva onesta: testul verifica daca cifra apare in citat, nu daca a fost
# pusa pe campul potrivit. Increderea joasa ar putea insemna „nu-s sigur ca
# asta e `dobanda_fixa` si nu `dae`", iar aia nu se vede in masuratoare. De
# aceea zona de mijloc se marcheaza, nu se amesteca.
PRAG_SIGUR = float(os.getenv("PRAG_SIGUR", "0.85"))
# Sub atâtea caractere, un citat nu mai identifică rândul din care vine.
MIN_CARACTERE_CITAT = int(os.getenv("MIN_CARACTERE_CITAT", "12"))
# Cât text se trimite la extracție. Nu mai e o limită tehnică: Opus 5 are 1M
# de tokeni de context, iar o pagină de tarife ocupă sub 3% din ea. E o
# decizie de cost — 200.000 de caractere ≈ 60k tokeni. Peste atât se cade pe
# fragmentare, care rămâne doar supapă, nu drum principal.
MAX_CARACTERE_LLM = int(os.getenv("MAX_CARACTERE_LLM", "200000"))
MAX_HTML_LLM = int(os.getenv("MAX_HTML_LLM", "120000"))
PRAG_FIDELITATE = float(os.getenv("PRAG_FIDELITATE", "0.70"))
PP = "\n\n"


# ══════════════════════════════════════════════════════════════════
# CATALOG — încărcat din produse_bancare_v2.json
# ══════════════════════════════════════════════════════════════════
#
# Catalogul nu mai e scris aici. Trăiește în `produse_bancare_v2.json`, care e
# sursa unică: îl citesc și `claudeCrawl.py` pentru discovery, și scripturile
# de populare a bazei. Două liste paralele ar divergea, iar divergența s-ar
# vedea abia când o extracție ar cere un produs pe care discovery-ul nu-l
# cunoaște.
#
# Versiunea 2 a scos măsurile dintre produse. `dae`, `dobanda_nominala`,
# `marja_banca`, `ircc`, `curs_cumparare` nu sunt produse — sunt cifre care
# descriu un produs, deci sunt câmpuri. În v1, fiecare primea apel propriu de
# extracție, iar același fapt ajungea sub 7 etichete de produs diferite.

CALE_CATALOG = Path(__file__).with_name(
    os.getenv("CATALOG_PRODUSE", "produse_bancare_v2.json"))


def _incarca_catalog() -> tuple[dict, dict]:
    """
    @returns (CATALOG, CAMPURI) — metadatele produsului si vocabularul lui.
    """
    if not CALE_CATALOG.exists():
        raise SystemExit(
            f"Lipsește {CALE_CATALOG.name}. Fără catalog nu se poate extrage: "
            "produsele, keywordurile și vocabularul de câmpuri vin de acolo.")

    date = json.loads(CALE_CATALOG.read_text(encoding="utf-8"))
    catalog, campuri = {}, {}
    for p in date["produse"]:
        catalog[p["id"]] = {
            "nume": p["nume"],
            "keywords": p.get("keywords", []),
            "cauta": p.get("cauta", ""),
            "interval": p.get("interval", {}),
            "segment": p.get("segment"),
            "grup": p.get("grup"),
            # Axele pe care variaza pretul produsului. Nu se confunda cu
            # `interval`, care e plaja de plauzibilitate a lui `valoare_num`.
            "trepte": p.get("trepte", []),
        }
        campuri[p["id"]] = p.get("campuri", ["altele"])
    return catalog, campuri


CATALOG, CAMPURI = _incarca_catalog()


# ── SCENARII ────────────────────────────────────────────────────────
# Cazul fix pe care toate băncile îl raportează, ca valorile să stea pe aceeași
# axă. Vezi `scenarii.json` pentru de ce. Fișierul e opțional: fără el
# extracția rămâne exact cum era, adică liberă.

CALE_SCENARII = Path(__file__).with_name("scenarii.json")


def _incarca_scenarii() -> dict:
    if not CALE_SCENARII.exists():
        return {}
    date = json.loads(CALE_SCENARII.read_text(encoding="utf-8"))
    return {s["id"]: s for s in date.get("scenarii", [])}


SCENARII = _incarca_scenarii()


def scenariu_implicit(produs: str) -> dict | None:
    """Scenariul de referință al unui produs, dacă are unul marcat `implicit`."""
    for s in SCENARII.values():
        if s["produs"] == produs and s.get("implicit"):
            return s
    return None



# ══════════════════════════════════════════════════════════════════
# 1. SANITIZARE
# ══════════════════════════════════════════════════════════════════

# Ce se scoate din pagina. Sunt ELEMENTE de sablon, nu zone de continut:
# criteriul e „asta ar aparea identic pe orice pagina a sitului".
#
# `[class*=carousel]` a fost aici si a fost scos. Un carusel e un tipar de
# prezentare, nu reclama: Raiffeisen isi tine cardurile de dobanzi in caruseluri,
# iar selectorul arunca 11 din 13 procente de pe pagina de economii. Masurat pe
# 10 pagini: cu el 92 din 125 de procente si sume, fara el 118.
SELECTORI_DE_SCOS = (
    "script, style, noscript, iframe, svg, canvas, template, "
    "header, footer, nav, aside, form, "
    "[role=banner], [role=navigation], [role=contentinfo], [role=search], "
    "[class*=cookie], [id*=cookie], [class*=consent], [id*=consent], "
    "[class*=newsletter], [class*=popup], [class*=modal], [class*=overlay], "
    "[class*=breadcrumb], [class*=social], [class*=share], "
    "[class*=banner], [class*=promo-strip], "
    "[class*=menu], [class*=navbar], [class*=sidebar], "
    "[class*=advert], [class*=sponsor], [id*=ad-], [class*=widget-ad]"
)

# elemente volatile care ar schimba hashul fără ca informația să difere
VOLATILE = [
    (re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{4}\b"), ""),              # date
    (re.compile(r"\b\d{1,2}:\d{2}(:\d{2})?\b"), ""),                     # ore
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I), ""),
    (re.compile(r"[?&](utm_[a-z]+|sid|sessionid|token|nonce|_t|cb)=[^\s&\"']+", re.I), ""),
    (re.compile(r"\b(generat|actualizat|valabil|ultima actualizare)[^.\n]{0,40}", re.I), ""),
]


@dataclass
class Sanitizat:
    text: str
    titlu: str = ""
    titluri: list[str] = field(default_factory=list)
    procente: list[str] = field(default_factory=list)
    sume: list[str] = field(default_factory=list)
    metoda_curatare: str = ""
    lungime_html: int = 0


def sanitizeaza(html: str) -> Sanitizat:
    """
    Se scot ELEMENTELE de șablon — script, stil, header, footer, nav, bannere
    de cookie — și se păstrează tot textul rămas.

    Ordinea a fost invers, cu trafilatura pe primul loc. Trafilatura nu scoate
    elemente: alege „zona de conținut principal", ceea ce pe un articol e exact
    ce trebuie, iar pe o pagină de produs bancar aruncă tocmai tabelele și
    cardurile de tarife. Pe pagina de economii a Raiffeisen reducea 405.141 de
    caractere la 4.589 și păstra 1 din 13 procente; extracția ieșea cu
    `produse_gasite: 0` fără niciun semn că fusese o pierdere, nu o absență.

    Măsurat pe 10 pagini Raiffeisen, procente și sume păstrate din câte are
    textul paginii: trafilatura 41/125, curățarea pe elemente 118/125. Costul e
    de ~2,1x mai mult text trimis la model — 9.200 de caractere pe pagină în
    medie, față de un buget de 200.000.

    Trafilatura rămâne plasa de siguranță, pentru paginile fără `<body>`
    utilizabil.
    """
    doc = HTMLParser(html)
    titlu_el = doc.css_first("title")
    titlu = titlu_el.text(strip=True)[:160] if titlu_el else ""
    titluri = [h.text(strip=True)[:110] for h in doc.css("h1, h2, h3, h4")
               if h.text(strip=True)][:40]

    for tag in doc.css(SELECTORI_DE_SCOS):
        tag.decompose()
    corp = doc.css_first("main") or doc.css_first("[role=main]") or doc.body
    text = corp.text(separator="\n", strip=True) if corp else ""
    metoda = "selectolax"

    if len(text) < 500:
        text = trafilatura.extract(
            html, include_tables=True, include_links=False,
            include_comments=False, include_images=False,
            favor_recall=True, output_format="txt",
        ) or text
        metoda = "trafilatura"

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    return Sanitizat(
        text=text, titlu=titlu, titluri=titluri,
        procente=re.findall(r"\d{1,3}[.,]\d{1,3}\s*%|\b\d{1,3}\s*%", text)[:40],
        sume=re.findall(r"\d{1,3}(?:[.\s]\d{3})+(?:[.,]\d{2})?\s*(?:lei|RON|EUR|USD)",
                        text, re.I)[:30],
        metoda_curatare=metoda, lungime_html=len(html),
    )


def hash_stabil(text: str) -> str:
    """Hash pe text normalizat, ca să nu reextragem din cauza unui timestamp."""
    t = text.lower()
    for rx, rep in VOLATILE:
        t = rx.sub(rep, t)
    t = re.sub(r"\s+", " ", t).strip()
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


# ══════════════════════════════════════════════════════════════════
# 2. FRAGMENTARE
# ══════════════════════════════════════════════════════════════════

def pare_titlu(linie: str) -> bool:
    l = linie.strip()
    if not l or len(l) > 90:
        return False
    if re.match(r"^\s*\d+[.)]\s+\S", l):
        return True
    litere = [c for c in l if c.isalpha()]
    if litere and sum(c.isupper() for c in litere) / len(litere) > 0.7:
        return True
    return bool(re.match(r"^[A-ZĂÂÎȘȚ][^.!?]{3,70}$", l))


def fara_diacritice(s: str) -> str:
    """Minuscule, fără diacritice. Pentru potrivirea de keyworduri, nu pentru afișare."""
    return unicodedata.normalize("NFKD", s.lower()).encode("ascii", "ignore").decode()


def taie(text: str, keywords: list[str], min_caractere: int = 400) -> str | None:
    """
    Cuvântul-cheie e ancoră, nu filtru. Într-un tabel de tarife, contextul
    stă deasupra: rândul cu dobânda nu conține „card de credit”, titlul
    secțiunii da.
    """
    # Keywordurile din catalog sunt scrise fără diacritice, iar paginile le au.
    # Fără normalizare, „taxe si comisioane" nu prinde „Taxe și comisioane" —
    # măsurat pe pagina de taxe a BT, din patru keyworduri ale produsului doar
    # unul potrivea, și acela nimerea metadatele din head.
    chei = [fara_diacritice(k) for k in keywords]
    linii = text.split("\n")
    start = None
    for i, l in enumerate(linii):
        low = fara_diacritice(l)
        if any(k in low for k in chei):
            start = i
            break
    if start is None:
        return None

    sfarsit = len(linii)
    for j in range(start + 1, len(linii)):
        if pare_titlu(linii[j]) and j - start > 3:
            sfarsit = j
            break

    frag = "\n".join(linii[start:sfarsit]).strip()
    if len(frag) < min_caractere:              # am tăiat prea devreme
        frag = "\n".join(linii[start:min(start + 80, len(linii))]).strip()
    return frag or None


# Denumirile observate în primul lot, mapate pe cele canonice. Servesc la două
# lucruri: normalizează valorile extrase înainte de vocabular și rămân ca plasă
# dacă modelul scapă totuși un nume vechi.
SINONIME: dict[str, str] = {
    # cost lunar de cont / abonament
    "abonament_cost_lunar": "cost_lunar",
    "cost_lunar_abonament": "cost_lunar",
    "cost_lunar_abonament_premium_club": "cost_lunar",
    "cost_lunar_abonament_diaspora": "cost_lunar",
    "abonament_salut_lunar": "cost_lunar",
    "abonament_student_lunar": "cost_lunar",
    "abonament_365_lunar": "cost_lunar",
    "abonament_gold_lunar": "cost_lunar",
    "abonament_gold_plus_lunar": "cost_lunar",
    # administrare — la CREDITE, cele trei nume vechi merg pe campul nou.
    # `normalizeaza_camp` aplica sinonimul, apoi verifica vocabularul
    # produsului: la un cont curent `comision_administrare_lunar` ramane
    # valid si sinonimul nu se aplica, fiindca nu e in harta decat sub
    # numele specifice de mai jos.
    "comision_administrare_credit": "comision_administrare_credit_lunar_lei",
    "comision_administrare_credit_lunar": "comision_administrare_credit_lunar_lei",
    "comision_administrare_credit_procent": "comision_administrare_credit_procent_sold",
    "comision_lunar_administrare_credit": "comision_administrare_credit_lunar_lei",
    "comision_anual_administrare_credit": "comision_administrare_credit_procent_sold",
    "comision_administrare_sold": "comision_administrare_credit_procent_sold",
    "comision_administrare_cont_card": "comision_administrare_lunar",
    "comision_administrare_cont_eur": "comision_administrare_lunar",
    "comision_cont_valuta_lunar": "comision_administrare_lunar",
    "comision_deschidere_administrare_cont": "comision_deschidere_cont",
    "comision_deschidere_administrare_student": "comision_deschidere_cont",
    "deschidere_cont_curent": "comision_deschidere_cont",
    "comision_deschidere_cont_emitere_card": "comision_deschidere_cont",
    "comision_administrare_card_anual": "comision_administrare_card",
    # card
    "cost_emitere_card": "comision_emitere_card",
    "comision_emitere_card_suplimentar": "comision_emitere_card",
    "comision_emitere_mentenanta_card": "comision_emitere_card",
    "comision_emitere_mentenanta_card_student": "comision_emitere_card",
    "cost_livrare_card": "comision_livrare_card",
    # numerar
    "retragere_numerar_ghiseu_ron": "comision_retragere_ghiseu",
    "retragere_numerar_ghiseu_valuta": "comision_retragere_ghiseu",
    "comision_retragere_numerar_bt": "comision_retragere_ghiseu",
    "cost_utilizare_atm_numerar": "comision_retragere_atm",
    "depunere_numerar_terte_persoane": "comision_depunere_numerar",
    "depunere_numerar_titular": "comision_depunere_numerar",
    # plati si incasari
    "plata_bt_bt_ghiseu": "comision_plata_intrabancara",
    "comision_plati_intre_conturi_bt": "comision_plata_intrabancara",
    "plata_externa_swift_ron_ghiseu": "comision_plata_externa",
    "comision_plata_standard": "comision_plata_interbancara",
    "comision_plata_instant": "comision_plata_interbancara",
    "comision_plata_interbancara_standard": "comision_plata_interbancara",
    "comision_plata_interbancara_instant": "comision_plata_interbancara",
    "comision_incasari_interbancare": "comision_incasare",
    "comision_incasari_lei_alte_banci": "comision_incasare",
    "comision_incasari_alte_banci_student": "comision_incasare",
    "incasare_bt_altabanca_debit": "comision_incasare",
    "comision_consultare_sold_numerar_bt": "comision_consultare_sold",
    "scutire_comision_incasare_alte_banci": "conditie_scutire",
    "taxa_dezactivare_premium_club": "taxa_dezactivare",
    # dobanzi si marje
    "dobanda_simulare_exemplu": "dobanda_nominala",
    "dobanda_medie": "dobanda_nominala",
    "dobanda_sold_pozitiv": "dobanda_nominala",
    "dobanda_fixa_verde": "dobanda_fixa",
    "dobanda_fixa_initiala": "dobanda_fixa",
    "dobanda_fixa_3ani": "dobanda_fixa",
    "dobanda_fixa_introductorie": "dobanda_fixa_introductiva",
    "dobanda_variabila_exemplu": "dobanda_variabila",
    "marja_banca_exemplu": "marja_banca",
    "marja_reducere_verde": "marja_banca",
    "marja_fixa": "marja_banca",
    "marja_dobanda": "marja_banca",
    "marja_dobanda_variabila_min": "marja_banca_min",
    "marja_dobanda_variabila_max": "marja_banca_max",
    "dobanda_min_marja": "marja_banca_min",
    "dobanda_max_marja": "marja_banca_max",
    "dobanda_marja_fixa": "marja_banca",
    "dobanda_marja_banca": "marja_banca",
    "marja_ircc_exemplu_reprezentativ": "marja_ircc",
    "marja_peste_irc": "marja_peste_indice",
    "IRCC": "ircc",
    # perioade
    "perioada": "perioada_credit",
    "perioada_exemplu": "perioada_credit",
    "perioada_creditare": "perioada_credit",
    "perioada_finantare": "perioada_finantare_min",
    "avans_min": "avans_min",
    "termen_retragere_contract": "altele",
    # credite
    "valoare_rata_lunara": "rata_lunara",
    "comision_administrare_credit": "comision_administrare_credit",
    "rate_fara_dobanda": "numar_rate_fara_dobanda",
    "cost_asigurare_viata_lunar": "cost_asigurare",
    "dobanda_fixa_introductorie": "dobanda_fixa_introductiva",
}


def normalizeaza_camp(camp: str | None, produs: str) -> str:
    """
    Trece denumirea prin sinonime, apoi prin vocabularul produsului.

    Dacă rezultatul nu e în listă, devine `altele`. Nu se aruncă valoarea:
    citatul rămâne, iar frecvența lui `altele` spune când să lărgim lista.
    """
    permise = CAMPURI.get(produs, [])
    c = (camp or "").strip()
    c = SINONIME.get(c, c)
    return c if c in permise else "altele"


# ══════════════════════════════════════════════════════════════════
# 3. EXTRACȚIE
# ══════════════════════════════════════════════════════════════════

def unealta(produs: str, scenariu: dict | None = None) -> dict:
    # `potrivire_scenariu` se adaugă doar când cerem un scenariu. Fără el,
    # câmpul ar fi o întrebare fără context, iar modelul ar trebui să inventeze
    # un răspuns. Cu el, e chiar cheia de join a tabelului comparativ: fără o
    # afirmație explicită, „DAE 9,94%" și scenariul cerut ar fi lipite doar
    # fiindcă au apărut în același apel.
    potrivire = {
        "potrivire_scenariu": {
            "type": "string",
            "enum": ["exact", "aproximativ", "alt_scenariu", "neconditionat"],
            "description": (
                "OBLIGATORIU. Relația dintre valoare și scenariul cerut. "
                "`exact` — pagina dă chiar această valoare pentru suma, "
                "perioada și condițiile cerute. `aproximativ` — e pentru un "
                "caz vecin (altă sumă sau altă perioadă); scrie care în "
                "`conditii`. `alt_scenariu` — e pentru condiții diferite "
                "(cu asigurare, cu încasare venit, promoție). "
                "`neconditionat` — valoarea nu depinde de scenariu, se "
                "aplică oricui, ex. comisionul de analiză dosar. "
                "Nu pune `exact` dacă a trebuit să calculezi ceva."
            ),
        }
    } if scenariu else {}

    # `trepte` se cere numai la produsele care chiar au axe declarate. La un
    # cont curent, campul ar fi o intrebare fara raspuns, iar modelul l-ar
    # umple cu ceva.
    axe = CATALOG[produs].get("trepte") or []
    trepte = {
        "trepte": {
            "type": "array",
            "description": (
                "Pe ce treaptă se aplică valoarea, când pagina o spune. "
                "Câte un element pentru fiecare axă. Ex. un DAE publicat "
                "pentru „30.000 lei pe 60 de luni” dă două elemente: "
                "{dimensiune: suma, valoare: 30000} și "
                "{dimensiune: perioada, valoare: 60}. Un comision de "
                "rambursare anticipată de 1% „dacă perioada rămasă "
                "depășește un an” dă {dimensiune: perioada_ramasa, "
                "de_la: 12}. Listă GOALĂ dacă pagina nu leagă valoarea de "
                "nicio treaptă — nu ghici."
            ),
            "items": {
                "type": "object",
                "properties": {
                    "dimensiune": {"type": "string",
                                   "enum": [t["id"] for t in axe]},
                    "valoare": {"type": "number",
                                "description": "Punctul exact, când pagina îl dă."},
                    "valoare_text": {"type": "string",
                                     "description": "Pentru axe nenumerice, ex. valuta: „EUR”."},
                    "de_la": {"type": "number",
                              "description": "Capătul de jos al benzii, inclusiv."},
                    "pana_la": {"type": "number",
                                "description": "Capătul de sus al benzii, exclusiv."},
                },
                "required": ["dimensiune"],
            },
        }
    } if axe else {}

    return {
        "name": "raporteaza",
        "description": f"Raportează ce ai găsit despre {CATALOG[produs]['nume']}.",
        "input_schema": {
            "type": "object",
            "properties": {
                "gasit": {"type": "boolean",
                          "description": "false dacă produsul nu apare cu date în text."},
                "valori": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "camp": {"type": "string", "enum": CAMPURI[produs],
                                     "description": "Alege DIN LISTA. Dacă niciun câmp nu descrie faptul, folosește `altele` și completează `eticheta_libera`."},
                            "eticheta_libera": {"type": "string",
                                                "description": "OBLIGATORIU când `camp` e `altele`: ce este valoarea, în termenii paginii. Ex. „comision instituire poprire”, „speze SWIFT”, „dobândă penalizatoare”. Gol altfel."},
                            "cod_scenariu": {"type": "string",
                                             "description": "Obligatoriu când valoarea depinde de condiții. Format: TIP_SUMA_PERIOADA_CONDITII, ex. NP_30K_60L_VIRARE. Gol dacă valoarea e necondiționată."},
                            "valoare_num": {"type": "number"},
                            "valoare_text": {"type": "string",
                                             "description": "Doar când valoarea nu e numerică, ex. „gratuit” sau „negociabil”."},
                            "unitate": {"type": "string", "enum": ["procent", "lei", "eur", "usd", "zile", "luni", "ani", "numar", "puncte_procentuale", "altele"]},
                            "moneda": {"type": "string"},
                            "conditii": {"type": "array", "items": {"type": "string"},
                                         "description": "Condițiile de care depinde valoarea, una pe element, în termenii paginii. Scrie ce cere banca, nu o categorie: „încasarea salariului în cont”, „minimum 3 tranzacții cu cardul pe lună”, „sold mediu peste 40.000 lei”, „încheierea unei asigurări prin bancă”. LISTĂ GOALĂ dacă valoarea se aplică oricui, necondiționat — acela e prețul standard și e cel mai important de marcat corect."},
                            "valabil_de_la": {"type": "string", "description": "AAAA-LL-ZZ, dacă apare."},
                            "valabil_pana": {"type": "string", "description": "AAAA-LL-ZZ, dacă apare."},
                            "citat": {"type": "string",
                                      "description": "Fragmentul EXACT din text din care ai luat valoarea. Copiat literal, maximum 200 de caractere."},
                            "incredere": {"type": "number", "minimum": 0, "maximum": 1},
                            **potrivire,
                            **trepte,
                        },
                        "required": ["camp", "valoare_num", "unitate", "citat",
                                     "incredere"]
                                    + (["potrivire_scenariu"] if scenariu else []),
                    },
                },
                "nota": {"type": "string",
                         "description": "O propoziție: ce ai găsit în ansamblu, sau de ce nu ai găsit nimic."},
            },
            "required": ["gasit", "valori", "nota"],
        },
    }


def bloc_scenariu(scenariu: dict | None) -> str:
    """
    Partea din prompt care cere scenariul de referință.

    Nu restrânge extracția — asta ar fi o pierdere netă, fiindcă pagina se
    citește oricum o singură dată și valorile pe alte scenarii sunt tot date
    reale. Cere în plus: pe lângă ce găsește, modelul trebuie să spună pentru
    FIECARE valoare dacă e sau nu cazul cerut. Diferența e între un tabel în
    care coloanele se aliniază fiindcă am afirmat-o și unul în care se
    aliniază fiindcă au ieșit din același apel.
    """
    if not scenariu:
        return ""
    p = scenariu["parametri"]
    dep = ", ".join(scenariu["dependente"])
    ind = ", ".join(scenariu["independente"])
    return f"""
SCENARIU DE REFERINȚĂ: {scenariu['id']}
{scenariu['descriere_pentru_model']}
  sumă {p['suma']:,} {p['valuta']}, perioadă {p['perioada_luni']} luni
  fără asigurare, fără încasare venit la bancă, fără codebitor, fără promoție

Fiecare valoare primește `potrivire_scenariu`. Regulile:
  - Extragi TOT ce găsești despre produs, nu doar scenariul cerut. O valoare
    pentru alt caz se raportează cu `alt_scenariu` sau `aproximativ`, nu se
    aruncă.
  - `exact` numai dacă pagina publică acea cifră pentru chiar {p['suma']:,} \
{p['valuta']} pe {p['perioada_luni']} luni, în condițiile de mai sus. Dacă
    pagina dă un exemplu la altă sumă, e `aproximativ`, iar în `conditii`
    scrii suma și perioada reale din exemplu. NU recalculezi — regula 1.
  - Câmpurile astea depind de scenariu, deci nu pot fi `neconditionat`:
    {dep}
  - Câmpurile astea de obicei NU depind de scenariu, deci sunt
    `neconditionat` dacă pagina nu spune altceva: {ind}
  - Dacă pagina are un tabel cu mai multe sume și una dintre ele e chiar
    {p['suma']:,} {p['valuta']}, aceea e linia cu `exact`. Celelalte linii se
    raportează și ele, cu `aproximativ`.

  - O condiție care spune că un beneficiu LIPSEȘTE descrie chiar scenariul
    cerut, nu altul. „fără virare salarială”, „fără asigurare”, „dobânda
    standard, fără reduceri”, „client care nu îndeplinește condiția de
    rulaj”, „preț de listă” — toate confirmă cazul de referință. Acestea NU
    sunt `alt_scenariu`. Scrie-le oricum în `conditii`, ca să se vadă ce a
    spus pagina, dar potrivirea rămâne `exact` (dacă suma și perioada se
    potrivesc) sau `neconditionat` (dacă e un câmp care nu depinde de ele).
    `alt_scenariu` e numai pentru condiții care ADAUGĂ un beneficiu: cu
    asigurare, cu încasarea venitului, cu codebitor, cu promoție, client
    într-un program de fidelitate.

  - DAE e cifra după care se compară creditele între bănci. Dacă pagina o
    publică, raportează-o ca valoare separată, în câmpul `dae`, chiar dacă
    apare în aceeași frază cu rata și cu totalul plătibil. O citești acolo
    unde e, nu o rescrii dintr-un citat de la altă valoare.
"""


def bloc_trepte(produs: str) -> str:
    """
    Partea din prompt care descrie axele pe care variaza pretul.

    Rolul ei e sa ceara TOATA grila, nu o linie din ea. Pagina de depozite a
    unei banci are dobanzi la 1, 3, 6 si 12 luni in acelasi tabel; pana acum
    ieseau ca patru valori ale aceluiasi camp, indistinguibile intre ele, iar
    deduplicarea pastra una la intamplare. O cifra fara treapta ei nu e o
    cifra, e o jumatate de cifra.
    """
    axe = CATALOG[produs].get("trepte") or []
    if not axe:
        return ""
    linii = []
    for t in axe:
        if t.get("puncte"):
            grila = ", ".join(str(x) for x in t["puncte"])
            unde = f"valori uzuale: {grila} {t.get('unitate') or ''}".strip()
        elif t.get("benzi"):
            unde = "benzi: " + "; ".join(
                b.get("eticheta")
                or f"{b.get('de_la', '')}–{b.get('pana_la', '')}"
                for b in t["benzi"])
        else:
            unde = "valori: " + ", ".join(t.get("puncte_text") or [])
        linii.append(f"  `{t['id']}` — {t['nume']}. {unde}\n"
                     f"     se aplică la: {', '.join(t['campuri'])}")
    return f"""
TREPTE — prețul acestui produs variază pe axele astea:
{chr(10).join(linii)}

  - Dacă pagina publică un TABEL cu mai multe trepte, raportează FIECARE
    linie ca valoare separată, cu `trepte` completat. Nu alege una singură și
    nu face media. Patru dobânzi la patru durate sunt patru fapte.
  - Punctele de mai sus sunt axa pe care se compară băncile, nu o listă
    închisă. O dobândă publicată la 18 luni se raportează la 18.
  - `trepte` gol înseamnă că pagina nu leagă valoarea de nicio treaptă. Nu
    completa din ce pare rezonabil: o treaptă ghicită pune cifra pe rândul
    altcuiva.
"""


def sistem(produs: str, scenariu: dict | None = None) -> str:
    c = CATALOG[produs]
    # Sinonimele ajung la model, nu doar la `taie()`. Pagina numește produsul
    # cu termenii ei — „descoperit de cont" pentru overdraft, „Pachet ZERO"
    # pentru cont curent — iar fără lista asta modelul trebuie să ghicească
    # dacă secțiunea pe care o citește e despre produsul cerut.
    sinonime = ", ".join(c["keywords"]) if c["keywords"] else "—"
    return f"""Extragi date despre un singur produs bancar dintr-un text preluat de pe site-ul unei bănci.

PRODUS: {c['nume']}
CUM APARE ÎN PAGINĂ: {sinonime}
CE CAUȚI: {c['cauta']}
{bloc_trepte(produs)}{bloc_scenariu(scenariu)}
REGULI
1. Extragi doar ce apare LITERAL în text. Nu calculezi, nu deduci, nu completezi din cunoștințe generale.
2. `citat` e obligatoriu și trebuie copiat exact din text, fără reformulare. Fără citat valid, valoarea se respinge automat.
3. Fiecare valoare care depinde de condiții primește `cod_scenariu` și lista de `conditii`. O bancă poate publica trei DAE diferite pentru aceeași sumă și perioadă — sunt trei valori distincte, nu una.

3a. `conditii` GOL înseamnă „se aplică oricui”. Nu îl lăsa gol fiindcă n-ai găsit condiția: dacă pagina scrie „0*/60 lei” și nu vezi ce e asteriscul, valoarea de 0 primește condiția pe care o poți citi, fie și parțial („condiție marcată cu asterisc, neexplicitată în pagină”). Prețul necondiționat e reperul după care se compară băncile între ele, deci un preț promoțional marcat greșit ca necondiționat strică toată comparația.
4. Nu confunda dobânda nominală cu DAE. Sunt câmpuri separate.
5. Dacă produsul e doar menționat, fără cifre, întorci `gasit: false` și explici în `nota`.
6. Atenție la conținut expirat: dacă textul citează un indice sau o ofertă cu dată veche, pune `incredere` sub 0.5 și spune asta în `nota`.
7. Când nu ești sigur, `incredere` mică. Nu ghici.
9. `camp` se alege DIN LISTA din schema uneltei, nu se inventează. Dacă un fapt real nu are câmp potrivit în listă, folosești `altele` — citatul spune despre ce e vorba. Nu forța un fapt într-un câmp care descrie altceva: o dobândă pusă în `comision_administrare_lunar` e mai rea decât `altele`.
8. `unitate` e unitatea DIN TEXT, niciodată una convertită. „minim 1 an” se raportează ca 1 cu unitatea `ani`, nu ca 1 cu `luni` și nici ca 12. Regula 1 se aplică și unităților: nu transformi ani în luni, procente în puncte procentuale, sau o monedă în alta. Dacă unitatea din text nu există în listă, alegi `altele` și o scrii în `valoare_text`.

Raportezi întotdeauna prin unealta `raporteaza`."""


SISTEM_TEXT = """Esti un extractor de text, nu un rezumator si nu o sursa de informatie.

Primesti HTML brut. Intorci DOAR textul citibil din el, verbatim, in ordinea
din pagina. Pastrezi tabelele ca linii de forma "eticheta: valoare" sau cu
coloane separate prin " | ", ca sa nu se piarda perechile cifra-denumire.

Esti chemat tocmai pentru ca parserele clasice nu au gasit nimic. Deci cauta
continutul si acolo unde ele nu ajung: date structurate din <script> de tip
application/json, application/ld+json sau __NEXT_DATA__, atribute data-*,
continut din <template> sau <noscript>. Daca gasesti tarife intr-un JSON
inglobat, transcrie-le ca linii "denumire: valoare", inclusiv notele.

Reguli absolute:
- Nu inventa nimic. Daca o cifra nu e in HTML, nu apare in raspuns.
- Nu completa din ce stii despre banca sau despre produs.
- Nu reformula sumele, procentele, monedele sau denumirile de produs.
- Ignora cod JavaScript executabil, CSS, meniuri, footere si bannere de cookie.
- Daca HTML-ul chiar nu contine text util, raspunde exact: FARA_TEXT

Raspunzi doar cu textul extras, fara comentarii si fara markdown."""


async def extrage_text_llm(ai: AsyncAnthropic, html: str,
                           url: str) -> tuple[str, dict | None]:
    """
    Fallback de parsare cand trafilatura si selectolax nu scot nimic.

    Modelul primeste HTML pe care il avem deja; rolul lui e strict de parser mai
    bun, nu de sursa. Nu inlocuieste descarcarea si nu se foloseste niciodata
    pentru un document pe care nu l-am putut obtine.
    """
    r = await ai.messages.create(
        model=MODEL, max_tokens=16000, system=SISTEM_TEXT,
        messages=[{"role": "user",
                   "content": f"Sursa: {url}{PP}HTML:{PP}{html[:MAX_HTML_LLM]}"}],
    )
    text = "".join(b.text for b in r.content if b.type == "text").strip()
    tok = {"intrare": r.usage.input_tokens, "iesire": r.usage.output_tokens}
    if text == "FARA_TEXT" or len(text) < 40:
        return "", tok
    return text, tok


def fidelitate(text: str, html: str) -> float:
    """
    Cat din textul intors de model se regaseste chiar in HTML.

    Comparatia e pe tokeni, nu pe subsiruri: promptul cere tabelele
    reformatate ca "eticheta: valoare", deci potrivirea exacta ar respinge si
    text corect. Regula pe cifre ramane insa stricta — orice numar care nu
    apare in HTML descalifica linia, fiindca exact acolo ar aparea o valoare
    inventata. Fara pragul asta, un parser LLM ar putea strecura continut
    fabricat inainte ca `valideaza` sa apuce sa verifice citatele.
    """
    ref = normalizeaza_citat(re.sub(r"<[^>]+>", " ", html))
    cuvinte = set(re.findall(r"[^\W_]+", ref))

    linii = [l.strip() for l in text.splitlines() if len(l.strip()) > 25]
    if not linii:
        return 0.0

    bune = 0
    for l in linii:
        toc = re.findall(r"[^\W_]+", normalizeaza_citat(l))
        if not toc:
            continue
        cifre = [t for t in toc if any(c.isdigit() for c in t)]
        if any(c not in cuvinte for c in cifre):
            continue                      # numar inexistent in sursa
        if sum(1 for t in toc if t in cuvinte) / len(toc) >= 0.8:
            bune += 1
    return bune / len(linii)


async def extrage(ai: AsyncAnthropic, produs: str, text: str, url: str,
                  scenariu: dict | None = None, focus: str | None = None) -> dict:
    """
    `focus`: produsul anume al băncii căutat în document (ex. „Pachetul de cont
    curent IMM Ultra"). Fără el, un PDF de tarife întoarce toate pachetele de
    același tip: la Raiffeisen, ELITE primea 7 comisioane lunare (0-199 lei),
    aceleași ca PRIME și PRESTIGE, deși doar 199 lei (Ultra) era al lui.
    """
    # max_tokens generos: pe Opus 5 gândirea e activă implicit și se scade din
    # acelasi buget ca răspunsul. Cu 6000 o pagină cu 141 de rânduri de tarife
    # s-ar tăia la jumătate, iar `tool_use` ar veni trunchiat.
    antet = f"Sursă: {url}\n\n"
    if focus:
        antet += f"PRODUSUL CĂUTAT ÎN ACEST DOCUMENT\n{focus}\n\n"
    r = await ai.messages.create(
        model=MODEL, max_tokens=16000, system=sistem(produs, scenariu),
        tools=[unealta(produs, scenariu)],
        tool_choice={"type": "tool", "name": "raporteaza"},
        messages=[{"role": "user",
                   "content": f"{antet}TEXT:\n\n{text[:MAX_CARACTERE_LLM]}"}],
    )
    for b in r.content:
        if b.type == "tool_use":
            rez = {**b.input, "_tokeni": {"intrare": r.usage.input_tokens,
                                          "iesire": r.usage.output_tokens}}
            # Plasa de siguranță: enumul din schemă ar trebui să fi împiedicat
            # deja un nume inventat, dar `strict` nu e activat pe unealtă, deci
            # normalizăm oricum. Costă nimic și prinde regresiile.
            for v in rez.get("valori") or []:
                v["camp"] = normalizeaza_camp(v.get("camp"), produs)
            return rez
    # Fără bloc `tool_use`, motivul contează: refuz, buget de tokeni epuizat
    # sau altceva. „Nu a apelat unealta" singur ar ascunde diferența.
    motiv = f"modelul nu a apelat unealta (stop_reason: {r.stop_reason})"
    if r.stop_reason == "refusal":
        cat = getattr(r.stop_details, "category", None)
        motiv = f"cerere refuzată de clasificatoarele de siguranță ({cat})"
    return {"gasit": False, "valori": [], "nota": motiv,
            "_tokeni": {"intrare": r.usage.input_tokens,
                        "iesire": r.usage.output_tokens}}


# ══════════════════════════════════════════════════════════════════
# 4. VALIDARE
# ══════════════════════════════════════════════════════════════════

def normalizeaza_citat(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().replace("\u00a0", " ")).strip()


def fara_marcaj(s: str) -> str:
    """
    Aceeași normalizare, plus zgomotul de markdown.

    Textul venit prin `web_fetch` e markdown: tabelele au celule `**bold**`,
    `<br>` între linii și padding de aliniere. Modelul citează rândul turtit,
    fără ele, deci potrivirea pe subșir exact respinge valori corecte. Pe
    pagina de taxe a BT, 13 din 20 de respingeri erau de forma asta.

    Nu slăbim verificarea: citatul tot trebuie să existe în sursă, doar că
    egalitatea se judecă după conținut, nu după formatare. Cifrele, denumirile
    și ordinea rămân obligatorii.
    """
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.I)
    s = s.replace("*", "").replace("\\", "")
    s = re.sub(r"\s*\|\s*", " | ", s)
    return normalizeaza_citat(s)


# Unitățile de timp se confundă ușor, iar greșeala nu se vede: „1 an" raportat
# ca `luni` e greșit de douăsprezece ori și arată la fel de plauzibil ca oricare
# altă valoare. Dacă citatul numește o unitate de timp diferită de cea
# raportată, valoarea nu trece.
# Unitatile pe care intervalul din CATALOG le poate judeca. Pentru sume nu
# exista un interval plauzibil per produs: un comision de analiza dosar de 900
# lei si o dobanda de 9% sunt amandoua normale, dar nu incap in acelasi interval.
UNITATI_PROCENT = {"procent", "puncte_procentuale"}

# Prefixe de camp care descriu o durata sau o varsta. Acolo o unitate de bani
# semnaleaza un camp greșit, nu o valoare greșita.
DURATA_PREFIX = ("perioada", "termen", "varsta", "vechime")

UNITATI_TIMP = {
    "zile": r"\bzi\b|\bzile\b",
    "luni": r"\blun[ăai]\b|\bluni\b",
    "ani": r"\ban\b|\bani\b",
}


CONTEXT_CITAT = int(os.getenv("CONTEXT_CITAT", "150"))


def context_citat(citat: str, text: str) -> tuple[str | None, int]:
    """
    Citatul scurt, lărgit cu textul din jurul lui din același document.

    Un citat ca „DAE=9,94%" e o cifră adevărată, dar nu spune la ce exemplu se
    referă: pe BCR, 300 de valori erau respinse doar pentru asta, multe cu
    încredere 0,9. Aici se caută citatul în text (spațiile se potrivesc
    flexibil) și se ia rândul sau propoziția din jur, până la ±CONTEXT_CITAT
    caractere. Determinist: modelul nu e întrebat nimic.

    @returns (contextul, de câte ori apare citatul). Context None = citatul nu
             e în text, deci rămâne respins. Mai multe apariții = nu se știe
             care e cea bună; se ia prima, iar apelantul o marchează.
    """
    tokeni = citat.split()
    if not tokeni:
        return None, 0
    rx = re.compile(r"\s+".join(re.escape(t) for t in tokeni), re.IGNORECASE)
    potriviri = list(rx.finditer(text))
    if not potriviri:
        return None, 0
    m = potriviri[0]
    st, dr = max(0, m.start() - CONTEXT_CITAT), min(len(text), m.end() + CONTEXT_CITAT)
    stanga, dreapta = text[st:m.start()], text[m.end():dr]
    # se oprește la marginea rândului sau a propoziției, dacă e în fereastră
    taieri = [stanga.rfind("\n"), stanga.rfind(". ")]
    t = max(taieri)
    if t >= 0:
        rest = stanga[t + 1:]
        if rest.strip():
            stanga = rest
        else:
            # Citatul începe rândul: exemplul la care se referă e de obicei pe
            # rândul de deasupra („credit de 30.000 lei pe 60 luni" / „DAE=9,94%").
            anterior = stanga[:t].rstrip()
            stanga = anterior[anterior.rfind("\n") + 1:] + " " + rest
    capete = [i for i in (dreapta.find("\n"), dreapta.find(". ")) if i >= 0]
    if capete:
        dreapta = dreapta[:min(capete) + 1]
    ctx = re.sub(r"\s+", " ", (stanga + m.group(0) + dreapta)).strip()
    return ctx, len(potriviri)


def valideaza(valori: list[dict], produs: str, text: str) -> tuple[list[dict], list[dict]]:
    """Citatul trebuie să existe în sursă. Valoarea trebuie să fie plauzibilă."""
    ref = normalizeaza_citat(text)
    ref_curat = fara_marcaj(text)
    interval = CATALOG[produs].get("interval", {}).get("valoare_num")

    # Un câmp care apare de mai multe ori trebuie separat prin `cod_scenariu`.
    # Patru valori numite identic, fără cod, sunt patru fapte care nu se pot
    # deosebi în `observations` — iar dacă diferă între ele, se contrazic fără
    # ca nimic din rezultat să spună care e care.
    nr_camp = Counter(v.get("camp") for v in valori)
    nr_cheie = Counter((v.get("camp"), (v.get("cod_scenariu") or "").strip())
                       for v in valori)

    ok, respinse = [], []

    for v in valori:
        motive = []
        citat = normalizeaza_citat(v.get("citat", ""))
        if not citat:
            motive.append("citat lipsă")
        elif len(citat) < MIN_CARACTERE_CITAT:
            # Un citat de câteva caractere — „Gratuit", „3,5 LEI" — se
            # regăsește în orice pagină și nu dovedește din ce rând vine.
            # Dacă e totuși în document, se lărgește cu contextul lui și trece;
            # altfel rămâne respins.
            ctx, aparitii = context_citat(v.get("citat", ""), text)
            if ctx and len(normalizeaza_citat(ctx)) >= MIN_CARACTERE_CITAT:
                v["citat_original"] = v.get("citat")
                v["citat"] = ctx
                if aparitii > 1:
                    v["citat_aparitii"] = aparitii
                citat = normalizeaza_citat(ctx)
            else:
                motive.append(f"citat prea scurt ({len(citat)} caractere, "
                              f"minim {MIN_CARACTERE_CITAT})")
        elif citat not in ref:
            citat_curat = fara_marcaj(v.get("citat", ""))
            if citat_curat in ref_curat:
                v["citat_normalizat"] = True     # potrivit după curățarea marcajului
            elif citat[:60] in ref:
                v["citat_partial"] = True        # trunchiere sau spațiere
            else:
                motive.append("citatul nu apare în textul sursă")

        # Câmpul duplicat nu mai respinge, doar marchează.
        #
        # Regula a fost scrisă înainte de vocabularul închis, când cele cinci
        # prețuri de abonament BT aveau cinci nume diferite și nu se ciocneau
        # niciodată. După normalizare toate devin `cost_lunar`, iar regula a
        # început să respingă valori bune: măsurat pe ING, 50 din 65 de
        # respingeri aveau duplicatul ca SINGUR motiv — printre ele
        # `cost_lunar = 40 lei`, cu citatul „FIX Util(40 RON)", un preț real.
        #
        # Ambiguitatea rămâne o problemă, deci nu dispare: valoarea trece, dar
        # cu `conflict_scenariu`, ca să ajungă la review în loc să se piardă.
        camp = v.get("camp")
        cod = (v.get("cod_scenariu") or "").strip()
        if nr_camp[camp] > 1:
            if not cod:
                v["conflict_scenariu"] = (
                    f"câmpul „{camp}” apare de {nr_camp[camp]} ori, "
                    "iar această valoare nu are cod_scenariu")
            elif nr_cheie[(camp, cod)] > 1:
                v["conflict_scenariu"] = (
                    f"câmpul „{camp}” apare de {nr_cheie[(camp, cod)]} ori "
                    f"cu același cod_scenariu „{cod}”")

        unitate = v.get("unitate")
        if unitate in UNITATI_TIMP and citat:
            gasite = [u for u, rx in UNITATI_TIMP.items() if re.search(rx, citat)]
            if gasite and unitate not in gasite:
                motive.append(f"unitatea „{unitate}” nu apare în citat, "
                              f"dar apare „{gasite[0]}”")

        # Un câmp de durată cu unitate de bani e un câmp greșit, nu o valoare
        # greșită: `perioada_maxima = 1500000 lei` e o sumă pusă sub o
        # denumire de perioadă. Verificarea asta prinde exact ce pierde
        # intervalul acum că nu se mai aplică sumelor.
        if (any(camp.startswith(p) for p in DURATA_PREFIX)
                and unitate and unitate not in UNITATI_TIMP):
            motive.append(f"câmpul „{camp}” e o durată, dar unitatea e "
                          f"„{unitate}”")

        val = v.get("valoare_num")
        # Intervalul din CATALOG e calibrat pe procente — [0, 40] pentru
        # dobânzi, [0, 15] pentru marje. Aplicat orbește, respingea comisioane
        # reale: `comision_analiza_dosar = 900 lei` cădea în afara lui [0, 40].
        # Pe ING, 62 din 65 de respingeri pe interval erau valori în lei.
        # Pentru sume nu există un interval plauzibil per produs, deci nu se
        # verifică — coerența câmp/unitate de mai sus face acea muncă.
        if (interval and unitate in UNITATI_PROCENT
                and isinstance(val, (int, float))
                and not (interval[0] <= val <= interval[1])):
            motive.append(f"valoare în afara intervalului plauzibil {interval} "
                          f"pentru unitatea „{unitate}”")

        if v.get("incredere", 1) < PRAG_INCREDERE:
            motive.append(f"încredere {v.get('incredere')} sub pragul {PRAG_INCREDERE}")

        (respinse if motive else ok).append({**v, "motive": motive} if motive else v)

    return ok, respinse


# ══════════════════════════════════════════════════════════════════
# 5. FORMA `observations`
# ══════════════════════════════════════════════════════════════════

def _id_observatie(*parti: Any) -> str:
    """
    Cheie deterministă peste (url, produs, câmp, scenariu, hash de conținut).

    Aceeași valoare, din același document neschimbat, primește același id la
    fiecare rulare. Fără asta, jobul nocturn ar insera duplicate în loc să
    actualizeze rândul existent.
    """
    brut = "|".join("" if x is None else str(x) for x in parti)
    return hashlib.sha256(brut.encode("utf-8")).hexdigest()[:32]


def cheie_trepte(trepte: list | None) -> str:
    """
    Treptele unei valori, ca sir stabil — parte din identitatea randului.

    Fara ea, cele patru dobanzi de pe grila unui depozit (1, 3, 6, 12 luni)
    ies din acelasi document, cu acelasi camp si acelasi `cod_scenariu` gol,
    deci cu ACELASI id. Jobul care insereaza dupa id le-ar strange in una
    singura, pastrata la intamplare — exact cifra pe care nimeni n-a cerut-o.

    Sortarea pe `dimensiune` face cheia independenta de ordinea in care
    modelul a enumerat axele; altfel aceeasi valoare ar primi doua id-uri
    intre doua rulari.
    """
    if not trepte:
        return ""
    parti = []
    for t in sorted(trepte, key=lambda x: str(x.get("dimensiune"))):
        parti.append("{}={}:{}:{}:{}".format(
            t.get("dimensiune"),
            t.get("valoare", ""), t.get("valoare_text", ""),
            t.get("de_la", ""), t.get("pana_la", "")))
    return ",".join(parti)


def motiv_negasit(d: dict, rez: dict) -> str:
    """
    De ce n-a fost gasit produsul. Trei cauze diferite, care NU se confunda.

    `sursa_inaccesibila` e cea mai importanta de separat: acolo limitarea e
    a noastra, nu a bancii. O valoare adusa prin `web_fetch` n-are octeti
    bruti, iar un document blocat nu s-a citit deloc — in ambele cazuri
    „nu am gasit” nu autorizeaza afirmatia „banca nu percepe”.
    """
    # Tot ce vine din raspunsul modelului se trateaza defensiv: un raspuns
    # malformat a picat un document intreg pe BID, o singura data din 344, si
    # nu s-a reprodus. Un camp cu forma neasteptata nu trebuie sa coste
    # documentul — se raporteaza `negasit_in_pagina` si se merge mai departe.
    if not isinstance(d, dict):
        return "negasit_in_pagina"
    sanit = rez.get("sanitizare")
    if isinstance(sanit, str):
        sanit = {"metoda": sanit}
    if (sanit or {}).get("metoda") == "web_fetch":
        return "sursa_inaccesibila"
    if rez.get("stare") in ("blocat", "neacoperit"):
        return "sursa_inaccesibila"
    # Modelul a citit pagina si a spus explicit ca produsul nu e al bancii.
    nota = (d.get("nota") or "").lower()
    if any(t in nota for t in ("nu ofera", "nu oferă", "nu are acest produs",
                               "nu comercializeaza", "nu comercializează")):
        return "produs_inexistent"
    # Pagina s-a citit, produsul e mentionat, dar fara cifre publicate.
    if any(t in nota for t in ("nu publica", "nu publică", "la cerere",
                               "personalizat", "negociabil", "contactati",
                               "contactați")):
        return "nepublicat"
    return "negasit_in_pagina"


def ca_observatii(rez: dict, id_url: str | None = None) -> list[dict]:
    """
    Rezultatul, ca rânduri pentru tabelul `observations`.

    Intră DOAR valorile acceptate de `valideaza`. Cele respinse rămân în
    formatul complet, pentru review: o valoare al cărei citat nu s-a putut
    verifica nu are ce căuta într-un tabel de fapte.

    `id_produs` e slugul din CATALOG, același cu cel folosit în inventar. Dacă
    tabelul tău de produse are chei numerice, maparea se face la inserare.

    `unitate` și `citat` nu sunt decorative, deși nu apar în diagrama inițială.
    Fără `unitate`, `valoare_num` e un număr fără înțeles: pe pagina de leasing
    a BT, `valoare_reziduala_min = 1` înseamnă un procent, iar
    `perioada_finantare_min = 1` înseamnă un an — același număr, lucruri
    diferite. Fără `citat`, nicio valoare nu mai poate fi legată de rândul din
    care a fost citită, iar pe documentele fără Bronze acela e singurul fir
    care rămâne către sursă.
    """
    hash_continut = rez.get("content_hash")
    id_url = id_url or rez.get("url")
    randuri: list[dict] = []

    for id_produs, d in (rez.get("rezultate") or {}).items():
        if not isinstance(d, dict):     # raspuns malformat; vezi motiv_negasit
            d = {"gasit": False, "valori": [], "nota": str(d)[:200]}
        # Produs cerut, nimic gasit: un rand NEGATIV, nu tacere. `nota`
        # modelului spune de ce, iar motivul canonic il clasifica. Fara
        # randul asta, singura urma a celor 31% de cautari fara rezultat ar
        # fi absenta — care nu se poate deosebi de „n-am cautat niciodata".
        if not d.get("gasit") and not d.get("valori"):
            randuri.append({
                "id": _id_observatie(id_url, id_produs, "*negasit*", None,
                                     hash_continut),
                "id_url": id_url,
                "id_produs": id_produs,
                "camp": None,
                "not_found": True,
                "not_found_motiv": motiv_negasit(d, rez),
                "nota": d.get("nota"),
                "content_hash": hash_continut,
                "conditii": [],
                "necesita_verificare": False,
            })
            continue
        for v in d.get("valori", []):
            cod = (v.get("cod_scenariu") or "").strip() or None
            randuri.append({
                "id": _id_observatie(id_url, id_produs, v.get("camp"),
                                     cod, cheie_trepte(v.get("trepte")),
                                     hash_continut),
                "id_url": id_url,
                "id_produs": id_produs,
                "camp": v.get("camp"),
                "cod_scenariu": cod,
                "valoare_num": v.get("valoare_num"),
                "unitate": v.get("unitate"),
                "valid_from": v.get("valabil_de_la") or None,
                "valid_to": v.get("valabil_pana") or None,
                "content_hash": hash_continut,
                # Text liber, deliberat. Vocabularul canonic se derivă mai
                # târziu, dintr-o pasă peste observațiile acumulate: închis
                # acum, ar fi scris pe trei bănci și refăcut la a patra.
                # Lista goală e o afirmație — „preț necondiționat” — nu o
                # lipsă de date.
                "conditii": v.get("conditii") or [],
                # Ce e valoarea, când vocabularul n-a avut câmp pentru ea.
                # Fără asta, un rând `altele` își pierde înțelesul: rămâne o
                # cifră cu o unitate, iar ce anume costă 25 de lei se poate
                # citi doar din citat.
                "eticheta_libera": (v.get("eticheta_libera") or "").strip() or None,
                "citat": v.get("citat"),
                # Citatul scurt dat de model, când `citat` e contextul lărgit din
                # document (context_citat), și de câte ori apărea el acolo.
                "citat_original": v.get("citat_original"),
                "citat_aparitii": v.get("citat_aparitii"),
                "confidence": v.get("incredere"),
                # Adevarat pentru zona de mijloc. Nu blocheaza valoarea, dar
                # o tine deosebita de cele sigure in orice agregare.
                "necesita_verificare": (v.get("incredere") or 0) < PRAG_SIGUR,
                "not_found": False,
                "not_found_motiv": None,
                "nota": None,
                # Ambiguitatea de scenariu nu blocheaza valoarea, dar trebuie
                # sa ajunga in tabel: altfel doua rânduri care nu se pot
                # deosebi arata ca doua fapte independente.
                "conflict_scenariu": v.get("conflict_scenariu"),
                # Afirmatia modelului despre scenariul de referinta cerut.
                # `None` cand nu s-a cerut niciun scenariu — deosebit de
                # `alt_scenariu`, care inseamna ca s-a cerut si nu se potriveste.
                "potrivire_scenariu": v.get("potrivire_scenariu"),
                # Treapta pe care se aplica valoarea. Lista goala nu inseamna
                # „nu are treapta", inseamna „pagina nu a spus" — si asta e
                # tot o constatare, nu o lipsa de date.
                "trepte": v.get("trepte") or [],
            })
    return randuri


# ══════════════════════════════════════════════════════════════════
# ORCHESTRARE
# ══════════════════════════════════════════════════════════════════

async def proceseaza(
    html: str,
    metoda: str,
    produse: list[str],
    url: str | None = None,
    hash_anterior: str | None = None,
    include_text: bool = False,
    scenariu: dict | bool | None = None,
    focus: str | None = None,
) -> dict:
    """
    html           conținutul paginii, deja descărcat de router
    metoda         "http" sau "playwright" — cum a fost obținut. Metadată, dar
                   folosită la diagnostic: dacă sanitizarea nu produce text și
                   metoda era http, pagina e probabil randată din JavaScript.
    produse        produsele asociate acestui document la discovery
    url            doar pentru context în prompt și în rezultat
    hash_anterior  hashul din rularea precedentă; dacă e identic, nu se extrage
    include_text   adaugă `text_sanitizat` în rezultat. Implicit nu: routerul
                   are bytes-urile brute în Bronze, deci textul ar fi o copie
                   inutilă. Contează pe ramura `web_fetch`, unde Bronze nu
                   există și textul e singurul exemplar al dovezii.
    scenariu       cazul de referință cerut, din `scenarii.json`. `None` ia
                   scenariul implicit al produsului, dacă are unul; `False`
                   îl dezactivează explicit. Nu restrânge ce se extrage, cere
                   în plus o afirmație de potrivire pe fiecare valoare.
    """
    acum = datetime.now(timezone.utc).isoformat()
    necunoscute = [p for p in produse if p not in CATALOG]
    produse = [p for p in produse if p in CATALOG]

    baza: dict[str, Any] = {
        "url": url, "tip": "html", "metoda": metoda, "procesat_la": acum,
        "produse_cerute": produse,
    }
    if necunoscute:
        baza["produse_necunoscute"] = necunoscute
    if not produse:
        return {**baza, "stare": "eroare",
                "eroare": "niciun produs cunoscut în listă", "rezultate": {}}
    if not (html or "").strip() and not (url and WEB_FETCH_ACTIV):
        return {**baza, "stare": "eroare",
                "eroare": "conținut HTML gol și niciun fallback disponibil",
                "rezultate": {}}

    # 1 ── sanitizare
    # HTML gol e permis: se intră direct pe ramura de fallback, care cere
    # pagina prin API. Asta acoperă cazul în care descărcarea locală a fost
    # refuzată și routerul ne pasează doar URL-ul.
    s = sanitizeaza(html) if (html or "").strip() else Sanitizat(text="", lungime_html=0)
    # Câmpurile derivate din HTML se raportează doar dacă am avut HTML. Pe
    # ramura de fallback `sanitizeaza` nu rulează, deci `titlu`, `procente_gasite`
    # și `sume_gasite` ar ieși goale, iar `reducere` ar da 100% din împărțirea
    # la zero — cifre care arată ca măsurători fără să fie.
    are_html = s.lungime_html > 0
    baza["sanitizare"] = {
        "metoda": s.metoda_curatare,
        **({"lungime_html": s.lungime_html} if are_html else {}),
        "lungime_text": len(s.text),
        **({"reducere": f"{100 - round(len(s.text) / s.lungime_html * 100)}%",
            "titlu": s.titlu,
            "procente_gasite": s.procente[:15],
            "sume_gasite": s.sume[:10]} if are_html else {}),
    }
    if not s.text.strip():
        # Fallback în două trepte.
        #
        # (a) Modelul ca parser peste HTML-ul pe care îl avem deja. Nu aduce
        #     conținut nou; doar citește mai bine decât trafilatura/selectolax.
        # (b) Dacă tot nimic — sau dacă nici HTML nu avem, fiindcă descărcarea
        #     locală a fost refuzată — se cere pagina prin `web_fetch`. Aceea e
        #     o cerere HTTP reală, executată din infrastructura Anthropic.
        #     Conținutul e al paginii, nu generat de model.
        #
        # Diferența față de „reconstituire dintr-un LLM" e esențială: acolo
        # modelul ar inventa valori plauzibile; aici doar transportă ce a citit.
        t_llm, tok = ("", None)
        if (html or "").strip() and os.getenv("FALLBACK_TEXT_LLM", "1") != "0":
            t_llm, tok = await extrage_text_llm(
                AsyncAnthropic(), html, url or "(sursa nespecificata)")
        fid = fidelitate(t_llm, html) if (t_llm and html) else 0.0

        if t_llm and fid >= PRAG_FIDELITATE:
            s.text, s.metoda_curatare = t_llm, "llm"
            baza["sanitizare"].update({
                "metoda": "llm", "lungime_text": len(t_llm),
                "fidelitate": round(fid, 3), "tokeni_text": tok,
            })
        else:
            t_api, meta_api = ("", None)
            if url and WEB_FETCH_ACTIV:
                t_api, meta_api = await adu_text_api(url)

            if t_api:
                s.text, s.metoda_curatare = t_api, "web_fetch"
                baza["sanitizare"].update({
                    "metoda": "web_fetch", "lungime_text": len(t_api),
                    "fidelitate": None,
                })
                # Proveniența merge mai departe în `observations`: valorile
                # obținute așa nu au bytes bruți în Bronze și nu pot fi
                # reverificate față de marcajul original.
                baza["provenienta"] = meta_api
                baza["avertisment"] = (
                    "conținut obținut prin web_fetch, nu prin descărcare proprie; "
                    "fără Bronze, fără verificare de fidelitate față de HTML"
                )
            else:
                avert = ("sanitizarea nu a produs text"
                         if (html or "").strip() else "HTML indisponibil local")
                if t_llm:
                    avert += (f"; fallbackul LLM a întors text cu fidelitate {fid:.0%}"
                              f" sub pragul de {PRAG_FIDELITATE:.0%} — respins ca nesigur")
                elif tok:
                    avert += "; fallbackul LLM nu a găsit text util în HTML"
                if meta_api and meta_api.get("eroare"):
                    avert += f"; web_fetch a eșuat: {meta_api['eroare']}"
                elif meta_api:
                    avert += "; web_fetch nu a întors conținut"
                elif url and not WEB_FETCH_ACTIV:
                    avert += "; fallbackul web_fetch e dezactivat (FALLBACK_WEB_FETCH=0)"
                if metoda == "http" and (html or "").strip():
                    avert += ("; pagina e probabil randată din JavaScript — "
                              "marchează documentul pentru metoda playwright")
                return {**baza, "stare": "gol", "avertisment": avert,
                        "rezultate": {}, "tokeni_text": tok,
                        "provenienta": meta_api}

    # 2 ── hash pe textul sanitizat
    h = hash_stabil(s.text)
    baza["content_hash"] = h
    if include_text:
        baza["text_sanitizat"] = s.text
    if hash_anterior and h == hash_anterior:
        return {**baza, "stare": "neschimbat", "rezultate": {},
                "nota": "conținut identic cu rularea anterioară; extracția nu a rulat"}

    # 3 ── extracție per produs, în paralel
    #
    # Textul integral, nu fragmente. Modelul e parserul, iar contextul lui e
    # cu mult mai mare decât o pagină de tarife. Fragmentarea pe keyword se
    # ancora pe PRIMA potrivire, care pe orice site e în head sau în meniu:
    # pe pagina de taxe a BT trimitea 1.717 caractere de meta tags în loc de
    # tabelele care începeau la caracterul 23.187. Un tabel nu se poate tăia
    # bine fără să înțelegi ce e în el, deci nu se taie.
    #
    # `taie` rămâne doar pentru documentele care nu încap în buget — acolo
    # alegerea nu e între fragment și integral, ci între fragment și trunchiat.
    ai = AsyncAnthropic()

    async def unul(p: str) -> tuple[str, dict]:
        frag, mod = s.text, "text_integral"
        if len(s.text) > MAX_CARACTERE_LLM:
            t = taie(s.text, CATALOG[p]["keywords"])
            mod = "fragment" if t else "trunchiat"
            frag = (t or s.text)[:MAX_CARACTERE_LLM]
        # Scenariul cerut explicit bate implicitul produsului; `False` (nu
        # `None`) dezactivează scenariul cu totul, pentru rulările libere.
        sc = scenariu if scenariu is not None else scenariu_implicit(p)
        rez = await extrage(ai, p, frag, url or "(sursă nespecificată)",
                            sc or None, focus=focus)
        ok, respinse = valideaza(rez.get("valori", []), p, frag)
        return p, {
            "gasit": bool(ok) and rez.get("gasit", False),
            "valori": ok,
            "respinse": respinse,
            "nota": rez.get("nota"),
            "mod_text": mod,
            "caractere_trimise": len(frag),
            "tokeni": rez.get("_tokeni"),
        }

    rezultate = dict(await asyncio.gather(*[unul(p) for p in produse]))

    return {
        **baza,
        "stare": "extras",
        "rezultate": rezultate,
        "bilant": {
            "produse_cerute": len(produse),
            "produse_gasite": sum(1 for r in rezultate.values() if r["gasit"]),
            "valori_acceptate": sum(len(r["valori"]) for r in rezultate.values()),
            "valori_respinse": sum(len(r["respinse"]) for r in rezultate.values()),
            "tokeni_intrare": sum((r["tokeni"] or {}).get("intrare", 0) for r in rezultate.values()),
            "tokeni_iesire": sum((r["tokeni"] or {}).get("iesire", 0) for r in rezultate.values()),
        },
    }


# ══════════════════════════════════════════════════════════════════
# CLI — doar pentru testare izolată.
# În producție, routerul importă `proceseaza` și îi dă HTML-ul deja descărcat.
# ══════════════════════════════════════════════════════════════════

# Coduri pe care le tratăm ca refuz de acces, nu ca eroare de transport.
STATUS_REFUZ = (401, 403, 429, 451)

# Unele WAF-uri întorc 200 cu o pagină de refuz în loc de un cod de eroare.
# Fără verificarea asta, pagina de blocaj ajunge la sanitizare și iese „gol”,
# ceea ce ar trimite diagnosticul spre „randat din JavaScript” — greșit.
BLOCAJ_IN_PAGINA = re.compile(
    r"access denied|access to this page|request blocked|forbidden"
    r"|you (have been|are) blocked|attention required|error 10\d\d"
    r"|acces(ul)? (refuzat|interzis|blocat)|nu aveti (dreptul|permisiunea)",
    re.I,
)

# Sub atâtea caractere, un text de refuz e aproape sigur pagina de blocaj și nu
# o mențiune întâmplătoare în conținutul real al unei pagini de tarife.
MAX_PAGINA_BLOCAJ = 40_000


def _pare_pagina_de_blocaj(html: str) -> bool:
    if len(html) > MAX_PAGINA_BLOCAJ:
        return False
    return bool(BLOCAJ_IN_PAGINA.search(re.sub(r"<[^>]+>", " ", html)))


class AccesRefuzat(Exception):
    """
    Serverul a refuzat explicit cererea (401/403/429/451), sau a întors o
    pagină de refuz cu cod 200.

    Nu e o eroare de transport si nu se repara din cod: e o decizie de acces a
    detinatorului sitului. Singurele raspunsuri corecte sunt sa marchezi
    documentul ca blocat si sa ceri acces. Continutul NU se reconstituie dintr-un
    model de limbaj — un LLM ar genera valori plauzibile, nu valorile publicate,
    iar `valideaza` le-ar da un scor de incredere care le-ar face sa arate ca
    fapte masurate.
    """

    def __init__(self, url: str, status: int, corp: str = "") -> None:
        self.url = url
        self.status = status
        self.reference_id = _prim_grup(r"Reference ID:\s*([\w.\-]{8,})", corp)
        self.client_ip = _prim_grup(r"Client IP:\s*([0-9a-fA-F.:]{7,})", corp)
        super().__init__(f"{status} pentru {url}")


def _prim_grup(sablon: str, text: str) -> str | None:
    if not text:
        return None
    m = re.search(sablon, re.sub(r"<[^>]+>", " ", text), re.I | re.S)
    return m.group(1).strip() if m else None


def raport_blocat(
    exc: AccesRefuzat,
    metoda: str,
    produse: list[str],
    nivel_ip: bool | None = None,
) -> dict:
    """
    Rezultatul pe care routerul il primeste cand un document e inaccesibil.

    Aceeasi forma ca a lui `proceseaza`, ca sa intre in acelasi pipeline: o
    rulare pe 40 de banci nu trebuie sa cada pentru ca una refuza accesul.
    `rezultate` e gol — nu partial, nu presupus.
    """
    blocaj: dict[str, Any] = {"status_http": exc.status}
    if exc.reference_id:
        blocaj["reference_id"] = exc.reference_id
    if exc.client_ip:
        blocaj["client_ip"] = exc.client_ip
    if nivel_ip is not None:
        blocaj["nivel"] = "ip" if nivel_ip else "path_sau_client"
        blocaj["robots_accesibil"] = not nivel_ip

    return {
        "url": exc.url, "tip": "html", "metoda": metoda,
        "procesat_la": datetime.now(timezone.utc).isoformat(),
        "produse_cerute": produse,
        "stare": "blocat",
        "blocaj": blocaj,
        "rezultate": {},
        "actiune": ("cere acces de la detinatorul sitului; dupa acord, alimenteaza "
                    "documentul prin --fisier / routerul cu HTML obtinut legitim"),
    }


async def adu_http(url: str, **kw):
    """
    GET, cu o a doua incercare fara compresie.

    DE CE EXISTA

    Unele servere trimit antetul `Transfer-Encoding` de doua ori, dar numai
    cand raspunsul e comprimat. `h11` il respinge strict si ridica
    `RemoteProtocolError`, deci documentul se pierde intreg — nu partial, nu
    degradat, ci ca si cum pagina n-ar exista. curl nu pateste asta fiindca nu
    cere compresie implicit, ceea ce face defectul greu de vazut: pagina se
    deschide perfect din terminal si cade doar in conducta.

    Masurat pe patriabank.ro: 23 din 23 de documente cadeau asa, iar banca
    iesea din toate clasamentele ca si cum n-ar publica preturi. Cu `identity`,
    aceeasi pagina intoarce 200 si 146 KB.

    A doua incercare cere `identity`. Costa banda, dar numai pe serverele
    stricate: prima incercare ramane comprimata pentru toate celelalte, iar
    reincercarea porneste doar pe `RemoteProtocolError`, nu pe orice eroare.
    """
    import httpx
    antete = {**ANTETE, **(kw.pop("headers", None) or {})}
    try:
        async with httpx.AsyncClient(headers=antete, **kw) as c:
            return await c.get(url)
    except httpx.RemoteProtocolError:
        async with httpx.AsyncClient(
                headers={**antete, "Accept-Encoding": "identity"}, **kw) as c:
            return await c.get(url)


async def _robots_accesibil(url: str) -> bool | None:
    """
    Spune daca /robots.txt se poate citi. Daca nici el nu raspunde, blocajul e la
    nivel de IP si nici playwright nu ajuta — pleaca de la aceeasi adresa.
    Intoarce None daca verificarea insasi esueaza.
    """
    import httpx
    from urllib.parse import urlsplit
    u = urlsplit(url)
    try:
        async with httpx.AsyncClient(headers=ANTETE, timeout=TIMEOUT,
                                     follow_redirects=True) as c:
            return (await c.get(f"{u.scheme}://{u.netloc}/robots.txt")).status_code == 200
    except Exception:
        return None


async def _descarca_pentru_test(url: str, metoda: str) -> str:
    if metoda == "playwright":
        from playwright.async_api import async_playwright
        async with async_playwright() as pw:
            br = await pw.chromium.launch(headless=True)
            pg = await br.new_page(user_agent=UA, locale="ro-RO",
                                   extra_http_headers={
                                       k: v for k, v in ANTETE.items()
                                       if k not in ("User-Agent", "Accept-Encoding", "Connection")
                                   })
            resp = await pg.goto(url, wait_until="networkidle",
                                 timeout=TIMEOUT * 1000)
            await pg.wait_for_timeout(1200)
            html = await pg.content()
            await br.close()
            stare = resp.status if resp is not None else 200
            if stare in STATUS_REFUZ or _pare_pagina_de_blocaj(html):
                raise AccesRefuzat(url, stare, html)
            return html
    r = await adu_http(url, timeout=TIMEOUT, follow_redirects=True, http2=True)
    if r.status_code in STATUS_REFUZ:
        raise AccesRefuzat(url, r.status_code, r.text)
    r.raise_for_status()
    if _pare_pagina_de_blocaj(r.text):
        raise AccesRefuzat(url, r.status_code, r.text)
    return r.text


async def main() -> None:
    # Consola Windows e pe cp1252, iar tot ce scriem — ajutorul argparse, JSONul
    # cu ensure_ascii=False, mesajele de diagnostic — are diacritice. Fără asta,
    # scrierea crapă cu UnicodeEncodeError înainte să apuci să vezi rezultatul.
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass

    ap = argparse.ArgumentParser(
        description="Extracție HTML. În producție se importă `proceseaza`.")
    sursa = ap.add_mutually_exclusive_group(required=True)
    sursa.add_argument("--fisier", help="fișier HTML local")
    sursa.add_argument("--url", help="descarcă pagina (doar pentru testare)")
    ap.add_argument("--metoda", default="http", choices=["http", "playwright"])
    ap.add_argument("--produse", required=True, help="separate prin virgulă")
    ap.add_argument("--hash-anterior")
    ap.add_argument("--out")
    ap.add_argument("--text-out", metavar="FISIER",
                    help="scrie textul sanitizat care a ajuns la extracție. "
                         "Pe ramura web_fetch e singura dovadă care rămâne: "
                         "acolo nu există Bronze.")
    ap.add_argument("--format", default="complet",
                    choices=["complet", "observations"],
                    help="`complet` — diagnostic integral (valori, respinse, "
                         "provenienta, bilant). `observations` — doar randurile "
                         "pentru tabelul cu acelasi nume, din valorile acceptate.")
    ap.add_argument("--id-url", metavar="ID",
                    help="cheia externa catre tabelul `urls`. Implicit, URL-ul.")
    a = ap.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("Lipsește ANTHROPIC_API_KEY. Copiază .env.exemplu în .env.")

    def formateaza(rez: dict) -> str:
        """Forma ceruta. `observations` pastreaza doar valorile acceptate."""
        if a.format == "observations":
            return json.dumps(ca_observatii(rez, a.id_url),
                              ensure_ascii=False, indent=2)
        return json.dumps(rez, ensure_ascii=False, indent=2)

    def scoate_text(rez: dict) -> dict:
        """Textul iese în fișier separat, nu în JSONul de rezultat."""
        t = rez.pop("text_sanitizat", None)
        if a.text_out and t is not None:
            Path(a.text_out).write_text(t, encoding="utf-8")
            print(f"Text sanitizat în {a.text_out} ({len(t)} caractere)",
                  file=sys.stderr)
        return rez

    if a.fisier:
        html = Path(a.fisier).read_text(encoding="utf-8", errors="replace")
        url = None
    else:
        try:
            html = await _descarca_pentru_test(a.url, a.metoda)
        except AccesRefuzat as e:
            lista = [q.strip() for q in a.produse.split(",") if q.strip()]

            # Descărcarea locală a fost refuzată. Încercăm ramura de fallback,
            # cu HTML gol: `proceseaza` va cere pagina prin web_fetch. 403-ul
            # nu mai e capăt de drum, dar nici nu devine invizibil — dacă
            # reușește, rezultatul iese marcat ca fără Bronze.
            nota_fb = "fallbackul web_fetch e dezactivat (FALLBACK_WEB_FETCH=0)"
            if WEB_FETCH_ACTIV:
                rez_fb = scoate_text(await proceseaza(
                    html="", metoda=a.metoda, produse=lista, url=a.url,
                    hash_anterior=a.hash_anterior,
                    include_text=bool(a.text_out)))
                if rez_fb.get("stare") == "extras":
                    rez_fb.setdefault("blocaj", {})["status_http_local"] = e.status
                    text = formateaza(rez_fb)
                    if a.out:
                        Path(a.out).write_text(text, encoding="utf-8")
                        print(f"Scris in {a.out}", file=sys.stderr)
                    else:
                        print(text)
                    print(f"\n  descărcarea locală a fost refuzată ({e.status}); "
                          "conținut obținut prin web_fetch", file=sys.stderr)
                    print("  atenție: fără Bronze pentru acest document",
                          file=sys.stderr)
                    return
                nota_fb = rez_fb.get("avertisment") or "web_fetch nu a întors conținut"

            rez = raport_blocat(e, a.metoda, lista,
                                nivel_ip=(await _robots_accesibil(a.url)) is False)
            rez["blocaj"]["fallback_web_fetch"] = nota_fb
            text = json.dumps(rez, ensure_ascii=False, indent=2)
            if a.out:
                Path(a.out).write_text(text, encoding="utf-8")
                print(f"Scris in {a.out}", file=sys.stderr)
            else:
                print(text)
            b = rez["blocaj"]
            print(f"\n  stare: blocat ({b['status_http']})", file=sys.stderr)
            if b.get("nivel") == "ip":
                print("  Blocaj la nivel de IP (nici /robots.txt nu raspunde).\n"
                      "  --metoda playwright nu ajuta: acelasi IP de iesire.",
                      file=sys.stderr)
            elif b.get("nivel") == "path_sau_client":
                print("  /robots.txt se citeste, deci nu e blocaj de IP.\n"
                      "  Verifica intai ce permite robots.txt; daca pagina cere\n"
                      "  randare JS, --metoda playwright e varianta corecta.",
                      file=sys.stderr)
            for k in ("reference_id", "client_ip"):
                if b.get(k):
                    print(f"  {k}: {b[k]}", file=sys.stderr)
            print("  Continutul nu se reconstituie dintr-un LLM si nu se ocoleste\n"
                  "  filtrul. Cere acces, apoi alimenteaza prin --fisier.",
                  file=sys.stderr)
            raise SystemExit(4)
        url = a.url

    rez = scoate_text(await proceseaza(
        html=html, metoda=a.metoda, produse=[p.strip() for p in a.produse.split(",") if p.strip()],
        url=url, hash_anterior=a.hash_anterior, include_text=bool(a.text_out),
    ))

    text = formateaza(rez)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"Scris în {a.out}", file=sys.stderr)
    else:
        print(text)

    print(f"\n  stare: {rez['stare']}", file=sys.stderr)
    if rez["stare"] == "extras":
        b = rez["bilant"]
        print(f"  produse găsite     {b['produse_gasite']}/{b['produse_cerute']}", file=sys.stderr)
        print(f"  valori acceptate   {b['valori_acceptate']}", file=sys.stderr)
        print(f"  valori respinse    {b['valori_respinse']}  ← verifică", file=sys.stderr)
        print(f"  tokeni             {b['tokeni_intrare']} in / {b['tokeni_iesire']} out", file=sys.stderr)
        if a.format == "observations":
            print(f"  randuri observations {len(ca_observatii(rez, a.id_url))}",
                  file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())