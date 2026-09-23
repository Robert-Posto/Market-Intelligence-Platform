"""Cât de recent și-a atins fiecare bancă lista de tarife publicată.

Rulare:  python scripts/vechime_documente.py
Ieșire:  output/VECHIME_DOCUMENTE.md

Datele vin din `Last-Modified`, strâns de sonda de schimbări (urme.json). Nu e
nevoie de nicio descarcare in plus — e informație pe care serverul o da oricum
la o cerere HEAD, si pe care o aruncam.

Intr-o comparatie de piața conteaza nu doar CE preț publica banca, ci si de cand
nu l-a mai atins. Dar intrebarea trebuie pusa exact, si prima versiune a
scriptului o pusese greșit:

  GRESIT: "cel mai vechi document de tarife al bancii".
          Bancile lasa pe site toate versiunile succesive — BRCI are "mai 2024"
          si "vers oct 2024" simultan, BCR are trei luni in paralel. Cel mai
          vechi document masoara adancimea arhivei, NU prospețimea prețurilor.

  CORECT: "cel mai NOU document de tarife al bancii".
          Aia spune de cand nu a mai publicat banca nimic nou.

Ce NU spune nici asa: `Last-Modified` e data fișierului pe server, nu data
deciziei comerciale. Si daca multe fișiere de la aceeasi origine au exact
aceeasi data, aceea e aproape sigur o operație in masa (migrare de site, copiere
de pe alt server), nu o republicare editoriala — raportul o semnaleaza, ca sa nu
fie citita ca o actualizare.
"""
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import unquote

RADACINA = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADACINA))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from crawler.urme import citeste_urme

IEȘIRE = RADACINA / "output" / "VECHIME_DOCUMENTE.md"

# Filtrul se aplica pe NUMELE fișierului, nu pe tot URL-ul, si cere idiomul unei
# liste de tarife. Cu "taxe" singur pe tot URL-ul, intra si
# "Click24Banking_PlataImpoziteTaxe.pdf" — un FAQ despre plata impozitelor prin
# internet banking, pe care raportul il dadea drept cea mai veche lista de
# tarife a BCR, din 2017.
RE_NUME_TARIF = re.compile(
    r"tarif|comisio|speze"
    r"|dobanzi|dobânzi|dobanzile"
    r"|lista[_\-\s%20]*de[_\-\s%20]*(taxe|dobanzi)", re.I)
# ...iar cateva cai spun singure ca nu e o lista de prețuri
RE_CALE_EXCLUSA = re.compile(r"/faq/|/blog/|/noutati|/presa|/campanii", re.I)
# de la cate fișiere cu exact aceeasi data devine suspecta o operație in masa
PRAG_GRUP = 3
# cat de departe pot fi data din nume si Last-Modified si sa zicem ca se
# potrivesc: Garanti a incarcat pe 13 noiembrie un fișier numit "...10-11-2025"
ZILE_POTRIVIRE = 14
# ...iar cand numele da doar luna, fereastra acopera toata luna plus marginea
ZILE_LUNA = 33

LUNI = ["ianuarie", "februarie", "martie", "aprilie", "mai", "iunie", "iulie",
        "august", "septembrie", "octombrie", "noiembrie", "decembrie"]
SCURT = ["ian", "feb", "mar", "apr", "mai", "iun", "iul", "aug", "sep", "oct",
         "noi", "dec"]
# Formele in care bancile pun data in numele fișierului. Ordinea conteaza: cea
# mai specifica intai, altfel "02062025" ar fi citit ca an 0206.
RE_ZI_LUNA_AN = re.compile(r"(?<!\d)(\d{2})[-._](\d{2})[-._](20\d{2})(?!\d)")
RE_AN_LUNA_ZI = re.compile(r"(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)")
RE_ZILUNAAN = re.compile(r"(?<!\d)(\d{2})(\d{2})(20\d{2})(?!\d)")
RE_LUNA_TEXT = re.compile(
    r"(?<![a-z])(" + "|".join(LUNI + SCURT) + r")(?![a-z])[-._%\s0-9]*?(20\d{2})",
    re.I)


def _data(valoare):
    try:
        return parsedate_to_datetime(valoare)
    except (TypeError, ValueError):
        return None


