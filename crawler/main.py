"""Crawler pentru produse si tarife bancare din Romania.

Respecta robots.txt pentru fiecare domeniu si pauzele cerute (Crawl-delay).

Rulare:
    python -m crawler.main                      # toate bancile
    python -m crawler.main --banci bcr,ing      # doar anumite banci
    python -m crawler.main --pdf                # descarca si PDF-urile de tarife
    python -m crawler.main --max-pe-banca 30
"""
import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from .banci import BANCI, CATEGORII, CERINTE_TINTA, EXCLUDE
from .bnr import curs_referinta
from .extractor import clasifica, extrage, scor_url
from .robots import RegulliRobots
from .urme import nume_din_url

# Consola Windows e cp1252, iar mesajele de log au diacritice. Fara asta,
# procesul crapa TOCMAI cand raporteaza o eroare ("a esuat" are un s-virgula)
# si omoara tot grupul de banci rămase. S-a intamplat la grupul 3.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")

RADACINA = Path(__file__).resolve().parent.parent
IESIRE = RADACINA / "output" / "crawl"


def log(mesaj):
    print(mesaj, flush=True)


def urluri_din_sitemap(ctx, url_sitemap, limita_copii=6, jurnal=None):
    """Extrage URL-urile dintr-un sitemap, urmarind si indexurile de sitemap.

    Decodarea e tolerantă, si asta nu e o rafinare. Sitemap-ul Raiffeisen are
    peste 250 KB si NU e UTF-8 valid; `resp.text()` arunca UnicodeDecodeError,
    iar `except Exception: continue` inghitea eroarea si intorcea zero adrese.
    Crawlul trecea in liniste pe descoperirea prin navigatie, cu 113 adrese in
    loc de mii — al saselea mecanism din proiect care ascunde un eșec, si al
    doilea de forma "except Exception peste tot".
    """
    if not url_sitemap:
        return []
    de_citit, gasite, vizitate = [url_sitemap], [], set()
    while de_citit and len(vizitate) <= limita_copii:
        curent = de_citit.pop(0)
        if curent in vizitate:
            continue
        vizitate.add(curent)
        try:
            resp = ctx.request.get(curent, timeout=30000)
            if not resp.ok:
                if jurnal is not None:
                    jurnal.append((curent, f"cod {resp.status}"))
                continue
            # body() + decodare tolerantă, NU text(): un octet invalid nu are
            # voie sa arunce tot sitemap-ul
            text = resp.body().decode("utf-8", errors="replace")
        except Exception as e:
            if jurnal is not None:
                jurnal.append((curent, str(e).splitlines()[0][:70]))
            continue
        locuri = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", text)
        if "<sitemapindex" in text[:600].lower():
            de_citit.extend(locuri[:limita_copii])
        else:
            gasite.extend(locuri)
    return gasite


def _domeniu_radacina(gazda):
    """Ultimele doua etichete: "www.raiffeisen.ro" -> "raiffeisen.ro"."""
    parti = (gazda or "").lower().split(".")
    return ".".join(parti[-2:]) if len(parti) >= 2 else gazda


def pe_domeniul_bancii(urluri, base):
    """Doar adresele de pe domeniul bancii.

    Un sitemap declarat in robots.txt poate trimite la ALT site. BNP Paribas
    Romania are baza pe "www.romania.bnpparibas.com", iar robots.txt-ul lui
    declara "https://www.bnpparibas.lu/sitemap_index.xml" — sitemap-ul filialei
    din Luxemburg, cu 418 adrese care n-au nicio legatura cu piata romaneasca.
    Folosite ca atare, ar fi umplut crawlul cu pagini straine si ar fi produs
    date despre alta tara.

    Standardul permite sitemap-uri pe alta gazda, deci nu e o eroare a bancii —
    e o presupunere a noastra care trebuia verificata.
    """
    radacina = _domeniu_radacina(urlparse(base).netloc)
    return [u for u in urluri
            if _domeniu_radacina(urlparse(u).netloc) == radacina]


