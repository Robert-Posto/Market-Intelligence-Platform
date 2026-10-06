"""Teste offline pentru rulările manuale din Overview (app/rulari.py și rutele din server).

Nu pornesc niciun script de colectare: pornirea reală se testează doar cu o
comandă inofensivă (un `python -c` care numără), injectată în locul listei.

Rulare:  python app/test_rulari.py
"""

import http.client
import json
import os
import sys
import tempfile
import threading
import time
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AICI)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import rulari  # noqa: E402

NUMARA = "import time\nfor i in range(600):\n    print('rand', i, flush=True)\n    time.sleep(0.1)"
TEST = [
    {"id": "numara", "nume": "Numără", "ce": "test", "argumente": ["-c", NUMARA],
     "banca": None, "internet": False, "estimare_min": 1},
    {"id": "iese3", "nume": "Iese cu 3", "ce": "test",
     "argumente": ["-c", "print('gata, ăîșț'); raise SystemExit(3)"],
     "banca": "optional", "internet": False, "estimare_min": 2, "estimare_banca_min": 1},
    {"id": "pebanca", "nume": "Pe bancă", "ce": "test", "argumente": ["-c", "pass"],
     "banca": "obligatoriu", "internet": False, "estimare_banca_min": 10},
    # ca joburile din pagina „Rulare manuală”: băncile fluxului de extragere și un produs obligatoriu
    {"id": "peprodus", "nume": "Pe produs", "ce": "test", "argumente": ["-c", "pass"],
     "banca": "obligatoriu", "produs": "obligatoriu", "banci": "extragere", "internet": False,
     "estimare_banca_min": 1},
]
SLUGS = ["bcr", "libra", "vista"]
SLUGS_EXTRAGERE = ["bcr", "cec"]
PRODUSE = ["CONT_ECONOMII", "DEPOZIT_TERMEN"]


def asteapta(conditie, sec=15):
    t = time.time() + sec
    while time.time() < t:
        if conditie():
            return True
        time.sleep(0.1)
    return False


class Baza(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="rulari_test_")
        self.r = rulari.Rulari(comenzi=TEST, dir_rulari=self.dir, slugs=lambda: SLUGS,
                               produse=lambda: PRODUSE, slugs_extragere=lambda: SLUGS_EXTRAGERE)

    def tearDown(self):
        if self.r.curenta:
            try:
                self.r.opreste()
            except rulari.Respins:
                pass
            asteapta(lambda: self.r.curenta is None)


