"""Normalizatorul campaniilor și al comunicatelor: brut → rând în `campanii`,
`campanii_surse`, `comunicate` (migrarea 019).

Singurul loc brut → rând pentru aceste tabele, cum e `normalizeaza.py` pentru
`observations` (regula din CLAUDE.md, restrânsă explicit în același set de
modificări). Separat, fiindcă o campanie nu e un preț: nu trece prin
vocabularul canonic, prin praguri sau prin `cod_scenariu`, iar valorile ei nu
intră în `observations`.

Aici stau deciziile, o singură dată:
  - ce document dă titlul, fereastra și beneficiul campaniei (prioritățile);
  - `tip_oferta` și `stare`, după definiția strictă (§9.1 b): 'campanie' doar
    cu o fereastră citită din text; ce nu se decide din text → 'de_verificat',
    cu motivul scris, nu ghicit;
  - `organizator` (bancă / grup / schema de card / partener);
  - `e_campanie` pe titlul unui comunicat.

Scrierea e idempotentă: upsert pe (bancă, cheie) și pe (campanie, URL); nu se
șterge nimic. O campanie care nu mai apare rămâne, cu `ultima_vedere` veche.
Rândurile corectate de om (`metoda_extractie = 'manual'`) nu se suprascriu.
"""

import datetime
import re

import campanii_extractie as E

MAX_ZILE_FEREASTRA = 3 * 366


# ==========================================================================
# Campania: din documentele ei
# ==========================================================================

def _primul(*valori):
    return next((v for v in valori if v), None)


def _categorie(url, titlu):
    """Categoria de produs din regula unică de clasificare (extractoare.REGULI_URL).
    „comisioane" și „curs" nu sunt categorii de campanie: „curs" prindea
    „concurs", iar „conditii" din calea unui regulament dădea „comisioane"."""
    import extractoare
    categorie = extractoare.clasifica(url, titlu)[0]
    return None if categorie in (None, "comisioane", "curs") else categorie


