#!/usr/bin/env python3
"""
referinta.py — din toate valorile extrase pentru un câmp, valoarea de referință.

    from referinta import Fise, alege
    fise = Fise()
    for camp_cheie in fise.campuri_cheie("CARD_DEBIT_FREE"):
        rez = alege(fise, "CARD_DEBIT_FREE", camp_cheie, randuri)

`randuri` sunt rânduri din comparatie_libra pentru o bancă și un produs Libra, ca dict-uri, cu
`rol` și `url` din surse_libra. Funcțiile de aici nu știu de baza de date: consolideaza_referinta.py
le dă rândurile și scrie rezultatul în valori_referinta.

CUM SE ALEGE (fise_produse.json are câmpurile cheie și varianta de referință a fiecăruia)

  1. Doar rândurile neambigue ale câmpurilor brute ale câmpului cheie. Un comision anual, la un
     câmp lunar, intră împărțit la 12 (`derivat`).
  2. Fiecare rând e referință sau variantă:
       - câmpurile de scenariu (DAE, dobândă, dobânda depozitului) după potrivirea cu scenariul
         de referință, calculată deja la extragere (scenariu.referinta.potrivire);
       - restul după `referinta_fisa`, când l-a marcat modelul (fluxul nou), altfel după markeri
         (urgent, suplimentar, ghișeu ...) căutați în condiție și în eticheta din citat — partea
         dinaintea cifrei: „emitere card 0 lei; emitere urgentă 50 lei” are „urgent” lângă 50,
         nu lângă 0.
  3. Valorile de referință egale (aceeași cifră din trei documente) devin una, cu toate sursele.
  4. Câștigă sursa cea mai sigură (lista de tarife înaintea paginii de produs), apoi varianta
     preferată (online la transferuri), apoi cifra găsită în cele mai multe surse. Dacă la același
     nivel rămân cifre diferite, starea e `conflict`: se arată cea mai des găsită, iar celelalte
     stau în `alternative`, pentru verificare.
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

AICI = Path(__file__).parent
FISE = AICI / "fise_produse.json"
PRODUSE = AICI / "produse_libra.json"
REFERINTE = AICI / "referinte_libra.json"
V2 = AICI / "produse_bancare_v2.json"
RANG_NECUNOSCUT = 3
MAX_VARIANTE = 12


def fara_diacritice(s: str) -> str:
    s = s.replace("ş", "ș").replace("ţ", "ț")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


class Fise:
    """Fișele produselor și maparea produs Libra -> tip v2, încărcate o dată."""

    def __init__(self, cale: Path = FISE, produse: Path = PRODUSE):
        f = json.loads(cale.read_text(encoding="utf-8"))
        self.campuri = f["campuri"]
        self.tipuri = f["tipuri"]
        self.produse = f.get("produse") or {}
        self.rang = f["rang_surse"]
        self.markeri = {k: (v["eticheta"], re.compile(v["rx"])) for k, v in f["markeri"].items()}
        self.tip = {p["cod"]: p.get("tip_v2") for p in json.loads(produse.read_text(encoding="utf-8"))["produse"]}
        # produsele cu scenariu de referință (credite PF, depozite, economii, FX): la ele DAE și dobânda
        # se aleg după potrivirea cu scenariul; la celelalte (creditele pentru firme) ca un comision
        self.cu_scenariu = set(json.loads(REFERINTE.read_text(encoding="utf-8"))["produse"])
        self.v2 = {p["id"]: set(p.get("campuri") or [])
                   for p in json.loads(V2.read_text(encoding="utf-8"))["produse"]}

    def campuri_cheie(self, cod: str) -> list[str]:
        p = self.produse.get(cod) or {}
        return p.get("campuri_cheie") or (self.tipuri.get(self.tip.get(cod)) or {}).get("campuri_cheie") or []

    def exclude(self, cod: str, camp_cheie: str) -> list[str]:
        """Markerii care fac dintr-o valoare o variantă, fără cei pe care produsul îi are în nume
        (Gold la CARD_DEBIT_GOLD e chiar referința)."""
        pastrate = set((self.produse.get(cod) or {}).get("nu_exclude") or []) \
            | set((self.tipuri.get(self.tip.get(cod)) or {}).get("nu_exclude") or [])
        return [m for m in self.campuri[camp_cheie].get("exclude") or [] if m not in pastrate]

    def dupa_scenariu(self, cod: str, camp_cheie: str) -> bool:
        return bool(self.campuri[camp_cheie].get("scenariu")) and cod in self.cu_scenariu

    def descriere(self, cod: str) -> list[tuple[str, list[str], str]]:
        """Pentru promptul de extragere: (cheie, câmpurile brute ale tipului, varianta de referință).
        Fără câmpurile de scenariu ale produselor cu scenariu: pe acelea le acoperă blocul
        „SCENARIU DE REFERINȚĂ” din flow-html, iar două reguli pe aceeași valoare s-ar bate cap în cap."""
        permise = self.v2.get(self.tip.get(cod)) or set()
        out = []
        for k in self.campuri_cheie(cod):
            if self.dupa_scenariu(cod, k):
                continue
            d = self.campuri[k]
            brute = [c for c in d["campuri"] + list(d.get("lunar_din") or []) if c in permise]
            if brute:
                out.append((k, brute, d["referinta"]))
        return out


def _valoare_in_text(v: Decimal | float) -> re.Pattern:
    """Cifra, cum poate apărea în citat: 50 / 50,00 / 50.00 / 1.200 / 0,5."""
    d = Decimal(str(v)).normalize()
    intreg, _, zec = f"{d:f}".partition(".")
    # separatorul de mii: punct, spațiu sau spațiu fix („1.200”, „1 200”)
    cu_mii = re.sub(r"\B(?=(\d{3})+$)", lambda _: "[.  ]?", intreg)
    zec_rx = rf"[.,]{zec}0*" if zec else r"(?:[.,]0+)?"
    return re.compile(rf"(?<![\d.,]){cu_mii}{zec_rx}(?![\d])")


def eticheta_citat(citat: str | None, valoare) -> str:
    """Contextul cifrei în citat: eticheta dinaintea ei (rândul din tabel) și ce urmează după ea până
    la următoarea cifră („0 lei/lună* (primele 24 de luni…” spune promoția după cifră). Fără cifră
    în citat, tot citatul."""
    c = citat or ""
    if valoare is None:
        return c
    m = _valoare_in_text(valoare).search(c)
    if not m:
        return c
    # până la următoarea cifră sau la capătul rândului din tabel („;”, „|”, rând nou): „0 lei; emitere
    # urgentă 50 lei” nu face din 0 o emitere urgentă
    dupa = re.match(r"[^\d;|\n]*(?:\d+\s*(?:de\s+)?luni)?", c[m.end():])
    return c[:m.start()] + " " + (dupa.group(0) if dupa else "")


def markeri_gasiti(fise: Fise, r: dict, chei: list[str]) -> list[str]:
    text = fara_diacritice(" ".join([r.get("conditie") or "", eticheta_citat(r.get("citat"), r.get("valoare_num"))])).lower()
    return [k for k in chei if fise.markeri[k][1].search(text)]


def _sc(r: dict) -> dict:
    sc = r.get("scenariu")
    if isinstance(sc, str):
        sc = json.loads(sc)
    return sc or {}


def clasifica(fise: Fise, cod: str, camp_cheie: str, r: dict) -> tuple[str, str | None]:
    """('referinta' | 'aproximativ' | 'varianta', eticheta variantei)."""
    d = fise.campuri[camp_cheie]
    sc = _sc(r)
    if fise.dupa_scenariu(cod, camp_cheie):
        ref = (sc.get("referinta") or {}).get("potrivire")
        if sc.get("conditionat"):
            return "varianta", "condiționat: " + ", ".join(sc["conditionat"])[:80]
        if ref == "exact":
            return "referinta", None
        if ref == "aproximativ":
            return "aproximativ", None
        # depozitul / economiile au grila întreagă: fiecare treaptă e o variantă cu numele ei
        et = r.get("conditie") or ", ".join(sc.get("etichete") or []) or "alt scenariu"
        return "varianta", et[:80]
    exclude = fise.exclude(cod, camp_cheie)
    if sc.get("referinta_fisa") is not None:
        # fluxul nou: modelul a citit pagina întreagă și a spus dacă e varianta de referință
        # (extrage_comparatie_libra.bloc_referinta); markerii rămân pentru valorile vechi
        return ("referinta", None) if sc["referinta_fisa"] else ("varianta", (sc.get("varianta_fisa") or "altă variantă")[:80])
    gasiti = markeri_gasiti(fise, r, exclude)
    if gasiti:
        return "varianta", ", ".join(fise.markeri[k][0] for k in gasiti)
    return "referinta", None


def _num(v) -> Decimal | None:
    return None if v is None else Decimal(str(v))


def alege(fise: Fise, cod: str, camp_cheie: str, randuri: list[dict]) -> dict:
    """Rezultatul pentru valori_referinta (fără id-urile băncii și ale produsului)."""
    d = fise.campuri[camp_cheie]
    lunar_din = set(d.get("lunar_din") or [])
    brute = []
    for r in randuri:
        if r.get("ambiguu") or r.get("valoare_num") is None:
            continue
        if r["camp"] in d["campuri"]:
            brute.append({**r, "valoare_num": _num(r["valoare_num"]), "derivat": False})
        elif r["camp"] in lunar_din:
            brute.append({**r, "valoare_num": (_num(r["valoare_num"]) / 12).quantize(Decimal("0.01")),
                          "derivat": True})
    rez = {"camp_cheie": camp_cheie, "n_brut": len(brute), "n_unice": len({(x["valoare_num"], x["unitate"]) for x in brute}),
           "valoare_num": None, "unitate": None, "moneda": None, "camp_sursa": None, "derivat": False,
           "id_comparatie": None, "surse": [], "variante": [], "alternative": []}
    if not brute:
        return {**rez, "stare": "lipsa", "motiv": "nicio valoare extrasă pentru acest câmp"}

    unitati = d.get("unitati") or []
    ref, apr, var = [], [], []
    for r in brute:
        tip, et = clasifica(fise, cod, camp_cheie, r)
        if tip != "varianta" and unitati and r["unitate"] not in unitati:
            tip, et = "varianta", f"în {r['unitate'] or 'altă unitate'}"
        (ref if tip == "referinta" else apr if tip == "aproximativ" else var).append((r, et))

    def grupe(lista):
        g = defaultdict(list)
        for r, _ in lista:
            g[(r["valoare_num"], r["unitate"], r.get("moneda"))].append(r)
        return g

    # variantele, grupate pe etichetă și cifră
    gv = defaultdict(int)
    for r, et in var:
        gv[(et, r["valoare_num"], r["unitate"])] += 1
    rez["variante"] = [{"eticheta": et, "valoare_num": float(v), "unitate": u, "n": n}
                       for (et, v, u), n in sorted(gv.items(), key=lambda x: (-x[1], x[0][0] or ""))][:MAX_VARIANTE]

    alese = ref or apr
    if not alese:
        return {**rez, "stare": "doar_variante",
                "motiv": f"{len(var)} valori, toate pe alte variante decât referința"}
    stare = "referinta" if ref else "aproximativ"
    # unitatea preferată de fișă: o cifră în lei nu stă lângă una în procente
    if unitati:
        u = next(u for u in unitati if any(r["unitate"] == u for r, _ in alese))
        alese = [(r, et) for r, et in alese if r["unitate"] == u]
    prefera = d.get("prefera") or []

    def scor(rs: list[dict]):
        rang = min(fise.rang.get(r.get("rol") or "", RANG_NECUNOSCUT) for r in rs)
        pref = any(markeri_gasiti(fise, r, prefera) for r in rs) if prefera else False
        return (rang, not pref, -len({r["id_sursa"] for r in rs}), -max(float(r.get("incredere") or 0) for r in rs))

    # la egalitate: cifra cu mai multe apariții, apoi cifra însăși — aceleași date dau mereu aceeași
    # alegere (fără asta, ordinea rândurilor din bază decidea, iar două rulări se contraziceau)
    g = sorted(grupe(alese).items(), key=lambda kv: (*scor(kv[1]), -len(kv[1]), kv[0][0]))
    (val, unit, mon), rs = g[0]
    nivel = scor(rs)[:2]
    concurente = [(k, x) for k, x in g[1:] if scor(x)[:2] == nivel]
    if concurente:
        stare = "conflict"
        rez["alternative"] = [{"valoare_num": float(k[0]), "unitate": k[1], "n": len({r["id_sursa"] for r in x})}
                              for k, x in concurente]
    principal = max(rs, key=lambda r: (-fise.rang.get(r.get("rol") or "", RANG_NECUNOSCUT), float(r.get("incredere") or 0)))
    surse = {}
    for r in sorted(rs, key=lambda r: fise.rang.get(r.get("rol") or "", RANG_NECUNOSCUT)):
        surse.setdefault(r["id_sursa"], {"id_sursa": r["id_sursa"], "url": r.get("url"), "rol": r.get("rol"),
                                         "citat": r.get("citat"), "link": r.get("link_live")})
    rol = principal.get("rol") or "sursă necunoscută"
    motiv = {"referinta": f"varianta de referință, din {rol}",
             "aproximativ": f"cel mai apropiat caz de scenariul de referință, din {rol}",
             "conflict": f"{len(concurente) + 1} cifre diferite pe varianta de referință, din surse la fel de sigure ({rol}); "
                         "aleasă cea găsită în cele mai multe surse"}[stare]
    if principal["derivat"]:
        motiv += "; comision anual împărțit la 12"
    return {**rez, "stare": stare, "valoare_num": float(val), "unitate": unit, "moneda": mon,
            "camp_sursa": principal["camp"], "derivat": principal["derivat"], "id_comparatie": principal.get("id"),
            "surse": list(surse.values()), "motiv": motiv}
