"""Validarea inregistrarilor tipizate.

Patru stari, si distinctia dintre ele e tot ce conteaza:
  OK           valoarea e credibila si, unde se poate, confirmata de o sursa independenta
  SUSPECT      o verificare s-a facut si a eșuat, dar cauza nu se poate atribui
  SURSA_VECHE  extragerea e corecta, dar informatia publicata de banca e depasita
  NEVERIFICAT  verificarea NU s-a putut face (lipsa referinta)

A patra a fost adaugata pe 18 septembrie, dupa ce BNR a devenit inaccesibil. `stare`
pornea de la "OK" si doar o referinta o putea schimba, deci absenta unei verificari
arata identic cu o verificare trecuta: toate cele 13 valori de IRCC au ieșit "OK",
inclusiv cele de 4,05% care sunt clar vechi. O verificare care nu s-a putut face nu e
o confirmare.

Referinta pentru indici vine, in ordine: de la BNR (sursa de drept), altfel din
consensul paginilor bancare (`consens_indici`). Cu o referinta de mana a doua se
poate spune "difera de ce declara restul pietei", dar NU "e trimestrul 2025T3
expirat" — pentru asta trebuie seria trimestriala, care exista doar la BNR. De aceea
verdictele numesc sursa folosita, iar cu consens se opresc la SUSPECT.

Verificari:
  1. interval de plauzibilitate pe tip
  2. perioada de valabilitate declarata in text acopera ziua de azi?
  3. incrucisare cu BNR (IRCC, ROBOR, EURIBOR), pe indicele in vigoare azi
  4. indicele implicit: unde pagina arata si totalul si marja, total - marja = indicele
     pe care il foloseste efectiv banca
  5. invariant DAE >= dobanda nominala, pe aceeasi pagina
  6. consistenta aritmetica: indice + marja = rata nominala
"""
import re
from collections import defaultdict
from datetime import date

from .bnr_indici import (ircc_in_vigoare, ircc_pentru_perioada,
                         ircc_ultim_aplicabil, perioada_aplicare)

# toleranta la comparatii procentuale (puncte procentuale)
TOL = 0.05
# abatere peste care considerăm ca sursa e invechita, nu doar imprecisa
PRAG_VECHI = 0.5

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
    # promotie de plata in rate; rata e 0% prin definitie, orice altceva e o eroare
    "rate_fara_dobanda": (0.0, 0.0),
}

NUM = r"\d{1,3}(?:[.,]\d{1,3})?"
SUP = r"[*†‡°·]{0,3}"
IDX = r"(?:IRCC|EURIBOR|ROBOR)"

# --- perioada de valabilitate declarata de pagina
# "IRCC valabil în perioada 01.04.2026 – 30.06.2026 este 5,58%"
# "IRCC aplicabil în perioada 01.07 - 30.09.2026"  (anul lipseste de la prima data)
RE_PERIOADA = re.compile(
    r"(?:valabil|aplicabil)\w*\s*(?:în|in|pentru)?\s*perioada\s*"
    r"(\d{1,2})\.(\d{1,2})\.?(\d{4})?\s*[-–—]\s*(\d{1,2})\.(\d{1,2})\.(\d{4})", re.I)
# "*IRCC valabil de la 01.07.2026: 5.56%" — interval deschis
RE_VALABIL_DE_LA = re.compile(
    r"valabil\w*\s*(?:de\s+la|din)\s*(\d{1,2})\.(\d{1,2})\.(\d{4})", re.I)

# --- dovada structurala ca rata afisata ESTE suma indice + marja
# Nu e suficient ca marja si rata sa apara pe aceeasi linie: forma obisnuita din piata
# e "4,89% fixă în primii 3 ani, apoi variabilă IRCC + 2,10%", unde scaderea nu
# inseamna nimic. De aceea cerem una din cele doua forme explicite:
#   A: "9.06% (IRCC + 3.5%)"          total, apoi indicele si marja in paranteza
#   B: "3% + IRCC (8.68%)"            marja, apoi totalul in paranteza
RE_IMPLICIT_A = re.compile(
    rf"({NUM})\s*%{SUP}\s*\(\s*[^()]{{0,90}}?({IDX})[^()]{{0,90}}?\+\s*({NUM})\s*%", re.I)
RE_IMPLICIT_B = re.compile(
    rf"({NUM})\s*%{SUP}\s*%?\s*\+\s*({IDX})[^()]{{0,25}}?\(\s*({NUM})\s*%\s*\)", re.I)

TIP_INDICE = {"IRCC": "ircc_valoare", "EURIBOR": "euribor_valoare",
              "ROBOR": "robor_valoare"}


