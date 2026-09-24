"""Validatorul colegului (crawler/validator.py) aplicat dobânzilor extrase.

Pe etalonul manual: 37 din 38 de verdicte corecte. Nu era conectat la
pipeline. Rulează o dată pe tot setul, nu pe pagină: consensul indicilor între
bănci și regula „DAE ≥ nominală pe aceeași pagină" au nevoie de toate valorile.

SUSPECT și SURSA_VECHE nu se șterg: devin `ambiguu`, deci ajung în coada de
verificare umană, cum cere figura 3 („nu se publică automat nimic nesigur").
"""

import collections


def valideaza_rate(brute, valideaza=None):
    if valideaza is None:
        from crawler.validator import valideaza
    cu_rec = [b for b in brute if b.get("_rec")]
    raport = collections.Counter()
    if not cu_rec:
        return raport
    recs = [b["_rec"] for b in cu_rec]
    valideaza(recs, None)       # fără indici BNR: validatorul trece pe consens
    for b, r in zip(cu_rec, recs):
        stare = r.get("stare") or "NEVERIFICAT"
        b["stare"] = stare
        raport[f"validator_{stare}"] += 1
        if stare in ("SUSPECT", "SURSA_VECHE"):
            b["ambiguu"] = True
            b["motiv_ambiguu"] = f"validator: {stare}"
    return raport