def campanie(cheie, membri, documente, data_rulare, provenienta):
    """Rândul `campanii` și legăturile `campanii_surse` ale unei campanii.

    `membri`: [{url, rol_document, eticheta, url_hub}] — documentele campaniei
    (pagina, regulamentele, actele adiționale); `documente`: url → brut
    (ieșirea lui `campanii_extractie.document`, plus verdictul transportului).
    """
    docs = [(m, documente.get(m["url"]) or {}) for m in membri]
    pagini = [d for m, d in docs if m["rol_document"] == "landing" and d.get("format") == "html"]
    regulamente = [d for m, d in docs if m["rol_document"] in ("regulament", "act_aditional")]
    etichete = [m["eticheta"] for m, _ in docs if m.get("eticheta")]
    eticheta = next((m["eticheta"] for m, _ in docs if m["url"] == cheie and m.get("eticheta")),
                    etichete[0] if etichete else None)

    # Titlu: pagina campaniei, eticheta de pe hub, antetul regulamentului, URL
    titlu, titlu_din = None, None
    for valoare, sursa in [(_primul(*[d.get("titlu") for d in pagini]), "pagina"),
                           (eticheta, "eticheta_link"),
                           (_primul(*[d.get("titlu") for d in regulamente]), "document"),
                           (E.titlu_din_url(cheie), "url")]:
        if valoare:
            titlu, titlu_din = valoare, sursa
            break

    # Fereastra: regulamentul (62 din 74 aveau perioada dintr-un document),
    # pagina, eticheta de pe hub (11 campanii BCR o aveau doar acolo), numele
    # fișierului (BRD „Youth 07.09-30.11.2026.pdf", PDF scanat)
    fereastra, sursa_ferestrei = None, None
    candidati = ([(d.get("perioada"), "document") for d in regulamente + pagini]
                 + [(E.perioada(e, an_implicit=E.an_din_url(cheie), eticheta=True), "eticheta_link")
                    for e in etichete]
                 + [(E.perioada_din_url(m["url"]), "url") for m, _ in docs])
    for p, sursa in candidati:
        if p:
            fereastra, sursa_ferestrei = p, sursa
            break

    beneficiu = _primul(*[d.get("beneficiu") for d in pagini],
                        E.beneficiu("", eticheta=eticheta) if eticheta else None,
                        *[d.get("beneficiu") for d in regulamente])

    organizator, organizator_citat = "banca", None
    for d in regulamente + pagini:
        if d.get("organizator"):
            organizator, organizator_citat = d["organizator"]
            break

    act = any(d.get("act_aditional") for _, d in docs) or any(
        m["rol_document"] == "act_aditional" for m, _ in docs)
    adusi = [d for _, d in docs if d.get("verdict") == "OK"]
    cu_text = [d for d in adusi if not d.get("fara_text")]

    tip, stare, motive = None, None, []
    if fereastra:
        tip = "campanie"
        st, sf = fereastra["start"], fereastra["sfarsit"]
        if fereastra.get("an_dedus"):
            motive.append("anul lipsește din text; dedus din calea documentului")
        if not fereastra.get("ancorata"):
            motive.append("date fără cuvânt de perioadă în jur")
        if fereastra.get("o_singura_zi"):
            motive.append("o singură dată în etichetă: ziua campaniei sau data publicării?")
        if st and (sf - st).days > MAX_ZILE_FEREASTRA:
            motive.append("fereastră de peste 3 ani")
        if act:
            motive.append("act adițional: sfârșitul poate fi modificat")
        if not adusi:
            motive.append("documentul nu s-a putut aduce; fereastra doar din etichetă sau URL")
        if motive:
            stare = "de_verificat"
        elif sf < data_rulare:
            stare = "incheiata"
        elif st and st > data_rulare:
            stare, motive = "de_verificat", ["începe după data rulării"]
        else:
            stare = "activa"
    else:
        nedeterminat = _primul(*[d.get("nedeterminat") for d in cu_text])
        maxima = max([d["data_maxima"] for d in cu_text if d.get("data_maxima")], default=None)
        if nedeterminat:
            text_titlu = E._fara_diacritice_1la1(titlu or "")
            tip = "program" if "program" in text_titlu or "program" in nedeterminat else "oferta_curenta"
            stare, motive = "activa", [f"fără termen în text: „{nedeterminat}”"]
        elif maxima and maxima < data_rulare:
            # Treapta B (Nicolae, §4.1): pe testul din 25.09, 287 de documente
            # fără nicio dată din text ≥ ziua fotografiei, și niciuna dintre cele
            # 74 de campanii stricte active printre ele; tipul rămâne nedecis
            stare, motive = "incheiata", [f"treapta B: cea mai recentă dată din text e {maxima:%d.%m.%Y}"]
        else:
            stare = "de_verificat"
            if not adusi:
                motive.append("documentul nu s-a putut aduce: "
                              + ", ".join(sorted({d.get("verdict") or "?" for _, d in docs})))
            elif not cu_text:
                motive.append("fără strat de text (PDF scanat sau pagină randată în JS)")
            else:
                motive.append("fără perioadă în text")
    if act and "act adițional: sfârșitul poate fi modificat" not in motive:
        motive.append("act adițional: sfârșitul poate fi modificat")

    rand = {
        "cheie": cheie,
        "url": cheie,
        "titlu": titlu,
        "titlu_din": titlu_din,
        "beneficiu": beneficiu,
        "beneficiu_citat": beneficiu,
        "segment": _primul(E.segment(cheie, titlu), *[E.segment(m["url"]) for m, _ in docs]),
        "categorie_produs": _categorie(cheie, titlu),
        "tip_oferta": tip,
        "organizator": organizator,
        "organizator_citat": organizator_citat,
        "fereastra_start": fereastra["start"] if fereastra else None,
        "fereastra_sfarsit": fereastra["sfarsit"] if fereastra else None,
        "fereastra_citat": fereastra["citat"] if fereastra else None,
        "sfarsit_din": "perioada_initiala" if fereastra else None,
        "sursa_ferestrei": sursa_ferestrei,
        # extractorul citează doar ce a găsit în text sau în etichetă
        "citat_neverificat": False,
        "act_aditional": act,
        "metoda_extractie": "determinist",
        "stare": stare,
        "motiv_verificare": "; ".join(motive) or None,
        "provenienta": provenienta,
    }
    legaturi, vazute = [], set()
    for m, d in docs:
        if m["url"] not in vazute:
            vazute.add(m["url"])
            legaturi.append({"url": m["url"], "rol_document": m["rol_document"],
                             "eticheta": m.get("eticheta"), "format": d.get("format"),
                             "amprenta": d.get("amprenta"), "fara_text": bool(d.get("fara_text")),
                             "cale_bronze": d.get("cale_bronze"), "observat_la": d.get("observat_la"),
                             "id_sursa": d.get("id_sursa")})
        hub = m.get("url_hub")
        if hub and hub not in vazute:
            vazute.add(hub)
            hd = documente.get(hub) or {}
            legaturi.append({"url": hub, "rol_document": "hub", "eticheta": m.get("eticheta"),
                             "format": "html", "amprenta": hd.get("amprenta"), "fara_text": False,
                             "cale_bronze": hd.get("cale_bronze"), "observat_la": hd.get("observat_la"),
                             "id_sursa": hd.get("id_sursa")})
    return rand, legaturi


# ==========================================================================
# Comunicatele
# ==========================================================================

