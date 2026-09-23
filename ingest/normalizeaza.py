"""Normalizatorul unic: orice înregistrare brută -> un rând de `observations`.

De ce există: până acum fiecare variantă de colectare avea propriul loader, cu
propria mapare la vocabularul canonic — `load_playwright.py`, `load_bs4_depozite.py`
și era pe cale să apară un al treilea. Consecința nu e estetică: maparea
tip_rată -> produs, pragurile de plauzibilitate și construcția `cod_scenariu`
existau în trei copii, deci o schimbare trebuia făcută în trei locuri, iar orice
sursă nouă cerea un script nou. Exact așa au rămas neextrase 196 de pagini de
produs găsite de discovery-ul LLM: niciun script nu le avea în listă.

Forma corectă, și cea implementată aici:

    extractor PDF (Playwright) ─┐
    extractor HTML (BS4)       ─┼─> înregistrare brută ─> ACEST MODUL ─> observations
    extractor store (iTunes)   ─┘

Un extractor nu știe nimic despre schema bazei. Produce o înregistrare brută
(„am găsit 7,5 pe pagina asta, la serviciul ăsta, în contextul ăsta") și atât.
Modulul de aici deține toate deciziile de traducere, o singură dată:

  - slug-ul băncii (inclusiv aliasurile care pierdeau rânduri în tăcere)
  - conceptul canonic -> `camp`, plus regulile de rol (condiție / min / max)
  - tipul de valoare -> `unitate` și `valuta`
  - `cod_scenariu` (segment, categorie, canal, destinație, perioadă)
  - încrederea, din eticheta textuală a extractorului
  - versiunea: `data_vigoare` + `stare_data` se PĂSTREAZĂ, nu se filtrează la
    încărcare; filtrul e al afișării (vederea `observatii_curente`)

`PRAGURI` stă tot aici, ca pragurile de plauzibilitate să fie aceleași în
încărcare, în coada de verificare și în API. Erau trei valori scrise separat.

Scrierea (`scrie`) e idempotentă pe proveniență: șterge doar ce a scris aceeași
metodă de extracție, apoi inserează în bloc cu `execute_values`. Nu generează
text SQL — generarea de SQL prin concatenare a fost sursa unui duplicat real de
URL la prima încărcare (un `NOT EXISTS` nu vede duplicatele din propria listă
de VALUES).
"""

import collections
import datetime
import os
import sys

import psycopg2
import psycopg2.extras

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AICI))

# --------------------------------------------------------------------------
# Praguri de plauzibilitate. Un singur loc.
#
# Motivele sunt măsurate, nu presupuse:
#   comision   > 10.000 lei  -> nu e preț de retail; erau limite de retragere
#                               (Libra: retragere_numerar 0–20.000) și capitalul
#                               social al BCR (1,6 mld) extrase ca sumă
#   depozite   > 12%         -> TBI apărea cu „dobândă tipică 20%" din
#                               `LCP cu Taxa_depozit-scule`, care nu e dobândă
#   credite    > 30%         -> peste asta sunt penalități sau procente de alt fel
#   carduri    > 40%         -> dobânzile la cardul de credit ajung real la ~28%
# --------------------------------------------------------------------------
PRAGURI = {
    "suma": 10000,
    "depozite": 12,
    "credite": 30,
    "conturi_carduri": 40,
    "procent_absolut": 40,
}

# Pachetele folosesc alte slug-uri decât tabela `banci` pentru două bănci.
# Fără maparea asta rândurile lor nu găseau banca și dispăreau fără eroare
# (351 de observații pierdute la prima încărcare, prinse la reconciliere).
ALIAS_SLUG = {
    "eximbank": "exim",
    "bcrlocuinte": "bcr-locuinte",
}

# tip de rată -> produs din catalog
MAPARE_TIP_RATA = {
    "nominala": "dobanda-nominala",
    "marja_fixa": "dobanda-nominala",
    "dae": "dae",
    "marja_ircc": "marja-ircc",
    "ircc_valoare": "robor-euribor",
    "robor_valoare": "robor-euribor",
    "euribor_valoare": "robor-euribor",
    "marja_euribor": "robor-euribor",
    "marja_robor": "robor-euribor",
    "comision_procent": "comisioane",
    "cashback": "card-de-credit",
}

