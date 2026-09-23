"""Vizualizator read-only peste baza MIP.

Pornire:  python app/server.py        (apoi http://localhost:8765)

Doar citire: nu exista nicio ruta care scrie in baza. Interogarile folosesc
parametri (%s), nu interpolare de text, ca filtrele din interfata sa nu poata
deveni injectie SQL.
"""

import http.server
import json
import os
import socket
import socketserver
import urllib.parse

import sys

import psycopg2
import psycopg2.extras

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AICI))
sys.path.insert(0, os.path.join(os.path.dirname(AICI), "ingest"))
import config  # noqa: E402  (dupa sys.path, ca sa gaseasca radacina proiectului)

# Pragurile de plauzibilitate vin din normalizator, nu sunt rescrise aici.
# Erau in trei locuri (incarcare, coada de verificare, API) si o schimbare
# trebuia facuta in toate trei. Un singur loc, o singura valoare.
from normalizeaza import PRAGURI  # noqa: E402

# Comparatiile citesc din vederea `observatii_curente`, nu din tabela bruta.
# Vederea tine regula o singura data (`stare_data NOT IN (ISTORIC, DUBLURA)`) -
# altfel tarifele BCR din martie ar intra peste cele din decembrie in aceeasi
# celula. Versiunile istorice rman in tabela si se vad in pagina de Istoric.

# Etichete umane pentru proveniente. Trei variante de colectare, fiecare cu
# acoperire diferita - de-aia se arata separat, nu insumate.
PROVENIENTA = {
    "playwright": "Playwright (PDF-uri + HTML)",
    "bs4": "BS4 propriu (depozite)",
    "bs4_llm": "BS4 peste surse găsite de LLM",
    "llm": "discovery LLM",
    "manual": "introdus manual",
}

config.incarca()
DSN = os.environ.get(
    "MIP_DSN", "host=localhost port=5432 dbname=mip user=mip password=mip"
)
PORT = int(os.environ.get("MIP_PORT", "8765"))


def interoghează(sql, params=None):
    with psycopg2.connect(DSN) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            return [dict(r) for r in cur.fetchall()]


def sumar():
    return {
        "totaluri": interoghează(
            """
            SELECT 'bănci' AS ce, count(*)::int AS n FROM banci
            UNION ALL SELECT 'surse', count(*)::int FROM surse
            UNION ALL SELECT 'observații', count(*)::int FROM observations
            UNION ALL SELECT 'legături sursă-produs', count(*)::int FROM surse_produse
            UNION ALL SELECT 'amprente documente', count(*)::int FROM hashes
            UNION ALL SELECT 'evenimente schimbare', count(*)::int FROM change_events
            UNION ALL SELECT 'versiuni aplicații', count(*)::int FROM app_release
            UNION ALL SELECT 'review-uri aplicații', count(*)::int FROM app_review
            UNION ALL SELECT 'valori indici BNR', count(*)::int FROM indici_referinta
            """
        ),
        "surse_status": interoghează(
            "SELECT status, count(*)::int AS n FROM surse GROUP BY 1 ORDER BY 2 DESC"
        ),
        "surse_provenienta": interoghează(
            """SELECT tip_sursa, coalesce(metoda_extractie, 'descoperit (LLM), neextras') AS provenienta,
                      count(*)::int AS n
               FROM surse GROUP BY 1,2 ORDER BY 3 DESC"""
        ),
        "obs_produs": interoghează(
            """SELECT p.nume AS produs, count(*)::int AS n
               FROM observatii_curente o JOIN produse p ON p.id = o.id_produs
               GROUP BY 1 ORDER BY 2 DESC"""
        ),
        "obs_unitate": interoghează(
            "SELECT coalesce(unitate,'—') AS unitate, count(*)::int AS n FROM observations GROUP BY 1 ORDER BY 2 DESC"
        ),
    }


def banci():
    return interoghează(
        """
        SELECT b.slug, b.nume, b.tier,
               count(DISTINCT s.id)::int AS surse,
               count(o.id)::int          AS observatii,
               count(DISTINCT ar.id)::int AS versiuni_app
        FROM banci b
        LEFT JOIN surse s        ON s.id_banca = b.id
        LEFT JOIN observations o ON o.id_sursa = s.id
        LEFT JOIN app_release ar ON ar.id_banca = b.id
        GROUP BY b.id, b.slug, b.nume, b.tier
        ORDER BY observatii DESC, b.slug
        """
    )


def observatii(q):
    where, params = ["TRUE"], []
    if q.get("banca"):
        where.append("b.slug = %s")
        params.append(q["banca"][0])
    if q.get("produs"):
        where.append("p.nume = %s")
        params.append(q["produs"][0])
    if q.get("q"):
        where.append("(o.camp ILIKE %s OR o.citat ILIKE %s OR o.cod_scenariu ILIKE %s)")
        t = "%" + q["q"][0] + "%"
        params += [t, t, t]
    if q.get("doar_ambigue") and q["doar_ambigue"][0] == "1":
        where.append("o.ambiguu")
    limit = min(int((q.get("limit") or ["100"])[0]), 500)
    offset = int((q.get("offset") or ["0"])[0])

    sql_base = f"""
        FROM observatii_curente o
        JOIN surse s   ON s.id = o.id_sursa
        JOIN banci b   ON b.id = s.id_banca
        JOIN produse p ON p.id = o.id_produs
        WHERE {' AND '.join(where)}
    """
    total = interoghează("SELECT count(*)::int AS n " + sql_base, params)[0]["n"]
    randuri = interoghează(
        """SELECT b.slug AS banca, p.nume AS produs, o.camp, o.cod_scenariu,
                  o.valoare_num, o.unitate, o.valuta, o.confidence, o.ambiguu,
                  o.metoda_extractie, o.citat, s.sursa, s.tip_sursa
        """
        + sql_base
        + " ORDER BY o.valoare_num DESC NULLS LAST LIMIT %s OFFSET %s",
        params + [limit, offset],
    )
    return {"total": total, "limit": limit, "offset": offset, "randuri": randuri}


