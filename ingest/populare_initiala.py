"""Popularea inițială a bazei, de la zero, pe flow-ul din artefact.

Nu se folosește nimic colectat anterior: nici pachetele JSON ale colegilor,
nici Bronze-ul vechi, nici inventarul vechi de surse. Totul vine din
scripturile din repo, rulate acum.

TREI BENZI, legate prin tabele, nu prin apeluri (figura 2):

  A. descoperire (`descoperire.py`)   → scrie DOAR în `surse`
  B. extracție   (acest fișier)       → citește `surse`, scrie `observations`
  C. locatoare   (Task 12)            → `locatii`

TRASEUL UNEI SURSE, identic pentru oricare (figura 3):

    transport.adu: robots.txt → requests (UA-ul echipei)
        BLOCAT (401/403/429/… sau pagină de blocaj) → STOP, sursa `blocat`
        JS (schelet randat în browser)              → Playwright, același UA
    → sanitizare → amprentă pe text sanitizat (PDF: octeți)
        identică: STOP │ diferită: Bronze
    → extracție deterministă (parserele din crawler/)
    → normalizare + deduplicare semantică → observations

Rularea pe bănci în paralel e sigură pentru servere: pauza e per origine
(Crawl-delay), iar fiecare bancă are propriul proces, deci nicio bancă nu
primește cereri mai dese decât într-o rulare secvențială.

Rulare:
    python ingest/populare_initiala.py --de-la-zero --paralel 6   # tot
    python ingest/populare_initiala.py --banca vista              # o bancă
    python ingest/populare_initiala.py --din-bronze               # reextrage,
                                                                  # fără rețea
"""

import argparse
import collections
import concurrent.futures
import datetime
import io
import os
import shutil
import subprocess
import sys

import psycopg2

AICI = os.path.dirname(os.path.abspath(__file__))
RADACINA = os.path.dirname(AICI)
sys.path.insert(0, RADACINA)
sys.path.insert(0, AICI)

import config                      # noqa: E402
import extractoare                 # noqa: E402
import flux                        # noqa: E402
import normalizeaza as N           # noqa: E402
import sanitizare                  # noqa: E402
import transport                   # noqa: E402

METODA = "populare"
LOGURI = os.path.join(RADACINA, "loguri", "banci")


# ==========================================================================
# Pornire de la zero
# ==========================================================================

