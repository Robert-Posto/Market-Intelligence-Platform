"""Rezerva de extracție prin LLM (Anthropic): doar pe liniile pe care
parserul de dobânzi nu le-a putut citi, și doar cu cifre care apar LITERAL
în linie.

Figura 3 din artefact: „determinist întâi, LLM doar dacă nu găsește nimic".
`crawler/parser_rate.parseaza_linie` întoarce deja semnalul: `problema` e
nenul când linia are un procent pe care nu-l poate tipiza (pe etalon, 26 din
67 de valori de pe paginile dense se pierdeau).

Modelul nu aduce nimic de pe web: primește textul NOSTRU, descărcat și
sanitizat. Motivul e măsurat: pe 23.09, vechiul pas `web_fetch` salva textul
REPOVESTIT de model („Iată textul integral…"), deci o cifră putea fi rescrisă.
Încrederea e plafonată la 0,6: valorile trec prin validator și, sub prag,
prin coada de verificare umană.
"""

import json
import os
import re

import normalizeaza as N

MODEL = os.environ.get("MODEL_REZERVA", "claude-sonnet-5")
MAX_LINII = 25
SISTEM = (
    "Extragi dobânzi și costuri procentuale dintr-un text de pe site-ul unei bănci "
    "din România. Răspunzi DOAR cu JSON, fără alt text: "
    '{"valori": [{"linie": indexul liniei (de la 0), "tip_rata": '
    '"nominala|dae|marja_ircc|marja_euribor|marja_robor|comision_procent", '
    '"valoare": număr, "perioada": text sau null, "moneda": "RON|EUR|USD" sau null}]}. '
    "Nu inventa și nu calcula: fiecare valoare trebuie să apară scrisă în linia ei. "
    'Dacă nu e nimic sigur, răspunde {"valori": []}.')


def _forme(valoare):
    v = float(valoare)
    forme = {f"{v:g}", f"{v:.2f}", f"{v:.1f}"}
    return forme | {f.replace(".", ",") for f in forme}


def cifra_in_text(valoare, text):
    """Cifra apare întreagă în text (4,2 nu se potrivește în 4,25)."""
    try:
        return any(re.search(rf"(?<![\d,.]){re.escape(f)}(?![\d]|[,.]\d)", text)
                   for f in _forme(valoare))
    except (TypeError, ValueError):
        return False


def extrage(linii, banca, url, categorie, client=None, raport=None):
    linii = [l for l in linii if l.strip()][:MAX_LINII]
    if not linii:
        return []
    if client is None:
        import anthropic
        client = anthropic.Anthropic()
    numerotat = "\n".join(f"{i}: {l}" for i, l in enumerate(linii))
    r = client.messages.create(model=MODEL, max_tokens=2000, system=SISTEM,
                               messages=[{"role": "user", "content": numerotat}])
    if raport is not None:
        raport["llm_rezerva_apeluri"] += 1
        raport["llm_rezerva_tokeni_intrare"] += r.usage.input_tokens
        raport["llm_rezerva_tokeni_iesire"] += r.usage.output_tokens
    raspuns = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
    try:
        valori = json.loads(raspuns[raspuns.find("{"):raspuns.rfind("}") + 1])["valori"]
    except (ValueError, KeyError):
        if raport is not None:
            raport["llm_rezerva_raspuns_ilizibil"] += 1
        return []
    brute = []
    for v in valori:
        try:
            linie = linii[int(v.get("linie", 0))]
            valoare = float(v["valoare"])
        except (ValueError, TypeError, KeyError, IndexError):
            continue
        # Verificarea literală, pe linia EXACTĂ indicată de model.
        if not cifra_in_text(valoare, linie):
            if raport is not None:
                raport["llm_rezerva_respinse_nu_apar_in_text"] += 1
            continue
        rec = {"tip_rata": v.get("tip_rata"), "valoare": valoare, "moneda": v.get("moneda"),
               "perioada": v.get("perioada"), "text_sursa": linie,
               "sursa_url": url, "banca": banca, "categorie": categorie}
        brute.append(N.brut(
            banca=banca, sursa=url, frecventa_sursa="zilnic", concept=v.get("tip_rata"),
            tip="rata", valoare=valoare, moneda=v.get("moneda"), frecventa=v.get("perioada"),
            categorie=categorie, sectiune=categorie, perioada=v.get("perioada"),
            citat=linie, incredere=0.6, _rec=rec,
            # Cifra e verificată literal, dar TIPUL și produsul nu: pe Patria
            # (24.09) modelul a etichetat conversia valutară 1,75% drept marjă
            # ROBOR. Totul merge în coada de verificare, nu direct în comparații.
            ambiguu=True, motiv_ambiguu="extras de LLM: tipul și produsul de confirmat"))
        if raport is not None:
            raport["llm_rezerva_acceptate"] += 1
    return brute
