"""Genereaza locatii MOCK (sucursale + ATM-uri) in Bucuresti, pentru testarea hartii.

Datele NU sunt reale: coordonatele sunt plasate in zone reale din Bucuresti, cu
jitter, iar numele de banci sunt reale pentru ca filtrul sa se testeze pe ceva
recognoscibil. Fiecare rand are `sursa = 'mock'`, deci se pot sterge selectiv
cand vin datele adevarate:

    DELETE FROM locatii WHERE sursa = 'mock';

Distributia urmareste realitatea pietei, nu uniformitatea:
  - bancile cu retea mare (BCR, BRD, BT, Raiffeisen) primesc mai multe puncte
  - bancile digitale (Salt, Revolut) nu primesc ATM-uri proprii, doar zero-uri;
    e o proprietate a modelului lor, nu o lipsa de date
  - raportul ATM/sucursala e ~2:1, cum e in realitate

Seed fix (`random.seed`), deci rularea e reproductibila.
"""

import io
import random
import sys

SEED = 20260922
NR_PUNCTE = 66

# zone reale din Bucuresti, cu coordonate aproximative si sectorul
ZONE = [
    ("Piața Victoriei", 44.4520, 26.0870, "Sector 1"),
    ("Calea Victoriei", 44.4410, 26.0940, "Sector 1"),
    ("Piața Romană", 44.4470, 26.0975, "Sector 1"),
    ("Bulevardul Magheru", 44.4450, 26.0985, "Sector 1"),
    ("Aviatorilor", 44.4680, 26.0860, "Sector 1"),
    ("Floreasca", 44.4700, 26.1030, "Sector 1"),
    ("Băneasa", 44.5050, 26.0850, "Sector 1"),
    ("Pipera", 44.5100, 26.1150, "Sector 1"),
    ("Piața Unirii", 44.4270, 26.1020, "Sector 3"),
    ("Bulevardul Unirii", 44.4260, 26.1150, "Sector 3"),
    ("Calea Moșilor", 44.4380, 26.1120, "Sector 3"),
    ("Titan", 44.4180, 26.1550, "Sector 3"),
    ("Dristor", 44.4200, 26.1320, "Sector 3"),
    ("Vitan", 44.4130, 26.1230, "Sector 3"),
    ("Obor", 44.4480, 26.1230, "Sector 2"),
    ("Șoseaua Colentina", 44.4560, 26.1400, "Sector 2"),
    ("Șoseaua Pantelimon", 44.4430, 26.1480, "Sector 2"),
    ("Bulevardul Basarabia", 44.4320, 26.1620, "Sector 2"),
    ("Tei", 44.4620, 26.1180, "Sector 2"),
    ("Militari", 44.4350, 26.0180, "Sector 6"),
    ("Drumul Taberei", 44.4290, 26.0290, "Sector 6"),
    ("Crângași", 44.4500, 26.0400, "Sector 6"),
    ("Grozăvești", 44.4410, 26.0580, "Sector 6"),
    ("Rahova", 44.4080, 26.0620, "Sector 5"),
    ("Șoseaua Panduri", 44.4270, 26.0680, "Sector 5"),
    ("13 Septembrie", 44.4220, 26.0590, "Sector 5"),
    ("Berceni", 44.3880, 26.1130, "Sector 4"),
    ("Șoseaua Olteniței", 44.3950, 26.1250, "Sector 4"),
    ("Timpuri Noi", 44.4200, 26.1090, "Sector 4"),
    ("Tineretului", 44.4090, 26.1010, "Sector 4"),
]

# centre comerciale - loc tipic pentru ATM-uri, mai rar pentru sucursale
MALLURI = [
    ("AFI Cotroceni", 44.4300, 26.0540, "Sector 6"),
    ("Mega Mall", 44.4370, 26.1580, "Sector 2"),
    ("Promenada Mall", 44.4780, 26.1030, "Sector 1"),
    ("Sun Plaza", 44.3940, 26.1160, "Sector 4"),
    ("Băneasa Shopping City", 44.5090, 26.0780, "Sector 1"),
    ("Plaza România", 44.4340, 26.0150, "Sector 6"),
    ("Unirea Shopping Center", 44.4265, 26.1030, "Sector 3"),
]

