import os
import sys
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import sanitizare as S


class TestSanitizare(unittest.TestCase):
    def test_meniul_si_ora_nu_schimba_amprenta(self):
        a = b"<html><nav>Meniu A</nav><main>Depozit 5,5% valabil 01.04-30.06</main>" \
            b"<footer>generat 10:31:07</footer></html>"
        b = b"<html><nav>Meniu B</nav><main>Depozit 5,5% valabil 01.04-30.06</main>" \
            b"<footer>generat 11:02:44</footer></html>"
        self.assertEqual(S.amprenta_continut(a), S.amprenta_continut(b))

    def test_ora_in_continut_nu_schimba_amprenta(self):
        a = b"<main>Curs actualizat la 10:31 - EUR 4,97</main>"
        b = b"<main>Curs actualizat la 11:45 - EUR 4,97</main>"
        self.assertEqual(S.amprenta_continut(a), S.amprenta_continut(b))

    def test_pretul_schimba_amprenta(self):
        a = b"<main>Depozit 5,5%</main>"
        b = b"<main>Depozit 5,75%</main>"
        self.assertNotEqual(S.amprenta_continut(a), S.amprenta_continut(b))

    def test_perioada_de_valabilitate_se_pastreaza(self):
        self.assertIn("01.04.2026", S.text_sanitizat(b"<main>valabil din 01.04.2026</main>"))

    def test_pdf_pe_octeti(self):
        self.assertNotEqual(S.amprenta_continut(b"%PDF-1.7 a"), S.amprenta_continut(b"%PDF-1.7 b"))


if __name__ == "__main__":
    unittest.main()
