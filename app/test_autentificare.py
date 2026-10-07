"""Teste offline pentru autentificarea AD (app/autentificare.py).

Fără AD real. Logica (validare, roluri, limitare, sesiuni, jurnal) se testează cu un
verificator simulat; drumul real prin `ldap3` se testează cu un DC fals pe loopback
(LDAPS cu certificat generat aici, bind simplu, căutări), cu un port unde nu ascultă
nimeni și cu o adresă nerutabilă (TEST-NET-1, RFC 5737).

Rulare:  python app/test_autentificare.py
"""

import datetime
import hashlib
import json
import os
import socket
import ssl
import sys
import tempfile
import threading
import time
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AICI)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import autentificare  # noqa: E402

REGULA_IMBRICATA = "1.2.840.113556.1.4.1941"
GRUP_ADMIN = "CN=MCC-Admin,OU=Grupuri,DC=banca,DC=example"
GRUP_ANALIST = "CN=MCC-Analist,OU=Grupuri,DC=banca,DC=example"
PAROLA = "Parola-Secreta-123!"


class Ceas:
    """Ceas simulat, ca expirările de ore să se testeze în milisecunde."""

    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def avans(self, s):
        self.t += s


def config(**schimbari):
    c = dict(url="ldaps://dc01.banca.example:636", domeniu="banca.example", baza="DC=banca,DC=example",
             grup_admin=GRUP_ADMIN, grup_analist=GRUP_ANALIST, ca=None, sesiune_ore=8)
    c.update(schimbari)
    return autentificare.Config(**c)


CONTURI = {
    "ana": (PAROLA, "Ana Analist", "analist"),
    "adi": (PAROLA, "Adi Admin", "admin"),
    "fara": (PAROLA, "Fără Rol", None),
    "anonim": (PAROLA, "", "analist"),
    "ciudat": (PAROLA, "Ciudat", "root"),
}


class Simulat:
    """Verificatorul injectat: (nume, rol) pentru parola bună, None pentru cea greșită."""

    def __init__(self, conturi=CONTURI, intarziere=0):
        self.conturi = conturi
        self.intarziere = intarziere
        self.apeluri = []
        self.lacat = threading.Lock()

    def __call__(self, utilizator, parola):
        with self.lacat:
            self.apeluri.append(utilizator)
        if self.intarziere:
            time.sleep(self.intarziere)
        cont = self.conturi.get(utilizator)
        if cont is None or cont[0] != parola:
            return None
        return cont[1], cont[2]