# slug din `banci` -> (nume afisat, greutate retea, are ATM-uri proprii)
BANCI = [
    ("bcr",                "BCR",                12, True),
    ("brd",                "BRD",                11, True),
    ("banca-transilvania", "Banca Transilvania", 12, True),
    ("raiffeisen",         "Raiffeisen Bank",    10, True),
    ("ing",                "ING Bank",            8, True),
    ("unicredit",          "UniCredit Bank",      7, True),
    ("cec",                "CEC Bank",            6, True),
    ("garanti",            "Garanti BBVA",        4, True),
    ("libra",              "Libra Internet Bank", 3, False),   # retea mica, fara ATM propriu extins
    ("patria",             "Patria Bank",         3, True),
    ("salt",               "Salt Bank",           1, False),   # digital, fara retea proprie
]


def main():
    random.seed(SEED)
    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n")
    err = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

    pondere = []
    for slug, nume, greutate, are_atm in BANCI:
        pondere += [(slug, nume, are_atm)] * greutate

    out.write("BEGIN;\n")
    out.write("DELETE FROM locatii WHERE sursa = 'mock';\n\n")

    vazute = set()
    contor = {}
    generate = 0
    incercari = 0
    while generate < NR_PUNCTE and incercari < NR_PUNCTE * 40:
        incercari += 1
        slug, nume_banca, are_atm = random.choice(pondere)

        # ATM-urile sunt de ~2x mai multe ca sucursalele; bancile digitale n-au ATM
        tip = "atm" if (are_atm and random.random() < 0.66) else "sucursala"

        in_mall = tip == "atm" and random.random() < 0.35
        if in_mall:
            zona, lat0, lon0, sector = random.choice(MALLURI)
            nume_loc = f"{nume_banca} — ATM {zona}"
            adresa = f"{zona}, București"
        else:
            zona, lat0, lon0, sector = random.choice(ZONE)
            eticheta = "ATM" if tip == "atm" else "Agenția"
            nume_loc = f"{nume_banca} — {eticheta} {zona}"
            adresa = f"{zona} nr. {random.randint(1, 180)}, București"

        lat = round(lat0 + random.uniform(-0.006, 0.006), 6)
        lon = round(lon0 + random.uniform(-0.008, 0.008), 6)
        cheie = (slug, tip, lat, lon)
        if cheie in vazute:
            continue
        vazute.add(cheie)

        if tip == "sucursala":
            program = random.choice([
                "L-V 09:00-17:00",
                "L-V 09:00-18:00, S 10:00-13:00",
                "L-J 09:00-17:30, V 09:00-16:00",
            ])
        elif in_mall:
            program = random.choice(["program mall", "L-D 10:00-22:00"])
        else:
            program = random.choice(["non-stop", "L-D 08:00-22:00"])

        out.write(
            "INSERT INTO locatii (id_banca, tip, nume, adresa, oras, sector, lat, lon, program, sursa)\n"
            f"SELECT b.id, '{tip}', "
            f"'{nume_loc.replace(chr(39), chr(39) * 2)}', "
            f"'{adresa.replace(chr(39), chr(39) * 2)}', 'București', '{sector}', "
            f"{lat}, {lon}, '{program}', 'mock'\n"
            f"FROM banci b WHERE b.slug = '{slug}'\nON CONFLICT DO NOTHING;\n"
        )
        contor[(nume_banca, tip)] = contor.get((nume_banca, tip), 0) + 1
        generate += 1

    out.write("\nCOMMIT;\n")
    out.flush()

    err.write(f"=== {generate} locatii mock generate (seed {SEED}) ===\n")
    for (banca, tip), n in sorted(contor.items(), key=lambda kv: (-kv[1], kv[0][0])):
        err.write(f"{n:4d}  {banca:22s} {tip}\n")
    err.flush()


if __name__ == "__main__":
    main()
