"""Popularea inițială a bazei — un singur punct de intrare, o singură scriere.

De ce există: baza ajunsese o stratificare a încercărilor, nu rezultatul unui
pipeline. Cinci proveniențe scrise la momente diferite, 2.933 de grupuri cu
aceeași valoare din surse diferite și 3.483 de rânduri redundante — fiindcă
deduplicarea funcționa doar în interiorul unei rulări, nu între ele.

Aici totul trece prin O SINGURĂ normalizare, deci printr-o singură trecere de
deduplicare semantică. „Administrare cont, 15 lei, lunar, la BCR" e un fapt,
oricâte drumuri duc la el.

CELE TREI VARIANTE, fiecare cu ce are ea mai bun:

  1. scraperul propriu (Desktop/Scraping)
     - `scraper.py`     transport HTTP: UA care ne identifică, delay, encoding
     - depozitele       singura variantă care acoperă produsele de economisire

  2. Playwright, pachetul colegului (pentru_coleg_bs4_21sept/crawler)
     - `parser_pdf`     formularele standardizate prin Legea 258/2017
     - `parser_tarife`  listele de tarife nestandardizate
     - `parser_rate`    dobânzile din HTML
     - `vocabular`      maparea la conceptul canonic — fără ea, valorile ajung
                        în găleata generică și nu apar în nicio comparație
     - `robots.py`      robots.txt după RFC 9309, cu wildcard-uri. `urllib` face
                        doar potrivire pe prefix și ratează `Disallow: *.pdf`,
                        regula reală a ING
     - `urme.py`        amprentă pe OCTEȚI + nume stabil de fișier
     - `data_document`  data de vigoare, citită din textul documentului
     - `ambiguitate`    valori adevărate dar neatribuibile
     - browserul        transport de treapta 2, singurul care deblochează CEC
     - JSON-ul lui      comisioane din PDF-uri pe care noi nu le mai putem lua

  3. discovery LLM (flux-colectare)
     - inventarul       757 de surse găsite fără sitemap
     - `web_fetch`      transport de treapta 3, cu robots impus de Anthropic

TRASEUL, ca în figura 3 din artefact, aplicat identic oricărei surse:

    robots.txt ─► transport (http → playwright → llm) ─► Bronze
                                                           │
                                          amprentă pe octeți vs. ce știam
                                                           │
                                   identică ──► STOP, nimic nou
                                                           │
                                                      diferită
                                                           ▼
                                  extracție ─► vocabular ─► normalizare
                                                           │
                                                           ▼
                                    dedup semantic ─► observations

Rulare:
    python ingest/populare_initiala.py                 # tot, de la zero
    python ingest/populare_initiala.py --doar-fisiere  # fără rețea, rapid
    python ingest/populare_initiala.py --banca cec
    python ingest/populare_initiala.py --pastreaza     # nu golește baza
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

import config                      # noqa: E402
import extractoare                 # noqa: E402
import flux                        # noqa: E402
import normalizeaza as N           # noqa: E402

METODA = "populare"


def goleste(err):
    """Șterge observațiile și amprentele. Bronze RĂMÂNE.

    Observațiile se reconstruiesc din Bronze; Bronze nu se reconstruiește
    decât cerând din nou paginile băncilor. De aceea el rămâne: o repopulare
    nu trebuie să însemne încă o rundă de cereri către 30 de bănci.
    """
    with psycopg2.connect(N.dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM observations")
            o = cur.rowcount
            cur.execute("DELETE FROM hashes")
            h = cur.rowcount
    err.write(f"golit: {o} observații, {h} amprente. Bronze păstrat.\n\n")


def din_fisiere(err, raport):
    """Variantele care citesc din pachete locale: fără rețea, deci rapide."""
    brute = []
    for nume, generator in (("pachetul Playwright", extractoare.din_playwright()),
                            ("depozite (scraper propriu)", extractoare.din_bs4_depozite())):
        n = 0
        for b in generator:
            brute.append(b)
            n += 1
        err.write(f"  {nume:32s} {n:6d} înregistrări brute\n")
        raport[f"brut_{nume.split()[0].lower()}"] += n
    return brute


def din_rețea(err, raport, banca=None, limita=None, fara_llm=False):
    """Fluxul peste inventarul de surse, cu cascada de transport."""
    brute, stare = [], {}
    try:
        with psycopg2.connect(N.dsn()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT s.id, b.slug, s.sursa, s.format, s.rol
                       FROM surse s JOIN banci b ON b.id = s.id_banca
                       WHERE s.tip_sursa = 'url' AND s.status = 'activ'
                         AND s.rol IN ('produs', 'conditii')
                         AND (%s = '' OR b.slug = %s)
                       ORDER BY b.slug, s.format DESC, s.sursa""",
                    (banca or "", banca or ""),
                )
                surse = cur.fetchall()
                if limita:
                    surse = surse[:limita]
                pe_banca = collections.defaultdict(list)
                for s in surse:
                    pe_banca[s[1]].append(s)
                banci = sorted(pe_banca)
                err.write(f"  {len(surse)} surse, {len(banci)} bănci · cascadă: "
                          f"http → playwright{'' if fara_llm else ' → llm'}\n\n")

                for i, slug in enumerate(banci, 1):
                    stari, note, n = collections.Counter(), [], 0
                    for s in pe_banca[slug]:
                        b_noi, j = proceseaza(s, cur, stare, fara_llm)
                        stari[j["stare"]] += 1
                        raport["stare_" + str(j["stare"])] += 1
                        if j["transport"]:
                            raport["transport_" + j["transport"]] += 1
                        note.append((slug, j["sursa"], None if j["stare"] in
                                     ("OK", "NESCHIMBAT") else
                                     (str(j["stare"]) + ": " + str(j["nota"] or ""))[:300]))
                        brute.extend(b_noi)
                        n += len(b_noi)
                        time.sleep(1.5)
                    err.write(f"  [{i:2d}/{len(banci)}] {slug:20s} "
                              f"{len(pe_banca[slug]):3d} surse → {n:5d} brute  "
                              f"{dict(stari)}\n")
                    if note:
                        N.noteaza_surse(note)
    finally:
        if "browser" in stare:
            stare["browser"].close()
            stare["pw"].stop()
    return brute


