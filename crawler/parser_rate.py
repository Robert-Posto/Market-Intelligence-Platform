"""Transforma liniile de text extrase in inregistrari tipizate.

Principiul: conservator. Emite o valoare tipizata doar cand tiparul e neambiguu.
Altfel marcheaza linia cu un motiv — ca sa putem masura exact cat acopera parsarea
determinista si unde e nevoie de LLM, in loc sa ghicim.

Distinctia critica pe care o rezolva: "IRCC + 2,1%" (marja) vs "IRCC = 5,56%" (valoare).
Un parser naiv le confunda, iar eroarea e silentioasa.
"""
import re

NUM = r"\d{1,3}(?:[.,]\d{1,3})?"
# marcaje de nota de subsol lipite de procent: "2,20%* + IRCC", "7.95%** "
# fara ele, tiparele de marja nu se potrivesc si valoarea ajunge etichetata nominala
SUP = r"[*†‡°·¹²³⁴]{0,3}"


def numar(text, ca_procent=True):
    """'5,84' -> 5.84 ; '20,000' -> 20000.0 ; gestioneaza ambele formate zecimale.

    ca_procent=True adauga un control de bun-sens: daca interpretarea "separator de
    mii" produce un procent imposibil (>100), atunci virgula era zecimala.
    Cazul real care a impus asta: "EURIBOR 6 luni 2,568%" era citit ca 2568%.
    """
    t = text.strip()
    if "," in t and "." in t:
        # ultimul separator e cel zecimal
        if t.rindex(".") > t.rindex(","):
            t = t.replace(",", "")
        else:
            t = t.replace(".", "").replace(",", ".")
    elif "," in t:
        parte = t.split(",")[-1]
        if len(parte) == 3:
            # ambigu: "2,568" poate fi 2568 (mii, format englez) sau 2.568 (zecimal)
            ca_mii = t.replace(",", "")
            try:
                t = t.replace(",", ".") if ca_procent and float(ca_mii) > 100 else ca_mii
            except ValueError:
                t = ca_mii
        else:
            t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


