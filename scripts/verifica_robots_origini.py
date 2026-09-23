"""robots.txt pentru originile TERȚE de pe care am descarcat documente.

Rulare:  python scripts/verifica_robots_origini.py
Ieșire:  output/robots/<origine>.txt        — fișierul brut, ca dovada
         output/robots_origini.json         — verdictul pe fiecare document

De ce exista scriptul: robots.txt e per origine prin standard (RFC 9309), iar
documentele bancilor stau des pe alt domeniu. Regula am scris-o de la inceput,
dar crawlul a citit robots.txt numai pentru site-ul fiecarei banci. Registrul de
amprente a scos la iveala ca 63 de documente descarcate vin de pe 10 origini
pentru care nu exista nicio regula citita — cdn.erstegroup.com (45, pentru BCR),
static.anaf.ro, www.transfond.ro, www.oecd.org, www.arb.ro si altele.

O regula citita pentru www.bcr.ro nu spune NIMIC despre ce se poate lua de pe
cdn.erstegroup.com. ING a fost cazul care a dovedit ca diferenta conteaza:
"Disallow: *.pdf" pe ing.ro, deci documentele lor nu se descarca.

Ce face scriptul cu ce gaseste: doar raporteaza. Stergerea unui fisier interzis
o face omul, cu --sterge, dupa ce citeste verdictul. Un script care sterge
singur pe baza unei reguli abia citite e exact felul de automatizare in care nu
trebuie sa ai incredere.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

RADACINA = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADACINA))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright

from crawler.robots import RegulliRobots
from crawler.urme import STARI_CU_DOCUMENT, citeste_urme, compara, observa

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
IEȘIRE = RADACINA / "output" / "robots_origini.json"
DOSAR_ROBOTS = RADACINA / "output" / "robots"


def origini_de_verificat():
    """Originile terțe cu documente descarcate, si documentele lor."""
    urme = citeste_urme()
    observat, momente = observa()
    stari = compara(urme, observat, momente)
    pe_origine = defaultdict(list)
    for url, s in stari.items():
        if s["stare"] in STARI_CU_DOCUMENT and not s.get("origine_proprie"):
            pe_origine[s["origine"]].append({"url": url, "banca": s["banca"],
                                             "cale": s.get("cale")})
    return pe_origine


def main():
    pe_origine = origini_de_verificat()
    if not pe_origine:
        print("nicio origine terța cu documente descarcate — nimic de verificat")
        return

    print(f"{len(pe_origine)} origini, "
          f"{sum(len(v) for v in pe_origine.values())} documente\n")

    rezultat = {}
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(user_agent=UA, locale="ro-RO")
        pagina = ctx.new_page()
        for origine, documente in sorted(pe_origine.items(),
                                         key=lambda kv: -len(kv[1])):
            reguli = RegulliRobots(origine, f"https://{origine}")
            try:
                reguli.citeste(pagina, ctx.request)
            except Exception as e:
                reguli.status = f"eroare: {str(e).splitlines()[0][:70]}"

            # Fișierul brut se pastreaza ca dovada, cu numele originii.
            brut = reguli.text_brut
            if brut:
                DOSAR_ROBOTS.mkdir(parents=True, exist_ok=True)
                (DOSAR_ROBOTS / f"{origine.replace(':', '_')}.txt").write_text(
                    brut, encoding="utf-8")

            verdicte = []
            for d in documente:
                permis = reguli.permite(d["url"])
                verdicte.append(dict(d, permis=permis))

            interzise = [v for v in verdicte if not v["permis"]]
            rezultat[origine] = {
                "status": reguli.status,
                "delay": reguli.delay,
                "reguli": len(reguli.reguli),
                "documente": len(verdicte),
                "interzise": len(interzise),
                "verdicte": verdicte,
            }
            semn = "!!" if interzise else "ok"
            print(f"{semn} {origine:<30} {reguli.status[:42]:<42} "
                  f"{len(verdicte):>3} doc, {len(interzise)} interzise")
            for v in interzise:
                print(f"     INTERZIS  {v['url']}")
                print(f"               local: {v['cale']}  (legat de la {v['banca']})")
        b.close()

    IEȘIRE.write_text(json.dumps(rezultat, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    tot_interzis = sum(r["interzise"] for r in rezultat.values())
    # Cele doua feluri de "n-am citit fișierul" NU sunt acelasi lucru, si a le
    # pune la comun ar fi o alarma falsa: prin RFC 9309, un cod 4xx e un raspuns
    # definitiv — originea nu declara restricții — in timp ce o eroare de rețea
    # nu e un raspuns deloc. Aceeasi distincție ca intre LIPSA si NEVERIFICAT in
    # registrul de amprente, si ca intre SURSA_VECHE si NEVERIFICAT in validator.
    fara_reguli = [o for o, r in rezultat.items()
                   if "inaccesibil" in r["status"] or "4" == r["status"][-4:-3]]
    fara_verdict = [o for o, r in rezultat.items()
                    if not r["status"].startswith("citit") and o not in fara_reguli]

    print(f"\n>> {IEȘIRE.relative_to(RADACINA)}")
    print(f"   {tot_interzis} documente interzise de robots.txt al originii lor")
    if fara_reguli:
        print(f"   {len(fara_reguli)} origini fara robots.txt (cod 4xx): "
              f"{', '.join(sorted(fara_reguli))}")
        print("   Prin RFC 9309 asta e un raspuns, nu o lipsa de raspuns: originea")
        print("   nu declara nicio restricție, deci documentele sunt permise.")
    if fara_verdict:
        print(f"   !! {len(fara_verdict)} origini FARA VERDICT (eroare de rețea, nu 4xx): "
              f"{', '.join(sorted(fara_verdict))}")
        print("   Aici verificarea nu s-a putut face, deci nu e o confirmare.")
        print("   Documentele lor rămân nejudecate pana la o rulare reusita.")
    if tot_interzis:
        print("\n   Fișierele interzise trebuie șterse. Scriptul NU le șterge singur;")
        print("   citește verdictul si ruleaza cu --sterge daca ești de acord.")
        if "--sterge" in sys.argv:
            n = 0
            for r in rezultat.values():
                for v in r["verdicte"]:
                    if not v["permis"] and v["cale"]:
                        cale = RADACINA / v["cale"]
                        if cale.exists():
                            cale.unlink()
                            n += 1
                            print(f"   șters: {v['cale']}")
            print(f"\n   {n} fișiere șterse")


if __name__ == "__main__":
    main()
