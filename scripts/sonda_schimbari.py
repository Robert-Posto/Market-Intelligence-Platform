"""Intreaba serverele ce s-a schimbat, INAINTE sa descarce ceva.

Rulare:  python scripts/sonda_schimbari.py
         python scripts/sonda_schimbari.py --uita-te        (nu scrie registrul)
         python scripts/sonda_schimbari.py --origine cdn.erstegroup.com
Ieșire:  output/sonda_schimbari.json   — raspunsul serverului pe fiecare document
         output/urme.json              — semnalele si amprentele confirmate

Recrawlarea completa ar descarca 316 documente ca sa afle ca vreo 310 sunt
identice. O cerere HEAD raspunde la aceeasi intrebare fara sa ia niciun octet
inutil — si e mai politicoasa fata de banci.

Repartizarea rolurilor, si e partea care conteaza:

    Semnalul serverului decide DACA merita sa ne uitam.
    Octeții decid DACA s-a schimbat.

ETag se poate schimba fara ca fișierul sa se schimbe (rescriere, alt nod de
CDN), si un fișier se poate schimba pastrand aceeasi lungime. Deci semnalul nu e
crezut pe cuvant: unde zice "altfel", se descarca si se confirma prin sha256.

La PRIMA rulare nu exista ETag stocat — nu a fost inregistrat pe 16 septembrie,
cand s-a facut crawlul. Deci prima sonda nu poate folosi If-None-Match; foloseste
ce se poate compara imediat:

    Content-Length != octeții stocati   -> s-a schimbat sigur, se descarca
    Last-Modified mai nou decat baza    -> poate s-a schimbat, se descarca
    ambele la fel (sau absente)         -> PROBABIL neschimbat, nu s-a citit

Ultima stare NU e o confirmare, si nu e scrisa ca si cum ar fi. A patra oara in
proiect cand distincția asta conteaza — dupa cele patru stari ale validatorului,
LIPSA/NEVERIFICAT din registru si 4xx/eroare-de-rețea din verificarea robots.
"""
import hashlib
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

RADACINA = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADACINA))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright

from crawler.robots import RegulliRobots
from crawler.urme import (actualizeaza_semnale, cale_unica, citeste_urme,
                          clasifica_semnal, observa, scrie_urme,
                          validator_de_incredere)

from crawler import UA
IEȘIRE = RADACINA / "output" / "sonda_schimbari.json"
ISTORIC = RADACINA / "output" / "crawl" / "pdf_istoric"
DELAY_IMPLICIT = 2
# Content-Length trebuie sa fie marimea entitatii, nu a corpului comprimat:
# altfel nu se poate compara cu marimea fisierului de pe disc. Vezi
# crawler/urme.clasifica_semnal — fara asta, 57 din 58 de descarcari au fost
# inutile.
FARA_COMPRIMARE = {"Accept-Encoding": "identity"}

ORDINE = ["SCHIMBAT", "REASEZAT", "NESCHIMBAT_CONFIRMAT",
          "NESCHIMBAT_PROBABIL", "FARA_SEMNAL", "INTERZIS", "EROARE"]




