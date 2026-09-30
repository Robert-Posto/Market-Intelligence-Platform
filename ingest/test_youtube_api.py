"""Teste offline pentru `youtube_api.py`: nicio cerere, `requests.get` e înlocuit.

Acoperă paginarea playlist-ului de uploads, loturile de 50 la `videos.list`,
retenția de 30 de zile (III.E.4.d), mascarea cheii în jurnal, în fișier și în
mesajele de eroare, și găsirea canalelor pe fișiere reale din Bronze (sărite
dacă fișierele nu sunt pe disc).
"""
import contextlib
import datetime
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock
from urllib.parse import urlencode

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import requests  # noqa: E402
import youtube_api as y  # noqa: E402

CHEIE = "AIzaSyTEST-cheie-secreta-123"


class Raspuns:
    def __init__(self, status, date, url):
        self.status_code = status
        self._date = date
        self.url = url
        self.text = json.dumps(date)

    def json(self):
        return self._date


def raspunde(functie):
    """requests.get fals: `functie(metoda, params)` -> (status, json)."""
    def get(url, params=None, headers=None, timeout=None):
        metoda = url.rsplit("/", 1)[-1]
        status, date = functie(metoda, params)
        return Raspuns(status, date, url + "?" + urlencode(params))
    return get


def pagina(ids, zi, token=None):
    d = {"items": [{"contentDetails": {"videoId": i, "videoPublishedAt": f"{z}T10:00:00Z"}}
                   for i, z in zip(ids, zi)]}
    if token:
        d["nextPageToken"] = token
    return d


class FaraRetea(unittest.TestCase):
    def setUp(self):
        for tinta, val in (("youtube_api.flux.permite", True), ("youtube_api.flux.intarziere", 0),
                           ("youtube_api.time.sleep", None)):
            p = mock.patch(tinta, return_value=val)
            p.start()
            self.addCleanup(p.stop)

    def client(self, functie):
        p = mock.patch("youtube_api.requests.get", side_effect=raspunde(functie))
        self.get = p.start()
        self.addCleanup(p.stop)
        return y.Client(CHEIE, pauza=0)


class TestMascare(FaraRetea):
    def test_masca(self):
        self.assertEqual(y.masca(f"https://x/v3/videos?id=1&key={CHEIE}&part=a"),
                         "https://x/v3/videos?id=1&key=***&part=a")
        self.assertNotIn(CHEIE, y.masca(f"... url: /v3/channels?KEY={CHEIE}"))

    def test_jurnal_fara_cheie(self):
        c = self.client(lambda m, p: (200, {"items": []}))
        c.cere("channels", {"id": "UC1"})
        self.assertEqual(self.get.call_args.kwargs["params"]["key"], CHEIE)   # cheia pleacă
        self.assertNotIn(CHEIE, json.dumps(c.jurnal))                           # dar nu rămâne
        self.assertIn("key=***", c.jurnal[0]["url"])
        self.assertEqual(c.unitati, 1)

    def test_exceptie_fara_cheie(self):
        c = y.Client(CHEIE, pauza=0)
        eroare = requests.ConnectionError(f"Max retries exceeded with url: /v3/channels?key={CHEIE}")
        with mock.patch("youtube_api.requests.get", side_effect=eroare):
            with self.assertRaises(y.Oprire) as ctx:
                c.cere("channels", {"id": "UC1"})
        self.assertNotIn(CHEIE, str(ctx.exception))