def surse(q):
    """Inventarul de surse: de unde vin datele si ce nu s-a extras inca.

    Scopul paginii e guvernanta, nu navigare. Raspunde la doua intrebari pe
    care nicio alta pagina nu le pune: „de unde vine cifra asta" si „ce a
    gasit discovery-ul si nimeni nu a extras". A doua a fost gaura cea mai
    mare din proiect - 196 de pagini de produs descoperite si niciodata rulate.
    """
    where, params = ["TRUE"], []
    if q.get("banca"):
        where.append("b.slug = %s")
        params.append(q["banca"][0])
    if q.get("status"):
        where.append("s.status = %s")
        params.append(q["status"][0])
    if q.get("rol"):
        where.append("s.rol = %s")
        params.append(q["rol"][0])
    # Trei stari, nu doua. „Neextras" si „incercat, dar blocat de WAF" arata
    # identic in baza daca ne uitam doar la `metoda_extractie` (care rmane NULL
    # la eșec), dar cer acțiuni complet diferite: prima cere o rulare, a doua
    # cere alt transport (browser real). `nota_extractie` le separa.
    stare = (q.get("stare") or [""])[0]
    ARE_DATE = "EXISTS (SELECT 1 FROM observations o WHERE o.id_sursa = s.id)"
    if stare == "neatinse":
        where.append(f"NOT {ARE_DATE} AND s.nota_extractie IS NULL "
                     "AND s.metoda_extractie IS NULL")
    elif stare == "incercate":
        where.append(f"NOT {ARE_DATE} AND s.nota_extractie IS NOT NULL")
    elif stare == "cu_date":
        where.append(ARE_DATE)
    limit = min(int((q.get("limit") or ["100"])[0]), 500)
    offset = int((q.get("offset") or ["0"])[0])
    sql_base = f"FROM surse s JOIN banci b ON b.id = s.id_banca WHERE {' AND '.join(where)}"
    total = interoghează("SELECT count(*)::int AS n " + sql_base, params)[0]["n"]
    randuri = interoghează(
        """SELECT b.slug AS banca, b.nume AS banca_nume, s.sursa, s.tip_sursa,
                  s.format, s.metoda, s.rol, s.frecventa, s.status,
                  s.metoda_extractie, s.nota_extractie, s.url_public,
                  s.ultima_rulare,
                  (SELECT count(*)::int FROM observatii_curente o WHERE o.id_sursa = s.id) AS observatii
        """
        + sql_base
        + " ORDER BY observatii DESC, b.slug LIMIT %s OFFSET %s",
        params + [limit, offset],
    )
    return {
        "total": total, "limit": limit, "offset": offset, "randuri": randuri,
        "banci": interoghează(
            """SELECT b.slug, b.nume, count(*)::int AS surse,
                      count(*) FILTER (WHERE s.metoda_extractie IS NULL)::int AS neextrase
               FROM surse s JOIN banci b ON b.id = s.id_banca
               GROUP BY 1, 2 ORDER BY 3 DESC"""
        ),
        # Bilanțul care contează: din ce s-a descoperit, cât a produs date.
        "bilant": interoghează(
            """WITH x AS (
                 SELECT s.id, s.nota_extractie, s.metoda_extractie,
                        EXISTS (SELECT 1 FROM observations o WHERE o.id_sursa = s.id) AS are_date
                 FROM surse s
               )
               SELECT count(*)::int AS total,
                      count(*) FILTER (WHERE are_date)::int AS cu_date,
                      count(*) FILTER (WHERE NOT are_date
                        AND nota_extractie IS NOT NULL)::int AS incercate,
                      count(*) FILTER (WHERE NOT are_date AND nota_extractie IS NULL
                        AND metoda_extractie IS NULL)::int AS neatinse
               FROM x"""
        )[0],
        "motive": interoghează(
            """SELECT split_part(nota_extractie, ':', 1) AS motiv, count(*)::int AS n
               FROM surse WHERE nota_extractie IS NOT NULL
               GROUP BY 1 ORDER BY 2 DESC"""
        ),
    }


def mobil():
    return {
        "versiuni": interoghează(
            """SELECT b.slug AS banca, ar.platforma, ar.app_id, ar.versiune,
                      ar.note_lansare, ar.rating_agregat, ar.volum_rating
               FROM app_release ar JOIN banci b ON b.id = ar.id_banca
               ORDER BY ar.volum_rating DESC NULLS LAST"""
        ),
        "review_sumar": interoghează(
            """SELECT b.slug AS banca, v.storefront, count(*)::int AS review_uri,
                      round(avg(v.rating), 2) AS rating_mediu_text,
                      max(ar.rating_agregat)  AS rating_agregat_store
               FROM app_review v
               JOIN banci b ON b.id = v.id_banca
               LEFT JOIN app_release ar ON ar.id_banca = b.id AND ar.platforma = v.platforma
               GROUP BY 1,2 ORDER BY 1,2"""
        ),
        "review_recente": interoghează(
            """SELECT b.slug AS banca, v.storefront, v.rating, v.versiune,
                      left(v.text, 240) AS text, left(v.autor_hash, 12) AS autor,
                      v.postat_la
               FROM app_review v JOIN banci b ON b.id = v.id_banca
               ORDER BY v.postat_la DESC NULLS LAST LIMIT 40"""
        ),
        "screenshoturi": interoghează(
            """SELECT b.slug AS banca, sh.url
               FROM app_screenshot sh JOIN banci b ON b.id = sh.id_banca
               ORDER BY b.slug, sh.id"""
        ),
    }


def indici():
    return interoghează(
        """SELECT indice, scadenta, valoare, valabil_din
           FROM indici_referinta ORDER BY valabil_din DESC, indice, scadenta"""
    )


def locatii(q):
    where, params = ["TRUE"], []
    if q.get("banca"):
        where.append("b.slug = ANY(%s)")
        params.append(q["banca"])          # accepta ?banca=bcr&banca=ing
    if q.get("tip"):
        where.append("l.tip = %s")
        params.append(q["tip"][0])
    base = f"FROM locatii l JOIN banci b ON b.id = l.id_banca WHERE {' AND '.join(where)}"
    return {
        "banci": interoghează(
            """SELECT b.slug, b.nume,
                      count(*) FILTER (WHERE l.tip = 'sucursala')::int AS sucursale,
                      count(*) FILTER (WHERE l.tip = 'atm')::int       AS atm,
                      count(*)::int AS total
               FROM locatii l JOIN banci b ON b.id = l.id_banca
               GROUP BY b.slug, b.nume ORDER BY total DESC"""
        ),
        "total": interoghează("SELECT count(*)::int AS n " + base, params)[0]["n"],
        "puncte": interoghează(
            "SELECT l.id, b.slug AS banca, b.nume AS banca_nume, l.tip, l.nume, "
            "l.adresa, l.sector, l.lat::float8, l.lon::float8, l.program, l.sursa, "
            "l.rating::float8, l.nr_recenzii, l.furnizori "
            + base + " ORDER BY b.slug, l.tip",
            params,
        ),
    }


# ---------------------------------------------------------------------------
# Grupurile de comparatie. `camp` vine din vocabularul canonic al pachetului
# Playwright (vocabular.py), deci sunt aceleasi etichete la toate bancile -
# de-aia comparatia are sens. Numarul de banci per camp e verificat in date,
# nu presupus.
# ---------------------------------------------------------------------------
GRUPURI = {
    "cont_curent": {
        "titlu": "Cont curent",
        "campuri": ["administrare_cont", "deschidere_cont", "extras_de_cont",
                    "interogare_sold", "inchidere_cont"],
        "sens": "mic_bun",          # comision: mai mic = mai bun
    },
    "carduri": {
        "titlu": "Carduri",
        "campuri": ["emitere_card", "reemitere_card", "administrare_card",
                    "retragere_numerar", "interogare_sold"],
        "sens": "mic_bun",
    },
    "transferuri": {
        "titlu": "Transferuri și plăți",
        "campuri": ["transfer_credit", "incasare", "modificare_anulare",
                    "transfer_debit", "documentar"],
        "sens": "mic_bun",
    },
}

