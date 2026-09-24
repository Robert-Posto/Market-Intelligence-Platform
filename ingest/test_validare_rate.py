import os
import sys
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import normalizeaza as N
import validare


def fals(recs, indici_bnr=None):
    recs[0]["stare"], recs[1]["stare"] = "SUSPECT", "OK"
    return recs, {}


class TestValidare(unittest.TestCase):
    def test_suspect_devine_ambiguu(self):
        brute = [N.brut(banca="x", sursa="u", _rec={"tip_rata": "dae", "valoare": 7.0}),
                 N.brut(banca="x", sursa="u", _rec={"tip_rata": "nominala", "valoare": 9.0})]
        raport = validare.valideaza_rate(brute, valideaza=fals)
        self.assertTrue(brute[0]["ambiguu"])
        self.assertIn("validator", brute[0]["motiv_ambiguu"])
        self.assertFalse(brute[1]["ambiguu"])
        self.assertEqual(raport["validator_SUSPECT"], 1)

    def test_validatorul_real_da_o_stare(self):
        from crawler.parser_rate import parseaza_linie
        recs, _ = parseaza_linie("Dobânda nominală fixă 7,50%, DAE 8,12%", "x",
                                 "credite", "https://x.ro/credit")
        self.assertTrue(recs)
        brute = [N.brut(banca="x", sursa="https://x.ro/credit", _rec=r) for r in recs]
        validare.valideaza_rate(brute)
        for b in brute:
            self.assertIn(b["stare"], {"OK", "SUSPECT", "SURSA_VECHE", "NEVERIFICAT"})

    def test_suspect_plafoneaza_increderea(self):
        self.assertLessEqual(N._incredere({"incredere": 0.9, "stare": "SUSPECT"}), 0.5)


if __name__ == "__main__":
    unittest.main()