class ListaAlba(Baza):
    def test_id_necunoscut(self):
        for id_c in ("nu-exista", "", None, ["numara"], {"id": "numara"}, "numara; del"):
            with self.assertRaises(rulari.Respins):
                self.r.valideaza(id_c, None)

    def test_banca_necunoscuta(self):
        for b in ("nu-exista", "bcr --de-la-zero", "../bcr", ["bcr"], 3):
            with self.assertRaises(rulari.Respins):
                self.r.valideaza("iese3", b)

    def test_banca_unde_nu_se_poate(self):
        with self.assertRaises(rulari.Respins):
            self.r.valideaza("numara", "bcr")
        with self.assertRaises(rulari.Respins):
            self.r.valideaza("pebanca", None)

    def test_argv_doar_din_lista(self):
        c, b, p = self.r.valideaza("iese3", "bcr")
        self.assertEqual(self.r.argv(c, b, p)[-2:], ["--banca", "bcr"])
        c, b, p = self.r.valideaza("iese3", "")
        self.assertNotIn("--banca", self.r.argv(c, b, p))

    def test_produs(self):
        c, b, p = self.r.valideaza("peprodus", "cec", "CONT_ECONOMII")
        self.assertEqual(self.r.argv(c, b, p)[-4:], ["--banca", "cec", "--produse", "CONT_ECONOMII"])
        # produsul trece doar dacă e în listă, ca un singur element: nimic altceva nu ajunge în argv
        for p in ("NU_EXISTA", "CONT_ECONOMII,DEPOZIT_TERMEN", "CONT_ECONOMII --forteaza", ["CONT_ECONOMII"], 3, None, ""):
            with self.assertRaises(rulari.Respins):
                self.r.valideaza("peprodus", "cec", p)
        # comenzile fără produs nu primesc unul
        with self.assertRaises(rulari.Respins):
            self.r.valideaza("pebanca", "bcr", "CONT_ECONOMII")

    def test_banci_extragere(self):
        # joburile fluxului de comparație iau băncile din banci.json al fluxului, nu din banks.py
        self.r.valideaza("peprodus", "cec", "CONT_ECONOMII")
        with self.assertRaises(rulari.Respins):
            self.r.valideaza("peprodus", "vista", "CONT_ECONOMII")
        with self.assertRaises(rulari.Respins):
            self.r.valideaza("pebanca", "cec")

    def test_comenzile_reale(self):
        """Fiecare comandă reală: script existent în repo, fără parametrii interziși."""
        ids = [c["id"] for c in rulari.COMENZI]
        self.assertEqual(len(ids), len(set(ids)))
        for c in rulari.COMENZI:
            self.assertTrue(os.path.isfile(os.path.join(rulari.RADACINA, c["argumente"][0])), c["id"])
            for interzis in ("--de-la-zero", "--paralel", "--banca"):
                self.assertNotIn(interzis, c["argumente"], c["id"])
            self.assertIn(c["banca"], (None, "optional", "obligatoriu"))
            if "--llm-rezerva" in c["argumente"]:
                self.assertEqual(c.get("mediu", {}).get("MIP_LLM_DOAR_CACHE"), "1", c["id"])
        self.assertFalse(any("tiktok" in a or "google" in a for c in rulari.COMENZI for a in c["argumente"]))


class Securitate(unittest.TestCase):
    def test_host(self):
        for h in ("localhost:8765", "127.0.0.1:8765", "[::1]:8765"):
            self.assertIsNone(rulari.verifica_cerere({"Host": h}, 8765))
        for h in ("", "localhost", "localhost:8799", "evil.com:8765", "127.0.0.1.evil.com:8765", "10.0.0.5:8765"):
            self.assertIsNotNone(rulari.verifica_cerere({"Host": h}, 8765), h)

    def test_origin(self):
        ok = {"Host": "localhost:8765"}
        self.assertIsNone(rulari.verifica_cerere(dict(ok, Origin="http://localhost:8765"), 8765))
        for o in ("http://evil.com", "null", "http://127.0.0.1:8765", "https://localhost:8765"):
            self.assertIsNotNone(rulari.verifica_cerere(dict(ok, Origin=o), 8765), o)
        self.assertIsNotNone(rulari.verifica_cerere(dict(ok, **{"Sec-Fetch-Site": "cross-site"}), 8765))

    def test_token(self):
        ok = {"Host": "localhost:8765"}
        self.assertIsNotNone(rulari.verifica_cerere(ok, 8765, "abc"))
        self.assertIsNotNone(rulari.verifica_cerere(dict(ok, **{"X-MIP-Token": "abd"}), 8765, "abc"))
        self.assertIsNone(rulari.verifica_cerere(dict(ok, **{"X-MIP-Token": "abc"}), 8765, "abc"))


