"""Alege, per bancă, pagina de pe care banca publică lista de tarife.

De ce: 2.858 de observații de comision nu au niciun link. Cauza nu se poate
repara din datele existente — pachetul sursă reține calea locală a PDF-ului
(`libra/5a7975c2_Tarife_si_Comisioane_PF.pdf`) și pagina, dar nu URL-ul de
descărcare, iar PDF-urile nu sunt în pachet. Din 68 de documente, 9 s-au legat
exact la un URL descoperit; restul nu sunt printre cele 40 de URL-uri de PDF pe
care le-a găsit discovery-ul. Verificat: nu există mai mult de potrivit.

Ce se poate face onest: pentru aproape fiecare bancă, discovery-ul a găsit
pagina de pe care banca publică documentele — `librabank.ro/comisioane`,
`procreditbank.ro/lista-de-preturi/`, `creditcoop.ro/documente/`. Afirmația
„documentul se publică aici" e verificabilă și adevărată. Nu e același lucru cu
un link către documentul exact, și de-aia interfața le arată diferit: link
direct cu ↗, pagina băncii cu altă etichetă și un titlu care spune explicit că
nu e documentul însuși.

Alegerea e pe punctaj, nu pe prima potrivire, ca să fie repetabilă și
contestabilă. Motivul se scrie în baza de date.

Idempotent: rescrie de fiecare dată aceeași alegere pentru aceleași surse.
"""

import collections
import io
import os
import re
import sys
import urllib.parse

import psycopg2

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AICI))
sys.path.insert(0, AICI)
import config                      # noqa: E402
import normalizeaza as N           # noqa: E402

# Cuvinte din calea URL, cu punctaj. O pagină de listă de prețuri bate o pagină
# generică de documente, care bate un „informații utile". Punctajele sunt
# relative, nu absolute - contează doar ordinea dintre ele.
PUNCTAJ_CALE = [
    (r"lista[-_]?de[-_]?preturi",            100),
    (r"tarife[-_]?si[-_]?comisioane",         95),
    (r"^/comisioane/?$",                      90),
    (r"tarife",                               80),
    # `comisio`, nu `comision`: „comisioane" NU conține „comision" (după
    # `comisio` vine `a`, nu `n`). Cu forma lungă, pagina de comisioane a BCR
    # punctа doar 40, pe „informatii-utile", și pierdea în fața altei pagini.
    (r"comisio",                              75),
    (r"taxe",                                 70),
    (r"documente[-_]?contractuale",           65),
    (r"documente",                            60),
    (r"fees|pricing",                         55),
    (r"informatii[-_]?utile",                 40),
    (r"dobanzi",                              30),
]

# Rolul pus de discovery. `conditii` e cel mai bun semnal: discovery-ul a
# clasificat pagina ca fiind despre termenii contractuali.
PUNCTAJ_ROL = {"conditii": 25, "hub": 15, "produs": 5, "context": 0}

# Segmentul documentului, dedus din numele fisierului. O pagina de tarife PJ
# nu e cea mai buna insotitoare pentru un document PF, dar e mai buna decat
# nimic - de-aia e un bonus, nu un filtru.
SEGMENT = {"pf": r"persoane[-_]?fizice|/pf|_pf", "pj": r"business|companii|juridice|/pj|_pj"}

# Sub pragul asta nu se alege nimic. O pagină aleasă doar fiindcă discovery-ul
# a găsit-o e mai rea decât lipsa unui link: sugerează că documentul se publică
# acolo, ceea ce ar fi o afirmație falsă.
PRAG_MIN = 35


def fara_diacritice(t):
    sys.path.insert(0, os.path.join(os.path.expanduser("~"), "Desktop", "Scraping"))
    from scraper import strip_diacritics
    return strip_diacritics(t)


