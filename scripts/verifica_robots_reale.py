"""Verifica pe domenii reale ca robots.txt e citit si parsat corect."""
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.sync_api import sync_playwright
from crawler.robots import RegulliRobots

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")

DOMENII = [
    ("bcr", "https://www.bcr.ro", [("https://www.bcr.ro/search", False),
                                   ("https://www.bcr.ro/ro/persoane-fizice/credite", True)]),
    ("ing", "https://ing.ro", [("https://ing.ro/x/doc.pdf", False),
                               ("https://ing.ro/persoane-fizice/credite", True)]),
    ("patria", "https://www.patriabank.ro", [("https://www.patriabank.ro/d/x.pdf", False),
                                             ("https://www.patriabank.ro/persoane-fizice/credite", True)]),
    ("cdn_erste", "https://cdn.erstegroup.com", [("https://cdn.erstegroup.com/x/Tarif.pdf", True)]),
    ("libra", "https://www.librabank.ro", [("https://www.librabank.ro/persoane-fizice", True)]),
]

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context(user_agent=UA).new_page()
    total_esec = 0
    for nume, base, cazuri in DOMENII:
        r = RegulliRobots(nume, base)
        r.citeste(pg)
        print(f"\n=== {nume} ===")
        print(f"  status: {r.status} | delay: {r.delay}")
        for url, asteptat in cazuri:
            real = r.permite(url)
            marcaj = "OK " if real == asteptat else "ESEC"
            if real != asteptat:
                total_esec += 1
            print(f"  {marcaj} permite({url[:62]}) = {real}")
    b.close()
print(f"\n{'TOATE OK' if total_esec == 0 else f'{total_esec} ESECURI'}")
