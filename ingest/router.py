"""Routerul: decide ce extractor primește fiecare sursă, apoi normalizează.

Singurul punct de intrare pentru date în baza MIP. Înlocuiește cele trei
loadere separate, fiecare cu propria listă de intrare și propria mapare.

    python ingest/router.py --pas playwright      # comisioane PDF + rate
    python ingest/router.py --pas bs4             # depozite (scraperul propriu)
    python ingest/router.py --pas descoperite     # sursele găsite de LLM (rețea)
    python ingest/router.py --pas tot             # toate, în ordine

Pentru pasul `descoperite`, sursele vin din tabela `surse` — care are deja
`format` și `rol` de la discovery — și se aleg cele cu `metoda_extractie IS NULL`.
Adică: exact ce a fost descoperit și niciodată extras. Rularea e incrementală,
fiindcă sursele procesate se marchează.

    python ingest/router.py --pas descoperite --banca banca-transilvania
    python ingest/router.py --pas descoperite --limita 20        # probă
"""

import argparse
import collections
import io
import os
import sys
import time

import psycopg2

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AICI))
sys.path.insert(0, AICI)

import config                                                        # noqa: E402
import extractoare                                                   # noqa: E402
import normalizeaza as N                                              # noqa: E402


def _err():
    return io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", write_through=True)


def pas_din_fisier(generator, metoda, err):
    """Pașii care citesc dintr-un pachet local: fără rețea, deci fără pauze."""
    raport = collections.Counter()
    randuri = [x for x in (N.normalizeaza(b, raport) for b in generator) if x]
    err.write(f"{len(randuri)} randuri normalizate, provenienta '{metoda}'\n")
    N.scrie(randuri, metoda, raport)
    return raport


def pas_descoperite(err, banca=None, limita=None, roluri=("produs", "conditii")):
    """Veriga lipsă: extracție peste sursele pe care discovery-ul le-a găsit.

    Se scrie în bază la fiecare bancă, nu la final. O rulare de câteva sute de
    pagini nu trebuie să se piardă dacă a 200-a cade.
    """
    raport = collections.Counter()
    with psycopg2.connect(N.dsn()) as conn:
        with conn.cursor() as cur:
            # Candidații includ și sursele extrase ANTERIOR de acest pas
            # (`bs4_llm`), nu doar cele neatinse. Altfel rularea e distructivă,
            # nu idempotentă: ștergerea de la început curăță toate observațiile
            # `bs4_llm`, dar sursele deja marcate n-ar mai fi reprocesate, deci
            # datele lor dispar. Măsurat pe pielea proprie: 141 observații au
            # devenit 38 la a doua rulare.
            cur.execute(
                """SELECT b.slug, s.sursa, s.rol
                   FROM surse s JOIN banci b ON b.id = s.id_banca
                   WHERE (s.metoda_extractie IS NULL OR s.metoda_extractie = 'bs4_llm')
                     AND s.tip_sursa = 'url'
                     AND s.format = 'html' AND s.rol = ANY(%s)
                     AND s.status = 'activ'
                     AND (%s = '' OR b.slug = %s)
                   ORDER BY b.slug, s.sursa""",
                (list(roluri), banca or "", banca or ""),
            )
            candidati = cur.fetchall()

    if limita:
        candidati = candidati[:limita]
    banci = sorted({b for b, _, _ in candidati})
    err.write(f"{len(candidati)} surse neextrase, {len(banci)} bănci\n\n")

    pe_banca = collections.defaultdict(list)
    for slug, url, rol in candidati:
        pe_banca[slug].append((url, rol))

    # O singură ștergere, la început: mai jos se scrie incremental, per bancă.
    if not banca and not limita:
        raport["observatii_sterse"] = N.curata("bs4_llm")

    note = []
    for i, slug in enumerate(banci, 1):
        randuri, stari, de_notat = [], collections.Counter(), []
        for url, rol in pe_banca[slug]:
            brute, stare, nota, pauza = extractoare.din_html_live(url, slug, rol or "produs")
            stari[stare] += 1
            raport[f"pagini_{stare}"] += 1
            if stare != "OK":
                # Motivul e informație, nu absență de informație: „blocat de
                # robots.txt", „403 WAF" și „randată prin JS" cer acțiuni
                # diferite. Fără el, toate trei arată identic în interfață -
                # o sursă fără observații.
                de_notat.append((slug, url, f"{stare}: {nota or ''}"[:300]))
                if nota:
                    note.append((slug, url, stare, nota))
            else:
                # Nota se ȘTERGE la reușită. Altfel o sursă care a eșuat
                # într-o rulare și a mers în următoarea rămâne marcată ca
                # problemă, iar bilanțul din pagina Surse minte.
                de_notat.append((slug, url, None))
            for b in brute:
                r = N.normalizeaza(b, raport)
                if r:
                    randuri.append(r)
            if pauza:
                time.sleep(pauza)
        err.write(f"[{i}/{len(banci)}] {slug:20s} "
                  f"{len(pe_banca[slug]):3d} pagini -> {len(randuri):4d} valori  "
                  f"{dict(stari)}\n")
        if randuri:
            # Se scrie la fiecare bancă, nu la final: o rulare de câteva sute
            # de pagini nu trebuie să se piardă dacă a 200-a cade.
            N.scrie(randuri, "bs4_llm", raport, sterge=False)
        if de_notat:
            N.noteaza_surse(de_notat)
            raport["surse_cu_nota"] += len(de_notat)

    if note:
        err.write("\n--- surse fără rezultat, cu motiv ---\n")
        for slug, url, stare, nota in note[:40]:
            err.write(f"  {slug:18s} {stare:14s} {str(nota)[:56]:58s} {url[:52]}\n")
        if len(note) > 40:
            err.write(f"  … și {len(note) - 40} altele\n")
    return raport


