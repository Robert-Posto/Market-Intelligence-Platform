#!/usr/bin/env python3
"""
flow-pdf.py — flowul de extracție pentru documente PDF.

Același contract ca `flow-html.py`: primește CONȚINUTUL, nu un URL, și întoarce
aceeași formă de rezultat, ca routerul să nu deosebească flowurile. Observațiile
trec prin același `valideaza` și ies prin același `ca_observatii`.

    from importlib import ...            # numele are cratimă
    rez = await proceseaza(pdf=octeti, metoda="http",
                           produse=["cont-curent"], url="https://...")

DOUĂ CĂI, ȘI DE CE

  (a) DOCUMENTE STANDARDIZATE prin Legea 258/2017 (directiva UE 2014/92, PAD).
      Formularul „Document de informare cu privire la comisioane" e impus prin
      lege, cu secțiuni și terminologie identice la toate băncile. Se parsează
      DETERMINIST, fără niciun apel la model, cu `parser_rate.py`. Terminologia
      standard e și singurul loc unde comparația între bănci e garantată, nu
      sperată.

  (b) LISTE PROPRII DE TARIFE. Fiecare bancă își alege structura. `ambiguitate.py`
      scoate valorile corect — geometria bordurilor e rezolvată — dar etichetele
      de serviciu ies ca fragmente rupte: „programat1 si se percepe aditional
      sumei care depase". Propriul docstring al parserului o recunoaște:
      „eticheta e cea nesigura".

      Deci pe calea asta NU se folosește parserul pentru etichete. Se extrage
      textul cu pdfplumber și se trimite la model prin exact aceeași unealtă
      `raporteaza` din flow-html.py — cu vocabular închis și verificare de citat.
      Citatul se poate verifica, fiindcă avem textul.

CE NU FACE

  Nu scrie Bronze. Routerul descarcă, deci acolo sunt bytes-ii bruți.

  Nu citește PDF-uri scanate. Fără strat de text, pdfplumber întoarce gol, iar
  rezultatul e `stare: gol` cu motivul — nu se inventează OCR în tăcere.

    pip install pdfplumber
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import re
import sys
import tempfile
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pdfplumber
from anthropic import AsyncAnthropic

RADACINA = Path(__file__).parent


def _modul(nume: str, fisier: str):
    """Încarcă un fișier ca modul. Necesar pentru numele cu cratimă."""
    spec = importlib.util.spec_from_file_location(nume, RADACINA / fisier)
    m = importlib.util.module_from_spec(spec)
    sys.modules[nume] = m
    spec.loader.exec_module(m)
    return m


# flow-html.py dă vocabularul, validarea și forma observațiilor. Nu se duplică:
# două implementări ale lui `valideaza` ar divergea, iar divergența ar produce
# observații care trec într-un flow și cad în celălalt.
fh = _modul("flow_html", "flow-html.py")

# `parser_rate.py` e parserul formularului standardizat, autonom.
pad = _modul("parser_pad", "parser_rate.py")

# `ambiguitate.py` importă `crawler.parser_pdf`, care ESTE `parser_rate.py` —
# numele fișierelor s-au amestecat la copiere. Se satisface aliasul în
# sys.modules, ca să nu fie nevoie să edităm fișierele adăugate.
_pachet = types.ModuleType("crawler")
_pachet.__path__ = []
sys.modules.setdefault("crawler", _pachet)
sys.modules.setdefault("crawler.parser_pdf", pad)
nestd = _modul("parser_nestandardizat", "ambiguitate.py")

MODEL = fh.MODEL
MAX_CARACTERE_LLM = fh.MAX_CARACTERE_LLM

# Titlul se caută în CONȚINUT, nu în numele fișierului: din 38 de PDF-uri din
# inventare, doar 2 au numele formularului, dar formularul e obligatoriu legal
# la toate băncile care oferă conturi de plăți. Numele nu e o dovadă.
RE_TITLU_PAD = pad.RE_TITLU_FID

# Secțiunile normalizate ale formularului PAD, mapate pe vocabularul nostru.
# Aici maparea e legitimă fiindcă terminologia e impusă prin lege. La listele
# proprii nu se poate: etichetele sunt fragmente, nu denumiri.
CAMP_DIN_PAD = {
    ("servicii_de_cont", "administrare"): "comision_administrare_lunar",
    ("servicii_de_cont", "anual"): "comision_administrare_anual",
    ("servicii_de_cont", "deschidere"): "comision_deschidere",
    ("plati", "urgen"): "comision_plata_urgenta",
    ("plati", "interbanc"): "comision_plata_interbancara",
    ("plati", "intrabanc"): "comision_plata_intrabancara",
    ("plati", "incas"): "comision_incasare",
    ("plati", ""): "comision_plata_interbancara",
    ("carduri_si_numerar", "emitere"): "comision_emitere_card",
    ("carduri_si_numerar", "administrare"): "comision_administrare_card",
    ("carduri_si_numerar", "retrage"): "comision_retragere_atm",
    ("carduri_si_numerar", "depuner"): "comision_depunere_numerar",
    ("carduri_si_numerar", ""): "comision_administrare_card",
    ("alte_servicii", ""): "altele",
}

UNITATE_DIN_MONEDA = {"LEI": "lei", "EUR": "eur", "USD": "usd", None: "lei"}


def text_pdf(cale: Path) -> tuple[str, int]:
    """
    Textul documentului și numărul de pagini.

    Gol înseamnă PDF scanat, fără strat de text. Nu se încearcă OCR: ar produce
    valori pe care `valideaza` nu le poate verifica față de nimic.
    """
    bucati, pagini = [], 0
    with pdfplumber.open(str(cale)) as doc:
        pagini = len(doc.pages)
        for p in doc.pages:
            bucati.append(p.extract_text() or "")
    return "\n".join(bucati).strip(), pagini


def e_standardizat(text: str) -> bool:
    return bool(RE_TITLU_PAD.search(text[:6000]))


def camp_din_pad(inregistrare: dict) -> str:
    """Câmpul canonic pentru o înregistrare din formularul standardizat."""
    sectiune = (inregistrare.get("sectiune") or "").lower()
    serviciu = (inregistrare.get("serviciu") or "").lower()
    for (sect, cheie), camp in CAMP_DIN_PAD.items():
        if sect == sectiune and (not cheie or cheie in serviciu):
            return camp
    return "altele"


def valori_din_pad(inregistrari: list[dict], produs: str) -> list[dict]:
    """
    Înregistrările deterministe, în forma pe care o așteaptă `valideaza`.

    `incredere` e 0.95, nu 1.0, și nu e o precauție de formă: parserul e
    determinist, dar atribuirea etichetei către valoare depinde de geometria
    bordurilor, iar acolo pot apărea uniri greșite.
    """
    permise = set(fh.CAMPURI.get(produs, []))
    valori = []
    for r in inregistrari:
        camp = camp_din_pad(r)
        if camp not in permise:
            continue
        procent = r.get("tip") == "comision_procent"
        valori.append({
            "camp": camp,
            "cod_scenariu": (r.get("conditie") or r.get("frecventa") or None),
            "valoare_num": r.get("valoare"),
            "unitate": "procent" if procent else UNITATE_DIN_MONEDA.get(
                r.get("moneda"), "lei"),
            "moneda": r.get("moneda"),
            "citat": (r.get("text_sursa") or r.get("serviciu") or "")[:200],
            "incredere": 0.95,
            "_pagina": r.get("pagina"),
        })
    return valori


async def proceseaza(
    pdf: bytes | None,
    metoda: str,
    produse: list[str],
    url: str | None = None,
    hash_anterior: str | None = None,
    include_text: bool = False,
    scenariu: dict | bool | None = None,
    focus: str | None = None,
) -> dict:
    """
    Aceeași semnătură și aceeași formă de rezultat ca `flow-html.proceseaza`.

    pdf            octeții documentului, descărcați de router
    produse        produsele asociate documentului la discovery
    hash_anterior  dacă e identic cu hashul textului, nu se extrage
    """
    acum = datetime.now(timezone.utc).isoformat()
    necunoscute = [p for p in produse if p not in fh.CATALOG]
    produse = [p for p in produse if p in fh.CATALOG]

    baza: dict[str, Any] = {
        "url": url, "tip": "pdf", "metoda": metoda, "procesat_la": acum,
        "produse_cerute": produse,
    }
    if necunoscute:
        baza["produse_necunoscute"] = necunoscute
    if not produse:
        return {**baza, "stare": "eroare",
                "eroare": "niciun produs cunoscut în listă", "rezultate": {}}
    if not pdf:
        return {**baza, "stare": "eroare", "eroare": "conținut PDF gol",
                "rezultate": {}}

    # pdfplumber cere o cale, nu octeți.
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf)
        cale = Path(f.name)
    try:
        try:
            text, pagini = text_pdf(cale)
        except Exception as e:
            return {**baza, "stare": "eroare",
                    "eroare": f"PDF necitibil: {type(e).__name__}: {e}"[:200],
                    "rezultate": {}}

        standardizat = e_standardizat(text)
        baza["pdf"] = {
            "pagini": pagini,
            "lungime_text": len(text),
            "standardizat_258_2017": standardizat,
            "cale_extractie": "determinist" if standardizat else "model",
        }

        if not text:
            return {**baza, "stare": "gol", "rezultate": {},
                    "avertisment": "PDF fără strat de text, probabil scanat; "
                                   "nu se face OCR, deci nu există ce valida"}

        h = fh.hash_stabil(text)
        baza["content_hash"] = h
        if include_text:
            baza["text_sanitizat"] = text
        if hash_anterior and h == hash_anterior:
            return {**baza, "stare": "neschimbat", "rezultate": {},
                    "nota": "conținut identic cu rularea anterioară"}

        ai = AsyncAnthropic()
        banca = (url or "").split("//")[-1].split("/")[0]

        async def unul(p: str) -> tuple[str, dict]:
            if standardizat:
                # Calea deterministă: zero apeluri la model.
                brute = pad.extrage(cale, banca)
                valori = valori_din_pad(brute, p)
                tokeni, nota = None, (
                    f"formular standardizat Legea 258/2017, parsat determinist; "
                    f"{len(brute)} înregistrări în document")
            else:
                sc = (scenariu if scenariu is not None
                      else fh.scenariu_implicit(p))
                rez = await fh.extrage(ai, p, text,
                                       url or "(sursă nespecificată)",
                                       sc or None, focus=focus)
                valori = rez.get("valori", [])
                tokeni, nota = rez.get("_tokeni"), rez.get("nota")

            ok, respinse = fh.valideaza(valori, p, text)
            return p, {
                "gasit": bool(ok),
                "valori": ok,
                "respinse": respinse,
                "nota": nota,
                "mod_text": "pdf_determinist" if standardizat else "pdf_integral",
                "caractere_trimise": 0 if standardizat else len(
                    text[:MAX_CARACTERE_LLM]),
                "tokeni": tokeni,
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
                "tokeni_intrare": sum((r["tokeni"] or {}).get("intrare", 0)
                                      for r in rezultate.values()),
                "tokeni_iesire": sum((r["tokeni"] or {}).get("iesire", 0)
                                     for r in rezultate.values()),
            },
        }
    finally:
        cale.unlink(missing_ok=True)


# `ca_observatii` vine din flow-html: aceeași formă de rând, aceleași coloane.
ca_observatii = fh.ca_observatii


async def main() -> None:
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass

    ap = argparse.ArgumentParser(
        description="Extracție PDF. În producție, routerul importă `proceseaza`.")
    sursa = ap.add_mutually_exclusive_group(required=True)
    sursa.add_argument("--fisier", help="PDF local")
    sursa.add_argument("--url", help="descarcă documentul (doar pentru testare)")
    ap.add_argument("--produse", required=True, help="separate prin virgulă")
    ap.add_argument("--out")
    ap.add_argument("--text-out", metavar="FISIER",
                    help="scrie textul extras din PDF")
    a = ap.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("Lipsește ANTHROPIC_API_KEY.")

    if a.fisier:
        octeti, url = Path(a.fisier).read_bytes(), None
    else:
        import httpx
        async with httpx.AsyncClient(headers=fh.ANTETE, timeout=fh.TIMEOUT,
                                     follow_redirects=True) as c:
            r = await c.get(a.url)
        if r.status_code in fh.STATUS_REFUZ:
            raise SystemExit(f"Serverul a refuzat: {r.status_code}")
        r.raise_for_status()
        octeti, url = r.content, a.url

    rez = await proceseaza(
        pdf=octeti, metoda="http",
        produse=[p.strip() for p in a.produse.split(",") if p.strip()],
        url=url, include_text=bool(a.text_out))

    t = rez.pop("text_sanitizat", None)
    if a.text_out and t:
        Path(a.text_out).write_text(t, encoding="utf-8")
        print(f"Text în {a.text_out} ({len(t)} caractere)", file=sys.stderr)

    text = json.dumps(rez, ensure_ascii=False, indent=2)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"Scris în {a.out}", file=sys.stderr)
    else:
        print(text)

    print(f"\n  stare: {rez['stare']}", file=sys.stderr)
    if rez.get("pdf"):
        p = rez["pdf"]
        print(f"  {p['pagini']} pagini, {p['lungime_text']} caractere, "
              f"cale {p['cale_extractie']}"
              f"{' (Legea 258/2017)' if p['standardizat_258_2017'] else ''}",
              file=sys.stderr)
    if rez["stare"] == "extras":
        b = rez["bilant"]
        print(f"  produse găsite     {b['produse_gasite']}/{b['produse_cerute']}",
              file=sys.stderr)
        print(f"  valori acceptate   {b['valori_acceptate']}", file=sys.stderr)
        print(f"  valori respinse    {b['valori_respinse']}  ← verifică",
              file=sys.stderr)
        print(f"  tokeni             {b['tokeni_intrare']} in / "
              f"{b['tokeni_iesire']} out", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
