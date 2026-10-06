"""
scenariu_libra.py — codul de scenariu al extractorului, descompus în câmpuri.

Flow-ul îi cere modelului ca valorile multiple ale aceluiași câmp să poarte o
etichetă de scenariu (`cod_scenariu`). Modelul o compune singur, fără un
format comun între bănci:

    Raiffeisen  CASA_VERDE_350K_300L_PREMIUM_3ANI
    BRD         IP_300K_240L_FIX3ANI
    BCR         NP_350K_300L_VENIT10K_MAXINVEST

Toate spun același lucru — sumă, perioadă, perioadă fixă, profil de client —
dar ca text liber, deci nu se pot alinia pe rânduri. Aici se scot dimensiunile,
determinist, fără model. Ce nu se recunoaște rămâne ca etichetă, nu se ghicește.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# Prefixe de 2 litere puse de model ca nume de produs (NP, IP, CC...). Nu spun
# nimic despre scenariu, iar pe pagină ar fi doar zgomot.
PREFIXE = {"NP", "IP", "CC", "OP", "CI", "PF", "PJ", "CM", "DT"}

ETICHETE = {
    "MAXINVEST": "Max Invest", "MAX": "Max", "GO": "Go", "PREMIUM": "Premium", "STANDARD": "standard",
    "STARTUP": "start-up", "CLIENTNOU": "client nou", "BENEFICII": "program de beneficii",
    "VENITMARE": "venit mare", "VENITMIC": "venit mic", "SALARIU": "cu salariu virat",
    "FARAVIRARE": "fără virare salariu", "VIRARE": "cu virare salariu", "ASIG": "cu asigurare",
    "ASIGURARE": "cu asigurare", "FARAASIG": "fără asigurare", "CODEBITOR": "cu codebitor",
    "STRAINATATE": "străinătate", "ONLINE": "online", "PROMO": "promoție", "EXEMPLU": "exemplu",
    "REPREZENTATIV": "reprezentativ", "DOM": "cu domiciliere", "FARADOM": "fără domiciliere",
}
# perechi scrise de model cu underscore între ele: FARA_VIRARE, FARA_ASIG...
LIPIRI = [("FARA", "VIRARE"), ("FARA", "ASIG"), ("FARA", "ASIGURARE"), ("FARA", "DOM"),
          ("VENIT", "MARE"), ("VENIT", "MIC"), ("CLIENT", "NOU"), ("MAX", "INVEST")]

PRAG_LUNI = 480   # „300L" sunt luni; „5367L" (TOTAL_5367L) nu poate fi o perioadă: sunt lei


def _numar(s: str) -> float:
    return float(s.replace(",", "."))


def descompune(cod: str | None) -> dict | None:
    """
    @returns {"cod", "suma", "suma_max", "moneda", "perioada_luni", "perioada_zile",
              "fix_ani", "venit_min", "etichete"} — doar cheile recunoscute; None fără cod.
    """
    if not cod or not re.fullmatch(r"[A-Za-z0-9_.,]+", cod.strip()):
        return None
    tok = [t for t in cod.strip().upper().split("_") if t]
    i = 0
    lipit = []
    while i < len(tok):                       # FARA + VIRARE -> FARAVIRARE
        if i + 1 < len(tok) and (tok[i], tok[i + 1]) in LIPIRI:
            lipit.append(tok[i] + tok[i + 1]); i += 2
        else:
            lipit.append(tok[i]); i += 1
    r: dict = {"cod": cod}
    etichete: list[str] = []
    sume: list[float] = []
    for j, t in enumerate(lipit):
        if j == 0 and t in PREFIXE:
            continue
        if t in ("SUB", "PESTE") and j + 1 < len(lipit) and re.fullmatch(r"\d+(?:ANI|AN)", lipit[j + 1]):
            n = re.match(r"\d+", lipit[j + 1]).group(0)
            etichete.append(f"{t.lower()} {n} {'an' if n == '1' else 'ani'}")
            continue
        # „FARA_VIRARE_SALARIU": SALARIU continuă negația, nu înseamnă „cu salariu virat"
        if t == "SALARIU" and j > 0 and lipit[j - 1] in ("FARAVIRARE", "VIRARE"):
            continue
        m = re.fullmatch(r"(\d+(?:[.,]\d+)?)(K|M)", t)
        if m:
            sume.append(_numar(m.group(1)) * (1000 if m.group(2) == "K" else 1_000_000)); continue
        m = re.fullmatch(r"(?:MIN)?(\d+(?:[.,]\d+)?)(LEI|RON|EUR|USD)", t)
        if m:
            sume.append(_numar(m.group(1)))
            r["moneda"] = {"LEI": "RON", "RON": "RON"}.get(m.group(2), m.group(2)); continue
        m = re.fullmatch(r"(\d+)L", t)
        if m:
            n = int(m.group(1))
            if n <= PRAG_LUNI:
                r["perioada_luni"] = n
            else:
                sume.append(float(n)); r.setdefault("moneda", "RON")
            continue
        m = re.fullmatch(r"(\d+)(?:LUNI|LUNA)", t)
        if m:
            r["perioada_luni"] = int(m.group(1)); continue
        m = re.fullmatch(r"(\d+)Z(?:ILE)?", t)
        if m:
            r["perioada_zile"] = int(m.group(1)); continue
        if re.fullmatch(r"\d+(?:ANI|AN)", t) and j > 0 and lipit[j - 1] in ("SUB", "PESTE"):
            continue                          # deja scris ca „sub 1 an" la tokenul precedent
        m = re.fullmatch(r"FIX(\d+)(?:Y|ANI|AN|A)?", t) or re.fullmatch(r"(\d+)(?:ANI|AN|Y)", t)
        if m:
            r["fix_ani"] = int(m.group(1)); continue
        m = re.fullmatch(r"VENIT(\d+(?:[.,]\d+)?)K", t)
        if m:
            r["venit_min"] = _numar(m.group(1)) * 1000; continue
        etichete.append(ETICHETE.get(t, t.lower()))
    if sume:
        r["suma"] = min(sume)
        if len(sume) > 1:
            r["suma_max"] = max(sume)
        r.setdefault("moneda", "RON")
    if etichete:
        r["etichete"] = etichete
    return r


def interval(s: dict | None) -> tuple[float | None, float | None, str | None]:
    """Axa principală pentru coloanele interval_*: perioada, altfel suma."""
    if not s:
        return None, None, None
    if "perioada_luni" in s:
        return s["perioada_luni"], s["perioada_luni"], "luni"
    if "perioada_zile" in s:
        return s["perioada_zile"], s["perioada_zile"], "zile"
    if "suma" in s:
        u = {"RON": "lei", "EUR": "eur", "USD": "usd"}.get(s.get("moneda", "RON"), "lei")
        return s["suma"], s.get("suma_max", s["suma"]), u
    return None, None, None


# ── SCENARIUL DE REFERINȚĂ ──────────────────────────────────────────
# Vezi referinte_libra.json. Câmpurile dependente se iau din catalogul v2
# (`trepte[].campuri`): sunt exact câmpurile pe care flow-ul le cere pe trepte.

_AICI = Path(__file__).parent
_REF = json.loads((_AICI / "referinte_libra.json").read_text(encoding="utf-8"))
_TREPTE = {p["id"]: p.get("trepte") or []
           for p in json.loads((_AICI / "produse_bancare_v2.json").read_text(encoding="utf-8"))["produse"]}
_DIM = {"suma": "suma", "perioada_luni": "perioada", "valuta": "valuta"}
# etichete de profil care ADAUGĂ un beneficiu față de prețul de listă (vezi ETICHETE mai sus)
BENEFICII = re.compile(r"^(max|max invest|premium|gold|venit mare|cu salariu virat|cu virare salariu|cu asigurare|"
                       r"promoție|cu domiciliere|program de beneficii|cu codebitor)$", re.I)


def referinta(cod_libra: str) -> dict | None:
    return (_REF.get("produse") or {}).get(cod_libra)


def potrivire(cod_libra: str, v2: str, camp: str, sc: dict | None,
              potrivire_model: str | None = None) -> dict | None:
    """
    Relația unei valori cu scenariul de referință al produsului Libra:
      exact        — suma/perioada/valuta coincid (suma ±2%)
      aproximativ  — aproape (suma ±15%, perioada ±20%)
      alt          — alt exemplu: nu se compară cu referința
      nespecificat — câmpul depinde de scenariu, dar valoarea nu-l spune
    None când produsul n-are referință sau câmpul nu depinde de ea (un comision fix).
    """
    ref = referinta(cod_libra)
    if not ref:
        return None
    axe = {t["dimensiune"]: set(t.get("campuri") or []) for t in _TREPTE.get(v2, [])
           if t["id"] in ("suma", "perioada", "valuta")}
    dims = [k for k in ref["parametri"] if camp in axe.get(_DIM[k], set())]
    if not dims:
        return None
    tol = _REF.get("toleranta") or {}
    sc = sc or {}
    stari = []
    for k in dims:
        r = ref["parametri"][k]
        if k == "valuta":
            v = (sc.get("valuta") or "").upper().replace("LEI", "RON")
            stari.append("nespecificat" if not v else "exact" if v == r else "alt")
        elif k == "suma" and sc.get("banda"):
            # treaptă de sold (grilă): referința e în bandă sau nu; fără capete = orice sold
            lo, hi = sc.get("suma"), sc.get("suma_max")
            peste = lo is None or r >= lo
            sub = hi is None or (r < hi if sc.get("suma_max_exclusiv") else r <= hi)
            stari.append("exact" if peste and sub else "alt")
        elif k == "suma":
            lo, hi = sc.get("suma"), sc.get("suma_max")
            if lo is None:
                stari.append("nespecificat")
            elif hi is not None and lo <= r <= hi:
                stari.append("exact")
            else:
                d = abs(float(lo) - r) / r
                stari.append("exact" if d <= tol.get("suma_exact", .02) else
                             "aproximativ" if d <= tol.get("suma_aproximativ", .15) else "alt")
        else:
            v = sc.get("perioada_luni")
            if v is None and sc.get("perioada_zile") is not None:
                v = round(sc["perioada_zile"] / 30.4, 1)
            if v is None:
                stari.append("nespecificat")
            else:
                d = abs(float(v) - r) / r
                stari.append("exact" if d == 0 else "aproximativ" if d <= tol.get("perioada_aproximativ", .2) else "alt")
    # partea calitativă (asigurare, promoție) o judecă modelul, când i s-a cerut scenariul
    if potrivire_model == "alt_scenariu":
        stari.append("alt")
    stare = next(s for s in ("alt", "nespecificat", "aproximativ", "exact") if s in stari)
    out = {"id": ref["id"], "nume": ref["nume"], "potrivire": stare}
    if ref.get("pret_de_lista") and stare == "exact":
        ben = [e for e in sc.get("etichete") or [] if BENEFICII.match(e)]
        if sc.get("venit_min"):
            ben.append(f"venit ≥ {sc['venit_min']:,.0f} lei".replace(",", "."))
        if ben:
            out["potrivire"] = "aproximativ"
            out["motiv"] = "aceeași sumă și perioadă, dar pentru un profil cu beneficii: " + ", ".join(ben)
        elif sc.get("conditionat"):
            # grilele (extrage_comparatie_libra.grila): program de beneficii, plăți programate, promoție
            out["potrivire"] = "aproximativ"
            out["motiv"] = "ofertă condiționată: " + "; ".join(sc["conditionat"])
    return out


if __name__ == "__main__":
    for c in ["CASA_VERDE_350K_300L_PREMIUM_3ANI", "IP_300K_240L_FIX3ANI", "NP_350K_300L_VENIT10K_MAXINVEST",
              "TOTAL_5367L_24L", "NP_5000EUR_180Z", "NP_100K_499K", "RAMB_ANTIC_FIXA_SUB_1AN",
              "OVERDRAFT_FARA_VIRARE_SALARIU", "PACHET_ULTRA", "NP_BCR_MASTERCARD_CORPORATE_MIN600LEI",
              "PROMO_VISA_EPOSIBIL_PRIMUL_POS_6LUNI", "IP_350K_300L_FARAVIRARE"]:
        s = descompune(c)
        print(f"{c:42} -> {s} | interval {interval(s)}")