def _numar(text):
    try:
        return float(text.replace(",", "."))
    except (ValueError, AttributeError):
        return None


def _referinte_bnr(indici, azi):
    """Valorile de referinta in vigoare AZI, nu ultimele publicate."""
    ref, meta = {}, {}
    ircc = (indici or {}).get("ircc", {}) or {}
    trimestrial = ircc.get("trimestrial") or []
    in_vigoare = ircc_in_vigoare(trimestrial, azi)
    if not in_vigoare:
        # BNR nu a publicat inca trimestrul care se aplica azi. Folosim ultimul
        # aplicabil, dar marcam referinta ca expirata: pe baza ei nu putem nici
        # confirma, nici acuza o banca de date vechi.
        in_vigoare = ircc_ultim_aplicabil(trimestrial, azi)
        meta["ircc_referinta_expirata"] = bool(in_vigoare)
    if in_vigoare:
        ref["ircc_valoare"] = in_vigoare["valoare"]
        meta["ircc"] = in_vigoare
    meta["ircc_trimestrial"] = trimestrial

    zile = (indici or {}).get("robid_robor", {}).get("zile") or []
    if zile:
        robor = zile[0].get("robor", {})
        # comparam cu 3M, scadenta cel mai des citata in ofertele de credit
        if "3M" in robor:
            ref["robor_valoare"] = robor["3M"]
        meta["robor_toate"] = robor
    return ref, meta


# cate banci independente trebuie sa declare aceeasi valoare de indice ca s-o credem
# in lipsa referintei BNR. Trei, nu doua: doua banci pot copia aceeasi pagina veche.
BANCI_MIN_CONSENS = 3


def consens_indici(inregistrari):
    """{tip_indice: (valoare, proveniența)} din ce declara paginile bancare.

    Referinta de drept e BNR. Cand descarcarea de la BNR lipseste, alternativa la a
    nu verifica nimic e consensul intre surse independente — masurat pe 18
    septembrie, cand BNR a raspuns cu ERR_CONNECTION_CLOSED si toate cele 13 valori
    de IRCC au ieșit necontrolate.

    NU prin unanimitate, care nu exista niciodata: paginile vechi rămân publicate,
    deci IRCC apărea ca 5,56 (trei banci), 5,58 (una) si 4,05 (una). Regula e
    valoarea declarata de cele mai multe banci, cu minimum trei independente.

    E o referinta mai slaba decat BNR si se foloseste ca atare: pe baza ei se poate
    spune "difera de ce declara restul pietei", nu "e trimestrul 2025T3 expirat" —
    pentru asta ar trebui seria trimestriala, care vine doar de la BNR.
    """
    pe_tip = defaultdict(lambda: defaultdict(set))
    for r in inregistrari:
        if r["tip_rata"] in TIP_INDICE.values() and r.get("valoare") is not None:
            pe_tip[r["tip_rata"]][r["valoare"]].add(r["banca"])
    out = {}
    for tip, pe_valoare in pe_tip.items():
        valoare, banci = max(pe_valoare.items(), key=lambda kv: len(kv[1]))
        if len(banci) >= BANCI_MIN_CONSENS:
            out[tip] = (valoare, f"consens {len(banci)} bănci "
                                 f"({', '.join(sorted(banci))}), fără BNR")
    return out


def _perioada_din_text(text):
    """(start, final) declarate de pagina; final None = interval deschis."""
    m = RE_PERIOADA.search(text or "")
    if m:
        z1, l1, a1, z2, l2, a2 = m.groups()
        an2 = int(a2)
        # "01.07 - 30.09.2026": anul lipseste de la prima data, il luam de la a doua
        an1 = int(a1) if a1 else an2
        try:
            return date(an1, int(l1), int(z1)), date(an2, int(l2), int(z2))
        except ValueError:
            return None
    m = RE_VALABIL_DE_LA.search(text or "")
    if m:
        z, l, a = m.groups()
        try:
            return date(int(a), int(l), int(z)), None
        except ValueError:
            return None
    return None


def _indici_impliciti(text):
    """[(nume_indice, valoare_implicita, total, marja)] din formele explicite."""
    out = []
    for m in RE_IMPLICIT_A.finditer(text or ""):
        total, nume, marja = _numar(m.group(1)), m.group(2).upper(), _numar(m.group(3))
        if total is not None and marja is not None:
            out.append((nume, round(total - marja, 4), total, marja))
    for m in RE_IMPLICIT_B.finditer(text or ""):
        marja, nume, total = _numar(m.group(1)), m.group(2).upper(), _numar(m.group(3))
        if total is not None and marja is not None:
            out.append((nume, round(total - marja, 4), total, marja))
    return [x for x in out if 0.5 <= x[1] <= 12.0]


