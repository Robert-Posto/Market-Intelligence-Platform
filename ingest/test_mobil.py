# ingest/test_mobil.py
"""Track-ul iOS (load_mobil.py, itunes_lookup.py): fără rețea.

Reparațiile din documentul lui Nicolae (§10.1 punctele 2 și 5, §4.5):
UA importat, cererile prin transport (robots.txt), istoricul păstrat,
descrierea salvată. Testul pe bază rulează într-o tranzacție anulată.
"""
import io
import json
import os
import re
import sys
import unittest
from unittest import mock

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import crawler
import flux
import load_mobil as L
import transport as T

RADACINA = os.path.dirname(AICI)


def _text(*parti):
    with io.open(os.path.join(*parti), encoding="utf-8") as f:
        return f.read()


def _ok(octeti, url="https://itunes.apple.com/lookup"):
    return T.Rezultat("OK", octeti, url, "http", "HTTP 200")


class TestUA(unittest.TestCase):
    def test_itunes_lookup_importa_ecusonul(self):
        import itunes_lookup
        self.assertIs(itunes_lookup.USER_AGENT, crawler.UA)
        src = _text(AICI, "itunes_lookup.py")
        self.assertNotIn("contact:", src)


class TestRetea(unittest.TestCase):
    def test_lookup_grupat_un_singur_apel_prin_transport(self):
        corp = json.dumps({"resultCount": 2, "results": [
            {"trackId": 111, "version": "1.0", "description": "Aplicația A"},
            {"trackId": 222, "version": "2.0"}]}).encode()
        with mock.patch.object(L.transport, "adu", return_value=_ok(corp)) as adu:
            rez = L.lookup_grupat([111, 222, 333], {})
        adu.assert_called_once()
        url, proprietar = adu.call_args[0][:2]
        self.assertEqual(url, "https://itunes.apple.com/lookup?id=111,222,333&country=ro")
        self.assertEqual(proprietar, "apple")
        self.assertEqual(set(rez), {"111", "222"})        # 333 nu mai există în magazin
        self.assertEqual(rez["111"]["description"], "Aplicația A")

    def test_robots_interzice_nicio_cerere(self):
        with mock.patch.object(flux, "permite", return_value=False), \
             mock.patch.object(flux, "blocat", return_value=None), \
             mock.patch("requests.get", side_effect=AssertionError("cerere trimisă")):
            with self.assertRaises(L.Refuzat) as ctx:
                L.lookup_grupat([111], {})
            self.assertIn("ROBOTS", str(ctx.exception))
            intrari, distributie, motiv = L.pagina_app("111", {})
        self.assertIsNone(intrari)
        self.assertIsNone(distributie)
        self.assertIn("ROBOTS", motiv)

    def test_origine_blocat_nicio_cerere(self):
        with mock.patch.object(flux, "blocat", return_value="429"), \
             mock.patch("requests.get", side_effect=AssertionError("cerere trimisă")):
            with self.assertRaises(L.Refuzat) as ctx:
                L.lookup_grupat([111], {})
        self.assertIn("BLOCAT", str(ctx.exception))

    def test_fara_requests_direct(self):
        src = _text(AICI, "load_mobil.py")
        self.assertNotRegex(src, r"requests\.get|^import requests")

    def test_pagina_app_citeste_datele_serializate(self):
        date = {"x": [{"$kind": "Review", "id": "r1", "rating": 5, "title": "Bună"},
                      {"ratingCounts": [10, 2, 1, 0, 3]}]}
        corp = ('<html><script type="application/json" id="serialized-server-data">'
                + json.dumps(date) + "</script></html>").encode()
        with mock.patch.object(L.transport, "adu", return_value=_ok(corp)) as adu:
            intrari, distributie, motiv = L.pagina_app("111", {})
        self.assertEqual(adu.call_args[0][0], "https://apps.apple.com/ro/app/id111")
        self.assertEqual([x["id"] for x in intrari], ["r1"])
        self.assertEqual(distributie, [10, 2, 1, 0, 3])
        self.assertIsNone(motiv)


