import os
import sys
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import descoperire as D


class TestClasificare(unittest.TestCase):
    def test_pdf_de_tarife(self):
        c = D.clasifica_adresa("https://www.bcr.ro/content/dam/ro/tarife-pf.pdf")
        self.assertEqual((c["rol"], c["format"], c["produs"]), ("conditii", "pdf", "comisioane"))

    def test_document_fara_sufix_pdf(self):
        c = D.clasifica_adresa("https://x.ro/download?id=12", "Lista de tarife și comisioane (PDF)")
        self.assertEqual(c["rol"], "conditii")

    def test_locator(self):
        self.assertEqual(D.clasifica_adresa("https://x.ro/retea-unitati-atm")["rol"], "locator")

    def test_formular_standardizat_nu_e_exclus(self):
        self.assertIsNotNone(D.clasifica_adresa("https://x.ro/formular-standardizat-comisioane.pdf"))

    def test_zgomot_exclus(self):
        self.assertIsNone(D.clasifica_adresa("https://x.ro/blog/5-sfaturi"))
        self.assertIsNone(D.clasifica_adresa("https://x.ro/cariere"))
        self.assertIsNone(D.clasifica_adresa("https://x.ro/img/card.png"))

    def test_url_normalizat(self):
        self.assertEqual(D.normalizeaza_url("https://X.ro/credite/?utm_source=a#top"),
                         "https://x.ro/credite")


if __name__ == "__main__":
    unittest.main()
