# ingest/test_tiktok_api.py — offline: requests.post, flux.permite și time.sleep sunt mock.
import datetime
import json
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import tiktok_api as T

CHEIE, SECRET, TOKEN = "cheie-client-123", "SECRET-foarte-secret-456", "clt.token-789"
AZI = datetime.date(2026, 9, 30)


class R:
    """Răspuns requests minimal."""
    def __init__(self, status=200, corp=None, url=T.BAZA):
        self.status_code, self._corp, self.url = status, corp or {}, url
        self.text = json.dumps(self._corp)

    def json(self):
        return self._corp


def ok(data):
    return R(200, {"data": data, "error": {"code": "ok", "message": "", "log_id": "L1"}})


def eroare(status, cod, mesaj=""):
    return R(status, {"data": {}, "error": {"code": cod, "message": mesaj, "log_id": "L2"}})


def r_token():
    return R(200, {"access_token": TOKEN, "expires_in": 7200, "token_type": "Bearer"}, T.URL_TOKEN)


class Baza(unittest.TestCase):
    def setUp(self):
        T.JURNAL.clear()
        T.STARE.update(cheie=CHEIE, secret=SECRET, token=None, expira=0.0, la_rand_429=0)
        for tinta, val in (("tiktok_api.time.sleep", None), ("tiktok_api.flux.permite", True)):
            p = mock.patch(tinta, return_value=val)
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch("tiktok_api.requests.post")
        self.post = p.start()
        self.addCleanup(p.stop)


class TestToken(Baza):
    def test_client_credentials_si_refolosire(self):
        self.post.side_effect = [r_token(), ok({"display_name": "BCR"}), ok({"display_name": "BCR"})]
        T.cere("research/user/info/", {"username": "bcr"}, T.CAMPURI_PROFIL)
        T.cere("research/user/info/", {"username": "bcr"}, T.CAMPURI_PROFIL)
        prima = self.post.call_args_list[0]
        self.assertEqual(prima.args[0], "https://open.tiktokapis.com/v2/oauth/token/")
        self.assertEqual(prima.kwargs["data"]["grant_type"], "client_credentials")
        self.assertEqual(self.post.call_count, 3)          # un singur token pentru două cereri
        self.assertEqual(self.post.call_args.kwargs["headers"]["Authorization"], f"Bearer {TOKEN}")
        self.assertEqual(self.post.call_args.kwargs["headers"]["User-Agent"], T.UA)

    def test_reinnoit_inainte_de_expirare(self):
        self.post.side_effect = [r_token(), r_token()]
        T.token()
        T.STARE["expira"] = time.time() + 100              # sub pragul de 5 minute
        T.token()
        self.assertEqual(self.post.call_count, 2)

    def test_token_refuzat_opreste(self):
        self.post.return_value = R(401, {"error": "invalid_client",
                                         "error_description": f"bad {SECRET}", "log_id": "x"}, T.URL_TOKEN)
        with self.assertRaises(T.Oprire) as c:
            T.token()
        self.assertNotIn(SECRET, str(c.exception))

    def test_robots_interzice(self):
        with mock.patch("tiktok_api.flux.permite", return_value=False):
            with self.assertRaises(T.Oprire):
                T.token()
        self.post.assert_not_called()