class Baza(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="autentificare_test_")
        self.jurnal_vechi = autentificare.CALE_JURNAL
        autentificare.CALE_JURNAL = os.path.join(self.dir, "loguri", "autentificare.log")
        self.ceas = Ceas()
        self.ver = Simulat()
        self.a = autentificare.Autentificator(config(), verificator=self.ver, ceas=self.ceas)

    def tearDown(self):
        autentificare.CALE_JURNAL = self.jurnal_vechi

    def jurnal(self):
        try:
            with open(autentificare.CALE_JURNAL, encoding="utf-8") as f:
                return [json.loads(r) for r in f]
        except FileNotFoundError:
            return []

    def text_jurnal(self):
        try:
            with open(autentificare.CALE_JURNAL, encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return ""


# ---------------------------------------------------------------- cerințele 1, 2: validarea

class Validare(Baza):
    def test_numele_scurt_din_variante(self):
        for u in ("ana", "ANA", " ana ", "LIBRA\\ana", "ana@banca.example", "Ana@ALTCEVA.RO", "libra\\Ana"):
            r = self.a.autentifica(u, PAROLA, "10.0.0.1")
            self.assertTrue(r.ok, u)
            self.assertEqual(r.utilizator, "ana", u)
        self.assertEqual(set(self.ver.apeluri), {"ana"})

    def test_utilizator_invalid_nu_ajunge_la_ad(self):
        for u in ("", " ", "*)(", "ana*", "a)(sAMAccountName=*", "*", "an\na", "ana\x00", "ana b", "a" * 65,
                  "DOM\\a\\b", "ăna", "ana;x", "@banca.example", "DOM\\", "(ana)", None, 3, ["ana"], {"u": "ana"}):
            r = self.a.autentifica(u, PAROLA, "10.0.0.1")
            self.assertFalse(r.ok, repr(u))
            self.assertEqual(r.motiv, "invalid", repr(u))
        self.assertEqual(self.ver.apeluri, [])

    def test_lungimea_utilizatorului(self):
        self.a.autentifica("a" * 64, PAROLA, "10.0.0.1")
        self.assertEqual(self.ver.apeluri, ["a" * 64])
        self.a.autentifica("a" * 65, PAROLA, "10.0.0.1")
        self.assertEqual(len(self.ver.apeluri), 1)

    def test_parola_goala_spatii_sau_prea_lunga(self):
        for p in ("", " ", "  \t\n", None, 123, ["x"], "x" * 257):
            r = self.a.autentifica("ana", p, "10.0.0.1")
            self.assertEqual(r.motiv, "invalid", repr(p)[:20])
        self.assertEqual(self.ver.apeluri, [])
        # 256 de caractere trec de validare (le refuză AD-ul, nu noi)
        self.assertEqual(self.a.autentifica("ana", "x" * 256, "10.0.0.1").motiv, "invalid")
        self.assertEqual(self.ver.apeluri, ["ana"])
        # parola nu se „curăță”: spațiile sunt ale ei
        self.ver.conturi = {"ana": (" " + PAROLA + " ", "Ana", "analist")}
        self.assertTrue(self.a.autentifica("ana", " " + PAROLA + " ", "10.0.0.1").ok)


# ---------------------------------------------------------------- rolurile

class Roluri(Baza):
    def test_admin_si_analist(self):
        r = self.a.autentifica("adi", PAROLA, "10.0.0.1")
        self.assertEqual(r, autentificare.Rezultat(True, "adi", "Adi Admin", "admin", None))
        r = self.a.autentifica("ana", PAROLA, "10.0.0.1")
        self.assertEqual(r, autentificare.Rezultat(True, "ana", "Ana Analist", "analist", None))

    def test_fara_rol(self):
        r = self.a.autentifica("fara", PAROLA, "10.0.0.1")
        self.assertFalse(r.ok)
        self.assertEqual((r.motiv, r.rol), ("fara_rol", None))
        # un rol necunoscut întors de verificator nu dă acces
        r = self.a.autentifica("ciudat", PAROLA, "10.0.0.1")
        self.assertEqual((r.ok, r.motiv, r.rol), (False, "fara_rol", None))

    def test_parola_gresita(self):
        r = self.a.autentifica("ana", "alta", "10.0.0.1")
        self.assertEqual((r.ok, r.motiv), (False, "invalid"))

    def test_nume_gol_devine_utilizatorul(self):
        self.assertEqual(self.a.autentifica("anonim", PAROLA, "10.0.0.1").nume, "anonim")


# ---------------------------------------------------------------- cerința 6: limitarea

class Limitare(Baza):
    def test_al_saselea_pe_utilizator_nu_mai_intreaba_ad(self):
        for _ in range(5):
            self.assertEqual(self.a.autentifica("ana", "gresit", "10.0.0.1").motiv, "invalid")
        self.assertEqual(len(self.ver.apeluri), 5)
        r = self.a.autentifica("ana", PAROLA, "10.0.0.2")       # chiar cu parola bună, de pe alt IP
        self.assertEqual((r.ok, r.motiv), (False, "limitat"))
        self.assertEqual(len(self.ver.apeluri), 5)
        # alt utilizator nu e afectat
        self.assertTrue(self.a.autentifica("adi", PAROLA, "10.0.0.1").ok)

    def test_variantele_de_scriere_se_numara_impreuna(self):
        for u in ("ana", "ANA", "LIBRA\\ana", "ana@banca.example", "Ana"):
            self.assertEqual(self.a.autentifica(u, "gresit", "10.0.0.1").motiv, "invalid")
        self.assertEqual(self.a.autentifica("aNa", PAROLA, "10.0.0.1").motiv, "limitat")

    def test_succesul_sterge_contorul_utilizatorului(self):
        for _ in range(4):
            self.a.autentifica("ana", "gresit", "10.0.0.1")
        self.assertTrue(self.a.autentifica("ana", PAROLA, "10.0.0.1").ok)
        for _ in range(5):
            self.assertEqual(self.a.autentifica("ana", "gresit", "10.0.0.1").motiv, "invalid")
        self.assertEqual(self.a.autentifica("ana", PAROLA, "10.0.0.1").motiv, "limitat")

    def test_fereastra_de_15_minute(self):
        for _ in range(5):
            self.a.autentifica("ana", "gresit", "10.0.0.1")
        self.ceas.avans(14 * 60)
        self.assertEqual(self.a.autentifica("ana", PAROLA, "10.0.0.1").motiv, "limitat")
        self.ceas.avans(60 + 1)
        self.assertTrue(self.a.autentifica("ana", PAROLA, "10.0.0.1").ok)

    def test_douazeci_pe_ip(self):
        for i in range(20):
            self.assertEqual(self.a.autentifica(f"u{i}", "gresit", "10.0.0.9").motiv, "invalid")
        n = len(self.ver.apeluri)
        self.assertEqual(self.a.autentifica("ana", PAROLA, "10.0.0.9").motiv, "limitat")
        self.assertEqual(len(self.ver.apeluri), n)
        self.assertTrue(self.a.autentifica("ana", PAROLA, "10.0.0.10").ok)

    def test_succesul_nu_sterge_contorul_ip(self):
        for i in range(19):
            self.a.autentifica(f"u{i}", "gresit", "10.0.0.9")
        self.assertTrue(self.a.autentifica("ana", PAROLA, "10.0.0.9").ok)
        self.a.autentifica("u99", "gresit", "10.0.0.9")
        self.assertEqual(self.a.autentifica("adi", PAROLA, "10.0.0.9").motiv, "limitat")

    def test_fara_rol_si_indisponibil_nu_se_numara(self):
        for _ in range(8):
            self.assertEqual(self.a.autentifica("fara", PAROLA, "10.0.0.1").motiv, "fara_rol")

        def cade(u, p):
            raise TimeoutError("timed out")
        a = autentificare.Autentificator(config(), verificator=cade, ceas=self.ceas)
        for _ in range(8):
            self.assertEqual(a.autentifica("ana", PAROLA, "10.0.0.1").motiv, "indisponibil")
        a._verificator = self.ver
        self.assertTrue(a.autentifica("ana", PAROLA, "10.0.0.1").ok)

    def test_validarea_esuata_nu_se_numara(self):
        for _ in range(10):
            self.a.autentifica("ana", "", "10.0.0.1")
        self.assertTrue(self.a.autentifica("ana", PAROLA, "10.0.0.1").ok)

    def test_incercarile_simultane_nu_depasesc_limita(self):
        """10 încercări greșite deodată pe același cont: AD-ul primește cel mult 5."""
        ver = Simulat(intarziere=0.3)
        a = autentificare.Autentificator(config(), verificator=ver)
        rezultate = []
        fire = [threading.Thread(target=lambda: rezultate.append(a.autentifica("ana", "gresit", "10.0.0.1")))
                for _ in range(10)]
        for f in fire:
            f.start()
        for f in fire:
            f.join()
        self.assertLessEqual(len(ver.apeluri), 5)
        self.assertEqual(len(rezultate), 10)
        self.assertTrue(all(not r.ok for r in rezultate))


# ---------------------------------------------------------------- cerințele 5, 7: indisponibil

class Indisponibil(Baza):
    def test_timeout_devine_indisponibil(self):
        def lent(u, p):
            raise socket.timeout("timed out")
        a = autentificare.Autentificator(config(), verificator=lent, ceas=self.ceas)
        r = a.autentifica("ana", PAROLA, "10.0.0.1")
        self.assertEqual(r, autentificare.Rezultat(False, "ana", "", None, "indisponibil"))

    def test_detaliul_doar_in_jurnal_si_fara_parola(self):
        def vorbaret(u, p):
            raise RuntimeError(f"bind eșuat pentru {u} cu {p} la dc01:636")
        a = autentificare.Autentificator(config(), verificator=vorbaret, ceas=self.ceas)
        r = a.autentifica("ana", PAROLA, "10.0.0.1")
        self.assertEqual(r.motiv, "indisponibil")
        self.assertNotIn("dc01", repr(r))
        rand = self.jurnal()[-1]
        self.assertIn("RuntimeError", rand["detaliu"])
        self.assertIn("dc01:636", rand["detaliu"])
        self.assertNotIn(PAROLA, self.text_jurnal())

    def test_raspuns_neasteptat_de_la_verificator(self):
        a = autentificare.Autentificator(config(), verificator=lambda u, p: "da", ceas=self.ceas)
        self.assertEqual(a.autentifica("ana", PAROLA, "10.0.0.1").motiv, "indisponibil")

    def test_maximum_patru_verificari_simultane(self):
        poarta = threading.Event()
        intrate = []
        lacat = threading.Lock()

        def blocat(u, p):
            with lacat:
                intrate.append(u)
            poarta.wait(10)
            return "Nume", "analist"
        a = autentificare.Autentificator(config(), verificator=blocat)
        rezultate = {}
        fire = [threading.Thread(target=lambda u=u: rezultate.__setitem__(u, a.autentifica(u, PAROLA, "10.0.0.1")))
                for u in ("u1", "u2", "u3", "u4")]
        for f in fire:
            f.start()
        t = time.time() + 5
        while len(intrate) < 4 and time.time() < t:
            time.sleep(0.01)
        self.assertEqual(len(intrate), 4)
        t0 = time.monotonic()
        r = a.autentifica("u5", PAROLA, "10.0.0.1")
        self.assertLess(time.monotonic() - t0, 1)
        self.assertEqual(r.motiv, "indisponibil")
        self.assertNotIn("u5", intrate)
        poarta.set()
        for f in fire:
            f.join()
        self.assertTrue(all(r.ok for r in rezultate.values()))
        # locurile s-au eliberat
        self.assertTrue(a.autentifica("u5", PAROLA, "10.0.0.1").ok)


# ---------------------------------------------------------------- cerința 4: configurația

ENV_BUN = {
    "MCC_LDAP_URL": "ldaps://dc01.banca.example:636",
    "MCC_LDAP_DOMENIU": "banca.example",
    "MCC_LDAP_BAZA": "DC=banca,DC=example",
    "MCC_LDAP_GRUP_ADMIN": GRUP_ADMIN,
    "MCC_LDAP_GRUP_ANALIST": GRUP_ANALIST,
}


class Configurare(Baza):
    def test_din_mediu(self):
        c = autentificare.Config.din_mediu(ENV_BUN)
        self.assertEqual((c.url, c.domeniu, c.baza, c.grup_admin, c.grup_analist, c.ca, c.sesiune_ore),
                         (ENV_BUN["MCC_LDAP_URL"], "banca.example", "DC=banca,DC=example", GRUP_ADMIN,
                          GRUP_ANALIST, None, 8))
        self.assertIsNone(c.problema())
        self.assertEqual(autentificare.Config.din_mediu(dict(ENV_BUN, MCC_SESIUNE_ORE="4")).sesiune_ore, 4)

    def test_doar_ldaps(self):
        for url in ("ldap://dc01.banca.example:389", "http://dc01.banca.example", "dc01.banca.example:636",
                    "ldapi:///tmp/x", "ldaps://", "ldaps://:636", "ldaps://dc01.banca.example/DC=x?y",
                    "ldaps://u:p@dc01.banca.example", "ldaps://dc01.banca.example:abc"):
            p = autentificare.Config.din_mediu(dict(ENV_BUN, MCC_LDAP_URL=url)).problema()
            self.assertIsNotNone(p, url)
            self.assertIn("MCC_LDAP_URL", p, url)
        self.assertIn("ldaps", autentificare.Config.din_mediu(
            dict(ENV_BUN, MCC_LDAP_URL="ldap://dc01.banca.example")).problema())
        for url in ("LDAPS://dc01.banca.example", "ldaps://dc01.banca.example", "ldaps://dc01.banca.example:3269/"):
            self.assertIsNone(autentificare.Config.din_mediu(dict(ENV_BUN, MCC_LDAP_URL=url)).problema(), url)

    def test_variabile_lipsa(self):
        for cheie in ENV_BUN:
            env = dict(ENV_BUN)
            del env[cheie]
            self.assertIn(cheie, autentificare.Config.din_mediu(env).problema() or "")
            self.assertIn(cheie, autentificare.Config.din_mediu(dict(env, **{cheie: "  "})).problema() or "")
        self.assertIsNotNone(autentificare.Config.din_mediu({}).problema())

    def test_domeniul_doar_nume_dns(self):
        for d in ("banca.example)(x", "banca example", "banca.example/x", "@banca.example"):
            self.assertIn("MCC_LDAP_DOMENIU", autentificare.Config.din_mediu(
                dict(ENV_BUN, MCC_LDAP_DOMENIU=d)).problema() or "", d)

    def test_ca(self):
        lipsa = os.path.join(self.dir, "nu_exista.pem")
        self.assertIn("MCC_LDAP_CA", autentificare.Config.din_mediu(dict(ENV_BUN, MCC_LDAP_CA=lipsa)).problema())
        exista = os.path.join(self.dir, "ca.pem")
        with open(exista, "w") as f:
            f.write("x")
        c = autentificare.Config.din_mediu(dict(ENV_BUN, MCC_LDAP_CA=exista))
        self.assertEqual(c.ca, exista)
        self.assertIsNone(c.problema())

    def test_ore_de_sesiune(self):
        for ore in ("abc", "0", "-3", "nan"):
            self.assertIn("MCC_SESIUNE_ORE", autentificare.Config.din_mediu(
                dict(ENV_BUN, MCC_SESIUNE_ORE=ore)).problema() or "", ore)

    def test_configuratia_invalida_raspunde_indisponibil(self):
        a = autentificare.Autentificator(config(url="ldap://dc01.banca.example"), ceas=self.ceas)
        t0 = time.monotonic()
        r = a.autentifica("ana", PAROLA, "10.0.0.1")
        self.assertLess(time.monotonic() - t0, 2)     # fără nicio cerere în rețea
        self.assertEqual(r.motiv, "indisponibil")
        self.assertIn("ldaps", self.jurnal()[-1]["detaliu"])


# ---------------------------------------------------------------- cerința 3: filtrele LDAP

class Filtre(unittest.TestCase):
    def test_filtrul_utilizatorului(self):
        self.assertEqual(autentificare.filtru_utilizator("ana", "banca.example"),
                         "(&(objectClass=user)(|(sAMAccountName=ana)(userPrincipalName=ana@banca.example)))")
        # chiar dacă validarea ar lăsa să treacă ceva, valoarea e escapată
        self.assertEqual(autentificare.filtru_utilizator("a*)(b\\", "banca.example"),
                         "(&(objectClass=user)(|(sAMAccountName=a\\2a\\29\\28b\\5c)"
                         "(userPrincipalName=a\\2a\\29\\28b\\5c@banca.example)))")

    def test_filtrul_grupului(self):
        self.assertEqual(autentificare.filtru_grup("ana", GRUP_ADMIN),
                         f"(&(sAMAccountName=ana)(memberOf:{REGULA_IMBRICATA}:={GRUP_ADMIN}))")
        dn = "CN=MCC (Admin)*,OU=Grupuri\\, speciale,DC=banca,DC=example"
        self.assertEqual(autentificare.filtru_grup("ana", dn),
                         f"(&(sAMAccountName=ana)(memberOf:{REGULA_IMBRICATA}:="
                         "CN=MCC \\28Admin\\29\\2a,OU=Grupuri\\5c, speciale,DC=banca,DC=example))")


# ---------------------------------------------------------------- cerința 8: sesiunile

class SesiuniTest(unittest.TestCase):
    def setUp(self):
        self.ceas = Ceas()
        self.s = autentificare.Sesiuni(ore_inactivitate=8, ceas=self.ceas)

    def test_identificator_aleator_tinut_doar_ca_hash(self):
        a = self.s.creeaza("ana", "Ana", "analist")
        b = self.s.creeaza("ana", "Ana", "analist")
        self.assertNotEqual(a, b)
        self.assertGreaterEqual(len(a), 43)
        self.assertRegex(a, r"^[A-Za-z0-9_-]+$")
        intern = repr(self.s._sesiuni)
        self.assertNotIn(a, intern)
        self.assertIn(hashlib.sha256(a.encode()).hexdigest(), self.s._sesiuni)

    def test_citeste(self):
        sid = self.s.creeaza("ana", "Ana Analist", "analist")
        self.assertEqual(self.s.citeste(sid), {"utilizator": "ana", "nume": "Ana Analist", "rol": "analist"})
        for rau in ("", "x", sid + "x", sid[:-1], None, 123, b"abc", ["x"], "a" * 5000):
            self.assertIsNone(self.s.citeste(rau), repr(rau)[:30])

    def test_expira_la_inactivitate(self):
        sid = self.s.creeaza("ana", "Ana", "analist")
        self.ceas.avans(8 * 3600 - 5)
        self.assertIsNotNone(self.s.citeste(sid))
        alt = self.s.creeaza("adi", "Adi", "admin")
        self.ceas.avans(8 * 3600 + 1)
        self.assertIsNone(self.s.citeste(alt))
        self.ceas.t -= 8 * 3600                       # nici dacă ceasul ar reveni: a fost ștearsă
        self.assertIsNone(self.s.citeste(alt))

    def test_activitatea_reinnoieste(self):
        s = autentificare.Sesiuni(ore_inactivitate=4, ceas=self.ceas)
        sid = s.creeaza("ana", "Ana", "analist")
        for _ in range(2):                            # 8 h în total, sub plafonul de 12 h
            self.ceas.avans(4 * 3600 - 5)
            self.assertIsNotNone(s.citeste(sid))
        self.ceas.avans(4 * 3600 + 1)
        self.assertIsNone(s.citeste(sid))

    def test_ore_configurabile(self):
        s = autentificare.Sesiuni(ore_inactivitate=1, ceas=self.ceas)
        sid = s.creeaza("ana", "Ana", "analist")
        self.ceas.avans(3600 + 1)
        self.assertIsNone(s.citeste(sid))

    def test_maximum_12_ore_de_la_logare(self):
        sid = self.s.creeaza("ana", "Ana", "analist")
        for _ in range(12):
            self.ceas.avans(3600 - 10)
            self.assertIsNotNone(self.s.citeste(sid))
        self.ceas.avans(12 * 3600 - 12 * (3600 - 10) + 1)
        self.assertIsNone(self.s.citeste(sid))
        # și cu inactivitate mai lungă decât 12 h, plafonul rămâne
        s = autentificare.Sesiuni(ore_inactivitate=48, ceas=self.ceas)
        sid = s.creeaza("ana", "Ana", "analist")
        self.ceas.avans(12 * 3600 + 1)
        self.assertIsNone(s.citeste(sid))

    def test_maximum_10_sesiuni_pe_utilizator(self):
        alt = self.s.creeaza("adi", "Adi", "admin")
        ids = []
        for _ in range(11):
            ids.append(self.s.creeaza("ana", "Ana", "analist"))
            self.ceas.avans(1)
        self.assertIsNone(self.s.citeste(ids[0]))          # cea mai veche a ieșit
        self.assertTrue(all(self.s.citeste(i) for i in ids[1:]))
        self.assertIsNotNone(self.s.citeste(alt))
        self.assertEqual(sum(1 for v in self.s._sesiuni.values() if v["utilizator"] == "ana"), 10)

    def test_sterge(self):
        sid = self.s.creeaza("ana", "Ana", "analist")
        self.assertEqual(self.s.sterge(sid)["utilizator"], "ana")
        self.assertIsNone(self.s.citeste(sid))
        self.assertIsNone(self.s.sterge(sid))
        self.assertIsNone(self.s.sterge(None))

    def test_curatare(self):
        for u in ("ana", "adi", "ion"):
            self.s.creeaza(u, u, "analist")
        self.ceas.avans(9 * 3600)
        viu = self.s.creeaza("vio", "Vio", "admin")
        self.s.curata()
        self.assertEqual(len(self.s._sesiuni), 1)
        self.assertIsNotNone(self.s.citeste(viu))

    def test_curatare_periodica_fara_apel_explicit(self):
        for u in ("ana", "adi", "ion"):
            self.s.creeaza(u, u, "analist")
        self.ceas.avans(9 * 3600)
        self.s.citeste("oricare")
        self.assertEqual(len(self.s._sesiuni), 0)


# ---------------------------------------------------------------- cerința 10: jurnalul

class Jurnal(Baza):
    def test_o_linie_json_pe_eveniment(self):
        autentificare.jurnal({"eveniment": "proba", "utilizator": "ana", "ip": "10.0.0.1"})
        autentificare.jurnal({"eveniment": "proba2", "parola": PAROLA, "corp": {"parola": PAROLA}})
        randuri = self.jurnal()
        self.assertEqual([r["eveniment"] for r in randuri], ["proba", "proba2"])
        self.assertIn("moment", randuri[0])
        self.assertNotIn(PAROLA, self.text_jurnal())

    def test_logarile_in_jurnal_fara_parola(self):
        self.a.autentifica("adi", PAROLA, "10.0.0.1")                 # reușită
        self.a.autentifica("ana", PAROLA + "x", "10.0.0.1")           # parolă greșită
        self.a.autentifica("fara", PAROLA, "10.0.0.1")                # fără rol
        self.a.autentifica(PAROLA, PAROLA, "10.0.0.1")                # parola scrisă în câmpul utilizatorului
        self.a.autentifica("ana", "", "10.0.0.1")
        for _ in range(5):
            self.a.autentifica("ion", PAROLA, "10.0.0.1")
        self.a.autentifica("ion", PAROLA, "10.0.0.1")                 # limitat

        def vorbaret(u, p):
            raise OSError(f"conexiune închisă după bind cu parola {p}")
        a = autentificare.Autentificator(config(), verificator=vorbaret, ceas=self.ceas)
        a.autentifica("adi", PAROLA, "10.0.0.1")
        self.assertNotIn(PAROLA, self.text_jurnal())
        randuri = self.jurnal()
        self.assertEqual(len(randuri), 12)
        self.assertEqual({r["eveniment"] for r in randuri}, {"logare"})
        reusita = randuri[0]
        self.assertEqual((reusita["utilizator"], reusita["ip"], reusita["rezultat"], reusita["rol"]),
                         ("adi", "10.0.0.1", "reusit", "admin"))
        self.assertEqual([r["motiv"] for r in randuri[1:3]], ["invalid", "fara_rol"])
        self.assertIsNone(randuri[3]["utilizator"])
        self.assertEqual(randuri[10]["motiv"], "limitat")
        self.assertEqual(randuri[11]["motiv"], "indisponibil")
        self.assertTrue(all(r["rezultat"] == "esuat" for r in randuri[1:]))


# ---------------------------------------------------------------- cerința 11: scurtătura locală

class ModLocal(unittest.TestCase):
    def test_mod_local(self):
        self.assertEqual(autentificare.mod_local({"MCC_AUTH_LOCAL": "admin"}, {}), "admin")
        self.assertEqual(autentificare.mod_local({"MCC_AUTH_LOCAL": " Analist "}, {}), "analist")
        for env in ({}, {"MCC_AUTH_LOCAL": ""}, {"MCC_AUTH_LOCAL": "root"}, {"MCC_AUTH_LOCAL": "1"},
                    {"MCC_AUTH_LOCAL": "admin", "MCC_AUTH_OBLIGATORIE": "1"},
                    {"MCC_AUTH_LOCAL": "admin", "MCC_AUTH_OBLIGATORIE": " 1 "}):
            self.assertIsNone(autentificare.mod_local(env, {}), env)
        for antete in ({"X-Real-IP": "10.0.0.1"}, {"X-Real-IP": ""}):
            self.assertIsNone(autentificare.mod_local({"MCC_AUTH_LOCAL": "admin"}, antete), antete)

    def test_verifica_pornire(self):
        for env in ({}, {"MCC_AUTH_LOCAL": "admin"}, {"MCC_AUTH_LOCAL": "analist"}, {"MCC_AUTH_OBLIGATORIE": "1"},
                    {"MCC_AUTH_OBLIGATORIE": "1", "MCC_AUTH_LOCAL": ""}):
            self.assertIsNone(autentificare.verifica_pornire(env), env)
        for env in ({"MCC_AUTH_OBLIGATORIE": "1", "MCC_AUTH_LOCAL": "admin"},
                    {"MCC_AUTH_OBLIGATORIE": "1", "MCC_AUTH_LOCAL": "analist"},
                    {"MCC_AUTH_OBLIGATORIE": "1", "MCC_AUTH_LOCAL": "orice"}):
            self.assertIn("MCC_AUTH_LOCAL", autentificare.verifica_pornire(env) or "", env)
        # o valoare greșită pe laptop: oprire cu mesaj, nu logare cerută fără explicație
        self.assertIn("MCC_AUTH_LOCAL", autentificare.verifica_pornire({"MCC_AUTH_LOCAL": "root"}) or "")


# ---------------------------------------------------------------- drumul real, prin ldap3

def _tlv(tag, continut):
    n = len(continut)
    if n < 0x80:
        lungime = bytes([n])
    else:
        b = n.to_bytes((n.bit_length() + 7) // 8, "big")
        lungime = bytes([0x80 | len(b)]) + b
    return bytes([tag]) + lungime + continut


def _sir(text):
    return _tlv(0x04, text.encode("utf-8"))


def _rezultat_ldap(tag, cod, mesaj=""):
    return _tlv(tag, _tlv(0x0A, bytes([cod])) + _sir("") + _sir(mesaj))


def _mesaj(mid, op):
    return _tlv(0x30, _tlv(0x02, mid.to_bytes(mid.bit_length() // 8 + 1, "big")) + op)


def _exact(s, n):
    date = b""
    while len(date) < n:
        bucata = s.recv(n - len(date))
        if not bucata:
            return None
        date += bucata
    return date


def _citeste_ber(s):
    cap = _exact(s, 2)
    if cap is None:
        return None
    n = cap[1]
    if n & 0x80:
        lb = _exact(s, n & 0x7F)
        if lb is None:
            return None
        n = int.from_bytes(lb, "big")
        cap += lb
    corp = _exact(s, n)
    return None if corp is None else cap + corp


def _ber(date):
    """[(tag, conținut)] pentru o succesiune de TLV-uri BER (lungimi definite, cum trimite ldap3).

    Nu pyasn1 cu specificația din ldap3: pyasn1 0.6 nu decodează AttributeValueAssertion cu ea,
    deși octeții sunt corecți (ldap3 doar codează cu ea, nu și decodează).
    """
    i, rezultat = 0, []
    while i < len(date):
        tag, n = date[i], date[i + 1]
        i += 2
        if n & 0x80:
            k = n & 0x7F
            n = int.from_bytes(date[i:i + k], "big")
            i += k
        rezultat.append((tag, date[i:i + n]))
        i += n
    return rezultat


def _filtru(tag, continut):
    if tag in (0xA0, 0xA1):                      # and, or
        return ("and" if tag == 0xA0 else "or", [_filtru(t, c) for t, c in _ber(continut)])
    if tag == 0xA3:                              # equalityMatch
        (_, atr), (_, val) = _ber(continut)
        return ("eq", atr.decode("utf-8"), val.decode("utf-8"))
    if tag == 0xA9:                              # extensibleMatch: [1] regula, [2] atribut, [3] valoare
        p = dict(_ber(continut))
        return ("ext", p.get(0x81, b"").decode("utf-8"), p.get(0x82, b"").decode("utf-8"),
                p.get(0x83, b"").decode("utf-8"))
    return (hex(tag),)


def _text_filtru(f):
    """Filtrul primit, cu valorile așa cum ajung la DC (deci fără escape)."""
    if f[0] in ("and", "or"):
        return "(" + {"and": "&", "or": "|"}[f[0]] + "".join(_text_filtru(x) for x in f[1]) + ")"
    if f[0] == "eq":
        return f"({f[1]}={f[2]})"
    if f[0] == "ext":
        return f"({f[2]}:{f[1]}:={f[3]})"
    return f"({f[0]}?)"


def _potriveste(f, cont):
    if f[0] == "and":
        return all(_potriveste(x, cont) for x in f[1])
    if f[0] == "or":
        return any(_potriveste(x, cont) for x in f[1])
    if f[0] == "eq":
        atr, val = f[1].lower(), f[2].lower()
        if atr == "objectclass":
            return val in ("top", "person", "user")
        if atr == "samaccountname":
            return val == cont["sam"].lower()
        if atr == "userprincipalname":
            return val == cont["upn"].lower()
        if atr == "memberof":       # fără regula AD: doar apartenența directă, ca la un DC real
            return val in {g.lower() for g in cont["direct"]}
        return False
    if f[0] == "ext":
        _, regula, atr, val = f
        return (atr.lower() == "memberof" and regula == REGULA_IMBRICATA
                and val.lower() in {g.lower() for g in cont["direct"] + cont["imbricate"]})
    return False


class DCFals:
    """Un DC minimal pe loopback: LDAPS cu certificatul dat, bind simplu, căutări pe conturile date.

    Ca un AD: bind cu UPN-ul explicit sau cel implicit (sAMAccountName@domeniu), 49 la parolă
    greșită, apartenența imbricată doar prin regula 1.2.840.113556.1.4.1941, iar fiecare căutare
    pe subarbore întoarce și o referință (DomainDnsZones), pe care clientul nu trebuie s-o urmeze.
    """

    def __init__(self, cert, cheie, conturi, domeniu="banca.example", tace=False, cod_bind=None):
        self.conturi, self.domeniu, self.tace, self.cod_bind = conturi, domeniu, tace, cod_bind
        self.ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.ctx.load_cert_chain(cert, cheie)
        self.legari, self.cautari, self.conexiuni = [], [], 0
        try:
            self.sock = socket.socket(socket.AF_INET6)
            self.sock.bind(("::1", 0))
        except OSError:
            self.sock = socket.socket()
            self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(16)
        self.port = self.sock.getsockname()[1]
        threading.Thread(target=self._asculta, daemon=True).start()

    def inchide(self):
        self.sock.close()

    def _asculta(self):
        while True:
            try:
                c, _ = self.sock.accept()
            except OSError:
                return
            self.conexiuni += 1
            threading.Thread(target=self._conexiune, args=(c,), daemon=True).start()

    def _cont_legat(self, nume, parola):
        for cont in self.conturi:
            if nume.lower() in (cont["upn"].lower(), f"{cont['sam']}@{self.domeniu}".lower()):
                return cont if cont["parola"] == parola else None
        return None

    def _conexiune(self, c):
        try:
            with self.ctx.wrap_socket(c, server_side=True) as s:
                while True:
                    date = _citeste_ber(s)
                    if date is None:
                        return
                    if self.tace:
                        continue
                    (_, mesaj), = _ber(date)
                    (_, mid), (tip, op) = _ber(mesaj)[:2]
                    mid = int.from_bytes(mid, "big")
                    if tip == 0x60:                          # bindRequest: versiune, nume, [0] parola
                        parti = _ber(op)
                        nume, parola = parti[1][1].decode("utf-8"), parti[2][1].decode("utf-8")
                        self.legari.append(nume)
                        if self.cod_bind is not None:
                            cod = self.cod_bind
                        else:
                            cod = 0 if self._cont_legat(nume, parola) else 49
                        mesaj = "80090308: LdapErr: DSID-0C09044E, data 52e, v4563" if cod == 49 else ""
                        s.sendall(_mesaj(mid, _rezultat_ldap(0x61, cod, mesaj)))
                    elif tip == 0x63:                        # searchRequest
                        parti = _ber(op)
                        f = _filtru(*parti[6])
                        atribute = [c.decode("utf-8") for _, c in _ber(parti[7][1])]
                        self.cautari.append((parti[0][1].decode("utf-8"), _text_filtru(f), atribute))
                        for cont in self.conturi:
                            if _potriveste(f, cont):
                                valori = {"displayName": [cont["displayName"]] if cont["displayName"] else [],
                                          "sAMAccountName": [cont["sam"]]}
                                lista = b"".join(_tlv(0x30, _sir(a) + _tlv(0x31, b"".join(_sir(v) for v in valori[a])))
                                                 for a in atribute if a in valori)
                                s.sendall(_mesaj(mid, _tlv(0x64, _sir(cont["dn"]) + _tlv(0x30, lista))))
                        s.sendall(_mesaj(mid, _tlv(0x73, _sir(
                            "ldaps://DomainDnsZones.banca.example/DC=DomainDnsZones,DC=banca,DC=example"))))
                        s.sendall(_mesaj(mid, _rezultat_ldap(0x65, 0)))
                    else:       # unbind
                        return
        except (OSError, ssl.SSLError):
            return


def _cont(sam, direct=(), imbricate=(), upn=None, nume=None, parola=PAROLA):
    return {"sam": sam, "upn": upn or f"{sam}@banca.example", "parola": parola,
            "displayName": f"{sam.capitalize()} Test" if nume is None else nume,
            "dn": f"CN={sam},OU=Utilizatori,DC=banca,DC=example",
            "direct": list(direct), "imbricate": list(imbricate)}


def _certificat(dir_, nume_fisier, dns):
    """Certificat autosemnat pentru numele dat (propria lui autoritate)."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID
    cheie = ec.generate_private_key(ec.SECP256R1())
    pub = cheie.public_key()
    subiect = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, dns)])
    acum = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(subiect).issuer_name(subiect).public_key(pub)
            .serial_number(x509.random_serial_number())
            .not_valid_before(acum - datetime.timedelta(days=1))
            .not_valid_after(acum + datetime.timedelta(days=1))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName(dns)]), critical=False)
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False, key_encipherment=False,
                                         data_encipherment=False, key_agreement=False, key_cert_sign=True,
                                         crl_sign=True, encipher_only=False, decipher_only=False), critical=True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(pub), critical=False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(pub), critical=False)
            .sign(cheie, hashes.SHA256()))
    cale_cert = os.path.join(dir_, nume_fisier + ".pem")
    cale_cheie = os.path.join(dir_, nume_fisier + ".key")
    with open(cale_cert, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    with open(cale_cheie, "wb") as f:
        f.write(cheie.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                    serialization.NoEncryption()))
    return cale_cert, cale_cheie


try:
    import cryptography  # noqa: F401  (doar pentru certificatele din test; nu e dependența aplicației)
    ARE_CRYPTOGRAPHY = True
except ImportError:
    ARE_CRYPTOGRAPHY = False


class LdapFaraServer(Baza):
    """Drumul real (`ldap3`), până la „nu răspunde nimeni”."""

    def test_port_inchis(self):
        a = autentificare.Autentificator(config(url="ldaps://127.0.0.1:1"), ceas=self.ceas)
        t0 = time.monotonic()
        r = a.autentifica("ana", PAROLA, "10.0.0.1")
        self.assertLess(time.monotonic() - t0, 12)
        self.assertEqual(r, autentificare.Rezultat(False, "ana", "", None, "indisponibil"))
        self.assertIn("LDAPSocketOpenError", self.jurnal()[-1]["detaliu"])
        self.assertNotIn(PAROLA, self.text_jurnal())

    def test_adresa_nerutabila_cade_dupa_timeout_de_conectare(self):
        a = autentificare.Autentificator(config(url="ldaps://192.0.2.1:636"), ceas=self.ceas)
        t0 = time.monotonic()
        r = a.autentifica("ana", PAROLA, "10.0.0.1")
        durata = time.monotonic() - t0
        self.assertEqual(r.motiv, "indisponibil")
        self.assertLess(durata, autentificare.TIMEOUT_CONECTARE + 4)
        print(f"\n    (192.0.2.1:636 -> indisponibil după {durata:.1f} s; "
              f"{self.jurnal()[-1]['detaliu'][:90]})", end=" ")


@unittest.skipUnless(ARE_CRYPTOGRAPHY, "fără pachetul cryptography nu se pot genera certificatele de test")
class LdapCuDCFals(Baza):
    @classmethod
    def setUpClass(cls):
        cls.dir_cert = tempfile.mkdtemp(prefix="autentificare_cert_")
        cls.cert, cls.cheie = _certificat(cls.dir_cert, "localhost", "localhost")
        cls.cert_strain, cls.cheie_strain = _certificat(cls.dir_cert, "strain", "dc-test.invalid")
        cls.conturi = [
            _cont("ana", direct=["CN=Echipa,OU=Grupuri,DC=banca,DC=example"], imbricate=[GRUP_ANALIST],
                  nume="Ana Analist"),
            _cont("adi", direct=[GRUP_ADMIN, GRUP_ANALIST], nume="Adi Admin"),
            _cont("ion", direct=["CN=Altceva,OU=Grupuri,DC=banca,DC=example"]),
            _cont("dan", direct=[GRUP_ANALIST], upn="daniel.pop@banca.example", nume=""),
            _cont("eva", direct=["CN=MCC (Admin),OU=Grupuri\\, speciale,DC=banca,DC=example"]),
        ]

    def setUp(self):
        super().setUp()
        self.dc = None

    def tearDown(self):
        if self.dc:
            self.dc.inchide()
        super().tearDown()

    def porneste(self, cert=None, cheie=None, ca="implicit", conturi=None, grup_admin=GRUP_ADMIN, **kw_dc):
        self.dc = DCFals(cert or self.cert, cheie or self.cheie, conturi or self.conturi, **kw_dc)
        c = config(url=f"ldaps://localhost:{self.dc.port}", ca=self.cert if ca == "implicit" else ca,
                   grup_admin=grup_admin)
        return autentificare.Autentificator(c, ceas=self.ceas)

    def test_certificat_necunoscut_refuzat_inainte_de_parola(self):
        a = self.porneste(ca=None)         # depozitul sistemului nu are certificatul de test
        r = a.autentifica("ana", PAROLA, "10.0.0.1")
        self.assertEqual(r.motiv, "indisponibil")
        self.assertRegex(self.jurnal()[-1]["detaliu"], "(?i)certificate verify failed")
        self.assertEqual(self.dc.legari, [])     # parola n-a plecat spre un server neverificat

    def test_numele_serverului_diferit_de_certificat_refuzat(self):
        a = self.porneste(cert=self.cert_strain, cheie=self.cheie_strain, ca=self.cert_strain)
        r = a.autentifica("ana", PAROLA, "10.0.0.1")
        self.assertEqual(r.motiv, "indisponibil")
        self.assertIn("doesn't match", self.jurnal()[-1]["detaliu"])
        self.assertEqual(self.dc.legari, [])

    def test_analist_prin_grup_imbricat(self):
        a = self.porneste()
        r = a.autentifica("LIBRA\\Ana", PAROLA, "10.0.0.1")
        self.assertEqual(r, autentificare.Rezultat(True, "ana", "Ana Analist", "analist", None))
        self.assertEqual(self.dc.legari, ["ana@banca.example"])        # bind cu UPN
        baza, filtru, atribute = self.dc.cautari[0]
        self.assertEqual(baza, "DC=banca,DC=example")
        self.assertEqual(filtru, "(&(objectClass=user)(|(sAMAccountName=ana)(userPrincipalName=ana@banca.example)))")
        self.assertIn("displayName", atribute)
        filtre_grup = [f for _, f, _ in self.dc.cautari[1:]]
        self.assertEqual(filtre_grup, [f"(&(sAMAccountName=ana)(memberOf:{REGULA_IMBRICATA}:={GRUP_ADMIN}))",
                                       f"(&(sAMAccountName=ana)(memberOf:{REGULA_IMBRICATA}:={GRUP_ANALIST}))"])

    def test_in_ambele_grupuri_e_admin(self):
        a = self.porneste()
        r = a.autentifica("adi", PAROLA, "10.0.0.1")
        self.assertEqual((r.ok, r.rol, r.nume), (True, "admin", "Adi Admin"))

    def test_fara_grup_fara_rol(self):
        a = self.porneste()
        r = a.autentifica("ion", PAROLA, "10.0.0.1")
        self.assertEqual((r.ok, r.motiv), (False, "fara_rol"))

    def test_parola_gresita_49(self):
        a = self.porneste()
        r = a.autentifica("ana", PAROLA + "x", "10.0.0.1")
        self.assertEqual((r.ok, r.motiv), (False, "invalid"))
        self.assertEqual(self.dc.cautari, [])
        self.assertNotIn(PAROLA, self.text_jurnal())

    def test_alt_cod_la_bind_e_indisponibil_si_nu_se_numara(self):
        a = self.porneste(cod_bind=51)      # busy
        for _ in range(7):
            self.assertEqual(a.autentifica("ana", PAROLA, "10.0.0.1").motiv, "indisponibil")
        self.assertIn("busy", self.jurnal()[-1]["detaliu"])

    def test_upn_diferit_de_samaccountname(self):
        a = self.porneste()
        # bind cu UPN-ul implicit (dan@domeniu), contul are alt UPN explicit
        r = a.autentifica("dan", PAROLA, "10.0.0.1")
        self.assertEqual((r.ok, r.rol, r.nume), (True, "analist", "dan"))

    def test_dn_de_grup_cu_paranteze_si_virgula_escapata(self):
        dn = "CN=MCC (Admin),OU=Grupuri\\, speciale,DC=banca,DC=example"
        a = self.porneste(grup_admin=dn)
        r = a.autentifica("eva", PAROLA, "10.0.0.1")
        self.assertEqual((r.ok, r.rol), (True, "admin"))
        self.assertEqual(self.dc.cautari[1][1], f"(&(sAMAccountName=eva)(memberOf:{REGULA_IMBRICATA}:={dn}))")

    def test_doua_conturi_pentru_acelasi_nume_refuzat(self):
        """Contul X are UPN-ul explicit „ana@…”, iar contul ana alt UPN: identitatea e ambiguă."""
        conturi = [_cont("ana", direct=[GRUP_ANALIST], upn="ana.vechi@banca.example"),
                   _cont("altul", direct=[GRUP_ADMIN], upn="ana@banca.example")]
        a = self.porneste(conturi=conturi)
        r = a.autentifica("ana", PAROLA, "10.0.0.1")
        self.assertFalse(r.ok)
        self.assertEqual(r.motiv, "indisponibil")
        self.assertIn("ambigu", self.jurnal()[-1]["detaliu"])

    def test_raspuns_care_nu_vine_cade_la_timeout(self):
        vechi = autentificare.TIMEOUT_RASPUNS
        autentificare.TIMEOUT_RASPUNS = 1
        try:
            a = self.porneste(tace=True)
            t0 = time.monotonic()
            r = a.autentifica("ana", PAROLA, "10.0.0.1")
            self.assertLess(time.monotonic() - t0, 5)
        finally:
            autentificare.TIMEOUT_RASPUNS = vechi
        self.assertEqual(r.motiv, "indisponibil")


if __name__ == "__main__":
    unittest.main(verbosity=2)