# Dobanzile se compara pe alt criteriu: la depozite mai MARE e mai bun, la
# credite mai MIC. Le tratam separat, nu le amestecam in aceeasi matrice.
GRUPURI_RATE = {
    "depozite":        {"titlu": "Dobânzi la depozite", "campuri": ["nominala"],
                        "sens": "mare_bun", "prag": PRAGURI["depozite"]},
    "credite":         {"titlu": "Dobânzi la credite",
                        "campuri": ["nominala", "dae", "marja_ircc"],
                        "sens": "mic_bun", "prag": PRAGURI["credite"]},
    "conturi_carduri": {"titlu": "Conturi și carduri",
                        "campuri": ["nominala", "comision_procent"],
                        "sens": "mic_bun", "prag": PRAGURI["conturi_carduri"]},
}
# Pragul de plauzibilitate e pe categorie, nu global. Motivul e masurat: cu
# prag unic de 40%, TBI aparea cu „dobanda tipica la depozit 20%", dintr-o
# valoare cu serviciul `LCP cu Taxa_depozit-scule` - nu e o dobanda. La 12%
# (peste maximul real al pietei la depozite retail) dispare, fara sa taie
# nicio oferta adevarata. Cate se exclud se raporteaza in interfata; toate
# rman in coada de verificare.


def matrice(q):
    """Matrice banca x serviciu, cu interval min-max si numar de valori.

    Exclude valorile `ambiguu` (real, dar neatribuibile) si raporteaza cate a
    exclus - altfel un interval ar parea mai larg decat e, din valori despre
    care stim ca nu se pot atribui.

    O singura moneda per matrice: amestecarea lei cu euro in aceeasi celula ar
    produce intervale fara sens.
    """
    grup = (q.get("grup") or ["cont_curent"])[0]
    if grup not in GRUPURI:
        return {"eroare": f"grup necunoscut: {grup}"}
    unitate = (q.get("unitate") or ["lei"])[0]
    # Segmentul conteaza: pretul pentru persoana fizica si cel pentru firma
    # sunt in acelasi tabel. Comparate intre ele, dau o concluzie falsa.
    segment = (q.get("segment") or ["pf"])[0]
    campuri = GRUPURI[grup]["campuri"]

    # Rndurile FARA segment marcat in sursa se includ, nu se arunca.
    #
    # Motivul e masurat: BRD are 13 valori pentru `administrare_cont`, dintre
    # care 0 marcate `pf` si 12 fara nicio marcare. Exim, la fel: 7 valori, 0
    # marcate. Filtrul strict le arunca in silenta, iar in Versus coloana BRD
    # aparea goala - ceea ce se citea ca „nu s-a putut extrage", cand de fapt
    # extractia reusise si filtrul le ascundea.
    #
    # Nu se pretinde ca sunt PF: interfata le marcheaza „segment nemarcat in
    # sursa", iar `segment_necunoscut` spune per celula daca reprezentativa
    # vine dintr-un rnd nemarcat.
    COND_SEG = ("%s = ANY(string_to_array(coalesce(o.cod_scenariu, ''), '|')) "
                "OR NOT (coalesce(o.cod_scenariu, '') ~ '(^|\\|)(pf|pj|pfa|imm)(\\||$)')")
    filtru_seg = "" if segment == "toate" else f" AND ({COND_SEG})"
    p_seg = () if segment == "toate" else (segment,)

    # Prag de plauzibilitate, acelasi ca in coada de verificare: un comision de
    # retail peste 10.000 lei nu exista. Valorile mari sunt limite de retragere
    # sau praguri de eligibilitate extrase gresit ca pret (caz real: Libra,
    # retragere_numerar 0-20.000). Fara pragul asta, intervalul celulei devine
    # inutilizabil, iar comparatia induce in eroare.
    PLAUZIBIL = PRAGURI["suma"]

    # Valoarea reprezentativa + CE reprezinta. Intervalul singur („0-25") nu
    # spunea nici la ce se refera, nici care cifra conteaza.
    #
    # Reprezentativa e MEDIANA, nu minimul. Masurat: la minim, 80% din celulele
    # de cont curent ar arata „0 lei", fiindca fiecare banca are cel putin o
    # varianta gratuita (pachet promotional, cont pentru studenti, primul an).
    # O matrice de zerouri nu compara nimic. Mediana e cat costa de obicei si
    # nu se muta dupa o singura oferta promotionala.
    #
    # Se ia RANDUL de la mediana, nu valoarea calculata separat, ca `serviciu`
    # si `frecventa` afisate sa fie chiar ale cifrei afisate - altfel eticheta
    # ar explica alt pret decat cel de pe ecran.
    celule = interoghează(
        f"""WITH randuri AS (
              SELECT b.slug AS banca, o.camp, o.valoare_num, o.unitate, o.serviciu,
                     o.frecventa, o.conditie, o.pagina, s.url_public, s.sursa, s.tip_sursa,
                     NOT (coalesce(o.cod_scenariu, '') ~ '(^|\\|)(pf|pj|pfa|imm)(\\||$)')
                       AS seg_nemarcat
              FROM observatii_curente o
              JOIN surse s ON s.id = o.id_sursa
              JOIN banci b ON b.id = s.id_banca
              WHERE o.camp = ANY(%s) AND o.unitate = %s AND NOT o.ambiguu
                AND o.valoare_num IS NOT NULL AND o.valoare_num <= {PLAUZIBIL}{filtru_seg}
            ), agregat AS (
              SELECT banca, camp, count(*)::int AS n,
                     min(valoare_num)::float8 AS minim, max(valoare_num)::float8 AS maxim,
                     count(DISTINCT serviciu)::int AS servicii,
                     count(*) FILTER (WHERE valoare_num = 0)::int AS gratuite,
                     count(*) FILTER (WHERE seg_nemarcat)::int AS nemarcate
              FROM randuri GROUP BY 1, 2
            ), numerotat AS (
              SELECT *, row_number() OVER (PARTITION BY banca, camp
                                           ORDER BY valoare_num, serviciu) AS rn,
                        count(*)     OVER (PARTITION BY banca, camp) AS tot
              FROM randuri
            ), reprezentativ AS (
              SELECT DISTINCT ON (banca, camp) banca, camp,
                     valoare_num::float8 AS valoare, unitate, serviciu, frecventa,
                     conditie, pagina, url_public, sursa, tip_sursa, seg_nemarcat
              FROM numerotat
              ORDER BY banca, camp, abs(rn - (tot + 1) / 2.0), rn
            )
            SELECT a.banca, a.camp, a.n, a.minim, a.maxim, a.servicii, a.gratuite,
                   a.nemarcate, r.valoare, r.unitate, r.serviciu, r.frecventa,
                   r.conditie, r.pagina, r.url_public, r.sursa, r.tip_sursa,
                   r.seg_nemarcat AS segment_necunoscut
            FROM agregat a JOIN reprezentativ r USING (banca, camp)""",
        (campuri, unitate) + p_seg,
    )
    excluse = interoghează(
        f"""SELECT count(*)::int AS n FROM observatii_curente o
            WHERE o.camp = ANY(%s) AND o.unitate = %s AND o.ambiguu{filtru_seg}""",
        (campuri, unitate) + p_seg,
    )[0]["n"]
    implauzibile = interoghează(
        f"""SELECT count(*)::int AS n FROM observatii_curente o
            WHERE o.camp = ANY(%s) AND o.unitate = %s AND NOT o.ambiguu
              AND o.valoare_num > {PLAUZIBIL}{filtru_seg}""",
        (campuri, unitate) + p_seg,
    )[0]["n"]

    banci_ord = interoghează(
        f"""SELECT b.slug, b.nume, count(*)::int AS n
            FROM observatii_curente o JOIN surse s ON s.id = o.id_sursa
            JOIN banci b ON b.id = s.id_banca
            WHERE o.camp = ANY(%s) AND o.unitate = %s AND NOT o.ambiguu
              AND o.valoare_num <= {PLAUZIBIL}{filtru_seg}
            GROUP BY 1, 2 ORDER BY n DESC""",
        (campuri, unitate) + p_seg,
    )
    segmente = interoghează(
        """SELECT seg, count(*)::int AS n FROM (
             SELECT unnest(string_to_array(coalesce(o.cod_scenariu, ''), '|')) AS seg
             FROM observatii_curente o WHERE o.camp = ANY(%s) AND o.unitate = %s
           ) x WHERE seg IN ('pf', 'pj', 'imm', 'pfa') GROUP BY 1 ORDER BY 2 DESC""",
        (campuri, unitate),
    )
    return {
        "grup": grup, "titlu": GRUPURI[grup]["titlu"], "sens": GRUPURI[grup]["sens"],
        "unitate": unitate, "segment": segment, "segmente": segmente,
        "campuri": campuri, "banci": banci_ord,
        "celule": celule, "excluse_ambigue": excluse,
        "excluse_implauzibile": implauzibile, "prag_plauzibil": PLAUZIBIL,
    }


