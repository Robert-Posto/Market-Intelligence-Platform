"""Raportul de calitate al populării: cât din date e corect și curat, pe bancă.

„Curat" = o valoare pe care un om o poate verifica și compara fără ajutor:
  - e curentă (în `observatii_curente`, nu istoric/dublură/viitor),
  - nu e marcată ambiguă,
  - are link spre sursă,
  - citatul se regăsește în sursă: în conținutul principal al paginii (HTML)
    sau pe pagina indicată a PDF-ului (verificat pe un eșantion per bancă),
  - la comisioane, are un concept comparabil (nu găleata generică `comision`).

Comparația cu pachetul colegului (date/pachet) e doar numerică: nimic din
pachet nu se încarcă.

Rulare: python scripts/raport_calitate.py [--esantion-pdf 15]
"""
import argparse
import collections
import json
import os
import random
import re
import sys

RADACINA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [RADACINA, os.path.join(RADACINA, "ingest")]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import config                      # noqa: E402
import flux                        # noqa: E402
import normalizeaza as N           # noqa: E402
import psycopg2                    # noqa: E402
import sanitizare                  # noqa: E402


def norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def cheie_citat(c):
    return norm(c)[:25]


def pachet_coleg():
    cale = os.path.join(RADACINA, "date", "pachet")
    n = collections.Counter()
    try:
        for x in json.load(open(os.path.join(cale, "comisioane_unificate.json"), encoding="utf-8")):
            n[(x.get("sursa_pdf") or "").replace("\\", "/").split("/")[0]] += 1
        for x in json.load(open(os.path.join(cale, "rate_validate.json"), encoding="utf-8")):
            n[x.get("banca")] += 1
    except OSError:
        pass
    return {N.ALIAS_SLUG.get(k, k): v for k, v in n.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--esantion-pdf", type=int, default=15)
    a = ap.parse_args()
    config.incarca()
    cur = psycopg2.connect(N.dsn()).cursor()
    cur.execute("""SELECT b.slug, o.id, s.tip_sursa, s.sursa, o.citat, o.camp, o.unitate,
                          o.data_vigoare IS NOT NULL, o.ambiguu, o.pagina,
                          o.id IN (SELECT id FROM observatii_curente)
                   FROM observations o JOIN surse s ON s.id = o.id_sursa
                   JOIN banci b ON b.id = s.id_banca""")
    randuri = cur.fetchall()
    cur.execute("SELECT slug FROM banci ORDER BY slug")
    banci = [r[0] for r in cur.fetchall()]
    cur.execute("""SELECT b.slug, s.status, count(*) FROM surse s JOIN banci b ON b.id = s.id_banca
                   WHERE s.tip_sursa = 'url' GROUP BY 1, 2""")
    surse = collections.defaultdict(dict)
    for slug, st, n in cur.fetchall():
        surse[slug][st] = n

    text_html, pdf_verif = {}, {}
    pe_banca = collections.defaultdict(list)
    for r in randuri:
        pe_banca[r[0]].append(r)

    def html_vizibil(url):
        if url not in text_html:
            try:
                text_html[url] = norm(sanitizare.text_sanitizat(open(flux.cale_bronze(url), "rb").read()))
            except OSError:
                text_html[url] = None
        return text_html[url]

    def pdf_are(url, pagina, citat):
        import pdfplumber
        try:
            with pdfplumber.open(flux.cale_bronze(url)) as pdf:
                pagini = [pdf.pages[pagina - 1]] if pagina and pagina <= len(pdf.pages) else pdf.pages[:3]
                text = norm(" ".join((p.extract_text() or "") for p in pagini))
        except Exception:
            return None
        return cheie_citat(citat) in text

    coleg = pachet_coleg()
    total = collections.Counter()
    print(f"{'banca':20s} {'val':>6s} {'cur':>6s} {'curat':>6s} {'%curat':>6s} "
          f"{'map%':>5s} {'dat%':>5s} {'amb%':>5s} {'cit_html':>9s} {'cit_pdf':>8s} {'coleg':>6s}  surse")
    for slug in banci:
        rr = pe_banca.get(slug, [])
        c = collections.Counter()
        pdfuri = [r for r in rr if r[2] == "document" and r[4]]
        esantion = set(x[1] for x in random.Random(1).sample(pdfuri, min(a.esantion_pdf, len(pdfuri))))
        for (_, oid, tip, sursa, citat, camp, unit, datat, amb, pagina, curenta) in rr:
            c["val"] += 1
            c["curente"] += curenta
            c["datat"] += datat
            c["ambiguu"] += bool(amb)
            e_comision = unit in ("lei", "eur", "usd") or (camp or "").startswith("comision")
            mapat = not (e_comision and camp == "comision")
            c["mapat"] += mapat
            link = str(sursa).startswith("http")
            verificat = None
            if tip == "url" and citat:
                v = html_vizibil(sursa)
                verificat = None if v is None else cheie_citat(citat) in v
                c["html"] += 1
                c["html_ok"] += bool(verificat)
            elif tip == "document" and oid in esantion:
                verificat = pdf_are(sursa, pagina, citat)
                c["pdf_esantion"] += 1
                c["pdf_ok"] += bool(verificat)
            citat_ok = verificat is not False    # PDF-urile din afara eșantionului: neverificate
            if curenta and not amb and link and citat and citat_ok and mapat:
                c["curat"] += 1
        total.update(c)
        pct = lambda x, y: f"{100 * x / y:5.0f}" if y else "    -"
        st = ", ".join(f"{k} {v}" for k, v in sorted(surse.get(slug, {}).items()))
        print(f"{slug:20s} {c['val']:6d} {c['curente']:6d} {c['curat']:6d} {pct(c['curat'], c['val']):>6s} "
              f"{pct(c['mapat'], c['val'])} {pct(c['datat'], c['val'])} {pct(c['ambiguu'], c['val'])} "
              f"{c['html_ok']:4d}/{c['html']:<4d} {c['pdf_ok']:3d}/{c['pdf_esantion']:<4d} "
              f"{coleg.get(slug, 0):6d}  {st}")
    t = total
    print(f"\nTOTAL: {t['val']} valori, {t['curente']} curente, {t['curat']} curate "
          f"({100 * t['curat'] / max(t['val'], 1):.0f}%); concept comparabil "
          f"{100 * t['mapat'] / max(t['val'], 1):.0f}%; datate {100 * t['datat'] / max(t['val'], 1):.0f}%; "
          f"ambigue {100 * t['ambiguu'] / max(t['val'], 1):.0f}%")
    print(f"citate HTML regăsite în conținut: {t['html_ok']}/{t['html']} "
          f"({100 * t['html_ok'] / max(t['html'], 1):.0f}%); citate PDF pe eșantion: "
          f"{t['pdf_ok']}/{t['pdf_esantion']} ({100 * t['pdf_ok'] / max(t['pdf_esantion'], 1):.0f}%)")
    print(f"pachetul colegului (doar ca reper): {sum(coleg.values())} valori la "
          f"{sum(1 for v in coleg.values() if v)} bănci")


if __name__ == "__main__":
    main()
