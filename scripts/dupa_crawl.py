"""Aștepta cele sase crawluri paralele, apoi ruleaza tot lantul si masoara.

Rulare:  python scripts/dupa_crawl.py
Ieșire:  output/log/dupa_crawl.txt   — jurnalul propriu
         output/RULARE_18SEPT.md     — ce s-a schimbat fata de 16 septembrie

De ce un script si nu pasi dati de mana: rularea dureaza, iar pasii trebuie sa
mearga si daca nu se uita nimeni. Fiecare pas isi raporteaza codul de ieșire, si
lantul NU se opreste la primul eșec — altfel un pas stricat ar ascunde starea
tuturor celorlalti.

Scriptul NU ruleaza sonda de schimbari. Cu cateva mii de documente si pauzele
per origine, ar dura peste o ora, si nu aduce nimic azi: linia de baza exista
deja, iar documentele noi intra in registru prin urmareste.py.
"""
import json
import pathlib
import subprocess
import sys
import time
from datetime import datetime, timezone

RADACINA = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADACINA))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

JURNAL = RADACINA / "output" / "log" / "dupa_crawl.txt"
RAPORT = RADACINA / "output" / "RULARE_18SEPT.md"
LOGURI = [RADACINA / "output" / "log" / f"grup{i}.txt" for i in range(1, 7)]
MARCAJ_GATA = "Rezultate in:"
ASTEPTARE_MAX = 75 * 60          # daca trece atata, ceva e blocat
PAS_VERIFICARE = 20

PASI = [
    # parseaza_tot produce rate_tipizate.json din paginile crawlate. Lipsea din
    # lista, si efectul a fost mut: ratele au ieșit EXACT 555, adica fișierul
    # vechi de pe 16 septembrie, desi crawlul gasise de doua ori mai multe linii.
    # Egalitatea perfecta a fost semnul — o cifra care nu se mișca deloc dupa o
    # rulare de patru ori mai mare nu e o coincidenta.
    ("parseaza_tot", ["python", "scripts/parseaza_tot.py"]),
    ("parseaza_pdf", ["python", "scripts/parseaza_pdf.py"]),
    ("parseaza_tarife", ["python", "scripts/parseaza_tarife.py"]),
    # date_documente TREBUIE sa fie inaintea unificarii: ea citeste
    # output/date_documente.json ca sa stie care documente sunt in vigoare.
    # Daca lipsește, comisioanele ies cu stare_data=NECITIT si nimic nu se
    # filtreaza — se vede in jurnal, dar tot e o rulare irosita.
    ("date_documente", ["python", "scripts/date_documente.py"]),
    ("unifica_comisioane", ["python", "scripts/unifica_comisioane.py"]),
    ("ruleaza_validare", ["python", "scripts/ruleaza_validare.py"]),
    ("compara_rate", ["python", "scripts/compara_rate.py"]),
    ("urmareste", ["python", "scripts/urmareste.py"]),
    # dupa urmareste: are nevoie de registrul actualizat ca sa stie care
    # documente au o versiune veche pastrata pe disc
    ("compara_versiuni", ["python", "scripts/compara_versiuni.py"]),
    ("raport", ["python", "scripts/raport.py"]),
    ("teste", ["python", "scripts/test_validare.py"]),
    ("teste_robots", ["python", "scripts/test_robots_matcher.py"]),
    ("arhiva", ["python", "scripts/fa_arhiva.py"]),
]


def log(mesaj):
    linie = f"[{datetime.now():%H:%M:%S}] {mesaj}"
    print(linie, flush=True)
    with open(JURNAL, "a", encoding="utf-8") as f:
        f.write(linie + "\n")


def crawluri_gata():
    """(gata, in_lucru, crapate) — starea celor sase jurnale."""
    gata, in_lucru, crapate = [], [], []
    for cale in LOGURI:
        if not cale.exists():
            in_lucru.append(cale.name)
            continue
        t = cale.read_text(encoding="utf-8", errors="replace")
        if MARCAJ_GATA in t:
            gata.append(cale.name)
        elif "Traceback" in t:
            crapate.append(cale.name)
        else:
            in_lucru.append(cale.name)
    return gata, in_lucru, crapate


def acoperire():
    """Cerinte acoperite / total, si detaliul pe banca."""
    from crawler.banci import CERINTE_TINTA
    crawl = RADACINA / "output" / "crawl"
    pe_banca, azi = {}, 0
    for f in sorted(crawl.glob("*.json")):
        if f.name in ("consolidat.json", "bnr_curs_referinta.json"):
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        b = d.get("banca_id") or f.stem
        pe_banca[b] = {
            "cerinte": len(d.get("cerinte_acoperite") or {}),
            "pagini": len(d.get("pagini") or []),
            "sursa": (d.get("descoperire") or {}).get("sursa"),
            "urluri": (d.get("descoperire") or {}).get("total_urluri"),
            "recrawlat": (d.get("moment_crawl") or "")[:10] == "2026-09-18",
            "pdf": (d.get("sumar") or {}).get("pdfs_descarcate"),
        }
        azi += pe_banca[b]["recrawlat"]
    total = sum(v["cerinte"] for v in pe_banca.values())
    return pe_banca, total, len(pe_banca) * len(CERINTE_TINTA), azi