class CursorFals:
    def __init__(self):
        self.comenzi = []

    def execute(self, sql, params=None):
        self.comenzi.append((sql, params))

    def fetchone(self):
        return (7,)


class TestIstoric(unittest.TestCase):
    def test_nicio_stergere(self):
        src = _text(AICI, "load_mobil.py")
        self.assertNotRegex(src, re.compile(r"DELETE\s+FROM", re.I))

    def test_versiunea_upsert_cu_descriere(self):
        cur = CursorFals()
        app = {"version": "3.1", "releaseNotes": "Remedieri", "description": "Banca în buzunar",
               "averageUserRating": 4.5, "userRatingCount": 1200}
        self.assertEqual(L.scrie_versiune(cur, 5, "111", app), 7)
        sql, params = cur.comenzi[0]
        self.assertIn("ON CONFLICT (id_banca, platforma, versiune) DO UPDATE", sql)
        self.assertIn("vazut_ultima", sql)
        self.assertIn("Banca în buzunar", params)

    def test_capturile_upsert_fara_dubluri_in_lot(self):
        prinse = {}

        def ev(cur, sql, valori, template=None):
            prinse.update(sql=sql, valori=valori)
        with mock.patch.object(L.psycopg2.extras, "execute_values", side_effect=ev):
            n = L.scrie_capturi(object(), 5, ["https://a/1.png", "https://a/2.png",
                                              "https://a/1.png"])
        self.assertEqual(n, 2)
        self.assertIn("DO UPDATE SET vazut_ultima", prinse["sql"])
        self.assertEqual([v[2] for v in prinse["valori"]], ["https://a/1.png", "https://a/2.png"])


class TestPeBaza(unittest.TestCase):
    """Migrarea 026 și upsert-ul pe baza reală, într-o tranzacție anulată."""

    def setUp(self):
        try:
            import config
            import normalizeaza as N
            import psycopg2
            config.incarca()
            self.conn = psycopg2.connect(N.dsn(), connect_timeout=3)
        except Exception as exc:
            self.skipTest(f"baza indisponibilă: {type(exc).__name__}")

    def tearDown(self):
        self.conn.rollback()
        self.conn.close()

    def test_versiunea_veche_ramane(self):
        cur = self.conn.cursor()
        cur.execute(_text(RADACINA, "db", "migration_026_aplicatii.sql"))
        # o bancă fără aplicație, nu BCR (refacerea BCR rulează în paralel)
        cur.execute("SELECT id FROM banci WHERE slug = 'banorient'")
        id_banca = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM app_release WHERE id_banca = %s", (id_banca,))
        inainte = cur.fetchone()[0]

        L.scrie_versiune(cur, id_banca, "999", {"version": "test-1", "description": "d1"})
        L.scrie_versiune(cur, id_banca, "999", {"version": "test-2", "description": "d2"})
        L.scrie_versiune(cur, id_banca, "999", {"version": "test-2"})   # a doua rulare
        L.scrie_capturi(cur, id_banca, ["https://test/1.png"])
        L.scrie_capturi(cur, id_banca, ["https://test/1.png"])

        cur.execute("""SELECT versiune, descriere FROM app_release
                       WHERE id_banca = %s AND versiune LIKE 'test-%%' ORDER BY 1""", (id_banca,))
        self.assertEqual(cur.fetchall(), [("test-1", "d1"), ("test-2", "d2")])
        cur.execute("SELECT count(*) FROM app_release WHERE id_banca = %s", (id_banca,))
        self.assertEqual(cur.fetchone()[0], inainte + 2)
        cur.execute("SELECT count(*) FROM app_screenshot WHERE url = 'https://test/1.png'")
        self.assertEqual(cur.fetchone()[0], 1)
        cur.execute("SELECT count(*) FROM app_release_curente WHERE id_banca = %s", (id_banca,))
        self.assertEqual(cur.fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