class Pornire(Baza):
    def test_un_singur_proces_si_oprire(self):
        cur = self.r.porneste("numara")
        self.assertTrue(asteapta(lambda: any("rand 3" in x for x in self.r.stare()["curenta"]["jurnal"])))
        with self.assertRaises(rulari.Ocupat) as e:
            self.r.porneste("iese3")
        self.assertIn("Numără", str(e.exception))
        self.r.opreste()
        self.assertTrue(asteapta(lambda: self.r.curenta is None))
        self.assertFalse(rulari._proces_viu(cur["pid"]))
        ist = self.r.istoric()
        self.assertEqual(len(ist), 1)
        self.assertTrue(ist[0]["oprit"])
        self.assertEqual(ist[0]["id"], "numara")
        self.assertFalse(os.path.exists(os.path.join(self.dir, "curenta.json")))
        with self.assertRaises(rulari.Respins):
            self.r.opreste()

    def test_istoric_la_final(self):
        self.r.porneste("iese3", "vista")
        self.assertTrue(asteapta(lambda: self.r.curenta is None))
        r = self.r.istoric()[-1]
        self.assertEqual((r["id"], r["banca"], r["cod"], r["oprit"]), ("iese3", "vista", 3, False))
        self.assertIn("gata, ăîșț", r["ultimele"])
        for k in ("inceput", "sfarsit", "durata_s", "log"):
            self.assertIn(k, r)
        self.assertTrue(os.path.isfile(os.path.join(self.dir, r["log"])))
        ultima = next(c for c in self.r.stare()["comenzi"] if c["id"] == "iese3")["ultima"]
        self.assertEqual(ultima["cod"], 3)

    def test_mediu_fara_cheia_serverului(self):
        """Jobul #172: placeholder-ul din .env-ul serverului ajungea în proces și bătea cheia fluxului."""
        cmd = [{"id": "mediu", "nume": "Mediu", "ce": "test", "banca": None, "internet": False, "estimare_min": 1,
                "argumente": ["-c", "import os; print('CHEIE', os.environ.get('ANTHROPIC_API_KEY'), "
                                    "'MANUAL', os.environ.get('MIP_RULARE_MANUALA'))"],
                "fara_mediu": ["ANTHROPIC_API_KEY"]}]
        r = rulari.Rulari(comenzi=cmd, dir_rulari=self.dir, slugs=lambda: SLUGS)
        os.environ["ANTHROPIC_API_KEY"] = "placeholder"
        try:
            r.porneste("mediu")
            self.assertTrue(asteapta(lambda: r.curenta is None))
        finally:
            del os.environ["ANTHROPIC_API_KEY"]
        self.assertIn("CHEIE None MANUAL 1", r.istoric()[-1]["ultimele"])

    def test_reluare_dupa_repornire(self):
        """Serverul repornit cât rulează ceva nu lasă să pornească al doilea proces."""
        cur = self.r.porneste("numara")
        r2 = rulari.Rulari(comenzi=TEST, dir_rulari=self.dir, slugs=lambda: SLUGS)
        self.assertTrue(r2.curenta and r2.curenta.get("orfan"))
        with self.assertRaises(rulari.Ocupat):
            r2.porneste("iese3")
        self.assertTrue(r2.stare()["curenta"]["dupa_repornire"])
        r2.opreste()
        self.assertTrue(asteapta(lambda: not rulari._proces_viu(cur["pid"])))
        self.assertTrue(asteapta(lambda: r2.stare()["curenta"] is None))
        self.assertTrue(asteapta(lambda: self.r.curenta is None))

    def test_orfan_mort_la_pornire(self):
        with open(os.path.join(self.dir, "curenta.json"), "w", encoding="utf-8") as f:
            json.dump({"id": "numara", "banca": None, "inceput": "2026-10-01T10:00:00+03:00",
                       "t0": time.time() - 30, "pid": 999999, "log": "numara_x.log",
                       "estimare_s": 60, "oprit": False}, f)
        r2 = rulari.Rulari(comenzi=TEST, dir_rulari=self.dir, slugs=lambda: SLUGS)
        self.assertIsNone(r2.curenta)
        r = r2.istoric()[-1]
        self.assertIsNone(r["cod"])
        self.assertIn("repornire", r["nota"])