class TestErori(FaraRetea):
    def test_cota_depasita_opreste(self):
        c = self.client(lambda m, p: (403, {"error": {"errors": [{"reason": "quotaExceeded"}]}}))
        with self.assertRaises(y.Oprire) as ctx:
            c.cere("videos", {"id": "a"})
        self.assertIn("quotaExceeded", str(ctx.exception))

    def test_cheie_invalida_opreste(self):
        c = self.client(lambda m, p: (400, {"error": {"message": "API key not valid.",
                                                      "errors": [{"reason": "badRequest"}]}}))
        with self.assertRaises(y.Oprire):
            c.cere("channels", {"id": "UC1"})

    def test_404_nu_opreste(self):
        c = self.client(lambda m, p: (404, {"error": {"errors": [{"reason": "playlistNotFound"}]}}))
        self.assertEqual(c.cere("playlistItems", {"playlistId": "UU1"})["eroare"],
                         "HTTP 404 playlistNotFound")

    def test_robots_interzice(self):
        with mock.patch("youtube_api.flux.permite", return_value=False):
            c = self.client(lambda m, p: (200, {}))
            with self.assertRaises(y.Oprire):
                c.cere("channels", {})
        self.get.assert_not_called()


class TestPaginare(FaraRetea):
    def test_se_opreste_la_pagina_care_trece_de_limita(self):
        pagini = {None: pagina([f"a{i}" for i in range(50)], ["2026-09-01"] * 50, "T2"),
                  "T2": pagina(["b1", "b2", "vechi"], ["2026-01-01", "2025-10-01", "2025-09-01"], "T3"),
                  "T3": pagina(["nu-se-cere"], ["2025-08-01"])}
        c = self.client(lambda m, p: (200, pagini[p.get("pageToken")]))
        ids = y.id_uri_din_fereastra(c, "UU1", "2025-09-30")
        self.assertEqual(len(ids), 52)
        self.assertNotIn("vechi", ids)
        self.assertEqual(c.unitati, 2)                  # T3 nu s-a mai cerut
        self.assertEqual(self.get.call_args_list[0].kwargs["params"]["maxResults"], 50)

    def test_ultima_pagina(self):
        c = self.client(lambda m, p: (200, pagina(["x"], ["2026-09-01"])))
        self.assertEqual(y.id_uri_din_fereastra(c, "UU1", "2025-09-30"), ["x"])

    def test_plafon(self):
        c = self.client(lambda m, p: (200, pagina(["x" + str(p.get("pageToken"))], ["2026-09-01"], "T")))
        with mock.patch.object(y, "MAX_PAGINI", 3):
            y.id_uri_din_fereastra(c, "UU1", "2025-09-30")
        self.assertEqual(c.unitati, 3)


class TestLoturi(FaraRetea):
    def test_loturi_de_50(self):
        def videos(m, p):
            return 200, {"items": [{"id": i, "snippet": {"title": "t " + i, "publishedAt": "2026-05-01T00:00:00Z"},
                                    "contentDetails": {"duration": "PT1M5S"},
                                    "statistics": {"viewCount": "10", "likeCount": "2"}}
                                   for i in p["id"].split(",")]}
        c = self.client(videos)
        rez = y.videoclipuri(c, [f"v{i}" for i in range(120)])
        loturi = [len(a.kwargs["params"]["id"].split(",")) for a in self.get.call_args_list]
        self.assertEqual(loturi, [50, 50, 20])
        self.assertEqual(len(rez), 120)
        self.assertEqual(rez[0]["durata_sec"], 65)
        self.assertIsNone(rez[0]["comentarii"])          # comentarii dezactivate: lipsă, nu 0
        self.assertEqual(rez[0]["link"], "https://www.youtube.com/watch?v=v0")

    def test_durata_si_luni(self):
        self.assertEqual(y.secunde("PT1H2M3S"), 3723)
        self.assertEqual(y.secunde("P1DT1S"), 86401)
        self.assertIsNone(y.secunde(None))
        self.assertEqual(y.secunde("P0D"), 0)           # transmisiune live în curs
        self.assertEqual(y.minus_luni(datetime.date(2026, 9, 30), 12), datetime.date(2025, 9, 30))
        self.assertEqual(y.minus_luni(datetime.date(2026, 3, 31), 1), datetime.date(2026, 2, 28))
        self.assertEqual(y.minus_luni(datetime.date(2026, 1, 15), 1), datetime.date(2025, 12, 15))

    def test_estimare(self):
        self.assertEqual(y.unitati_pe_banca(0), 2)
        self.assertEqual(y.unitati_pe_banca(12), 3)
        self.assertEqual(y.unitati_pe_banca(50), 4)      # a doua pagină arată că s-a trecut de limită
        self.assertEqual(y.unitati_pe_banca(150), 8)


