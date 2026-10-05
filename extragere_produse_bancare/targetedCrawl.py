#!/usr/bin/env python3
"""
Discovery țintit: o rulare = o bancă × un produs din produse_bancare_v2.json.

Spre deosebire de claudeCrawl.py (o buclă de 100 de pagini care caută toate
produsele deodată), aici modelul primește UN singur produs — cu sinonimele,
descrierea și câmpurile lui din catalog — și caută adresele unde se găsesc
datele acelui produs. Fiecare sursă găsită e un rând cu un singur produs;
dacă aceeași pagină servește și alt produs, o va raporta rularea acelui produs.

    python targetedCrawl.py --banca bcr --produs depozit-termen
    python targetedCrawl.py --banca bcr --combina      # adună rezultatele per produs

Rezultate:
    inventare-targeted/<banca>/<produs>.json     unul per produs
    inventare-targeted/inventar-<banca>.json     combinat, cu `documente`
                                                  compatibil cu ruleaza-extractie.py

Domeniile permise: domeniul de bază al URL-ului băncii (web_fetch include
automat toate subdomeniile) plus `domenii_inrudite` din banci.json.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from anthropic import Anthropic
from dotenv import load_dotenv

import preturi

AICI = Path(__file__).parent
load_dotenv(AICI / ".env")

CALE_CATALOG = AICI / os.getenv("CATALOG_PRODUSE", "produse_bancare_v2.json")
CALE_BANCI = AICI / "banci.json"
IESIRE = AICI / "inventare-targeted"

MODEL = os.getenv("MODEL", "claude-sonnet-5")
MAX_PAGINI = int(os.getenv("MAX_PAGINI", "15"))
MAX_CAUTARI = int(os.getenv("MAX_CAUTARI", "3"))
TURE_MAX = int(os.getenv("TURE_MAX", "10"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "16000"))
CACHE = os.getenv("CACHE_PROMPT", "1") != "0"
# Un produs, nu 31: istoricul rămâne mic, deci ne permitem pagini mai lungi
# decât în claudeCrawl.py — 15 × 10.000 = 150k tokeni de conținut în cel mai rău caz.
MAX_CONTINUT = int(os.getenv("WEB_FETCH_MAX_CONTENT", "10000"))
WEB_TOOLS = os.getenv("WEB_TOOLS", "baza")

# Sub atâtea cuvinte, citatul nu mai poate fi verificat de un om fără să
# redeschidă pagina — exact problema pe care o avea `dovada` din inventarele vechi.
CUVINTE_MIN_CITAT = 20


# ── configurare ───────────────────────────────────────────────────

def incarca_banca(id_banca: str) -> dict:
    banci = json.loads(CALE_BANCI.read_text(encoding="utf-8"))["banci"]
    for b in banci:
        if b["id"] == id_banca:
            return b
    sys.exit(f"Bancă necunoscută: {id_banca}. Valide: {', '.join(b['id'] for b in banci)}")


def incarca_produs(id_produs: str) -> dict:
    produse = json.loads(CALE_CATALOG.read_text(encoding="utf-8"))["produse"]
    for p in produse:
        if p["id"] == id_produs:
            return p
    sys.exit(f"Produs necunoscut: {id_produs}. Valide: {', '.join(p['id'] for p in produse)}")


def domenii_permise(banca: dict) -> list[str]:
    """
    Domeniul de bază (ultimele două etichete ale hostului) + subsidiarele.
    web_fetch acoperă singur subdomeniile: `bcr.ro` permite și www.bcr.ro,
    cdn.bcr.ro, documente.bcr.ro — de unde vin de obicei PDF-urile de tarife.
    """
    host = urlparse(banca["url"]).netloc.lower().split(":")[0]
    baza = ".".join(host.split(".")[-2:])
    return sorted({baza, *banca.get("domenii_inrudite", [])})


# ── prompt și unelte ──────────────────────────────────────────────

def unealta_gata(produs: dict) -> dict:
    campuri = produs.get("campuri") or []
    return {
        "name": "gata",
        "description": "Returnează sursele găsite pentru produs. Se apelează o singură dată, la sfârșit.",
        "input_schema": {
            "type": "object",
            "properties": {
                "surse": {
                    "type": "array",
                    "description": "Câte un rând per adresă. Gol dacă produsul nu a fost găsit.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "Adresa exactă pe care ai deschis-o cu web_fetch. Nu o reconstrui."},
                            "tip": {"type": "string", "enum": ["html", "pdf", "xml"]},
                            "metoda": {"type": "string", "enum": ["http", "playwright"]},
                            "incredere_metoda": {"type": "number", "minimum": 0, "maximum": 1},
                            "dovada_metoda": {"type": "string", "description": "Ce anume din conținut a decis metoda."},
                            "rol": {"type": "string", "enum": ["pagina-produs", "tarife", "dobanzi", "conditii", "simulator"],
                                    "description": "pagina-produs = pagina dedicată; tarife = document de tarife/comisioane; dobanzi = listă sau grilă de dobânzi; conditii = FIPC, fișă informativă, regulament, condiții generale; simulator = calculator interactiv."},
                            "frecventa": {"type": "string", "enum": ["zilnic", "saptamanal", "lunar", "trimestrial", "la_descoperire"]},
                            "segment": {"type": "string", "enum": ["retail", "imm-corporate"]},
                            "incredere": {"type": "number", "minimum": 0, "maximum": 1,
                                          "description": "Cât de sigur ești că sursa conține date despre ACEST produs, la această bancă."},
                            "explicatie_incredere": {"type": "string",
                                                     "description": "O propoziție: de ce ai dat scorul ăsta. Ex: 'pagina dedicată produsului, cu dobânda și comisionul în text' sau 'document general de tarife, produsul apare doar într-un tabel de 3 rânduri'."},
                            "citat": {"type": "string",
                                      "description": f"Fragment copiat LITERAL din conținutul primit, 1-3 propoziții (minim {CUVINTE_MIN_CITAT} de cuvinte), care numește produsul și conține cifrele relevante: dobândă, comision, sumă, termen. Nu parafraza, nu rezuma, nu lipi bucăți din locuri diferite."},
                            "campuri_vazute": {"type": "array", "items": {"type": "string", **({"enum": campuri} if campuri else {})},
                                               "description": "Câmpurile din catalog pentru care ai văzut efectiv o valoare în această sursă."},
                        },
                        "required": ["url", "tip", "metoda", "incredere_metoda", "dovada_metoda", "rol",
                                     "frecventa", "segment", "incredere", "explicatie_incredere", "citat",
                                     "campuri_vazute"],
                    },
                },
                "gol": {
                    "type": "object",
                    "description": "Completează DOAR dacă `surse` e gol.",
                    "properties": {
                        "motiv": {"type": "string", "enum": ["nu_am_gasit", "produs_inexistent",
                                                             "necesita_alt_domeniu", "blocat_de_robots"]},
                        "nota": {"type": "string", "description": "Ce ai verificat și unde ai căutat."},
                    },
                    "required": ["motiv", "nota"],
                },
            },
            "required": ["surse"],
        },
    }


def sistem(produs: dict) -> str:
    sinonime = ", ".join(produs.get("keywords", []))
    campuri = ", ".join(produs.get("campuri", []))
    return f"""Cauți, pe site-ul unei bănci, adresele unde se găsesc datele publice pentru UN SINGUR produs. Rezultatul alimentează o platformă de market intelligence: pe fiecare adresă raportată va rula ulterior un extractor de valori.

