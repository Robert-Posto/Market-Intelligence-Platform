"""
Teste pentru robots_matcher.py -- matcher robots.txt conform RFC 9309.

Motivul pentru care exista acest modul (nu urllib.robotparser): parser-ul din
biblioteca standard face doar potrivire pe prefix simplu, deci rateaza complet
tipare cu wildcard gen `Disallow: *.pdf` -- vezi test_wildcard_star_matches_any_suffix.
"""

import unittest

from robots_matcher import can_fetch, get_crawl_delay, parse


class TestWildcardMatching(unittest.TestCase):
    def test_wildcard_star_matches_any_suffix(self):
        # bug-ul clasic urllib.robotparser: *.pdf nu potriveste nimic, pentru
        # ca robotparser trateaza tiparul ca prefix literal.
        rules = parse("User-agent: *\nDisallow: *.pdf\n")
        self.assertFalse(can_fetch(rules, "AnyBot", "/documente/tarife.pdf"))

    def test_wildcard_does_not_block_unrelated_path(self):
        rules = parse("User-agent: *\nDisallow: *.pdf\n")
        self.assertTrue(can_fetch(rules, "AnyBot", "/depozite/index.html"))


class TestEndAnchor(unittest.TestCase):
    def test_dollar_anchor_blocks_exact_path_only(self):
        rules = parse("User-agent: *\nDisallow: /pagina$\n")
        self.assertFalse(can_fetch(rules, "AnyBot", "/pagina"))

    def test_dollar_anchor_does_not_block_longer_path(self):
        rules = parse("User-agent: *\nDisallow: /pagina$\n")
        self.assertTrue(can_fetch(rules, "AnyBot", "/pagina/alta"))


class TestLongestMatchPrecedence(unittest.TestCase):
    def test_more_specific_allow_overrides_broader_disallow(self):
        rules = parse(
            "User-agent: *\n"
            "Disallow: /privat/\n"
            "Allow: /privat/public.html\n"
        )
        self.assertTrue(can_fetch(rules, "AnyBot", "/privat/public.html"))
        self.assertFalse(can_fetch(rules, "AnyBot", "/privat/secret.html"))

    def test_allow_wins_on_equal_length_tie(self):
        rules = parse(
            "User-agent: *\n"
            "Disallow: /pagina$\n"
            "Allow: /pagina$\n"
        )
        self.assertTrue(can_fetch(rules, "AnyBot", "/pagina"))


class TestDefaultAllow(unittest.TestCase):
    def test_no_matching_rule_is_allowed(self):
        rules = parse("User-agent: *\nDisallow: /privat/\n")
        self.assertTrue(can_fetch(rules, "AnyBot", "/public/pagina.html"))

    def test_empty_robots_txt_allows_everything(self):
        rules = parse("")
        self.assertTrue(can_fetch(rules, "AnyBot", "/orice/pagina"))


class TestUserAgentGroupSelection(unittest.TestCase):
    def test_specific_group_used_when_present(self):
        rules = parse(
            "User-agent: *\n"
            "Allow: /\n"
            "\n"
            "User-agent: BadBot\n"
            "Disallow: /\n"
        )
        self.assertFalse(can_fetch(rules, "BadBot", "/pagina"))
        self.assertTrue(can_fetch(rules, "GoodBot", "/pagina"))

    def test_group_matching_is_case_insensitive(self):
        rules = parse("User-agent: MyBot\nDisallow: /privat/\n")
        self.assertFalse(can_fetch(rules, "mybot", "/privat/x"))


class TestCrawlDelay(unittest.TestCase):
    def test_crawl_delay_extracted_for_matching_group(self):
        rules = parse("User-agent: *\nCrawl-delay: 5\n")
        self.assertEqual(get_crawl_delay(rules, "AnyBot"), 5.0)

    def test_crawl_delay_none_when_not_declared(self):
        rules = parse("User-agent: *\nAllow: /\n")
        self.assertIsNone(get_crawl_delay(rules, "AnyBot"))


if __name__ == "__main__":
    unittest.main()