class TestRetentie(unittest.TestCase):
    def test_sterge_de_la_30_de_zile(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        azi = datetime.date(2026, 9, 30)
        for zile in (0, 29, 30, 45):
            open(os.path.join(d, f"youtube_{(azi - datetime.timedelta(days=zile)).isoformat()}.json"), "w").close()
        open(os.path.join(d, "altceva_2020-01-01.json"), "w").close()
        self.assertEqual(y.curata(azi, d), ["youtube_2026-08-16.json", "youtube_2026-08-31.json"])
        self.assertEqual(sorted(os.listdir(d)), ["altceva_2020-01-01.json", "youtube_2026-09-01.json",
                                                 "youtube_2026-09-30.json"])

    def test_director_lipsa(self):
        self.assertEqual(y.curata(director=os.path.join(tempfile.gettempdir(), "nu-exista-yt")), [])


class TestExtragere(FaraRetea):
    def raspunsuri(self, m, p):
        if m == "channels":
            if "lipsa" in (p.get("forUsername"), p.get("forHandle", "").lstrip("@")):
                return 200, {"items": []}
            return 200, {"items": [{"id": "UCx", "snippet": {"title": "Banca", "customUrl": "@banca"},
                                    "statistics": {"subscriberCount": "1200", "viewCount": "99",
                                                   "videoCount": "3", "hiddenSubscriberCount": False},
                                    "contentDetails": {"relatedPlaylists": {"uploads": "UUx"}}}]}
        if m == "playlistItems":
            return 200, pagina(["v1", "v2", "v3"], ["2026-09-01", "2026-01-01", "2024-01-01"])
        return 200, {"items": [{"id": i, "snippet": {"title": i}, "contentDetails": {},
                                "statistics": {}} for i in p["id"].split(",")]}

    def test_fisier_cu_data_si_fara_cheie(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        randuri = [{"slug": "brd", "canal": "UCx", "tip": "id", "url_dovada": "https://www.brd.ro/"},
                   {"slug": "ing", "canal": "lipsa", "tip": "user", "url_dovada": "https://ing.ro/"}]
        azi = datetime.date(2026, 9, 30)
        with mock.patch.object(y, "DIR_IESIRE", d), contextlib.redirect_stdout(io.StringIO()):
            rez, cale = y.extrage(self.client(self.raspunsuri), randuri, 12, azi)
            self.assertEqual(os.path.basename(cale), "youtube_2026-09-30.json")
            with open(cale, encoding="utf-8") as f:
                text = f.read()
            self.assertNotIn(CHEIE, text)
            scris = json.loads(text)
            self.assertEqual(scris["data_extragerii"], "2026-09-30")
            self.assertEqual(scris["sterge_la"], "2026-10-30")
            self.assertEqual(scris["banci"]["brd"]["canal"]["abonati"], 1200)
            self.assertEqual([v["id"] for v in scris["banci"]["brd"]["videoclipuri"]], ["v1", "v2"])
            self.assertEqual(scris["banci"]["brd"]["unitati"], 3)
            self.assertEqual(scris["banci"]["ing"]["eroare"], "canal negăsit de API")
            self.assertEqual(scris["unitati_consumate"], 5)      # ING: forUsername + forHandle

            # reluarea: BRD nu se mai cere, ING (cu eroare) da
            c2 = self.client(self.raspunsuri)
            y.extrage(c2, randuri, 12, azi)
            self.assertEqual([a.args[0].rsplit("/", 1)[-1] for a in self.get.call_args_list],
                             ["channels", "channels"])
            self.assertEqual(c2.unitati, 7)

    def test_user_cade_pe_handle(self):
        def r(m, p):
            if "forUsername" in p:
                return 200, {"items": []}
            return self.raspunsuri(m, p)
        c = self.client(r)
        info, eroare = y.canal(c, {"canal": "LibraInternetBank", "tip": "user"})
        self.assertIsNone(eroare)
        self.assertEqual(self.get.call_args.kwargs["params"]["forHandle"], "@LibraInternetBank")
        self.assertEqual(c.unitati, 2)

    def test_custom_verificat(self):
        c = self.client(self.raspunsuri)
        info, eroare = y.canal(c, {"canal": "AltaBanca", "tip": "custom"})
        self.assertIsNone(info)
        self.assertIn("nu e handle-ul", eroare)
        self.assertEqual(self.get.call_args.kwargs["params"]["forHandle"], "@AltaBanca")


class TestDescoperire(unittest.TestCase):
    def test_pagina_sintetica(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        pagini = {
            "a_acasa": b'<link rel="canonical" href="https://www.brd.ro/acasa">'
                       b'<a href="https://www.youtube.com/channel/UCoEyYt1n-eiZ4OLoiqcZofA">yt</a>',
            "b_articol": b'<meta property="og:url" content="https://www.brd.ro/stire">'
                         b'<a href="https://youtube.com/channel/UCoEyYt1n-eiZ4OLoiqcZofA">x</a>'
                         b'<a href="https://www.youtube.com/@Partener%20X">partener</a>',
            "c_presa": b'<link rel="canonical" href="https://www.ziar.ro/brd">'
                       b'<a href="https://www.youtube.com/@AltCanal">nu e site-ul bancii</a>',
            "d_pdf": b"%PDF-1.7 youtube.com/@DinPdf",
        }
        for nume, octeti in pagini.items():
            with open(os.path.join(d, nume), "wb") as f:
                f.write(octeti)
        g = y.descopera([d])
        self.assertEqual(list(g), ["brd"])
        canale = g["brd"]["canale"]
        self.assertEqual(canale[0][:3], ["UCoEyYt1n-eiZ4OLoiqcZofA", "id", 2])
        self.assertEqual(canale[1][:2], ["@Partener X", "handle"])
        rand = {r["slug"]: r for r in y.randuri_csv(g, ["brd", "cec"], {})}
        self.assertEqual(rand["brd"]["stare"], "GASIT")
        self.assertEqual(rand["brd"]["url_dovada"], "https://www.brd.ro/acasa")
        self.assertEqual(rand["cec"]["stare"], "NEGASIT")

    def test_grupul_nu_se_extrage(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        cale = os.path.join(d, "c.csv")
        g = {"pko": {"canale": [["pkobp", "user", 90, "https://www.pkobp.pl/", "bronze/x"]],
                     "pagini": 90, "videoclipuri": {}}}
        y.scrie_csv(y.randuri_csv(g, ["pko"]), cale)
        self.assertEqual(y.citeste_canale(cale), [])


# Fișiere reale din Bronze, cu dovada din date/youtube_canale.csv (30.09.2026).
REALE = {"brd": "UCoEyYt1n-eiZ4OLoiqcZofA", "procredit": "ProCreditBankRomania",
         "salt": "@SaltBankRO", "bcr": "@BCR-BancaComercialaRomana"}


def dovezi():
    try:
        with open(y.CSV_CANALE, encoding="utf-8", newline="") as f:
            import csv
            return {r["slug"]: r for r in csv.DictReader(f)}
    except OSError:
        return {}


class TestBronzeReal(unittest.TestCase):
    def test_canalele_din_fisierele_reale(self):
        randuri = dovezi()
        verificate = 0
        for slug, canal in REALE.items():
            r = randuri.get(slug)
            cale = os.path.join(y.RADACINA, r["fisier_bronze"]) if r else ""
            if not r or not os.path.exists(cale):
                continue
            with open(cale, "rb") as f:
                octeti = f.read()
            self.assertEqual(y.adresa_paginii(octeti)[0], slug, cale)
            gasite = [y.canal_din_link(m)[0] for m in y.RE_CANAL.findall(octeti)]
            self.assertIn(canal, gasite, cale)
            verificate += 1
        if not verificate:
            self.skipTest("fișierele de dovadă nu sunt în Bronze")


if __name__ == "__main__":
    unittest.main()
