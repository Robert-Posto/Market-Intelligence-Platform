"""
clasifica_produse.py — pentru un candidat (o pagină a băncii): e produs? ce fel?
are echivalent în catalogul Libra? (pașii 3–5)

Modelul primește doar începutul paginii (titlu + primele ~5.000 de caractere de
text curățat): ajunge ca să spună ce produs e, iar costul rămâne de cenți pe bancă.
Răspunsul trece prin două verificări deterministe, ca la valori:
  - citatul trebuie regăsit în textul paginii (targetedCrawl.citat_regasit);
  - codul Libra propus ca echivalent trebuie să existe în produse_libra.

Un produs ajunge „nou” (fără echivalent) doar cu încredere ≥ PRAG_NOU. Sub prag
merge la `de_verificat`: un „Libra nu are” fals induce mai mult în eroare decât un
produs lipsă din pagină.

Catalogul Libra se trimite fără descrieri: descrierile conțin prețurile noastre,
iar regula fluxului e că prețurile Libra nu intră în prompturile despre concurență.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

AICI = Path(__file__).parent
sys.path.insert(0, str(AICI))

from anthropic import AsyncAnthropic          # noqa: E402
from candidati_produse import Blocat, adu, fh  # noqa: E402
from targetedCrawl import citat_regasit       # noqa: E402

MODEL = os.getenv("MODEL_CLASIFICARE", "claude-haiku-4-5")
PRAG_NOU = float(os.getenv("PRAG_PRODUS_NOU", "0.7"))
CARACTERE = 5000

CATEGORII = ["conturi", "carduri", "credite", "depozite_economii", "investitii", "asigurari", "pensii",
             "leasing", "plati_digitale", "schimb_valutar", "trade_finance", "acceptare_plati", "altele"]

UNEALTA = {
    "name": "clasifica",
    "description": "Clasificarea unei pagini de pe site-ul unei bănci.",
    "input_schema": {
        "type": "object",
        "properties": {
            "e_produs": {"type": "boolean", "description":
                "true dacă pagina prezintă un produs sau un serviciu pe care clientul îl poate contracta de la "
                "bancă sau prin bancă (cont, card, credit, depozit, asigurare, investiție, serviciu de plăți sau "
                "de încasări), inclusiv o familie de produse de același tip („Asigurări de călătorie”, „Carduri "
                "de credit”). false pentru: articole și ghiduri, campanii și concursuri, pagini de suport, oferte "
                "ale partenerilor (alte firme decât banca și grupul ei) și pagini-cuprins care doar trimit spre "
                "produse de tipuri diferite."},
            "denumire_produs": {"type": "string", "description": "numele comercial, exact ca pe pagină"},
            "descriere_produs": {"type": ["string", "null"], "description":
                "o frază, din ce spune pagina: ce e și pentru cine. null dacă pagina nu spune."},
            "categorie": {"type": "string", "enum": CATEGORII},
            "segment": {"type": "string", "enum": ["PF", "PJ", "PF+PJ"],
                        "description": "PF = persoane fizice, PJ = firme / IMM / profesii liberale"},
            "citat": {"type": "string", "description":
                "fragment COPIAT LITERAL din pagină (10–40 de cuvinte) care arată ce e produsul"},
            "echivalent_libra": {"type": ["string", "null"], "description":
                "codul produsului Libra echivalent din lista dată, sau null dacă niciunul nu e același "
                "tip de produs pentru același segment"},
            "incredere": {"type": "number", "description": "0–1: cât de sigur e verdictul despre echivalent"},
        },
        "required": ["e_produs", "denumire_produs", "categorie", "segment", "citat", "echivalent_libra", "incredere"],
    },
}


def sistem(catalog: list[dict]) -> str:
    linii = "\n".join(f"  {p['cod']}: {p['denumire']} ({p['segment']}, {p['categorie_cod'] or '-'})" for p in catalog)
    return f"""Primești începutul unei pagini de pe site-ul unei bănci din România. Spune dacă pagina
prezintă un produs bancar și, dacă da, dacă Libra Internet Bank are un produs echivalent.

Catalogul Libra (cod: denumire (segment, categorie)):
{linii}