# ------------------------------------------------- tipare neambigue (ordinea conteaza)
# fiecare: (tip_rata, regex compilat, indexul grupului cu valoarea)
TIPARE = [
    # --- valoarea indicilor de referinta
    # "IRCC = 5,56%" · "IRCC valabil ...: 5.56%" · "valoarea de 4.06%" · "este 5,58%"
    ("ircc_valoare", re.compile(
        rf"IRCC\b[^+%]{{0,70}}?(?:=|:|valoarea\s+de|este|egal\s+cu)\s*({NUM})\s*%", re.I), 1),
    # rand de tabel: "IRCC 01.07.2026<tab>5.56000%"
    ("ircc_valoare", re.compile(
        rf"IRCC\b[^+%]{{0,30}}?\d{{2}}\.\d{{2}}\.\d{{4}}\s*({NUM})\s*%", re.I), 1),
    # valoare in paranteza: "Indice de referință IRCC (...) (5,56%) + 4,77% marjă fixă"
    ("ircc_valoare", re.compile(rf"IRCC[^()]{{0,140}}?\(\s*({NUM})\s*%\s*\)", re.I), 1),
    ("euribor_valoare", re.compile(
        rf"EURIBOR[^()+%]{{0,40}}?\(\s*({NUM})\s*%\s*\)", re.I), 1),
    ("euribor_valoare", re.compile(
        rf"EURIBOR[^+%]{{0,70}}?(?:=|:|valoarea\s+de|este|egal\s+cu)\s*({NUM})\s*%", re.I), 1),
    ("euribor_valoare", re.compile(
        rf"EURIBOR\s*(?:\d+\s*(?:luni|M))\s+({NUM})\s*%", re.I), 1),
    ("robor_valoare", re.compile(
        rf"ROBOR[^+%]{{0,70}}?(?:=|:|valoarea\s+de|este|egal\s+cu)\s*({NUM})\s*%", re.I), 1),

    # --- marje peste indice
    ("marja_ircc", re.compile(rf"IRCC(?:\s*\d*[MT])?\s*\+\s*({NUM})\s*%", re.I), 1),
    # %? tolereaza procentul dublu din "4.50% % + IRCC" (greseala de tipar pe site)
    ("marja_ircc", re.compile(rf"({NUM})\s*%{SUP}\s*%?\s*\+\s*IRCC", re.I), 1),
    ("marja_euribor", re.compile(rf"EURIBOR(?:\s*\d*[MT])?\s*\+\s*({NUM})\s*%", re.I), 1),
    ("marja_euribor", re.compile(rf"({NUM})\s*%{SUP}\s*\+\s*EURIBOR", re.I), 1),
    ("marja_robor", re.compile(rf"ROBOR(?:\s*\d*[MT])?\s*\+\s*({NUM})\s*%", re.I), 1),
    # marja in puncte procentuale: "IRCC + Marjă Fixă* 3,25 p.p."
    ("marja_ircc", re.compile(
        rf"IRCC[^%]{{0,45}}?marj[ăa][^%\d]{{0,12}}({NUM})\s*p\.?\s*p\.?", re.I), 1),
    ("marja_euribor", re.compile(
        rf"EURIBOR[^%]{{0,45}}?marj[ăa][^%\d]{{0,12}}({NUM})\s*p\.?\s*p\.?", re.I), 1),
    # marja declarata separat: "+ 4,77% marjă fixă" · "Marja fixă a dobânzii<tab>2,90%"
    ("marja_fixa", re.compile(rf"\+\s*({NUM})\s*%\s*marj[ăa]", re.I), 1),
    # [^%\d] interzice traversarea unei alte cifre: in "Marjă Fixă** 5,2 p.p.<tab>FIXĂ
    # 3 ani 6% pe an" vechea versiune sarea peste 5,2 p.p. si raporta 6% drept marja,
    # desi 6% e rata fixa pe 3 ani (caz real Vista Bank)
    ("marja_fixa", re.compile(rf"marj[ăa]\s+fix[ăa][^%\d]{{0,30}}?({NUM})\s*%", re.I), 1),

    # --- DAE. \d? acopera nota de subsol: "DAE2 este 10,82% pentru lei"
    ("dae", re.compile(rf"\bDAE\d?\b[^%]{{0,45}}?({NUM})\s*%", re.I), 1),
    ("dae", re.compile(
        rf"dob[âa]nd[ăa]\s+anual[ăa]\s+efectiv[ăa][^%]{{0,40}}?({NUM})\s*%", re.I), 1),
    ("dae", re.compile(rf"({NUM})\s*%\s*DAE", re.I), 1),

    # --- cashback
    ("cashback", re.compile(rf"({NUM})\s*%\s*cashback", re.I), 1),
    ("cashback", re.compile(rf"cashback[^%]{{0,25}}?({NUM})\s*%", re.I), 1),

    # --- comisioane si taxe exprimate procentual
    # "Comisionul anual de administrare: Credite in lei: 200 LEI pe an, in Euro: 0.2% p.a."
    # Distanta e mare, dar cerand SI "comision" inainte SI "p.a." dupa, tiparul ramane
    # ingust. Fara el, 0.2% ajungea dobanda nominala (caz real Vista Bank).
    ("comision_procent", re.compile(
        rf"comision[^%]{{0,120}}?({NUM})\s*%\s*p\.?\s*a\b", re.I), 1),
    ("comision_procent", re.compile(rf"comision[^%]{{0,45}}?({NUM})\s*%", re.I), 1),
    ("comision_procent", re.compile(rf"({NUM})\s*%\s*comision", re.I), 1),
    ("comision_procent", re.compile(rf"({NUM})\s*%\s*tax[ăa]", re.I), 1),
    ("comision_procent", re.compile(rf"tax[ăa][^%]{{0,35}}?({NUM})\s*%", re.I), 1),

    # --- dobanda nominala
    ("nominala", re.compile(rf"dob[âa]nd[ăa][^%]{{0,85}}?({NUM})\s*%", re.I), 1),
    ("nominala", re.compile(
        rf"rat[ăa]\s+(?:\w+\s+){{0,2}}(?:a\s+)?dob[âa]nzii[^%]{{0,45}}?({NUM})\s*%", re.I), 1),
    # ordine inversa: cifra inaintea termenului ("0% dobanda", "1% dobândă anuală")
    ("nominala", re.compile(rf"({NUM})\s*%\s*(?:p\.?\s*a\.?\s*)?dob[âa]nd", re.I), 1),
    ("nominala", re.compile(rf"rat[ăa]\s+fix[ăa][^%]{{0,25}}?({NUM})\s*%", re.I), 1),

    # --- engleza (Revolut si alte entitati care publica in engleza)
    ("nominala", re.compile(rf"({NUM})\s*%\s*(?:p\.?\s*a\b|per\s+annum)", re.I), 1),
    ("nominala", re.compile(rf"({NUM})\s*%\s*APY\b", re.I), 1),
    ("nominala", re.compile(rf"interest[^%]{{0,30}}?({NUM})\s*%", re.I), 1),
    ("comision_procent", re.compile(rf"fee[^%]{{0,30}}?({NUM})\s*%", re.I), 1),
    ("comision_procent", re.compile(rf"({NUM})\s*%\s*fee", re.I), 1),
]

