"""Inventarul produselor Libra: citirea și modificarea `produse_libra.json`.

Fișierul e sursa de adevăr a produselor Libra (57 pe 07.10.2026), până trec
într-o tabelă editabilă: din el `incarca_baza.py` umple tabela `produse_libra`,
iar extragerea ia `tip_v2`. Pagina „Inventar produse” îl modifică direct; baza
se actualizează abia la următoarea rulare a `incarca_baza.py`, deci aici nu se
scrie nimic în Postgres.

Rutele de scriere trec prin aceleași verificări ca rulările manuale
(`rulari.verifica_cerere`: Host, Origin, token), cu un token separat.

Cheia e `cod`: leagă produsul de `inventare-libra/<banca>/<COD>.json`, de
`axa_libra.json` și de rândurile din bază, deci nu se schimbă după adăugare.
Un cod greșit se repară prin ștergere și adăugare, cu toate legăturile pierdute
văzute înainte.
"""

import hashlib
import json
import os
import re
import secrets
import threading
from datetime import datetime, timezone

RADACINA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FISIER = os.path.join(RADACINA, "extragere_produse_bancare", "produse_libra.json")
# tipurile după care extragerea știe ce câmpuri să caute; un produs fără tip e sărit la extragere
FISIER_V2 = os.path.join(RADACINA, "extragere_produse_bancare", "produse_bancare_v2.json")
SEGMENTE = ("PF", "PJ", "PF+PJ")
# CREDIT_SIMPLU_IMM, CARD_DE_CREDIT_PF: așa sunt toate cele 57 de coduri din catalog
CODUL = re.compile(r"^[A-Z0-9]+(_[A-Z0-9]+)*$")
MAX_DENUMIRE = 200
# cea mai lungă descriere din catalog avea 208 octeți pe 07.10.2026
MAX_DESCRIERE = 1000

TOKEN = secrets.token_urlsafe(32)
# două salvări simultane (două file deschise) ar citi aceeași versiune și
# a doua ar șterge modificarea primei
_LACAT = threading.Lock()


class Respins(Exception):
    """Produs invalid sau cerere greșită (HTTP 400)."""


class Conflict(Exception):
    """Fișierul s-a schimbat de la citirea paginii (HTTP 409)."""


def _citeste():
    with open(FISIER, "rb") as f:
        brut = f.read()
    return json.loads(brut.decode("utf-8")), hashlib.sha256(brut).hexdigest()[:16], b"\r\n" in brut


def citeste():
    """Conținutul fișierului, cu versiunea (amprenta) pe care o trimite înapoi orice salvare."""
    date, versiune, _ = _citeste()
    return {
        "fisier": os.path.relpath(FISIER, RADACINA).replace(os.sep, "/"),
        "versiune": versiune,
        "modificat": datetime.fromtimestamp(os.path.getmtime(FISIER), timezone.utc).isoformat(),
        "generat": date.get("generat"),
        "produse": date["produse"],
        "tipuri_v2": tipuri_v2(),
    }


def tipuri_v2():
    with open(FISIER_V2, encoding="utf-8") as f:
        return [{"id": p["id"], "nume": p.get("nume") or p["id"], "segment": p.get("segment")}
                for p in json.load(f)["produse"]]


def _text(v):
    return v.strip() if isinstance(v, str) else ""


def _valideaza(corp, cod):
    denumire = _text(corp.get("denumire"))
    if not denumire:
        raise Respins("denumirea lipsește")
    if len(denumire) > MAX_DENUMIRE:
        raise Respins(f"denumirea are peste {MAX_DENUMIRE} de caractere")
    descriere = _text(corp.get("descriere")) or None
    if descriere and len(descriere) > MAX_DESCRIERE:
        raise Respins(f"descrierea are peste {MAX_DESCRIERE} de caractere")
    segment = corp.get("segment")
    if segment not in SEGMENTE:
        raise Respins(f"segment necunoscut: {segment}")
    categorie = _text(corp.get("categorie_cod")).upper() or None
    if categorie and not CODUL.match(categorie):
        raise Respins("categoria se scrie cu majuscule, cifre și _")
    if not isinstance(corp.get("prioritar"), bool):
        raise Respins("prioritar trebuie să fie da sau nu")
    tip_v2 = corp.get("tip_v2")
    if tip_v2 not in {t["id"] for t in tipuri_v2()}:
        raise Respins(f"tip v2 necunoscut: {tip_v2}")
    # ordinea cheilor din fișier, ca diff-ul să arate doar ce s-a schimbat
    return {"cod": cod, "denumire": denumire, "descriere": descriere, "segment": segment,
            "categorie_cod": categorie, "prioritar": corp["prioritar"], "tip_v2": tip_v2}


def _scrie(date, crlf):
    text = json.dumps(date, ensure_ascii=False, indent=1)
    if crlf:
        text = text.replace("\n", "\r\n")
    temp = f"{FISIER}.{os.getpid()}.tmp"
    with open(temp, "wb") as f:
        f.write(text.encode("utf-8"))
    # înlocuire atomică: un fișier scris pe jumătate ar strica incarca_baza.py și pagina
    os.replace(temp, FISIER)


def salveaza(actiune, corp):
    """Adaugă, modifică sau șterge un produs, doar dacă fișierul e la versiunea văzută de pagină."""
    if actiune not in ("adauga", "modifica", "sterge"):
        raise Respins("acțiune necunoscută")
    cod = _text(corp.get("cod")).upper()
    if not CODUL.match(cod):
        raise Respins("codul se scrie cu majuscule, cifre și _ (ex. CREDIT_SIMPLU_IMM)")
    with _LACAT:
        date, versiune, crlf = _citeste()
        if corp.get("versiune") != versiune:
            raise Conflict("fișierul s-a schimbat între timp; reîncarcă pagina")
        produse = date["produse"]
        poz = next((i for i, p in enumerate(produse) if p["cod"] == cod), None)
        if actiune == "adauga":
            if poz is not None:
                raise Respins(f"codul {cod} există deja")
            produse.append(_valideaza(corp, cod))
            produse.sort(key=lambda p: p["cod"])
        elif poz is None:
            raise Respins(f"produsul {cod} nu există în fișier")
        elif actiune == "modifica":
            produse[poz] = _valideaza(corp, cod)
        else:
            del produse[poz]
        _scrie(date, crlf)
    return citeste()
