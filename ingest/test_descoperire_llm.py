import os
import sys
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import descoperire_llm as L


class TestLlm(unittest.TestCase):
    def test_domenii_permise_din_url(self):
        self.assertEqual(L.domenii("https://salt.bank/"), ["salt.bank", "www.salt.bank"])
        self.assertEqual(L.domenii("https://www.bcr.ro/"), ["bcr.ro", "www.bcr.ro"])

    def test_cost_se_insumeaza(self):
        c = L.Cost()
        c.adauga(type("U", (), {"input_tokens": 100, "output_tokens": 30})())
        c.adauga(type("U", (), {"input_tokens": 50, "output_tokens": 10})())
        self.assertEqual((c.intrare, c.iesire), (150, 40))

    def test_banci_blocate_din_baza(self):
        class Cur:
            def execute(self, sql, params=None):
                self.sql = sql

            def fetchall(self):
                return [("cec",), ("banca-transilvania",)]
        self.assertEqual(L.banci_blocate(Cur()), {"cec", "banca-transilvania"})


if __name__ == "__main__":
    unittest.main()
