"""Construiește arhiva pentru colegul care lucreaza cu BeautifulSoup.

Rulare:  python scripts/fa_arhiva.py [nume]
Ieșire:  output/pentru_coleg_bs4_<nume>.zip    (implicit: data de azi, "18sept")

Lista de scripturi e EXPLICITA, nu un glob. Din cele ~60 de scripturi din
scripts/, doar 21 sunt de folos cuiva din afara: restul sunt sonde de o singura
folosinta (debug_bt2, sniff_bnr, inspect_revolut) pe care le-am scris ca sa vad
o pagina o data. Un glob le-ar trimite pe toate si ar ascunde care conteaza.

Cele 319 documente descarcate NU intra: sunt ale bancilor, iar ING interzice
explicit descarcarea lor prin robots.txt (Disallow: *.pdf). Colegul le ia singur,
de la sursa, dupa ce citeste robots.txt pentru originea fiecaruia.
"""
import datetime
import pathlib
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RADACINA = pathlib.Path(__file__).resolve().parent.parent

MODULE = [
    "__init__.py", "banci.py", "bnr.py", "bnr_indici.py", "extractor.py",
    "main.py", "parser_pdf.py", "parser_rate.py", "parser_tarife.py",
    "ambiguitate.py", "data_document.py", "diferente.py", "robots.py", "urme.py",
    "validator.py",
    "vocabular.py",
]
SCRIPTURI = [
    # lanțul principal, in ordinea rularii
    "parseaza_tot.py", "parseaza_pdf.py", "parseaza_tarife.py",
    "unifica_comisioane.py", "ruleaza_validare.py", "compara_rate.py",
    "raport.py",
    # detecția schimbarii si conformitatea per origine
    "urmareste.py", "sonda_schimbari.py", "vechime_documente.py",
    # datarea documentelor: care pret e cel de azi
    "date_documente.py", "inventar_date.py", "compara_versiuni.py",
    "verifica_robots_origini.py",
    # masurare si calitate
    "calitate_tarife.py", "masoara_vocabular.py", "verifica_tarife.py",
    "valideaza.py",
    # etalonul manual
    "alege_esantion.py", "culege_etalon.py", "acoperire_etalon.py",
    "etalon_tarife.py",
    # teste si robots
    "test_validare.py", "test_generic.py", "test_indici.py",
    "test_robots_matcher.py", "verifica_robots_reale.py",
    "verifica_robots_toate.py",
    # arhiva insasi, ca sa fie reproductibila
    "fa_arhiva.py",
]
DOCUMENTE = [
    "BRIEFING_BEAUTIFULSOUP.md", "BRIEFING_BEAUTIFULSOUP_2.md",
    "BRIEFING_BEAUTIFULSOUP_3.md", "COMISIOANE_PDF.md", "COMISIOANE_TARIFE.md",
    # prima in lista: e singurul document pe care trebuie sa-l citeasca
    # cineva care doar integreaza datele
    "CITESTE_PENTRU_MERGE.md",
    "CONSTATARI.md", "DATAREA_DOCUMENTELOR.md", "SCHIMBARI_PRETURI.md",
    "RULARE_18SEPT.md", "RAPORT.md",
    "CONCLUZII.md", "DETECTIA_SCHIMBARII.md", "VECHIME_DOCUMENTE.md",
    "ETALON_MANUAL.md",
    "LUCRU_16_SEPTEMBRIE.md",
    "SUMAR_ACCESIBILITATE.md", "comparatie_comisioane.md", "comparatie_rate.md",
]
REZULTATE = [
    "bnr_indici.json", "comisioane_pdf.json", "comisioane_tarife.json",
    "comisioane_unificate.json", "etalon_manual.json", "necesita_llm.json",
    "rate_tipizate.json", "rate_unificate.json", "rate_validate.json",
    "urme.json", "robots_origini.json", "sonda_schimbari.json",
    "date_documente.json", "schimbari_preturi.json",
]


def main():
    nume = sys.argv[1] if len(sys.argv) > 1 else (
        f"{datetime.date.today().day}"
        f"{['ian','feb','mar','apr','mai','iun','iul','aug','sept','oct','nov','dec'][datetime.date.today().month - 1]}")
    ieșire = RADACINA / "output" / f"pentru_coleg_bs4_{nume}.zip"

    de_pus, lipsa = [], []
    for grup, dosar in (("crawler", MODULE), ("scripts", SCRIPTURI),
                        ("output", DOCUMENTE), ("output", REZULTATE)):
        for f in dosar:
            cale = RADACINA / grup / f
            (de_pus if cale.exists() else lipsa).append(f"{grup}/{f}")

    if lipsa:
        print(f"!! {len(lipsa)} fișiere din listă nu există:")
        for f in lipsa:
            print(f"   {f}")
        print("   arhiva se face fără ele — verifică dacă s-au redenumit\n")

    # Fisierele robots.txt brute merg intregi, ca dosar, nu pe lista: sunt
    # DOVADA primara de conformitate, iar cine o verifica trebuie sa se uite la
    # ce a raspuns serverul, nu la ce a inteles un script de-al nostru din el.
    robots = sorted((RADACINA / "output" / "robots").glob("*.txt"))

    with zipfile.ZipFile(ieșire, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in de_pus:
            z.write(RADACINA / rel, rel)
        for f in robots:
            z.write(f, f"output/robots/{f.name}")
    de_pus += [f"output/robots/{f.name}" for f in robots]

    kb = ieșire.stat().st_size / 1024
    print(f">> {ieșire.relative_to(RADACINA)}")
    print(f"   {len(de_pus)} fișiere, {kb:.0f} KB")
    print(f"   {len(MODULE)} module, {len(SCRIPTURI)} scripturi, "
          f"{len(DOCUMENTE)} documente, {len(REZULTATE)} rezultate")


if __name__ == "__main__":
    main()