def celula(q):
    """Toate valorile din spatele unei celule, cu ce reprezinta si de unde vin.

    Fara asta, un numar intr-o matrice de comparatie e o afirmatie
    neverificabila. Include si valorile ambigue, marcate ca atare.

    `serviciu` e numele dat de banca („Administrarea contului (EURO)"), nu
    conceptul canonic. E diferenta intre „7,5 lei" si „7,5 lei pe luna pentru
    administrarea contului in euro, pachet Standard". Ordonarea e pe serviciu,
    ca sa se poata grupa in interfata: acelasi serviciu cu mai multe preturi
    (praguri, pachete) e informatia care lipsea cel mai mult.

    `url_public` exista doar la sursele web si la cele 9 PDF-uri legate exact.
    Unde lipseste, `sursa` + `pagina` rman verificabile manual - un link greșit
    ar fi mai rau decat niciun link.
    """
    if not (q.get("banca") and q.get("camp")):
        return {"eroare": "lipsește banca sau camp"}
    # `camp` singur nu e destul la dobanzi: `nominala` inseamna si dobanda de
    # depozit si dobanda de credit. Fara filtrul pe categorie, sertarul deschis
    # dintr-o celula de depozit arata si dobanzi de credit - exact amestecul pe
    # care matricea il evita. Categoria e primul segment din cod_scenariu.
    categorie = (q.get("scenariu") or [""])[0]
    rows = interoghează(
        """SELECT o.valoare_num::float8 AS valoare, o.valoare_text, o.unitate,
                  o.valuta, o.cod_scenariu, o.citat, o.confidence::float8,
                  o.ambiguu, o.motiv_ambiguu, o.metoda_extractie,
                  o.serviciu, o.sectiune, o.conditie, o.frecventa, o.detaliu,
                  o.pagina, o.nr_aparitii, s.sursa, s.tip_sursa, s.url_public,
                  s.format, b.pagina_documente, b.pagina_documente_motiv
           FROM observatii_curente o
           JOIN surse s ON s.id = o.id_sursa
           JOIN banci b ON b.id = s.id_banca
           WHERE b.slug = %s AND o.camp = %s
             AND (%s = '' OR o.unitate = %s)
             AND (%s = '' OR split_part(coalesce(o.cod_scenariu, ''), '|', 1) = %s)
           ORDER BY o.ambiguu, coalesce(o.serviciu, ''), o.valoare_num""",
        (q["banca"][0], q["camp"][0],
         (q.get("unitate") or [""])[0], (q.get("unitate") or [""])[0],
         categorie, categorie),
    )
    # Trei nivele de dovada, in ordinea puterii. Interfata le arata diferit,
    # fiindca nu sunt acelasi lucru si nu trebuie sa para:
    #
    #   link          = documentul exact, sau pagina web de unde s-a citit.
    #                   Duce la cifra insasi.
    #   link_pagina   = pagina de pe care BANCA publica documentul. Afirmatia
    #                   „se publica aici" e verificabila si adevarata, dar nu e
    #                   documentul. Acopera 48 din cele 59 de documente care nu
    #                   au URL propriu.
    #   niciunul      = rmane numele fisierului si pagina din PDF, verificabile
    #                   manual. Se intampla la bancile pentru care nu s-a gasit
    #                   nicio pagina de publicare potrivita.
    #
    # De ce nu toate au `link`: pachetul sursa reține calea locala a PDF-ului,
    # nu URL-ul de descarcare, si nu include PDF-urile. Din 40 de URL-uri de
    # PDF descoperite, 9 s-au potrivit exact. Masurat: nu exista mai mult de
    # potrivit, iar un link greșit ar trimite la alt document decat cifra.
    for r in rows:
        r["link"] = r["url_public"] or (
            r["sursa"] if r["tip_sursa"] == "url" and str(r["sursa"]).startswith("http")
            else None
        )
        r["link_pagina"] = None if r["link"] else r["pagina_documente"]
        r["fisier"] = os.path.basename(str(r["sursa"])) if r["tip_sursa"] == "document" else None
        r["ancora"] = ancora(r)
    return rows