INCREDERE = {"ridicata": 0.9, "medie": 0.6, "scazuta": 0.3}

# metoda de extracție -> transport folosit ca să se aducă sursa
TRANSPORT = {
    "playwright": "playwright", "bs4": "http", "bs4_llm": "http",
    "llm": "http", "manual": "manual",
}
MONEDA_UNITATE = {"LEI": "lei", "RON": "lei", "EUR": "eur", "USD": "usd"}

COLOANE = (
    "id_sursa", "id_produs", "id_hash", "camp", "cod_scenariu",
    "valoare_num", "valoare_text", "unitate", "valuta", "citat", "confidence",
    "ambiguu", "metoda_extractie", "serviciu", "sectiune", "conditie",
    "frecventa", "detaliu", "pagina", "data_vigoare", "stare_data",
    "motiv_ambiguu",
)


def brut(**kw):
    """Înregistrarea brută pe care o produce un extractor.

    Toate câmpurile sunt opționale în afară de `banca` și `sursa`; un extractor
    completează doar ce a găsit efectiv pe pagină. Ce lipsește rămâne NULL în
    bază, nu se inventează.
    """
    z = {
        # de unde vine
        "banca": None, "sursa": None, "tip_sursa": "url", "format": "html",
        "rol_sursa": "produs", "frecventa_sursa": "lunar", "amprenta": None,
        # ce e valoarea
        "concept": None,        # conceptul canonic din vocabular, sau tip_rata
        "tip": None,            # comision_suma | comision_procent | gratuit | rata
        "rol": None,            # conditie | min | max  (schimbă înțelesul cifrei)
        "valoare": None, "valoare_text": None, "moneda": None,
        # la ce se aplică
        "serviciu": None, "sectiune": None, "conditie": None,
        "frecventa": None, "detaliu": None, "pagina": None,
        # scenariul
        "segment": None, "categorie": None, "canal": None,
        "destinatie": None, "perioada": None, "nr_rate": None,
        # calitate și versiune
        "citat": None, "incredere": None, "ambiguu": False, "motiv_ambiguu": None,
        "data_vigoare": None, "stare_data": None,
        # produsul din catalog; dacă lipsește, se deduce din concept/tip
        "produs": None,
    }
    z.update(kw)
    return z


def _produs(b):
    if b.get("produs"):
        return b["produs"]
    concept, tip, categorie = b.get("concept"), b.get("tip"), b.get("categorie")
    if tip == "rata" or concept in MAPARE_TIP_RATA or concept == "rate_fara_dobanda":
        if concept == "rate_fara_dobanda":
            # e o facilitate de plată în rate, nu o rată de produs; pe carduri
            # e locul ei firesc
            return "card-de-credit" if categorie == "conturi_carduri" else "dobanda-nominala"
        return MAPARE_TIP_RATA.get(concept)
    return "comisioane"


def _unitate(b):
    tip = b.get("tip")
    if tip in ("comision_procent", "rata") or b.get("concept") in MAPARE_TIP_RATA:
        return "procent"
    if tip == "gratuit":
        return "lei"
    if b.get("valoare") is None and b.get("valoare_text") is not None:
        return None                      # nume de produs: nu are unitate
    return MONEDA_UNITATE.get((b.get("moneda") or "").upper(), "altele")


def _camp(b):
    camp = b.get("concept") or "comision"
    rol = b.get("rol")
    if rol == "conditie":
        return "conditie"                # cifra e o cerință/limită, NU un preț
    if rol in ("min", "max"):
        return f"{camp}_{rol}"           # plafon al unui comision procentual
    return camp


def _scenariu(b):
    """Primul segment e categoria, fiindcă API-ul filtrează pe el.

    `split_part(cod_scenariu, '|', 1)` separă dobânda de depozit de cea de
    credit. Dacă categoria n-ar fi prima, cele două ar ajunge în aceeași
    coloană și comparația ar fi falsă.
    """
    bucati = [b.get("categorie"), b.get("segment"), b.get("canal"),
              b.get("destinatie"), b.get("perioada"), b.get("nr_rate")]
    return "|".join(str(x) for x in bucati if x) or None


