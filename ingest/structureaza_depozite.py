"""
Pasul 2 al pipeline-ului de depozite: transforma textul curat din
pagini_depozite_raw.json (produs de fetch_deposit_pages.py) in produse
structurate, automat, folosind Claude cu o schema fortata (tool use).

Inlocuieste pasul de citire manuala facut anterior in conversatie -- acelasi
tip de intelegere semantica, dar repetabil, fara sa fie nevoie de mine in loop
de fiecare data cand rulezi.

Cere:
  - pachetul `anthropic` instalat (pip install anthropic)
  - variabila de mediu ANTHROPIC_API_KEY setata

Rulare:
    python structureaza_depozite.py

NOTA: acest script nu a putut fi testat live in sesiunea in care a fost
scris, pentru ca nu exista o cheie ANTHROPIC_API_KEY disponibila. Structura
lui (schema, apel API, parsare raspuns) e corecta conform documentatiei
Anthropic curente, dar merita o prima rulare supravegheata, pe 2-3 banci
(vezi argumentul --banci mai jos), inainte de rularea completa.
"""

import argparse
import json
import os
import sys
import time

import anthropic

sys.stdout.reconfigure(encoding="utf-8")

MODEL = "claude-sonnet-5"
MAX_TOKENS = 4096
MAX_TEXT_CHARS_PER_CALL = 60000  # per banca; peste asta, taiem (rar atins)
DELAY_BETWEEN_CALLS = 1.0

TOOL = {
    "name": "inregistreaza_produse_depozit",
    "description": (
        "Inregistreaza produsele de tip depozit la termen sau cont/plan de "
        "economii identificate explicit in textul furnizat, cu conditiile "
        "lor reale. Nu inventa produse sau valori care nu apar in text."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "produse": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "nume": {
                            "type": "string",
                            "description": (
                                "Numele exact al produsului, asa cum apare in text "
                                "(ex. 'Depozitul la Termen BCR', "
                                "'Contul de Economii Super Acces Plus')."
                            ),
                        },
                        "tip_client": {
                            "type": "string",
                            "enum": [
                                "persoane_fizice",
                                "persoane_juridice",
                                "profesii_liberale",
                                "nespecificat",
                            ],
                        },
                        "valute": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "Monedele in care se poate constitui, ex "
                                "['RON', 'EUR', 'USD']. Lista vida daca nu se "
                                "specifica in text."
                            ),
                        },
                        "termen": {
                            "type": ["string", "null"],
                            "description": (
                                "Termenul/termenele disponibile, ca text "
                                "(ex. '1-24 luni', '7 luni', 'nelimitat'). "
                                "Null daca nu apare in text."
                            ),
                        },
                        "dobanda": {
                            "type": ["string", "null"],
                            "description": (
                                "Dobanda/dobanzile mentionate, ca text (ex. "
                                "'6,5%/an', 'de la 4,20% la 5,40% in functie de "
                                "termen'). Null daca nu apare o valoare numerica."
                            ),
                        },
                        "suma_minima": {
                            "type": ["string", "null"],
                            "description": "Suma minima de constituire, ca text (ex. '500 RON'). Null daca nu apare.",
                        },
                        "conditii_cheie": {
                            "type": "string",
                            "description": (
                                "Conditii importante pe scurt: comisioane, "
                                "restrictii de eligibilitate, optiuni de "
                                "retragere/prelungire."
                            ),
                        },
                        "este_promotie_cu_data": {
                            "type": "boolean",
                            "description": (
                                "true daca textul mentioneaza explicit o "
                                "perioada de campanie cu date calendaristice "
                                "(semn ca poate fi deja expirata)."
                            ),
                        },
                        "sursa_url": {
                            "type": "string",
                            "description": (
                                "URL-ul exact al paginii (din marcajele "
                                "'=== URL ===' din text) de unde a fost "
                                "extras acest produs."
                            ),
                        },
                    },
                    "required": ["nume", "tip_client", "conditii_cheie", "sursa_url"],
                },
            }
        },
        "required": ["produse"],
    },
}

PROMPT_TEMPLATE = """Ai mai jos textul curat (fara meniuri/footer) al mai multor pagini de pe
site-ul bancii "{banca}", separate prin marcaje "=== URL ===".

Extrage TOATE produsele de tip depozit la termen sau cont/plan de economii
mentionate explicit, cu conditiile lor reale (valuta, termen, dobanda, suma
minima). Nu inventa si nu presupune valori care nu apar in text. Daca doua
mentiuni se refera la acelasi produs (aparut pe doua pagini diferite),
pastreaza-l o singura data, cu sursa cea mai detaliata. Ignora produsele de
credit, asigurari de viata cu componenta investitionala sau fonduri mutuale
care NU sunt depozite/conturi de economii propriu-zise -- pot fi mentionate
ca alternative in text, dar nu le inregistrezi aici.

{text}
"""


def structureaza_banca(client: anthropic.Anthropic, banca: str, pagini: list[dict]) -> list[dict]:
    bucati = [
        f"=== {p['url']} ===\nTITLU: {p.get('titlu')}\n{p['text_curat']}" for p in pagini
    ]
    text = "\n\n".join(bucati)
    if len(text) > MAX_TEXT_CHARS_PER_CALL:
        text = text[:MAX_TEXT_CHARS_PER_CALL] + "\n\n[...trunchiat, text prea lung...]"

    prompt = PROMPT_TEMPLATE.format(banca=banca, text=text)

    resp = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        tools=[TOOL],
        tool_choice={"type": "tool", "name": "inregistreaza_produse_depozit"},
        messages=[{"role": "user", "content": prompt}],
    )

    for block in resp.content:
        if block.type == "tool_use" and block.name == "inregistreaza_produse_depozit":
            return block.input.get("produse", [])
    return []


