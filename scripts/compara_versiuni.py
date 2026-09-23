"""Ce PRET s-a schimbat, la documentele pe care sonda le-a gasit schimbate.

Rulare:  python scripts/compara_versiuni.py
Ieșire:  output/SCHIMBARI_PRETURI.md  +  output/schimbari_preturi.json

Sonda de schimbari spune CA s-a atins un document. Scriptul asta spune CE s-a
schimbat in el, si o spune in preturi, nu in octeți.

Perechile vin din registru: `urme.json` tine, pentru fiecare document care s-a
schimbat, calea versiunii vechi pastrate in `output/crawl/pdf_istoric`. Nimic
nu se descarca aici — se citeste doar ce e deja pe disc.

De ce se pot compara valorile, desi de obicei nu se poate: vezi antetul lui
`crawler/diferente.py`. Pe scurt — amandoua fișierele se parseaza ACUM, cu
acelasi parser, deci diferentele introduse de parser se anuleaza.
"""
import json
import sys
from pathlib import Path

RADACINA = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADACINA))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from crawler.data_document import data_documentului
from crawler.diferente import compara, rezumat
from crawler.parser_pdf import RE_NUME_FID, extrage
from crawler.parser_tarife import extrage_tarife

PDFURI = RADACINA / "output" / "crawl" / "pdf"
URME = RADACINA / "output" / "urme.json"
RAPORT = RADACINA / "output" / "SCHIMBARI_PRETURI.md"
JSON_IES = RADACINA / "output" / "schimbari_preturi.json"


def perechi():
    """(url, banca, cale_noua, cale_veche, moment) pentru fiecare schimbare cu octeți."""
    if not URME.exists():
        return []
    urme = json.loads(URME.read_text(encoding="utf-8"))
    out = []
    for url, d in (urme.get("documente") or {}).items():
        cale = d.get("cale")
        for h in (d.get("istoric") or []):
            vechi = h.get("versiune_veche")
            if not (vechi and cale):
                continue
            pn, pv = RADACINA / cale, RADACINA / vechi
            if pn.exists() and pv.exists():
                out.append((url, d.get("banca"), pn, pv, h.get("moment")))
    return sorted(out, key=lambda t: t[4] or "")


def parseaza(cale, banca):
    """Acelasi parser pe care il foloseste lantul pentru documentul asta.

    Alegerea se face dupa nume, ca in `parseaza_tarife.candidati` — formularul
    standardizat merge la `parser_pdf`, restul la `parser_tarife`. Important e
    ca AMBELE versiuni sa treaca prin acelasi parser; altfel comparatia masoara
    diferenta dintre parseri.
    """
    if RE_NUME_FID.search(cale.name):
        return extrage(cale, banca, radacina=cale.parent.parent)
    return extrage_tarife(cale, banca, radacina=cale.parent.parent)


def _et(cheie):
    serviciu, tip, moneda, frecventa = cheie[0], cheie[1], cheie[2], cheie[3]
    bucati = [(serviciu or "(fara nume)")[:56]]
    if moneda:
        bucati.append(moneda.upper())
    if frecventa:
        bucati.append(frecventa)
    return "  ".join(bucati) + f"  [{(tip or '').replace('comision_', '')}]"