def _incredere(b):
    if isinstance(b.get("incredere"), (int, float)):
        return round(float(b["incredere"]), 3)
    c = INCREDERE.get(b.get("incredere"), 0.5)
    if b.get("stare_data") == "DATA_NECUNOSCUTA":
        c = min(c, 0.7)          # extras corect, dar nu știm de când se aplică
    if b.get("stare") == "SURSA_VECHE":
        c = min(c, 0.5)          # extras corect, dar pagina băncii e învechită
    return round(c, 3)


def _data(v):
    if not v:
        return None
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v if isinstance(v, datetime.date) else v.date()
    try:
        return datetime.date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def normalizeaza(b, raport=None):
    """Înregistrare brută -> dict cu cheile din COLOANE (mai puțin id-urile).

    Întoarce None și numără motivul dacă rândul nu poate fi normalizat. Nimic
    nu se pierde în tăcere: fiecare respingere are un motiv în raport.
    """
    raport = raport if raport is not None else collections.Counter()
    if not b.get("banca") or not b.get("sursa"):
        raport["respins_fara_banca_sau_sursa"] += 1
        return None
    if b.get("valoare") is None and not b.get("valoare_text"):
        raport["respins_fara_valoare"] += 1
        return None
    produs = _produs(b)
    if not produs:
        raport[f"respins_concept_nemapat:{b.get('concept')}"] += 1
        return None

    val = None if b.get("valoare") is None else float(b["valoare"])
    unitate = _unitate(b)

    # Marcăm ambiguu ce depășește pragul de plauzibilitate, în loc să-l
    # aruncăm: rândul rămâne verificabil în coadă, dar nu intră în comparații.
    ambiguu = bool(b.get("ambiguu"))
    if val is not None:
        if unitate in ("lei", "eur", "usd") and val > PRAGURI["suma"] and _camp(b) != "conditie":
            ambiguu = True
            raport["marcat_implauzibil_suma"] += 1
        elif unitate == "procent" and val > PRAGURI["procent_absolut"]:
            ambiguu = True
            raport["marcat_implauzibil_procent"] += 1

    raport["normalizate"] += 1
    return {
        "banca": ALIAS_SLUG.get(b["banca"], b["banca"]),
        "sursa": b["sursa"],
        "tip_sursa": b.get("tip_sursa") or "url",
        "format": b.get("format") or "html",
        "rol_sursa": b.get("rol_sursa") or "produs",
        "frecventa_sursa": b.get("frecventa_sursa") or "lunar",
        "amprenta": b.get("amprenta"),
        "produs": produs,
        "camp": _camp(b),
        "cod_scenariu": _scenariu(b),
        "valoare_num": val,
        "valoare_text": (b.get("valoare_text") or None) and str(b["valoare_text"])[:300],
        "unitate": unitate,
        "valuta": ((b.get("moneda") or "")[:3] or None),
        "citat": (b.get("citat") or None) and str(b["citat"])[:500],
        "confidence": _incredere(b),
        "ambiguu": ambiguu,
        "serviciu": (b.get("serviciu") or None) and str(b["serviciu"])[:300],
        "sectiune": b.get("sectiune"),
        "conditie": b.get("conditie"),
        "frecventa": b.get("frecventa"),
        "detaliu": b.get("detaliu"),
        "pagina": b.get("pagina") if isinstance(b.get("pagina"), int) else None,
        "data_vigoare": _data(b.get("data_vigoare")),
        "stare_data": b.get("stare_data"),
        # De ce e ambiguă, nu doar CĂ e. Cele două motive reale din pachet
        # („antet de coloană pierdut", „prag de sumă pierdut") sunt pierderi de
        # structură la citirea tabelului, nu greșeli de citire a cifrei — și
        # asta schimbă complet ce faci cu valoarea.
        "motiv_ambiguu": b.get("motiv_ambiguu") or (
            "peste pragul de plauzibilitate" if ambiguu and not b.get("ambiguu") else None
        ),
    }


# --------------------------------------------------------------------------
# Scrierea în bază
# --------------------------------------------------------------------------

def dsn():
    return os.environ.get(
        "MIP_DSN", "host=localhost port=5432 dbname=mip user=mip password=mip"
    )


