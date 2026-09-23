"""
Teste pentru known_block_reason (scraper.py) -- scurtcircuitare pentru banci
deja confirmate ca inaccesibile, ca sa nu mai irosim cereri pe ele.
"""

import unittest

from scraper import known_block_reason


class TestKnownBlockReason(unittest.TestCase):
    def test_no_annotation_returns_none(self):
        self.assertIsNone(known_block_reason({"name": "Banca X", "url": "https://x.ro/"}))

    def test_waf_blocat_returns_readable_reason(self):
        bank = {"name": "Banca X", "url": "https://x.ro/", "acces_cunoscut": "waf_blocat"}
        reason = known_block_reason(bank)
        self.assertIn("WAF", reason)

    def test_includes_sursa_info_when_present(self):
        bank = {
            "name": "Banca X", "url": "https://x.ro/",
            "acces_cunoscut": "timeout", "sursa_info": "info: coleg, briefing 16-17 sept",
        }
        reason = known_block_reason(bank)
        self.assertIn("timeout", reason.lower())
        self.assertIn("briefing 16-17 sept", reason)


if __name__ == "__main__":
    unittest.main()