# Procente care NU sunt rate de dobanda. Fiecare tipar vine dintr-un caz real
# intalnit in crawl, nu din presupuneri.
EXCLUDERI = [
    (r"avans", "avans, nu rata"),
    (r"din\s+(?:dob[âa]nda\s+)?brut", "impozit pe venitul din dobanda"),
    (r"impozit", "impozit"),
    # doar cand procentul insusi e o reducere; "dobanda minima, cu toate reducerile
    # incluse: 5,79%" trebuie sa treaca
    (r"discount|reducere\s+(?:de|la)\s+dob|\d+[.,]?\d*\s*%\s*reducere",
     "discount comercial"),
    (r"[îi]ndator", "grad de indatorare"),
    (r"\bTVA\b", "TVA"),
    (r"100\s*%\s*on", "'100% online', nu o rata"),
    (r"din\s+(?:pre[țt]ul|valoarea|suma)", "procent din suma, nu rata"),
    (r"\bLTV\b", "LTV"),
    (r"subven[țt]i", "subventie de dobanda, nu rata"),
    (r"\bLIBOR\b", "exemplu explicativ cu LIBOR (indice retras)"),
    (r"rat[ăa]\s+de\s+garantare|garantare:", "rata de garantare, nu dobanda"),
    (r"cifra\s+de\s+afaceri", "procent din cifra de afaceri"),
    (r"puncte\s+bonus", "program de loializare"),
    (r"din\s+dob[âa]nda\s+acumulat|din\s+soldul", "penalizare/limita, nu rata"),
    (r"rat[ăa]\s+Lombard|a\s+cotat", "text explicativ despre ROBOR"),
    (r"marj[ăa][^.]{0,40}(?:curs|schimb\s+valutar)", "marja de curs valutar"),
    (r"conversie\s+valutar", "marja de conversie valutara"),
    (r"recupereze|ajutor\s+de\s+stat|\bgrant", "subventie/grant"),
    (r"retrager[ei][^.]{0,30}limita|o\s+singur[ăa]\s+retragere", "limita de retragere"),
]

# intervale plauzibile pe tip (Romania, 2026) — folosite pentru marcarea increderii
INTERVALE = {
    "nominala": (0.0, 40.0),
    "dae": (0.0, 50.0),
    "marja_ircc": (0.1, 20.0),
    "marja_euribor": (0.1, 20.0),
    "marja_robor": (0.1, 20.0),
    "marja_fixa": (0.1, 20.0),
    "ircc_valoare": (4.0, 8.0),
    "robor_valoare": (4.0, 9.0),
    "euribor_valoare": (1.5, 5.0),
    "cashback": (0.0, 10.0),
    "comision_procent": (0.0, 10.0),
    "rate_fara_dobanda": (0.0, 0.0),
}

# --- promotiile de tip "N rate fara dobanda"
# 0% de aici NU e rata dobanzii produsului, e o facilitate de plata in rate. Etichetate
# "nominala" dadeau citiri absurde ("ING credit card: dobanda nominala 0%"). Verificarea
# manuala a gasit 77 de astfel de inregistrari, 60 doar la TBI.
RE_PROMO_RATE = [
    re.compile(r"(\d{1,2})\s*(?:de\s+)?rate[^.%]{0,25}?0\s*%\s*dob", re.I),
    re.compile(r"(\d{1,2})\s*(?:de\s+)?rate\s*(?:lunare\s*)?f[ăa]r[ăa]\s*dob", re.I),
    re.compile(r"(\d{1,2})\s*(?:monthly\s+)?instal?ments?[^.%]{0,20}?0\s*%", re.I),
    re.compile(r"0\s*%\s*dob[âa]nd[ăa]?[^.]{0,30}?\brate\b", re.I),
    re.compile(r"\brate\s+f[ăa]r[ăa]\s+dob[âa]nd", re.I),
    re.compile(r"interest[- ]free\s+instal?ments?", re.I),
]

# cuvinte care anunta o masura nouă; opresc propagarea tipului pe rand
RE_ETICHETA_NOUA = re.compile(
    r"dob[âa]nd|comision|tax[ăa]|\bDAE\b|IRCC|EURIBOR|ROBOR|marj|cashback"
    r"|\bfee\b|interest|\bAPY\b|avans|\bLTV\b", re.I)