def curata(metoda, banci=None):
    """Șterge ce a scris anterior aceeași metodă. De apelat O DATĂ per rulare.

    Există separat de `scrie` fiindcă pașii care scriu incremental (o bancă
    odată, ca o rulare lungă să nu se piardă la o eroare pe pagina 200) ar
    șterge băncile anterioare la fiecare apel.

    `banci` restrânge ștergerea la o listă de slug-uri, pentru rulările țintite.
    Fără el, o rulare cu `--banca` avea de ales între două greșeli: să nu
    șteargă nimic, și atunci dubla datele — s-a întâmplat, 1.603 valori ING au
    devenit 3.206 — sau să șteargă tot, inclusiv băncile care nu se rescriu în
    rularea aceea.
    """
    with psycopg2.connect(dsn()) as conn:
        with conn.cursor() as cur:
            if banci:
                cur.execute(
                    """DELETE FROM observations o
                       USING surse s, banci b
                       WHERE o.id_sursa = s.id AND b.id = s.id_banca
                         AND o.metoda_extractie = %s AND b.slug = ANY(%s)""",
                    (metoda, list(banci)),
                )
            else:
                cur.execute("DELETE FROM observations WHERE metoda_extractie = %s",
                            (metoda,))
            return cur.rowcount


def noteaza_surse(note):
    """Scrie pe sursă de ce n-a produs nimic (`surse.nota_extractie`)."""
    if not note:
        return 0
    with psycopg2.connect(dsn()) as conn:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                """UPDATE surse s SET nota_extractie = v.nota, ultima_rulare = now()
                   FROM (VALUES %s) AS v(slug, sursa, nota)
                   JOIN banci b ON b.slug = v.slug
                   WHERE s.id_banca = b.id AND s.sursa = v.sursa""",
                note,
            )
            return cur.rowcount


