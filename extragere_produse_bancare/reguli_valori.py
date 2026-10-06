"""
reguli_valori.py — reguli deterministe aplicate fiecărei valori extrase, înainte
de comparatie_libra. Fără model, fără rețea: se pot reaplica oricând pe JSON.

DE CE. Analiza din 02.10 pe 2.156 de valori: cifra apare literal în citat la 99%
din ele, deci validatorul de citat merge. Greșelile erau de INTERPRETARE, iar
încrederea modelului nu le separa (0,77 la zerourile greșite față de 0,81 media):
  - „0” fără niciun „gratuit / fără comision / inclus” în citat: „comision
    negociabil”, „nelimitat”, un citat de pe rândul vecin (2% la retragere salvat
    ca 0 la depunere), 0 pe `altele` pentru un fapt text (garanții, perioadă de grație);
  - dobânda minimă / medie / maximă salvate toate ca `dobanda_fixa`;
  - dobânda penalizatoare (descoperit neautorizat, 50%) salvată ca dobânda produsului;
  - aceeași perioadă în ani la o bancă și în luni la alta.

Ce face fiecare regulă cu valoarea: o lasă, o corectează (cu nota în `reguli`),
sau o respinge (cu motivul). Respinsele nu se pierd: ajung în
inventare-libra/respinse-reguli-<banca>.json.

Plus axa Libra (axa_libra.json): la Libra, valorile vin doar din paginile
produsului Libra respectiv; paginile altor produse Libra se exclud, iar
variantele legitime primesc o etichetă.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

AICI = Path(__file__).parent
AXA = json.loads((AICI / "axa_libra.json").read_text(encoding="utf-8"))
CAMPURI_V2 = {p["id"]: set(p["campuri"])
              for p in json.loads((AICI / "produse_bancare_v2.json").read_text(encoding="utf-8"))["produse"]}

# ── 1. ZERO ─────────────────────────────────────────────────────────
# Un 0 e cea mai grea afirmație din tabel („la concurent e gratuit”), deci
# cere o dovadă explicită în citat. „-” dintr-un tabel NU e dovadă: în listele
# de tarife înseamnă de obicei „nu se aplică”, nu „gratuit”.
DOVADA_ZERO = re.compile(
    r"(?<![\d.,])0(?:[.,]0+)?\s*(?:%|lei|ron|eur|euro|usd)?(?![\d.,]*\d)|\bzero\b|gratuit|gratis|\bfree\b|"
    r"f[aă]r[aă]\s+(?:niciun\s+|nici\s+un\s+)?(?:comision|cost|tax[aăe]|plat[aă]|costuri|comisioane)|"
    r"nu\s+(?:se\s+)?(?:percep|percepe|aplic[aă]|datoreaz[aă])|nu\s+(?:pl[aă]te[sș]ti|vei\s+pl[aă]ti)|"
    r"nu\s+(?:exist[aă]|are|ai|au|percepem)\s+(?:niciun\s+|nicio\s+)?(?:comisi(?:on|oane)|tax[aăe]|cost)|"
    r"nici\s*un(?:ul)?\s+comision|niciun\s+cost|nici\s+la\s+acordare|"
    r"scutit|inclus|included|no\s+fees?|without\s+(?:any\s+)?(?:fees?|charges?)|free\s+of\s+charge|"
    r"nu\s+se\s+taxeaz|netaxat|nu\s+cost[aă]|nu\s+sunt\s+percepute|f[aă]r[aă]\s+sum[aă]\s+minim", re.I)
NEGOCIABIL = re.compile(r"negocia", re.I)
NELIMITAT = re.compile(r"nelimitat|unlimited|f[aă]r[aă]\s+limit|or?ic[aâ]te", re.I)

# câmpuri care numără ceva: la ele „nelimitat” e răspunsul, nu un 0
CAMPURI_NUMARARE = {"operatiuni_incluse", "numar_operatiuni_incluse", "retrageri_gratuite", "numar_rate_fara_dobanda"}

# ── 2. DOBÂNZI ──────────────────────────────────────────────────────
CAMPURI_DOBANDA = {"dobanda_fixa", "dobanda_nominala", "dobanda_variabila"}
PENALIZATOARE = re.compile(r"neautorizat|penaliz|[iî]nt[aâ]rzier|restan[tț]|dep[aă][sș]ire|majorare\s+de\s+[iî]nt", re.I)
# calificativul trebuie să fie lipit de „dobândă”: în „suma minimă 10.000 lei,
# dobândă 7,99%” cuvântul „minimă” e al sumei, nu al dobânzii
CALIFICATIV = re.compile(
    r"(?:dob[aâ]nd\w*|interest(?:\s+rate)?)\s+(?:\w+\s+){0,2}?(minim\w*|maxim\w*|medi[ae]\w*|minimum|maximum|average)\b"
    r"|\b(minim\w*|maxim\w*|medi[ae]\w*|minimum|maximum|average)\s+(?:\w+\s+){0,1}?(?:dob[aâ]nd|interest)", re.I)

INTERVAL = re.compile(r"valoare(?:a)?\s+(minim\w*|maxim\w*)\s+a\s+intervalului()", re.I)

# ── 3. UNITĂȚI ──────────────────────────────────────────────────────
# perioadele se compară în luni; `fix_ani` din scenariu nu e afectat
PERIOADE_IN_LUNI = re.compile(r"^perioada")


def _forme(x: float) -> set[str]:
    """Felurile în care o cifră poate fi scrisă într-un document românesc sau englez."""
    f = set()
    for d in range(0, 5):
        s = f"{x:.{d}f}"
        if float(s) != x:
            continue
        i, _, z = s.partition(".")
        for sep in (".", " ", ",", ""):
            g = f"{int(i):,}".replace(",", sep)
            f |= {g + ("," + z if z else ""), g + ("." + z if z else "")}
    return f


def pozitie_cifra(x: float, citat: str) -> int | None:
    """Unde apare cifra în citat (inclusiv „2 milioane”), sau None dacă nu apare literal."""
    c = citat.replace(" ", " ")
    for f in sorted(_forme(x), key=len, reverse=True):
        m = re.search(r"(?<![\d.,])" + re.escape(f) + r"(?![\d])", c)
        if m:
            return m.start()
    for mult, cuv in ((1e9, "miliard"), (1e6, "milio"), (1e6, r"m\b"), (1e3, "mii")):
        if abs(x) >= mult:
            for f in _forme(x / mult):
                m = re.search(r"(?<![\d.,])" + re.escape(f) + r"\s*" + cuv, c, re.I)
                if m:
                    return m.start()
    return None


def aplica(o: dict) -> tuple[dict | None, str | None]:
    """
    Aplică regulile pe o observație din flow (dicționarul din `observatii`).
    Întoarce (observația, None) — eventual corectată, cu notele în o["reguli"] —
    sau (None, motiv) când valoarea se respinge.
    """
    o = dict(o)
    note = []
    camp, x, cit = o.get("camp") or "", o.get("valoare_num"), o.get("citat") or ""
    v2 = CAMPURI_V2.get(o.get("id_produs") or "", set())

    # 1. zero
    if x is not None and float(x) == 0:
        numarare = camp in CAMPURI_NUMARARE
        if NEGOCIABIL.search(cit):
            o["valoare_num"], o["eticheta_libera"] = None, "negociabil"
            note.append("0 → „negociabil”: citatul spune că se negociază, nu că e gratuit")
        elif numarare and NELIMITAT.search(cit):
            o["valoare_num"], o["eticheta_libera"] = None, "nelimitat"
            note.append("0 → „nelimitat”")
        elif numarare:
            # un număr de operațiuni incluse: 0 doar dacă scrie „0”; o listă de servicii nu e un număr
            if not re.search(r"(?<![\d.,])0(?![\d.,]*\d)", cit):
                return None, "0 operațiuni incluse fără „0” în citat: e o listă de servicii, nu un număr"
        elif DOVADA_ZERO.search(cit):
            pass                              # „0 lei”, „gratuit”, „fără comision”, „inclus”: zero dovedit
        elif NELIMITAT.search(cit):
            o["valoare_num"], o["eticheta_libera"] = None, "nelimitat"
            note.append("0 → „nelimitat”")
        elif camp == "altele":
            return None, "0 pe `altele` fără „0 / gratuit” în citat: faptul e text (garanții, perioadă de grație)"
        else:
            return None, "0 nesusținut de citat: lipsește „0 / gratuit / fără comision / inclus”"

    # 2. dobânzi
    if camp in CAMPURI_DOBANDA and x is not None:
        if PENALIZATOARE.search(cit):
            return None, "dobândă penalizatoare (descoperit neautorizat / întârziere), nu dobânda produsului"
        poz = pozitie_cifra(float(x), cit)
        # doar propoziția în care stă cifra, până la 100 de caractere înapoi
        fereastra = re.split(r"[;\n]|\.\s", cit[max(0, poz - 100):poz])[-1] if poz is not None else ""
        m = CALIFICATIV.search(fereastra)
        if not m:
            # calificativul poate sta în condițiile citite de model („dobândă maximă, fără reduceri”,
            # „valoare minimă a intervalului standard”). NU în codul de scenariu: acolo MAX e
            # nivelul clientului (PROGRAM_BENEFICII_MAX), nu dobânda maximă.
            conds = " ".join(c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)
                             for c in (o.get("conditii") or []))
            m = CALIFICATIV.search(conds) or INTERVAL.search(conds)
        if m:
            cuv = m.group(1) or m.group(2)
            k = cuv.lower()
            tinta = ("dobanda_min" if k.startswith("minim") else
                     "dobanda_max" if k.startswith("maxim") else None)
            if tinta and tinta in v2:
                o["camp"] = tinta
                note.append(f"{camp} → {tinta}: citatul o numește „{cuv}”")
            else:
                eticheta = ("dobândă minimă" if k.startswith("minim") else
                            "dobândă maximă" if k.startswith("maxim") else "dobândă medie")
                o.setdefault("etichete_reguli", []).append(eticheta)
                note.append(f"etichetă „{eticheta}”: citatul o numește „{cuv}”")

    # 4. valoare derivată: cifra nu e scrisă ca atare în citat (ex. 85% finanțat → 15% avans)
    if o.get("valoare_num") is not None and float(o["valoare_num"]) != 0 and cit \
            and pozitie_cifra(float(o["valoare_num"]), cit) is None:
        o["metoda"] = "derivat"
        note.append("cifra nu apare literal în citat: e dedusă din el")

    # 3. unități
    if x is not None and o.get("unitate") == "ani" and PERIOADE_IN_LUNI.match(o.get("camp") or ""):
        o["valoare_num"], o["unitate"] = float(x) * 12, "luni"
        note.append(f"{float(x):g} ani → {float(x) * 12:g} luni")

    if note:
        o["reguli"] = note
    return o, None


def axa_libra(url: str, cod: str) -> tuple[str, str | None]:
    """
    Rolul unei pagini Libra pentru un produs Libra: ("principal", None),
    ("varianta", eticheta) sau ("exclus", motiv). Paginile nelistate sunt principale.
    """
    p = (AXA.get("produse") or {}).get(cod) or {}
    baza = url.split("#")[0]
    for u, motiv in (p.get("exclus") or {}).items():
        if baza == u:
            return "exclus", motiv
    for u, eticheta in (p.get("variante") or {}).items():
        if baza == u:
            return "varianta", eticheta
    return "principal", None
