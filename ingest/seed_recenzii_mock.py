"""Genereaza recenzii MOCK pentru locatiile mock, in forma Google Places.

Scrie direct in Postgres (psycopg2), nu genereaza SQL ca celelalte loadere:
aici avem nevoie de id-urile locatiilor deja inserate, iar un fisier SQL orb
nu le poate sti.

Ce imita din Places:
  - pe locatie: `rating` (media) + `nr_recenzii` (totalul declarat)
  - pe recenzie: rating 1-5, text, data, autor

Autorul: Places intoarce numele real al persoanei. Aici numele sunt fictive,
DAR se stocheaza doar ca hash cu sare - exact ce se va intampla cu cele reale.
Asa interfata si interogarile se scriu de la inceput peste forma corecta.

Distributia notelor nu e uniforma, urmareste realitatea:
  - sucursalele iau note mai mici decat ATM-urile (lumea reclama cozile la
    ghiseu, nu bancomatul care merge)
  - `nr_recenzii` declarat e mai mare decat cate recenzii se afiseaza, fiindca
    Places afiseaza maximum 5 din N

Seed fix -> reproductibil. Idempotent: sterge intai recenziile `mock`.
"""

import hashlib
import io
import os
import random
import sys

import psycopg2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402

SEED = 20260922

TEXTE = {
    "sucursala": {
        5: [
            "Personal amabil, m-au ajutat repede cu deschiderea contului.",
            "Consilieră foarte răbdătoare, a explicat tot fără să mă grăbească.",
            "Mi-au rezolvat problema cu cardul în 10 minute.",
            "Agenție curată, se stă civilizat, recomand.",
        ],
        4: [
            "Bine în general, doar că se stă la coadă la orele de vârf.",
            "Personal ok, ar ajuta un program de sâmbătă.",
            "Totul rezolvat, dar a durat mai mult decât mă așteptam.",
        ],
        3: [
            "Doar două ghișee deschise din patru.",
            "Consilierul a fost amabil, însă a durat aproape o oră.",
            "Acceptabil, nimic remarcabil.",
        ],
        2: [
            "Am așteptat 50 de minute pentru o simplă adeverință.",
            "Program afișat greșit pe site, am venit degeaba.",
            "Mi s-a spus să revin altă zi pentru o operațiune banală.",
        ],
        1: [
            "Un singur ghișeu funcțional, coadă până la ușă.",
            "Comisioanele mi-au fost explicate abia după ce am semnat.",
        ],
    },
    "atm": {
        5: [
            "Funcționează mereu, bancnote în stare bună.",
            "Rapid, fără comision pentru retrageri de la propria bancă.",
            "Accesibil non-stop, locație bună.",
            "Acceptă și depuneri, foarte util.",
        ],
        4: [
            "Merge bine, doar că uneori nu are bancnote mici.",
            "Ok, dar ecranul e greu de citit în soare.",
        ],
        3: [
            "Funcționează, însă zona nu e bine iluminată noaptea.",
            "Uneori cere mai multe încercări la citirea cardului.",
        ],
        2: [
            "A fost fără numerar de două ori când am avut nevoie.",
            "Comision mare pentru retragere cu card de la altă bancă.",
        ],
        1: [
            "Mi-a reținut cardul, a durat trei zile să îl recuperez.",
            "Deseori defect, dă eroare după introducerea PIN-ului.",
        ],
    },
}

PRENUME = ["Andrei", "Maria", "Ioana", "Mihai", "Elena", "Cristian", "Alexandra",
           "George", "Diana", "Radu", "Simona", "Vlad", "Raluca", "Bogdan",
           "Gabriela", "Ștefan", "Oana", "Cătălin", "Roxana", "Daniel"]
NUME = ["Popescu", "Ionescu", "Dumitru", "Stoica", "Marin", "Constantin", "Radu",
        "Gheorghe", "Nistor", "Munteanu", "Tudor", "Barbu", "Sandu", "Voicu"]

# ponderi de nota, pe tip: sucursalele iau note mai mici
PONDERI = {
    "sucursala": [(5, 22), (4, 26), (3, 24), (2, 18), (1, 10)],
    "atm":       [(5, 38), (4, 28), (3, 18), (2, 10), (1, 6)],
}


def nota(tip):
    perechi = PONDERI[tip]
    total = sum(p for _, p in perechi)
    x = random.uniform(0, total)
    acum = 0
    for val, p in perechi:
        acum += p
        if x <= acum:
            return val
    return perechi[-1][0]


def main():
    config.incarca()
    sare = os.environ.get("MIP_SALT")
    if not sare:
        sys.stderr.write("MIP_SALT lipseste (vezi .env.example). Opresc.\n")
        return 1

    err = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
    random.seed(SEED)
    dsn = os.environ.get("MIP_DSN", "host=localhost port=5432 dbname=mip user=mip password=mip")

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM locatii_recenzii WHERE sursa = 'mock'")
            cur.execute("SELECT id, tip FROM locatii WHERE sursa = 'mock' ORDER BY id")
            locatii = cur.fetchall()

            total_rec = 0
            fara_recenzii = 0
            for id_loc, tip in locatii:
                # 15% din locatii n-au nicio recenzie - realist, mai ales la ATM-uri
                if random.random() < 0.15:
                    cur.execute(
                        "UPDATE locatii SET rating = NULL, nr_recenzii = 0 WHERE id = %s",
                        (id_loc,),
                    )
                    fara_recenzii += 1
                    continue

                nr_afisate = random.randint(2, 5)
                note = []
                for _ in range(nr_afisate):
                    r = nota(tip)
                    text = random.choice(TEXTE[tip][r])
                    autor = f"{random.choice(PRENUME)} {random.choice(NUME)}"
                    zi = random.randint(1, 28)
                    luna = random.randint(1, 9)
                    cur.execute(
                        """INSERT INTO locatii_recenzii
                               (id_locatie, rating, text, autor_hash, postat_la, sursa)
                           VALUES (%s, %s, %s, %s, make_date(2026, %s, %s), 'mock')
                           ON CONFLICT DO NOTHING""",
                        (id_loc, r, text,
                         hashlib.sha256((sare + "|" + autor).encode("utf-8")).hexdigest()[:32],
                         luna, zi),
                    )
                    note.append(r)
                    total_rec += 1

                # totalul declarat e mai mare decat cate se afiseaza (ca la Places)
                declarat = len(note) + random.randint(0, 40 if tip == "sucursala" else 12)
                cur.execute(
                    "UPDATE locatii SET rating = %s, nr_recenzii = %s WHERE id = %s",
                    (round(sum(note) / len(note), 1), declarat, id_loc),
                )

    err.write(f"{total_rec} recenzii pentru {len(locatii) - fara_recenzii} locatii "
              f"({fara_recenzii} locatii fara recenzii, intentionat)\n")
    err.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
