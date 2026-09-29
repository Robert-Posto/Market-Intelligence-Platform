# ingest/test_conformitate_transport.py
"""Regulile comune din stratul de transport (Nicolae, §7.3 și §10.1).

Totul offline: `requests.get` e înlocuit, iar fișierele (copii robots.txt,
jurnalul BLOCAT, cozile) se scriu într-un folder temporar.
"""
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import requests  # noqa: E402
from requests.structures import CaseInsensitiveDict  # noqa: E402

import flux  # noqa: E402
import transport as T  # noqa: E402
from crawler.robots import RegulliRobots  # noqa: E402


def raspuns(status=200, corp=b"", url="https://x.ro/", antete=None, istoric=()):
    r = requests.Response()
    r.status_code, r._content, r.url = status, corp, url
    r.headers = CaseInsensitiveDict(antete or {"Content-Type": "text/html"})
    r.history = list(istoric)
    return r


def reguli(origine, text=""):
    rr = RegulliRobots("test", origine)
    rr._parseaza(text)
    rr.status = "test"
    return rr


PAGINA = ("<html><body><main>" + "Depozit la termen 12 luni 5,5% " * 40
          + "</main></body></html>").encode()


def resetare():
    from urllib3.exceptions import ProtocolError
    return requests.ConnectionError(ProtocolError(
        "Connection aborted.", ConnectionResetError(10054, "An existing connection was forcibly closed")))


