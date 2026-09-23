import os
import sys
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import extractoare


class TestLocator(unittest.TestCase):
    def test_json_inline(self):
        html = b"""<script>var agentii = [{"name":"Agentia Unirii","type":"branch",
        "address":"Bd. Unirii 1","lat":44.4268,"lng":26.1025,"schedule":"L-V 9-17"},
        {"name":"ATM Mall","type":"atm","latitude":"44.43","longitude":"26.05"}];</script>"""
        puncte, _ = extractoare.din_locator(html, "https://x.ro/retea", "libra")
        self.assertEqual(len(puncte), 2)
        self.assertEqual(puncte[0]["tip"], "sucursala")
        self.assertEqual(puncte[1]["tip"], "atm")
        self.assertAlmostEqual(puncte[0]["lat"], 44.4268)
        self.assertEqual(puncte[0]["program"], "L-V 9-17")

    def test_atribute_data(self):
        html = b'<div class="atm" data-lat="45.75" data-lng="21.22">ATM Timisoara</div>'
        puncte, _ = extractoare.din_locator(html, "https://x.ro/atm", "libra")
        self.assertEqual((puncte[0]["tip"], puncte[0]["lat"]), ("atm", 45.75))

    def test_coordonate_in_afara_romaniei_se_arunca(self):
        html = b'<div data-lat="48.85" data-lng="2.35">Paris</div>'
        self.assertEqual(extractoare.din_locator(html, "https://x.ro/retea", "libra")[0], [])

    def test_acelasi_punct_o_singura_data(self):
        html = b'<div data-lat="45.75" data-lng="21.22">A</div><div data-lat="45.75" data-lng="21.22">A</div>'
        self.assertEqual(len(extractoare.din_locator(html, "https://x.ro/retea", "libra")[0]), 1)


if __name__ == "__main__":
    unittest.main()