def proceseaza(sursa, cur, stare, fara_llm=False):
    """Traseul complet pentru o sursă. Întoarce (brute, jurnal)."""
    sid, slug, url, fmt, rol = sursa
    j = {"sursa": url, "banca": slug, "transport": None, "stare": None, "nota": None}

    if not flux.permite(url, slug):
        j["stare"], j["nota"] = "ROBOTS", "interzis de robots.txt al băncii"
        return [], j

    octeti, motive = None, []
    for nume, aducator in flux.CASCADA:
        if nume == "llm" and fara_llm:
            continue
        octeti, nota = aducator(url, stare)
        if octeti:
            j["transport"], j["nota"] = nume, nota
            break
        motive.append(f"{nume}: {nota}")
        time.sleep(1.2)
    if not octeti:
        j["stare"], j["nota"] = "INACCESIBIL", " | ".join(motive)
        return [], j

    cale = flux.scrie_bronze(url, octeti)
    amp = flux.amprenta(octeti)
    if flux.amprenta_cunoscuta(cur, sid, amp):
        j["stare"], j["nota"] = "NESCHIMBAT", "aceiași octeți ca la ultima rulare"
        return [], j
    cur.execute("INSERT INTO hashes (id_sursa, format, hash) VALUES (%s, %s, %s)",
                (sid, "pdf" if octeti.startswith(b"%PDF") else "html", amp))

    # Formatul se decide din PRIMII OCTEȚI, nu din extensia URL-ului:
    # extensia și Content-Type mint amândouă (regula din artefact).
    if octeti.startswith(b"%PDF"):
        b_noi, nota = extractoare.din_pdf(cale, slug, sursa=url)
    else:
        b_noi, nota = extractoare.din_html(octeti, url, slug, rol)
    j["nota"], j["stare"] = nota, ("OK" if b_noi else "GOL")
    return b_noi, j


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--banca", help="doar o bancă (slug)")
    ap.add_argument("--limita", type=int, help="oprește după N surse din rețea")
    ap.add_argument("--doar-fisiere", action="store_true",
                    help="fără rețea: doar pachetele locale")
    ap.add_argument("--fara-llm", action="store_true",
                    help="sari treapta 3 a cascadei (costă per apel)")
    ap.add_argument("--pastreaza", action="store_true",
                    help="nu golește baza înainte")
    a = ap.parse_args()

    config.incarca()
    err = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", write_through=True)
    raport = collections.Counter()

    if not a.pastreaza and not a.banca:
        goleste(err)

    err.write("═══ 1. Variantele din fișier (fără rețea)\n")
    brute = din_fisiere(err, raport)

    if not a.doar_fisiere:
        err.write("\n═══ 2. Fluxul peste inventar (rețea)\n")
        brute += din_rețea(err, raport, a.banca, a.limita, a.fara_llm)

    err.write(f"\n═══ 3. Normalizare + dedup + scriere ({len(brute)} brute)\n")
    randuri = [x for x in (N.normalizeaza(b, raport) for b in brute) if x]
    N.scrie(randuri, METODA, raport)

    err.write("\n")
    N.raporteaza(raport, sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