def scrie(randuri, metoda, raport=None, sterge=True):
    """Scrie rândurile normalizate, idempotent pe `metoda`.

    Pașii, în ordinea impusă de chei străine:
      1. surse noi (ON CONFLICT DO NOTHING — o sursă găsită de discovery se
         refolosește, nu se dublează)
      2. amprente pentru sursele-document
      3. ștergerea observațiilor scrise anterior de ACEEAȘI metodă
      4. inserarea în bloc

    Pasul 3 e restrâns la metodă anume: altfel o reîncărcare a unei variante ar
    șterge datele altei variante.
    """
    raport = raport if raport is not None else collections.Counter()
    if not randuri:
        raport["nimic_de_scris"] += 1
        return raport

    with psycopg2.connect(dsn()) as conn:
        with conn.cursor() as cur:
            # Extractoarele identifică banca diferit: pachetul Playwright dă
            # slug-ul (`raiffeisen`), scraperul propriu dă numele complet
            # („Raiffeisen Bank"). Amândouă sunt corecte pentru extractorul
            # lor; traducerea e treaba normalizatorului. Fără asta, 511
            # observații se pierdeau — prinse la reconciliere, fiindcă
            # respingerile se numără pe motiv, nu se ignoră.
            cur.execute("SELECT slug, nume, id FROM banci")
            banci, spre_slug = {}, {}
            for slug, nume, bid in cur.fetchall():
                banci[slug] = bid
                spre_slug[slug] = slug
                spre_slug[nume] = slug
            # Se canonizează O SINGURĂ dată, aici: mai jos totul lucrează pe
            # slug, inclusiv cheia de căutare a sursei. Dacă s-ar accepta și
            # numele ca cheie, căutarea sursei (care vine din baza de date cu
            # slug) n-ar mai potrivi și observațiile ar dispărea.
            for r in randuri:
                r["banca"] = spre_slug.get(r["banca"], r["banca"])
            cur.execute("SELECT nume, id FROM produse")
            produse = dict(cur.fetchall())

            # --- 1. surse
            surse = {}
            for r in randuri:
                if r["banca"] not in banci:
                    raport[f"sursa_sarita_banca_necunoscuta:{r['banca']}"] += 1
                    continue
                surse[(r["banca"], r["sursa"], r["tip_sursa"])] = r
            # `surse.metoda` e TRANSPORTUL (cum s-a adus pagina), nu unealta de
            # parsare. `surse.metoda_extractie` e unealta. Confundate, o sursă
            # adusă prin HTTP simplu și parsată cu BS4 ar pretinde că a avut
            # nevoie de browser — și ar pica pe CHECK-ul tabelei.
            transport = TRANSPORT.get(metoda, "http")
            noi = [
                (banci[b], t, s, r["rol_sursa"], r["format"], transport, metoda,
                 r["frecventa_sursa"], "activ")
                for (b, s, t), r in sorted(surse.items())
            ]
            if noi:
                psycopg2.extras.execute_values(
                    cur,
                    """INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format,
                                          metoda, metoda_extractie, frecventa, status)
                       VALUES %s ON CONFLICT DO NOTHING""",
                    noi,
                )
                # `+=`, nu `=`: pașii care scriu incremental (o bancă odată)
                # apelează `scrie` de mai multe ori, iar atribuirea ar lăsa în
                # raport doar cifrele ultimei bănci. Am raportat „35 inserate"
                # când în bază intraseră 141.
                raport["surse_propuse"] += len(noi)
                raport["surse_inserate"] += cur.rowcount

            # marcăm sursele ca extrase, ca o rulare următoare să fie incrementală
            cur.execute(
                """UPDATE surse s SET metoda_extractie = %s, ultima_rulare = now()
                   FROM banci b
                   WHERE b.id = s.id_banca AND s.metoda_extractie IS NULL
                     AND (b.slug, s.sursa) IN %s""",
                (metoda, tuple((b, s) for (b, s, _t) in surse) or (("", ""),)),
            )
            raport["surse_marcate_extrase"] += cur.rowcount

            cur.execute(
                """SELECT b.slug, s.sursa, s.tip_sursa, s.id
                   FROM surse s JOIN banci b ON b.id = s.id_banca"""
            )
            id_sursa = {(b, s, t): i for b, s, t, i in cur.fetchall()}

            # --- 2. amprente (doar documente)
            amprente = {
                (r["banca"], r["sursa"], r["tip_sursa"]): r["amprenta"]
                for r in randuri if r.get("amprenta")
            }
            if amprente:
                cur.execute(
                    "DELETE FROM hashes WHERE id_sursa IN "
                    "(SELECT id FROM surse WHERE metoda_extractie = %s)", (metoda,)
                )
                psycopg2.extras.execute_values(
                    cur, "INSERT INTO hashes (id_sursa, format, hash) VALUES %s",
                    [(id_sursa[k], "pdf", v) for k, v in sorted(amprente.items())
                     if k in id_sursa],
                )
                raport["amprente"] += len(amprente)
            cur.execute(
                """SELECT h.id_sursa, max(h.id) FROM hashes h
                   GROUP BY h.id_sursa"""
            )
            id_hash = dict(cur.fetchall())

            # --- 3. idempotență pe proveniență (sărită la scriere incrementală)
            if sterge:
                cur.execute("DELETE FROM observations WHERE metoda_extractie = %s",
                            (metoda,))
                raport["observatii_sterse"] += cur.rowcount

            # --- 4. observații
            valori = []
            for r in randuri:
                k = (r["banca"], r["sursa"], r["tip_sursa"])
                if k not in id_sursa:
                    raport["obs_sarita_fara_sursa"] += 1
                    continue
                if r["produs"] not in produse:
                    raport[f"obs_sarita_produs_necunoscut:{r['produs']}"] += 1
                    continue
                s_id = id_sursa[k]
                valori.append((
                    s_id, produse[r["produs"]], id_hash.get(s_id),
                    r["camp"], r["cod_scenariu"], r["valoare_num"], r["valoare_text"],
                    r["unitate"], r["valuta"], r["citat"], r["confidence"],
                    r["ambiguu"], metoda, r["serviciu"], r["sectiune"], r["conditie"],
                    r["frecventa"], r["detaliu"], r["pagina"],
                    r["data_vigoare"], r["stare_data"], r["motiv_ambiguu"],
                ))
            if valori:
                psycopg2.extras.execute_values(
                    cur,
                    f"INSERT INTO observations ({', '.join(COLOANE)}) VALUES %s",
                    valori, page_size=1000,
                )
            raport["observatii_inserate"] += len(valori)
    return raport


def raporteaza(raport, unde=None):
    unde = unde or sys.stderr
    if hasattr(unde, "buffer"):
        import io as _io
        unde = _io.TextIOWrapper(unde.buffer, encoding="utf-8", write_through=True)
    unde.write("=== RAPORT ===\n")
    for k in sorted(raport):
        unde.write(f"{raport[k]:8d}  {k}\n")
    unde.flush()
