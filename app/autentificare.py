"""Autentificarea cu Active Directory (LDAPS) și rolurile admin / analist.

De ce: pe mcc-test.libra.bank aplicația era deschisă oricui din rețea. Logarea se face cu
contul de Windows, verificat la AD; rolul vine din grupurile AD (inclusiv imbricate):
`MCC_LDAP_GRUP_ADMIN` → admin, `MCC_LDAP_GRUP_ANALIST` → analist, în ambele → admin.

Modulul nu știe nimic de server (testabil separat, `app/test_autentificare.py`):
  - `Config`: setările AD din mediu (`.env`), cu `problema()` = de ce nu se poate loga;
  - `Autentificator`: validare, limitarea încercărilor, verificarea la AD (`ldap3`, sau un
    verificator injectat în teste) și jurnalul fiecărei încercări;
  - `Sesiuni`: în memorie (serverul nu scrie în bază), identificatorul ținut doar ca SHA-256;
  - `jurnal`: o linie JSON pe eveniment în `loguri/autentificare.log`, niciodată parola;
  - `mod_local` / `verifica_pornire`: scurtătura de pe laptop (`MCC_AUTH_LOCAL`), care pe
    server (`MCC_AUTH_OBLIGATORIE=1`) nu poate avea efect.

Cerințele de securitate (numerotate ca în planul din docs/superpowers/plans/
2026-10-06-autentificare-ldap.md) sunt citate lângă codul care le respectă.
"""

import datetime
import hashlib
import json
import os
import re
import secrets
import ssl
import sys
import threading
import time
import urllib.parse
from typing import NamedTuple, Optional

RADACINA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# citit la fiecare scriere, ca testele să-l poată muta într-un director temporar
CALE_JURNAL = os.path.join(RADACINA, "loguri", "autentificare.log")

ROLURI = ("admin", "analist")
ORE_IMPLICITE = 8
# cerința 5: conectarea și fiecare răspuns au limită; AD-ul care nu răspunde nu ține firul
TIMEOUT_CONECTARE = 5
TIMEOUT_RASPUNS = 10
LDAP_SIMULTANE = 4
# cerința 6: sub pragul de blocare al AD-ului (de obicei 5–10), ca aplicația să nu poată fi
# folosită la blocarea conturilor prin parole greșite trimise în serie
FEREASTRA_S = 15 * 60
ESECURI_UTILIZATOR = 5
ESECURI_IP = 20
# cerința 8
MAXIM_ABSOLUT_S = 12 * 3600
SESIUNI_PE_UTILIZATOR = 10
CURATARE_S = 15 * 60
PAROLA_MAXIM = 256
# regula AD LDAP_MATCHING_RULE_IN_CHAIN: apartenența și prin grupuri imbricate
REGULA_IMBRICATA = "1.2.840.113556.1.4.1941"

# fullmatch, nu ^…$: în Python `$` acceptă și un „\n” la final
_UTILIZATOR = re.compile(r"[A-Za-z0-9._-]{1,64}")
_DOMENIU = re.compile(r"[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*")