def pas_pdf(err, banca=None, limita=None):
    """Comisioanele din PDF-urile de tarife ale băncilor.

    Veriga care lipsea cel mai vizibil: măsurat înainte, comisioanele existau
    în bază exact la băncile care aveau un PDF adus de pachetul colegului.
    Celelalte 16 - ING, Patria, Nexent, Cetelem, Vista, Banca Transilvania,
    UniCredit, CEC și restul - aveau ZERO pe pagina 2.1, deși multe răspund
    perfect la HTTP simplu. Nu erau bănci problematice; nimic nu citea PDF-uri.

    Traseul: se iau URL-urile de PDF pe care le avem deja în `surse` (puse de
    discovery sau recoltate de pe pagina de tarife a băncii), se descarcă prin
    cache-ul local, se detectează dacă documentul e formularul standardizat
    prin Legea 258/2017 și se dă parserului potrivit.

    Sursa înregistrată e URL-ul public, nu calea din cache: altfel dovada ar
    duce la un nume de fișier temporar, care nu spune nimic nimănui.
    """
    raport = collections.Counter()
    with psycopg2.connect(N.dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT b.slug, s.sursa
                   FROM surse s JOIN banci b ON b.id = s.id_banca
                   WHERE s.tip_sursa = 'url' AND s.format = 'pdf'
                     AND s.status = 'activ'
                     AND (s.metoda_extractie IS NULL OR s.metoda_extractie = 'pdf')
                     AND (%s = '' OR b.slug = %s)
                   ORDER BY b.slug, s.sursa""",
                (banca or "", banca or ""),
            )
            candidati = cur.fetchall()

    if limita:
        candidati = candidati[:limita]
    banci = sorted({b for b, _ in candidati})
    err.write(f"{len(candidati)} PDF-uri de procesat, {len(banci)} bănci\n\n")
    # Curățenia se face pe exact ce urmează să rescriem. La rulare pe o
    # singură bancă se șterg DOAR rândurile ei: altfel o rulare țintită fie
    # dubla datele (fără ștergere), fie ștergea toate celelalte bănci. Prima
    # variantă s-a și întâmplat: 1.603 valori ING au devenit 3.206.
    raport["observatii_sterse"] = N.curata("pdf", banci=banci if banca else None)

    pe_banca = collections.defaultdict(list)
    for slug, url in candidati:
        pe_banca[slug].append(url)

    for i, slug in enumerate(banci, 1):
        randuri, note = [], []
        for url in pe_banca[slug]:
            try:
                cale = descarca_pdf(url)
            except Exception as exc:
                note.append((slug, url, f"DESCARCARE: {type(exc).__name__}: {exc}"[:280]))
                raport["pdf_nedescarcat"] += 1
                continue
            brute, nota = extractoare.din_pdf(cale, slug, sursa=url)
            if not brute:
                note.append((slug, url, f"FARA_VALORI: {nota}"[:280]))
                raport["pdf_fara_valori"] += 1
            else:
                raport["pdf_citite"] += 1
            for b in brute:
                r = N.normalizeaza(b, raport)
                if r:
                    randuri.append(r)
            time.sleep(PAUZA_PDF)
        err.write(f"[{i}/{len(banci)}] {slug:20s} {len(pe_banca[slug]):3d} PDF-uri "
                  f"-> {len(randuri):5d} comisioane\n")
        if randuri:
            N.scrie(randuri, "pdf", raport, sterge=False)
        if note:
            N.noteaza_surse(note)
    return raport


PAUZA_PDF = 1.5      # aceeași politețe ca la restul colectării


def descarca_pdf(url):
    """Descarcă o singură dată și păstrează local.

    Refolosește cache-ul serverului (`app/.cache_pdf`), ca un document deschis
    din interfață să nu fie descărcat a doua oară pentru extracție, și invers.

    Se folosește `requests`, NU `urllib`. Motivul e măsurat: `urllib` verifică
    certificatele prin depozitul sistemului, care pe mașina asta nu are
    intermediarele necesare, iar cele trei PDF-uri de tarife ale ING picau toate
    cu `CERTIFICATE_VERIFY_FAILED`. `requests` vine cu `certifi` și le ia fără
    problemă (HTTP 200, 398 KB). Aceeași stivă ca la restul colectării, deci și
    același User-Agent onest.
    """
    import hashlib
    import requests
    from scraper import HEADERS

    dosar = os.path.join(os.path.dirname(AICI), "app", ".cache_pdf")
    os.makedirs(dosar, exist_ok=True)
    cale = os.path.join(dosar, hashlib.sha256(url.encode()).hexdigest() + ".pdf")
    if os.path.exists(cale) and os.path.getsize(cale) > 1000:
        return cale
    antete = dict(HEADERS)
    antete["Accept"] = "application/pdf,*/*"
    r = requests.get(url, headers=antete, timeout=60)
    if not r.ok:
        raise ValueError(f"HTTP {r.status_code}")
    if not r.content.startswith(b"%PDF"):
        tip = (r.headers.get("Content-Type") or "?").split(";")[0]
        raise ValueError(f"nu e un PDF (Content-Type: {tip})")
    with open(cale, "wb") as f:
        f.write(r.content)
    return cale


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pas", required=True,
                    choices=["playwright", "bs4", "descoperite", "pdf", "tot"])
    ap.add_argument("--banca", help="doar o bancă (slug), la pasul descoperite")
    ap.add_argument("--limita", type=int, help="oprește după N surse (probă)")
    a = ap.parse_args()

    config.incarca()
    err = _err()
    total = collections.Counter()

    if a.pas in ("playwright", "tot"):
        err.write("\n=== PAS: playwright (comisioane PDF + rate HTML) ===\n")
        total.update(pas_din_fisier(extractoare.din_playwright(), "playwright", err))
    if a.pas in ("bs4", "tot"):
        err.write("\n=== PAS: bs4 (depozite, scraperul propriu) ===\n")
        total.update(pas_din_fisier(extractoare.din_bs4_depozite(), "bs4", err))
    if a.pas in ("descoperite", "tot"):
        err.write("\n=== PAS: descoperite (BS4 peste sursele găsite de LLM) ===\n")
        total.update(pas_descoperite(err, a.banca, a.limita))
    if a.pas in ("pdf", "tot"):
        err.write("\n=== PAS: pdf (comisioane din documentele de tarife) ===\n")
        total.update(pas_pdf(err, a.banca, a.limita))

    err.write("\n")
    N.raporteaza(total, sys.stderr)


if __name__ == "__main__":
    main()