def main():
    pr = perechi()
    print(f"documente cu doua versiuni pe disc: {len(pr)}\n")
    if not pr:
        print("Nimic de comparat. Sonda n-a gasit inca niciun document schimbat,\n"
              "sau octeții vechi n-au fost pastrati.")
        return

    L = ["# Ce preț s-a schimbat", "",
         "Generat de `scripts/compara_versiuni.py`. Fiecare secțiune e un document",
         "pe care sonda l-a găsit schimbat și pentru care avem păstrată și versiunea",
         "dinainte. Cele două se parsează **acum, cu același parser**, deci ce vezi",
         "aici vine din document, nu din codul nostru.", ""]
    toate = {}

    for url, banca, pn, pv, moment in pr:
        dn, dv = data_documentului(pn), data_documentului(pv)
        try:
            nou, vechi = parseaza(pn, banca), parseaza(pv, banca)
        except Exception as e:
            print(f"  EROARE  {pn.name[:44]}  {type(e).__name__}: {e}")
            L += [f"## {banca} — {pn.name}", "",
                  f"Nu s-a putut parsa: `{type(e).__name__}: {e}`", ""]
            continue

        dif = compara(vechi, nou)
        s = rezumat(dif)
        toate[url] = {"banca": banca, "moment": moment,
                      "data_veche": dv.get("data_vigoare"),
                      "data_noua": dn.get("data_vigoare"),
                      "valori_vechi": len(vechi), "valori_noi": len(nou),
                      "rezumat": s,
                      "pret": [{"serviciu": d["cheie"][0], "vechi": d["vechi"],
                                "nou": d["nou"],
                                "text": (d["exemplu"].get("text_sursa") or "")[:120]}
                               for d in dif["pret"]],
                      "banda": [{"serviciu": d["cheie"][0],
                                 "banda_veche": d["banda_veche"],
                                 "banda_noua": d["banda_noua"],
                                 "vechi": d["vechi"], "nou": d["nou"]}
                                for d in dif["banda"]]}

        print(f"  {banca:10} {pn.name[:42]:44} {len(vechi):4} -> {len(nou):4} valori"
              f"   preturi schimbate: {s['pret']}")

        L += [f"## {banca} — {pn.name}", "",
              f"`{url}`", "",
              f"- versiunea veche: **{dv.get('data_vigoare') or 'fără dată'}**, "
              f"{len(vechi)} valori extrase",
              f"- versiunea nouă: **{dn.get('data_vigoare') or 'fără dată'}**, "
              f"{len(nou)} valori extrase",
              f"- detectat de sondă la {(moment or '')[:16]}", ""]

        if dif["pret"]:
            L += [f"### Prețuri schimbate ({len(dif['pret'])})", "",
                  "| serviciu | vechi | nou |", "|---|---|---|"]
            for d in sorted(dif["pret"], key=lambda d: str(d["cheie"])):
                v = ", ".join(f"{x:g}" for x in d["vechi"]) or "—"
                n = ", ".join(f"{x:g}" for x in d["nou"]) or "—"
                L.append(f"| {_et(d['cheie'])} | {v} | {n} |")
            L.append("")
        else:
            L += ["### Niciun preț schimbat **din ce extragem**", "",
                  "Documentul s-a schimbat pe octeți, dar nicio valoare pe care o",
                  "citim noi nu s-a mișcat. Două explicații, și diferă mult:", "",
                  "1. schimbarea e cosmetică — dată nouă pe copertă, reformatare,",
                  "   o randare cu alt font;",
                  "2. **schimbarea e într-o parte a documentului pe care parserul",
                  "   nu o citește.**", "",
                  "A doua s-a întâmplat deja. La `Dobanzi_indicative.pdf` de la BCR,",
                  "tabelul de indici (IRCC, ROBOR, EURIBOR) chiar a rămas identic —",
                  "dar tabelul de dedesubt, cu dobânzile de referință proprii, a urcat",
                  "de la 12,57% la 12,70% pe RON. Parserul nu scoate nicio valoare din",
                  "el, deci comparația nu avea ce compara.", "",
                  "**Absența unei schimbări aici nu e o dovadă că banca n-a schimbat",
                  "nimic.** E o dovadă că n-a schimbat nimic din ce știm să citim.", ""]

        if dif["banda"]:
            L += [f"### Praguri mutate sau apărute ({len(dif['banda'])})", "",
                  "Aici **nu se poate decide automat** dacă banca a mutat un prag sau",
                  "dacă pragul exista dinainte și abia acum s-a putut citi. Ghidul BRD",
                  "din 1 septembrie nu avea glifele `≥` și `≤` în font, deci pragurile",
                  "scrise cu ele lipseau cu totul din text.", "",
                  "| serviciu | prag vechi | prag nou | valori |", "|---|---|---|---|"]
            for d in sorted(dif["banda"], key=lambda d: str(d["cheie"]))[:40]:
                v = ", ".join(f"{x:g}" for x in d["vechi"]) or "—"
                n = ", ".join(f"{x:g}" for x in d["nou"]) or "—"
                L.append(f"| {_et(d['cheie'])} | {d['banda_veche'] or '—'} "
                         f"| {d['banda_noua'] or '—'} | {v} → {n} |")
            L.append("")

        # Rândurile fără pereche se LISTEAZĂ, nu se numără. Schimbarea reală din
        # ghidul BRD — excepția Electrica de 1,50 lei, eliminată — e un rând
        # dispărut, nu un preț mutat: linia veche avea două înregistrări pentru
        # același serviciu ("gratuit" și "1,5 lei"), iar acum are una. Într-un
        # raport care le numără doar, exact asta se pierde.
        for eticheta, lot, explicatie in (
                ("Rânduri dispărute", dif["disparut"],
                 "Banca a încetat să perceapă ceva — sau am încetat noi să-l citim."),
                ("Rânduri apărute", dif["aparut"],
                 "Un tarif nou — sau un rând pe care versiunea veche nu-l dădea.")):
            if not lot:
                continue
            L += [f"### {eticheta} ({len(lot)})", "", explicatie, "",
                  "| serviciu | prag | valori |", "|---|---|---|"]
            for d in sorted(lot, key=lambda d: -max(d["valori"] or [0]))[:25]:
                v = ", ".join(f"{x:g}" for x in d["valori"]) or "—"
                tipuri = "/".join(t.replace("comision_", "") for t in d["tipuri"])
                L.append(f"| {_et(d['cheie'])} | {d['cheie'][-1] or '—'} "
                         f"| {v} _{tipuri}_ |")
            if len(lot) > 25:
                L.append(f"| … încă {len(lot) - 25} | | |")
            L.append("")

        if dif["reformatat"]:
            L += [f"*{len(dif['reformatat'])} rânduri au aceleași valori și același",
                  "prag, dar alt nume de serviciu: documentul a fost re-randat și",
                  "despărțirile în cuvinte s-au mutat. Nu e o schimbare de preț.*", ""]

    RAPORT.write_text("\n".join(L), encoding="utf-8")
    JSON_IES.write_text(json.dumps(toate, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    n_pret = sum(v["rezumat"]["pret"] for v in toate.values())
    print(f"\ntotal preturi schimbate: {n_pret}")
    print(f">> {RAPORT.relative_to(RADACINA)}")
    print(f">> {JSON_IES.relative_to(RADACINA)}")


if __name__ == "__main__":
    main()
