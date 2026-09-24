"""Versiunile aceluiași document: doar cea mai nouă e „în vigoare".

Măsurat pe 24.09.2026: BCR avea lista de tarife PJ în peste 15 versiuni
(2021–2026) plus traducerile în engleză, toate `IN_VIGOARE` — 13.661 de valori,
jumătate din bază. `data_document.stare_fata_de` știe doar dacă o dată e în
viitor, nu și că există o versiune mai nouă a aceluiași document.

Trei reguli, pe documentele unei bănci:
  1. în aceeași familie (`data_document.familie_document`), versiunea cu cea
     mai nouă dată rămâne; celelalte devin ISTORIC;
  2. o traducere (EN / „fees", „tariffs") devine DUBLURA dacă banca are și
     documente în română pentru același segment;
  3. o familie a cărei ultimă versiune e cu peste 365 de zile mai veche decât
     cel mai nou document al aceluiași segment devine ISTORIC — același
     document, publicat mai demult sub alt tipar de nume.

Nimic nu se șterge: ISTORIC rămâne în istoricul de prețuri (`schimbari_pret`),
doar nu mai apare printre prețurile curente.
"""

import collections
import datetime
import re
import urllib.parse

RE_TRADUCERE = re.compile(r"(^|[_\W])(en|eng|english)([_\W]|$)|fees|tariffs|commission", re.I)
ZILE_FAMILIE_VECHE = 365


def _data(v):
    if isinstance(v, datetime.date):
        return v
    try:
        return datetime.date.fromisoformat(str(v)[:10])
    except (TypeError, ValueError):
        return None


def _nume(sursa):
    return urllib.parse.unquote(str(sursa).split("?")[0].rsplit("/", 1)[-1])


def marcheaza(brute, familie=None, azi=None):
    if familie is None:
        from crawler.data_document import familie_document as familie
    azi = azi or datetime.date.today()
    docs = collections.defaultdict(lambda: {"data": None, "segment": None})
    for b in brute:
        if b.get("tip_sursa") != "document":
            continue
        d = docs[(b["banca"], b["sursa"])]
        dv = _data(b.get("data_vigoare"))
        if dv and dv <= azi and (d["data"] is None or dv > d["data"]):
            d["data"] = dv
        d["segment"] = d["segment"] or b.get("segment")

    stare = {}
    pe_familie = collections.defaultdict(list)
    pe_segment = collections.defaultdict(list)
    for (banca, sursa), d in docs.items():
        f = familie(_nume(sursa))
        pe_familie[(banca, f)].append((sursa, d["data"]))
        pe_segment[(banca, d["segment"])].append((sursa, d["data"], f))

    for (banca, f), membri in pe_familie.items():
        date = [x for _, x in membri if x]
        if not date:
            continue
        cea_noua = max(date)
        for sursa, x in membri:
            if x and x < cea_noua:
                stare[(banca, sursa)] = "ISTORIC"

    for (banca, seg), membri in pe_segment.items():
        date = [x for _, x, _ in membri if x]
        if not date:
            continue
        cea_noua = max(date)
        ultima_pe_familie = collections.defaultdict(lambda: None)
        for _, x, f in membri:
            if x and (ultima_pe_familie[f] is None or x > ultima_pe_familie[f]):
                ultima_pe_familie[f] = x
        are_romana = any(not RE_TRADUCERE.search(_nume(s)) for s, _, _ in membri)
        for sursa, x, f in membri:
            if are_romana and RE_TRADUCERE.search(_nume(sursa)):
                stare[(banca, sursa)] = "DUBLURA"
            elif ultima_pe_familie[f] and (cea_noua - ultima_pe_familie[f]).days > ZILE_FAMILIE_VECHE:
                stare.setdefault((banca, sursa), "ISTORIC")

    raport = collections.Counter()
    for b in brute:
        s = stare.get((b.get("banca"), b.get("sursa")))
        if s and b.get("stare_data") in (None, "IN_VIGOARE", "DATA_NECUNOSCUTA"):
            b["stare_data"] = s
            raport[f"versiuni_{s}"] += 1
    return raport