class Config:
    """Setările AD. Lipsa lor nu oprește serverul: logarea răspunde `ad_indisponibil`."""

    def __init__(self, url="", domeniu="", baza="", grup_admin="", grup_analist="", ca=None,
                 sesiune_ore=ORE_IMPLICITE):
        self.url = url
        self.domeniu = domeniu
        self.baza = baza
        self.grup_admin = grup_admin
        self.grup_analist = grup_analist
        self.ca = ca
        self.sesiune_ore = sesiune_ore      # None = valoare invalidă în mediu (vezi problema())

    @classmethod
    def din_mediu(cls, env=os.environ):
        def v(cheie):
            return (env.get(cheie) or "").strip()
        text_ore = v("MCC_SESIUNE_ORE") or str(ORE_IMPLICITE)
        try:
            ore = float(text_ore)
        except ValueError:
            ore = None
        if ore is not None and not ore > 0:        # prinde și NaN
            ore = None
        return cls(url=v("MCC_LDAP_URL"), domeniu=v("MCC_LDAP_DOMENIU"), baza=v("MCC_LDAP_BAZA"),
                   grup_admin=v("MCC_LDAP_GRUP_ADMIN"), grup_analist=v("MCC_LDAP_GRUP_ANALIST"),
                   ca=v("MCC_LDAP_CA") or None, sesiune_ore=ore)

    def problema(self):
        """De ce nu se poate verifica o logare cu setările astea, sau None."""
        if not self.url:
            return "MCC_LDAP_URL lipsește"
        u = urllib.parse.urlsplit(self.url)
        # cerința 4: doar LDAPS. Pe ldap:// parola ar trece prin rețea în clar.
        if u.scheme.lower() != "ldaps":
            return "MCC_LDAP_URL trebuie să înceapă cu ldaps:// (fără TLS parola ar trece în clar)"
        try:
            u.port
        except ValueError:
            return "MCC_LDAP_URL are un port invalid"
        if not u.hostname or u.username or u.password or u.path not in ("", "/") or u.query or u.fragment:
            return "MCC_LDAP_URL trebuie să fie doar ldaps://server[:port]"
        if not self.domeniu:
            return "MCC_LDAP_DOMENIU lipsește"
        if not _DOMENIU.fullmatch(self.domeniu):
            return "MCC_LDAP_DOMENIU trebuie să fie un nume DNS (ex. banca.example)"
        if not self.baza:
            return "MCC_LDAP_BAZA lipsește"
        if not self.grup_admin:
            return "MCC_LDAP_GRUP_ADMIN lipsește"
        if not self.grup_analist:
            return "MCC_LDAP_GRUP_ANALIST lipsește"
        if self.ca and not os.path.isfile(self.ca):
            return f"MCC_LDAP_CA: fișierul {self.ca} nu există"
        if self.sesiune_ore is None:
            return "MCC_SESIUNE_ORE invalid (un număr de ore mai mare ca 0)"
        return None


class Rezultat(NamedTuple):
    ok: bool
    utilizator: str
    nume: str
    rol: Optional[str]
    motiv: Optional[str]        # invalid | fara_rol | indisponibil | limitat


def normalizeaza_utilizator(text):
    """Numele scurt, cu litere mici, sau None (cerința 1).

    `DOMENIU\\x` și `x@domeniu` devin `x`: bind-ul se face oricum în domeniul nostru. Literele
    mici fac ca „Ana”, „ANA” și „LIBRA\\ana” să fie același cont și la limitare; altfel fiecare
    variantă de scriere ar avea propriile 5 încercări.
    """
    if not isinstance(text, str):
        return None
    text = text.strip()
    if "\\" in text:
        text = text.split("\\", 1)[1]
    if "@" in text:
        text = text.split("@", 1)[0]
    return text.lower() if _UTILIZATOR.fullmatch(text) else None


def _parola_valida(parola):
    # cerința 2: cu parolă goală AD-ul face „unauthenticated bind” și răspunde SUCCES
    return isinstance(parola, str) and bool(parola.strip()) and len(parola) <= PAROLA_MAXIM


def filtru_utilizator(utilizator, domeniu):
    """Contul legat: după sAMAccountName sau după UPN-ul explicit.

    Bind-ul cu `x@domeniu` reușește pentru contul cu acel UPN explicit SAU, dacă nu există, pentru
    contul cu sAMAccountName `x` (UPN-ul implicit). Căutând după amândouă, un al doilea cont
    potrivit iese la iveală (ambiguu, refuzat) în loc să ia rolul celuilalt.
    """
    from ldap3.utils.conv import escape_filter_chars as esc
    # cerința 3: valorile escapate, deși validarea lasă oricum doar [A-Za-z0-9._-]
    return (f"(&(objectClass=user)(|(sAMAccountName={esc(utilizator)})"
            f"(userPrincipalName={esc(utilizator + '@' + domeniu)})))")


def filtru_grup(sam, dn_grup):
    """Apartenența, directă sau prin grupuri imbricate, la grupul cu DN-ul dat.

    DN-ul se escapează și el: un grup ca „CN=MCC (Admin),…” ar rupe altfel filtrul.
    """
    from ldap3.utils.conv import escape_filter_chars as esc
    return f"(&(sAMAccountName={esc(sam)})(memberOf:{REGULA_IMBRICATA}:={esc(dn_grup)}))"