# Regex pe titlu, apoi om (§4.3). Capcanele măsurate de Nicolae: „premi"
# prindea „premieră", „castig" prindea „câștigătorii". „premii" rămâne, deși
# prinde și premiile primite de bancă (Exim, „premii pentru dinamica
# creditării"): de aceea cuvântul potrivit se păstrează, pentru om.
RE_E_CAMPANIE = re.compile(
    r"\bcampani[ae]\b(?!\s+de\s+(?:phishing|frauda|informare|constientizare))|\bpromoti"
    r"|\bconcurs|\btombol|\bcastig[ai]\b|\bcastigi\b|\bpremii(?:le)?\b|\bpremiaz|\bcashback"
    r"|\bbonus\b|\bvoucher|\breducer|rate\s+fara\s+dobanda|dobanda\s+promotional"
    r"|oferta\s+special|\bgratuit")


def e_campanie(titlu):
    """(bool, cuvântul potrivit) pe titlul unui comunicat."""
    m = RE_E_CAMPANIE.search(E._fara_diacritice_1la1(titlu or ""))
    return (True, m.group(0)) if m else (False, None)


def comunicat(brut):
    """Rândul `comunicate` dintr-un comunicat enumerat."""
    da, potrivire = e_campanie(brut.get("titlu"))
    return {"url": brut["url"], "titlu": brut.get("titlu"), "titlu_din": brut.get("titlu_din"),
            "data_publicarii": brut.get("data"), "data_din": brut.get("data_din"),
            "e_campanie": da, "e_campanie_potrivire": potrivire,
            "provenienta": brut["provenienta"], "amprenta": brut.get("amprenta"),
            "cale_bronze": brut.get("cale_bronze"), "id_sursa": brut.get("id_sursa")}


# ==========================================================================
# Scrierea
# ==========================================================================

COLOANE_CAMPANIE = ("titlu", "titlu_din", "beneficiu", "beneficiu_citat", "segment",
                    "categorie_produs", "tip_oferta", "organizator", "organizator_citat",
                    "fereastra_start", "fereastra_sfarsit", "fereastra_citat", "sfarsit_din",
                    "sursa_ferestrei", "citat_neverificat", "act_aditional", "metoda_extractie",
                    "stare", "motiv_verificare", "provenienta", "url")
# Rândurile corectate de om păstrează tot ce a pus omul; se actualizează doar
# momentul în care campania a fost văzută din nou.
_ACTUALIZARE = ",\n".join(
    f"{c} = CASE WHEN campanii.metoda_extractie = 'manual' THEN campanii.{c} ELSE EXCLUDED.{c} END"
    for c in COLOANE_CAMPANIE)


def migrarea_aplicata(cur):
    cur.execute("SELECT to_regclass('public.campanii'), to_regclass('public.comunicate')")
    return all(cur.fetchone())


STATUS_DIN_VERDICT = {"OK": "activ", "ROBOTS": "blocat", "BLOCAT": "blocat",
                      "EXCLUS": "retras", "DISPARUT": "eroare"}


def inregistreaza_sursa(cur, slug, url, rol, fmt, transport, verdict, nota):
    """Sursa documentului în `surse` (ruta `/pdf` servește doar URL-uri de
    acolo), cu rol 'campanie' / 'comunicat'. O sursă care există deja cu alt
    rol (un regulament adus de popularea de prețuri) rămâne a ei: nu i se
    schimbă nici rolul, nici starea. Întoarce id-ul sursei."""
    status = STATUS_DIN_VERDICT.get(verdict, "eroare")
    nota = None if verdict == "OK" else f"{verdict}: {nota or ''}"[:300]
    fmt = fmt if fmt in ("html", "pdf") else None
    metoda = transport if transport in ("http", "playwright") else None
    cur.execute(
        """INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda, status,
                              frecventa, nota_extractie, ultima_rulare)
           SELECT id, 'url', %s, %s, %s, %s, %s, 'manual', %s, now() FROM banci WHERE slug = %s
           ON CONFLICT DO NOTHING RETURNING id""",
        (url, rol, fmt, metoda, status, nota, slug))
    r = cur.fetchone()
    if r:
        return r[0]
    cur.execute("""SELECT s.id, s.rol FROM surse s JOIN banci b ON b.id = s.id_banca
                   WHERE b.slug = %s AND s.tip_sursa = 'url' AND s.sursa = %s""", (slug, url))
    r = cur.fetchone()
    if not r:
        return None
    if r[1] in ("campanie", "comunicat") and verdict is not None:
        cur.execute("""UPDATE surse SET status = %s, nota_extractie = %s, ultima_rulare = now(),
                              format = coalesce(%s, format), metoda = coalesce(%s, metoda)
                       WHERE id = %s""", (status, nota, fmt, metoda, r[0]))
    return r[0]


