"""
Teste pentru crawl_bfs (scraper.py) -- descoperire de linkuri pe mai multe
niveluri, nu doar de pe homepage. Foloseste fetch/robots/sleep injectate
(fake-uri), fara cereri de retea reale.
"""

import unittest

from bs4 import BeautifulSoup

from scraper import crawl_bfs

SITE = {
    "https://example.ro/depozite": (
        '<html><body><a href="https://example.ro/depozite/detalii">Depozit detalii</a></body></html>'
    ),
    "https://example.ro/depozite/detalii": (
        '<html><body>'
        '<a href="https://example.ro/depozite/final">Depozit final</a>'
        '<a href="https://example.ro/altceva">Altceva</a>'
        '</body></html>'
    ),
    "https://example.ro/depozite/final": "<html><body>Nimic relevant aici.</body></html>",
}

HOME_URL = "https://example.ro/"
HOME_HTML = (
    '<html><body>'
    '<a href="https://example.ro/depozite">Depozite</a>'
    '<a href="https://example.ro/despre">Despre noi</a>'
    '</body></html>'
)
KEYWORDS = ["depozit"]


def fake_fetch(url):
    if url in SITE:
        return {"ok": True, "final_url": url, "html": SITE[url]}
    return {"ok": False, "error": "404 nu exista in site-ul fals"}


def make_fake_robots(blocked=frozenset()):
    def fake_robots(url):
        if url in blocked:
            return "disallow", "interzis (test)", None
        return "allow", "ok", None
    return fake_robots


def fake_sleep(_seconds):
    pass


def home_soup():
    return BeautifulSoup(HOME_HTML, "lxml")


class TestCrawlBfsDepth(unittest.TestCase):
    def test_max_depth_1_does_not_recurse_past_homepage_links(self):
        found = crawl_bfs(
            home_soup(), HOME_URL, KEYWORDS, max_depth=1, max_pages=10,
            fetch=fake_fetch, check_robots=make_fake_robots(), sleep=fake_sleep,
        )
        urls = [p["url"] for p in found]
        self.assertEqual(urls, ["https://example.ro/depozite"])

    def test_max_depth_2_follows_one_more_level(self):
        found = crawl_bfs(
            home_soup(), HOME_URL, KEYWORDS, max_depth=2, max_pages=10,
            fetch=fake_fetch, check_robots=make_fake_robots(), sleep=fake_sleep,
        )
        urls = [p["url"] for p in found]
        self.assertEqual(
            urls,
            ["https://example.ro/depozite", "https://example.ro/depozite/detalii"],
        )


class TestCrawlBfsMaxPages(unittest.TestCase):
    def test_stops_at_max_pages_without_extra_fetches(self):
        found = crawl_bfs(
            home_soup(), HOME_URL, KEYWORDS, max_depth=2, max_pages=1,
            fetch=fake_fetch, check_robots=make_fake_robots(), sleep=fake_sleep,
        )
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["url"], "https://example.ro/depozite")


class TestCrawlBfsRobots(unittest.TestCase):
    def test_disallowed_page_and_its_subtree_are_excluded(self):
        found = crawl_bfs(
            home_soup(), HOME_URL, KEYWORDS, max_depth=2, max_pages=10,
            fetch=fake_fetch,
            check_robots=make_fake_robots(blocked={"https://example.ro/depozite"}),
            sleep=fake_sleep,
        )
        self.assertEqual(found, [])


class TestCrawlBfsDedup(unittest.TestCase):
    def test_same_url_linked_twice_is_only_visited_once(self):
        site = dict(SITE)
        site["https://example.ro/depozite"] = (
            '<html><body>'
            '<a href="https://example.ro/depozite/detalii">Depozit detalii</a>'
            '<a href="https://example.ro/depozite/detalii">Depozit detalii din nou</a>'
            '</body></html>'
        )

        def fetch(url):
            return {"ok": True, "final_url": url, "html": site[url]} if url in site else {"ok": False, "error": "missing"}

        found = crawl_bfs(
            home_soup(), HOME_URL, KEYWORDS, max_depth=2, max_pages=10,
            fetch=fetch, check_robots=make_fake_robots(), sleep=fake_sleep,
        )
        urls = [p["url"] for p in found]
        self.assertEqual(urls.count("https://example.ro/depozite/detalii"), 1)


if __name__ == "__main__":
    unittest.main()
