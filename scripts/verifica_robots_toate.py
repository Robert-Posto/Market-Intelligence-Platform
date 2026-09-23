"""Verifica citirea robots.txt pe toate domeniile din config, prin ambele canale."""
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.sync_api import sync_playwright
from crawler.banci import BANCI
from crawler.robots import RegulliRobots

from crawler import UA

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(user_agent=UA, locale="ro-RO")
    pg = ctx.new_page()
    necitite = []
    for banca in BANCI:
        r = RegulliRobots(banca["id"], banca["base"], banca.get("delay", 2))
        r.citeste(pg, ctx.request)
        marcaj = "!!" if r.status.startswith(("NECITIT", "necitibil", "invalid")) else "  "
        print(f"{marcaj} {banca['id']:<14} delay={r.delay:<4} {r.status}")
        if marcaj == "!!":
            necitite.append(banca["id"])
    b.close()
print(f"\nnecitite: {necitite if necitite else 'niciuna'}")
