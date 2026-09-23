"""Tabelul de comparație a ratelor între bănci, pe vocabularul canonic de produse.

Rulare:  python scripts/compara_rate.py
Ieșire:  output/rate_unificate.json     (cele 555 de valori, cu produs/segment)
         output/comparatie_rate.md      (tabelul produs x bancă)

Perechea tabelului de comisioane. Diferența e că aici nu există nicio lege care
să standardizeze denumirile — vezi nota din crawler/vocabular.py.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RADACINA = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADACINA))

from crawler.validator import consens_indici
from crawler.vocabular import produs_canonic

MIN_BANCI = 3
# Cat de mult pot varia valorile intr-o linie ca ea sa rămana o comparatie.
# Mai larg decat la comisioane (5): ratele de credit chiar variaza mult intre
# banci si intre profiluri de client, fara ca asta sa insemne ca s-au amestecat
# produse diferite.
DISPERSIE_MAX = 8

# Ce NU e o rata de dobanda, desi sta in acelasi set. Etalonul manual le-a gasit
# pe toate trei; fara excludere ar apărea in tabel ca "dobanda 0%".
TIPURI_EXCLUSE = {
    "rate_fara_dobanda",   # promoții "3 rate cu 0% dobandă" — 78 de valori
    "cashback",            # beneficiu, nu cost
    "comision_procent",    # comision, are deja tabelul lui
}
# Valorile indicilor de piata nu se compara intre banci: sunt aceeasi cifra
# publicata de BNR, iar diferenta dintre banci masoara cat de veche e pagina, nu
# oferta. Ele stau in raportul de validare, nu aici.
TIPURI_INDICI = {"ircc_valoare", "robor_valoare", "euribor_valoare"}


# --- marja peste indice -> rata totala ---
#
# Libra publica marja peste IRCC ("IRCC + 2,15%"), iar majoritatea celorlalti publica
# rata nominala. E aceeasi informatie in doua unitati, dar tabelul le pune pe randuri
# diferite — asa incat Libra lipsea din linia de credit de nevoi personale, unde stau
# 8 banci, adica exact cel mai comparat produs bancar.
#
# Conversia se aplica la TOATE bancile care publica marja, nu doar la Libra: sunt 9,
# iar Raiffeisen are 8 valori, ProCredit 7, BRD 5. A converti doar pentru banca
# proprie ar umfla-o in tabel.
#
# Ce NU se converteste, si de ce:
#   marja_euribor  - consensul pentru EURIBOR vine de la o singura banca (Patria).
#                    O sursa nu e un consens, deci n-avem indice de incredere.
#   marja_fixa     - la Patria textul e "IRCC + marja fixa a bancii (de la 6,67% la
#                    17,24%)". Un interval de 6,67-17,24 e prea larg pentru o marja;
#                    alea par TOTALURI clasificate greșit ca marja. De verificat
#                    separat — deocamdata a converti de acolo ar inventa cifre.
MARJE_CONVERTIBILE = {"marja_ircc": "ircc"}

# O rata fixa si una variabila nu sunt acelasi produs, oricat de apropiate ar fi
# cifrele. Conversia marja -> total a scos asta la iveala: in linia de credit de
# nevoi personale, Libra intra cu 7,71-10,06 (variabila, la IRCC-ul de azi) alaturi
# de Salt 5,49 si BRD 5,70 — care sunt RATE FIXE, si pe deasupra "de la". Comparate
# direct, ar sugera ca Libra e scumpa, cand de fapt sunt doua produse diferite.
#
# Felul se citește determinist din text, ca frecvența la comisioane, deci intra in
# cheie. O marja peste un indice e variabila prin construcție.
RE_FIXA = re.compile(r"\bfix[ăae]?\b|\brat[ăa]\s+fix|\bdob[âa]nd[ăa]\s+fix", re.I)
RE_VARIABILA = re.compile(r"\bvariabil", re.I)
# "de la 5,49%" nu e un preț, e capătul de jos al unui interval — cel mai bun caz,
# pentru clientul cel mai bun. 16% din ratele nominale sunt așa. Nu putem recupera
# capătul de sus (pagina nu-l scrie), dar putem marca valoarea ca incompletă.
RE_CAPAT_DE_JOS = re.compile(
    r"\bde\s+la\b|\b[îi]ncep[âa]nd\s+(?:de\s+la|cu)\b|\bstarting\s+(?:from|at)\b", re.I)


def fel_rata(x):
    """'fixa', 'variabila' sau '-' daca pagina nu spune."""
    if x.get("derivata") or x["tip_rata"].startswith("marja"):
        return "variabila"
    text = x.get("text_sursa") or ""
    if RE_VARIABILA.search(text):
        return "variabila"
    if RE_FIXA.search(text):
        return "fixa"
    return "-"


def e_capat_de_jos(x):
    """Valoarea e marginea de jos a unui interval, nu un preț."""
    return bool(RE_CAPAT_DE_JOS.search(x.get("text_sursa") or ""))


def indice_in_vigoare(rate):
    """{nume_indice: (valoare, proveniența)} pentru indicii in care avem incredere.

    Sursa de drept e BNR. Cand descarcarea de la BNR lipseste (18 septembrie:
    ERR_CONNECTION_CLOSED), se cade pe consensul paginilor bancare — dar numai pe
    valorile pe care validatorul le-a confirmat cu BNR la o rulare anterioara, si
    numai daca vin de la cel putin doua banci independente. Proveniența se pastreaza
    si ajunge in tabel: o rata derivata dintr-un indice de mana a doua trebuie sa
    arate asta.
    """
    out = {}
    cale = RADACINA / "output" / "bnr_indici.json"
    if cale.exists():
        ircc = json.loads(cale.read_text(encoding="utf-8")).get("ircc") or {}
        rand = ircc.get("in_vigoare") or {}
        if rand.get("valoare"):
            out["ircc"] = (rand["valoare"], "BNR")
    if "ircc" not in out:
        # Consensul e calculat de validator (crawler/validator.py: consens_indici),
        # ca sa existe UN singur loc care decide ce credem despre un indice. Inainte
        # regula era scrisa si aici, si erau doua reguli care puteau diverge.
        din_consens = consens_indici(rate)
        if "ircc_valoare" in din_consens:
            out["ircc"] = din_consens["ircc_valoare"]
    return out


def deriva_totaluri(rate):
    """Adauga o rata nominala pentru fiecare marja peste un indice cunoscut.

    Inregistrarea derivata pastreaza marja si indicele folosit, si e marcata
    `derivata`: o rata calculata NU e o rata publicata. Fara marcaj, cineva citeste
    tabelul peste sase luni si crede ca Libra a publicat 7,71%, cand banca a publicat
    "IRCC + 2,15%".
    """
    indici = indice_in_vigoare(rate)
    noi = []
    for x in rate:
        nume = MARJE_CONVERTIBILE.get(x["tip_rata"])
        if not nume or nume not in indici or x["valoare"] is None:
            continue
        valoare, provenienta = indici[nume]
        noi.append({**x,
                    "tip_rata": "nominala",
                    "valoare": round(x["valoare"] + valoare, 4),
                    "derivata": True,
                    "marja_sursa": x["valoare"],
                    "indice_sursa": nume,
                    "indice_valoare": valoare,
                    "indice_provenienta": provenienta})
    return noi, indici


def capete_de_interval(rate):
    """Capatul de SUS al fiecarui interval declarat, ca valoare separata.

    Parserul reține valoarea si, separat, intervalul din care vine. Fara pasul asta,
    tabelul arata doar capatul de jos: ING apărea cu 5,99% cand pagina scrie "intre
    5,99% - 15,99%", iar Raiffeisen cu 5,95% din "intre 5.95% si 18.35%". Cinci banci
    din sapte pe randul de credit de nevoi personale erau asa, deci randul sugera ca
    ele sunt cele mai ieftine — cand de fapt le retinusem cel mai bun caz.

    Capatul de sus e scris in aceeasi propozitie, deci e la fel de publicat ca cel de
    jos. Emis ca inregistrare separata, intra automat si in celula si in dispersie.
    """
    noi = []
    for x in rate:
        iv = x.get("interval") or {}
        sus = iv.get("max")
        if sus is None or x["valoare"] is None or sus <= x["valoare"] + 0.01:
            continue
        noi.append({**x, "valoare": sus, "capat_de_sus": True})
    return noi


def incarca():
    """Ratele validate, cu produs, segment, capetele de interval si totalurile derivate."""
    date = json.loads((RADACINA / "output" / "rate_validate.json")
                      .read_text(encoding="utf-8"))
    out = []
    for x in date:
        produs, segment = produs_canonic(x)
        out.append({**x, "produs_canonic": produs, "segment": segment,
                    "derivata": False, "capat_de_sus": False})
    out += capete_de_interval(out)
    derivate, _indici = deriva_totaluri(out)
    return out + derivate


def _celula(valori):
    """Mediana, intervalul dacă diferă, și semnele de avertizare."""
    sume = sorted(v["valoare"] for v in valori)
    m = median(sume)
    text = f"{m:g}" if sume[0] == sume[-1] else f"{m:g} ({sume[0]:g}–{sume[-1]:g})"
    if any(v.get("stare") == "SURSA_VECHE" for v in valori):
        text += " ⚠"
    # o rata calculata din marja + indice, nu publicata de banca in forma asta
    if all(v.get("derivata") for v in valori):
        text += " †"
    elif any(v.get("derivata") for v in valori):
        text += " (†)"
    # toate valorile băncii sunt "de la X%" — capătul de jos, nu prețul
    if all(e_capat_de_jos(v) for v in valori):
        text += " ↓"
    return text


def _raport(valori):
    """Raportul intre cea mai mare si cea mai mica valoare nenula."""
    nenule = [v for v in valori if v]
    return max(nenule) / min(nenule) if nenule else 1.0


# Aceleasi doua masuri ca la comisioane (vezi unifica_comisioane.py): `max/min` pe
# toate valorile la comun amesteca dezacordul dintre banci cu eterogenitatea din
# interiorul unei banci. Pe cele 13 linii de rate clasificarea iese identica, dar
# cele doua numere spun care e problema pe fiecare rand.
def dispersie_intre(pe_banca):
    """Dezacordul dintre banci, pe chiar cifrele afisate (medianele)."""
    return _raport([median(sorted(v["valoare"] for v in valori))
                    for valori in pe_banca.values()])


def dispersie_interna(pe_banca):
    """Cea mai mare imprastiere din interiorul unei singure banci."""
    return max(_raport([v["valoare"] for v in valori])
               for valori in pe_banca.values())


def e_de_incredere(pe_banca):
    """Linia e o comparatie doar daca trec amandoua masurile."""
    return (dispersie_intre(pe_banca) <= DISPERSIE_MAX
            and dispersie_interna(pe_banca) <= DISPERSIE_MAX)


# Peste atatea produse diferite, la aceeasi banca, un text identic nu mai e despre
# vreun produs.
PRODUSE_MAX_PE_TEXT = 3


def mobilier_de_site(rate):
    """Textele care apar la mai multe produse ale aceleiasi banci.

    Acelasi principiu ca filtrul de subsol de pagina din PDF-uri, in alta forma:
    ce se repeta peste tot nu e despre nimic anume. Aici sunt teasere si note de
    subsol prezente pe toate paginile — nota Libra "*IRCC valabil de la
    01.07.2026: 5,56%" apare la patru produse diferite, iar promoția TBI "4 rate,
    0% dobanda" la sapte.
    """
    pe_text = defaultdict(set)
    for x in rate:
        if x["produs_canonic"]:
            pe_text[(x["banca"], x["text_sursa"][:70])].add(x["produs_canonic"])
    return {k for k, produse in pe_text.items()
            if len(produse) >= PRODUSE_MAX_PE_TEXT}


def linii(rate):
    """Liniile tabelului, doar pentru ce se poate compara."""
    respinse = mobilier_de_site(rate)
    grupe = defaultdict(lambda: defaultdict(list))
    for x in rate:
        if (not x["produs_canonic"] or x["valoare"] is None
                or x["tip_rata"] in TIPURI_EXCLUSE
                or x["tip_rata"] in TIPURI_INDICI
                or (x["banca"], x["text_sursa"][:70]) in respinse):
            continue
        # Moneda NU intra in cheie: o rata e un procent, nu are unitate de
        # moneda. Cand era in cheie, "credit_nevoi_personale pf nominala -" si
        # "... LEI" ieseau doua randuri pentru acelasi lucru, despartite doar de
        # faptul ca moneda n-a fost prinsa pe pagina. Se pierde distincția intre
        # varianta in lei si cea in euro a aceluiasi credit — iar acolo unde ea
        # conteaza mult (ipotecar: IRCC vs EURIBOR), linia iese cu dispersie mare
        # si se duce singura in tabelul al doilea.
        cheie = (x["produs_canonic"], _segment(x), x["tip_rata"], fel_rata(x))
        grupe[cheie][x["banca"]].append(x)
    return {k: v for k, v in grupe.items() if len(v) >= MIN_BANCI}


def _segment(x):
    """Segmentul, cu presupunerea explicita: o pagina de retail e pentru PF.

    162 din 555 de valori nu spun segmentul. A le lasa separat de "pf" rupea
    liniile in doua fara motiv. Presupunerea se aplica DOAR cand categoria paginii
    nu e "business".
    """
    if x["segment"]:
        return x["segment"]
    return "-" if x.get("categorie") == "business" else "pf"


def main():
    rate = incarca()
    mapate = [x for x in rate if x["produs_canonic"]]
    print(f"rate validate:           {len(rate)}")
    print(f"  mapate pe un produs:   {len(mapate)} "
          f"({100 * len(mapate) // len(rate)}%)")
    print(f"  excluse (promo/cashback/comision): "
          f"{sum(1 for x in rate if x['tip_rata'] in TIPURI_EXCLUSE)}")
    print(f"  indici de piață (nu se compară): "
          f"{sum(1 for x in rate if x['tip_rata'] in TIPURI_INDICI)}")
    print(f"  cu sursă învechită:    "
          f"{sum(1 for x in rate if x.get('stare') == 'SURSA_VECHE')}")

    print("\npe produs:")
    for p, n in Counter(x["produs_canonic"] for x in mapate).most_common():
        banci = len({x["banca"] for x in mapate if x["produs_canonic"] == p})
        print(f"  {n:4} valori  {banci:2} bănci  {p}")

    tabel = linii(rate)
    print(f"\nlinii comparabile (>={MIN_BANCI} bănci): {len(tabel)}")

    ies = RADACINA / "output" / "rate_unificate.json"
    ies.write_text(json.dumps(rate, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n>> {ies.relative_to(RADACINA)}")
    scrie(tabel, len(rate), len(mapate))


def scrie(tabel, total, total_mapate):
    """Tabelul de comparație a ratelor, în Markdown."""
    banci = sorted({b for pe_banca in tabel.values() for b in pe_banca})
    rand = ["libra"] + [b for b in banci if b != "libra"]
    strans = {k: v for k, v in tabel.items() if e_de_incredere(v)}
    larg = {k: v for k, v in tabel.items() if not e_de_incredere(v)}

    out = [
        "# Comparația ratelor și dobânzilor între bănci",
        "",
        "Generat de `scripts/compara_rate.py`. Perechea tabelului de comisioane",
        "([comparatie_comisioane.md](comparatie_comisioane.md)).",
        "",
        "Fiecare linie e un produs canonic, un segment de clienți, un tip de rată,",
        "**felul** ei (fixă / variabilă) și o monedă. Cifra e mediana, iar în",
        "paranteză intervalul.",
        "",
        "**Semnele din celule:**",
        "",
        "| | |",
        "|---|---|",
        "| `⚠` | cel puțin o valoare vine dintr-o pagină cu **sursă învechită**, "
        "depistată la validarea încrucișată cu BNR |",
        "| `†` | rată **derivată**: marja publicată de bancă plus indicele în "
        "vigoare. Banca nu a publicat cifra asta în forma asta. `(†)` = doar unele "
        "valori din celulă sunt derivate |",
        "| `↓` | toate valorile băncii sunt de forma „**de la** X%” — capătul de jos "
        "al unui interval, cel mai bun caz pentru cel mai bun client, nu prețul "
        "obișnuit |",
        "",
        "**Felul rătei nu e un detaliu.** O rată fixă de 5,49% și una variabilă de",
        "7,71% nu sunt același produs, iar fără axa asta tabelul le punea pe același",
        "rând — vezi secțiunea despre conversia marjelor.",
        "",
        "## Cum se citește, și ce nu e aici",
        "",
        f"**Acoperire.** Din {total} de valori extrase din web, {total_mapate} "
        f"({100 * total_mapate // total}%) s-au putut mapa pe unul din cele 18",
        "produse canonice. Restul vin din pagini care nu numesc un produs anume",
        '(„Carduri persoane fizice”, „Compare Revolut plans”).',
        "",
        "**Maparea e o judecată, nu o măsurătoare** — la fel ca la comisioane, dar",
        "aici e mai greu: pe comisioane aveam secțiunile impuse prin Legea",
        "258/2017 ca axă comună, la rate nu există nicio lege care să",
        "standardizeze ceva. Din 185 de denumiri de pagină, doar 4 sunt folosite",
        "de mai mult de o bancă. Ce salvează situația e că produsele sunt uniforme",
        'ca *concept*: „Expresso” la BRD, „Libra Way” la Libra și „creditul',
        'Econom” la Patria sunt toate credite de nevoi personale.',
        "Verificată de mână pe 20 de valori: **18 produse corecte din 20**.",
        "",
        "**Ce am scos deliberat:**",
        "",
        '- **promoțiile „rate fără dobândă”** (78 de valori) — sunt „3 rate cu 0%',
        '  dobândă” la comerciant, nu rata unui produs de creditare. Ar fi apărut',
        "  în tabel ca dobândă 0%.",
        "- **cashback-ul** — e un beneficiu, nu un cost.",
        "- **valorile indicilor de piață** (IRCC, ROBOR, EURIBOR) — sunt aceeași",
        "  cifră publicată de BNR pentru toată lumea. Diferența dintre bănci nu",
        "  măsoară oferta, măsoară cât de veche e pagina; ea e în raportul de",
        "  validare, nu aici. Marja *peste* indice, în schimb, e ofertă și rămâne.",
        "",
    ]
    for titlu, nota, grup in [
        (f"## Linii de încredere ({len(strans)})",
         f"Valorile variază de cel mult {DISPERSIE_MAX} ori între bănci.", strans),
        (f"## Linii prea eterogene ({len(larg)})",
         "Aici s-au amestecat oferte prea diferite sub același produs — de obicei"
         " pentru că pagina dă un interval larg, sau un exemplu reprezentativ"
         " alături de rata reală. Intervalul e informativ, mediana **nu**.", larg),
    ]:
        out += [titlu, "", nota, "",
                "| produs | segm. | tip rată | fel | mon. | între | intern | "
                + " | ".join(rand) + " |",
                "|" + "---|" * (7 + len(rand))]
        for (produs, seg, tip, fel), pe_banca in sorted(
                grup.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            celule = [_celula(pe_banca[b]) if b in pe_banca else "" for b in rand]
            monede = sorted({v["moneda"] for valori in pe_banca.values()
                             for v in valori if v["moneda"]})
            out.append(f"| {produs} | {seg} | {tip} | {fel} | "
                       f"{'/'.join(monede) or '-'} | "
                       f"{dispersie_intre(pe_banca):.0f}× | "
                       f"{dispersie_interna(pe_banca):.0f}× | "
                       + " | ".join(celule) + " |")
        out.append("")
    cale = RADACINA / "output" / "comparatie_rate.md"
    cale.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f">> {cale.relative_to(RADACINA)}")


if __name__ == "__main__":
    main()