def goleste_tot(err):
    """Nu rămâne nimic din colectările anterioare.

    Rămân cataloagele (`banci`, `produse`) și sursele care nu sunt web
    (aplicații mobile), fiindcă track-ul mobil le folosește. Bronze nu se
    șterge: se mută deoparte, ca dovadă a colectării anterioare.
    """
    with psycopg2.connect(N.dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM observations")
            o = cur.rowcount
            cur.execute("DELETE FROM hashes")
            web = "SELECT id FROM surse WHERE tip_sursa IN ('url', 'document')"
            # Explicit, nu prin CASCADE: FK-urile spre `surse` nu sunt toate
            # declarate cu ștergere în cascadă.
            cur.execute(f"DELETE FROM surse_produse WHERE id_sursa IN ({web})")
            cur.execute(f"DELETE FROM change_events WHERE id_sursa IN ({web})")
            cur.execute("DELETE FROM surse WHERE tip_sursa IN ('url', 'document')")
            s = cur.rowcount
    if os.path.isdir(flux.BRONZE):
        arhiva = f"{flux.BRONZE}_arhiva_{datetime.datetime.now():%Y%m%d_%H%M}"
        shutil.move(flux.BRONZE, arhiva)
    err.write(f"de la zero: {o} observații și {s} surse șterse, Bronze arhivat.\n\n")


# ==========================================================================
# Traseul unei surse
# ==========================================================================

def proceseaza(sursa, cur, stare, raport):
    """Traseul complet pentru o sursă, ca în figura 3. Întoarce (brute, jurnal)."""
    sid, slug, url, fmt, rol = sursa
    j = {"sursa": url, "banca": slug, "transport": None, "stare": None, "nota": None}
    rez = transport.adu(url, slug, stare)
    j["transport"], j["nota"] = rez.transport, rez.nota
    if rez.verdict != "OK":
        j["stare"] = rez.verdict
        if rez.verdict == "BLOCAT":
            # Documentat ca blocat, cu dovada; nu se încearcă alt canal.
            cur.execute("UPDATE surse SET status = 'blocat', nota_extractie = %s, "
                        "ultima_rulare = now() WHERE id = %s",
                        (f"blocat de bancă: {rez.nota}"[:300], sid))
        return [], j

    amp = sanitizare.amprenta_continut(rez.octeti)
    if flux.amprenta_cunoscuta(cur, sid, amp):
        j["stare"] = "NESCHIMBAT"
        return [], j
    cur.execute("INSERT INTO hashes (id_sursa, format, hash) VALUES (%s, %s, %s)",
                (sid, "pdf" if rez.octeti.startswith(b"%PDF") else "html", amp))
    cale = flux.scrie_bronze(url, rez.octeti)      # Bronze DOAR la schimbare
    return extrage(rez.octeti, cale, slug, url, rol, j)


def extrage(octeti, cale, slug, url, rol, j):
    """Extracția — aceeași fie că octeții vin de la bancă, fie din Bronze.

    Formatul se decide din PRIMII OCTEȚI, nu din extensia URL-ului: extensia
    și Content-Type mint amândouă (regula din artefact).
    """
    try:
        if rol == "locator":
            if not hasattr(extractoare, "din_locator"):
                j["stare"], j["nota"] = "AMANAT", "locatorul se extrage din Bronze (Task 12)"
                return [], j
            b_noi, nota = extractoare.din_locator(octeti, url, slug)
        elif octeti.startswith(b"%PDF"):
            b_noi, nota = extractoare.din_pdf(cale, slug, sursa=url)
        else:
            b_noi, nota = extractoare.din_html(octeti, url, slug, rol)
    except Exception as exc:
        # O pagină care strică parserul nu oprește toată banca; se numără.
        j["stare"], j["nota"] = "EROARE_EXTRACTIE", f"{type(exc).__name__}: {exc}"[:300]
        return [], j
    j["nota"], j["stare"] = nota, ("OK" if b_noi else "GOL")
    return b_noi, j


def surse_active(cur, banca=None, limita=None):
    cur.execute(
        """SELECT s.id, b.slug, s.sursa, s.format, s.rol
           FROM surse s JOIN banci b ON b.id = s.id_banca
           WHERE s.tip_sursa = 'url' AND s.status = 'activ'
             AND s.rol IN ('produs', 'conditii', 'locator')
             AND (%s = '' OR b.slug = %s)
           ORDER BY b.slug, s.rol, s.sursa""",
        (banca or "", banca or ""))
    surse = cur.fetchall()
    return surse[:limita] if limita else surse


def din_retea(err, raport, banca=None, limita=None):
    brute, stare = [], {}
    try:
        with psycopg2.connect(N.dsn()) as conn:
            with conn.cursor() as cur:
                surse = surse_active(cur, banca, limita)
                pe_banca = collections.defaultdict(list)
                for s in surse:
                    pe_banca[s[1]].append(s)
                for slug in sorted(pe_banca):
                    stari, note, n = collections.Counter(), [], 0
                    for s in pe_banca[slug]:
                        b_noi, j = proceseaza(s, cur, stare, raport)
                        stari[j["stare"]] += 1
                        raport["stare_" + str(j["stare"])] += 1
                        if j["transport"]:
                            raport["transport_" + j["transport"]] += 1
                        if j["stare"] not in ("OK", "NESCHIMBAT"):
                            note.append((slug, j["sursa"],
                                         f"{j['stare']}: {j['nota'] or ''}"[:300]))
                        brute.extend(b_noi)
                        n += len(b_noi)
                        conn.commit()
                    err.write(f"  {slug:20s} {len(pe_banca[slug]):4d} surse → "
                              f"{n:6d} brute  {dict(stari)}\n")
                    if note:
                        N.noteaza_surse(note)
    finally:
        transport.inchide(stare)
    return brute


def din_bronze(err, raport, banca=None):
    """Reextrage din Bronze, fără nicio cerere către bănci.

    Doar sursele cu amprentă în `hashes` (ce a adus ultima colectare), iar
    fiecare fișier se verifică față de amprenta lui înainte de folosire.
    """
    brute = []
    with psycopg2.connect(N.dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT s.id, b.slug, s.sursa, s.format, s.rol, array_agg(h.hash)
                   FROM surse s JOIN banci b ON b.id = s.id_banca
                   JOIN hashes h ON h.id_sursa = s.id
                   WHERE (%s = '' OR b.slug = %s)
                   GROUP BY s.id, b.slug ORDER BY s.id""",
                (banca or "", banca or ""))
            surse = cur.fetchall()
    stari = collections.Counter()
    for sid, slug, url, fmt, rol, amp in surse:
        j = {"sursa": url, "banca": slug, "transport": "bronze", "stare": None, "nota": None}
        cale = flux.cale_bronze(url)
        try:
            with open(cale, "rb") as f:
                octeti = f.read()
        except OSError:
            octeti = None
        if octeti is None:
            j["stare"] = "LIPSA_BRONZE"
        elif sanitizare.amprenta_continut(octeti) not in amp:
            j["stare"] = "AMPRENTA_DIFERITA"
        else:
            b_noi, j = extrage(octeti, cale, slug, url, rol, j)
            brute.extend(b_noi)
        stari[j["stare"]] += 1
        raport["stare_" + j["stare"]] += 1
    err.write(f"  {len(surse)} surse din Bronze · {dict(stari)}\n")
    return brute


# ==========================================================================
# O bancă, cap-coadă
# ==========================================================================

def ruleaza_banca(err, raport, banca, limita=None):
    import descoperire
    # O bancă rulată din nou se extrage integral: amprentele ei se șterg,
    # altfel sursele neschimbate n-ar produce nimic, iar scrierea (care
    # înlocuiește observațiile băncii) i-ar pierde datele.
    with psycopg2.connect(N.dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute("""DELETE FROM hashes h USING surse s, banci b
                           WHERE h.id_sursa = s.id AND b.id = s.id_banca AND b.slug = %s""",
                        (banca,))
    err.write("═══ 1. Descoperire\n")
    descoperire.ruleaza(err, raport, banca)
    err.write("\n═══ 2. Extracție\n")
    brute = din_retea(err, raport, banca, limita)
    scrie(err, raport, brute, [banca])


def scrie(err, raport, brute, banci):
    locatii = [b for b in brute if b.get("_locatie")]
    brute = [b for b in brute if not b.get("_locatie")]
    err.write(f"\n═══ 3. Normalizare + dedup + scriere ({len(brute)} brute, "
              f"{len(locatii)} locații)\n")
    import validare
    raport.update(validare.valideaza_rate(brute))
    randuri = [x for x in (N.normalizeaza(b, raport) for b in brute) if x]
    N.scrie(randuri, METODA, raport, banci=banci)
    scrie_locatii(locatii, raport)


def scrie_locatii(puncte, raport):
    """Locatorul băncii e sursa oficială: la băncile care îl au, înlocuiește
    Overture; la celelalte, Overture rămâne."""
    if not puncte:
        return
    with psycopg2.connect(N.dsn()) as conn:
        with conn.cursor() as cur:
            banci = sorted({p["banca"] for p in puncte})
            cur.execute("""DELETE FROM locatii l USING banci b
                           WHERE b.id = l.id_banca AND b.slug = ANY(%s)
                             AND l.sursa IN ('locator_banca', 'overture')""", (banci,))
            for p in puncte:
                cur.execute("""INSERT INTO locatii (id_banca, tip, nume, adresa, lat, lon,
                                   program, sursa, ref_extern, retea)
                               SELECT id, %s, %s, %s, %s, %s, %s, 'locator_banca', %s, %s
                               FROM banci WHERE slug = %s
                               ON CONFLICT (id_banca, tip, lat, lon) DO NOTHING""",
                            (p["tip"], p["nume"], p["adresa"], p["lat"], p["lon"],
                             p["program"], p["sursa"], p.get("retea", "proprie"), p["banca"]))
                raport["locatii_locator"] += cur.rowcount


def paralel(err, n, argumente, sari=()):
    """Câte un proces per bancă; jurnalul fiecăreia în loguri/banci/<slug>.log."""
    os.makedirs(LOGURI, exist_ok=True)
    with psycopg2.connect(N.dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT slug FROM banci ORDER BY slug")
            banci = [r[0] for r in cur.fetchall() if r[0] not in sari]

    def una(slug):
        cale = os.path.join(LOGURI, f"{slug}.log")
        with open(cale, "w", encoding="utf-8") as log:
            p = subprocess.run([sys.executable, "-u", os.path.abspath(__file__),
                                "--banca", slug] + argumente,
                               stdout=log, stderr=subprocess.STDOUT,
                               env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        return slug, p.returncode

    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as ex:
        for slug, cod in ex.map(una, banci):
            err.write(f"  {slug:20s} {'gata' if cod == 0 else f'EROARE (cod {cod})'}\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--banca", help="doar o bancă (slug)")
    ap.add_argument("--limita", type=int, help="oprește după N surse, pentru probe")
    ap.add_argument("--de-la-zero", action="store_true",
                    help="golește observațiile, amprentele și inventarul web; "
                         "Bronze se arhivează")
    ap.add_argument("--paralel", type=int, default=0,
                    help="rulează toate băncile, câte N în paralel")
    ap.add_argument("--fara", default="",
                    help="cu --paralel: bănci de sărit, separate prin virgulă")
    ap.add_argument("--din-bronze", action="store_true",
                    help="reextrage din Bronze, fără rețea")
    a = ap.parse_args()

    config.incarca()
    err = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", write_through=True)
    raport = collections.Counter()

    if a.de_la_zero and not a.banca:
        goleste_tot(err)
    if a.din_bronze and (a.banca or not a.paralel):
        brute = din_bronze(err, raport, a.banca)
        scrie(err, raport, brute, [a.banca] if a.banca else None)
    elif a.banca:
        ruleaza_banca(err, raport, a.banca, a.limita)
    elif a.paralel:
        paralel(err, a.paralel, ["--din-bronze"] if a.din_bronze else [],
                sari={s.strip() for s in a.fara.split(",") if s.strip()})
        return 0
    else:
        ap.error("alege --banca, --paralel N sau --din-bronze")

    err.write("\n")
    N.raporteaza(raport, sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
