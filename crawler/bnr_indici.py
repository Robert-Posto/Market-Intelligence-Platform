"""Indicii de referinta publicati central de BNR: ROBID/ROBOR si IRCC.

De ce conteaza: aceste valori sunt raportate de banci la BNR si publicate centralizat,
in format tabelar uniform. E mult mai eficient sa le luam de aici decat sa le
extragem din 23 de site-uri de banca, unde apar inconsecvent si doar ca marja
(ex. "IRCC + 2,3%"), nu ca valoare.

Paginile cer JavaScript, deci au nevoie de browser (nu merge cu o simpla cerere HTTP).
"""

import calendar
import re
from datetime import date

PAGINI = {
    "robor": "https://www.bnr.ro/1973-ratele-medii-ale-dobanzilor-pe-piata-monetara-interbancara",
    "ircc": "https://www.bnr.ro/1974-indicele-de-referinta-pentru-creditele-consumatorilor",
}

RE_ETICHETA_TRIM = re.compile(r"(\d{4})\s*T\s*([1-4])", re.I)


def perioada_aplicare(eticheta):
    """'2026T1' -> (2026-07-01, 2026-09-30): cand se APLICA indicele, nu cand s-a calculat.

    BNR eticheteaza valorile pe trimestrul de calcul. Indicele calculat pentru un
    trimestru se aplica din prima zi a celui de-al doilea trimestru calendaristic
    urmator. Regula e confirmata independent de paginile bancilor:
      - BRD scrie 5,58% pentru 01.04-30.06.2026, iar BNR eticheteaza acea valoare "2025T4"
      - Patria si Nexent scriu 5,56% pentru 01.07-30.09.2026, etichetat "2026T1"
    Fara distincia asta, "cel mai recent rand" poate fi o valoare care intra in vigoare
    abia in viitor, iar toate bancile ar parea brusc invechite.
    """
    m = RE_ETICHETA_TRIM.search(eticheta or "")
    if not m:
        return None
    an, trim = int(m.group(1)), int(m.group(2))
    trim_aplicare = trim + 2
    if trim_aplicare > 4:
        trim_aplicare -= 4
        an += 1
    luna_start = 3 * (trim_aplicare - 1) + 1
    luna_final = luna_start + 2
    return (date(an, luna_start, 1),
            date(an, luna_final, calendar.monthrange(an, luna_final)[1]))


def _cu_perioada(rand):
    per = perioada_aplicare(rand.get("perioada"))
    if not per:
        return None
    return {**rand, "aplicabil_de_la": per[0].isoformat(),
            "aplicabil_pana_la": per[1].isoformat()}


def ircc_in_vigoare(trimestrial, la_data=None):
    """Randul al carui interval de aplicare acopera data (implicit azi)."""
    azi = la_data or date.today()
    for rand in trimestrial or []:
        per = perioada_aplicare(rand.get("perioada"))
        if per and per[0] <= azi <= per[1]:
            return _cu_perioada(rand)
    return None


def ircc_ultim_aplicabil(trimestrial, la_data=None):
    """Cel mai recent rand a carui aplicare a INCEPUT deja.

    Plasa de siguranta pentru intervalul in care BNR nu a publicat inca trimestrul
    urmator: fara ea, dupa 1 octombrie nu mai exista nicio referinta si toate
    verificarile IRCC ar amuti pe nesimtite.
    """
    azi = la_data or date.today()
    candidati = []
    for rand in trimestrial or []:
        per = perioada_aplicare(rand.get("perioada"))
        if per and per[0] <= azi:
            candidati.append((per[0], rand))
    if not candidati:
        return None
    return _cu_perioada(max(candidati, key=lambda x: x[0])[1])


def ircc_pentru_perioada(trimestrial, start, final):
    """Randul care se aplica exact in intervalul dat (pentru a verifica ce scrie pagina)."""
    for rand in trimestrial or []:
        per = perioada_aplicare(rand.get("perioada"))
        if per and per[0] == start and per[1] == final:
            return _cu_perioada(rand)
    return None

JS_TABELE = """
els => els.map(t => Array.from(t.querySelectorAll('tr')).map(
    r => Array.from(r.querySelectorAll('th,td')).map(c => c.innerText.trim())
).filter(r => r.some(c => c)))
"""


def _numar(text):
    """'5,84' -> 5.84 ; returneaza None daca nu e numeric."""
    try:
        return float(text.replace(",", "."))
    except (ValueError, AttributeError):
        return None


def robid_robor(page):
    """Seriile zilnice ROBID si ROBOR, pe scadente (O/N, T/N, 1W, 1M, 3M, 6M, 12M)."""
    page.goto(PAGINI["robor"], wait_until="load", timeout=45000)
    page.wait_for_timeout(5000)
    tabele = page.eval_on_selector_all("table", JS_TABELE)
    if not tabele:
        return {"sursa": PAGINI["robor"], "zile": [], "eroare": "niciun tabel"}

    tabel = tabele[0]
    # randul de antet: "Perioada | O/N | T/N | ... " de 2 ori (ROBID, apoi ROBOR)
    antet = next((r for r in tabel if r and "perioada" in r[0].lower()), None)
    scadente = antet[1:] if antet else []
    jumatate = len(scadente) // 2

    zile = []
    for rand in tabel:
        if not rand or not rand[0] or "perioada" in rand[0].lower():
            continue
        valori = [_numar(c) for c in rand[1:]]
        if not any(v is not None for v in valori):
            continue
        zile.append({
            "data": rand[0],
            "robid": dict(zip(scadente[:jumatate], valori[:jumatate])),
            "robor": dict(zip(scadente[jumatate:], valori[jumatate:])),
        })
    return {"sursa": PAGINI["robor"], "scadente": scadente[:jumatate], "zile": zile}


def ircc(page):
    """IRCC: indicele trimestrial (cel aplicat in credite) si seria zilnica."""
    page.goto(PAGINI["ircc"], wait_until="load", timeout=45000)
    page.wait_for_timeout(5000)
    tabele = page.eval_on_selector_all("table", JS_TABELE)

    def serie(tabel):
        iesire = []
        for rand in tabel:
            if len(rand) < 2 or "perioada" in rand[0].lower():
                continue
            val = _numar(rand[1])
            if val is not None:
                iesire.append({"perioada": rand[0], "valoare": val})
        return iesire

    # primul tabel = trimestrial (ex. "2026T1"), al doilea = zilnic (ex. "15.09.2026")
    trimestrial = serie(tabele[0]) if len(tabele) > 0 else []
    zilnic = serie(tabele[1]) if len(tabele) > 1 else []
    return {
        "sursa": PAGINI["ircc"],
        "trimestrial": trimestrial,
        "zilnic": zilnic,
        # nu "cel mai recent rand": alegem randul al carui interval de aplicare
        # acopera ziua de azi (vezi perioada_aplicare)
        "in_vigoare": ircc_in_vigoare(trimestrial),
        "cel_mai_recent_calculat": _cu_perioada(trimestrial[0]) if trimestrial else None,
    }


def toti_indicii(page):
    """Strange ROBOR si IRCC intr-o singura structura."""
    rezultat = {}
    for nume, functie in (("robid_robor", robid_robor), ("ircc", ircc)):
        try:
            rezultat[nume] = functie(page)
        except Exception as e:
            rezultat[nume] = {"eroare": str(e).splitlines()[0][:120]}
    return rezultat