def data_din_nume(url):
    """Data pe care banca a scris-o in numele fișierului, ori None.

    Intoarce (data, precizie), unde precizia e "zi" sau "luna": "mai 2024" nu
    spune ziua, iar comparatia cu Last-Modified trebuie facuta atunci pe luna.
    Altfel "Lista Tarife PJ mai 2024", urcata pe 29 mai, ieșea drept dezacord
    intre nume si server — desi cele doua spun acelasi lucru.

    E o a doua sursa, independenta de server. Unde cele doua se potrivesc,
    `Last-Modified` nu mai e o presupunere — e confirmat de banca insasi. Unde
    difera, raportul le scrie pe amandoua, in loc sa aleaga una.
    """
    # Numele se decodeaza intai: "%20" devine "20" si se lipeste de cifre, deci
    # "mai%202024" arata ca "mai202024" si anul iesea 2020 in loc de 2024. A treia
    # data in proiect cand "%20" din numele descarcate strica o citire.
    nume = unquote(url.rsplit("/", 1)[-1])
    for tipar, ordine in ((RE_ZI_LUNA_AN, "zla"), (RE_AN_LUNA_ZI, "alz"),
                          (RE_ZILUNAAN, "zla")):
        m = tipar.search(nume)
        if not m:
            continue
        a, b, c = m.groups()
        zi, luna, an = ((int(a), int(b), int(c)) if ordine == "zla"
                        else (int(c), int(b), int(a)))
        if 1 <= zi <= 31 and 1 <= luna <= 12:
            try:
                return datetime(an, luna, zi, tzinfo=timezone.utc), "zi"
            except ValueError:
                pass
    m = RE_LUNA_TEXT.search(nume)
    if m:
        gasit = m.group(1).lower()
        luna = next((i for i, l in enumerate(LUNI, 1)
                     if l == gasit or l.startswith(gasit)), 0)
        if luna:
            return datetime(int(m.group(2)), luna, 1, tzinfo=timezone.utc), "luna"
    return None, None


def e_document_de_tarife(url):
    if RE_CALE_EXCLUSA.search(url):
        return False
    nume = url.rsplit("/", 1)[-1]
    return bool(RE_NUME_TARIF.search(nume))