# Intervalul de rata, in toate formele pe care il scriu bancile. Doar prima forma
# ("de la X la Y") era acoperita, iar celelalte se pierdeau — cu efect direct pe
# comparatie: retineam doar capatul de jos, deci ING apărea in tabel cu 5,99% cand
# pagina scrie "intre 5,99% - 15,99%", iar Raiffeisen cu 5,95% din "5.95% si 18.35%".
# Cinci banci din sapte pe randul de credit de nevoi personale erau asa, deci randul
# sugera ca ele sunt cele mai ieftine cand de fapt le retinusem cel mai bun caz.
RE_INTERVAL = re.compile(
    rf"de\s+la\s+({NUM})\s*%\s+(?:la|p[âa]n[ăa]\s+la)\s+({NUM})\s*%"
    rf"|de\s+la\s+({NUM})\s*%\s*[-–—]\s*({NUM})\s*%"
    # "intre 5,99% - 15,99%", "cuprinsa intre 5.95% si 18.35%", "intre 7,40% – 12,40%"
    rf"|[îi]ntre\s+({NUM})\s*%\s*(?:[-–—]|[șs]i|p[âa]n[ăa]\s+la)\s*({NUM})\s*%", re.I)
RE_ORICE_PROC = re.compile(rf"({NUM})\s*%")
RE_PERIOADA = re.compile(
    r"(prim(?:ii|ul|ele)\s+\d+\s+(?:ani|an|luni)|pe\s+\d+\s+(?:ani|an|luni)"
    r"|\d+\s+(?:ani|luni)|pe\s+toat[ăa]\s+perioada)", re.I)
RE_MONEDA = re.compile(r"\b(lei|RON|EUR|euro|USD)\b", re.I)
# "marja% + IRCC (total%)" — paranteza contine rata totala, nu valoarea indicelui
RE_PARANTEZA_E_TOTAL = re.compile(
    rf"{NUM}\s*%\s*%?\s*\+\s*(?:IRCC|EURIBOR|ROBOR)", re.I)


def _limite_celule(linie):
    """[(start, end)] pentru fiecare celula separata de tab."""
    limite, poz = [], 0
    for bucata in linie.split("\t"):
        limite.append((poz, poz + len(bucata)))
        poz += len(bucata) + 1
    return limite


def _celula_lui(poz, limite):
    for i, (s, e) in enumerate(limite):
        if s <= poz <= e:
            return i
    return None


def _coloane_suplimentare(linie, gasite, acoperite):
    """Restul coloanelor din acelasi rand de tabel, cu tipul dat de eticheta.

    Problema rezolvata: tiparele se ancoreaza pe eticheta rândului ("DAE", "Marja
    fixa a dobanzii"), care apare o singura data. finditer gaseste o potrivire, deci
    se extragea doar prima coloana, iar restul rândului se pierdea:

        DAE 4<tab>8,91%<tab>8,04%<tab>6,96%<tab>5,49%   ->  se lua doar 8,91%

    Propagarea se face DOAR cand potrivirea porneste din celula de eticheta (0) si se
    incheie in prima celula de valori (1). Altfel un tip prins in celula de eticheta
    ar fi intins peste o coloana care inseamna altceva — cazul real Vista Bank, unde
    celula 0 da marja peste EURIBOR si celula 1 da rata fixa pe 3 ani.
    """
    limite = _limite_celule(linie)
    if len(limite) < 3:
        return []

    tip_rand = None
    for (s, e), g in zip(acoperite, gasite):
        if _celula_lui(s, limite) == 0 and _celula_lui(e, limite) == 1:
            tip_rand = g
            break
    if tip_rand is None:
        return []

    noi = []
    for idx in range(2, len(limite)):
        s, e = limite[idx]
        celula = linie[s:e]
        rest = RE_ORICE_PROC.sub(" ", celula).strip()
        # celula trebuie sa fie una de valori: fara eticheta nouă si fara text lung
        # (un "1,000 - 340,000 RON - 60 luni" inseamna ca am ieșit din zona de rate)
        if RE_ETICHETA_NOUA.search(rest) or len(rest) > 28:
            break
        for m in RE_ORICE_PROC.finditer(celula):
            val = numar(m.group(1))
            if val is None:
                continue
            if any(abs(val - g["valoare"]) < 0.001 for g in gasite + noi):
                continue
            rec = dict(tip_rand)
            rec["valoare"] = val
            rec["coloana"] = idx
            rec["nota_coloana"] = celula.strip()[:60] or None
            rec["incredere"] = _incredere(tip_rand["tip_rata"], val, linie)
            noi.append(rec)
            acoperite.append((s + m.start(), s + m.end()))
    return noi