def scrie_campanii(cur, slug, campanii, data_rulare):
    """campanii: [(rand, legaturi)]. Întoarce (campanii scrise, legături scrise)."""
    n_c = n_l = 0
    for rand, legaturi in campanii:
        valori = [rand[c] for c in COLOANE_CAMPANIE]
        cur.execute(
            f"""INSERT INTO campanii (id_banca, cheie, {", ".join(COLOANE_CAMPANIE)},
                                    prima_vedere, ultima_vedere)
                SELECT b.id, %s, {", ".join(["%s"] * len(COLOANE_CAMPANIE))}, %s, %s
                FROM banci b WHERE b.slug = %s
                ON CONFLICT (id_banca, cheie) DO UPDATE SET
                {_ACTUALIZARE},
                ultima_vedere = greatest(campanii.ultima_vedere, EXCLUDED.ultima_vedere)
                RETURNING id""",
            [rand["cheie"]] + valori + [data_rulare, data_rulare, slug])
        r = cur.fetchone()
        if not r:
            continue
        n_c += 1
        for leg in legaturi:
            cur.execute(
                """INSERT INTO campanii_surse (id_campanie, id_sursa, url, rol_document,
                        eticheta_link, format, amprenta, fara_text, cale_bronze, observat_la,
                        prima_vedere, ultima_vedere)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (id_campanie, url) DO UPDATE SET
                     id_sursa = coalesce(EXCLUDED.id_sursa, campanii_surse.id_sursa),
                     eticheta_link = coalesce(EXCLUDED.eticheta_link, campanii_surse.eticheta_link),
                     format = coalesce(EXCLUDED.format, campanii_surse.format),
                     amprenta = coalesce(EXCLUDED.amprenta, campanii_surse.amprenta),
                     fara_text = EXCLUDED.fara_text,
                     cale_bronze = coalesce(EXCLUDED.cale_bronze, campanii_surse.cale_bronze),
                     observat_la = coalesce(EXCLUDED.observat_la, campanii_surse.observat_la),
                     ultima_vedere = greatest(campanii_surse.ultima_vedere, EXCLUDED.ultima_vedere)""",
                (r[0], leg.get("id_sursa"), leg["url"], leg["rol_document"], leg.get("eticheta"),
                 leg.get("format"), leg.get("amprenta"), leg.get("fara_text", False),
                 leg.get("cale_bronze"), leg.get("observat_la"), data_rulare, data_rulare))
            n_l += 1
    return n_c, n_l


def scrie_comunicate(cur, slug, randuri, data_rulare):
    n = 0
    for c in randuri:
        cur.execute(
            """INSERT INTO comunicate (id_banca, id_sursa, url, titlu, titlu_din, data_publicarii,
                    data_din, e_campanie, e_campanie_potrivire, provenienta, amprenta, cale_bronze,
                    prima_vedere, ultima_vedere)
               SELECT b.id, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
               FROM banci b WHERE b.slug = %s
               ON CONFLICT (id_banca, url) DO UPDATE SET
                 id_sursa = coalesce(EXCLUDED.id_sursa, comunicate.id_sursa),
                 -- un titlu citit din pagină nu se înlocuiește cu unul din URL
                 titlu = CASE WHEN comunicate.titlu_din = 'pagina' AND EXCLUDED.titlu_din <> 'pagina'
                              THEN comunicate.titlu ELSE coalesce(EXCLUDED.titlu, comunicate.titlu) END,
                 titlu_din = CASE WHEN comunicate.titlu_din = 'pagina' AND EXCLUDED.titlu_din <> 'pagina'
                                  THEN comunicate.titlu_din ELSE coalesce(EXCLUDED.titlu_din, comunicate.titlu_din) END,
                 data_publicarii = coalesce(EXCLUDED.data_publicarii, comunicate.data_publicarii),
                 data_din = coalesce(EXCLUDED.data_din, comunicate.data_din),
                 e_campanie = EXCLUDED.e_campanie,
                 e_campanie_potrivire = EXCLUDED.e_campanie_potrivire,
                 amprenta = coalesce(EXCLUDED.amprenta, comunicate.amprenta),
                 cale_bronze = coalesce(EXCLUDED.cale_bronze, comunicate.cale_bronze),
                 ultima_vedere = greatest(comunicate.ultima_vedere, EXCLUDED.ultima_vedere)""",
            (c.get("id_sursa"), c["url"], c["titlu"], c["titlu_din"], c["data_publicarii"],
             c["data_din"], c["e_campanie"], c["e_campanie_potrivire"], c["provenienta"],
             c["amprenta"], c["cale_bronze"], data_rulare, data_rulare, slug))
        n += cur.rowcount
    return n


def azi(momentul=None):
    """Data rulării ca dată (pentru stare) și ca moment (pentru vedere)."""
    m = momentul or datetime.datetime.now().astimezone()
    return m.date(), m