class Autentificator:
    def __init__(self, config, verificator=None, ceas=time.monotonic):
        self.config = config
        # verificator(utilizator, parola) -> (nume, rol) | (nume, None) fără rol | None parolă greșită;
        # o excepție înseamnă AD indisponibil
        self._verificator = verificator or self._verifica_ldap
        self._ceas = ceas
        self._lacat = threading.Lock()
        self._esecuri = {}              # ("u", nume) / ("ip", adresa) -> momentele eșecurilor
        self._ultima_curatare = ceas()
        # cerința 5: cel mult 4 verificări deodată; a cincea nu așteaptă, primește indisponibil
        self._semafor = threading.BoundedSemaphore(LDAP_SIMULTANE)

    def autentifica(self, utilizator, parola, ip):
        nume_scurt = normalizeaza_utilizator(utilizator)
        if nume_scurt is None or not _parola_valida(parola):
            # fără AD și fără contor: nimic nu ajunge la AD, deci nu poate bloca un cont
            return self._incheie(Rezultat(False, nume_scurt or "", "", None, "invalid"), ip, nume_scurt)
        chei = (("u", nume_scurt), ("ip", ip))
        with self._lacat:
            acum = self._ceas()
            self._curata_esecuri(acum)
            limitat = (len(self._recente(chei[0], acum)) >= ESECURI_UTILIZATOR
                       or len(self._recente(chei[1], acum)) >= ESECURI_IP)
            if not limitat:
                # Încercarea se socotește eșec de la început și se iartă doar dacă nu e o parolă
                # greșită. Altfel 10 cereri simultane ar trece toate de „sub 5” și ar ajunge la AD.
                for cheie in chei:
                    self._esecuri.setdefault(cheie, []).append(acum)
        if limitat:
            return self._incheie(Rezultat(False, nume_scurt, "", None, "limitat"), ip, nume_scurt)
        rezultat, detaliu = self._intreaba_ad(nume_scurt, parola)
        with self._lacat:
            if rezultat.motiv != "invalid":
                for cheie in chei:
                    lista = self._esecuri.get(cheie)
                    if lista and acum in lista:
                        lista.remove(acum)
            if rezultat.ok:
                self._esecuri.pop(chei[0], None)     # cerința 6: succesul șterge contorul utilizatorului
        if detaliu:
            # cerința 7: detaliul (excepția LDAP) doar în jurnal, iar dacă biblioteca ar fi pus
            # parola în mesaj, nici acolo
            detaliu = detaliu.replace(parola, "***")
        return self._incheie(rezultat, ip, nume_scurt, detaliu)

    def _intreaba_ad(self, nume_scurt, parola):
        if not self._semafor.acquire(blocking=False):
            return (Rezultat(False, nume_scurt, "", None, "indisponibil"),
                    f"peste {LDAP_SIMULTANE} verificări LDAP simultane")
        try:
            raspuns = self._verificator(nume_scurt, parola)
            if raspuns is None:
                return Rezultat(False, nume_scurt, "", None, "invalid"), None
            if not isinstance(raspuns, tuple) or len(raspuns) != 2:
                # un șir de 2 litere s-ar despacheta altfel în (nume, rol)
                raise TypeError(f"verificatorul a întors {type(raspuns).__name__}, nu (nume, rol)")
            nume, rol = raspuns
            nume = nume if isinstance(nume, str) and nume.strip() else nume_scurt
            if rol not in ROLURI:
                return Rezultat(False, nume_scurt, nume, None, "fara_rol"), None
            return Rezultat(True, nume_scurt, nume, rol, None), None
        except Exception as exc:
            return Rezultat(False, nume_scurt, "", None, "indisponibil"), f"{exc.__class__.__name__}: {exc}"
        finally:
            self._semafor.release()

    def _recente(self, cheie, acum):
        lista = [t for t in self._esecuri.get(cheie, ()) if acum - t < FEREASTRA_S]
        if lista:
            self._esecuri[cheie] = lista
        else:
            self._esecuri.pop(cheie, None)
        return lista

    def _curata_esecuri(self, acum):
        # contoarele vechi s-ar aduna altfel la nesfârșit (câte unul pe nume încercat)
        if acum - self._ultima_curatare >= FEREASTRA_S:
            for cheie in list(self._esecuri):
                self._recente(cheie, acum)
            self._ultima_curatare = acum

    def _incheie(self, rezultat, ip, nume_scurt, detaliu=None):
        eveniment = {"eveniment": "logare",
                     # un nume care nu trece validarea poate fi chiar parola, scrisă în câmpul greșit
                     "utilizator": nume_scurt, "ip": ip,
                     "rezultat": "reusit" if rezultat.ok else "esuat", "motiv": rezultat.motiv}
        if rezultat.ok:
            eveniment["rol"] = rezultat.rol
        if detaliu:
            eveniment["detaliu"] = detaliu
        jurnal(eveniment)
        return rezultat

    # ---------------- verificarea reală, prin ldap3 ----------------

    def _verifica_ldap(self, utilizator, parola):
        import ldap3
        c = self.config
        motiv = c.problema()
        if motiv:
            raise RuntimeError(f"configurație AD invalidă: {motiv}")
        u = urllib.parse.urlsplit(c.url)
        # cerința 4: certificatul DC-ului verificat (CA-ul dat sau depozitul sistemului), iar
        # ldap3 verifică și numele din certificat față de MCC_LDAP_URL; altfel parola ar pleca
        # spre oricine răspunde pe adresa aceea
        tls = ldap3.Tls(validate=ssl.CERT_REQUIRED, ca_certs_file=c.ca or None)
        server = ldap3.Server(u.hostname, port=u.port or 636, use_ssl=True, tls=tls,
                              get_info=ldap3.NONE, connect_timeout=TIMEOUT_CONECTARE)
        # auto_referrals=False: AD întoarce referințe (DomainDnsZones…), iar ldap3 le-ar urma
        # refăcând bind-ul cu aceeași parolă pe serverul din referință
        conn = ldap3.Connection(server, user=f"{utilizator}@{c.domeniu}", password=parola,
                                authentication=ldap3.SIMPLE, receive_timeout=TIMEOUT_RASPUNS,
                                read_only=True, auto_referrals=False, raise_exceptions=False)
        try:
            if not conn.bind():
                if conn.result.get("result") == 49:      # invalidCredentials: parolă greșită, cont blocat/expirat
                    return None
                raise RuntimeError(f"bind refuzat: {conn.result.get('description')} {conn.result.get('message')}")
            gasite = self._cauta(conn, filtru_utilizator(utilizator, c.domeniu), ["displayName", "sAMAccountName"])
            if not gasite:
                return utilizator, None       # legat, dar în afara MCC_LDAP_BAZA: fără acces
            if len(gasite) > 1:
                raise RuntimeError(f"cont ambiguu: {len(gasite)} conturi pentru „{utilizator}” "
                                   "(sAMAccountName și UPN explicit diferite)")
            atribute = gasite[0].get("attributes") or {}
            nume, sam = _prima(atribute.get("displayName")), _prima(atribute.get("sAMAccountName")) or utilizator
            # admin întâi: cine e în ambele grupuri e admin
            for dn_grup, rol in ((c.grup_admin, "admin"), (c.grup_analist, "analist")):
                if self._cauta(conn, filtru_grup(sam, dn_grup), ["sAMAccountName"]):
                    return nume, rol
            return nume, None
        finally:
            try:
                conn.unbind()
            except Exception:
                pass
            # după un connect eșuat (timeout, refuz) ldap3 lasă socket-ul deschis până la GC
            if getattr(conn, "socket", None) is not None:
                try:
                    conn.socket.close()
                except OSError:
                    pass

    def _cauta(self, conn, filtru, atribute):
        conn.search(self.config.baza, filtru, attributes=atribute, size_limit=2, time_limit=TIMEOUT_RASPUNS)
        cod = conn.result.get("result")
        if cod not in (0, 4):       # 4 = sizeLimitExceeded: mai mult de un cont, prins ca ambiguu
            raise RuntimeError(f"căutare LDAP eșuată: {conn.result.get('description')} {conn.result.get('message')}")
        # doar intrările: referințele (searchResRef) nu sunt conturi
        return [r for r in conn.response or () if r.get("type") == "searchResEntry"]


