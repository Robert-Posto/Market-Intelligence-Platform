import collections
import os
import sys
import unittest
from unittest import mock

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import populare_initiala as P
import sanitizare
import transport as T


class Cursor:
    def __init__(self, cunoscute=()):
        self.cunoscute, self.executate, self._rez = set(cunoscute), [], None

    def execute(self, sql, params=None):
        self.executate.append((sql, params))
        if sql.startswith("SELECT 1 FROM hashes"):
            self._rez = (1,) if params[1] in self.cunoscute else None

    def fetchone(self):
        return self._rez


SURSA = (7, "cec", "https://cec.ro/tarife", "html", "produs")


class TestTraseu(unittest.TestCase):
    def test_blocat_marcheaza_sursa_si_se_opreste(self):
        cur = Cursor()
        rez = T.Rezultat("BLOCAT", None, SURSA[2], "http", "HTTP 403")
        with mock.patch.object(T, "adu", return_value=rez):
            brute, j = P.proceseaza(SURSA, cur, {}, collections.Counter())
        self.assertEqual((brute, j["stare"]), ([], "BLOCAT"))
        self.assertTrue(any("status = 'blocat'" in s for s, _ in cur.executate))

    def test_continut_neschimbat_nu_scrie_bronze(self):
        octeti = b"<main>Depozit 5%</main>"
        cur = Cursor(cunoscute={sanitizare.amprenta_continut(octeti)})
        rez = T.Rezultat("OK", octeti, SURSA[2], "http", "HTTP 200")
        with mock.patch.object(T, "adu", return_value=rez), \
             mock.patch.object(P.flux, "scrie_bronze") as bronze:
            brute, j = P.proceseaza(SURSA, cur, {}, collections.Counter())
        self.assertEqual(j["stare"], "NESCHIMBAT")
        bronze.assert_not_called()

    def test_parser_care_crapa_nu_opreste_banca(self):
        j = {"sursa": "u", "banca": "x", "transport": None, "stare": None, "nota": None}
        with mock.patch.object(P.extractoare, "din_html", side_effect=ValueError("rupt")):
            brute, j = P.extrage(b"<html></html>", "c", "x", "u", "produs", j)
        self.assertEqual((brute, j["stare"]), ([], "EROARE_EXTRACTIE"))

    def test_bronze_html_fara_sufix_pdf(self):
        self.assertFalse(P.flux.cale_bronze("https://x.ro/credite/nevoi-personale").endswith(".pdf"))
        self.assertTrue(P.flux.cale_bronze("https://x.ro/tarife.pdf").endswith(".pdf"))


if __name__ == "__main__":
    unittest.main()