PRODUSUL
- id: {produs['id']}
- nume: {produs['nume']}
- segment: {produs.get('segment', '')}
- cum îl numesc băncile: {sinonime or '—'}
- ce contează: {produs.get('cauta', '—')}
- câmpuri urmărite: {campuri or '—'}

Ignoră orice alt produs. Dacă o pagină acoperă și alte produse, raportezi doar partea despre produsul tău.

CE CAUȚI, în ordinea valorii
1. Pagina dedicată produsului, dacă are cifre în text.
2. Lista sau grila de dobânzi care îl acoperă.
3. Documentul de tarife și comisioane (de obicei PDF, legat din footer: „Tarife și comisioane", „Documente utile", „Informații utile"). Raportează-l doar dacă produsul chiar apare în el.
4. Documentele de condiții: FIPC / fișa cu informații precontractuale, fișa produsului, regulamentul, condițiile generale.
Un produs are de obicei 1-4 surse. Nu raporta pagini de listare, hub-uri, bloguri, știri sau campanii expirate.

NAVIGARE
- Pornești de la pagina principală. Deschizi doar adrese care apar ca linkuri în ce ai citit sau în rezultatele `web_search`.
- `web_search` e util pentru un salt direct, de ex. „{produs['nume']} dobândă" sau „tarife comisioane pdf". Ai puține căutări, folosește-le când meniul nu duce clar la produs.
- Ai voie pe orice subdomeniu al băncii și pe subsidiarele din lista de domenii permise. Leasingul, pensiile și locuințele stau adesea pe domenii separate.
- Nu deschide internet banking, cariere, contact, cookies.
- Dacă o pagină nu se încarcă, poate fi blocată prin robots.txt. Mergi mai departe.

CITATUL — partea cea mai importantă
`citat` e fragmentul pe care un om îl caută cu Ctrl+F în pagină ca să verifice asocierea. De aceea:
- se copiază LITERAL din conținutul primit, fără parafrazare, fără „...";
- 1-3 propoziții consecutive, minim {CUVINTE_MIN_CITAT} de cuvinte;
- numește produsul (sau secțiunea lui) ȘI conține cifrele: procent, comision, sumă, termen;
- dacă sursa e un tabel, copiază rândul cu antetul lui, așa cum apare în text.
Greșit: „dobândă fixă 5,5%". Corect: „Depozitul la termen în lei cu scadența la 12 luni are o dobândă fixă de 5,50% pe an, plătită la scadență, pentru sume de minimum 500 lei."

ÎNCREDEREA
`incredere` — cât de sigur ești că adresa conține date despre ACEST produs:
- 0.9+: pagină dedicată sau document în care ai văzut cifrele produsului
- 0.7-0.85: document general (tarife, dobânzi) în care produsul apare explicit cu valori
- 0.5-0.7: produsul e menționat, dar cifrele sunt parțiale sau ambigue (altă variantă, alt segment)
- sub 0.5: nu raporta
`explicatie_incredere` justifică scorul într-o propoziție concretă.

METODA — estimare, nu măsurătoare
Primești text extras, nu marcaj. `http` când cifrele apar în conținut, sau e PDF/XML (întotdeauna `http`). `playwright` când e clar pagina produsului dar nu conține nicio cifră, menționează un simulator care „se încarcă", sau cere JavaScript.
`incredere_metoda`: 0.9+ dacă ai văzut cifrele sau e PDF/XML; 0.6-0.8 pagină descriptivă fără cifre; sub 0.6 bănuiești randare dinamică.
La `dovada_metoda` scrii motivul concret.

ALTE REGULI
- `tip` din ce ai primit efectiv, nu din extensia adresei.
- Frecvența: dobânzi și curs valutar `zilnic`, tarife `saptamanal`, pagini de produs `lunar`, regulamente de campanie `la_descoperire`.
- Dacă produsul nu există la bancă, `surse` gol și `gol.motiv = produs_inexistent`. E un rezultat valid.

Ai maximum {MAX_PAGINI} deschideri de pagini. Încheie apelând `gata` o singură dată."""


# ── bucla ─────────────────────────────────────────────────────────

def curata(content: list) -> list:
    """Scoate `server_tool_use` fără rezultat (răspuns tăiat la max_tokens)."""
    cu_rezultat = {getattr(b, "tool_use_id", None) for b in content
                   if b.type in ("web_fetch_tool_result", "web_search_tool_result")}
    return [b for b in content
            if not (b.type == "server_tool_use" and b.id not in cu_rezultat)]


def normalizeaza_gata(intrare: dict) -> dict:
    """
    Modelul trimite uneori `surse` (sau `gol`) ca șir JSON în loc de listă.
    La BT, card-debit a picat așa și a plătit o reîncercare întreagă.
    """
    rez = dict(intrare)
    for cheie in ("surse", "gol"):
        v = rez.get(cheie)
        if isinstance(v, str):
            try:
                rez[cheie] = json.loads(v)
            except json.JSONDecodeError:
                rez[cheie] = [] if cheie == "surse" else None
    rez["surse"] = [s for s in (rez.get("surse") or []) if isinstance(s, dict) and s.get("url")]
    return rez


def text_din_rezultat(bloc) -> tuple[str, str] | None:
    """(url, text) dintr-un web_fetch_tool_result reușit; None pentru PDF binar sau eroare."""
    d = bloc.to_dict() if hasattr(bloc, "to_dict") else {}
    c = d.get("content") or {}
    if c.get("type") != "web_fetch_result":
        return None
    sursa = (c.get("content") or {}).get("source") or {}
    if sursa.get("type") != "text":
        return None
    return c.get("url", ""), sursa.get("data", "")


def ruleaza(banca: dict, produs: dict, prompt_sistem: str | None = None,
            gata: dict | None = None, cerere: str | None = None) -> dict:
    """
    Bucla pentru o bancă × un produs. Promptul, unealta `gata` și cererea se
    pot da din afară (descopera_surse_libra.py le dă pentru produsele Libra);
    implicit sunt cele pentru catalogul v2.
    """
    client = Anthropic()
    domenii = domenii_permise(banca)
    # Varianta de bază, nu `_20260209`. Cea nouă filtrează paginile prin cod
    # rulat pe server: la BT, cont-curent a citit 1,7M tokeni din cache pentru
    # 4 pagini, a adus aceeași pagină de până la 4 ori, iar textul paginii nu
    # mai ajungea întreg în răspuns — deci citatul nu putea fi verificat.
    # WEB_TOOLS=dinamic revine la ea.
    if WEB_TOOLS == "dinamic":
        tip_fetch, tip_search, betas = "web_fetch_20260209", "web_search_20260209", []
    else:
        tip_fetch, tip_search, betas = "web_fetch_20250910", "web_search_20250305", ["web-fetch-2025-09-10"]
    unelte = [
        {"type": tip_fetch, "name": "web_fetch", "max_uses": MAX_PAGINI,
         "allowed_domains": domenii, "max_content_tokens": MAX_CONTINUT},
        {"type": tip_search, "name": "web_search", "max_uses": MAX_CAUTARI,
         "allowed_domains": domenii},
        gata or unealta_gata(produs),
    ]
    prompt_sistem = prompt_sistem or sistem(produs)
    mesaje = [{"role": "user", "content":
               f"Banca: {banca['nume']} ({banca['id']})\n"
               f"Pagina principală: {banca['url']}\n"
               f"Domenii permise (cu subdomenii): {', '.join(domenii)}\n\n"
               + (cerere or f"Găsește sursele pentru produsul „{produs['nume']}”, apoi apelează `gata`.")}]

    deschise: list[str] = []
    texte: dict[str, str] = {}
    usage: dict = {}

    for tura in range(TURE_MAX):
        argumente = dict(model=MODEL, max_tokens=MAX_TOKENS, system=prompt_sistem,
                         tools=unelte, messages=mesaje)
        if CACHE:
            argumente["cache_control"] = {"type": "ephemeral"}

        if betas:
            with client.beta.messages.stream(betas=betas, **argumente) as flux:
                r = flux.get_final_message()
        else:
            with client.messages.stream(**argumente) as flux:
                r = flux.get_final_message()
        preturi.aduna_usage(usage, r.usage)

        for bloc in r.content:
            if bloc.type == "server_tool_use" and bloc.name == "web_fetch":
                u = bloc.input.get("url", "")
                deschise.append(u)
                print(f"  [{len(deschise):2}] {u}", file=sys.stderr)
            elif bloc.type == "server_tool_use" and bloc.name == "web_search":
                print(f"  [cautare] {bloc.input.get('query', '')}", file=sys.stderr)
            elif bloc.type == "web_fetch_tool_result":
                rez = text_din_rezultat(bloc)
                if rez:
                    texte[rez[0]] = rez[1]
                else:
                    c = getattr(bloc, "content", None)
                    cod = getattr(c, "error_code", None)
                    if cod:
                        print(f"       ! {cod}", file=sys.stderr)

        if r.stop_reason == "refusal":
            return {"surse": [], "_eroare": "refuz de la model", "_deschise": deschise,
                    "_texte": texte, "_usage": usage}

        final = [b for b in r.content if b.type == "tool_use" and b.name == "gata"]
        if final:
            # `_brut`: intrarea `gata` neatinsă. normalizeaza_gata poate goli
            # `surse` (JSON invalid, rânduri fără url); fără brut, cauza se pierde.
            return {**normalizeaza_gata(final[0].input), "_brut": final[0].input,
                    "_deschise": deschise, "_texte": texte, "_usage": usage}

        pastrate = curata(r.content)
        if pastrate:
            mesaje.append({"role": "assistant", "content": pastrate})

        # pause_turn: serverul a oprit bucla uneltelor server-side; se retrimite
        # conversația așa cum e, fără mesaj nou de la utilizator.
        if r.stop_reason == "pause_turn" and pastrate:
            continue

        ramase = MAX_PAGINI - len(deschise)
        if not pastrate:
            indiciu = "Răspunsul s-a întrerupt. Reia de unde ai rămas, cu o singură pagină o dată."
        elif r.stop_reason == "max_tokens":
            indiciu = "Răspunsul s-a oprit la limita de lungime. Scrie mai puțin între apeluri."
        elif ramase <= 2:
            indiciu = f"Au mai rămas {ramase} deschideri. Încheie acum cu `gata`."
        else:
            indiciu = "Continuă. Când ai sursele produsului, apelează `gata`."
        print(f"  -- tura {tura + 1}, stop_reason={r.stop_reason}, "
              f"{len(deschise)}/{MAX_PAGINI} pagini", file=sys.stderr)
        mesaje.append({"role": "user", "content": indiciu})

    return {"surse": [], "_deschise": deschise, "_texte": texte, "_usage": usage,
            "_eroare": f"s-au epuizat {TURE_MAX} ture fără apel `gata`"}


# ── verificări pe rezultat ────────────────────────────────────────

def normalizeaza(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[\"'„”“«»’‘`*|]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def citat_regasit(citat: str, text: str) -> bool:
    """
    Citatul apare în textul primit? Literal, după normalizare; altfel ≥ 80% din
    secvențele de 6 cuvinte — web_fetch poate rupe tabelele diferit față de
    cum le copiază modelul.
    """
    c, t = normalizeaza(citat), normalizeaza(text)
    if not c or not t:
        return False
    if c in t:
        return True
    cuv = c.split()
    if len(cuv) < 6:
        return False
    secvente = [" ".join(cuv[i:i + 6]) for i in range(len(cuv) - 5)]
    if sum(s in t for s in secvente) / len(secvente) >= 0.8:
        return True
    # Tabele: modelul lipește celulele pe un rând („SALUT 0 lei/ lună STUDENT
    # 0 lei/ lună"), textul primit le are pe linii separate sau în altă ordine.
    # Acceptăm dacă TOATE cifrele citatului apar în text și aproape toate cuvintele.
    cuvinte_t = set(re.findall(r"\w+", t))
    tokeni = re.findall(r"\w+", c)
    cifre = [x for x in tokeni if any(ch.isdigit() for ch in x)]
    if not cifre or any(x not in cuvinte_t for x in cifre):
        return False
    return sum(x in cuvinte_t for x in tokeni) / len(tokeni) >= 0.9


def verifica(surse: list[dict], deschise: list[str], texte: dict[str, str]) -> None:
    fara_slash = {u.rstrip("/") for u in deschise}
    texte_n = {u.rstrip("/"): t for u, t in texte.items()}
    for s in surse:
        avert = []
        cheie = s["url"].rstrip("/")
        if cheie not in fara_slash and cheie not in texte_n:
            avert.append("adresă neregăsită printre deschiderile efective")
        n = len(s.get("citat", "").split())
        if n < CUVINTE_MIN_CITAT:
            avert.append(f"citat scurt ({n} cuvinte)")
        if cheie in texte_n:
            s["citat_verificat"] = citat_regasit(s.get("citat", ""), texte_n[cheie])
            if not s["citat_verificat"]:
                avert.append("citatul nu apare în textul primit")
        else:
            # PDF-urile vin ca document binar: nu avem text de comparat.
            s["citat_verificat"] = None
        if avert:
            s["avertisment"] = "; ".join(avert)


def deduplica(surse: list[dict]) -> list[dict]:
    """Aceeași adresă raportată de două ori: o păstrăm pe cea cu încredere mai mare."""
    per_url: dict[str, dict] = {}
    for s in surse:
        k = s["url"].rstrip("/")
        if k not in per_url or s.get("incredere", 0) > per_url[k].get("incredere", 0):
            per_url[k] = s
    return list(per_url.values())


# ── comenzi ───────────────────────────────────────────────────────

def un_produs(banca: dict, produs: dict) -> None:
    print(f"Discovery țintit: {banca['id']} × {produs['id']}  "
          f"(domenii: {', '.join(domenii_permise(banca))})\n", file=sys.stderr)
    rez = ruleaza(banca, produs)
    surse = deduplica(rez.get("surse") or [])
    verifica(surse, rez["_deschise"], rez["_texte"])
    surse.sort(key=lambda s: -s.get("incredere", 0))

    u = rez.get("_usage") or {}
    iesire = {
        "generat": str(date.today()),
        "banca": banca["id"],
        "produs": produs["id"],
        "produs_nume": produs["nume"],
        "model": MODEL,
        "surse": surse,
        "gol": rez.get("gol") if not surse else None,
        "bilant": {
            "pagini_deschise": len(rez["_deschise"]),
            "surse": len(surse),
            "citate_verificate": sum(1 for s in surse if s.get("citat_verificat") is True),
            "cu_avertisment": sum(1 for s in surse if "avertisment" in s),
        },
        "deschise": rez["_deschise"],
        "consum": {**u, "cost_estimat_usd": preturi.cost(
            MODEL, u.get("intrare", 0), u.get("iesire", 0),
            u.get("citire_cache", 0), u.get("scriere_cache", 0))},
    }
    if "_eroare" in rez:
        iesire["eroare"] = rez["_eroare"]

    dosar = IESIRE / banca["id"]
    dosar.mkdir(parents=True, exist_ok=True)
    cale = dosar / f"{produs['id']}.json"
    cale.write_text(json.dumps(iesire, ensure_ascii=False, indent=2), encoding="utf-8")

    for s in surse:
        semn = "✓" if s.get("citat_verificat") else ("?" if s.get("citat_verificat") is None else "✗")
        print(f"  {s['incredere']:.2f} {semn} {s['rol']:13} {s['url']}", file=sys.stderr)
        if "avertisment" in s:
            print(f"       ! {s['avertisment']}", file=sys.stderr)
    if iesire["gol"]:
        print(f"  gol: {iesire['gol'].get('motiv')} — {iesire['gol'].get('nota', '')}", file=sys.stderr)
    for linie in preturi.formateaza(MODEL, u):
        print(linie, file=sys.stderr)
    print(f"\nScris în {cale}", file=sys.stderr)

    if "eroare" in iesire:
        sys.exit(2)


def combina(banca: dict) -> None:
    """
    Adună fișierele per produs într-un inventar al băncii. Fiecare rând din
    `documente` are un singur produs; `produse: [id]` e păstrat ca
    ruleaza-extractie.py și exporta-surse.py să-l poată citi fără modificări.
    """
    dosar = IESIRE / banca["id"]
    fisiere = sorted(dosar.glob("*.json"))
    if not fisiere:
        sys.exit(f"Niciun rezultat în {dosar}")

    documente, goluri, erori = [], [], []
    total: dict = {}
    for f in fisiere:
        d = json.loads(f.read_text(encoding="utf-8"))
        for s in d["surse"]:
            documente.append({"produs": d["produs"], "produse": [d["produs"]],
                              "dovada": s.get("citat", ""), **s})
        if d.get("gol"):
            goluri.append({"produs": d["produs"], **d["gol"]})
        if d.get("eroare"):
            erori.append({"produs": d["produs"], "eroare": d["eroare"]})
        for k, v in (d.get("consum") or {}).items():
            if isinstance(v, (int, float)):
                total[k] = total.get(k, 0) + v

    inventar = {
        "generat": str(date.today()),
        "stare": "PROPUNERE — intră în coada de review, nu direct în tabelul urls",
        "structura": "un rând = o sursă × un produs; aceeași adresă poate apărea la mai multe produse",
        "colectare": {
            "executata_de": "infrastructura Anthropic, user-agent Claude-User",
            "robots_txt": "respectat de Claude-User; paginile excluse nu au putut fi citite",
            "limitare_cunoscuta": "`metoda` e o estimare a modelului. `citat_verificat` = null la PDF-uri (nu avem text de comparat).",
        },
        "competitor": {"id": banca["id"], "domeniu_principal": urlparse(banca["url"]).netloc,
                       "domenii_permise": domenii_permise(banca)},
        "documente": documente,
        "goluri": goluri,
        "erori": erori,
        "bilant": {
            "produse_rulate": len(fisiere),
            "produse_gasite": len({d["produs"] for d in documente}),
            "randuri_sursa_produs": len(documente),
            "adrese_distincte": len({d["url"].rstrip("/") for d in documente}),
            "citate_verificate": sum(1 for d in documente if d.get("citat_verificat") is True),
            "citate_neregasite": sum(1 for d in documente if d.get("citat_verificat") is False),
            "asociere_nesigura": sum(1 for d in documente if d.get("incredere", 1) < 0.7),
            "estimate_playwright": sum(1 for d in documente if d.get("metoda") == "playwright"),
        },
        "consum": {"model": MODEL, **{k: round(v, 4) if isinstance(v, float) else v
                                      for k, v in total.items()},
                   "nota": "estimare din prețuri de listă, nu factura reală"},
    }
    cale = IESIRE / f"inventar-{banca['id']}.json"
    cale.write_text(json.dumps(inventar, ensure_ascii=False, indent=2), encoding="utf-8")
    b = inventar["bilant"]
    print(f"{banca['id']}: {b['produse_gasite']}/{b['produse_rulate']} produse găsite, "
          f"{b['randuri_sursa_produs']} rânduri, {b['adrese_distincte']} adrese distincte, "
          f"{b['citate_verificate']} citate verificate, {b['citate_neregasite']} neregăsite",
          file=sys.stderr)
    print(f"Scris în {cale}", file=sys.stderr)


def main() -> None:
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--banca", required=True)
    ap.add_argument("--produs")
    ap.add_argument("--combina", action="store_true")
    a = ap.parse_args()

    banca = incarca_banca(a.banca)
    if a.combina:
        combina(banca)
        return
    if not a.produs:
        ap.error("--produs sau --combina")
    un_produs(banca, incarca_produs(a.produs))


if __name__ == "__main__":
    main()
