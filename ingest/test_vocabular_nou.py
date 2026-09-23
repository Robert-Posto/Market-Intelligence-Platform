import os
import sys
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

from crawler import vocabular


def concept(serviciu):
    return vocabular.canonic({"serviciu": serviciu, "sectiune": "", "detaliu": ""})[0]


class TestVocabular(unittest.TestCase):
    def test_recuperare_card(self):
        self.assertEqual(concept("Taxa recuperare card reținut de ATM"), "recuperare_card")

    def test_contestare(self):
        self.assertEqual(concept("Contestare nejustificată a unei tranzacții"), "contestare_tranzactie")

    def test_pachet(self):
        self.assertEqual(concept("Comision lunar pachet de servicii"), "pachet_servicii")


if __name__ == "__main__":
    unittest.main()