def _prima(valoare):
    if isinstance(valoare, (list, tuple)):
        valoare = valoare[0] if valoare else ""
    return valoare if isinstance(valoare, str) else ""


class Sesiuni:
    """Sesiunile, în memorie (serverul nu scrie în bază); o repornire le închide pe toate."""

    def __init__(self, ore_inactivitate=ORE_IMPLICITE, ceas=time.monotonic):
        self._inactivitate_s = ore_inactivitate * 3600
        self._ceas = ceas
        self._lacat = threading.Lock()
        self._sesiuni = {}       # sha256(id) -> {utilizator, nume, rol, creat, activ}, în ordinea creării
        self._ultima_curatare = ceas()

    @staticmethod
    def _cheie(id_sesiune):
        # cerința 8: doar hash-ul; cine vede memoria (sau un dump) nu are cookie-uri valide
        return hashlib.sha256(id_sesiune.encode("utf-8")).hexdigest()

    def creeaza(self, utilizator, nume, rol):
        """Identificatorul în clar, o singură dată (pentru cookie); nou la fiecare logare."""
        id_sesiune = secrets.token_urlsafe(32)
        with self._lacat:
            acum = self._ceas()
            self._curata_periodic(acum)
            ale_lui = [k for k, s in self._sesiuni.items() if s["utilizator"] == utilizator]
            for k in ale_lui[:max(0, len(ale_lui) - SESIUNI_PE_UTILIZATOR + 1)]:
                del self._sesiuni[k]         # cea mai veche iese
            self._sesiuni[self._cheie(id_sesiune)] = {"utilizator": utilizator, "nume": nume, "rol": rol,
                                                      "creat": acum, "activ": acum}
        return id_sesiune

    def citeste(self, id_sesiune):
        """{utilizator, nume, rol} pentru o sesiune validă (și îi reînnoiește activitatea), altfel None."""
        if not isinstance(id_sesiune, str) or not id_sesiune or len(id_sesiune) > 128:
            return None
        cheie = self._cheie(id_sesiune)
        with self._lacat:
            acum = self._ceas()
            self._curata_periodic(acum)
            s = self._sesiuni.get(cheie)
            if s is None:
                return None
            if self._expirata(s, acum):
                del self._sesiuni[cheie]
                return None
            s["activ"] = acum
            return {"utilizator": s["utilizator"], "nume": s["nume"], "rol": s["rol"]}

    def sterge(self, id_sesiune):
        """Ieșirea: sesiunea ștearsă (pentru jurnal) sau None."""
        if not isinstance(id_sesiune, str) or not id_sesiune or len(id_sesiune) > 128:
            return None
        with self._lacat:
            return self._sesiuni.pop(self._cheie(id_sesiune), None)

    def curata(self):
        with self._lacat:
            self._curata(self._ceas())

    def _expirata(self, s, acum):
        return acum - s["activ"] >= self._inactivitate_s or acum - s["creat"] >= MAXIM_ABSOLUT_S

    def _curata_periodic(self, acum):
        if acum - self._ultima_curatare >= CURATARE_S:
            self._curata(acum)

    def _curata(self, acum):
        for k in [k for k, s in self._sesiuni.items() if self._expirata(s, acum)]:
            del self._sesiuni[k]
        self._ultima_curatare = acum


