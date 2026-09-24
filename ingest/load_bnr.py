"""Indicii de referință BNR, colectați acum de pe www.bnr.ro: ROBID, ROBOR, IRCC.

Înlocuiește varianta care citea pachetul colegului (`date/pachet/bnr_indici.json`,
21.09): acela avea ROBOR doar pe 4–17.09 și deloc IRCC (pagina căzuse la
rularea lui).

De unde: paginile BNR de ROBOR și IRCC, pe `www.bnr.ro`, permise de robots.txt
(`Disallow:` gol, verificat 24.09.2026). Tabelele se randează în JavaScript,
deci se citesc cu Playwright și UA-ul echipei; parsarea e cea a colegului
(`crawler/bnr_indici.py`), inclusiv regula de aplicare a IRCC (valoarea
etichetată „2026T1" se aplică din al doilea trimestru următor).

Cursul de referință NU e aici: feed-ul XML stă pe `curs.bnr.ro`, unde robots.txt
interzice tot (`Disallow: /`).

Rulare:
    python ingest/load_bnr.py            # colectează și înlocuiește tabela
    python ingest/load_bnr.py --uscat    # doar afișează ce ar scrie
"""

import argparse
import datetime
import os
import sys

import psycopg2
import psycopg2.extras

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import config                      # noqa: E402
import flux                        # noqa: E402
import normalizeaza as N           # noqa: E402
from crawler import UA             # noqa: E402
from crawler import bnr_indici     # noqa: E402


def _iso(zz_ll_aaaa):
    z, l, a = zz_ll_aaaa.split(".")
    return datetime.date(int(a), int(l), int(z))


def colecteaza():
    for u in bnr_indici.PAGINI.values():
        if not flux.permite(u, "bnr"):
            raise PermissionError(f"robots.txt interzice {u}")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(user_agent=UA, locale="ro-RO").new_page()
        rr = bnr_indici.robid_robor(page)
        ircc = bnr_indici.ircc(page)
        browser.close()
    randuri = []
    for zi in rr.get("zile") or []:
        for indice in ("robid", "robor"):
            for scadenta, valoare in (zi.get(indice) or {}).items():
                if valoare is not None:
                    d = _iso(zi["data"])
                    randuri.append((indice, scadenta, valoare, d, d, rr["sursa"]))
    for t in ircc.get("trimestrial") or []:
        per = bnr_indici.perioada_aplicare(t["perioada"])
        if per:
            randuri.append(("ircc", t["perioada"], t["valoare"], per[0], per[1], ircc["sursa"]))
    return randuri, rr, ircc


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--uscat", action="store_true")
    a = ap.parse_args()
    config.incarca()
    randuri, rr, ircc = colecteaza()
    zile = sorted({r[3] for r in randuri if r[0] == "robor"})
    print(f"ROBID/ROBOR: {len(rr.get('zile') or [])} zile ({zile[0] if zile else '-'} … "
          f"{zile[-1] if zile else '-'}), {sum(r[0] != 'ircc' for r in randuri)} valori")
    iv = ircc.get("in_vigoare") or {}
    print(f"IRCC: {len(ircc.get('trimestrial') or [])} trimestre; în vigoare azi: "
          f"{iv.get('perioada')} = {iv.get('valoare')}% "
          f"({iv.get('aplicabil_de_la')} … {iv.get('aplicabil_pana_la')})")
    if a.uscat:
        return 0
    with psycopg2.connect(N.dsn()) as conn:
        with conn.cursor() as cur:
            # Datele din pachetul din 21.09 pleacă: popularea e de la zero.
            cur.execute("DELETE FROM indici_referinta")
            print(f"șterse: {cur.rowcount} rânduri vechi")
            psycopg2.extras.execute_values(
                cur, """INSERT INTO indici_referinta (indice, scadenta, valoare, valabil_din,
                            valabil_pana, sursa) VALUES %s ON CONFLICT DO NOTHING""", randuri)
            print(f"scrise: {len(randuri)} rânduri")
    return 0


if __name__ == "__main__":
    sys.exit(main())