class Izolat(unittest.TestCase):
    """Fiecare test cu folderele lui și cu starea din memorie golită."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = self.tmp.name
        self.patchuri = [
            mock.patch.object(flux, "DIR_ROBOTS", os.path.join(d, "robots")),
            mock.patch.object(flux, "JURNAL_BLOCAT", os.path.join(d, "origini_blocate.jsonl")),
            mock.patch.object(flux, "DIR_COADA", os.path.join(d, "origini")),
            mock.patch.object(flux, "_CACHE_ROBOTS", {}),
            mock.patch.object(flux, "_BLOCATE", None),
            mock.patch.object(flux, "_RESETARI", flux.collections.Counter()),
            mock.patch.object(time, "sleep"),      # fără pauzele reale
            mock.patch("sys.stderr", new_callable=lambda: open(os.devnull, "w", encoding="utf-8")),
        ]
        for p in self.patchuri:
            p.start()

    def tearDown(self):
        sys.stderr.close()
        for p in reversed(self.patchuri):
            p.stop()
        self.tmp.cleanup()


# ==========================================================================
# 1. robots.txt pe disc
# ==========================================================================

class TestRobotsPeDisc(Izolat):
    def fisiere(self):
        return sorted(os.listdir(flux.DIR_ROBOTS))

    def test_octetii_si_metadatele(self):
        corp = b"User-agent: *\r\nDisallow: /secret\r\n\xef\xbb\xbf# comentariu\n"
        r = raspuns(200, corp, "https://www.bcr.ro/robots.txt", {"Content-Type": "text/plain"})
        with mock.patch("requests.get", return_value=r):
            rr = flux.reguli_pentru("https://www.bcr.ro/x", "bcr")
        self.assertFalse(rr.permite("https://www.bcr.ro/secret"))   # decizia rămâne
        txt = [f for f in self.fisiere() if f.endswith(".txt")]
        self.assertEqual(len(txt), 1)
        self.assertRegex(txt[0], r"^www\.bcr\.ro_\d{4}-\d\d-\d\dT\d{4}\.txt$")
        with open(os.path.join(flux.DIR_ROBOTS, txt[0]), "rb") as f:
            self.assertEqual(f.read(), corp)                        # byte cu byte
        with open(os.path.join(flux.DIR_ROBOTS, txt[0][:-4] + ".json"), encoding="utf-8") as f:
            meta = json.load(f)
        self.assertEqual((meta["cod_http"], meta["url_final"], meta["abatere"]),
                         (200, "https://www.bcr.ro/robots.txt", False))
        self.assertEqual(meta["octeti"], len(corp))

    def test_nu_suprascrie_niciodata(self):
        r1 = raspuns(200, b"User-agent: *\nDisallow: /a\n", "https://x.ro/robots.txt")
        r2 = raspuns(200, b"User-agent: *\nDisallow: /b\n", "https://x.ro/robots.txt")
        with mock.patch("requests.get", side_effect=[r1, r2]):
            flux.reguli_pentru("https://x.ro/", "x")
            flux._CACHE_ROBOTS.clear()                 # o a doua rulare, același minut
            flux.reguli_pentru("https://x.ro/", "x")
        txt = [f for f in self.fisiere() if f.endswith(".txt")]
        self.assertEqual(len(txt), 2)
        continut = set()
        for f in txt:
            with open(os.path.join(flux.DIR_ROBOTS, f), "rb") as g:
                continut.add(g.read())
        self.assertEqual(continut, {r1.content, r2.content})

    def test_5xx_jurnalizat_si_tratat_ca_permis(self):
        r = raspuns(503, b"<html>maintenance</html>", "https://x.ro/robots.txt")
        with mock.patch("requests.get", return_value=r):
            self.assertTrue(flux.permite("https://x.ro/orice", "x"))
        (js,) = [f for f in self.fisiere() if f.endswith(".json")]
        with open(os.path.join(flux.DIR_ROBOTS, js), encoding="utf-8") as f:
            meta = json.load(f)
        self.assertEqual((meta["cod_http"], meta["abatere"]), (503, True))

    def test_timeout_jurnalizat_fara_corp(self):
        with mock.patch("requests.get", side_effect=requests.Timeout("15 s")):
            self.assertTrue(flux.permite("https://x.ro/orice", "x"))
        self.assertEqual([f[-5:] for f in self.fisiere()], [".json"])
        with open(os.path.join(flux.DIR_ROBOTS, self.fisiere()[0]), encoding="utf-8") as f:
            meta = json.load(f)
        self.assertIsNone(meta["cod_http"])
        self.assertTrue(meta["abatere"])
        self.assertIn("Timeout", meta["eroare"])


# ==========================================================================
# 2 și 3. Curățare și excluderi (funcții pure)
# ==========================================================================

class TestCurata(unittest.TestCase):
    def test_parametrii_de_urmarire(self):
        u = ("https://x.ro/p?utm_source=fb&id=3&gclid=a&dclid=b&gbraid=c&wbraid=d"
             "&gad_source=1&fbclid=e&msclkid=f&sfmc_id=g&mc_cid=h&_hsenc=i&_hsmi=j#top")
        self.assertEqual(flux.curata_url(u), "https://x.ro/p?id=3#top")

    def test_fara_parametri_de_urmarire_ramane_identica(self):
        u = "https://x.ro/p?b=2&a=%20x&&c"
        self.assertEqual(flux.curata_url(u), u)

    def test_query_golit_dispare(self):
        self.assertEqual(flux.curata_url("https://x.ro/p?UTM_Source=x"), "https://x.ro/p")

    def test_nu_taie_parametri_asemanatori(self):
        u = "https://x.ro/p?utmx=1&gclid_nu=2&promo=3"
        self.assertEqual(flux.curata_url(u), u)


class TestExcluderi(unittest.TestCase):
    def test_se_cer(self):
        for u in ("https://www.bcr.ro/ro/persoane-fizice/credite",
                  "https://www.ing.ro/promotii?id=4",
                  "https://www.george.bcr.ro/ce-este-george"):
            self.assertIsNone(flux.motiv_excludere(u), u)

    def test_recomandari(self):
        for u in ("https://x.ro/card?promotion=ABC", "https://x.ro/mgmp/invita",
                  "https://revolut.com/referral?code=1", "https://x.ro/a?b=1&promotion=2"):
            self.assertIn("recomandare", flux.motiv_excludere(u), u)

    def test_castigatori(self):
        for u in ("https://x.ro/campanii/castigatori-vara", "https://x.ro/c%C3%A2%C8%99tig%C4%83tori",
                  "https://x.ro/câștigătorii-campaniei", "https://x.ro/en/Winners.pdf"):
            self.assertIn("câștigători", flux.motiv_excludere(u), u)

    def test_onboarding(self):
        for u in ("https://online.bcr.ro/x", "https://banking.x.ro/", "https://george.bcr.ro/register",
                  "https://www.x.ro/aplica-online/card", "https://cloud.email.ing.ro/p"):
            self.assertIn("onboarding", flux.motiv_excludere(u), u)

    def test_previzualizare(self):
        for u in ("https://review.gem.erste-group.net/doc.pdf", "https://staging.x.ro/",
                  "https://www-staging.x.ro/"):
            self.assertIn("previzualizare", flux.motiv_excludere(u), u)


class TestAduExcluderi(Izolat):
    def test_exclus_nu_se_cere(self):
        with mock.patch("requests.get") as get:
            rez = T.adu("https://x.ro/castigatori", "x", {})
        self.assertEqual(rez.verdict, "EXCLUS")
        self.assertIn("câștigători", rez.nota)
        get.assert_not_called()

    def test_se_cere_adresa_curatata(self):
        flux._CACHE_ROBOTS["https://x.ro"] = reguli("https://x.ro")
        with mock.patch("requests.get", return_value=raspuns(200, PAGINA)) as get:
            rez = T.adu("https://x.ro/p?utm_source=a&id=1", "x", {})
        self.assertEqual(rez.verdict, "OK")
        self.assertEqual(get.call_args.args[0], "https://x.ro/p?id=1")
        self.assertFalse(get.call_args.kwargs["allow_redirects"])


# ==========================================================================
# 4. Robots pe fiecare pas al redirectului
# ==========================================================================

class TestRedirect(Izolat):
    def setUp(self):
        super().setUp()
        flux._CACHE_ROBOTS["https://a.ro"] = reguli("https://a.ro")
        flux._CACHE_ROBOTS["https://b.ro"] = reguli("https://b.ro", "User-agent: *\nDisallow: /secret\n")

    def test_pas_interzis_nu_se_mai_cere(self):
        cereri = []

        def get(url, **kw):
            cereri.append(url)
            if url == "https://a.ro/p":
                return raspuns(302, b"", url, {"Location": "https://b.ro/secret/doc.pdf"})
            return raspuns(200, PAGINA, url)
        with mock.patch("requests.get", side_effect=get):
            rez = T.adu("https://a.ro/p", "a", {})
        self.assertEqual(rez.verdict, "ROBOTS")
        self.assertEqual(cereri, ["https://a.ro/p"])       # b.ro/secret nu s-a cerut
        self.assertIn("b.ro/secret", rez.nota)

    def test_pas_permis_curatat_si_urmat(self):
        cereri = []

        def get(url, **kw):
            cereri.append(url)
            if url == "https://a.ro/p":
                return raspuns(301, b"", url, {"Location": "/q?utm_medium=x&k=1"})
            return raspuns(200, PAGINA, url)
        with mock.patch("requests.get", side_effect=get):
            rez = T.adu("https://a.ro/p", "a", {})
        self.assertEqual((rez.verdict, rez.url_final), ("OK", "https://a.ro/q?k=1"))
        self.assertEqual(cereri, ["https://a.ro/p", "https://a.ro/q?k=1"])

    def test_pas_spre_previzualizare_exclus(self):
        with mock.patch("requests.get", return_value=raspuns(
                302, b"", "https://a.ro/doc", {"Location": "https://review.a.ro/doc.pdf"})) as get:
            rez = T.adu("https://a.ro/doc", "a", {})
        self.assertEqual(rez.verdict, "EXCLUS")
        self.assertEqual(get.call_count, 1)

    def test_limita_de_pasi(self):
        with mock.patch("requests.get", return_value=raspuns(
                302, b"", "https://a.ro/x", {"Location": "https://a.ro/x"})) as get:
            rez = T.adu("https://a.ro/x", "a", {})
        self.assertEqual(rez.verdict, "REDIRECTURI")
        self.assertEqual(get.call_count, T.MAX_PASI_REDIRECT + 1)

    def test_garda_playwright(self):
        class Cadru:
            parent_frame = None

        class Cerere:
            def __init__(self, url):
                self.url, self.frame = url, Cadru()

            def is_navigation_request(self):
                return True

        class Ruta:
            def __init__(self, url):
                self.request, self.oprita, self.lasata = Cerere(url), False, False

            def abort(self, motiv):
                self.oprita = True

            def continue_(self):
                self.lasata = True

        refuzuri = []
        garda = T._garda_navigare("a", refuzuri)
        bun, rau = Ruta("https://a.ro/pagina"), Ruta("https://b.ro/secret")
        garda(bun)
        garda(rau)
        self.assertTrue(bun.lasata and rau.oprita)
        self.assertEqual([r.verdict for r in refuzuri], ["ROBOTS"])


# ==========================================================================
# 5. BLOCAT pe origine, păstrat între rulări; coada pe origine
# ==========================================================================

class TestBlocat(Izolat):
    def setUp(self):
        super().setUp()
        flux._CACHE_ROBOTS["https://x.ro"] = reguli("https://x.ro")

    def test_doua_resetari_blocheaza_originea(self):
        with mock.patch("requests.get", side_effect=resetare()) as get:
            rez = T.adu("https://x.ro/a", "x", {})
            self.assertEqual(rez.verdict, "BLOCAT")
            self.assertEqual(get.call_count, 2)            # o reîncercare, apoi BLOCAT
            rez = T.adu("https://x.ro/b", "x", {})
            self.assertEqual(get.call_count, 2)            # nicio cerere în plus
        self.assertEqual(rez.verdict, "BLOCAT")
        self.assertIn("jurnal", rez.nota)
        self.assertFalse(flux.permite("https://x.ro/c", "x"))

    def test_o_singura_resetare_nu_blocheaza(self):
        with mock.patch("requests.get", side_effect=[resetare(), raspuns(200, PAGINA)]):
            self.assertEqual(T.adu("https://x.ro/a", "x", {}).verdict, "OK")
        self.assertIsNone(flux.blocat("https://x.ro/"))

    def test_waf_blocheaza_originea_403_simplu_doar_sursa(self):
        with mock.patch("requests.get", return_value=raspuns(403, b"Forbidden")):
            self.assertEqual(T.adu("https://x.ro/a", "x", {}).verdict, "BLOCAT")
        self.assertIsNone(flux.blocat("https://x.ro/"))    # ca înainte: doar sursa
        waf = b"<html><title>Access Denied</title>Reference #18.2f</html>"
        with mock.patch("requests.get", return_value=raspuns(403, waf)):
            self.assertEqual(T.adu("https://x.ro/b", "x", {}).verdict, "BLOCAT")
        self.assertIsNotNone(flux.blocat("https://x.ro/"))

    def test_jurnalul_se_citeste_la_rularea_urmatoare(self):
        flux.marcheaza_blocat("https://x.ro/a", "conexiune resetată de 2 ori", "x")
        flux._BLOCATE = None                               # „proces nou"
        flux._CACHE_ROBOTS.clear()
        with mock.patch("requests.get") as get:
            rez = T.adu("https://x.ro/b", "x", {})
            flux.reguli_pentru("https://x.ro/", "x")       # nici robots.txt nu se cere
        get.assert_not_called()
        self.assertEqual(rez.verdict, "BLOCAT")
        flux.deblocheaza("https://x.ro", "decizie Robert, test")
        flux._BLOCATE = None
        self.assertIsNone(flux.blocat("https://x.ro/"))
        with open(flux.JURNAL_BLOCAT, encoding="utf-8") as f:
            self.assertEqual([json.loads(l)["actiune"] for l in f], ["BLOCAT", "DEBLOCAT"])

    def test_e_resetare(self):
        self.assertTrue(flux.e_resetare(resetare()))
        self.assertFalse(flux.e_resetare(requests.Timeout("x")))


class TestCoada(Izolat):
    def test_doua_fire_nu_se_suprapun(self):
        intervale = []

        def cerere():
            with flux.coada_origine("https://x.ro/a"):
                inceput = time.perf_counter()
                threading.Event().wait(0.05)     # o „cerere" care durează
                intervale.append((inceput, time.perf_counter()))
        fire = [threading.Thread(target=cerere) for _ in range(3)]
        for f in fire:
            f.start()
        for f in fire:
            f.join()
        intervale.sort()
        self.assertEqual(len(intervale), 3)
        for (_, sf), (inc, _) in zip(intervale, intervale[1:]):
            self.assertLessEqual(sf, inc)

    def test_pauza_de_la_cererea_anterioara(self):
        with flux.coada_origine("https://x.ro/a"):
            pass
        with flux.coada_origine("https://x.ro/b", pauza=5):
            pass
        (apel,) = time.sleep.call_args_list
        self.assertGreater(apel.args[0], 4)

    def test_reintrare_in_acelasi_fir(self):
        with flux.coada_origine("https://x.ro/a"):
            with flux.coada_origine("https://x.ro/robots.txt"):
                pass


if __name__ == "__main__":
    unittest.main()
