import os
import sys
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

from crawler.robots import RegulliRobots


def reguli(text):
    r = RegulliRobots("test", "https://exemplu.ro")
    r._parseaza(text)
    return r


class TestRobots(unittest.TestCase):
    def test_wildcard_pdf(self):
        r = reguli("User-agent: *\nDisallow: *.pdf\n")
        self.assertFalse(r.permite("https://exemplu.ro/docs/tarife.pdf"))
        self.assertTrue(r.permite("https://exemplu.ro/docs/tarife"))

    def test_grupuri_stea_repetate_se_unesc(self):
        r = reguli("User-agent: *\nDisallow: /a\n\nUser-agent: Googlebot\nDisallow: /\n\n"
                   "User-agent: *\nDisallow: /search\n")
        self.assertFalse(r.permite("https://exemplu.ro/search?q=x"))
        self.assertTrue(r.permite("https://exemplu.ro/credite"))

    def test_query_conteaza(self):
        r = reguli("User-agent: *\nDisallow: /?s=\n")
        self.assertFalse(r.permite("https://exemplu.ro/?s=card"))

    def test_grupul_care_ne_numeste_bate_steaua(self):
        r = reguli("User-agent: *\nDisallow: /\n\nUser-agent: LibraBank-MarketIntel-Test\n"
                   "Allow: /\n")
        self.assertTrue(r.permite("https://exemplu.ro/credite"))

    def test_grup_test_nu_ne_prinde_pe_subsir(self):
        # „Test" nu e UA-ul nostru, deși UA-ul nostru conține „-Test/"
        r = reguli("User-agent: Test\nDisallow: /\n\nUser-agent: *\nCrawl-delay: 5\n")
        self.assertTrue(r.permite("https://exemplu.ro/credite"))
        self.assertEqual(r.delay, 5)


if __name__ == "__main__":
    unittest.main()