def ancora(r):
    """Fragmentul care duce la LOCUL exact al cifrei, nu doar la document.

    Datele exista: 100% din observatiile din PDF au `pagina`, 98% au `citat`,
    iar 99% din cele din HTML au `citat`. Deci se poate construi, nu ghici.

      PDF   #page=N&search=<citat>   - vizualizatorul sare la pagina si
                                       evidentiaza textul (PDF.js, Chrome, Edge)
      HTML  #:~:text=<citat>         - Text Fragments: browserul sare la fraza
                                       si o evidentiaza (Chrome, Edge)

    Citatul se scurteaza la o secventa scurta si se taie la ultimul spatiu:
    fragmentele de text cer potrivire EXACTA, iar un citat lung are mai multe
    sanse sa difere de pagina prin spatii sau diacritice. O ancora care nu
    potriveste e inofensiva - browserul deschide pur si simplu documentul.
    """
    citat = (r.get("citat") or "").strip()
    scurt = citat[:60].rsplit(" ", 1)[0] if len(citat) > 60 else citat
    if r["tip_sursa"] == "document":
        if not r.get("pagina"):
            return ""
        a = f"#page={int(r['pagina'])}"
        return a + ("&search=" + urllib.parse.quote(scurt) if scurt else "")
    if scurt and len(scurt) > 8:
        return "#:~:text=" + urllib.parse.quote(scurt, safe="")
    return ""


def rate(q):
    """Dobanzi pe categorie (depozite / credite / conturi), din cod_scenariu.

    Categoria e primul segment din cod_scenariu, pus la incarcare. Asa se
    separa dobanda de depozit de cea de credit - altfel ar ajunge in aceeasi
    coloana, iar comparatia ar fi falsa.
    """
    categorie = (q.get("categorie") or ["depozite"])[0]
    if categorie not in GRUPURI_RATE:
        return {"eroare": f"categorie necunoscută: {categorie}"}
    campuri = GRUPURI_RATE[categorie]["campuri"]
    prag = GRUPURI_RATE[categorie]["prag"]
    return {
        "categorie": categorie,
        "titlu": GRUPURI_RATE[categorie]["titlu"],
        "sens": GRUPURI_RATE[categorie]["sens"],
        "campuri": campuri,
        "prag": prag,
        "celule": interoghează(
            f"""WITH randuri AS (
                  SELECT b.slug AS banca, o.camp, o.valoare_num, o.serviciu,
                         o.frecventa, o.conditie
                  FROM observatii_curente o
                  JOIN surse s ON s.id = o.id_sursa
                  JOIN banci b ON b.id = s.id_banca
                  WHERE o.unitate = 'procent' AND o.camp = ANY(%s)
                    AND split_part(o.cod_scenariu, '|', 1) = %s
                    AND NOT o.ambiguu AND o.valoare_num IS NOT NULL
                    AND o.valoare_num <= {prag}
                ), agregat AS (
                  SELECT banca, camp, count(*)::int AS n,
                         min(valoare_num)::float8 AS minim,
                         max(valoare_num)::float8 AS maxim,
                         count(*) FILTER (WHERE valoare_num = 0)::int AS gratuite
                  FROM randuri GROUP BY 1, 2
                ), numerotat AS (
                  SELECT *, row_number() OVER (PARTITION BY banca, camp
                                               ORDER BY valoare_num, serviciu) AS rn,
                            count(*)     OVER (PARTITION BY banca, camp) AS tot
                  FROM randuri
                ), reprezentativ AS (
                  -- mediana, ca la comisioane: o singura dobanda promotionala
                  -- nu trebuie sa reprezinte toata oferta de depozite a bancii
                  SELECT DISTINCT ON (banca, camp) banca, camp,
                         valoare_num::float8 AS valoare, serviciu, frecventa, conditie
                  FROM numerotat
                  ORDER BY banca, camp, abs(rn - (tot + 1) / 2.0), rn
                )
                SELECT a.banca, a.camp, a.n, a.minim, a.maxim, a.gratuite,
                       r.valoare, r.serviciu, r.frecventa, r.conditie
                FROM agregat a JOIN reprezentativ r USING (banca, camp)
                ORDER BY 1""",
            (campuri, categorie),
        ),
        # peste prag nu e dobanda de retail in categoria asta; sunt procente de
        # alt fel (reduceri, praguri de venit, cote de garantare, taxe) extrase
        # gresit ca dobanda. Vezi coada de verificare.
        "excluse_implauzibile": interoghează(
            f"""SELECT count(*)::int AS n FROM observatii_curente o
                WHERE o.unitate = 'procent' AND o.camp = ANY(%s)
                  AND split_part(o.cod_scenariu, '|', 1) = %s
                  AND o.valoare_num > {prag}""",
            (campuri, categorie),
        )[0]["n"],
        # Cine a adus valorile. Cele trei variante de colectare acopera banci
        # diferite: la depozite, varianta BS4 e singura care ajunge la garanti,
        # procredit, salt si vista. Fara defalcarea asta, contributia fiecarei
        # variante e invizibila in interfata.
        "provenienta": interoghează(
            f"""SELECT o.metoda_extractie AS metoda, count(*)::int AS valori,
                       count(DISTINCT b.slug)::int AS banci
                FROM observatii_curente o
                JOIN surse s ON s.id = o.id_sursa
                JOIN banci b ON b.id = s.id_banca
                WHERE o.unitate = 'procent' AND o.camp = ANY(%s)
                  AND split_part(o.cod_scenariu, '|', 1) = %s
                  AND NOT o.ambiguu AND o.valoare_num <= {prag}
                GROUP BY 1 ORDER BY 2 DESC""",
            (campuri, categorie),
        ),
    }


def sentiment(q):
    """Sentiment din review-urile reale de App Store (nu mock).

    Filtrabil pe banca si pe nota. Sumarul si distributia rman pe TOATE
    bancile, nu se filtreaza: altfel nu se mai vede cu ce se compara banca
    selectata.
    """
    where, params = ["TRUE"], []
    if q.get("banca"):
        where.append("b.slug = %s")
        params.append(q["banca"][0])
    if q.get("nota"):
        where.append("v.rating = %s")
        params.append(int(q["nota"][0]))
    if q.get("storefront"):
        where.append("v.storefront = %s")
        params.append(q["storefront"][0])
    filtru = " AND ".join(where)
    return {
        "distributie": interoghează(
            """SELECT b.slug AS banca, v.rating, count(*)::int AS n
               FROM app_review v JOIN banci b ON b.id = v.id_banca
               GROUP BY 1, 2 ORDER BY 1, 2"""
        ),
        "sumar": interoghează(
            """SELECT b.slug AS banca, b.nume,
                      count(*)::int AS review_uri,
                      round(avg(v.rating), 2)::float8 AS medie_text,
                      max(ar.rating_agregat)::float8  AS medie_store,
                      max(ar.volum_rating)::int       AS volum_store,
                      count(*) FILTER (WHERE v.rating <= 2)::int AS negative
               FROM app_review v
               JOIN banci b ON b.id = v.id_banca
               LEFT JOIN app_release ar ON ar.id_banca = b.id AND ar.platforma = v.platforma
               GROUP BY 1, 2 ORDER BY review_uri DESC"""
        ),
        "storefronts": interoghează(
            """SELECT v.storefront, count(*)::int AS n FROM app_review v
               GROUP BY 1 ORDER BY 2 DESC"""
        ),
        "total_filtrat": interoghează(
            f"""SELECT count(*)::int AS n FROM app_review v
                JOIN banci b ON b.id = v.id_banca WHERE {filtru}""", params
        )[0]["n"],
        "recente": interoghează(
            f"""SELECT b.slug AS banca, b.nume AS banca_nume, v.rating, v.storefront,
                       v.versiune, v.text, left(v.autor_hash, 8) AS autor, v.postat_la
                FROM app_review v JOIN banci b ON b.id = v.id_banca
                WHERE {filtru}
                ORDER BY v.postat_la DESC NULLS LAST LIMIT 120""", params
        ),
    }