def _trimestrul_valorii(trimestrial, valoare):
    """Eticheta si intervalul de aplicare al trimestrului cu aceasta valoare IRCC."""
    for rand in trimestrial or []:
        if abs(rand.get("valoare", -1) - valoare) <= TOL:
            per = perioada_aplicare(rand.get("perioada"))
            if per:
                return rand["perioada"], per
    return None, None


def _zi(d):
    return d.strftime("%d.%m.%Y")


def valideaza(inregistrari, indici_bnr=None, euribor_referinta=None, azi=None):
    """Returneaza (inregistrari adnotate, sumar)."""
    azi = azi or date.today()
    ref, meta = _referinte_bnr(indici_bnr, azi)
    ref_expirata = bool(meta.get('ircc_referinta_expirata'))
    if euribor_referinta:
        ref["euribor_valoare"] = euribor_referinta
    trimestrial = meta.get("ircc_trimestrial") or []

    # Referinta de rezerva, doar pentru indicii pe care BNR nu i-a dat. `din_consens`
    # tine minte care referinta e de mana a doua, ca verdictele sa spuna asta.
    din_consens = {}
    for tip, (valoare, provenienta) in consens_indici(inregistrari).items():
        if tip not in ref:
            ref[tip] = valoare
            din_consens[tip] = provenienta
    meta["referinte_din_consens"] = din_consens

    pe_pagina = defaultdict(list)
    pe_linie = defaultdict(list)
    for r in inregistrari:
        pe_pagina[r["sursa_url"]].append(r)
        pe_linie[(r["sursa_url"], r["text_sursa"])].append(r)

    for r in inregistrari:
        verificari = []
        stare = "OK"

        # 1. interval de plauzibilitate
        lo, hi = INTERVALE.get(r["tip_rata"], (0.0, 100.0))
        if not lo <= r["valoare"] <= hi:
            stare = "SUSPECT"
            verificari.append(f"in afara intervalului {lo}-{hi}% pentru {r['tip_rata']}")

        # 2. perioada declarata de pagina (doar pentru valorile de indice)
        expirata = viitoare = False
        dist_perioada = None   # cat de bine se potriveste valoarea cu trimestrul declarat
        per = _perioada_din_text(r["text_sursa"]) if r["tip_rata"].endswith("_valoare") else None
        if per:
            start, final = per
            if final and final < azi:
                expirata = True
                verificari.append(
                    f"pagina declara valoarea pentru {_zi(start)}-{_zi(final)}, "
                    f"perioada incheiata acum {(azi - final).days} zile")
                # Valoarea se potriveste cu trimestrul pe care pagina il declara?
                # Aici se separa doua situatii care arata la fel pe magnitudine:
                #   BRD  5,58% pentru 01.04-30.06.2026 -> se potriveste => chiar e veche
                #   Nexent 5,56% pentru 01.07-30.09.2025 -> NU se potriveste (era 5,55%),
                #          iar valoarea e cea in vigoare azi => e o eroare de an in text
                potrivit = ircc_pentru_perioada(trimestrial, start, final)
                if potrivit and abs(potrivit["valoare"] - r["valoare"]) <= TOL:
                    dist_perioada = abs(potrivit["valoare"] - r["valoare"])
                    verificari.append(
                        f"valoarea era corecta pentru acea perioada "
                        f"(BNR {potrivit['perioada']} = {potrivit['valoare']}%)")
            elif start > azi:
                viitoare = True
                stare = "SUSPECT"
                verificari.append(
                    f"valoare anuntata pentru {_zi(start)}, perioada nu a inceput")
            else:
                verificari.append(
                    f"perioada declarata de pagina ({_zi(start)}-"
                    f"{_zi(final) if final else 'fara termen'}) acopera ziua de azi")

        # 3. incrucisare cu BNR
        if ref_expirata and r["tip_rata"] == "ircc_valoare":
            ic = meta.get("ircc") or {}
            verificari.append(
                f"verificare neconcludenta: BNR nu a publicat inca trimestrul aplicabil "
                f"azi; ultima referinta e {ic.get('perioada')} = {ic.get('valoare')}%, "
                f"aplicabila pana la {ic.get('aplicabil_pana_la')}")
        elif r["tip_rata"] in ref:
            asteptat = ref[r["tip_rata"]]
            # Referinta poate fi BNR sau consensul paginilor; verdictul o numește pe
            # cea folosita. Fara asta, un text ar fi spus "difera de BNR" tocmai
            # cand BNR era inaccesibil.
            sursa_ref = din_consens.get(r["tip_rata"]) or "BNR"
            abatere = abs(r["valoare"] - asteptat)
            eticheta, interval = _trimestrul_valorii(trimestrial, r["valoare"])
            e_trimestru_incheiat = bool(eticheta and interval[1] < azi)
            unde = (f"{r['valoare']}% e indicele BNR {eticheta}, aplicabil "
                    f"{_zi(interval[0])}-{_zi(interval[1])}") if eticheta else ""

            # Valoarea se potriveste mai bine cu trimestrul declarat decat cu cel in
            # vigoare? Ambele pot intra in toleranta (Nexent: 5,56% e la 0,01 de
            # trimestrul declarat si la 0,00 de cel curent), deci decide cine e mai
            # aproape, nu daca intra in toleranta.
            coerenta_cu_perioada = dist_perioada is not None and dist_perioada < abatere

            if expirata and abatere <= TOL and not coerenta_cu_perioada:
                # perioada declarata e incheiata, valoarea coincide cu cea de azi si NU
                # se potriveste cu trimestrul declarat: greseala e in eticheta perioadei,
                # nu in date (Nexent scrie 2025 in loc de 2026 intr-o nota de subsol)
                verificari.append(
                    f"confirmat cu {sursa_ref} ({asteptat}%) — perioada din text pare o "
                    f"eroare de an, valoarea e cea in vigoare")
            elif expirata:
                # NU spunem "confirmat": valoarea se refera la un trimestru incheiat.
                stare = "SURSA_VECHE"
                verificari.append(f"in vigoare azi: {asteptat}%")
            elif abatere <= TOL:
                verificari.append(f"confirmat cu {sursa_ref} ({asteptat}%)")
            elif r["tip_rata"] == "robor_valoare" and any(
                    abs(r["valoare"] - v) <= TOL
                    for v in (meta.get("robor_toate") or {}).values()):
                verificari.append(f"confirmat cu {sursa_ref} (alta scadenta ROBOR)")
            elif e_trimestru_incheiat:
                # Criteriul tare: valoarea se potriveste exact cu un trimestru incheiat
                # din seria BNR. Mai precis decat orice prag de magnitudine, fiindca
                # trimestrele consecutive difera uneori cu doar 0,02 p.p.
                stare = "SURSA_VECHE"
                verificari.append(
                    f"{unde} — trimestru incheiat; in vigoare azi: {asteptat}%")
            elif abatere > PRAG_VECHI:
                stare = "SURSA_VECHE"
                verificari.append(
                    f"difera de {sursa_ref} cu {abatere:.2f} p.p. ({asteptat}%) "
                    f"-> informatie probabil depasita pe site")
            elif not viitoare:
                stare = "SUSPECT"
                verificari.append(f"difera de {sursa_ref} cu {abatere:.2f} p.p.")
        elif r["tip_rata"] in TIP_INDICE.values():
            # Valoarea e un indice de piata, dar N-AVEM referinta BNR pentru el.
            # Pana la 18 septembrie asta trecea drept "OK": starea porneste de la OK
            # si doar o referinta o poate schimba. Efectul, cand BNR a raspuns cu
            # ERR_CONNECTION_CLOSED: toate cele 13 valori de IRCC au ieșit "OK",
            # inclusiv cele de 4,05% si 5,58% care sunt clar vechi, iar constatarea
            # despre pagina Libra a dispărut fara nicio alarma.
            # O verificare care nu s-a putut face NU e o confirmare.
            stare = "NEVERIFICAT"
            verificari.append(
                f"fara referinta BNR pentru {r['tip_rata']}: verificarea de "
                f"prospețime nu s-a putut face")

        r["verificari"] = verificari
        r["stare"] = stare

    # 4. indicele implicit: total - marja, doar din formele explicite
    for (_url, text), grup in pe_linie.items():
        for nume, implicit, total, marja in _indici_impliciti(text):
            tip = TIP_INDICE[nume]
            asteptat = ref.get(tip)
            nota = (f"indice implicit din pagina: {total}% - {marja}% = {implicit}% "
                    f"({nume})")
            stare_noua = None
            if asteptat is not None:
                if abs(implicit - asteptat) <= TOL:
                    nota += f"; coincide cu {nume} in vigoare ({asteptat}%)"
                else:
                    nota += f"; {nume} in vigoare e {asteptat}%"
                    eticheta, interval = (_trimestrul_valorii(trimestrial, implicit)
                                          if tip == "ircc_valoare" else (None, None))
                    if eticheta:
                        nota += (f" — {implicit}% e indicele BNR {eticheta}, aplicabil "
                                 f"{_zi(interval[0])}-{_zi(interval[1])}")
                    # acelasi criteriu tare ca la verificarea directa: potrivirea exacta
                    # cu un trimestru incheiat bate orice prag de magnitudine (Libra
                    # foloseste 5,68% = trimestrul 01.01-31.03.2026, la doar 0,12 p.p.
                    # de valoarea curenta, deci sub PRAG_VECHI)
                    if (eticheta and interval[1] < azi) or abs(implicit - asteptat) > PRAG_VECHI:
                        stare_noua = "SURSA_VECHE"
                    elif tip in din_consens:
                        # Referinta e consensul pietei, nu BNR, deci NU putem spune
                        # "e trimestrul 2025T3 expirat" — pentru asta ar trebui seria
                        # trimestriala. Iar 0,12 p.p. e prea putin pentru un prag de
                        # magnitudine: proiectul a respins deja "vechime dupa marime"
                        # in favoarea potrivirii exacte cu un trimestru.
                        #
                        # Ce putem spune: o verificare s-a facut si a eșuat, dar cauza
                        # nu se poate atribui cu autoritate. Adica exact definitia lui
                        # SUSPECT. Cazul care conteaza: pagina Libra de credit de nevoi
                        # personale calculeaza 8,68% = 3,0% + 5,68%, iar trei alte banci
                        # publica 5,56%.
                        stare_noua = "SUSPECT"
                        nota += (" — aritmetica paginii nu se potrivește cu indicele "
                                 "declarat de restul pieței; de verificat manual")
            for x in grup:
                x["verificari"].append(nota)
                x["indice_implicit"] = {"indice": nume, "valoare": implicit}
                if stare_noua and x["stare"] == "OK":
                    x["stare"] = stare_noua

    # 5. invariant DAE >= nominala, pe aceeasi pagina
    for _url, grup in pe_pagina.items():
        dae = [x for x in grup if x["tip_rata"] == "dae"]
        nom = [x for x in grup if x["tip_rata"] == "nominala" and x["valoare"] > 0]
        if dae and nom and max(x["valoare"] for x in dae) < min(x["valoare"] for x in nom):
            for x in dae:
                x["stare"] = "SUSPECT"
                x["verificari"].append(
                    "DAE mai mic decat dobanda nominala de pe aceeasi pagina "
                    "(imposibil: DAE include comisioanele)")

    # 6. consistenta aritmetica: IRCC + marja = nominala
    ircc_ref = ref.get("ircc_valoare")
    if ircc_ref:
        for _url, grup in pe_pagina.items():
            noms = [x for x in grup if x["tip_rata"] == "nominala"]
            for m in grup:
                if not _marja_peste_ircc(m):
                    continue
                asteptat = ircc_ref + m["valoare"]
                if [n for n in noms if abs(n["valoare"] - asteptat) <= 0.1]:
                    m["verificari"].append(
                        f"consistent aritmetic: IRCC {ircc_ref}% + marja "
                        f"{m['valoare']}% = {asteptat:.2f}% (regasit in pagina)")

    sumar = defaultdict(int)
    for r in inregistrari:
        sumar[r["stare"]] += 1
        if any("confirmat cu" in v for v in r["verificari"]):
            sumar["confirmate_cu_bnr"] += 1
        if any("consistent aritmetic" in v for v in r["verificari"]):
            sumar["consistente_aritmetic"] += 1
        if r.get("indice_implicit"):
            sumar["cu_indice_implicit"] += 1
    if ref_expirata:
        sumar["referinta_ircc_expirata"] = 1
    return inregistrari, dict(sumar)


def _marja_peste_ircc(rec):
    """Marja sta peste IRCC? 'marja_fixa' nu spune peste ce indice sta.

    Fara verificarea asta, o marja peste EURIBOR (Patria: '+ 2,20% marjă fixă' dupa
    'Euribor 6 luni') era adunata cu IRCC si putea produce o confirmare falsa.
    """
    if rec["tip_rata"] == "marja_ircc":
        return True
    if rec["tip_rata"] != "marja_fixa":
        return False
    text = (rec.get("text_sursa") or "").upper()
    if "IRCC" in text:
        # linia poate cita ambii indici (Patria pune lei si euro pe acelasi rand);
        # verificarea se auto-valideaza oricum, raportand doar cand suma se regaseste
        # efectiv in pagina, iar aritmetica e scrisa explicit in nota
        return True
    return "EURIBOR" not in text and "ROBOR" not in text
