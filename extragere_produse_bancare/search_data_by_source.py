#!/usr/bin/env python3
"""
search_data_by_source.py — routerul: o sursă din inventar, în observații.

Unitatea de lucru a colectării. Primește o singură sursă și întoarce
observațiile ei, alegând singur flowul după formatul REAL al conținutului.

Unitatea e RANDUL DIN INVENTAR. Din linia de comanda, dat prin banca lui:

    python search_data_by_source.py --din-inventar raiffeisen --listeaza
    python search_data_by_source.py --din-inventar raiffeisen --rand 2
    python search_data_by_source.py --din-inventar raiffeisen --url tarife-comisioane

Randul se ia intreg - `tip`, `metoda` si `produse` vin din inventar, nu se
scriu de mana. `--metoda` le calca doar daca e dat explicit.

Din cod, aceleasi chei; orice rand de inventar merge direct:

    from search_data_by_source import cauta_date

    rez = await cauta_date({
        "id": 412,                       # cheia din tabelul `surse`
        "id_banca": 7,                   # cheia din tabelul `banci`
        "url": "https://www.bcr.ro/ro/curs-valutar",
        "format": "html",                # din inventar — ESTIMARE, se verifică
        "metoda": "http",                # http | playwright
        "produse": ["schimb-valutar"],   # asocierile de la discovery
        "hash_anterior": "9744b4...",    # din url_check, dacă există
    })

CE FACE, ȘI DE CE AICI

  DESCARCĂ. Aici, nu în flowuri. Flowurile primesc conținut, nu adrese —
  docstringul lui flow-html.py o spune de la prima linie. Consecința practică:
  ăsta e singurul loc din sistem unde există bytes bruți.

  SCRIE BRONZE. Fiindcă e singurul loc cu bytes bruți. Fără el, nicio valoare
  nu se poate reverifica: 91 din observațiile de până acum sunt deja marcate
  „fără Bronze" și acelea rămân așa pentru totdeauna.

  VERIFICĂ FORMATUL DIN CONȚINUT, nu din inventar. `format` de la discovery e
  o estimare a modelului — `web_fetch` întoarce text, nu marcaj, deci nu s-a
  putut măsura. Un PDF servit de la o adresă fără extensie, trimis la flowul
  HTML, ar consuma apeluri degeaba: `flow-html.py` nu verifică tipul, îl
  presupune. Se citesc octeții de la început: `%PDF-` e semnătura.

  ALEGE FLOWUL. pdf → flow-pdf.py, html → flow-html.py. Ambele au același
  contract pentru `proceseaza`, deci ramura e o singură linie.

  PROPAGĂ IDENTITATEA. `id` devine `id_sursa` și `id_banca` rămâne `id_banca`
  pe fiecare rând de observație, ca inserarea în baza de date să nu mai caute
  sursa după URL.

CE NU FACE

  Nu iterează. O sursă, un rezultat. Bucla, paralelismul și ordinea după
  `frecventa` aparțin planificatorului — `ruleaza-extractie.py` azi, un job
  nocturn mâine.

  Nu scrie în baza de date. Întoarce rândurile; inserarea e a apelantului.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

# Totul stă lângă cod, în extragere_produse_bancare/: Bronze-ul acestui flux
# (bronze/, în .gitignore) e separat de bronze/ din rădăcina repo-ului, unde își
# scrie crawler-ul MIP octeții cu altă structură de foldere.
COD = Path(__file__).parent
DATE = COD
INVENTARE = DATE / "inventare"


def _modul(nume: str, fisier: str):
    """Încarcă un fișier ca modul. Necesar pentru numele cu cratimă."""
    spec = importlib.util.spec_from_file_location(nume, COD / fisier)
    m = importlib.util.module_from_spec(spec)
    sys.modules[nume] = m
    spec.loader.exec_module(m)
    return m


fh = _modul("flow_html", "flow-html.py")
fp = _modul("flow_pdf", "flow-pdf.py")

# Unde se scriu bytes-ii bruți. Gol în .env dezactivează Bronze — util la
# testare, dar atunci observațiile ies fără dovadă și trebuie să se vadă.
BRONZE = os.getenv("BRONZE", "bronze")

# Semnăturile pe care le recunoaștem din primii octeți. Extensia și
# Content-Type mint amândouă; octeții nu.
SEMNATURI = {
    b"%PDF-": "pdf",
    b"PK\x03\x04": "zip",          # docx/xlsx ambalate; niciun flow încă
    b"\x89PNG": "imagine",
    b"\xff\xd8\xff": "imagine",
}


def format_real(octeti: bytes) -> str:
    """Formatul dedus din conținut. `html` e presupunerea de rezervă."""
    for semnatura, nume in SEMNATURI.items():
        if octeti.startswith(semnatura):
            return nume
    inceput = octeti[:2048].lstrip().lower()
    if inceput.startswith((b"<!doctype", b"<html", b"<?xml")):
        return "xml" if inceput.startswith(b"<?xml") else "html"
    return "html"


# Id-uri care se pot folosi ca nume de folder neatinse: cele din tabelul
# `surse` (numerice) si slugurile. Restul se trec prin `dosar_sursa`.
ID_CA_NUME = re.compile(r"[A-Za-z0-9._-]{1,64}")


def dosar_sursa(id_sursa: Any) -> str:
    """
    Numele de folder pentru o sursa, sub `bronze/`.

    Pana la baza de date `id` e URL-ul, iar un URL nu e nume de folder: `:` si
    `//` din `https://` sunt refuzate de Windows (WinError 123), iar adresele
    lungi de PDF ar trece si de MAX_PATH. Se scurteaza la gazda plus un hash
    pe URL-ul intreg — gazda ca sa recunosti folderul cand te uiti in `bronze/`,
    hashul fiindca el face unicitatea.

    Id-urile simple raman neatinse, altfel Bronze-ul scris pana acum sub `412`
    s-ar orfaniza la prima rulare de dupa schimbare.
    """
    text = str(id_sursa)
    if ID_CA_NUME.fullmatch(text):
        return text
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    gazda = re.sub(r"[^A-Za-z0-9.-]", "", urlsplit(text).netloc)[:40]
    return f"{gazda}-{h}" if gazda else h


def scrie_bronze(octeti: bytes, id_sursa: Any, url: str) -> dict | None:
    """
    Bytes-ii bruți, plus hashul pe ei. Dovada de audit pentru tot ce iese.

    Hashul e pe octeți, nu pe textul sanitizat: `content_hash` din observații
    răspunde la „s-a schimbat pagina", iar ăsta la „e acesta documentul din
    care am extras". Sunt întrebări diferite.
    """
    if not BRONZE:
        return None
    h = hashlib.sha256(octeti).hexdigest()
    dosar = DATE / BRONZE / dosar_sursa(id_sursa)
    dosar.mkdir(parents=True, exist_ok=True)
    cale = dosar / f"{h[:16]}.bin"
    if not cale.exists():
        cale.write_bytes(octeti)
    # `id_sursa` in clar aici: numele folderului e hashuit, deci fara el nu se
    # poate face drumul invers de la fisier la sursa.
    (dosar / f"{h[:16]}.json").write_text(json.dumps({
        "id_sursa": str(id_sursa),
        "url": url, "sha256": h, "octeti": len(octeti),
        "descarcat_la": datetime.now(timezone.utc).isoformat(),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"sha256": h, "octeti": len(octeti),
            "cale": str(cale.relative_to(DATE))}


async def descarca(url: str, metoda: str) -> tuple[bytes, int | None]:
    """
    @returns (octeți, status_refuz). Status nenul = serverul a refuzat, iar
             octeții sunt goi; apelantul decide dacă trece pe fallback.
    """
    try:
        if metoda == "playwright":
            # Playwright întoarce text randat, nu octeți — nu se poate folosi
            # pentru PDF, dar pentru asta nu e nici nevoie.
            html = await fh._descarca_pentru_test(url, "playwright")
            return html.encode("utf-8"), None
        r = await fh.adu_http(url, timeout=fh.TIMEOUT,
                              follow_redirects=True, http2=True)
        if r.status_code in fh.STATUS_REFUZ:
            return b"", r.status_code
        r.raise_for_status()
        if fh._pare_pagina_de_blocaj(r.text if r.headers.get(
                "content-type", "").startswith("text") else ""):
            return b"", r.status_code
        return r.content, None
    except fh.AccesRefuzat as e:
        return b"", e.status


async def cauta_date(sursa: dict) -> dict:
    """
    Observațiile unei singure surse.

    Cheile citite din `sursa`: `id`, `id_banca`, `url`, `format`, `metoda`,
    `produse`, `hash_anterior`, `scenariu`, `fara_fallback`, `focus` (produsul
    anume al băncii căutat în document). Toate în afară
    de `url` și `produse` sunt opționale.

    `scenariu` e cazul de referință din `scenarii.json`, pentru extracțiile
    ancorate pe produs. Lipsa lui lasă fluxul exact cum era.
    """
    id_sursa = sursa.get("id") or sursa.get("url")
    id_banca = sursa.get("id_banca")
    url = sursa["url"]
    metoda = sursa.get("metoda") or "http"
    produse = sursa.get("produse") or []
    format_inventar = sursa.get("format") or sursa.get("tip")

    raport: dict[str, Any] = {
        "id_sursa": id_sursa,
        "id_banca": id_banca,
        "url": url,
        "format_inventar": format_inventar,
        "metoda": metoda,
        "produse_cerute": produse,
    }

    if not produse:
        return {**raport, "stare": "sarit",
                "motiv": "nicio asociere de produs; hub sau pagină de context",
                "observatii": []}

    octeti, refuz = await descarca(url, metoda)
    raport["blocaj_http_local"] = refuz

    if refuz and sursa.get("fara_fallback"):
        # Regula echipei MIP: o bancă care refuză (401/403/429/451, pagină de
        # blocaj) nu se accesează prin alt canal. Fallbackul web_fetch de mai
        # jos ar fi exact acel alt canal, deci apelantul îl poate opri.
        return {**raport, "stare": "blocat",
                "motiv": f"{refuz} la descărcare; fără fallback (regula echipei)",
                "observatii": []}

    if refuz and format_inventar == "pdf":
        # Fallbackul prin web_fetch întoarce text, nu octeți, deci nu poate
        # reconstitui un PDF. Se raportează, nu se improvizează.
        return {**raport, "stare": "blocat",
                "motiv": f"{refuz} la descărcare, iar un PDF nu se poate "
                         "recupera prin web_fetch (acela întoarce text)",
                "observatii": []}

    format_efectiv = format_real(octeti) if octeti else format_inventar
    raport["format_efectiv"] = format_efectiv
    if octeti and format_inventar and format_efectiv != format_inventar:
        # Nu e o notă de curiozitate: e diferența dintre a extrage și a plăti
        # apeluri degeaba.
        raport["avertisment_format"] = (
            f"inventarul spune `{format_inventar}`, conținutul e "
            f"`{format_efectiv}`; s-a folosit conținutul")

    if format_efectiv not in ("html", "pdf"):
        return {**raport, "stare": "neacoperit",
                "motiv": f"format `{format_efectiv}`, fără flow",
                "observatii": []}

    raport["bronze"] = scrie_bronze(octeti, id_sursa, url) if octeti else None

    if format_efectiv == "pdf":
        rez = await fp.proceseaza(pdf=octeti, metoda=metoda, produse=produse,
                                 url=url,
                                 hash_anterior=sursa.get("hash_anterior"),
                                 scenariu=sursa.get("scenariu"),
                                 focus=sursa.get("focus"))
        flow = "flow-pdf"
    else:
        # HTML gol pornește ramura de fallback din `proceseaza`, care cere
        # pagina prin web_fetch. Rezultatul iese marcat ca fără Bronze.
        rez = await fh.proceseaza(html=octeti.decode("utf-8", "replace"),
                                  metoda=metoda, produse=produse, url=url,
                                  hash_anterior=sursa.get("hash_anterior"),
                                  scenariu=sursa.get("scenariu"),
                                  focus=sursa.get("focus"))
        flow = "flow-html"

    randuri = fh.ca_observatii(rez, id_url=id_sursa)
    # Proveniența pe fiecare rând: o valoare adusă prin web_fetch nu are bytes
    # bruți, deci nu poate fi reverificată nici dacă Bronze e activ.
    sanit = (rez.get("sanitizare") or {}).get("metoda")
    provenienta = {"web_fetch": "web_fetch", "llm": "llm_parser"}.get(
        sanit, "descarcare_proprie")
    for r in randuri:
        r["id_banca"] = id_banca
        r["sursa_continut"] = provenienta
        r["bronze_sha256"] = (raport["bronze"] or {}).get("sha256") \
            if provenienta == "descarcare_proprie" else None

    return {
        **raport,
        "flow": flow,
        "stare": rez.get("stare"),
        "content_hash": rez.get("content_hash"),
        "metoda_sanitizare": sanit,
        "avertisment": rez.get("avertisment"),
        "bilant": rez.get("bilant"),
        "observatii": randuri,
        "respinse": [
            {"produs": p, **{k: v.get(k) for k in
                             ("camp", "cod_scenariu", "valoare_num", "unitate",
                              "incredere", "citat", "motive")}}
            for p, d in (rez.get("rezultate") or {}).items()
            for v in d.get("respinse", [])
        ],
    }


def surse_din_inventar(slug: str, doar_extractibile: bool = False) -> list[dict]:
    """
    Sursele unei bănci, în forma pe care o așteaptă `cauta_date`.

    Până la baza de date, `id` e URL-ul: e stabil și unic, iar un id numeric
    inventat aici nu s-ar potrivi cu cel din `surse`.
    """
    cale = INVENTARE / f"inventar-{slug}.json"
    if not cale.exists():
        raise SystemExit(f"Nu există {cale.name}")
    docs = json.loads(cale.read_text(encoding="utf-8"))["documente"]
    surse = [{
        "id": d["url"],
        "id_banca": slug,
        "url": d["url"],
        "format": d.get("tip"),
        "metoda": d.get("metoda") or "http",
        "produse": d.get("produse") or [],
    } for d in docs]
    if doar_extractibile:
        surse = [s for s in surse if s["produse"]]
    return surse


def alege_rand(slug: str, url: str | None, rand: int | None) -> dict:
    """
    Un singur rand din inventarul bancii, cu tot ce are pe el.

    `url` se potriveste pe fragment, nu doar exact: adresele de PDF sunt lungi
    si se tasteaza gresit. O potrivire ambigua e o eroare, nu o alegere
    arbitrara - s-ar extrage din sursa gresita si nimic nu ar arata asta.
    """
    surse = surse_din_inventar(slug)
    if rand is not None:
        if not 1 <= rand <= len(surse):
            raise SystemExit(
                f"--rand {rand} in afara intervalului 1..{len(surse)} "
                f"pentru {slug}; vezi --listeaza")
        return surse[rand - 1]

    exacte = [s for s in surse if url == s["url"]]
    potriviri = exacte or [s for s in surse if url in s["url"]]
    if not potriviri:
        raise SystemExit(f"Niciun URL din inventarul {slug} nu contine "
                         f"`{url}`; vezi --listeaza")
    if len(potriviri) > 1:
        linii = "\n".join(f"    {s['url']}" for s in potriviri)
        raise SystemExit(f"`{url}` se potriveste cu {len(potriviri)} "
                         f"adrese:\n{linii}")
    return potriviri[0]


async def main() -> None:
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--din-inventar", metavar="SLUG",
                    help="ia rândul din inventarul băncii, cu tip/metodă/"
                         "produse cu tot")
    sursa = ap.add_mutually_exclusive_group()
    sursa.add_argument("--rand", type=int, metavar="N",
                       help="al N-lea rând, cum îl numerotează --listeaza")
    sursa.add_argument("--url", help="URL-ul rândului (fragment, cu "
                                     "--din-inventar) sau o sursă dată direct")
    sursa.add_argument("--json", metavar="FISIER",
                       help="sursa ca obiect JSON, cu id / id_banca / produse")
    ap.add_argument("--listeaza", action="store_true",
                    help="doar arată rândurile băncii, fără să extragă")
    ap.add_argument("--produse", help="separate prin virgulă; doar cu --url "
                                      "fără --din-inventar")
    # Fără implicit: altfel `http` ar călca tăcut `metoda` din inventar,
    # inclusiv pe rândurile marcate `playwright`.
    ap.add_argument("--metoda", choices=["http", "playwright"],
                    help="calcă metoda din inventar")
    ap.add_argument("--id", help="id-ul sursei; implicit URL-ul")
    ap.add_argument("--id-banca")
    ap.add_argument("--out")
    a = ap.parse_args()

    # Intai cazul precis, apoi cel general: altfel `--rand 2` singur pica pe
    # mesajul generic, care nu spune ce lipseste de fapt.
    if a.rand is not None and not a.din_inventar:
        sys.exit("--rand cere și --din-inventar.")
    if not (a.din_inventar or a.url or a.json):
        sys.exit("Dă --din-inventar, --url sau --json.")

    # Listarea e inspecție pură: iese înainte de cheia de API, deci nu costă.
    if a.din_inventar and (a.listeaza or not (a.rand or a.url)):
        surse = surse_din_inventar(a.din_inventar)
        for i, s in enumerate(surse, 1):
            print(f"{i:3}  {len(s['produse']):2}p {s['format'] or '?':5} "
                  f"{s['url']}")
        perechi = sum(len(s["produse"]) for s in surse)
        print(f"\n  {len(surse)} rânduri, {perechi} perechi "
              f"(= apeluri de extracție)", file=sys.stderr)
        print(f"  extrage unul:  --din-inventar {a.din_inventar} --rand N",
              file=sys.stderr)
        return

    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("Lipsește ANTHROPIC_API_KEY.")

    if a.json:
        s = json.loads(Path(a.json).read_text(encoding="utf-8"))
    elif a.din_inventar:
        s = alege_rand(a.din_inventar, a.url, a.rand)
        if a.id:
            s["id"] = a.id
        if a.id_banca:
            s["id_banca"] = a.id_banca
        print(f"  rând      {s['format'] or '?'} · {len(s['produse'])} produse"
              f" · metoda {s['metoda']}", file=sys.stderr)
        print(f"  produse   {', '.join(s['produse']) or '—'}", file=sys.stderr)
        print(f"  url       {s['url']}", file=sys.stderr)
    else:
        if not a.produse:
            sys.exit("--url fără --din-inventar cere și --produse")
        s = {"id": a.id or a.url, "id_banca": a.id_banca, "url": a.url,
             "produse": [p.strip() for p in a.produse.split(",") if p.strip()]}

    if a.metoda:
        s["metoda"] = a.metoda
    s.setdefault("metoda", "http")

    rez = await cauta_date(s)
    text = json.dumps(rez, ensure_ascii=False, indent=2)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"Scris în {a.out}", file=sys.stderr)
    else:
        print(text)

    print(f"\n  stare            {rez['stare']}", file=sys.stderr)
    print(f"  flow             {rez.get('flow', '—')}", file=sys.stderr)
    print(f"  format inventar  {rez.get('format_inventar')} -> efectiv "
          f"{rez.get('format_efectiv')}", file=sys.stderr)
    if rez.get("avertisment_format"):
        print(f"  ATENȚIE          {rez['avertisment_format']}", file=sys.stderr)
    b = rez.get("bronze")
    print(f"  bronze           {b['cale'] if b else 'nescris'}", file=sys.stderr)
    print(f"  observații       {len(rez['observatii'])}", file=sys.stderr)
    print(f"  respinse         {len(rez.get('respinse') or [])}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