Reguli:
- Echivalent = același tip de produs pentru același segment, chiar dacă numele diferă
  („Depozitul Star” la altă bancă ↔ DEPOZIT_TERMEN). O variantă (alt pachet, altă monedă, alt
  nivel de card) e tot echivalentul produsului de bază.
- Nu e echivalent un produs doar înrudit: un cont pentru copii nu e CONT_ONLINE_PERSONAL, leasingul
  operațional nu e LEASING_FINANCIAR, o asigurare de viață nu e un credit.
- Dacă ai dubii, dă `incredere` mică; nu forța un cod și nici „null”.
- Un ton de marketing („Protejează-ți familia!”) nu face pagina să nu fie de produs: contează
  dacă descrie ceva ce clientul poate contracta.
- `citat` se copiază literal din textul primit; nu reformula.
- Completezi unealta `clasifica` o singură dată."""


async def clasifica(ai: AsyncAnthropic, c: dict, catalog: list[dict], coduri: set[str]) -> dict:
    """
    @returns candidatul completat cu `rezultat` ∈ {nou, echivalent, de_verificat, respins},
             `motiv` și `tokeni`. Blocat se propagă: banca se oprește.
    """
    out = {**c, "tokeni": {"intrare": 0, "iesire": 0, "citire_cache": 0, "scriere_cache": 0}}
    r = await adu(c["url"])                    # 401/403/429/451 -> Blocat, prins de orchestrator
    if r.status_code != 200 or "html" not in r.headers.get("content-type", "html"):
        return {**out, "rezultat": "respins", "motiv": f"HTTP {r.status_code} / {r.headers.get('content-type')}"}
    s = fh.sanitizeaza(r.text)
    text = f"{s.titlu}\n{s.text}"[:CARACTERE]
    if len(text.strip()) < 200:
        return {**out, "rezultat": "respins", "motiv": "pagină aproape goală după curățare"}

    raspuns = await ai.messages.create(
        model=MODEL, max_tokens=800,
        system=[{"type": "text", "text": sistem(catalog), "cache_control": {"type": "ephemeral"}}],
        tools=[UNEALTA], tool_choice={"type": "tool", "name": "clasifica"},
        messages=[{"role": "user", "content": f"URL: {c['url']}\n\n{text}"}])
    u = raspuns.usage
    out["tokeni"] = {"intrare": u.input_tokens, "iesire": u.output_tokens,
                     "citire_cache": getattr(u, "cache_read_input_tokens", 0) or 0,
                     "scriere_cache": getattr(u, "cache_creation_input_tokens", 0) or 0}
    v = next((b.input for b in raspuns.content if b.type == "tool_use"), None)
    if not v:
        return {**out, "rezultat": "respins", "motiv": "modelul n-a completat unealta"}
    out.update({k: v.get(k) for k in ("denumire_produs", "descriere_produs", "categorie", "segment",
                                      "citat", "echivalent_libra", "incredere")})
    if not v.get("e_produs"):
        return {**out, "rezultat": "respins", "motiv": "nu e o pagină de produs"}
    if not citat_regasit(v.get("citat") or "", text):
        # nu se aruncă: la pilotul BCR + ING, 12 pagini de produs reale (ING Salary Protect,
        # ING Gold, conturi în valută) cădeau doar pe citat; merg la verificare, nu în tabel
        return {**out, "rezultat": "de_verificat", "motiv": "e produs, dar citatul nu se regăsește în pagină"}
    cod = v.get("echivalent_libra")
    if cod and cod not in coduri:
        return {**out, "rezultat": "de_verificat", "motiv": f"cod Libra necunoscut: {cod}"}
    if cod:
        return {**out, "rezultat": "echivalent", "motiv": f"echivalent cu {cod}"}
    if float(v.get("incredere") or 0) < PRAG_NOU:
        return {**out, "rezultat": "de_verificat", "motiv": f"fără echivalent, dar încredere {v.get('incredere')}"}
    return {**out, "rezultat": "nou", "motiv": "fără echivalent în catalogul Libra"}


__all__ = ["Blocat", "CATEGORII", "MODEL", "clasifica"]