def main():
    doar_priveste = "--uita-te" in sys.argv
    filtru = None
    if "--origine" in sys.argv:
        filtru = sys.argv[sys.argv.index("--origine") + 1]

    urme = citeste_urme()
    documente = {u: r for u, r in urme.get("documente", {}).items()
                 if r.get("amprenta") and r.get("cale")}
    if filtru:
        documente = {u: r for u, r in documente.items()
                     if r.get("origine") == filtru}
    if not documente:
        print("nimic de sondat — ruleaza mai intai python scripts/urmareste.py")
        return

    pe_origine = defaultdict(list)
    for u, r in documente.items():
        pe_origine[r["origine"]].append(u)

    print(f"{len(documente)} documente, {len(pe_origine)} origini\n")

    # URL-urile care isi impart fisierul local: comparatia lor nu e valida
    observat, _ = observa()
    partajate = {u: r.get("cale_partajata") for u, r in observat.items()}
    rezultat, semnale, amprente_noi = {}, {}, {}
    stari = Counter()
    # originile prinse cu un validator care se schimba pe fisiere identice
    mincinosi = {}

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(user_agent=UA, locale="ro-RO")
        pagina = ctx.new_page()

        for origine, urls in sorted(pe_origine.items(), key=lambda kv: -len(kv[1])):
            # robots.txt se citeste per origine, si Crawl-delay se respecta per
            # origine. O regula pentru www.bcr.ro nu spune nimic despre CDN-ul lui.
            reguli = RegulliRobots(origine, f"https://{origine}")
            try:
                reguli.citeste(pagina, ctx.request)
            except Exception as e:
                reguli.status = f"eroare: {str(e).splitlines()[0][:60]}"
            delay = reguli.delay or DELAY_IMPLICIT
            print(f"-- {origine}  ({len(urls)} doc, delay {delay}s, "
                  f"{reguli.status[:38]})")

            for i, url in enumerate(sorted(urls)):
                rand = documente[url]
                if not reguli.permite(url):
                    rezultat[url] = {"stare": "INTERZIS", "motiv": "robots.txt"}
                    stari["INTERZIS"] += 1
                    continue
                if i:
                    time.sleep(delay)
                try:
                    resp = ctx.request.head(url, timeout=25000,
                                            headers=FARA_COMPRIMARE)
                    cap = {k.lower(): v for k, v in resp.headers.items()}
                    cod = resp.status
                except Exception as e:
                    rezultat[url] = {"stare": "EROARE",
                                     "motiv": str(e).splitlines()[0][:80]}
                    stari["EROARE"] += 1
                    continue

                if cod >= 400:
                    rezultat[url] = {"stare": "EROARE", "motiv": f"cod {cod}"}
                    stari["EROARE"] += 1
                    continue

                stare, sem, motiv = clasifica_semnal(
                    rand, cap,
                    foloseste_etag=validator_de_incredere(urme, origine, "etag"),
                    foloseste_lm=validator_de_incredere(urme, origine, "lm"))
                if partajate.get(url):
                    # Mai multe URL-uri scriu in acelasi fisier local, deci
                    # amprenta din registru poate fi a altui URL. Se descarca
                    # o data, ca fiecare URL sa-si primeasca propriul fisier.
                    stare, motiv = "DE_CITIT", "cale locala partajata cu alt URL"
                semnale[url] = sem

                if stare != "DE_CITIT":
                    rezultat[url] = {"stare": stare, "motiv": motiv,
                                     "banca": rand.get("banca")}
                    stari[stare] += 1
                    continue

                # semnalul zice "altfel" -> se descarca si se confirma pe octeți
                time.sleep(delay)
                try:
                    r2 = ctx.request.get(url, timeout=60000,
                                         headers=FARA_COMPRIMARE)
                    octeti = r2.body()
                except Exception as e:
                    rezultat[url] = {"stare": "EROARE",
                                     "motiv": f"descarcare: {str(e)[:60]}"}
                    stari["EROARE"] += 1
                    continue

                cale = RADACINA / rand["cale"]
                amp = hashlib.sha256(octeti).hexdigest()
                if partajate.get(url) and not doar_priveste:
                    noua = cale_unica(url, rand["cale"])
                    (RADACINA / noua).write_bytes(octeti)
                    rezultat[url] = {"stare": "REASEZAT", "motiv": motiv,
                                    "banca": rand.get("banca"),
                                    "cale_noua": noua}
                    stari["REASEZAT"] += 1
                    amprente_noi[url] = {"amprenta": amp,
                                        "octeti": len(octeti), "cale": noua}
                    continue
                schimbat = amp != rand["amprenta"]
                if schimbat and not doar_priveste:
                    # Versiunea veche se pastreaza INAINTE de suprascriere. Fara
                    # ea stim doar CA s-a schimbat, nu CE s-a schimbat — iar
                    # pentru o comparatie de piața "s-a schimbat fisierul" nu
                    # valoreaza mai nimic fața de "prețul a trecut de la X la Y".
                    # S-a intamplat deja: primul document schimbat (TBI) a fost
                    # suprascris si nu s-a mai putut spune ce anume difera.
                    ISTORIC.mkdir(parents=True, exist_ok=True)
                    pastrat = ISTORIC / f"{rand['amprenta'][:12]}_{cale.name}"
                    if not pastrat.exists():
                        pastrat.write_bytes(cale.read_bytes())
                    cale.write_bytes(octeti)
                    amprente_noi[url] = {"amprenta": amp, "octeti": len(octeti),
                                         "versiune_veche": str(
                                             pastrat.relative_to(RADACINA))}
                if not schimbat:
                    # Validatorul care a cerut descarcarea a mințit: octeții sunt
                    # aceiasi. De la rularea urmatoare nu se mai foloseste la
                    # originea asta, si se cade pe urmatorul.
                    care = ("etag" if motiv.startswith("ETag")
                            else "lm" if motiv.startswith("Last-Modified")
                            else None)
                    if care:
                        v = dict(mincinosi.get(origine) or {})
                        v[f"{care}_nesigur"] = True
                        v.setdefault("dovezi", []).append(
                            {"validator": care, "url": url, "motiv": motiv})
                        mincinosi[origine] = v
                stare = "SCHIMBAT" if schimbat else "NESCHIMBAT_CONFIRMAT"
                stari[stare] += 1
                rezultat[url] = {"stare": stare, "motiv": motiv,
                                 "banca": rand.get("banca"),
                                 "amprenta_veche": rand["amprenta"],
                                 "amprenta_noua": amp,
                                 "octeti_vechi": rand.get("octeti"),
                                 "octeti_noi": len(octeti)}
                print(f"   {stare}  {url.rsplit('/', 1)[-1][:56]}")
        b.close()

    print()
    for st in ORDINE:
        if stari.get(st):
            print(f"  {st:<22} {stari[st]:>4}")

    schimbate = {u: r for u, r in rezultat.items() if r["stare"] == "SCHIMBAT"}
    if schimbate:
        print("\n=== S-A SCHIMBAT LA BANCA ===")
        for u, r in sorted(schimbate.items(), key=lambda kv: kv[1].get("banca") or ""):
            print(f"  [{r['banca']}] {u}")
            print(f"      {r['amprenta_veche'][:12]} -> {r['amprenta_noua'][:12]}  "
                  f"({r['octeti_vechi']:,} -> {r['octeti_noi']:,} octeți)")
            print(f"      semnal: {r['motiv']}")
    else:
        print("\nniciun document schimbat.")

    # Acoperirea semnalelor, pe server. Nu o ascund intr-o medie: unde serverul
    # nu trimite nimic, singura cale de a sti e descarcarea, si asta trebuie
    # spus pe nume.
    fara = [u for u, r in rezultat.items() if r["stare"] == "FARA_SEMNAL"]
    if fara:
        pe_o = Counter(documente[u]["origine"] for u in fara)
        print(f"\n{len(fara)} documente FARA SEMNAL de la server, pe origini:")
        for o, n in pe_o.most_common():
            print(f"  {o:<32} {n:>3}")
        print("  Aici nu se poate sti fara descarcare. NU sunt raportate ca")
        print("  neschimbate — nu am verificat.")

    probabil = stari.get("NESCHIMBAT_PROBABIL", 0)
    if probabil:
        print(f"\n{probabil} documente NESCHIMBAT_PROBABIL: serverul spune ca nu s-au")
        print("  schimbat, dar octeții nu au fost cititi. Nu e o confirmare.")

    IEȘIRE.write_text(json.dumps(rezultat, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    print(f"\n>> {IEȘIRE.relative_to(RADACINA)}")

    if doar_priveste:
        print("(--uita-te: registrul NU s-a scris)")
        return
    if mincinosi:
        print(f"\n{len(mincinosi)} origini cu validator nesigur, "
              f"de acum ignorat acolo:")
        for o, v in sorted(mincinosi.items()):
            care = ", ".join(k[:-8] for k in v if k.endswith("_nesigur"))
            print(f"  {o:<30} {care} — schimbat pe octeți identici "
                  f"({len(v.get('dovezi', []))} dovezi)")
    nou = actualizeaza_semnale(urme, semnale, dict(stari), amprente_noi)
    # verdictele vechi se pastreaza: o origine prinsa ieri rămâne prinsa
    origini = {o: dict(v) for o, v in (nou.get("origini") or {}).items()}
    for o, v in mincinosi.items():
        origini[o] = dict(origini.get(o) or {}, **v)
    nou["origini"] = origini
    scris, mesaj = scrie_urme(nou)
    print(f"{'>>' if scris else '!!'} {mesaj}")


if __name__ == "__main__":
    main()