def main():
    JURNAL.parent.mkdir(parents=True, exist_ok=True)
    log("aștept cele sase crawluri")
    inceput = time.time()
    while True:
        gata, in_lucru, crapate = crawluri_gata()
        if len(gata) + len(crapate) == len(LOGURI):
            break
        if time.time() - inceput > ASTEPTARE_MAX:
            log(f"!! am depasit {ASTEPTARE_MAX // 60} minute de aștept; "
                f"continui cu ce exista ({len(gata)} gata, {len(in_lucru)} in lucru)")
            break
        time.sleep(PAS_VERIFICARE)
    gata, in_lucru, crapate = crawluri_gata()
    log(f"crawluri: {len(gata)} gata, {len(crapate)} crapate, "
        f"{len(in_lucru)} neterminate")
    for c in crapate:
        log(f"   !! crapat: {c}")

    pdf = list((RADACINA / "output" / "crawl" / "pdf").rglob("*.pdf"))
    log(f"documente pe disc: {len(pdf)}")

    rezultate = {}
    for nume, cmd in PASI:
        t0 = time.time()
        p = subprocess.run(cmd, cwd=RADACINA, capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        rezultate[nume] = {"cod": p.returncode, "secunde": time.time() - t0,
                           "ieșire": (p.stdout or "")[-2500:],
                           "eroare": (p.stderr or "")[-900:]}
        semn = "ok" if p.returncode == 0 else "EȘEC"
        log(f"{semn:>4}  {nume:<20} {time.time() - t0:>6.1f}s")
        if p.returncode:
            for l in (p.stderr or "").strip().split("\n")[-3:]:
                log(f"        {l[:110]}")

    pe_banca, tot, maxim, azi = acoperire()
    log(f"acoperire cerinte: {tot}/{maxim} = {100*tot/maxim:.0f}%  "
        f"(era 170/460 = 37%)")
    log(f"banci recrawlate azi: {azi} din {len(pe_banca)}")

    # --- raportul ---
    L = ["# Rularea din 18 septembrie: limita 32 -> 80", "",
         f"Generat de `scripts/dupa_crawl.py` la {datetime.now():%H:%M}.", ""]
    L.append(f"**Acoperirea cerințelor: {tot}/{maxim} = {100*tot/maxim:.0f}%** "
             f"(era 170/460 = 37% la crawlul din 16 septembrie).")
    L.append("")
    L.append(f"Bănci recrawlate: {azi} din {len(pe_banca)}. "
             f"Documente pe disc: {len(pdf)} (erau 319).")
    L.append("")
    L.append("| bancă | cerințe | pagini | descoperire | URL-uri | PDF |")
    L.append("|---|---:|---:|---|---:|---:|")
    for b, v in sorted(pe_banca.items(), key=lambda kv: -kv[1]["cerinte"]):
        semn = "" if v["recrawlat"] else " *(vechi)*"
        L.append(f"| {b}{semn} | {v['cerinte']}/20 | {v['pagini']} "
                 f"| {v['sursa']} | {v['urluri']} | {v['pdf']} |")
    L.append("")
    L.append("## Pașii de după crawl")
    L.append("")
    L.append("| pas | cod | secunde |")
    L.append("|---|---|---:|")
    for nume, r in rezultate.items():
        L.append(f"| {nume} | {'ok' if r['cod'] == 0 else '**EȘEC**'} "
                 f"| {r['secunde']:.0f} |")
    L.append("")
    for nume, r in rezultate.items():
        if r["cod"]:
            L.append(f"### {nume} a eșuat")
            L.append("")
            L.append("```")
            L.append((r["eroare"] or r["ieșire"])[-1200:])
            L.append("```")
            L.append("")
    L.append("## Ieșirile pașilor")
    L.append("")
    for nume, r in rezultate.items():
        L.append(f"<details><summary>{nume}</summary>")
        L.append("")
        L.append("```")
        L.append(r["ieșire"].strip())
        L.append("```")
        L.append("")
        L.append("</details>")
        L.append("")
    RAPORT.write_text("\n".join(L), encoding="utf-8")
    log(f">> {RAPORT.relative_to(RADACINA)}")
    esecuri = [n for n, r in rezultate.items() if r["cod"]]
    log(f"GATA. eșecuri: {', '.join(esecuri) if esecuri else 'niciunul'}")


if __name__ == "__main__":
    main()