class Estimare(Baza):
    def scrie(self, randuri):
        with open(os.path.join(self.dir, "istoric.jsonl"), "w", encoding="utf-8") as f:
            for r in randuri:
                f.write(json.dumps(r) + "\n")

    def test_implicit(self):
        self.assertEqual(self.r.estimare("numara"), (60, "implicit", 0))
        self.assertEqual(self.r.estimare("iese3"), (120, "implicit", 0))
        self.assertEqual(self.r.estimare("iese3", "bcr"), (60, "implicit", 0))
        self.assertEqual(self.r.estimare("pebanca", "bcr"), (600, "implicit", 0))

    def test_mediana(self):
        self.scrie([
            {"id": "iese3", "banca": None, "durata_s": 100, "cod": 0, "oprit": False},
            {"id": "iese3", "banca": None, "durata_s": 300, "cod": 0, "oprit": False},
            {"id": "iese3", "banca": None, "durata_s": 200, "cod": 0, "oprit": False},
            {"id": "iese3", "banca": None, "durata_s": 9999, "cod": 1, "oprit": False},   # eșuată
            {"id": "iese3", "banca": None, "durata_s": 5, "cod": None, "oprit": True},    # oprită
            {"id": "iese3", "banca": "bcr", "durata_s": 50, "cod": 0, "oprit": False},
            {"id": "iese3", "banca": "bcr", "durata_s": 70, "cod": 0, "oprit": False},
            {"id": "iese3", "banca": "vista", "durata_s": 10, "cod": 0, "oprit": False},
            {"id": "numara", "banca": None, "durata_s": 7, "cod": 0, "oprit": False},
        ])
        self.assertEqual(self.r.estimare("iese3"), (200, "istoric", 3))
        self.assertEqual(self.r.estimare("iese3", "bcr"), (60, "istoric", 2))
        self.assertEqual(self.r.estimare("iese3", "vista"), (10, "istoric", 1))
        # bancă fără istoric: mediana pe celelalte bănci, nu pe rulările „toate băncile”
        self.assertEqual(self.r.estimare("iese3", "libra"), (50, "istoric", 3))
        self.assertEqual(self.r.estimare("numara"), (7, "istoric", 1))
        c = next(c for c in self.r.stare()["comenzi"] if c["id"] == "iese3")
        self.assertEqual(c["estimare_s"], 200)
        self.assertEqual(c["estimari_banca"], {"bcr": 60, "vista": 10})
        self.assertEqual(c["estimare_banca_s"], 50)


