"""Vox (pagina #/vox): o întrebare despre o valoare a unei bănci → parametrii
unei căutări în baza noastră.

Modelul doar înțelege întrebarea, nu răspunde el: întoarce un JSON cu schemă strictă (băncile,
conceptul, categoria, termenul), iar valorile vin din `observatii_curente` prin `celula()` din
server, aceeași funcție ca Sertar-ul din 2.1. Modelul nu vede nicio valoare și nu scrie nicio
cifră; spre Anthropic pleacă doar întrebarea, lista băncilor și lista conceptelor (date publice),
nimic din catalogul intern Libra. Singurul text al modelului care ajunge pe ecran e `clarificare`.

Activ NUMAI local, cu `MIP_PERMITE_VOX=1` și o cheie reală în `.env`. Rutele stau în spatele
logării AD (07.10.2026), dar istoricul conversațiilor e comun tuturor utilizatorilor, iar fiecare
întrebare costă: pe `mcc-test` rămâne oprit.
Modulul nu știe de HTTP și nici de SQL: serverul îi dă funcțiile de citire, ca la `rulari.py`.
"""

import datetime
import importlib.util
import json
import os
import re
import secrets
import threading
import unicodedata
from decimal import ROUND_HALF_UP, Decimal

RADACINA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_JURNAL = os.path.join(RADACINA, "loguri", "vox")
MAX_TOKENS = 400        # interpretarea are sub 200 de tokeni; marja e pentru `clarificare`
# SDK-ul reîncearcă singur după timeout: cu 30 s și max_retries=2, „n-a răspuns în 30 s” venea
# după până la 90 s; acum cel mult 2 × 20 s, iar mesajul spune toată așteptarea
TIMEOUT_S = 20.0
REINCERCARI = 1