def main():
    ap = argparse.ArgumentParser(description="Structureaza automat produsele de depozit, cu Claude")
    date = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "date")
    ap.add_argument("--intrare", default=os.path.join(date, "pagini_depozite_raw.json"))
    ap.add_argument("--iesire-json", default=os.path.join(date, "depozite_structurate.json"))
    ap.add_argument("--iesire-md", default=os.path.join(date, "depozite_pe_banci_AUTO.md"))
    ap.add_argument("--banci", help="lista de nume (substring) separate prin virgula, pentru test partial")
    args = ap.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit(
            "ANTHROPIC_API_KEY nu e setat. Seteaza-l ca variabila de mediu "
            "(vezi console.anthropic.com) inainte de a rula acest script."
        )

    client = anthropic.Anthropic(api_key=api_key)

    with open(args.intrare, encoding="utf-8") as f:
        banci_raw = json.load(f)

    if args.banci:
        filtre = [b.strip().lower() for b in args.banci.split(",")]
        banci_raw = [b for b in banci_raw if any(f in b["name"].lower() for f in filtre)]
        if not banci_raw:
            sys.exit("Niciuna dintre bancile din --banci nu s-a gasit in fisierul de intrare.")

    rezultate = []
    for i, banca in enumerate(banci_raw, 1):
        nume = banca["name"]
        print(f"[{i}/{len(banci_raw)}] {nume}")

        if banca.get("status") in ("BLOCKED_ROBOTS", "ERROR"):
            rezultate.append({
                "name": nume, "url": banca["url"], "status": banca["status"],
                "eroare": banca.get("eroare"), "produse": [],
            })
            print(f"    sarit (status={banca.get('status')})")
            continue

        pagini = banca.get("pagini") or []
        if not pagini:
            rezultate.append({
                "name": nume, "url": banca["url"], "status": "OK_FARA_PAGINI_GASITE",
                "eroare": None, "produse": [],
            })
            print("    sarit (fara pagini de intrare)")
            continue

        try:
            produse = structureaza_banca(client, nume, pagini)
        except Exception as exc:
            print(f"    EROARE Claude: {exc.__class__.__name__}: {exc}")
            rezultate.append({
                "name": nume, "url": banca["url"], "status": "ERROR_STRUCTURARE",
                "eroare": f"{exc.__class__.__name__}: {exc}", "produse": [],
            })
            time.sleep(DELAY_BETWEEN_CALLS)
            continue

        print(f"    produse extrase: {len(produse)}")
        rezultate.append({
            "name": nume, "url": banca["url"], "status": "OK", "eroare": None,
            "produse": produse,
        })
        time.sleep(DELAY_BETWEEN_CALLS)

    with open(args.iesire_json, "w", encoding="utf-8") as f:
        json.dump(rezultate, f, ensure_ascii=False, indent=2)

    scrie_markdown(rezultate, args.iesire_md)
    print(f"\nDone. Vezi {args.iesire_json} si {args.iesire_md}")


def scrie_markdown(rezultate: list[dict], cale: str):
    linii = []
    linii.append("# Tipuri de depozite pe bănci din România (structurare automată, Claude)\n")
    linii.append(
        "Generat automat: text curat → Claude (schemă forțată, tool use) → "
        "tabel. Nu necesită citire manuală — rulează din nou oricând pentru "
        "date actualizate, peste rezultatul deja produs de "
        "`fetch_deposit_pages.py`. Verifică sursa la fiecare produs înainte "
        "de a-l folosi ca atare — modelul poate rata nuanțe, chiar dacă nu "
        "are voie să inventeze valori.\n"
    )
    cu_produse = sum(1 for r in rezultate if r["produse"])
    linii.append(f"**Total bănci:** {len(rezultate)} · Cu cel puțin un produs identificat: {cu_produse}\n")
    linii.append("---\n")

    for r in rezultate:
        linii.append(f"## {r['name']}\n")
        linii.append(f"- **URL:** {r['url']}")
        if r["status"] != "OK" or not r["produse"]:
            motiv = f" — {r['eroare']}" if r.get("eroare") else ""
            linii.append(f"- **Status:** {r['status']}{motiv}")
            linii.append("")
            continue
        linii.append(f"- **Produse identificate ({len(r['produse'])}):**\n")
        linii.append("| Produs | Tip client | Valute | Termen | Dobândă | Sumă minimă | Condiții |")
        linii.append("|---|---|---|---|---|---|---|")
        for p in r["produse"]:
            valute = ", ".join(p.get("valute") or [])
            promo = " ⚠️ promoție cu dată" if p.get("este_promotie_cu_data") else ""
            nume = (p.get("nume") or "").replace("|", "/")
            conditii = (p.get("conditii_cheie") or "").replace("|", "/").replace("\n", " ")
            linii.append(
                f"| [{nume}]({p.get('sursa_url', '')}) | {p.get('tip_client', '')} | {valute} | "
                f"{p.get('termen') or '—'} | {p.get('dobanda') or '—'} | "
                f"{p.get('suma_minima') or '—'} | {conditii}{promo} |"
            )
        linii.append("")

    with open(cale, "w", encoding="utf-8") as f:
        f.write("\n".join(linii))


if __name__ == "__main__":
    main()