def _incredere(tip, valoare, linie):
    lo, hi = INTERVALE.get(tip, (0.0, 100.0))
    if not lo <= valoare <= hi:
        return "scazuta"
    # o linie lunga si plina de cifre e mai probabil text de marketing
    if len(linie) > 200 and len(RE_ORICE_PROC.findall(linie)) > 4:
        return "medie"
    return "ridicata"


def parseaza_linie(linie, banca, categorie, url, titlu_pagina=None):
    """Returneaza (inregistrari, problema). problema != None => candidat pentru LLM."""
    jos = linie.lower()

    for tipar, _motiv in EXCLUDERI:
        if re.search(tipar, jos, re.I):
            return [], None  # exclus deliberat, nu e candidat pentru LLM

    # fara acest control, "4.50% + IRCC (10.18%)" ar raporta 10.18% drept valoare IRCC
    paranteza_e_total = bool(RE_PARANTEZA_E_TOTAL.search(linie))

    gasite, acoperite = [], []

    # Promotiile "N rate fara dobanda" se tipizeaza INAINTE de restul tiparelor: asa
    # deduplicarea pe valoare impiedica 0% sa mai ajunga si in "nominala".
    for rx in RE_PROMO_RATE:
        m = rx.search(linie)
        if not m:
            continue
        nr = None
        if m.groups() and m.group(1) and m.group(1).isdigit():
            nr = int(m.group(1))
        gasite.append({
            "banca": banca,
            "categorie": categorie,
            "produs": titlu_pagina,
            "tip_rata": "rate_fara_dobanda",
            "valoare": 0.0,
            "nr_rate": nr,
            "moneda": None,
            "perioada": None,
            "sursa_url": url,
            "text_sursa": linie[:300],
            "incredere": "ridicata",
        })
        acoperite.append(m.span())
        break

    for tip, regex, grup in TIPARE:
        if paranteza_e_total and tip.endswith("_valoare") and r"\(" in regex.pattern:
            continue
        for m in regex.finditer(linie):
            val = numar(m.group(grup))
            if val is None:
                continue
            # nu raporta acelasi procent de doua ori sub tipuri diferite
            if any(abs(val - g["valoare"]) < 0.001 for g in gasite):
                continue
            gasite.append({
                "banca": banca,
                "categorie": categorie,
                "produs": titlu_pagina,
                "tip_rata": tip,
                "valoare": val,
                "moneda": (RE_MONEDA.search(linie).group(1).upper()
                           if RE_MONEDA.search(linie) else None),
                "perioada": (RE_PERIOADA.search(linie).group(1)
                             if RE_PERIOADA.search(linie) else None),
                "sursa_url": url,
                "text_sursa": linie[:300],
                "incredere": _incredere(tip, val, linie),
            })
            acoperite.append(m.span())

    # restul coloanelor din acelasi rand de tabel
    if "\t" in linie and gasite:
        gasite.extend(_coloane_suplimentare(linie, gasite, acoperite))

    # interval "de la X% la Y%" pe aceeasi masura
    interval = RE_INTERVAL.search(linie)
    if interval and gasite:
        capete = [g for g in interval.groups() if g is not None]
        lo, hi = (numar(capete[0]), numar(capete[1])) if len(capete) == 2 else (None, None)
        # Un interval real are capatul mic scris PRIMUL. Ordinea inversa e semnul ca
        # potrivirea a prins doua cifre nelegate din propozitii diferite — la BRD
        # ieșea {min: 26,0, max: 16,9} dintr-un text despre cumularea cheltuielilor.
        # Se respinge, nu se sorteaza: daca ordinea e greșita, nu e un interval.
        if lo is not None and hi is not None and lo < hi:
            gasite[0]["interval"] = {"min": lo, "max": hi}

    # cate procente din linie au ramas neinterpretate?
    toate = list(RE_ORICE_PROC.finditer(linie))
    neatinse = [m for m in toate
                if not any(s <= m.start() and m.end() <= e for s, e in acoperite)]

    problema = None
    if toate and not gasite:
        problema = "procente prezente, dar niciun tipar cunoscut nu se potriveste"
    elif neatinse:
        # pragul era >= 2, deci o linie care pierdea EXACT un procent trecea in
        # silentiu. Asa ratam 48 de linii: 61 pierdeau valori, doar 13 erau raportate.
        problema = f"{len(neatinse)} procente neinterpretate in aceeasi linie"
    elif gasite and all(g["produs"] is None for g in gasite):
        problema = "valoare fara produs identificabil"

    return gasite, problema