def _incarca_preturi():
    # tabelul de prețuri al fluxului de comparație, un singur loc; încărcat după cale, nu prin
    # sys.path, ca modulele din extragere_produse_bancare/ să nu acopere modulele din app/ și ingest/
    spec = importlib.util.spec_from_file_location(
        "preturi", os.path.join(RADACINA, "extragere_produse_bancare", "preturi.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


preturi = _incarca_preturi()

MODEL_IMPLICIT = "claude-haiku-4-5"    # ales de Nicolae pe 06.10.2026; MIP_VOX_MODEL îl schimbă
# `npm run dev`: pagina e pe :5173; proxy-ul Vite rescrie Host-ul la server, dar Origin rămâne
# http://localhost:5173 (vezi rulari.verifica_cerere, `porturi_extra`)
PORT_VITE = 5173
LUNGIME_MAX = 500
MAX_BANCI = 3
# BCR are 1.253 de valori `transfer_credit` (baza mip, 06.10.2026): rezumatul le numără pe toate,
# dar răspunsul trimite cel mult atâtea rânduri; restul sunt în Sertar
MAX_RANDURI = 50
# PF primul: la BCR · administrare cont, 302 valori PJ, 234 PFA și 33 PF stăteau într-un singur interval,
# 0–1.200 lei (mip_merge, 07.10.2026); rândurile fără segment în sursă vin la final. `celula` din server
# acceptă la `segment` doar aceste valori, plus `nemarcat`.
ORDINE_SEGMENT = ("pf", "pfa", "imm", "pj")
TIPURI = ("cautare", "clasament", "aplicatii", "neclar", "in_afara")
CHEI = ("tip", "banci", "concept", "categorie", "termen", "produs_credit", "text_cautat", "clarificare",
        "segment", "metrica", "functie", "aspect", "prag_note")
# „cea mai ieftină variantă” cere cea mai bună valoare a fiecărei bănci, nu mediana (decizia lui
# Nicolae, 07.10.2026); mediana rămâne implicită, ca în 2.1 și Versus
METRICI = ("mediana", "cea_mai_buna")
# Aplicațiile: funcțiile din analiza aplicațiilor Android sau notele din magazine (decizia lui Nicolae, 08.10.2026)
# și recenziile (09.10.2026)
ASPECTE = ("functii", "note", "recenzii")
# Pragurile oferite ca butoane sub clasamentul notelor. Fără prag (decizia lui Nicolae, 08.10.2026), ProCredit iese
# primul în App Store cu 5,0 din 6 note (24.09.2026): sub cel mai mic prag, Vox spune asta și întreabă ce prag vrea
PRAGURI_NOTE = (100, 1000)
PRAG_AVERTIZARE = min(PRAGURI_NOTE)
# Revolut are 4.147.313 note în Google Play (06.10.2026); un prag peste atât nu mai lasă nimic de clasat
PRAG_NOTE_MAX = 100_000_000
# Istoricul conversațiilor (coloana „Conversații” din pagina Vox): fișiere pe laptop, nu în bază
ID_CONVERSATIE = re.compile(r"[0-9a-f]{16}")
TITLU_MAX = 120
CONVERSATIE_LIPSA = "Conversația nu mai există."


class Respins(Exception):
    """Cerere greșită (400): întrebare goală sau prea lungă, interpretare anterioară invalidă."""


class EroareModel(Exception):
    """Apelul la model n-a reușit (502); mesajul e pentru utilizator."""


class ConversatieLipsa(Exception):
    """Conversația cerută nu există (404): ștearsă sau un id greșit în adresă."""


def mesaj_eroare(exc):
    """Mesajul pentru utilizator, de la eroarea cea mai specifică la cea generală (retryable sau nu)."""
    import anthropic
    if isinstance(exc, anthropic.AuthenticationError):
        return "Cheia Anthropic e respinsă (401). Verifică ANTHROPIC_API_KEY din .env."
    if isinstance(exc, anthropic.RateLimitError):
        return "Prea multe cereri la Anthropic (429). Încearcă din nou peste un minut."
    if isinstance(exc, anthropic.APITimeoutError):
        return f"Modelul n-a răspuns în {int(TIMEOUT_S * (REINCERCARI + 1))} s. Încearcă din nou."
    if isinstance(exc, anthropic.APIConnectionError):
        return "Nu s-a putut ajunge la api.anthropic.com (rețea sau proxy)."
    if isinstance(exc, anthropic.APIStatusError):
        return f"API-ul Anthropic a răspuns cu eroarea {exc.status_code}."
    return f"Eroare la apelul modelului ({exc.__class__.__name__})."


def _acum():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def _gol(tip="neclar"):
    return {"tip": tip, "banci": [], "concept": None, "categorie": None, "termen": None,
            "produs_credit": None, "text_cautat": None, "clarificare": None, "segment": None, "metrica": None,
            "functie": None, "aspect": None, "prag_note": None}


def cheie_reala():
    """Pe 06.10.2026, `.env`-ul din rădăcină avea în ANTHROPIC_API_KEY un placeholder de 10
    caractere (jobul 172); cheia reală pusă atunci începe cu `sk-ant-` și are 108. Pragul de 40
    desparte orice placeholder scurt de o cheie, fără să depindă de lungimea exactă a cheilor."""
    k = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    return k.startswith("sk-ant-") and len(k) >= 40


def activ():
    return os.environ.get("MIP_PERMITE_VOX", "").strip() == "1" and cheie_reala()


def model():
    return os.environ.get("MIP_VOX_MODEL", "").strip() or MODEL_IMPLICIT


def verifica_intrebarea(intrebare):
    if not isinstance(intrebare, str) or not intrebare.strip():
        raise Respins("Scrie o întrebare.")
    intrebare = intrebare.strip()
    if len(intrebare) > LUNGIME_MAX:
        raise Respins(f"Întrebarea are peste {LUNGIME_MAX} de caractere.")
    return intrebare


def verifica_anterior(anterior):
    """Interpretarea întrebării precedente, trimisă de pagină pentru „și la BRD?” sau de un buton. Forma și
    mărimea ajung: valorile fie merg la model ca text de context (`intreaba`), fie trec prin `valideaza`
    (`continua`, butoanele), care refuză tot ce nu e în liste."""
    if anterior is None:
        return None
    if not isinstance(anterior, dict) or not set(anterior) <= set(CHEI):
        raise Respins("Interpretarea anterioară nu e validă.")
    curat = {k: anterior.get(k) for k in CHEI}
    if len(json.dumps(curat, ensure_ascii=False)) > 1000:
        raise Respins("Interpretarea anterioară nu e validă.")
    return curat


def schema(ctx):
    """Schema strictă a răspunsului: băncile și conceptele sunt `enum` generate din bază, deci API-ul
    nu acceptă un slug inexistent. Modul strict nu acceptă `maxItems`: limita de 3 bănci e în
    `valideaza`."""
    def optional(valori):
        return {"anyOf": [{"type": "string", "enum": list(valori)}, {"type": "null"}]}

    text_optional = {"anyOf": [{"type": "string"}, {"type": "null"}]}
    return {
        "type": "object",
        "properties": {
            "tip": {"type": "string", "enum": list(TIPURI)},
            "banci": {"type": "array", "items": {"type": "string", "enum": [b["slug"] for b in ctx["banci"]]}},
            "concept": optional(c["camp"] for c in ctx["concepte"]),
            "categorie": optional(ctx["categorii"]),
            "termen": optional(ctx["termene"]),
            "produs_credit": optional(ctx["produse"]),
            "text_cautat": text_optional,
            "clarificare": text_optional,
            "segment": optional(ORDINE_SEGMENT),
            "metrica": optional(METRICI),
            # o bază fără analiza Android ar fi dat `"enum": []`, pe care API-ul îl poate refuza: ar fi căzut orice
            # întrebare, nu doar cele despre aplicații
            "functie": optional(f["functie"] for f in ctx["functii"]) if ctx["functii"] else {"type": "null"},
            "aspect": optional(ASPECTE),
            "prag_note": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
        },
        "required": list(CHEI),
        "additionalProperties": False,
    }


def prompt(ctx):
    """Promptul de sistem, construit din bază. Identic între întrebări (fără dată, fără ordine
    aleatoare): cache-ul promptului cere un prefix stabil."""
    linii = [
        "Ești interpretul paginii Vox din Marketing Command Center (Libra Bank).",
        "Utilizatorul întreabă, în română sau în engleză, despre o valoare publicată de o bancă din "
        "România (un comision, o dobândă, o limită) sau compară băncile între ele pe o astfel de valoare. "
        "Poate întreba și despre aplicațiile mobile ale băncilor: funcțiile găsite în analiza aplicațiilor "
        "Android, notele din magazine (Google Play, App Store) și recenziile lor.",
        "Sarcina ta: traduci întrebarea în parametrii unei căutări în baza noastră. NU răspunzi la "
        "întrebare, nu scrii nicio cifră și nu folosești ce știi despre bănci: valorile le arată "
        "aplicația, din bază.",
        "",
        "Reguli:",
        "- tip = cautare: întrebarea cere o valoare a uneia sau mai multor bănci (cel mult 3).",
        "- tip = clasament: întrebarea compară băncile între ele pe o valoare („care bancă are cel mai "
        "mic…”, „cine dă cea mai mare dobândă…”, „clasamentul la…”, „unde stă Libra la…”). concept e "
        "obligatoriu; banci = doar băncile numite în întrebare (aplicația le evidențiază), altfel []. Se "
        "pot clasa doar conceptele din lista „Clasabile” de la final; pentru altele pune tot clasament, "
        "iar aplicația spune că nu are clasament.",
        "- Întrebările care încep cu „care bancă…”, „ce bancă…”, „which bank…” și cer o valoare (un comision, "
        "o dobândă) sunt întotdeauna clasament; cele despre aplicații („care bancă are cea mai bună "
        "aplicație?”) sunt aplicatii, iar cele despre campanii rămân in_afara. "
        "O întrebare cu „cine are cel mai…”, „cea mai ieftină variantă…” compară și ea băncile: e "
        "clasament chiar fără bancă numită, chiar dacă serviciul nu are "
        "concept sau nu-l recunoști; nu pune neclar pentru asta. Exemple: „Care bancă are cel mai mic "
        "comision la X?”, cu X fără concept → clasament, concept = null, text_cautat = X; „Unde stă Libra "
        "la …?”, „pe ce loc e Libra la …?” → clasament (nu căutare), banci = [libra].",
        "- tip = aplicatii: întrebarea e despre aplicația mobilă a unei bănci: ce funcții are („Are George "
        "RoPay?”, „Ce funcții are aplicația BRD?”, „Ce bănci au plata cu telefonul?”, „Ce are BT Pay și n-are "
        "Libra?”) sau ce notă are în magazine („Ce notă are aplicația Libra?”, „Care bancă are cea mai bună "
        "aplicație?”). banci = băncile numite sau ale aplicațiilor numite (lista „Aplicațiile” de la final: "
        "„George” → bcr), altfel []. functie = funcția din lista „Funcțiile aplicațiilor”, dacă întrebarea "
        "numește una; o funcție care nu e în listă („Apple Pay”) → functie = null și numele ei în text_cautat. "
        "aspect = note pentru notă (stelele și numărul de note) și clasamentul ei („cea mai bună aplicație” = cea mai "
        "bună notă); aspect = recenzii pentru ce scriu sau spun clienții despre o aplicație (recenzii, comentarii, "
        "păreri, plângeri), cu functie = null și text_cautat = cuvintele căutate în recenzii, doar dacă întrebarea "
        "caută ceva anume, un cuvânt sau o funcție („Se plâng clienții de logare la Libra?” → logare; "
        "„Ce spun clienții despre plata cu telefonul?” → banci = [], text_cautat = plata cu telefonul); "
        "fără bancă numită, recenziile se caută la toate aplicațiile, deci nu ceri banca. "
        "Fără note sau recenzii, aspect = functii. prag_note = numărul minim de note, doar dacă întrebarea îl cere („cu cel puțin 1.000 de "
        "note” → 1000), altfel null. La aplicatii, concept, categorie, termen, produs_credit, segment și "
        "metrica sunt null.",
        "- tip = neclar: lipsește banca (iar întrebarea nu compară băncile) sau nu se înțelege ce valoare; "
        "scrie atunci în clarificare "
        "o întrebare scurtă, în limba utilizatorului. O întrebare fără bancă și fără comparație "
        "(„Cât costă administrarea contului?”) e neclar; cu o comparație "
        "(„Unde e cea mai ieftină administrare a contului?”) e clasament. La neclar completezi totuși ce ai înțeles "
        "(banci, concept sau text_cautat): aplicația decide ce face cu ele.",
        "- tip = in_afara: orice altceva (trackere, permisiuni, campanii, sfaturi, texte de scris, întrebări "
        "generale).",
        "- concept: conceptul din lista de mai jos care corespunde valorii cerute. Dacă niciunul nu "
        "se potrivește clar, concept = null și scrii în text_cautat 1–3 cuvinte în română, așa cum ar "
        "apărea în tariful băncii (de pildă „datoria vamală”). Nu forța un concept. „Comisionul de "
        "administrare” fără alt detaliu e `administrare_cont`.",
        "- Când banca și serviciul sunt clare, tip = cautare, chiar dacă serviciul nu are concept și "
        "nu-l recunoști: aplicația caută text_cautat în tarifele băncii, iar tu nu știi ce conțin "
        "tarifele, deci nu pune neclar pentru că nu ești sigur că serviciul există.",
        "- categorie: doar la dobânzi (depozite, credite, conturi și carduri); la comisioane, null. "
        "La o dobândă, conceptul e unul din cele ale categoriei (lista „Categorii” de la final); "
        "„dobânda” fără alt detaliu e `nominala`. La un clasament de dobânzi categoria e obligatorie; "
        "dacă întrebarea n-o spune, tip = neclar, cu o clarificare scurtă (depozit, credit sau cont?).",
        "- Termenii englezești au conceptul lor, nu pe cel mai apropiat: APR / annual percentage rate "
        "= `dae` (nu `nominala`; „interest rate” e `nominala`); incoming payment / incoming transfer "
        "= `incasare` (bani primiți), outgoing transfer / payment sent = `transfer_credit` (bani trimiși).",
        "- termen și produs_credit: doar dacă întrebarea le spune.",
        "- segment: pf (persoane fizice), pfa, imm, pj (firme, companii, persoane juridice); doar dacă "
        "întrebarea îl spune, altfel null. „Firme” e pj; nu cere clarificări despre segment. „Pentru "
        "firme”, „pentru persoane fizice” nu fac întrebarea neclară: pui doar segmentul („… pentru firme "
        "la BCR?” → cautare, banci = [bcr], segment = pj).",
        "- metrica: cea_mai_buna doar dacă întrebarea cere explicit cea mai bună variantă a fiecărei bănci "
        "(„cea mai ieftină variantă”, „cel mai mic comision posibil”, „dobânda maximă”, „cea mai bună "
        "variantă”); „care bancă are cel mai mic comision…” și „cine dă cea mai mare dobândă…” compară "
        "prețul obișnuit, deci metrica = null.",
        "- Dacă primești interpretarea întrebării anterioare, întrebarea curentă o poate continua "
        "(„și la BRD?”, „dar pe 6 luni?”): păstrezi ce nu se schimbă. O bancă numită în continuare "
        "(„și la BRD?”) înlocuiește băncile anterioare, nu se adaugă la ele. O întrebare care se "
        "înțelege singură, cu banca și valoarea spuse („Cât costă administrarea contului la BCR și la "
        "BRD?”), e o întrebare nouă, nu o continuare: nu păstrezi nimic din cea anterioară, nici "
        "segmentul, termenul sau tipul de credit.",
        "- După un clasament, „și pentru firme?” rămâne clasament, cu alt segment; o bancă numită "
        "(„dar la BCR?”) face o căutare la acea bancă, pentru același concept.",
        "",
        "Băncile (slug: nume):",
    ]
    linii += [f"{b['slug']}: {b['nume']}" for b in ctx["banci"]]
    linii += ["", "Conceptele (slug · unități · categorii · câte valori · denumiri reale din tarifele băncilor):"]
    for c in ctx["concepte"]:
        exemple = " | ".join(e[:80] for e in c["exemple"])
        linii.append(f"{c['camp']} · {', '.join(c['unitati'])} · {', '.join(c['categorii'])} · {c['n']} · {exemple}")
    cl = ctx["clasabile"]
    linii += [
        "",
        "Categorii: " + "; ".join(
            f"{k} ({v}; concepte: {', '.join(ctx['concepte_categorie'].get(k, []))})"
            for k, v in ctx["categorii"].items()),
        "Termene: " + "; ".join(f"{k} ({v})" for k, v in ctx["termene"].items()),
        "Tipuri de credit: " + "; ".join(f"{k} ({v})" for k, v in ctx["produse"].items()),
        "Clasabile: comisioane (în lei): " + ", ".join(cl["comisioane"]) + "; dobânzi (cu categoria): "
        + "; ".join(f"{k} ({', '.join(v)})" for k, v in cl["dobanzi"].items()),
    ]
    linii += [
        "Funcțiile aplicațiilor (slug: titlu): "
        + ("; ".join(f"{f['functie']}: {f['titlu']}" for f in ctx["functii"]) or "(niciuna în bază)"),
        "Aplicațiile (bancă: nume): "
        + ("; ".join(f"{a['banca']}: {a['aplicatie']}" for a in ctx["aplicatii"]) or "(niciuna în bază)"),
    ]
    return "\n".join(linii)


# Fără diacritice pe ambele părți: întrebarea vine adesea scrisă fără ele, tarifele cu ele.
# Aceleași litere ca `_TEXT_CAUTARE` din server, care face același lucru în SQL.
DIACRITICE = str.maketrans("ăâîșşțţ", "aaisstt")


def cuvinte_cautare(text):
    """Cuvintele unei căutări după text: litere și cifre (fără `%` sau `_`, care în LIKE ar fi
    wildcard-uri), de cel puțin 3 caractere, fără dubluri, cel mult 5. Aici, nu în server: și
    validarea, și `celula` trebuie să știe dacă rămâne ceva de căutat.

    Fiecare cuvânt e tăiat la rădăcină (6+ litere pierd ultimele 2, 5 litere ultima): pe subșirul
    exact, „datoria vamală” nu găsea „Decontarea electronică a datoriei vamale” la BCR (0 rânduri
    din 13, mip, 06.10.2026); flexiunea românească schimbă tocmai finalul cuvântului."""
    cuvinte = []
    for c in re.findall(r"[^\W_]+", (text or "").lower().translate(DIACRITICE)):
        if len(c) < 3:
            continue
        if not c.isdigit():     # „100000” tăiat la „1000” ar potrivi orice sumă care îl conține
            c = c[:-2] if len(c) >= 6 else c[:-1] if len(c) == 5 else c
        if c not in cuvinte:
            cuvinte.append(c)
    return cuvinte[:5]


def _fara_accente(s):
    """Ca `faraDiacritice` din pagină: NFD, fără semnele combinate U+0300–U+036F, litere mici. `DIACRITICE` pliază doar
    ăâîșşțţ, iar „café” trebuie să se potrivească cu „cafe” ca în îngroșare."""
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if not "̀" <= c <= "ͯ").lower()


def potriveste_recenzia(text, cuvinte):
    """Adevărat dacă fiecare cuvânt căutat (rădăcina din `cuvinte_cautare`) e începutul unui cuvânt din recenzie. Subșirul
    nu ajunge: „lentă” (rădăcina „lent”) potrivea 13 recenzii, dintre care 12 erau „excelent” (09.10.2026).

    Aceeași regulă ca îngroșarea din pagină (cuvinte = litere și cifre, `_` desparte, accentele pliate), ca o recenzie
    arătată să aibă mereu cuvântul în bold: `\\b` ar fi tratat `_` drept literă."""
    if not cuvinte:
        return True
    norm = _fara_accente(text)
    return all(re.search(r"(?<![^\W_])" + re.escape(_fara_accente(c)), norm) for c in cuvinte)


def _text(v, maxim):
    if not isinstance(v, str):
        return None
    return v.strip()[:maxim] or None


def valideaza(brut, ctx):
    """Interpretarea curată și băncile tăiate peste limită.

    Schema strictă oprește deja la API un slug inexistent; verificarea se repetă aici fiindcă un
    model schimbat din `.env` sau un răspuns tăiat n-ar trebui să ajungă într-o interogare. Ce nu e
    din liste devine `neclar` fără clarificare: pagina arată atunci mesajul ei fix, nu textul modelului.
    """
    if not isinstance(brut, dict) or brut.get("tip") not in TIPURI:
        return _gol(), []
    # `isinstance` înaintea lui `in set`: fără el, o listă sau un obiect într-un câmp ridică TypeError (500).
    # Butoanele trimit înapoi interpretarea din pagină, deci și ce a pus acolo un client; așa devine `neclar`
    banci = brut.get("banci")
    if not isinstance(banci, list) or any(
            not isinstance(b, str) or b not in {x["slug"] for x in ctx["banci"]} for b in banci):
        return _gol(), []
    permise = {"concept": {c["camp"] for c in ctx["concepte"]}, "categorie": set(ctx["categorii"]),
               "termen": set(ctx["termene"]), "produs_credit": set(ctx["produse"]),
               "segment": set(ORDINE_SEGMENT), "metrica": set(METRICI),
               "functie": {f["functie"] for f in ctx["functii"]}, "aspect": set(ASPECTE)}
    for cheie, valori in permise.items():
        v = brut.get(cheie)
        if v is not None and (not isinstance(v, str) or v not in valori):
            return _gol(), []
    banci = list(dict.fromkeys(banci))
    curat = _gol(brut["tip"])
    curat.update({k: brut.get(k) for k in permise})
    curat["banci"] = banci[:MAX_BANCI]
    curat["text_cautat"] = _text(brut.get("text_cautat"), 80)
    if not cuvinte_cautare(curat["text_cautat"]):
        # „PO” nu are niciun cuvânt de căutat: fișa ar fi spus „nu avem valori” fără să caute
        curat["text_cautat"] = None
    curat["clarificare"] = _text(brut.get("clarificare"), 300)
    # categoria doar unde conceptul are valori: `administrare_cont` e numai sub `comision`, iar o
    # categorie din 2.2 lângă el golea fișa („BCR n-are comisionul”, deși avea 570 de valori)
    categorii = next((c["categorii"] for c in ctx["concepte"] if c["camp"] == curat["concept"]), [])
    if curat["categorie"] not in categorii:
        curat["categorie"] = None
    if curat["tip"] == "aplicatii":
        return _aplicatii_curat(curat, brut.get("prag_note")), banci[MAX_BANCI:]
    curat["functie"] = curat["aspect"] = None
    if curat["tip"] == "clasament":
        curat["clarificare"] = None
        dobanzi = ctx["clasabile"]["dobanzi"]
        if curat["concept"] in dobanzi and not curat["categorie"]:
            categorii = dobanzi[curat["concept"]]
            if len(categorii) == 1:
                curat["categorie"] = categorii[0]          # `dae` e doar la credite
            else:
                curat["tip"] = "neclar"                    # `nominala`: depozit, credit sau cont?
        elif not (curat["concept"] or curat["text_cautat"]):
            curat["tip"] = "neclar"
        return curat, banci[MAX_BANCI:]
    cu_ce = bool(curat["banci"] and (curat["concept"] or curat["text_cautat"]))
    if curat["tip"] == "cautare" and not cu_ce:
        curat["tip"] = "neclar"
    elif curat["tip"] == "neclar" and cu_ce:
        # cu bancă și valoare nu e neclar (spec); Haiku punea neclar pe servicii fără concept, cu o
        # clarificare care afirma că serviciul „nu se găsește în tarife”, fals (evaluarea, 06.10.2026)
        curat["tip"], curat["clarificare"] = "cautare", None
    return curat, banci[MAX_BANCI:]


def _aplicatii_curat(curat, prag):
    """`aplicatii` (decizia lui Nicolae, 08.10.2026): banca, funcția, aspectul și pragul; câmpurile comisioanelor
    n-au sens aici. Un prag invalid se ignoră: rafinează întrebarea, nu-i schimbă sensul."""
    for k in ("concept", "categorie", "termen", "produs_credit", "segment", "metrica", "clarificare"):
        curat[k] = None
    if curat["aspect"] == "recenzii":
        curat["functie"] = None              # la recenzii, ce se caută stă în text_cautat
        if not (curat["banci"] or curat["text_cautat"]):
            curat["aspect"] = None           # „Ce scriu clienții?”: fără aplicație și fără ce se caută
    elif curat["functie"]:
        curat["aspect"] = "functii"          # o funcție e mereu despre funcții, nu despre note
    elif curat["aspect"] != "note":
        # fără funcție, bancă sau text, „funcții” n-are la ce se referi: „Ce funcții au aplicațiile băncilor?” ajungea
        # la „„” nu e printre funcțiile analizate” (revizia finală, 08.10.2026)
        curat["aspect"] = "functii" if (curat["banci"] or curat["text_cautat"]) else None
    valid = isinstance(prag, int) and not isinstance(prag, bool) and 1 <= prag <= PRAG_NOTE_MAX
    curat["prag_note"] = prag if valid and curat["aspect"] == "note" else None
    if curat["aspect"] is None:
        curat["tip"] = "neclar"              # fără funcție, aplicație sau note: pagina arată mesajul ei fix
    return curat


def _categorie(r):
    return (r.get("cod_scenariu") or "").split("|")[0]


# „gratuit” are sens doar la comisioane: pe mip erau 21 de dobânzi neambigue de 0% (06.10.2026),
# iar „2 gratuite” lângă o dobândă la card s-ar citi ca un comision
CATEGORII_COMISION = ("comision", "comisioane")

# Moneda unei dobânzi, din coloana `valuta`: LEI 9.195, EUR 4.875, USD 458, RON 28, GBP 18, CHF 13, gol 8.559
# (mip_merge, 08.10.2026). Doar la dobânzi: la comisioane unitatea (lei / eur) e moneda prețului, iar `valuta`
# poate fi a contului („Administrarea contului (EURO): 20 Lei”). Nu se ghicește din text: gol = monedă nespusă.
MONEDE = {"LEI": "lei", "RON": "lei", "EUR": "eur", "USD": "usd", "GBP": "gbp", "CHF": "chf"}
ORDINE_MONEDA = ("lei", "eur", "usd")


def _moneda(r):
    v = (r.get("valuta") or "").strip().upper()
    return MONEDE.get(v, v.lower() or None)


def _ordine_moneda(moneda):
    # lei, euro, dolari, celelalte; monedă nespusă la final, ca rândurile fără segment
    if moneda is None:
        return len(ORDINE_MONEDA) + 1
    return ORDINE_MONEDA.index(moneda) if moneda in ORDINE_MONEDA else len(ORDINE_MONEDA)


def separa(randuri, categorii_rate):
    """Rândurile cu prețul serviciului (un comision sau o dobândă din categoriile 2.2) și celelalte: note,
    limite, cursuri, „dobândă” trecută la un comision. La Garanti · schimbarea PIN-ului, toate cele 7 valori
    neambigue erau limite la plățile contactless (100–700 lei), iar fișa le arăta drept comision (mip_merge,
    08.10.2026). Rândurile de alt tip primesc `tip_alt`, ca tabelul fișei să le eticheteze."""
    pret, alte = [], []
    for r in randuri:
        tip = _categorie(r)
        if tip in CATEGORII_COMISION or tip in categorii_rate:
            pret.append(r)
        else:
            r["tip_alt"] = tip
            alte.append(r)
    return pret, alte


def _ordine_segment(segment, primul=None):
    # segmentul cerut în întrebare („pentru firme”) vine primul; restul, în ordinea obișnuită
    if primul and segment == primul:
        return -1
    return ORDINE_SEGMENT.index(segment) if segment in ORDINE_SEGMENT else len(ORDINE_SEGMENT)


def _cheie_frecventa(frecventa):
    # Aceeași frecvență se scrie cu și fără diacritice în surse: la comisioane, „pe tranzactie” are 90 de valori
    # și „pe tranzacție” 86, „pe operatiune” 103 și „pe operațiune” 38 (mip_merge, 08.10.2026). Grupate după
    # textul brut, cardul Garanti · retragere numerar arăta două rânduri `pe tranzacție · 4`. Aceeași regulă ca
    # `faraDiacritice` din interfață.
    plat = unicodedata.normalize("NFD", frecventa)
    return "".join(c for c in plat if not "\u0300" <= c <= "\u036f").lower().strip()


def rezuma(randuri, primul=None, categorii_rate=()):
    """Pe segment, unitate și categorie: câte valori, intervalul, câte gratuite; fără cele ambigue, ca în Sertar.

    Pe categorie, nu doar pe unitate: `nominala` e și dobânda de depozit, și cea de credit, iar fără
    categorie în întrebare un singur interval le-ar amesteca (6,5% la depozit cu 9,9% la ipotecar).
    Pe segment, cu PF primul (`ORDINE_SEGMENT`); un rând fără segment în sursă are grupa lui, la final.
    La dobânzi (`categorii_rate`), și pe monedă: la Libra · depozit, 4,75% în lei, 1,95% în euro și 9 valori
    fără monedă stăteau într-un singur interval, 1,95–5,5% (mip_merge, 08.10.2026). La comisioane, o grupă cu
    mai multe frecvențe primește `frecvente`: la BCR · administrare cont PF, 16 valori lunare (0–100 lei),
    6 anuale (0–1.200) și 11 fără frecvență dădeau un singur „0 – 1.200 lei”.
    """
    grupe, pe_frecventa = {}, {}
    for r in randuri:
        v = r.get("valoare")
        if r.get("ambiguu") or v is None:
            continue
        categorie = _categorie(r)
        dobanda = categorie in categorii_rate
        cheie = (r.get("segment"), r.get("unitate") or "", categorie, _moneda(r) if dobanda else None)
        g = grupe.get(cheie)
        if g is None:
            g = grupe[cheie] = {"segment": cheie[0], "unitate": cheie[1], "categorie": categorie,
                                "n": 0, "minim": v, "maxim": v, "gratuite": 0}
            if dobanda:
                g["moneda"] = cheie[3]
        g["n"] += 1
        g["minim"] = min(g["minim"], v)
        g["maxim"] = max(g["maxim"], v)
        g["gratuite"] += int(v == 0 and categorie in CATEGORII_COMISION)
        if categorie in CATEGORII_COMISION:
            frecventa = r.get("frecventa") or None
            # se afișează prima grafie văzută: `etFrecventa` din interfață o duce oricum la aceeași etichetă
            f = pe_frecventa.setdefault(cheie, {}).setdefault(
                _cheie_frecventa(frecventa) if frecventa else None,
                {"frecventa": frecventa, "n": 0, "minim": v, "maxim": v})
            f["n"] += 1
            f["minim"] = min(f["minim"], v)
            f["maxim"] = max(f["maxim"], v)
    for cheie, frecvente in pe_frecventa.items():
        if len(frecvente) > 1:
            grupe[cheie]["frecvente"] = sorted(
                frecvente.values(), key=lambda f: (-f["n"], f["frecventa"] is None, f["frecventa"] or ""))
    # tipurile, după câte valori au în segment; în același tip, moneda înaintea mărimii grupei
    pe_tip = {}
    for g in grupe.values():
        pe_tip[(g["segment"], g["categorie"])] = pe_tip.get((g["segment"], g["categorie"]), 0) + g["n"]
    return sorted(grupe.values(), key=lambda g: (
        _ordine_segment(g["segment"], primul), -pe_tip[(g["segment"], g["categorie"])], g["categorie"],
        _ordine_moneda(g.get("moneda")), -g["n"], g["unitate"]))


def clasa(celule, sens, metrica, evidentiate, nume):
    """Băncile unui bloc, de la cel mai avantajos pentru client: crescător la comisioane și credite,
    descrescător la depozite; la egalitate, după nume. Locurile egale se împart: la administrarea
    contului PF, 7 din 14 bănci au mediana 0 lei (mip_merge, 07.10.2026), iar „Libra pe locul 4” ar fi
    fost un loc arbitrar. Serviciul e al rândului de la mediană, deci la „cea mai bună variantă” lipsește."""
    def cifra(c):
        if metrica == "cea_mai_buna":
            return c["minim"] if sens == "mic_bun" else c["maxim"]
        return c["valoare"]

    la_mediana = metrica != "cea_mai_buna"
    randuri = [{"banca": c["banca"], "valoare": cifra(c), "minim": c["minim"], "maxim": c["maxim"], "n": c["n"],
                "serviciu": c.get("serviciu") if la_mediana else None,
                "frecventa": c.get("frecventa") if la_mediana else None,
                "conditie": c.get("conditie") if la_mediana else None,
                "segment_necunoscut": c.get("segment_necunoscut") if la_mediana else None,
                "evidentiata": c["banca"] in evidentiate,
                **({"alte_monede": c["alte_monede"]} if c.get("alte_monede") else {})}
               for c in celule if cifra(c) is not None]
    semn = -1 if sens == "mare_bun" else 1
    randuri.sort(key=lambda r: (semn * r["valoare"], (nume.get(r["banca"]) or r["banca"]).lower()))
    i = 0
    while i < len(randuri):
        j = i
        while j + 1 < len(randuri) and randuri[j + 1]["valoare"] == randuri[i]["valoare"]:
            j += 1
        for r in randuri[i:j + 1]:
            r["loc"], r["loc_pana"] = i + 1, j + 1
        i = j + 1
    return randuri


VERDICTE = ("sigur", "probabil", "absent", "neconcludent")
# „sigur” = găsit în cel puțin două surse (cod, texte, fișiere web), „probabil” = într-una; „neconcludent” = aplicație
# web cu textul pe server, deci absența nu dovedește nimic (pagina Android, mobil.android_verdict_d.*)
ARE = ("sigur", "probabil")


def _nota_zecimala(nota):
    """Nota cu o zecimală, ca în magazin. `round(4.25, 1)` dă 4,2 (rotunjire la par), magazinul arată 4,3."""
    return Decimal(str(nota)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def clasa_note(randuri, evidentiate, nume, prag=None):
    """Clasamentul notelor dintr-un magazin, fără prag implicit (decizia lui Nicolae, 08.10.2026): ProCredit e pe
    locul 1 în App Store cu 5,0 din 6 note (24.09.2026), iar fișa spune asta (`putine_note`). Nota se compară
    rotunjită la o zecimală, ca în magazin: în Google Play, BRD 4,83, BCR 4,81, ING 4,79, Revolut 4,78 și UniCredit
    4,77 au toate 4,8 (06.10.2026), deci loc comun, în ordinea numelui, ca la `clasa`. Cu prag, aplicațiile cu mai
    puține note trec în `sub_prag`; cele fără notă, în `fara_nota`. Rândurile păstrează câmpurile primite."""
    def dupa_nume(r):
        return (nume.get(r["banca"]) or r["banca"]).lower()

    def rand(r, **extra):
        afisata = float(_nota_zecimala(r["nota"])) if r["nota"] is not None else None
        return {**r, "nota_afisata": afisata, "evidentiata": r["banca"] in evidentiate, **extra}

    clasate, sub, fara = [], [], []
    for r in randuri:
        if r["nota"] is None:
            fara.append(r)
        elif prag and (r["evaluari"] or 0) < prag:
            sub.append(r)
        else:
            clasate.append(r)
    clasate.sort(key=lambda r: (-_nota_zecimala(r["nota"]), dupa_nume(r)))
    rez, i = [], 0
    while i < len(clasate):
        j = i
        while j + 1 < len(clasate) and _nota_zecimala(clasate[j + 1]["nota"]) == _nota_zecimala(clasate[i]["nota"]):
            j += 1
        rez += [rand(r, loc=i + 1, loc_pana=j + 1) for r in clasate[i:j + 1]]
        i = j + 1
    return {"randuri": rez, "sub_prag": [rand(r) for r in sorted(sub, key=dupa_nume)],
            "fara_nota": [rand(r) for r in sorted(fara, key=dupa_nume)]}


def putine_note(clasamente):
    """Fără prag: câte aplicații clasate au sub PRAG_AVERTIZARE note, pe magazin, și cea mai bine clasată dintre ele,
    pe care fișa o numește când întreabă ce prag vrea utilizatorul (ProCredit, locul 1 în App Store cu 6 note,
    24.09.2026). None când nu e niciuna."""
    rez, candidati = {}, []
    for magazin in ("app_store", "play"):
        c = clasamente.get(magazin)
        if not c:
            continue
        mici = [r for r in c["randuri"] if (r["evaluari"] or 0) < PRAG_AVERTIZARE]
        rez[magazin] = len(mici)
        candidati += [(r["loc"], magazin, r) for r in mici]
    if not candidati:
        return None
    _, magazin, r = min(candidati, key=lambda x: x[0])
    return {**rez, "prag": PRAG_AVERTIZARE,
            "primul": {"magazin": magazin, "banca": r["banca"], "loc": r["loc"], "loc_pana": r["loc_pana"],
                       "evaluari": r["evaluari"]}}


def diferente(coloane):
    """Funcțiile pe care o aplicație le are („sigur” sau „probabil”), iar alta nu („absent”), pe două niveluri
    (decizia lui Nicolae, 08.10.2026): `sigur` dacă una dintre cele care o au e „sigur”, altfel `probabil`.
    „Neconcludent” nu intră în comparație. BT Pay vs Libra (mip_merge, 08.10.2026): RoPay sigură; chatul,
    marketingul și asistentul vocal, probabile."""
    cu = [c for c in coloane if not c.get("fara_aplicatie")]
    rez = []
    for f in sorted({f for c in cu for f in c["functii"]}):
        verdicte = [(c["banca"], (c["functii"].get(f) or {}).get("verdict")) for c in cu]
        au = [b for b, v in verdicte if v in ARE]
        n_au = [b for b, v in verdicte if v == "absent"]
        if au and n_au:
            nivel = "sigur" if any(v == "sigur" for _, v in verdicte) else "probabil"
            rez.append({"functie": f, "nivel": nivel, "au": au, "n_au": n_au})
    return rez


def _magazin_play(play, banca):
    p = ((play or {}).get("aplicatii") or {}).get(banca)
    if not isinstance(p, dict):
        return None
    return {"nota": p.get("nota"), "evaluari": p.get("evaluari") or 0,
            "distributie_stele": p.get("distributie_stele"), "versiune": p.get("versiune"), "url": p.get("url")}


def _magazin_app_store(r):
    if not r:
        return None
    return {"nota": r["nota"], "evaluari": r["evaluari"] or 0, "distributie_stele": r["distributie_stele"],
            "versiune": r["versiune"], "url": f"https://apps.apple.com/ro/app/id{r['app_id']}"}


def _cate_aplicatii(a):
    """Câte aplicații arată răspunsul, pentru jurnal."""
    if a["vedere"] == "functie":
        return sum(len(g["aplicatii"]) for g in a["grupuri"])
    if a["vedere"] == "aplicatii":
        return sum(not c["fara_aplicatie"] for c in a["coloane"])
    if a["vedere"] == "note":
        return len({r["banca"] for c in a["clasamente"].values() if c
                    for r in c["randuri"] + c["sub_prag"] + c["fara_nota"]})
    if a["vedere"] == "recenzii":
        return len(a["blocuri"])
    return 0


def _recenzii_raspuns(interp, date, aplicatia, nume):
    """Vederea `recenzii` (spec 2026-10-09-vox-recenzii): recenziile așa cum le-au scris clienții, pe bancă și pe magazin,
    cele mai noi întâi; cu `text_cautat`, doar cele potrivite. Fără bănci, doar băncile cu potriviri, în ordinea numelui:
    eșantioanele (cel mult 20 în Google Play, cel mult 8 alese de Apple) nu suportă un clasament."""
    cuvinte = cuvinte_cautare(interp["text_cautat"])
    play = date.get("recenzii_play")
    pe_play = (play or {}).get("aplicatii") or {}
    ios = {}
    for r in date.get("recenzii_app_store") or []:
        ios.setdefault(r["banca"], []).append({k: v for k, v in r.items() if k != "banca"})

    def magazin(lista):
        lista = sorted(lista, key=lambda r: r.get("data") or "", reverse=True)
        return {"recenzii": [r for r in lista if potriveste_recenzia(r.get("text"), cuvinte)], "din": len(lista)}

    def bloc(b):
        return {"banca": b, "aplicatie": aplicatia(b),
                "fara_aplicatie": aplicatia(b) is None and b not in pe_play and b not in ios,
                "evidentiata": b == "libra",
                "play": magazin(pe_play.get(b, [])) if play else None, "app_store": magazin(ios.get(b, []))}

    if interp["banci"]:
        blocuri, fara = [bloc(b) for b in interp["banci"]], 0
    else:
        candidate = sorted(set(pe_play) | set(ios), key=lambda b: (nume.get(b) or b).lower())
        toate = [bloc(b) for b in candidate]
        blocuri = [b for b in toate if (b["play"] or {}).get("recenzii") or b["app_store"]["recenzii"]]
        fara = len(toate) - len(blocuri)
    return {"vedere": "recenzii", "blocuri": blocuri, "cuvinte": cuvinte, "fara_potriviri": fara,
            "play_la": play["colectat_la"] if play else None}


# Butoanele de sub un răspuns (decizia lui Nicolae, 08.10.2026): continuă fără model, deci gratuit și fără
# riscul unei interpretări greșite. Eticheta română e textul turei în conversație.
BUTOANE = {"firme": "Pentru firme", "pf": "Pentru persoane fizice", "libra": "Compară cu Libra",
           "toate": "La toate băncile", "prag_100": "Cel puțin 100 de note",
           "prag_1000": "Cel puțin 1.000 de note", "fara_prag": "Fără prag"}
PRAG_BUTON = {f"prag_{p}": p for p in PRAGURI_NOTE}
NEPOTRIVIT = "Butonul nu se potrivește răspunsului."


def butoane(interp, raspunsuri, clasament, aplicatii=None):
    """Ce butoane are un răspuns. Segmentul doar la comisioane: rândurile de dobânzi n-au segment în sursă,
    deci „Pentru firme” n-ar schimba nimic."""
    if interp["tip"] == "aplicatii":
        return _butoane_aplicatii(interp, aplicatii)
    tip = interp["tip"]
    if tip == "cautare" and not interp["categorie"]:
        cu_segment = any(g.get("segment") for r in raspunsuri for g in r.get("rezumat") or [])
    elif tip == "clasament":
        cu_segment = bool(clasament and clasament.get("sursa") == "matrice")
    elif tip == "cautare":
        cu_segment = False
    else:
        return []
    rez = []
    if cu_segment and interp.get("segment") != "pj":
        rez.append("firme")
    if cu_segment and interp.get("segment") in ("pj", "pfa", "imm"):
        rez.append("pf")
    if tip == "cautare" and "libra" not in interp["banci"] and len(interp["banci"]) < MAX_BANCI:
        rez.append("libra")
    return rez


def _butoane_aplicatii(interp, aplicatii):
    """La aplicații: Libra lângă băncile numite, aceeași întrebare la toate băncile și pragul de note. Fără prag,
    pragurile apar doar când clasamentul are aplicații cu puține note (`putine_note`)."""
    if not aplicatii:
        return []
    banci, rez = interp["banci"], []
    if banci and "libra" not in banci and len(banci) < MAX_BANCI:
        rez.append("libra")
    if banci and (interp["functie"] or interp["aspect"] == "note" or (interp["aspect"] == "recenzii" and interp["text_cautat"])):
        rez.append("toate")
    if interp["aspect"] == "note":
        prag = interp.get("prag_note")
        if prag is None:
            rez += list(PRAG_BUTON) if aplicatii.get("putine_note") else []
        else:
            rez += [b for b, p in PRAG_BUTON.items() if p != prag] + ["fara_prag"]
    return rez


def din_buton(anterior, buton):
    """Interpretarea nouă după un buton, fără model. Un buton care nu se potrivește ridică `Respins`. Fiecare buton
    are ramura lui: cu `toate` și pragurile în BUTOANE, o ramură „orice altceva = Libra” ar fi adăugat Libra la un
    `toate` trimis pe o căutare."""
    if not isinstance(buton, str) or buton not in BUTOANE or anterior["tip"] not in ("cautare", "clasament", "aplicatii"):
        raise Respins(NEPOTRIVIT)
    nou = dict(anterior, clarificare=None)
    if anterior["tip"] == "aplicatii":
        return _din_buton_aplicatii(nou, buton)
    if buton in ("firme", "pf"):
        if anterior["categorie"]:
            raise Respins(NEPOTRIVIT)
        nou["segment"] = "pj" if buton == "firme" else "pf"
    elif (buton == "libra" and anterior["tip"] == "cautare" and "libra" not in anterior["banci"]
          and len(anterior["banci"]) < MAX_BANCI):
        nou["banci"] = anterior["banci"] + ["libra"]
    else:
        raise Respins(NEPOTRIVIT)
    return nou


def _din_buton_aplicatii(nou, buton):
    banci = nou["banci"]
    if buton == "libra" and banci and "libra" not in banci and len(banci) < MAX_BANCI:
        nou["banci"] = banci + ["libra"]
    elif buton == "toate" and banci and (nou["functie"] or nou["aspect"] == "note" or (nou["aspect"] == "recenzii" and nou["text_cautat"])):
        nou["banci"] = []
    elif (buton in PRAG_BUTON or buton == "fara_prag") and nou["aspect"] == "note":
        nou["prag_note"] = PRAG_BUTON.get(buton)
    else:
        raise Respins(NEPOTRIVIT)
    return nou


def _moment(data):
    """Ora unei ture, pentru ordonare: după ora reală, nu după text (la ora de iarnă „03:10+02:00” e
    după „03:30+03:00”); o dată stricată ajunge la coadă."""
    try:
        return datetime.datetime.fromisoformat(data).timestamp()
    except (TypeError, ValueError):
        return float("-inf")


class Istoric:
    """Conversațiile din Vox: câte un fișier JSONL pe conversație, în `dir` (pe laptop, nu în bază).

    Un rând pe întrebare (`{data, intrebare, raspuns}`) sau pe redenumire (`{data, titlu}`): fișierul
    doar crește, deci o scriere întreruptă strică cel mult ultimul rând, care se sare la citire. Orice
    id venit din afară trece prin `valid` înainte să devină cale, deci nu poate ieși din `dir`."""

    def __init__(self, dir):
        self.dir = dir
        self._lacat = threading.Lock()
        # id -> ((mtime_ns, mărime), rezumat): un răspuns are până la ~60 KB, iar lista se cere după
        # fiecare întrebare; un fișier neschimbat nu se recitește
        self._rezumate = {}

    @staticmethod
    def valid(id):
        return isinstance(id, str) and ID_CONVERSATIE.fullmatch(id) is not None

    @staticmethod
    def id_nou():
        return secrets.token_hex(8)

    def _cale(self, id):
        return os.path.join(self.dir, id + ".jsonl")

    def exista(self, id):
        return self.valid(id) and os.path.isfile(self._cale(id))

    def _scrie(self, id, rand):
        os.makedirs(self.dir, exist_ok=True)
        with self._lacat:
            with open(self._cale(id), "a", encoding="utf-8") as f:
                f.write(json.dumps(rand, ensure_ascii=False, default=str) + "\n")

    def adauga(self, id, intrebare, raspuns, data=None):
        if not self.valid(id):
            raise ConversatieLipsa(CONVERSATIE_LIPSA)
        self._scrie(id, {"data": data or _acum(), "intrebare": intrebare, "raspuns": raspuns})

    def citeste(self, id):
        """Conversația întreagă (`id`, `titlu`, `redenumita`, `ture`), sau None."""
        if not self.valid(id):
            return None
        try:
            # errors="replace": o scriere tăiată în mijlocul unei litere de 2 octeți („ă”) arunca
            # UnicodeDecodeError și lua cu ea toată lista; așa doar rândul acela nu mai e JSON și se sare
            with open(self._cale(id), encoding="utf-8", errors="replace") as f:
                linii = f.readlines()
        except OSError:
            return None
        ture, titlu = [], None
        for linie in linii:
            try:
                r = json.loads(linie)
            except ValueError:
                continue
            if not isinstance(r, dict):
                continue
            if isinstance(r.get("intrebare"), str):
                ture.append({"data": r.get("data"), "intrebare": r["intrebare"], "raspuns": r.get("raspuns")})
            elif "titlu" in r:
                titlu = r["titlu"] if isinstance(r["titlu"], str) and r["titlu"] else None
        if not ture:
            return None
        return {"id": id, "titlu": titlu or ture[0]["intrebare"], "redenumita": titlu is not None, "ture": ture}

    def _rezumat(self, id):
        st = os.stat(self._cale(id))
        cheie = (st.st_mtime_ns, st.st_size)
        vechi = self._rezumate.get(id)
        if vechi and vechi[0] == cheie:
            return vechi[1]
        c = self.citeste(id)
        rez = None if c is None else {
            "id": id, "titlu": c["titlu"], "redenumita": c["redenumita"], "intrebari": len(c["ture"]),
            "texte": [t["intrebare"] for t in c["ture"]],
            "inceputa": c["ture"][0]["data"], "ultima": c["ture"][-1]["data"],
            "cost_usd": sum((t["raspuns"].get("cost_usd") or 0) if isinstance(t["raspuns"], dict) else 0
                            for t in c["ture"]),
        }
        self._rezumate[id] = (cheie, rez)
        return rez

    def lista(self):
        """Rezumatele, cea cu ultima întrebare cea mai recentă prima."""
        try:
            nume = os.listdir(self.dir)
        except OSError:
            return []
        rez = []
        for n in nume:
            id = n[:-6] if n.endswith(".jsonl") else None
            if not self.valid(id):
                continue
            try:
                r = self._rezumat(id)
            except OSError:
                continue
            if r:
                rez.append(r)
        return sorted(rez, key=lambda r: _moment(r["ultima"]), reverse=True)

    def redenumeste(self, id, titlu):
        """Un rând `{data, titlu}` în plus; gol = înapoi la prima întrebare. Întoarce titlul afișat."""
        if titlu is not None and not isinstance(titlu, str):
            raise Respins("Titlul nu e valid.")
        titlu = (titlu or "").strip()
        if len(titlu) > TITLU_MAX:
            raise Respins(f"Titlul are peste {TITLU_MAX} de caractere.")
        if not self.exista(id):
            raise ConversatieLipsa(CONVERSATIE_LIPSA)
        self._scrie(id, {"data": _acum(), "titlu": titlu or None})
        c = self.citeste(id)
        return {"titlu": c["titlu"], "redenumita": c["redenumita"]}

    def sterge(self, id):
        if not self.exista(id):
            return False
        try:
            with self._lacat:
                os.remove(self._cale(id))
        except FileNotFoundError:
            return False
        self._rezumate.pop(id, None)
        return True


def _temperatura(m):
    """Aceeași interpretare la aceeași întrebare: la temperatura implicită, patru evaluări cu aceleași
    40 de întrebări au dat 36, 36, 39 și 37, cu alte greșeli de fiecare dată (07.10.2026). SDK-ul 1.x a
    scos `temperature` din `messages.create` (TypeError), deci trece prin `extra_body`; doar la Haiku 4.5,
    fiindcă Opus 4.7 și modelele mai noi întorc 400 pentru orice valoare."""
    return {"extra_body": {"temperature": 0}} if m.startswith("claude-haiku-4-5") else {}


class Vox:
    """O întrebare → interpretarea modelului → valorile din bază. Fără HTTP și fără SQL: serverul
    dă funcțiile de citire (`context`, `cauta`, `stare_banca`), ca la `rulari.Rulari`."""

    def __init__(self, context, cauta, stare_banca, client=None, dir_jurnal=DIR_JURNAL, dir_conversatii=None,
                 clasament=None, stare_banci=None, aplicatii=None):
        self._sursa_context = context
        self._cauta = cauta
        self._stare_banca = stare_banca
        # clasamentele: celulele din 2.1 / 2.2 și motivul pe toate băncile (app/server.py); fără ele,
        # orice clasament iese `neclasabil` (evaluarea interpretării nu le folosește)
        self._clasament = clasament
        self._stare_banci = stare_banci
        # aplicațiile (app/server.py, `_aplicatii_vox`); fără cititor, răspunsul are `aplicatii: null` (evaluarea)
        self._aplicatii = aplicatii
        self._client = client
        self.dir = dir_jurnal
        # lângă jurnal: în teste și la evaluare jurnalul e într-un dosar temporar, deci și conversațiile
        self.istoric = Istoric(dir_conversatii or os.path.join(dir_jurnal, "conversatii"))
        # separat de tokenul rulărilor: pagina asta are voie și de pe Vite (:5173), rulările nu
        self.token = secrets.token_urlsafe(32)
        self._lacat = threading.Lock()
        self._lacat_jurnal = threading.Lock()
        self._pregatit = None

    def stare(self):
        return {"activ": activ(), "model": model()}

    def _context(self):
        # o conexiune nouă la Postgres costă ~2 s pe Windows, iar promptul trebuie să rămână identic
        # între întrebări ca să intre în cache: se construiește o dată, la prima întrebare; după o
        # încărcare de date nouă se reface la repornirea serverului
        with self._lacat:
            if self._pregatit is None:
                ctx = self._sursa_context()
                self._pregatit = (ctx, prompt(ctx), schema(ctx))
            return self._pregatit

    def _clientul(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(timeout=TIMEOUT_S, max_retries=REINCERCARI)
        return self._client

    def _cheama(self, m, sistem, sch, intrebare, anterior):
        import anthropic
        continut = intrebare if anterior is None else (
            "Interpretarea întrebării anterioare: " + json.dumps(anterior, ensure_ascii=False)
            + "\nÎntrebarea curentă: " + intrebare)
        try:
            r = self._clientul().messages.create(
                model=m,
                max_tokens=MAX_TOKENS,
                # o oră, nu 5 minute: în conversația din 08.10.2026 (18 întrebări, 7,5 cenți), promptul s-a scris în
                # cache de 3 ori, la prima întrebare și după două pauze, de 9 și de 5 minute: 4,9 cenți. Cu ora,
                # aceeași conversație ar fi costat 5,5 cenți; documentația recomandă ora pentru întrebări la
                # 5–60 de minute una de alta
                system=[{"type": "text", "text": sistem, "cache_control": {"type": "ephemeral", "ttl": "1h"}}],
                messages=[{"role": "user", "content": continut}],
                output_config={"format": {"type": "json_schema", "schema": sch}},
                **_temperatura(m),
            )
        except anthropic.APIError as exc:
            raise EroareModel(mesaj_eroare(exc)) from None
        tokeni = preturi.aduna_usage({}, r.usage)
        tokeni.pop("apeluri", None)
        text = next((b.text for b in r.content if getattr(b, "type", None) == "text"), "")
        try:
            brut = json.loads(text)
        except ValueError:
            brut = None
        return brut, tokeni, r.stop_reason

    def _raspuns(self, banca, interp, ctx):
        text = None if interp["concept"] else interp["text_cautat"]

        def cauta(termen, produs):
            return self._cauta(banca, interp["concept"], interp["categorie"], termen, produs, text)

        termen, produs = interp["termen"], interp["produs_credit"]
        randuri, relaxate = cauta(termen, produs), []
        # termenul și tipul de credit se citesc din textul băncii, deci pot goli un răspuns: la „depozit
        # pe 12 luni” 28 din 30 de bănci n-aveau nicio valoare, deși Libra avea 11 dobânzi fără termen în
        # sursă (mip_merge, 07.10.2026). Se cade pe „termen nespecificat”, apoi și pe „credit
        # nespecificat”, nu pe niciun filtru: BCR are 6% pe 5 luni, răspuns greșit la „12 luni”
        if not randuri and termen and termen != "necunoscut":
            termen, relaxate = "necunoscut", ["termen"]
            randuri = cauta(termen, produs)
        if not randuri and produs and produs != "altele":
            produs, relaxate = "altele", relaxate + ["produs"]
            randuri = cauta(termen, produs)
        fara_filtre = None
        if not randuri:
            relaxate = []
            # nici așa: câte sunt fără niciun filtru (alt termen, alt tip de credit), ca „nu avem
            # valori” să nu se citească „banca n-are produsul”
            if interp["termen"] or interp["produs_credit"]:
                fara_filtre = len(cauta(None, None))
        # PF primele, înainte de tăierea la MAX_RANDURI: la BCR · administrare cont primele 50 de rânduri
        # (ordinea pe serviciu) erau 18 PF, 19 PFA și 13 PJ amestecate (mip_merge, 07.10.2026)
        randuri = sorted(randuri, key=lambda r: _ordine_segment(r.get("segment"), interp["segment"]))
        categorii_rate = ctx["categorii"]
        pret, alte = separa(randuri, categorii_rate)
        lipsa = None if randuri else self._stare_banca(banca)
        return {
            "banca": banca,
            "mod": "text" if text else "concept",
            "total": len(randuri),
            # căutarea după text e tăiată la MAX_RANDURI în SQL, deci totalul real poate fi mai mare
            "limitat": bool(text) and len(randuri) >= MAX_RANDURI,
            "ambigue": sum(1 for r in randuri if r.get("ambiguu")),
            # rezumatul are doar valorile cu cifră; fără acest număr, „1 valoare” stătea deasupra unui
            # tabel mai lung (589 de valori doar text, neambigue, în mip_merge, 07.10.2026)
            "fara_cifra": sum(1 for r in randuri if r.get("valoare") is None and not r.get("ambiguu")),
            "rezumat": rezuma(pret, interp["segment"], categorii_rate),
            # notele, limitele, cursurile: separat, ca să nu treacă drept prețul cerut
            "alte": rezuma(alte, interp["segment"], categorii_rate),
            "randuri": randuri[:MAX_RANDURI],
            "filtre_relaxate": relaxate,
            "stare_banca": lipsa["stare"] if lipsa else None,
            # câte surse ale băncii sunt blocate și de ce; doar când banca n-are nicio valoare
            "blocaje": {k: lipsa[k] for k in ("surse", "robots", "refuzate", "pdf")} if lipsa else None,
            "fara_filtre": fara_filtre,
        }

    def _clasament_raspuns(self, interp, ctx):
        cel = (self._clasament(interp["concept"], interp["categorie"], interp["termen"],
                               interp["produs_credit"], interp["segment"])
               if self._clasament and interp["concept"] else None)
        if not cel:
            return {"concept": interp["concept"], "text": interp["text_cautat"], "neclasabil": True}
        metrica = interp["metrica"] or "mediana"
        nume = {b["slug"]: b["nume"] for b in ctx["banci"]}
        evidentiate = {"libra", *interp["banci"]}
        blocuri = [{"tip": b["tip"], "termen": b["termen"], "produs": b["produs"],
                    "randuri": clasa(b["celule"], cel["sens"], metrica, evidentiate, nume)}
                   for b in cel["blocuri"]]
        # Libra poate lipsi din primul bloc și sta în cel „nespecificat”: pe depozitul de 12 luni e pe locul
        # 7 din 9 acolo, iar fișa spunea „Libra n-are valori aici” (mip_merge, 07.10.2026)
        libra = next(({"loc": r["loc"], "loc_pana": r["loc_pana"], "din": len(b["randuri"]), "bloc": b["tip"]}
                      for b in blocuri for r in b["randuri"] if r["banca"] == "libra"), None)
        cu_date = {r["banca"] for b in blocuri for r in b["randuri"]}
        stari = self._stare_banci() if self._stare_banci else {}
        fara_date = [{"banca": b["slug"], **(stari.get(b["slug"]) or {})}
                     for b in ctx["banci"] if b["slug"] not in cu_date]
        return {"concept": interp["concept"], "sursa": cel["sursa"], "grup": cel["grup"],
                "unitate": cel["unitate"], "sens": cel["sens"], "metrica": metrica, "segment": cel["segment"],
                "categorie": interp["categorie"], "termen": interp["termen"], "produs": interp["produs_credit"],
                "blocuri": blocuri, "libra": libra, "fara_date": fara_date}


    def _aplicatii_raspuns(self, interp, ctx):
        """Una din cele patru vederi (spec 2026-10-08-vox-aplicatii): o funcție la toate băncile, aplicațiile
        băncilor numite, notele din magazine sau o funcție care nu e analizată."""
        if not self._aplicatii:
            return None
        date = self._aplicatii(cu_recenzii=True) if interp["aspect"] == "recenzii" else self._aplicatii()
        nume = {b["slug"]: b["nume"] for b in ctx["banci"]}
        evidentiate = {"libra", *interp["banci"]}
        principale, secundare = {}, {}
        for a in date["aplicatii"]:
            if a["rol"] == "secundar":
                secundare.setdefault(a["banca"], []).append(a["aplicatie"])
            else:
                principale.setdefault(a["banca"], a)
        functii = {}
        for f in date["functii"]:
            functii.setdefault(f["package"], {})[f["functie"]] = {
                "verdict": f["verdict"], "surse": [s for s in (f["surse"] or "").split("|") if s],
                "dovada_text": f["dovada_text"] or None}
        play = date["play"]
        ios = {r["banca"]: r for r in date["app_store"]}
        cu_aplicatie = set(principale) | set(ios) | set((play or {}).get("aplicatii") or {})
        rez = {"functie": interp["functie"], "text_cautat": interp["text_cautat"],
               "analiza_la": max((a["data_analizei"] for a in principale.values() if a["data_analizei"]), default=None),
               "app_store_la": max((r["observat_la"] for r in ios.values() if r["observat_la"]), default=None),
               "play_la": play["colectat_la"] if play else None,
               "banci_fara_aplicatie": [b["slug"] for b in ctx["banci"] if b["slug"] not in cu_aplicatie]}

        def aplicatia(b):
            return (principale.get(b) or {}).get("aplicatie")

        if interp["aspect"] == "recenzii":
            return {**rez, **_recenzii_raspuns(interp, date, aplicatia, nume)}
        if interp["aspect"] == "note":
            surse = {"play": (lambda b: _magazin_play(play, b)) if play else None,
                     "app_store": lambda b: _magazin_app_store(ios.get(b))}
            clasamente = {}
            for magazin, din in surse.items():
                clasamente[magazin] = None if din is None else clasa_note(
                    [{"banca": b, "aplicatie": aplicatia(b), **m} for b in sorted(cu_aplicatie) if (m := din(b))],
                    evidentiate, nume, interp["prag_note"])
            carduri = []
            for b in interp["banci"]:
                card = {"banca": b, "aplicatie": aplicatia(b), "fara_aplicatie": b not in cu_aplicatie}
                for magazin, din in surse.items():
                    m, c = (din(b) if din else None), clasamente[magazin]
                    if m and c:
                        r = next((x for x in c["randuri"] if x["banca"] == b), None)
                        m.update(loc=r["loc"] if r else None, loc_pana=r["loc_pana"] if r else None,
                                 din=len(c["randuri"]), sub_prag=any(x["banca"] == b for x in c["sub_prag"]))
                    card[magazin] = m
                carduri.append(card)
            return {**rez, "vedere": "note", "prag": interp["prag_note"], "clasamente": clasamente,
                    "putine_note": None if interp["prag_note"] else putine_note(clasamente), "carduri": carduri}
        if interp["functie"] and not interp["banci"]:
            grupuri = {v: [] for v in VERDICTE}
            for b, a in principale.items():
                f = functii.get(a["package"], {}).get(interp["functie"])
                if f and f["verdict"] in grupuri:
                    grupuri[f["verdict"]].append({"banca": b, "aplicatie": a["aplicatie"], **f,
                                                  "evidentiata": b in evidentiate})
            return {**rez, "vedere": "functie", "grupuri": [
                {"verdict": v, "aplicatii": sorted(x, key=lambda r: (nume.get(r["banca"]) or r["banca"]).lower())}
                for v, x in grupuri.items()]}
        if not interp["banci"]:
            return {**rez, "vedere": "neanalizata", "functii": [f["functie"] for f in ctx["functii"]]}
        coloane = []
        for b in interp["banci"]:
            a = principale.get(b)
            coloane.append({"banca": b, "fara_aplicatie": a is None, "aplicatie": a["aplicatie"] if a else None,
                            "versiune_analizata": a["versiune_analizata"] if a else None,
                            "data_analizei": a["data_analizei"] if a else None,
                            "framework": a["framework"] if a else None, "secundare": secundare.get(b, []),
                            "functii": functii.get(a["package"], {}) if a else {},
                            "play": _magazin_play(play, b), "app_store": _magazin_app_store(ios.get(b))})
        return {**rez, "vedere": "aplicatii", "coloane": coloane, "diferente": diferente(coloane)}

    def intreaba(self, intrebare, anterior=None, conversatie=None):
        intrebare = verifica_intrebarea(intrebare)
        anterior = verifica_anterior(anterior)
        if conversatie is not None and not self.istoric.exista(conversatie):
            # înainte de model: o conversație ștearsă în alt tab nu se mai plătește
            raise Respins(CONVERSATIE_LIPSA)
        ctx, sistem, sch = self._context()
        m = model()
        rand = {"data": _acum(), "intrebare": intrebare, "model": m, "conversatie": conversatie}
        try:
            brut, tokeni, stop = self._cheama(m, sistem, sch, intrebare, anterior)
        except EroareModel as exc:
            rand["eroare"] = str(exc)
            self._jurnal(rand)
            raise
        if stop in ("refusal", "max_tokens"):
            interp, ignorate = _gol(), []
        else:
            interp, ignorate = valideaza(brut, ctx)
        # singurul marcaj de cache din cerere e cel de o oră, deci orice scriere e de o oră
        cost = preturi.cost(m, tokeni["intrare"], tokeni["iesire"], tokeni["citire_cache"],
                            scriere_cache_1h=tokeni["scriere_cache"])
        rand.update(interpretare=interp, stop=stop, tokeni=tokeni, cost_usd=cost)
        return self._raspunde(rand, intrebare, interp, ignorate, ctx)

    def _raspunde(self, rand, intrebare, interp, ignorate, ctx, buton=None):
        """Valorile din bază pentru o interpretare, tura salvată în conversație și rândul din jurnal: același
        drum pentru o întrebare și pentru un buton."""
        try:
            raspunsuri = [self._raspuns(b, interp, ctx) for b in interp["banci"]] if interp["tip"] == "cautare" else []
            clasament = self._clasament_raspuns(interp, ctx) if interp["tip"] == "clasament" else None
            aplicatii = self._aplicatii_raspuns(interp, ctx) if interp["tip"] == "aplicatii" else None
        except Exception as exc:
            # întrebarea sau butonul intră în jurnal și când cade baza (la o întrebare, apelul la model s-a plătit deja)
            rand["eroare"] = f"{exc.__class__.__name__}: {exc}"
            self._jurnal(rand)
            raise
        rand["randuri"] = {r["banca"]: r["total"] for r in raspunsuri}
        if clasament and clasament.get("blocuri"):
            rand["clasate"] = len(clasament["blocuri"][0]["randuri"])
        if aplicatii:
            rand["aplicatii"] = _cate_aplicatii(aplicatii)
            if aplicatii["vedere"] == "recenzii":
                rand["recenzii"] = sum(len(m["recenzii"]) for b in aplicatii["blocuri"]
                                       for m in (b["play"], b["app_store"]) if m)
        rezultat = {"interpretare": interp, "ignorate": ignorate, "raspunsuri": raspunsuri,
                    "clasament": clasament, "aplicatii": aplicatii, "model": rand["model"], "tokeni": rand["tokeni"],
                    "cost_usd": rand["cost_usd"], "butoane": butoane(interp, raspunsuri, clasament, aplicatii)}
        if buton:
            rezultat["buton"] = buton
        id = rand["conversatie"] or self.istoric.id_nou()
        try:
            self.istoric.adauga(id, intrebare, rezultat)
        except OSError:
            # disc plin sau fără drept de scriere: răspunsul se arată oricum, doar nu se păstrează
            id = None
        rand["conversatie"] = id
        self._jurnal(rand)
        return {**rezultat, "conversatie": id}

    def continua(self, anterior, buton, conversatie=None):
        """Un buton de sub un răspuns („Pentru firme”, „Compară cu Libra”): interpretarea răspunsului cu
        butonul aplicat, pe același drum ca o întrebare, fără model (cost 0, nicio interpretare greșită)."""
        anterior = verifica_anterior(anterior)
        if anterior is None:
            raise Respins("Lipsește răspunsul la care se aplică butonul.")
        if conversatie is not None and not self.istoric.exista(conversatie):
            raise Respins(CONVERSATIE_LIPSA)
        ctx, _, _ = self._context()
        interp = din_buton(valideaza(anterior, ctx)[0], buton)
        tokeni = {"intrare": 0, "iesire": 0, "citire_cache": 0, "scriere_cache": 0}
        rand = {"data": _acum(), "intrebare": BUTOANE[buton], "buton": buton, "model": None,
                "conversatie": conversatie, "interpretare": interp, "tokeni": tokeni, "cost_usd": 0.0}
        return self._raspunde(rand, BUTOANE[buton], interp, [], ctx, buton)

    def _jurnal(self, rand):
        """Un rând pe întrebare, ca să se vadă unde greșește interpretarea. Nu oprește răspunsul."""
        try:
            os.makedirs(self.dir, exist_ok=True)
            with self._lacat_jurnal:
                with open(os.path.join(self.dir, rand["data"][:7] + ".jsonl"), "a", encoding="utf-8") as f:
                    f.write(json.dumps(rand, ensure_ascii=False, default=str) + "\n")
        except OSError:
            pass
