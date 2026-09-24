import os
import sys
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]


class TestReparatii(unittest.TestCase):
    def test_din_html_importa_parserul_din_crawler(self):
        import extractoare
        html = ("<html><head><title>Depozite la termen</title></head><body>"
                "<h1>Depozit clasic</h1><table><tr><td>12 luni</td><td>DAE 5,50%</td>"
                "</tr></table></body></html>").encode("utf-8")
        brute, nota = extractoare.din_html(html, "https://exemplu.ro/depozite-la-termen",
                                           "libra")
        self.assertTrue(any(b.get("valoare") == 5.5 for b in brute), nota)

    def test_scrie_accepta_banci(self):
        import inspect
        import normalizeaza
        self.assertIn("banci", inspect.signature(normalizeaza.scrie).parameters)

    def test_dobanda_din_meniu_nu_se_atribuie_paginii(self):
        import extractoare
        html = ("<html><head><title>Depozite la termen</title></head><body>"
                "<nav>Credit ipotecar: DAE 4,79%</nav><main><h1>Depozit clasic</h1>"
                "<p>Depozit 12 luni, DAE 5,50%</p></main></body></html>").encode("utf-8")
        brute, _ = extractoare.din_html(html, "https://exemplu.ro/depozite-la-termen", "libra")
        valori = {b.get("valoare") for b in brute if b.get("tip") == "rata"}
        self.assertIn(5.5, valori)
        self.assertNotIn(4.79, valori)

    def test_pagina_de_presa_nu_da_preturi(self):
        import extractoare
        html = b"<html><body><main>Dobanda 7,5% pentru creditul nou</main></body></html>"
        brute, nota = extractoare.din_html(html, "https://x.ro/en/press/2018/credit", "bcr")
        self.assertEqual(brute, [])


if __name__ == "__main__":
    unittest.main()
