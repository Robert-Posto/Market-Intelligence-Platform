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


if __name__ == "__main__":
    unittest.main()
