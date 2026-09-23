"""Verifica matcher-ul robots pe regulile reale ING + cazuri de precedenta."""
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from crawler.robots import RegulliRobots

ING = """
User-agent: Googlebot
Disallow:
User-agent: *
Disallow:
Disallow: /migrate/
Disallow: /*.pdf$
Disallow: *.pdf
Disallow: /*.xml$
Disallow: *.xml
Disallow: /TSPD/
Sitemap: https://ing.ro/dam/ingro/sitemaps/sitemap.xml
"""

BCR = """
User-agent: *
Allow: /
User-agent: ClaudeBot
Allow: /
User-agent: *
Disallow: /?s=
Disallow: /search
Disallow: /*.compare
"""

PATRIA = """
User-agent: *
Disallow:
Crawl-delay: 5
Disallow: /d/
Disallow: /content/
User-agent: GPTBot
Disallow: /
"""

def verifica(nume, text, cazuri, delay_asteptat=None):
    r = RegulliRobots(nume, "https://exemplu.ro")
    r._parseaza(text)
    print(f"\n=== {nume} ({len(r.reguli)} reguli) ===")
    ok = True
    for url, asteptat in cazuri:
        real = r.permite(url)
        marcaj = "OK " if real == asteptat else "EȘEC"
        if real != asteptat:
            ok = False
        print(f"  {marcaj} permite({url}) = {real} (așteptat {asteptat})")
    if delay_asteptat is not None:
        marcaj = "OK " if r.delay == delay_asteptat else "EȘEC"
        if r.delay != delay_asteptat:
            ok = False
        print(f"  {marcaj} crawl-delay = {r.delay} (așteptat {delay_asteptat})")
    return ok

toate_ok = True
toate_ok &= verifica("ING", ING, [
    ("https://ing.ro/persoane-fizice/credite", True),
    ("https://ing.ro/dam/ingro/doc/contractuale/pers-fizice/Lista-de-taxe-si-comisioane.pdf", False),
    ("https://ing.ro/dam/jcr:abc/rate_dobanzi.pdf", False),
    ("https://ing.ro/dam/ingro/sitemaps/sitemap.xml", False),
    ("https://ing.ro/migrate/ceva", False),
    ("https://ing.ro/TSPD/x", False),
])

toate_ok &= verifica("BCR", BCR, [
    ("https://www.bcr.ro/ro/persoane-fizice/credite", True),
    ("https://www.bcr.ro/search", False),
    ("https://www.bcr.ro/ro/produs.compare", False),
    ("https://cdn.erstegroup.com/x/Tarif.pdf", True),
])

toate_ok &= verifica("PATRIA", PATRIA, [
    ("https://www.patriabank.ro/persoane-fizice/credite", True),
    ("https://www.patriabank.ro/d/document.pdf", False),
    ("https://www.patriabank.ro/content/x", False),
], delay_asteptat=5)

print("\n" + ("TOATE TESTELE AU TRECUT" if toate_ok else "EXISTA TESTE PICATE"))
