"""Alege esantionul pentru etalonul manual.

Stratificat pe tip_rata (toate tipurile reprezentate) si pe banca (maxim 3 pe
banca, ca sa nu domine libra/raiffeisen). Seminificat => reproductibil.
"""
import json
import random
from collections import defaultdict
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

random.seed(1609)

CAI = "output/rate_validate.json"
LLM = "output/necesita_llm.json"

d = json.load(open(CAI, encoding="utf-8"))

pe_tip = defaultdict(list)
for i, r in enumerate(d):
    r["_idx"] = i
    pe_tip[r["tip_rata"]].append(r)

# cate din fiecare tip: proportional, dar minim 2 din tipurile rare
CVOTE = {
    "nominala": 8, "comision_procent": 4, "marja_ircc": 4, "dae": 4,
    "cashback": 2, "marja_fixa": 3, "ircc_valoare": 3,
    "euribor_valoare": 2, "robor_valoare": 2, "marja_euribor": 2,
}

ales = []
pe_banca = defaultdict(int)
for tip, cvota in CVOTE.items():
    lista = pe_tip[tip][:]
    random.shuffle(lista)
    luate = 0
    # doua treceri: prima respecta limita de 3 pe banca, a doua completeaza
    for limita in (3, 99):
        for r in lista:
            if luate >= cvota:
                break
            if r in ales or pe_banca[r["banca"]] >= limita:
                continue
            ales.append(r)
            pe_banca[r["banca"]] += 1
            luate += 1

# toate cele SURSA_VECHE intra obligatoriu (sunt constatarea cea mai importanta)
for r in d:
    if r["stare"] == "SURSA_VECHE" and r not in ales:
        ales.append(r)

ales.sort(key=lambda r: (r["banca"], r["sursa_url"], r["tip_rata"]))

with open("output/etalon_esantion.json", "w", encoding="utf-8") as f:
    json.dump(ales, f, ensure_ascii=False, indent=2)

print(f"eșantion: {len(ales)} valori")
from collections import Counter
print("pe tip: ", Counter(r["tip_rata"] for r in ales).most_common())
print("pe banca:", Counter(r["banca"] for r in ales).most_common())
print("pagini unice:", len({r["sursa_url"] for r in ales}))
