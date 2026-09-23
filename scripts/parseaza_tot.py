"""Aplica parserul pe tot rezultatul crawl-ului si masoara acoperirea determinista."""
import json, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from crawler.parser_rate import parseaza_linie

CRAWL = Path("output/crawl")
inregistrari, probleme = [], []
linii_totale = 0

for f in sorted(CRAWL.glob("*.json")):
    if f.name in ("consolidat.json", "bnr_curs_referinta.json"):
        continue
    d = json.loads(f.read_text(encoding="utf-8"))
    bid = d.get("banca_id")
    for p in (d.get("pagini") or []):
        titlu = (p.get("titlu") or "").strip() or None
        for linie in p["linii_rata"]:
            linii_totale += 1
            recs, problema = parseaza_linie(linie, bid, p["categorie"], p["url"], titlu)
            inregistrari.extend(recs)
            if problema:
                probleme.append({"banca": bid, "url": p["url"],
                                 "motiv": problema, "text": linie[:220]})

print(f"linii procesate:        {linii_totale}")
print(f"valori tipizate:        {len(inregistrari)}")
print(f"linii care cer LLM:     {len(probleme)}")
print(f"\n=== valori pe tip ===")
for tip, n in Counter(r["tip_rata"] for r in inregistrari).most_common():
    print(f"  {tip:<20} {n:>4}")
print(f"\n=== incredere ===")
for niv, n in Counter(r["incredere"] for r in inregistrari).most_common():
    print(f"  {niv:<12} {n:>4}")
print(f"\n=== motive pentru LLM ===")
for motiv, n in Counter(p["motiv"] for p in probleme).most_common():
    print(f"  {n:>4}  {motiv}")

Path("output/rate_tipizate.json").write_text(
    json.dumps(inregistrari, ensure_ascii=False, indent=2), encoding="utf-8")
Path("output/necesita_llm.json").write_text(
    json.dumps(probleme, ensure_ascii=False, indent=2), encoding="utf-8")
print("\n>> output/rate_tipizate.json | output/necesita_llm.json")