class TestPaginare(Baza):
    def test_reclame_pe_search_id(self):
        adv = {"business_id": 11, "business_name": "Banca Comerciala Romana SA", "country_code": "RO"}
        strain = {"business_id": 99, "business_name": "BCR Logistic Trans", "country_code": "RO"}

        def reclama(i, bid=11):
            return {"ad": {"id": i}, "advertiser": {"business_id": bid, "business_name": "x"}}
        self.post.side_effect = [
            r_token(),
            ok({"advertisers": [adv, strain]}),              # „Banca Comerciala Romana"
            ok({"advertisers": [adv]}),                      # „BCR"
            ok({"ads": [reclama(1), reclama(2, bid=77)], "has_more": "true", "search_id": "S1"}),
            ok({"ads": [reclama(3)], "has_more": False, "search_id": "S1"}),
            ok({"ad": {"id": 1, "title": "t1"}}), ok({"ad": {"id": 3, "title": "t3"}}),
        ]
        x = T.reclame_banca("bcr", AZI)
        corp_p2 = self.post.call_args_list[4].kwargs["json"]
        self.assertEqual(corp_p2["search_id"], "S1")
        self.assertEqual(corp_p2["filters"]["country_code_list"], ["RO"])
        self.assertEqual(corp_p2["filters"]["ad_published_date_range"]["max"], "20260930")
        self.assertEqual(corp_p2["max_count"], 10)
        self.assertEqual([r["ad"]["id"] for r in x["reclame"]], [1, 3])
        self.assertEqual([r["ad"]["id"] for r in x["reclame_neatribuite"]], [2])
        self.assertEqual([a["business_id"] for a in x["advertiseri"]], [11])
        self.assertEqual([a["business_id"] for a in x["advertiseri_neatribuiti"]], [99])
        self.assertEqual(x["reclame"][0]["link_biblioteca"], "https://library.tiktok.com/ads/detail/?ad_id=1")
        self.assertEqual(self.post.call_count, 7)

    def test_video_pe_cursor(self):
        gol = ok({"videos": [], "has_more": False, "cursor": 0})
        self.post.side_effect = [
            r_token(), ok({"display_name": "BCR"}),
            ok({"videos": [{"id": 1}], "has_more": True, "cursor": 100, "search_id": "V1"}),
            ok({"videos": [{"id": 2}], "has_more": False, "cursor": 101, "search_id": "V1"}),
            gol, gol,
        ]
        x = T.organic_banca("bcr", {"username": "bcr", "nivel": "RO", "url": "u"}, AZI)
        c2 = self.post.call_args_list[3].kwargs["json"]
        self.assertEqual((c2["cursor"], c2["search_id"]), (100, "V1"))
        self.assertEqual(c2["query"]["and"][0], {"operation": "EQ", "field_name": "username",
                                                 "field_values": ["bcr"]})
        self.assertEqual([v["id"] for v in x["videoclipuri"]], [1, 2])
        self.assertEqual(x["videoclipuri"][0]["link"], "https://www.tiktok.com/@bcr/video/1")

    def test_ferestre_de_cel_mult_30_de_zile(self):
        f = T.ferestre(AZI)
        self.assertEqual(f[0][1], "20260930")
        self.assertEqual(len(f), 3)
        for a, b in f:
            zile = (datetime.datetime.strptime(b, "%Y%m%d") - datetime.datetime.strptime(a, "%Y%m%d")).days
            self.assertLessEqual(zile, 30)


class TestAtribuire(unittest.TestCase):
    def test_potriviri(self):
        cazuri = [
            ("bcr", "Banca Comerciala Romana S.A.", True),
            ("bcr", "BCR", True),
            ("bcr", "BCR SA", True),
            ("bcr", "BCR Banca pentru Locuinte", False),
            ("bcr", "BCRX Logistics", False),
            ("bcr", "Abcr Consulting", False),
            ("bcr-locuinte", "BCR Banca pentru Locuinte SA", True),
            ("brd", "BRD - Groupe Société Générale S.A.", True),
            ("brd", "BRD Transport SRL", False),
            ("ing", "ING Bank N.V. Amsterdam Sucursala Bucuresti", True),
            ("ing", "ING Bank Slaski", False),
            ("ing", "Vikings Shop", False),
            ("raiffeisen", "Raiffeisen Bank S.A.", True),
            ("raiffeisen", "Raiffeisen Bank International AG", False),
            ("intesa", "Intesa Sanpaolo Bank d.d.", False),
            ("tbi", "tbi bank EAD", True),
            ("revolut", "Revolut Bank UAB", True),
            ("libra", "Libra Internet Bank S.A.", True),
            ("libra", "Libra Fashion", False),
            ("cec", "CEC Bank SA", True),
            ("cec", "Cecilia Bankova", False),
        ]
        for slug, nume, asteptat in cazuri:
            with self.subTest(slug=slug, nume=nume):
                self.assertEqual(T.atribuie(slug, nume), asteptat)

    def test_bancile_din_banks_si_csv(self):
        for slug in T.BANCI:
            self.assertNotEqual(T.nume_banca(slug), slug, f"{slug} lipsește din banks.py")
        with open(T.CSV_RETELE, encoding="utf-8") as f:
            din_csv = {l.split(",")[0] for l in f.read().splitlines()[1:] if l}
        self.assertEqual(set(T.BANCI), din_csv)

    def test_conturi_fara_negasit(self):
        c = T.conturi_tiktok()
        self.assertEqual(c["bcr"]["username"], "bcr")
        self.assertEqual(c["ing"]["username"], "ing.romania")
        self.assertNotIn("intesa", c)                      # NEGASIT


