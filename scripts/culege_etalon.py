"""Reculege paginile din esantion, ca sa pot verifica valorile de mana.

Nu foloseste parserul. Salveaza textul brut al paginii si, pentru fiecare
valoare din esantion, o fereastra larga de context in jurul textului sursa.
Astfel judecata se face pe textul paginii, nu pe fragmentul pastrat de parser.
"""
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from crawler.banci import BANCI
from crawler.robots import RegulliRobots

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")

RADACINA = Path(__file__).resolve().parent.parent
TEXTE = RADACINA / "output" / "etalon_texte"
TEXTE.mkdir(parents=True, exist_ok=True)

DELAY = {b["id"]: b.get("delay", 1.5) for b in BANCI}


def nume_fisier(url):
    p = urlparse(url)
    s = (p.netloc + p.path).strip("/").replace("/", "_")
    return re.sub(r"[^A-Za-z0-9._-]", "_", s)[:120] + ".txt"


def main():
    esantion = json.load(open(RADACINA / "output/etalon_esantion.json", encoding="utf-8"))
    pagini = {}
    for r in esantion:
        pagini.setdefault(r["sursa_url"], r["banca"])

    rezultate = []
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        ctx = br.new_context(user_agent=UA, locale="ro-RO",
                             viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        robots_cache = {}

        for i, (url, banca) in enumerate(pagini.items(), 1):
            origine = "{0.scheme}://{0.netloc}".format(urlparse(url))
            if origine not in robots_cache:
                reg = RegulliRobots(banca, origine, DELAY.get(banca, 1.5))
                reg.citeste(page, ctx.request)
                robots_cache[origine] = reg
            reg = robots_cache[origine]
            if not reg.permite(url):
                print(f"[{i}/{len(pagini)}] INTERZIS de robots.txt: {url}")
                rezultate.append({"url": url, "banca": banca, "stare": "interzis"})
                continue
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(2500)
                text = page.inner_text("body")
                titlu = page.title()
            except Exception as e:
                print(f"[{i}/{len(pagini)}] EROARE {url}: {type(e).__name__}")
                rezultate.append({"url": url, "banca": banca,
                                  "stare": "eroare", "detaliu": str(e)[:200]})
                time.sleep(DELAY.get(banca, 1.5))
                continue

            f = TEXTE / nume_fisier(url)
            f.write_text(f"URL: {url}\nTITLU: {titlu}\n\n{text}", encoding="utf-8")
            print(f"[{i}/{len(pagini)}] OK {len(text)} car. -> {f.name}")
            rezultate.append({"url": url, "banca": banca, "stare": "ok",
                              "titlu": titlu, "fisier": f.name, "lungime": len(text)})
            time.sleep(DELAY.get(banca, 1.5))
        br.close()

    with open(RADACINA / "output/etalon_culegere.json", "w", encoding="utf-8") as fh:
        json.dump(rezultate, fh, ensure_ascii=False, indent=2)
    ok = sum(1 for r in rezultate if r["stare"] == "ok")
    print(f"\n{ok}/{len(rezultate)} pagini reculese")


if __name__ == "__main__":
    main()