_LACAT_JURNAL = threading.Lock()


def jurnal(eveniment):
    """O linie JSON în `loguri/autentificare.log` (cerința 10). Fără parolă și fără corpul cererii."""
    rand = {"moment": datetime.datetime.now().astimezone().isoformat(timespec="seconds")}
    rand.update({k: v for k, v in eveniment.items() if k not in ("parola", "corp")})
    # json.dumps escapează și „\n”: un nume nu poate scrie un rând fals în jurnal
    linie = json.dumps(rand, ensure_ascii=False, default=str)
    try:
        with _LACAT_JURNAL:
            os.makedirs(os.path.dirname(CALE_JURNAL), exist_ok=True)
            with open(CALE_JURNAL, "a", encoding="utf-8") as f:
                f.write(linie + "\n")
    except OSError as exc:
        # logarea nu cade din cauza jurnalului; rândul ajunge măcar în jurnalul serviciului
        print(f"jurnal autentificare indisponibil ({exc}): {linie}", file=sys.stderr)


def mod_local(env, antete):
    """Rolul utilizatorului local (laptopul de dezvoltare) sau None (cerința 11).

    Activ doar cu `MCC_AUTH_LOCAL`, fără `MCC_AUTH_OBLIGATORIE=1` și fără antetul `X-Real-IP`:
    nginx îl pune pe fiecare cerere, deci nimic din ce vine prin nginx nu e „local”.
    """
    rol = (env.get("MCC_AUTH_LOCAL") or "").strip().lower()
    if rol not in ROLURI:
        return None
    if (env.get("MCC_AUTH_OBLIGATORIE") or "").strip() == "1":
        return None
    if antete.get("X-Real-IP") is not None:
        return None
    return rol


def verifica_pornire(env):
    """Motivul pentru care serverul refuză să pornească, sau None (cerința 11)."""
    local = (env.get("MCC_AUTH_LOCAL") or "").strip()
    if not local:
        return None
    if (env.get("MCC_AUTH_OBLIGATORIE") or "").strip() == "1":
        return ("MCC_AUTH_LOCAL e setată, dar serverul cere autentificare (MCC_AUTH_OBLIGATORIE=1). "
                "Scoate MCC_AUTH_LOCAL din .env: pe server nu există utilizator local.")
    if local.lower() not in ROLURI:
        return f"MCC_AUTH_LOCAL trebuie să fie admin sau analist (este „{local}”)"
    return None