class Test429(Baza):
    def test_trei_la_rand_opresc(self):
        self.post.side_effect = [r_token()] + [eroare(429, "rate_limit_exceeded")] * 3
        with self.assertRaises(T.Oprire):
            T.cere("research/user/info/", {"username": "bcr"}, T.CAMPURI_PROFIL)
        self.assertEqual(self.post.call_count, 4)
        pauze = [c.args[0] for c in T.time.sleep.call_args_list]
        self.assertIn(T.ASTEPTARE_429, pauze)

    def test_429_apoi_200_continua(self):
        self.post.side_effect = [r_token(), eroare(429, "rate_limit_exceeded"), ok({"display_name": "x"})]
        self.assertEqual(T.cere("research/user/info/", {}, "f"), {"display_name": "x"})
        self.assertEqual(T.STARE["la_rand_429"], 0)

    def test_cota_zilnica_opreste_imediat(self):
        self.post.side_effect = [r_token(), eroare(429, "daily_quota_limit_exceeded")]
        with self.assertRaises(T.Oprire):
            T.cere("research/video/query/", {}, "f")
        self.assertEqual(self.post.call_count, 2)

    def test_5xx_opreste(self):
        self.post.side_effect = [r_token(), R(503, {})]
        with self.assertRaises(T.Oprire):
            T.cere("research/video/query/", {}, "f")

    def test_refuz_de_scope(self):
        self.post.side_effect = [r_token(), eroare(401, "scope_not_authorized", "no research.data.basic")]
        with self.assertRaises(T.Refuzat):
            T.cere("research/user/info/", {}, "f")

    def test_400_nu_opreste(self):
        self.post.side_effect = [r_token(), eroare(400, "invalid_params", "user not found")]
        self.assertIn("invalid_params", T.cere("research/user/info/", {}, "f")["eroare"])


class TestRetentie(unittest.TestCase):
    def test_sterge_de_la_30_de_zile(self):
        with tempfile.TemporaryDirectory() as d:
            for zile in (31, 30, 29, 0):
                data = AZI - datetime.timedelta(days=zile)
                open(os.path.join(d, f"tiktok_{data.isoformat()}.json"), "w").close()
            vechi = os.path.join(d, "fara_data.json")
            open(vechi, "w").close()
            t = time.time() - 40 * 86400
            os.utime(vechi, (t, t))
            sterse = T.curata(AZI, d)
            self.assertEqual(sorted(sterse), ["fara_data.json", "tiktok_2026-08-30.json",
                                              "tiktok_2026-08-31.json"])
            self.assertEqual(sorted(os.listdir(d)), ["tiktok_2026-09-01.json", "tiktok_2026-09-30.json"])

    def test_constanta(self):
        self.assertEqual(T.RETENTIE_ZILE, 30)


class TestRulareCompleta(Baza):
    """Reclamele refuzate, organicul aprobat: secretul și tokenul nu ajung în fișier."""
    def test_produse_separate_si_fara_secrete(self):
        def raspunde(url, **kw):
            if url == T.URL_TOKEN:
                return r_token()
            if "adlib" in url:
                return eroare(403, "scope_not_authorized", f"echo {TOKEN}")
            if "user/info" in url:
                return ok({"display_name": "Libra"})
            return ok({"videos": [{"id": 5}], "has_more": False, "cursor": 1})
        self.post.side_effect = raspunde
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(T, "DIR", d), \
                mock.patch("tiktok_api.config.cere", side_effect=lambda k: {
                    "TIKTOK_CLIENT_KEY": CHEIE, "TIKTOK_CLIENT_SECRET": SECRET}[k]), \
                mock.patch.object(sys, "argv", ["tiktok_api.py", "--banca", "libra"]), \
                mock.patch("sys.stdout.reconfigure", create=True), \
                mock.patch("builtins.print"):
            T.main()
            cale = os.path.join(d, os.listdir(d)[0])
            with open(cale, encoding="utf-8") as f:
                text = f.read()
        rez = json.loads(text)
        self.assertTrue(rez["acces"]["reclame"].startswith("REFUZAT"))
        self.assertEqual(rez["acces"]["organic"], "ok")
        self.assertNotIn("libra", rez["reclame"])
        self.assertEqual(len(rez["organic"]["libra"]["videoclipuri"]), 3)   # 3 ferestre
        self.assertTrue(rez["cereri"])
        for s in (SECRET, TOKEN, CHEIE):
            self.assertNotIn(s, text)
        for c in self.post.call_args_list:
            self.assertNotIn(SECRET, c.args[0])


if __name__ == "__main__":
    unittest.main()