def versus_extra():
    """Rândurile de comparație care NU vin din prețuri.

    Versus acoperea doar 2.1 și 2.2 (comisioane + dobânzi). Secțiunile 2.3
    (mobil), 2.5 (rețea) și 2.7 (sentiment) existau în aplicație, dar nu se
    puteau compara cap la cap. Aici sunt aduse în aceeași formă ca celulele de
    preț: valoare + la ce se referă + sensul (mai mare/mai mic e mai bun).

    Fiecare rând spune și de unde vine, fiindcă nu toate sunt egale: ratingul
    e real din App Store, locațiile vin din Overture Maps.
    """
    return {
        "mobil": interoghează(
            """SELECT b.slug AS banca, ar.platforma, ar.versiune,
                      ar.rating_agregat::float8 AS rating,
                      ar.volum_rating::int      AS volum,
                      (SELECT count(*)::int FROM app_screenshot sh
                        WHERE sh.id_banca = b.id) AS capturi
               FROM app_release ar JOIN banci b ON b.id = ar.id_banca"""
        ),
        "retea": interoghează(
            """SELECT b.slug AS banca,
                      count(*) FILTER (WHERE l.tip = 'sucursala')::int AS sucursale,
                      count(*) FILTER (WHERE l.tip = 'atm')::int       AS atm,
                      round(avg(l.rating) FILTER (WHERE l.tip = 'sucursala'), 2)::float8
                        AS rating_sucursale
               FROM locatii l JOIN banci b ON b.id = l.id_banca
               GROUP BY 1"""
        ),
        "sentiment": interoghează(
            """SELECT b.slug AS banca, count(*)::int AS review_uri,
                      round(avg(v.rating), 2)::float8 AS medie_text,
                      round(100.0 * count(*) FILTER (WHERE v.rating <= 2) / count(*), 0)::float8
                        AS pct_negative
               FROM app_review v JOIN banci b ON b.id = v.id_banca
               GROUP BY 1"""
        ),
        "acoperire": interoghează(
            """SELECT b.slug AS banca,
                      count(DISTINCT o.camp)::int AS servicii_cunoscute,
                      count(o.id)::int            AS valori
               FROM banci b
               LEFT JOIN surse s ON s.id_banca = b.id
               LEFT JOIN observatii_curente o ON o.id_sursa = s.id
               GROUP BY 1"""
        ),
    }


def istoric(q):
    """Schimbarile de pret: acelasi serviciu, alta data de vigoare, alta valoare.

    Vine din vederea `schimbari_pret`, care se recalculeaza din observatii -
    deci nu poate rmane desincronizata de ele. Asta e „change_event" din
    figura 1 a artefactului: schimbarea e produsul, nu un efect secundar.

    Prima incarcare arunca istoricul (excludea `stare_data IN (ISTORIC,
    DUBLURA)` si nu pastra `data_vigoare`). Migrarea 008 l-a recuperat.
    """
    where, params = ["TRUE"], []
    if q.get("banca"):
        where.append("banca = %s")
        params.append(q["banca"][0])
    if q.get("camp"):
        where.append("camp = %s")
        params.append(q["camp"][0])
    if q.get("directie") == ["scumpire"]:
        where.append("delta > 0")
    elif q.get("directie") == ["ieftinire"]:
        where.append("delta < 0")
    filtru = " AND ".join(where)
    return {
        "randuri": interoghează(
            f"""SELECT banca, banca_nume, camp, serviciu, unitate,
                       data_ant, valoare_ant::float8, data_noua, valoare_noua::float8,
                       delta::float8, delta_pct::float8, citat, pagina, sursa,
                       url_public, metoda_extractie
                FROM schimbari_pret WHERE {filtru}
                ORDER BY data_noua DESC, abs(delta_pct) DESC NULLS LAST""", params
        ),
        "pe_banca": interoghează(
            """SELECT banca, count(*)::int AS n,
                      count(*) FILTER (WHERE delta > 0)::int AS scumpiri,
                      count(*) FILTER (WHERE delta < 0)::int AS ieftiniri
               FROM schimbari_pret GROUP BY 1 ORDER BY 2 DESC"""
        ),
        # Cate observatii au datare, si cate nu: fara asta, „18 schimbari" pare
        # o cifra completa, cand de fapt se poate calcula doar pe ce e datat.
        "acoperire": interoghează(
            """SELECT coalesce(stare_data, 'fără datare') AS stare,
                      count(*)::int AS n
               FROM observations GROUP BY 1 ORDER BY 2 DESC"""
        ),
        "interval": interoghează(
            """SELECT min(data_vigoare) AS din, max(data_vigoare) AS pana,
                      count(DISTINCT data_vigoare)::int AS date_distincte
               FROM observations WHERE data_vigoare IS NOT NULL"""
        )[0],
    }


def stare():
    """Prospetimea reala a fiecarui domeniu de date, din timestampurile din baza.

    Nu e estimare: fiecare rand vine din max(created_at/observat_la) al
    tabelului respectiv. Unde scrie 'niciodata', chiar nu s-a rulat nimic.
    """
    return interoghează(
        """
        SELECT 'Surse descoperite'      AS domeniu, count(*)::int AS randuri,
               max(created_at)          AS ultima, 'discovery LLM' AS provenienta FROM surse
        UNION ALL
        SELECT 'Observații (comisioane + rate)', count(*)::int, max(created_at),
               (SELECT string_agg(DISTINCT metoda_extractie, ' + ' ORDER BY metoda_extractie)
                  FROM observations) FROM observations
        UNION ALL
        SELECT 'Schimbări de preț detectate', count(*)::int, NULL::timestamptz,
               'vederea schimbari_pret' FROM schimbari_pret
        UNION ALL
        SELECT 'Amprente documente', count(*)::int, max(created_at), 'urme.py' FROM hashes
        UNION ALL
        SELECT 'Versiuni aplicații', count(*)::int, max(observat_la), 'iTunes Lookup API' FROM app_release
        UNION ALL
        SELECT 'Review-uri aplicații', count(*)::int, max(postat_la)::timestamptz, 'feed RSS Apple' FROM app_review
        UNION ALL
        SELECT 'Indici BNR', count(*)::int, NULL::timestamptz, 'bnr_indici.json' FROM indici_referinta
        UNION ALL
        SELECT 'Locații', count(*)::int, max(observat_la), 'Overture Maps Places' FROM locatii
        UNION ALL
        SELECT 'Evenimente de schimbare', count(*)::int, max(created_at), 'diferente.py (neconectat)' FROM change_events
        """
    )