class Http(unittest.TestCase):
    """Rutele din server, pe un port liber, cu lista de test în locul celei reale."""

    @classmethod
    def setUpClass(cls):
        import server
        cls.server_mod = server
        cls.vechi = server.RULARI
        cls.dir = tempfile.mkdtemp(prefix="rulari_http_")
        server.RULARI = rulari.Rulari(comenzi=TEST, dir_rulari=cls.dir, slugs=lambda: SLUGS,
                                      produse=lambda: PRODUSE, slugs_extragere=lambda: SLUGS_EXTRAGERE)
        cls.srv = server.Server(("::", 0), server.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.env_vechi = os.environ.get("MIP_PERMITE_RULARI")

    @classmethod
    def tearDownClass(cls):
        r = cls.server_mod.RULARI
        if r.curenta:
            r.opreste()
            asteapta(lambda: r.curenta is None)
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.server_mod.RULARI = cls.vechi
        if cls.env_vechi is None:
            os.environ.pop("MIP_PERMITE_RULARI", None)
        else:
            os.environ["MIP_PERMITE_RULARI"] = cls.env_vechi

    def setUp(self):
        os.environ["MIP_PERMITE_RULARI"] = "1"

    def cere(self, metoda, cale, corp=None, antete=None, host=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        h = {"Host": host or f"localhost:{self.port}"}
        if corp is not None:
            h["Content-Type"] = "application/json"
            corp = json.dumps(corp)
        h.update(antete or {})
        c.request(metoda, cale, body=corp, headers=h)
        r = c.getresponse()
        d = r.read().decode("utf-8")
        c.close()
        try:
            return r.status, json.loads(d)
        except ValueError:
            return r.status, d

    def token(self):
        return self.cere("GET", "/api/rulari")[1]["token"]

    def test_get(self):
        cod, d = self.cere("GET", "/api/rulari")
        self.assertEqual(cod, 200)
        self.assertTrue(d["activ"])
        self.assertEqual(d["token"], self.server_mod.RULARI.token)
        self.assertEqual([c["id"] for c in d["comenzi"]], ["numara", "iese3", "pebanca", "peprodus"])
        self.assertEqual(d["banci"], SLUGS)
        self.assertEqual(d["banci_joburi"], SLUGS_EXTRAGERE)

    def test_get_inactiv_fara_token(self):
        os.environ["MIP_PERMITE_RULARI"] = "0"
        cod, d = self.cere("GET", "/api/rulari")
        self.assertEqual(cod, 200)
        self.assertFalse(d["activ"])
        self.assertNotIn("token", d)

    def test_get_host_strain(self):
        for h in ("evil.com:%d" % self.port, "localhost:1"):
            self.assertEqual(self.cere("GET", "/api/rulari", host=h)[0], 403)
        self.assertEqual(self.cere("GET", "/api/rulari", antete={"Origin": "http://evil.com"})[0], 403)

    def test_post_refuzat(self):
        t = self.token()
        ok = {"X-MIP-Token": t}
        cazuri = [
            ({}, None),                                                   # fără token
            ({"X-MIP-Token": t[:-1] + ("x" if t[-1] != "x" else "y")}, None),  # token greșit
            (ok, f"evil.com:{self.port}"),                                # Host străin
            (dict(ok, Origin="http://evil.com"), None),                   # Origin străin
            (dict(ok, **{"Sec-Fetch-Site": "cross-site"}), None),
        ]
        for antete, host in cazuri:
            cod, _ = self.cere("POST", "/api/rulari/porneste", {"id": "numara"}, antete, host)
            self.assertEqual(cod, 403, (antete, host))
        self.assertIsNone(self.server_mod.RULARI.curenta)

    def test_post_inactiv(self):
        t = self.token()
        os.environ["MIP_PERMITE_RULARI"] = "0"
        cod, d = self.cere("POST", "/api/rulari/porneste", {"id": "numara"}, {"X-MIP-Token": t})
        self.assertEqual(cod, 403)
        self.assertIn("MIP_PERMITE_RULARI", d["eroare"])
        self.assertIsNone(self.server_mod.RULARI.curenta)

    def test_post_lista_alba_si_formular(self):
        ok = {"X-MIP-Token": self.token()}
        self.assertEqual(self.cere("POST", "/api/rulari/porneste", {"id": "rm -rf"}, ok)[0], 400)
        self.assertEqual(self.cere("POST", "/api/rulari/porneste", {"id": "iese3", "banca": "x; y"}, ok)[0], 400)
        self.assertEqual(self.cere("POST", "/api/rulari/porneste", ["numara"], ok)[0], 400)
        cod, _ = self.cere("POST", "/api/rulari/porneste", None,
                           dict(ok, **{"Content-Type": "application/x-www-form-urlencoded"}))
        self.assertEqual(cod, 415)
        self.assertEqual(self.cere("POST", "/api/altceva", {}, ok)[0], 404)
        self.assertIsNone(self.server_mod.RULARI.curenta)

    def test_pornire_ocupat_oprire(self):
        ok = {"X-MIP-Token": self.token(), "Origin": f"http://localhost:{self.port}"}
        cod, d = self.cere("POST", "/api/rulari/porneste", {"id": "numara"}, ok)
        self.assertEqual(cod, 200, d)
        cod, d = self.cere("POST", "/api/rulari/porneste", {"id": "iese3"}, ok)
        self.assertEqual(cod, 409)
        self.assertIn("rulează deja", d["eroare"])
        self.assertTrue(asteapta(lambda: self.cere("GET", "/api/rulari")[1]["curenta"]["jurnal"]))
        cur = self.cere("GET", "/api/rulari")[1]["curenta"]
        self.assertEqual(cur["id"], "numara")
        self.assertIn("scurs_s", cur)
        self.assertEqual(self.cere("POST", "/api/rulari/opreste", {}, ok)[0], 200)
        self.assertTrue(asteapta(lambda: self.cere("GET", "/api/rulari")[1]["curenta"] is None))
        ultima = next(c for c in self.cere("GET", "/api/rulari")[1]["comenzi"] if c["id"] == "numara")["ultima"]
        self.assertTrue(ultima["oprit"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