def main():
    documente = citeste_urme().get("documente", {})
    azi = datetime.now(timezone.utc)

    randuri, fara_data = [], defaultdict(int)
    for url, r in documente.items():
        lm = _data((r.get("semnale") or {}).get("last_modified"))
        if not lm:
            if r.get("amprenta") and e_document_de_tarife(url):
                fara_data[r.get("banca")] += 1
            continue
        if not e_document_de_tarife(url):
            continue
        din_nume, precizie = data_din_nume(url)
        acord = None
        if din_nume:
            # Cand numele da doar luna, ziua presupusa e 1, deci fereastra
            # trebuie sa acopere toata luna — plus cateva zile inainte, fiindca
            # e normal sa publici pe 31 iulie lista care intra in vigoare pe 1
            # august. BCR face exact asta, si cu fereastra de zile ieșea
            # dezacord intre nume si server pentru un document corect.
            fereastra = ZILE_LUNA if precizie == "luna" else ZILE_POTRIVIRE
            acord = abs((lm - din_nume).days) <= fereastra
        randuri.append({"banca": r.get("banca"), "url": url, "data": lm,
                        "zile": (azi - lm).days, "din_nume": din_nume,
                        "acord": acord})

    if not randuri:
        print("nicio data de modificare in registru — ruleaza mai intai")
        print("  python scripts/sonda_schimbari.py")
        return

    pe_banca = defaultdict(list)
    for r in randuri:
        pe_banca[r["banca"]].append(r)

    # operațiile in masa: multe fișiere de la aceeasi banca cu exact aceeasi data
    grupuri = {}
    for banca, lista in pe_banca.items():
        c = Counter(r["data"].date() for r in lista)
        mari = {d: n for d, n in c.items() if n >= PRAG_GRUP}
        if mari:
            grupuri[banca] = mari

    ordonat = sorted(pe_banca.items(), key=lambda kv: min(r["zile"] for r in kv[1]))

    L = ["# Cât de recent și-a atins fiecare bancă lista de tarife", ""]
    L.append(f"Din `Last-Modified`, strâns de sonda de schimbări — informație pe")
    L.append(f"care serverul o dă oricum la un HEAD. {len(randuri)} documente de")
    L.append(f"tarife cu dată, la {len(pe_banca)} bănci.")
    L.append("")
    L.append("**Coloana care contează e „cel mai nou”.** Băncile lasă pe site toate")
    L.append("versiunile succesive (BRCI are „mai 2024” și „vers oct 2024”")
    L.append("simultan), deci cel mai *vechi* document măsoară adâncimea arhivei,")
    L.append("nu prospețimea prețurilor.")
    L.append("")
    L.append("Coloana **dovadă** e o verificare independentă: multe bănci pun data")
    L.append("în numele fișierului. Unde ea și `Last-Modified` se potrivesc (±14")
    L.append("zile), data nu mai e o presupunere despre server — e confirmată de")
    L.append("bancă. Unde diferă, scrie amândouă, fără să aleg una.")
    L.append("")
    L.append("| bancă | doc | cel mai nou | zile | dovadă | arhivă păstrată |")
    L.append("|---|---:|---|---:|---|---|")
    for banca, lista in ordonat:
        nou = min(lista, key=lambda r: r["zile"])
        vechi = max(lista, key=lambda r: r["zile"])
        if nou["acord"] is True:
            dovada = f"da, numele zice {nou['din_nume']:%Y-%m-%d}"
        elif nou["acord"] is False:
            dovada = f"**nu**: numele zice {nou['din_nume']:%Y-%m-%d}"
        else:
            dovada = "numele nu are dată"
        L.append(f"| {banca} | {len(lista)} | {nou['data']:%Y-%m-%d} "
                 f"| {nou['zile']} | {dovada} | {vechi['data']:%Y-%m-%d} "
                 f"({vechi['zile']} z) |")
    L.append("")

    cu_acord = [r for r in randuri if r["acord"] is True]
    fara_acord = [r for r in randuri if r["acord"] is False]
    L.append(f"Pe tot setul: {len(cu_acord)} documente în care cele două date se")
    L.append(f"potrivesc, {len(fara_acord)} în care nu, "
             f"{len(randuri) - len(cu_acord) - len(fara_acord)} fără dată în nume.")
    L.append("")
    if fara_acord:
        L.append("### Unde cele două date nu se potrivesc")
        L.append("")
        for r in sorted(fara_acord, key=lambda r: r["banca"])[:12]:
            L.append(f"- **{r['banca']}** · server {r['data']:%Y-%m-%d}, "
                     f"nume {r['din_nume']:%Y-%m-%d} — "
                     f"`{unquote(r['url'].rsplit('/', 1)[-1])[:64]}`")
        L.append("")

    if grupuri:
        L.append("## Atenție: date puse în masă")
        L.append("")
        L.append("Mai multe fișiere ale aceleiași bănci au **exact** aceeași dată.")
        L.append("Aceea e aproape sigur o operație în masă — migrare de site sau")
        L.append("copiere de pe alt server — nu o republicare editorială. Pentru")
        L.append("băncile de mai jos, data nu spune când s-au schimbat tarifele.")
        L.append("")
        for banca, mari in sorted(grupuri.items()):
            for d, n in sorted(mari.items()):
                L.append(f"- **{banca}**: {n} fișiere, toate cu {d}")
        L.append("")

    if fara_data:
        L.append("## Fără dată de la server")
        L.append("")
        L.append("Aici nu se poate spune nimic: serverul nu trimite `Last-Modified`,")
        L.append("ori îl pune la ora cererii (și atunci se aruncă — vezi")
        L.append("`crawler/urme.py`, `SECUNDE_STAMPILA`).")
        L.append("")
        for banca, n in sorted(fara_data.items(), key=lambda kv: -kv[1]):
            L.append(f"- {banca}: {n} documente de tarife")
        L.append("")

    IEȘIRE.write_text("\n".join(L), encoding="utf-8")

    print(f"{len(randuri)} documente de tarife cu dată, {len(pe_banca)} bănci")
    print(f"\n{'banca':<14} {'cel mai nou':>12} {'zile':>6}   arhiva")
    for banca, lista in ordonat:
        nou = min(lista, key=lambda r: r["zile"])
        vechi = max(lista, key=lambda r: r["zile"])
        semn = "  (date in masa)" if banca in grupuri else ""
        print(f"{banca:<14} {nou["data"]:%Y-%m-%d}     {nou['zile']:>6}   "
              f"pana la {vechi['zile']:>5} z{semn}")
    if fara_data:
        print(f"\nfără Last-Modified: {sum(fara_data.values())} documente de tarife "
              f"la {len(fara_data)} bănci ({', '.join(sorted(fara_data))})")
    print(f"\n>> {IEȘIRE.relative_to(RADACINA)}")


if __name__ == "__main__":
    main()