def logos():
    """slug -> calea locala a logoului, pentru bancile care au unul descarcat."""
    dosar = os.path.join(AICI, "logos")
    gasite = {}
    if os.path.isdir(dosar):
        for f in sorted(os.listdir(dosar)):
            slug, _, ext = f.rpartition(".")
            if slug and ext.lower() in ("svg", "png", "ico", "jpg", "jpeg", "webp"):
                gasite.setdefault(slug, "/logos/" + f)
    return gasite


def recenzii(q):
    if not q.get("id_locatie"):
        return {"eroare": "lipsește id_locatie"}
    return interoghează(
        """SELECT rating, text, left(autor_hash, 8) AS autor, postat_la, sursa
           FROM locatii_recenzii WHERE id_locatie = %s
           ORDER BY postat_la DESC NULLS LAST""",
        (int(q["id_locatie"][0]),),
    )


def coada(q):
    """Valorile care nu trec porțile de calitate, cu tot ce trebuie ca să decizi.

    Selecta doar 11 coloane si nu includea `url_public`, `pagina`, `tip_sursa`
    sau `serviciu` - de-aia linkurile din pagina nu functionau: interfata cerea
    campuri care nu veneau. Acum vine tot ce cere o decizie umana.

    `fratii` e detaliul care lipsea cel mai mult: pentru un rand cu „prag de
    suma pierdut", celelalte valori ale ACELUIASI serviciu (1, 3, 5, 15 lei)
    fac problema evidenta - se vede ca sunt tranșe, nu preturi alternative.
    Fara ele, fiecare rand pare o valoare izolata si inexplicabila.
    """
    where, params = ["TRUE"], []
    if q.get("motiv"):
        where.append("c.motiv = %s")
        params.append(q["motiv"][0])
    if q.get("banca"):
        where.append("c.banca = %s")
        params.append(q["banca"][0])
    if q.get("produs"):
        where.append("c.produs = %s")
        params.append(q["produs"][0])
    limit = min(int((q.get("limit") or ["120"])[0]), 500)
    base = f"FROM coada_verificare c WHERE {' AND '.join(where)}"

    randuri = interoghează(
        """SELECT c.id, c.banca, c.banca_nume, c.produs, c.camp, c.serviciu,
                  c.valoare_num::float8 AS valoare_num, c.unitate,
                  c.confidence::float8 AS confidence, c.ambiguu, c.motiv,
                  c.motiv_ambiguu, c.citat, c.pagina, c.sursa, c.tip_sursa,
                  c.url_public, c.metoda_extractie, b.pagina_documente
           """
        + base.replace("FROM coada_verificare c",
                       "FROM coada_verificare c JOIN banci b ON b.slug = c.banca")
        + " ORDER BY c.banca, c.camp, coalesce(c.serviciu, ''), c.valoare_num "
          "LIMIT %s",
        params + [limit],
    )
    for r in randuri:
        r["link"] = r["url_public"] or (
            r["sursa"] if r["tip_sursa"] == "url" and str(r["sursa"]).startswith("http")
            else None
        )
        r["link_pagina"] = None if r["link"] else r["pagina_documente"]
        r["fisier"] = os.path.basename(str(r["sursa"])) if r["tip_sursa"] == "document" else None
        r["ancora"] = ancora(r)

    # Valorile-frate: acelasi serviciu la aceeasi banca, TOATE valorile, nu
    # doar cele din coada. Asa se vede daca cifra face parte dintr-o serie de
    # tranșe sau e singura.
    chei = {(r["banca"], r["camp"], r["serviciu"]) for r in randuri if r["serviciu"]}
    fratii = {}
    if chei:
        rez = interoghează(
            """SELECT b.slug AS banca, o.camp, o.serviciu,
                      array_agg(DISTINCT o.valoare_num ORDER BY o.valoare_num) AS valori,
                      count(*)::int AS n
               FROM observations o
               JOIN surse s ON s.id = o.id_sursa
               JOIN banci b ON b.id = s.id_banca
               WHERE (b.slug, o.camp, o.serviciu) IN %s AND o.valoare_num IS NOT NULL
               GROUP BY 1, 2, 3""",
            (tuple(chei),),
        )
        for x in rez:
            fratii[f'{x["banca"]}|{x["camp"]}|{x["serviciu"]}'] = {
                "valori": [float(v) for v in x["valori"]][:14], "n": x["n"]
            }

    return {
        "pe_motiv": interoghează(
            "SELECT motiv, count(*)::int AS n FROM coada_verificare GROUP BY 1 ORDER BY 2 DESC"
        ),
        "pe_banca": interoghează(
            """SELECT banca, banca_nume, count(*)::int AS n
               FROM coada_verificare GROUP BY 1, 2 ORDER BY 3 DESC"""
        ),
        "pe_produs": interoghează(
            """SELECT produs, count(*)::int AS n
               FROM coada_verificare GROUP BY 1 ORDER BY 2 DESC"""
        ),
        # Cât din tot ce avem stă în coadă: fără raportul asta, „1.166 de
        # rânduri" nu spune dacă e mult sau puțin.
        "context": interoghează(
            """SELECT (SELECT count(*)::int FROM observations) AS observatii_total,
                      (SELECT count(*)::int FROM coada_verificare) AS in_coada,
                      (SELECT count(*)::int FROM coada_verificare
                        WHERE url_public IS NOT NULL) AS in_coada_cu_link"""
        )[0],
        "total": interoghează("SELECT count(*)::int AS n " + base, params)[0]["n"],
        "randuri": randuri,
        "fratii": fratii,
    }


RUTE = {
    "/api/sumar": lambda q: sumar(),
    "/api/banci": lambda q: banci(),
    "/api/observatii": observatii,
    "/api/surse": surse,
    "/api/mobil": lambda q: mobil(),
    "/api/indici": lambda q: indici(),
    "/api/coada": coada,
    "/api/locatii": locatii,
    "/api/recenzii": recenzii,
    "/api/logos": lambda q: logos(),
    "/api/matrice": matrice,
    "/api/celula": celula,
    "/api/rate": rate,
    "/api/sentiment": sentiment,
    "/api/istoric": istoric,
    "/api/versus_extra": lambda q: versus_extra(),
    "/api/stare": lambda q: stare(),
}