def puncteaza(url, rol):
    """Punctaj + explicația lui, ca alegerea să poată fi contestată."""
    p = urllib.parse.urlparse(url)
    cale = fara_diacritice(urllib.parse.unquote(p.path).lower()) or "/"
    total, motive = 0, []

    # Se ia cel mai MARE punctaj care se potrivește, nu primul din listă.
    # Cu `break` pe prima potrivire, ordinea regulilor decidea în locul
    # specificității: `/ro/persoane-fizice/informatii-utile/comisioane` primea
    # 40 pentru „informatii-utile" în loc de 75 pentru „comisioane", și pagina
    # de business a BCR (mai puțin adâncă) o bătea pe cea corectă.
    potrivite = [(pct, rx) for rx, pct in PUNCTAJ_CALE if re.search(rx, cale)]
    if potrivite:
        pct, rx = max(potrivite)
        total += pct
        motive.append(f"cale «{rx}» +{pct}")

    pr = PUNCTAJ_ROL.get(rol or "", 0)
    if pr:
        total += pr
        motive.append(f"rol {rol} +{pr}")

    # O pagină care E un PDF nu e „pagina de unde se publică": e un alt
    # document. Ar induce în eroare mai rău decât lipsa unui link.
    if cale.endswith(".pdf"):
        return 0, ["este un PDF, nu o pagină de publicare"]

    # Majoritatea documentelor din pachet sunt pentru persoane fizice
    # (segmentul `pf` domină în `cod_scenariu`), deci o pagină de tarife PF e
    # însoțitoarea mai potrivită decât una de business. Bonus, nu filtru: o
    # pagină de business e totuși mai bună decât niciun link.
    if re.search(SEGMENT["pf"], cale):
        total += 10
        motive.append("pagină PF +10")
    elif re.search(SEGMENT["pj"], cale):
        total -= 10
        motive.append("pagină PJ −10")

    # Mai puțin adânc = mai aproape de indexul de documente. Diferența e mică,
    # dar rupe egalitățile într-un mod previzibil.
    adancime = len([x for x in cale.split("/") if x])
    total -= adancime
    motive.append(f"adâncime {adancime} −{adancime}")
    return total, motive


def main():
    config.incarca()
    err = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", write_through=True)
    raport = collections.Counter()

    with psycopg2.connect(N.dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT b.slug, b.nume, s.sursa, s.rol
                   FROM surse s JOIN banci b ON b.id = s.id_banca
                   WHERE s.tip_sursa = 'url' AND s.status = 'activ'
                   ORDER BY b.slug"""
            )
            pe_banca = collections.defaultdict(list)
            for slug, nume, url, rol in cur.fetchall():
                pe_banca[slug].append((url, rol))

            # câte documente fără link are fiecare bancă: arată cât ajută
            cur.execute(
                """SELECT b.slug, count(*)::int
                   FROM surse s JOIN banci b ON b.id = s.id_banca
                   WHERE s.tip_sursa = 'document' AND s.url_public IS NULL
                   GROUP BY 1"""
            )
            fara_link = dict(cur.fetchall())

            alese = {}
            for slug, surse in sorted(pe_banca.items()):
                candidati = []
                for url, rol in surse:
                    pct, motive = puncteaza(url, rol)
                    if pct >= PRAG_MIN:
                        candidati.append((pct, url, motive))
                if not candidati:
                    # Mai bine niciun link decât unul greșit. Fără prag, Cetelem
                    # primea o pagină de tombolă promoțională și Vista o pagină
                    # despre agricultură — doar fiindcă discovery-ul le găsise.
                    raport["banci_fara_pagina_potrivita"] += 1
                    continue
                candidati.sort(key=lambda x: (-x[0], x[1]))
                pct, url, motive = candidati[0]
                alese[slug] = (url, f"punctaj {pct}: " + ", ".join(motive))

            for slug, (url, motiv) in sorted(alese.items()):
                cur.execute(
                    """UPDATE banci SET pagina_documente = %s,
                                        pagina_documente_motiv = %s
                       WHERE slug = %s""",
                    (url, motiv, slug),
                )
                raport["pagini_alese"] += 1
                raport["documente_acoperite"] += fara_link.get(slug, 0)

    err.write(f"{raport['pagini_alese']} bănci au acum o pagină de publicare\n")
    err.write(f"acoperă {raport['documente_acoperite']} documente care nu aveau niciun link\n\n")
    for slug, (url, motiv) in sorted(alese.items(), key=lambda x: -fara_link.get(x[0], 0)):
        n = fara_link.get(slug, 0)
        err.write(f"  {slug:14s} {n:3d} doc  {url[:64]}\n")
    N.raporteaza(raport, sys.stderr)


if __name__ == "__main__":
    main()