def urluri_din_navigatie(page, base):
    """Fallback: strange link-urile interne din homepage."""
    try:
        page.goto(base, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(3000)
        hrefs = page.eval_on_selector_all("a[href]", "e => e.map(a => a.href)")
    except Exception as e:
        log(f"      ! navigatie eșuată: {str(e).splitlines()[0][:70]}")
        return []
    domeniu = urlparse(base).netloc.replace("www.", "")
    interne = set()
    for h in hrefs:
        if domeniu in h and "#" not in h and not h.lower().endswith(
                (".jpg", ".png", ".svg", ".zip", ".doc", ".docx")):
            interne.add(h.split("?")[0])
    return sorted(interne)


class VerificatorRobots:
    """Aplica robots.txt pe fiecare origine intalnita, nu doar pe domeniul bancii.

    Necesar fiindca documentele stau adesea pe alt domeniu (ex. PDF-urile BCR sunt
    pe cdn.erstegroup.com), iar robots.txt e specific fiecarei origini.
    """

    def __init__(self, pagina_robots, request_ctx=None):
        self.pagina = pagina_robots
        self.request_ctx = request_ctx
        self.cache = {}

    def pentru(self, url, banca_id=None, delay=2):
        analiza = urlparse(url)
        origine = f"{analiza.scheme}://{analiza.netloc}"
        if origine not in self.cache:
            reguli = RegulliRobots(banca_id or "", origine, delay)
            reguli.citeste(self.pagina, self.request_ctx)
            self.cache[origine] = reguli
            log(f"      robots[{analiza.netloc}]: {reguli.status}")
        return self.cache[origine]

    def permite(self, url, banca_id=None):
        return self.pentru(url, banca_id).permite(url)


def descarca_pdf(ctx, url, dosar):
    """Descarca un PDF; returneaza calea sau None.

    Numele venea din ultimul segment al URL-ului, si de aici doua defecte care
    lucrau impreuna:

    1. Doua adrese diferite cu acelasi nume de fisier ajungeau in acelasi loc.
       Masurat: 8 cai folosite de 16 URL-uri. Doua adrese TBI ("/2023/09/" si
       "/2022/09/") servesc fisiere de 68.548 si 68.572 octeți.
    2. "if cale.exists(): return" intorcea calea FARA sa descarce. Deci al doilea
       URL nu era luat niciodata, iar `fisier_local` al lui trimitea la octeții
       PRIMULUI. Sonda de schimbari a comparat apoi unul cu amprenta celuilalt si
       a raportat "TBI si-a schimbat documentul" — ce nu se intamplase.

    Al doilea defect avea si un efect propriu, independent de coliziuni: o
    recrawlare nu reinnoia NICIUN document, fiindca toate existau deja pe disc.
    Crawlul singur n-ar fi vazut niciodata o schimbare.

    Acum numele vine din URL-ul intreg (crawler/urme.nume_din_url), deci e unic
    si stabil, iar descarcarea se face de fiecare data.
    """
    cale = dosar / nume_din_url(url)
    try:
        resp = ctx.request.get(url, timeout=60000)
        if not resp.ok:
            return None
        date = resp.body()
        if not date.startswith(b"%PDF"):
            return None
        dosar.mkdir(parents=True, exist_ok=True)
        cale.write_bytes(date)
        return str(cale.relative_to(RADACINA))
    except Exception:
        return None


def crawl_banca(browser, banca, args):
    """Crawleaza o singura banca si returneaza rezultatul."""
    bid, base = banca["id"], banca["base"]
    log(f"\n{'='*74}\n### {banca['nume']}  ({base})")
    if banca.get("nota"):
        log(f"    nota: {banca['nota']}")

    rezultat = {
        "banca_id": bid,
        "nume": banca["nume"],
        "base_url": base,
        "moment_crawl": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pagini": [],
        "erori": [],
    }

    ctx = browser.new_context(user_agent=UA, locale="ro-RO")
    page = ctx.new_page()
    page.set_default_timeout(45000)
    pagina_robots = ctx.new_page()
    verificator = VerificatorRobots(pagina_robots, ctx.request)

    # 1. robots.txt
    reguli = RegulliRobots(bid, base, banca.get("delay", 2))
    reguli.citeste(pagina_robots, ctx.request)
    origine_baza = f"{urlparse(base).scheme}://{urlparse(base).netloc}"
    verificator.cache[origine_baza] = reguli
    rezultat["robots"] = {"status": reguli.status, "delay_aplicat": reguli.delay,
                          "sitemapuri_declarate": reguli.sitemapuri[:5]}
    log(f"    robots.txt: {reguli.status} | pauza {reguli.delay}s")
    if reguli.status.startswith("NECITIT"):
        log("    ATENTIE: regulile nu au putut fi citite; crawl fara confirmare robots.txt")
        rezultat["avertisment"] = "robots.txt necitit - reguli neconfirmate"

    # 2. descoperirea URL-urilor
    #
    # Se incearca pe rand: ce declara banca in robots.txt, apoi ce am scris noi
    # in banci.py, si abia la urma navigatia. Ordinea asta conteaza: patru banci
    # (ING, Raiffeisen, Revolut, Cetelem) DECLARA un sitemap in robots.txt, iar
    # crawlul il ignora fiindca citea numai configuratia. Masurat pe cele 23 de
    # banci, descoperirea prin sitemap acopera 10,7 cerinte din 20, iar cea prin
    # navigatie doar 4,8 — de doua ori mai putin.
    candidati_sitemap = []
    for u in list(reguli.sitemapuri) + [banca.get("sitemap")]:
        if u and u not in candidati_sitemap:
            candidati_sitemap.append(u)

    urluri, sursa, jurnal, folosit = [], "navigatie", [], None
    for u in candidati_sitemap:
        if not reguli.permite(u):
            log(f"    sitemap interzis de robots.txt: {u[:66]}")
            jurnal.append((u, "interzis de robots.txt"))
            continue
        gasite = urluri_din_sitemap(ctx, u, jurnal=jurnal)
        proprii = pe_domeniul_bancii(gasite, base)
        if gasite and not proprii:
            log(f"    sitemap de pe ALT site, ignorat: {u[:56]} "
                f"({len(gasite)} adrese straine)")
            jurnal.append((u, f"{len(gasite)} adrese, niciuna pe domeniul bancii"))
            continue
        if proprii:
            if len(proprii) < len(gasite):
                log(f"    sitemap: {len(gasite) - len(proprii)} adrese de pe alte "
                    f"domenii, ignorate")
            urluri, sursa, folosit = proprii, "sitemap", u
            log(f"    sitemap: {u[:66]}")
            break
    if not urluri:
        urluri = urluri_din_navigatie(page, base)
        sursa = "navigatie"

    log(f"    descoperire ({sursa}): {len(urluri)} URL-uri")
    # Eșecurile de sitemap se scriu in rezultat, nu se inghit: unul dintre ele a
    # costat 10x din descoperirea Raiffeisen (sitemap care nu e UTF-8 valid).
    for u, motiv in jurnal:
        log(f"      ! sitemap eșuat: {u[:58]} — {motiv}")
    rezultat["descoperire"] = {"sursa": sursa, "total_urluri": len(urluri),
                               "sitemap_folosit": folosit,
                               "sitemapuri_eșuate": [{"url": u, "motiv": m}
                                                     for u, m in jurnal]}

    # 3. clasificare + filtrare robots + selectie condusa de cerinte
    candidati = {c: [] for c in CATEGORII}
    documente = []
    for u in urluri:
        if not reguli.permite(u):
            continue
        if u.lower().split("?")[0].endswith(".pdf"):
            documente.append(u)
            continue
        cat = clasifica(u, CATEGORII, EXCLUDE)
        if cat:
            candidati[cat].append((scor_url(u, cat), u))
    for lista in candidati.values():
        lista.sort(key=lambda x: (-x[0], len(x[1])))

    selectate, alese, acoperite = [], set(), {}

    # Pasul 1: o pagina garantata pentru fiecare cerinta, daca exista pe site.
    # Fara asta, plafonul pe categorie face imposibila acoperirea celor 5 tipuri
    # de credit sau a produselor de corporate.
    #
    # Cautarea e deliberat independenta de categorie: clasificarea merge pe primul
    # cuvant-cheie potrivit, deci un URL ca ".../conturi-si-servicii/servicii-cash-management"
    # ajunge in "conturi_carduri", nu in "business". Caut peste tot, dar prefer
    # categoria asteptata a cerintei.
    toti_candidatii = [(s, u, cat) for cat, lista in candidati.items() for s, u in lista]
    for cerinta_id, cat_preferata, chei in CERINTE_TINTA:
        potriviri = [(s, u, c) for s, u, c in toti_candidatii
                     if u not in alese and any(k in u.lower() for k in chei)]
        if potriviri:
            potriviri.sort(key=lambda x: (x[2] != cat_preferata, -x[0], len(x[1])))
            _, u, c = potriviri[0]
            selectate.append((c, u))
            alese.add(u)
            acoperite[cerinta_id] = u

    # Pasul 2: umple bugetul ramas, round-robin pe categorii
    buget = max(0, args.max_pe_banca - len(selectate))
    if buget:
        indici = {c: 0 for c in candidati}
        adaugate = 0
        while adaugate < buget:
            progres = False
            for cat, lista in candidati.items():
                if adaugate >= buget:
                    break
                while indici[cat] < len(lista):
                    _, u = lista[indici[cat]]
                    indici[cat] += 1
                    if u not in alese:
                        selectate.append((cat, u))
                        alese.add(u)
                        adaugate += 1
                        progres = True
                        break
            if not progres:
                break

    interzise = sum(1 for u in urluri if not reguli.permite(u))
    if interzise:
        log(f"    {interzise} URL-uri sarite (interzise de robots.txt)")
    lipsa = [c for c, _, _ in CERINTE_TINTA if c not in acoperite]
    log(f"    cerinte acoperite: {len(acoperite)}/{len(CERINTE_TINTA)}"
        + (f" | lipsesc: {', '.join(lipsa)}" if lipsa else ""))
    log(f"    de vizitat: {len(selectate)} pagini"
        + (f" | {len(documente)} documente in sitemap" if documente else ""))
    rezultat["cerinte_acoperite"] = acoperite
    rezultat["cerinte_lipsa"] = lipsa
    rezultat["documente_din_sitemap"] = documente[:60]

    # 4. extragere
    dosar_pdf = IESIRE / "pdf" / bid
    for i, (cat, u) in enumerate(selectate, 1):
        try:
            resp = page.goto(u, wait_until="domcontentloaded", timeout=45000)
            cod = resp.status if resp else None
            if cod != 200:
                rezultat["erori"].append({"url": u, "status": cod})
                log(f"    [{i}/{len(selectate)}] {cod} {u[:78]}")
                continue
            page.wait_for_timeout(2500)
            date = extrage(page, u, cat)

            if args.pdf and date["pdfs"]:
                for p in date["pdfs"][:args.max_pdf]:
                    # PDF-urile stau adesea pe alt domeniu: verificam robots.txt-ul lui
                    if not verificator.permite(p["url"], bid):
                        p["sarit"] = "interzis de robots.txt"
                        continue
                    cale = descarca_pdf(ctx, p["url"], dosar_pdf)
                    if cale:
                        p["fisier_local"] = cale

            rezultat["pagini"].append(date)
            log(f"    [{i}/{len(selectate)}] OK {cat:<16} "
                f"tab={date['numar_tabele']} rate={len(date['linii_rata'])} "
                f"pdf={len(date['pdfs'])}  {u[:56]}")
        except Exception as e:
            mesaj = str(e).splitlines()[0][:110]
            rezultat["erori"].append({"url": u, "eroare": mesaj})
            log(f"    [{i}/{len(selectate)}] ERR {u[:60]} — {mesaj[:50]}")
        time.sleep(reguli.delay)

    ctx.close()

    pdf_descarcate = sum(1 for p in rezultat["pagini"] for d in p["pdfs"]
                         if d.get("fisier_local"))
    pdf_sarite = sum(1 for p in rezultat["pagini"] for d in p["pdfs"] if d.get("sarit"))
    rezultat["sumar"] = {
        "pagini_extrase": len(rezultat["pagini"]),
        "tabele_total": sum(p["numar_tabele"] for p in rezultat["pagini"]),
        "linii_rata_total": sum(len(p["linii_rata"]) for p in rezultat["pagini"]),
        "pdfs_gasite": sum(len(p["pdfs"]) for p in rezultat["pagini"]),
        "pdfs_descarcate": pdf_descarcate,
        "pdfs_sarite_robots": pdf_sarite,
        "erori": len(rezultat["erori"]),
    }
    log(f"    >> {rezultat['sumar']}")
    return rezultat


def main():
    ap = argparse.ArgumentParser(description="Crawler produse si tarife bancare")
    ap.add_argument("--banci", help="lista de id-uri separate prin virgula")
    ap.add_argument("--max-pe-categorie", type=int, default=4)
    # Ridicata de la 32: masurat pe crawlul din 16 septembrie, BCR avea 2.559
    # de adrese in sitemap si ne uitam la 32 din ele. Acoperirea cerintelor
    # era 37% (170 din 460), iar limita era una din cele doua cauze.
    ap.add_argument("--max-pe-banca", type=int, default=80)
    ap.add_argument("--pdf", action="store_true", help="descarca PDF-urile de tarife")
    ap.add_argument("--max-pdf", type=int, default=5, help="PDF-uri descarcate pe pagina")
    ap.add_argument("--fara-bnr", action="store_true")
    args = ap.parse_args()

    IESIRE.mkdir(parents=True, exist_ok=True)

    selectie = BANCI
    if args.banci:
        ceruta = {b.strip() for b in args.banci.split(",")}
        selectie = [b for b in BANCI if b["id"] in ceruta]
        lipsa = ceruta - {b["id"] for b in selectie}
        if lipsa:
            log(f"! id-uri necunoscute: {', '.join(sorted(lipsa))}")
        if not selectie:
            sys.exit("Nicio banca selectata.")

    log(f"Crawler pornit: {len(selectie)} banci | "
        f"max {args.max_pe_banca} pagini/banca | PDF: {'da' if args.pdf else 'nu'}")

    toate = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for banca in selectie:
            try:
                rez = crawl_banca(browser, banca, args)
            except Exception as e:
                log(f"    !! {banca['id']} a eșuat: {str(e).splitlines()[0][:100]}")
                rez = {"banca_id": banca["id"], "nume": banca["nume"],
                       "eroare_fatala": str(e).splitlines()[0][:200]}
            toate.append(rez)
            (IESIRE / f"{banca['id']}.json").write_text(
                json.dumps(rez, ensure_ascii=False, indent=2), encoding="utf-8")
        browser.close()

    # cursul de referinta BNR
    bnr = None
    if not args.fara_bnr:
        try:
            bnr = curs_referinta()
            (IESIRE / "bnr_curs_referinta.json").write_text(
                json.dumps(bnr, ensure_ascii=False, indent=2), encoding="utf-8")
            zi = bnr["zile"][0] if bnr["zile"] else {}
            log(f"\nBNR curs referinta {zi.get('data')}: "
                f"EUR={zi.get('cursuri', {}).get('EUR')} "
                f"USD={zi.get('cursuri', {}).get('USD')}")
        except Exception as e:
            log(f"\n! BNR a eșuat: {str(e).splitlines()[0][:100]}")

    # Consolidarea se face din fisierele de pe disc, NU din lista acestei rulari.
    # Altfel doua procese pornite in paralel pe seturi diferite de banci si-ar
    # suprascrie consolidarea unul altuia, iar ultimul care termina ar lasa in
    # fisier numai bancile lui. Crawl-delay e per origine, deci bancile diferite
    # POT fi luate in paralel fara sa apasam mai tare pe niciun server — dar
    # atunci fisierele comune trebuie sa suporte scrieri concurente.
    de_pe_disc = []
    for f in sorted(IESIRE.glob("*.json")):
        if f.name in ("consolidat.json", "bnr_curs_referinta.json"):
            continue
        try:
            de_pe_disc.append(json.loads(f.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError) as e:
            log(f"! {f.name} nu s-a putut citi la consolidare: {str(e)[:60]}")
    consolidat = {
        "moment": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "banci": de_pe_disc,
        "bnr_curs_referinta": bnr,
    }
    (IESIRE / "consolidat.json").write_text(
        json.dumps(consolidat, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"\nconsolidat: {len(de_pe_disc)} banci de pe disc "
        f"({len(toate)} in rularea asta)")

    log(f"\n{'='*74}\nSUMAR FINAL")
    for r in toate:
        s = r.get("sumar")
        if s:
            log(f"  {r['banca_id']:<14} pagini={s['pagini_extrase']:<3} "
                f"tabele={s['tabele_total']:<4} rate={s['linii_rata_total']:<4} "
                f"pdf={s['pdfs_gasite']:<4} descarcate={s['pdfs_descarcate']:<3} "
                f"sarite={s['pdfs_sarite_robots']:<3} erori={s['erori']}")
        else:
            log(f"  {r['banca_id']:<14} {r.get('eroare_fatala', 'fara date')[:60]}")
    log(f"\nRezultate in: {IESIRE}")


if __name__ == "__main__":
    main()
