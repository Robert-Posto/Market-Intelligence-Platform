"""Locatorul cu coordonatele în pagină, pe fișierul real din Bronze.

Din cele 399 de surse GOL (29.09), singura cu date citibile direct din pagină,
fără browser, era `techventures.bank/sucursale`: 14 puncte în
`window.locations`, cu cheia „long” pe care extractorul n-o cunoștea.
Fișierul se citește de pe disc, nu se copiază în repo; fără el, testul se sare.
"""
import os
import sys
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import extractoare  # noqa: E402
import flux  # noqa: E402

TECHVENTURES = "https://techventures.bank/sucursale"


def din_bronze(url):
    try:
        with open(flux.cale_bronze(url), "rb") as f:
            return f.read()
    except OSError:
        return None


class TestCheiaLong(unittest.TestCase):
    def test_lat_long(self):
        html = b"""<script>window.locations = [{"id":1,"name":"Sucursala Arad",
        "type":"subsidiary_with_atm","lat":46.19013,"long":21.329302},
        {"id":14,"name":"Bucuresti, Calea Grivitei 359","type":"atm","lat":44.46584,"long":26.05378}];
        </script>"""
        puncte, _ = extractoare.din_locator(html, "https://x.ro/sucursale", "techventures")
        self.assertEqual({(p["tip"], p["lon"]) for p in puncte},
                         {("sucursala", 21.329302), ("atm", 26.05378)})


@unittest.skipUnless(din_bronze(TECHVENTURES), "fișierul nu e în Bronze")
class TestTechVenturesDinBronze(unittest.TestCase):
    def test_toate_punctele(self):
        puncte, nota = extractoare.din_locator(din_bronze(TECHVENTURES), TECHVENTURES,
                                               "techventures")
        self.assertEqual(len(puncte), 14, nota)
        tipuri = sorted(p["tip"] for p in puncte)
        self.assertEqual(tipuri.count("sucursala"), 9)
        self.assertEqual(tipuri.count("atm"), 5)
        self.assertTrue(all(p["retea"] == "proprie" for p in puncte))


if __name__ == "__main__":
    unittest.main()