_PERMISE = {}


def pdf_permis(url):
    """Un URL de PDF e servit DOAR dacă e deja în baza noastră de surse.

    Fără verificarea asta, ruta `/pdf` ar fi un proxy deschis: oricine cu
    acces la aplicație ar putea cere orice adresă din internet prin serverul
    nostru, inclusiv adrese din rețeaua internă. Lista albă e baza de date:
    se servesc doar documentele pe care pipeline-ul le-a înregistrat ca surse.

    Rezultatul se ține în memorie: o conexiune nouă la Postgres costă ~2s pe
    Windows, iar fără cache fiecare deschidere de document plătea de două ori
    (o dată verificarea, o dată servirea) chiar și când fișierul era deja local.
    """
    if not url or not url.startswith("https://"):
        return False
    if url not in _PERMISE:
        _PERMISE[url] = bool(interoghează(
            """SELECT 1 FROM surse
               WHERE url_public = %s OR (tip_sursa = 'url' AND sursa = %s)
               LIMIT 1""",
            (url, url),
        ))
    return _PERMISE[url]


CACHE_PDF = os.path.join(AICI, ".cache_pdf")


def adu_pdf(url):
    """Aduce PDF-ul o singură dată și îl păstrează local.

    De ce prin serverul nostru: vizualizatorul propriu (PDF.js) are nevoie de
    fișier de pe aceeași origine. Un `fetch` direct către CDN-ul băncii cade pe
    CORS, iar fără fișier nu se poate nici sări la pagină, nici evidenția.

    Cache-ul nu e optimizare, e politețe: altfel fiecare deschidere a
    sertarului ar re-descărca de la bancă același document.
    """
    import hashlib
    os.makedirs(CACHE_PDF, exist_ok=True)
    cale = os.path.join(CACHE_PDF, hashlib.sha256(url.encode()).hexdigest() + ".pdf")
    if os.path.exists(cale) and os.path.getsize(cale) > 1000:
        return cale
    # `requests`, nu `urllib`: verificarea certificatelor prin depozitul
    # sistemului pică pe unele domenii (ing.ro dă CERTIFICATE_VERIFY_FAILED
    # fiindcă lipsește intermediarul). `requests` folosește `certifi`.
    import requests
    r = requests.get(url, timeout=40, headers={
        # User-Agent onest, ca la colectare: se identifică, nu se dă drept browser.
        "User-Agent": "MIP/1.0 (monitorizare concurenta; contact IT Libra Bank)",
        "Accept": "application/pdf,*/*",
    })
    if not r.ok:
        raise ValueError(f"HTTP {r.status_code}")
    if not r.content.startswith(b"%PDF"):
        raise ValueError("răspunsul nu e un PDF")
    with open(cale, "wb") as f:
        f.write(r.content)
    return cale


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/pdf":
            q = urllib.parse.parse_qs(parsed.query)
            url = (q.get("u") or [""])[0]
            if not pdf_permis(url):
                self.send_error(403, "URL neinregistrat ca sursa")
                return
            try:
                cale = adu_pdf(url)
            except Exception as exc:
                self.send_error(502, f"nu s-a putut aduce PDF-ul: {exc}")
                return
            with open(cale, "rb") as f:
                corp = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Length", str(len(corp)))
            self.send_header("Cache-Control", "public, max-age=86400")
            self.end_headers()
            self.wfile.write(corp)
            return
        if parsed.path in RUTE:
            try:
                date = RUTE[parsed.path](urllib.parse.parse_qs(parsed.query))
                corp = json.dumps(date, ensure_ascii=False, default=str).encode("utf-8")
                cod = 200
            except Exception as exc:
                corp = json.dumps(
                    {"eroare": f"{exc.__class__.__name__}: {exc}"}, ensure_ascii=False
                ).encode("utf-8")
                cod = 500
            self.send_response(cod)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(corp)))
            self.end_headers()
            self.wfile.write(corp)
            return
        if parsed.path in ("/", "/index.html"):
            self.path = "/index.html"
        return super().do_GET()

    def translate_path(self, path):
        rel = urllib.parse.urlparse(path).path.lstrip("/")
        return os.path.join(AICI, rel or "index.html")

    def log_message(self, fmt, *args):
        pass  # fara zgomot in consola


class Server(socketserver.ThreadingTCPServer):
    """Server dual-stack pe loopback, ca `localhost` să nu mai coste 2 secunde.

    Problema, măsurată: pe Windows `localhost` se rezolvă întâi la `::1` (IPv6)
    și abia apoi la `127.0.0.1`. Serverul ascultând doar pe IPv4, fiecare cerere
    aștepta expirarea încercării IPv6 înainte să reușească. Rezultat:
    `http://localhost:8765/index.html` răspundea în 2.041 ms, iar
    `http://127.0.0.1:8765/index.html` în 7 ms — de 290 de ori mai repede,
    pentru exact aceeași muncă. Nu era baza de date și nu era randarea; era
    rezolvarea numelui.

    Soluția: un singur socket IPv6 cu `IPV6_V6ONLY` dezactivat acceptă și
    conexiuni IPv4 mapate, deci ambele nume merg instant. Se leagă la `::` ca
    dual-stack-ul să funcționeze (legarea la `::1` ar accepta doar IPv6), dar
    accesul din afara mașinii e refuzat în `verify_request` — aplicația citește
    dintr-o bază locală și nu are autentificare, deci nu are ce căuta în rețea.
    """
    allow_reuse_address = True
    daemon_threads = True
    address_family = socket.AF_INET6

    def server_bind(self):
        try:
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        except (AttributeError, OSError):
            pass          # sistem fără dual-stack: rămâne doar IPv6
        super().server_bind()

    def verify_request(self, cerere, adresa):
        gazda = adresa[0]
        return gazda in ("::1", "127.0.0.1", "::ffff:127.0.0.1")


if __name__ == "__main__":
    try:
        srv = Server(("::", PORT), Handler)
    except OSError:
        # fără IPv6 pe mașină: se revine la IPv4, cu avertismentul de rigoare
        socketserver.ThreadingTCPServer.allow_reuse_address = True
        srv = socketserver.ThreadingTCPServer(("127.0.0.1", PORT), Handler)
        print("IPv6 indisponibil — se ascultă doar IPv4. "
              "Folosește http://127.0.0.1 (nu localhost), altfel fiecare "
              "cerere plătește o încercare IPv6 expirată.")
    with srv:
        print(f"MIP viewer: http://localhost:{PORT}  (Ctrl+C pentru oprire)")
        srv.serve_forever()
