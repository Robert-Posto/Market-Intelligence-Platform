# „Întreabă datele”: planul de implementare

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Scop:** o pagină `#/intreaba` unde cineva scrie o întrebare despre o valoare a unei bănci și
primește valorile din baza noastră, cu citatul și documentul fiecăreia.

**Arhitectura:** `app/intreaba.py` trimite întrebarea la Claude Haiku 4.5, care întoarce doar o
interpretare (JSON cu schemă strictă: bănci, concept, categorie, termen). Serverul o validează și
caută valorile cu `celula()` (aceeași funcție ca Sertar-ul din 2.1), extinsă cu o căutare după text
pentru valorile fără concept. Pagina React arată fișa fiecărei bănci și deschide Sertar-ul
existent. Modelul nu vede nicio valoare și nu scrie nicio cifră.

**Stack:** Python 3.12+ (`app/server.py`, `anthropic` 1.8 deja în `requirements.txt`), PostgreSQL
(vederea `observatii_curente`), React 18 + Vite 6 + Ant Design 5 + Zod (`web/`, `shared/`).

**Specificația:** `docs/superpowers/specs/2026-10-06-intreaba-datele-design.md`. Citește-o
înaintea oricărui task.

## Constrângeri globale

- Fără pachete noi (pip sau npm). `anthropic` există deja.
- Codul Python trebuie să meargă pe 3.12 (proiectul), 3.13 (`mcc-test`) și 3.14 (laptopul lui Nicolae).
- Identificatorii sunt în română, fără diacritice. Textele pentru utilizator și comentariile sunt cu
  diacritice. Un comentariu spune **de ce**, cu cifra măsurată, nu ce face codul.
- Serverul nu scrie în bază. SQL doar cu parametri `%s`, niciun text din cerere interpolat.
- Modelul implicit e `claude-haiku-4-5`. La Haiku 4.5 **nu** se trimit `effort` și nici `thinking`:
  dau eroare sau nu sunt suportate.
- Orice apel real la model costă. Înainte de primul apel real (verificarea din browser, evaluarea),
  arată-i lui Nicolae estimarea și așteaptă acordul lui.
- Verificările de la `/api/rulari/*` nu se slăbesc. Testele lor (`python app/test_rulari.py`)
  trebuie să treacă după fiecare task care atinge `app/`.
- Orice text din interfață trece prin `t` / `tn` / `<T>`, ca pereche `[română, engleză]` în
  `web/src/i18n/dict/`. Datele băncilor (servicii, citate, condiții) nu se traduc. Mesajele
  românești de la server trec prin `deLaServer` și au cheie `server.intreaba.*`.
- Totul se rulează din rădăcina repo-ului. Pe Windows, consola e cp1252: scripturile și testele
  care afișează diacritice își reconfigurează `stdout` pe UTF-8 sau rulează cu
  `PYTHONIOENCODING=utf-8`.
- Commit-urile sunt în română, de forma „zonă: ce și de ce”, **fără** linii `Co-Authored-By`.
- Ramura: `intreaba-datele` (există deja, cu specificația).

## Ce poate strica, de verificat la review

Cazuri pe care le implică specificația, dar nu le spune explicit, ordonate după probabilitate.
Fiecare are un test în task-ul care deține codul.

1. **`nominala` fără categorie**: dobânzile de depozit și de credit ar ajunge în același interval.
   Rezumatul se grupează pe unitate **și** categorie (Task 1, `test_dobanzi_de_depozit_si_credit_separat`).
2. **O bancă cu mii de valori** (BCR are 1.253 de valori `transfer_credit`, `mip`, 06.10.2026):
   răspunsul trimite cel mult 50 de rânduri, dar rezumatul le numără pe toate (Task 2, `test_multe_randuri_taiate_la_50`).
3. **Text cu `%`, `_`, apostrof, diacritice sau majuscule** în căutarea după text: niciun
   wildcard nu ajunge în `LIKE`, iar diacriticele nu contează (Task 3, `test_cuvinte_cautare`).
4. **Modelul repetă o bancă sau dă peste 3**: dublurile se scot, restul se taie și se raportează
   (Task 1, `test_dubluri_si_peste_trei`).
5. **„Și la BRD?” după o clarificare sau o eroare** trebuie să continue ultima *căutare*, nu
   mesajul precedent. Pe server, `anterior` ajunge la model (Task 2, `test_anterior_ajunge_la_model`).
   Alegerea din pagină se verifică manual (Task 6, pasul de verificare 6.6).

---

### Task 1: nucleul fără rețea din `app/intreaba.py`

**Fișiere:**
- Creare: `app/intreaba.py`
- Creare: `app/test_intreaba.py`

**Interfețe:**
- Consumă: nimic.
- Produce, folosite mai departe:
  - constantele `MODEL_IMPLICIT`, `PORT_VITE` (5173), `LUNGIME_MAX` (500), `MAX_BANCI` (3),
    `MAX_RANDURI` (50), `TIPURI`, `CHEI`;
  - `class Respins(Exception)`;
  - `cheie_reala() -> bool`, `activ() -> bool`, `model() -> str`;
  - `verifica_intrebarea(x) -> str`, `verifica_anterior(x) -> dict | None`;
  - `schema(ctx) -> dict`, `prompt(ctx) -> str`;
  - `valideaza(brut, ctx) -> tuple[dict, list[str]]`, `rezuma(randuri) -> list[dict]`, `_gol(tip) -> dict`.
  - `ctx` are forma
    `{"banci": [{"slug", "nume"}], "concepte": [{"camp", "n", "unitati", "categorii", "exemple"}], "categorii": {cheie: eticheta}, "termene": {cheie: eticheta}, "produse": {cheie: eticheta}}`.

- [ ] **Pasul 1.1: scrie testele care eșuează**

Creează `app/test_intreaba.py`:

```python
"""Teste offline pentru „Întreabă datele” (app/intreaba.py și rutele din server).

Fără rețea și fără cheie: modelul e un client fals, care întoarce JSON-ul dat de test.

Rulare:  python app/test_intreaba.py
"""

import http.client
import json
import os
import sys
import tempfile
import threading
import types
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AICI)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import intreaba  # noqa: E402

CTX = {
    "banci": [{"slug": "bcr", "nume": "BCR"}, {"slug": "brd", "nume": "BRD"},
              {"slug": "ing", "nume": "ING Bank"}, {"slug": "libra", "nume": "Libra Internet Bank"}],
    "concepte": [
        {"camp": "administrare_cont", "n": 997, "unitati": ["eur", "lei"], "categorii": ["comision"],
         "exemple": ["Administrare cont curent", "Comision lunar de administrare"]},
        {"camp": "nominala", "n": 290, "unitati": ["procent"], "categorii": ["credite", "depozite"],
         "exemple": ["Depozit la termen 12 luni"]},
    ],
    "categorii": {"depozite": "Dobânzi la depozite", "credite": "Dobânzi la credite",
                  "conturi_carduri": "Conturi și carduri"},
    "termene": {"scurt": "1–3 luni", "6": "4–6 luni", "12": "7–12 luni", "lung": "peste 12 luni",
                "necunoscut": "termen nespecificat"},
    "produse": {"ipotecar": "Ipotecar / imobiliar", "nevoi_personale": "Nevoi personale",
                "card": "Card de credit / overdraft", "rate_magazin": "Rate fără dobândă în magazine",
                "altele": "Nespecificat în sursă"},
}


def interp(**k):
    baza = {"tip": "cautare", "banci": ["bcr"], "concept": "administrare_cont", "categorie": None,
            "termen": None, "produs_credit": None, "text_cautat": None, "clarificare": None}
    baza.update(k)
    return baza


def rand(valoare, unitate="lei", scenariu="comision|x", ambiguu=False):
    return {"valoare": valoare, "unitate": unitate, "cod_scenariu": scenariu, "ambiguu": ambiguu}


class Configurare(unittest.TestCase):
    def setUp(self):
        self.vechi = {k: os.environ.get(k)
                      for k in ("MIP_PERMITE_INTREBARI", "ANTHROPIC_API_KEY", "MIP_INTREABA_MODEL")}

    def tearDown(self):
        for k, v in self.vechi.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_activ_cere_variabila_si_cheie_reala(self):
        os.environ["MIP_PERMITE_INTREBARI"] = "1"
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-" + "x" * 90
        self.assertTrue(intreaba.activ())
        for cheie in ("", "placehold1", "sk-ant-...", "sk-ant-scurt"):
            os.environ["ANTHROPIC_API_KEY"] = cheie
            self.assertFalse(intreaba.activ(), cheie)
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-" + "x" * 90
        os.environ["MIP_PERMITE_INTREBARI"] = "0"
        self.assertFalse(intreaba.activ())

    def test_model_implicit_haiku(self):
        os.environ.pop("MIP_INTREABA_MODEL", None)
        self.assertEqual(intreaba.model(), "claude-haiku-4-5")
        os.environ["MIP_INTREABA_MODEL"] = "claude-sonnet-5-5"
        self.assertEqual(intreaba.model(), "claude-sonnet-5-5")


class Intrare(unittest.TestCase):
    def test_intrebarea(self):
        self.assertEqual(intreaba.verifica_intrebarea("  Cât costă?  "), "Cât costă?")
        self.assertEqual(len(intreaba.verifica_intrebarea("a" * 500)), 500)
        for rau in ("", "   ", None, 3, ["x"], "a" * 501):
            with self.assertRaises(intreaba.Respins):
                intreaba.verifica_intrebarea(rau)

    def test_anterior(self):
        self.assertIsNone(intreaba.verifica_anterior(None))
        self.assertEqual(intreaba.verifica_anterior(interp())["concept"], "administrare_cont")
        for rau in ("text", ["x"], {"tip": "cautare", "altceva": 1}, interp(text_cautat="x" * 2000)):
            with self.assertRaises(intreaba.Respins):
                intreaba.verifica_anterior(rau)


class Schema(unittest.TestCase):
    def test_enum_din_liste(self):
        s = intreaba.schema(CTX)
        p = s["properties"]
        self.assertEqual(p["banci"]["items"]["enum"], ["bcr", "brd", "ing", "libra"])
        self.assertEqual(p["concept"]["anyOf"][0]["enum"], ["administrare_cont", "nominala"])
        self.assertEqual(p["termen"]["anyOf"][0]["enum"], list(CTX["termene"]))
        self.assertEqual(sorted(s["required"]), sorted(intreaba.CHEI))
        self.assertIs(s["additionalProperties"], False)

    def test_prompt_contine_listele_si_regula(self):
        text = intreaba.prompt(CTX)
        self.assertIn("ing: ING Bank", text)
        self.assertIn("administrare_cont · eur, lei · comision · 997 · Administrare cont curent", text)
        self.assertIn("NU răspunzi", text)
        # identic la fiecare apel: cache-ul promptului cere un prefix stabil
        self.assertEqual(text, intreaba.prompt(CTX))


class Validare(unittest.TestCase):
    def test_bun(self):
        curat, ignorate = intreaba.valideaza(interp(banci=["bcr", "brd"]), CTX)
        self.assertEqual((curat["tip"], curat["banci"], ignorate), ("cautare", ["bcr", "brd"], []))

    def test_dubluri_si_peste_trei(self):
        curat, ignorate = intreaba.valideaza(interp(banci=["bcr", "bcr", "brd", "ing", "libra"]), CTX)
        self.assertEqual(curat["banci"], ["bcr", "brd", "ing"])
        self.assertEqual(ignorate, ["libra"])

    def test_slug_sau_enum_inexistent(self):
        for rau in (interp(banci=["nu-exista"]), interp(concept="inventat"), interp(categorie="comision"),
                    interp(termen="24"), interp(produs_credit="leasing"), interp(tip="altul"), None, "x"):
            curat, _ = intreaba.valideaza(rau, CTX)
            self.assertEqual(curat["tip"], "neclar", rau)
            self.assertIsNone(curat["clarificare"], rau)
            self.assertEqual(curat["banci"], [], rau)

    def test_cautare_fara_banca_sau_fara_ce(self):
        self.assertEqual(intreaba.valideaza(interp(banci=[]), CTX)[0]["tip"], "neclar")
        self.assertEqual(intreaba.valideaza(interp(concept=None, text_cautat=None), CTX)[0]["tip"], "neclar")
        self.assertEqual(intreaba.valideaza(interp(concept=None, text_cautat="   "), CTX)[0]["tip"], "neclar")
        curat, _ = intreaba.valideaza(interp(concept=None, text_cautat="  datoria vamală "), CTX)
        self.assertEqual((curat["tip"], curat["text_cautat"]), ("cautare", "datoria vamală"))

    def test_clarificare_pastrata(self):
        curat, _ = intreaba.valideaza(
            interp(tip="neclar", banci=[], concept=None, clarificare="La ce bancă?"), CTX)
        self.assertEqual(curat["clarificare"], "La ce bancă?")


class Rezumat(unittest.TestCase):
    def test_pe_unitate_fara_ambigue(self):
        r = intreaba.rezuma([rand(0), rand(5), rand(15), rand(999, ambiguu=True), rand(2, "eur"), rand(None)])
        self.assertEqual(r[0], {"unitate": "lei", "categorie": "comision", "n": 3,
                                "minim": 0, "maxim": 15, "gratuite": 1})
        self.assertEqual(r[1]["unitate"], "eur")
        self.assertEqual(len(r), 2)

    def test_dobanzi_de_depozit_si_credit_separat(self):
        """`nominala` fără categorie: dobânzile de depozit și de credit nu ajung în același interval."""
        r = intreaba.rezuma([rand(6.5, "procent", "depozite|12"), rand(9.9, "procent", "credite|ipotecar")])
        self.assertEqual({(x["categorie"], x["maxim"]) for x in r}, {("depozite", 6.5), ("credite", 9.9)})


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

- [ ] **Pasul 1.2: rulează testele, să vezi că eșuează**

Rulează: `python app/test_intreaba.py`
Aștepți: `ModuleNotFoundError: No module named 'intreaba'`.

- [ ] **Pasul 1.3: scrie modulul**

Creează `app/intreaba.py`:

```python
"""„Întreabă datele” (pagina #/intreaba): o întrebare despre o valoare a unei bănci → parametrii
unei căutări în baza noastră.

Modelul doar înțelege întrebarea, nu răspunde el: întoarce un JSON cu schemă strictă (băncile,
conceptul, categoria, termenul), iar valorile vin din `observatii_curente` prin `celula()` din
server, aceeași funcție ca Sertar-ul din 2.1. Modelul nu vede nicio valoare și nu scrie nicio
cifră; spre Anthropic pleacă doar întrebarea, lista băncilor și lista conceptelor (date publice),
nimic din catalogul intern Libra. Singurul text al modelului care ajunge pe ecran e `clarificare`.

Activ NUMAI local, cu `MIP_PERMITE_INTREBARI=1` și o cheie reală în `.env`: `mcc-test` n-are
autentificare (06.10.2026), iar cheia ar fi folosibilă de oricine din rețeaua internă.
Modulul nu știe de HTTP și nici de SQL: serverul îi dă funcțiile de citire, ca la `rulari.py`.
"""

import json
import os

MODEL_IMPLICIT = "claude-haiku-4-5"    # ales de Nicolae pe 06.10.2026; MIP_INTREABA_MODEL îl schimbă
# `npm run dev`: proxy-ul Vite (fără changeOrigin) păstrează Host-ul paginii, localhost:5173
PORT_VITE = 5173
LUNGIME_MAX = 500
MAX_BANCI = 3
# BCR are 1.253 de valori `transfer_credit` (baza mip, 06.10.2026): rezumatul le numără pe toate,
# dar răspunsul trimite cel mult atâtea rânduri; restul sunt în Sertar
MAX_RANDURI = 50
TIPURI = ("cautare", "neclar", "in_afara")
CHEI = ("tip", "banci", "concept", "categorie", "termen", "produs_credit", "text_cautat", "clarificare")


class Respins(Exception):
    """Cerere greșită (400): întrebare goală sau prea lungă, interpretare anterioară invalidă."""


def _gol(tip="neclar"):
    return {"tip": tip, "banci": [], "concept": None, "categorie": None, "termen": None,
            "produs_credit": None, "text_cautat": None, "clarificare": None}


def cheie_reala():
    """Pe 06.10.2026, `.env`-ul din rădăcină avea în ANTHROPIC_API_KEY un placeholder de 10
    caractere (jobul 172); o cheie reală începe cu `sk-ant-` și are peste 100 de caractere."""
    k = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    return k.startswith("sk-ant-") and len(k) >= 40


def activ():
    return os.environ.get("MIP_PERMITE_INTREBARI", "").strip() == "1" and cheie_reala()


def model():
    return os.environ.get("MIP_INTREABA_MODEL", "").strip() or MODEL_IMPLICIT


def verifica_intrebarea(intrebare):
    if not isinstance(intrebare, str) or not intrebare.strip():
        raise Respins("Scrie o întrebare.")
    intrebare = intrebare.strip()
    if len(intrebare) > LUNGIME_MAX:
        raise Respins(f"Întrebarea are peste {LUNGIME_MAX} de caractere.")
    return intrebare


def verifica_anterior(anterior):
    """Interpretarea întrebării precedente, trimisă de pagină pentru „și la BRD?”. Ajunge la model
    doar ca text de context, deci se verifică forma și mărimea, nu și listele."""
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
        },
        "required": list(CHEI),
        "additionalProperties": False,
    }


def prompt(ctx):
    """Promptul de sistem, construit din bază. Identic între întrebări (fără dată, fără ordine
    aleatoare): cache-ul promptului cere un prefix stabil."""
    linii = [
        "Ești interpretul paginii „Întreabă datele” din Marketing Command Center (Libra Bank).",
        "Utilizatorul întreabă, în română sau în engleză, despre o valoare publicată de o bancă din "
        "România: un comision, o dobândă, o limită.",
        "Sarcina ta: traduci întrebarea în parametrii unei căutări în baza noastră. NU răspunzi la "
        "întrebare, nu scrii nicio cifră și nu folosești ce știi despre bănci: valorile le arată "
        "aplicația, din bază.",
        "",
        "Reguli:",
        "- tip = cautare: întrebarea cere o valoare a uneia sau mai multor bănci (cel mult 3).",
        "- tip = neclar: lipsește banca sau nu se înțelege ce valoare; scrie atunci în clarificare "
        "o întrebare scurtă, în limba utilizatorului.",
        "- tip = in_afara: orice altceva (clasamente de tipul „cine are cel mai mic…”, aplicații, "
        "recenzii, campanii, sfaturi, texte de scris, întrebări generale).",
        "- concept: conceptul din lista de mai jos care corespunde valorii cerute. Dacă niciunul nu "
        "se potrivește clar, concept = null și scrii în text_cautat 1–3 cuvinte în română, așa cum ar "
        "apărea în tariful băncii (de pildă „datoria vamală”). Nu forța un concept.",
        "- categorie: doar la dobânzi (depozite, credite, conturi și carduri); la comisioane, null.",
        "- termen și produs_credit: doar dacă întrebarea le spune.",
        "- Dacă primești interpretarea întrebării anterioare, întrebarea curentă o poate continua "
        "(„și la BRD?”, „dar pe 6 luni?”): păstrezi ce nu se schimbă.",
        "",
        "Băncile (slug: nume):",
    ]
    linii += [f"{b['slug']}: {b['nume']}" for b in ctx["banci"]]
    linii += ["", "Conceptele (slug · unități · categorii · câte valori · denumiri reale din tarifele băncilor):"]
    for c in ctx["concepte"]:
        exemple = " | ".join(e[:80] for e in c["exemple"])
        linii.append(f"{c['camp']} · {', '.join(c['unitati'])} · {', '.join(c['categorii'])} · {c['n']} · {exemple}")
    linii += [
        "",
        "Categorii: " + "; ".join(f"{k} ({v})" for k, v in ctx["categorii"].items()),
        "Termene: " + "; ".join(f"{k} ({v})" for k, v in ctx["termene"].items()),
        "Tipuri de credit: " + "; ".join(f"{k} ({v})" for k, v in ctx["produse"].items()),
    ]
    return "\n".join(linii)


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
    banci = brut.get("banci")
    if not isinstance(banci, list) or any(b not in {x["slug"] for x in ctx["banci"]} for b in banci):
        return _gol(), []
    permise = {"concept": {c["camp"] for c in ctx["concepte"]}, "categorie": set(ctx["categorii"]),
               "termen": set(ctx["termene"]), "produs_credit": set(ctx["produse"])}
    for cheie, valori in permise.items():
        if brut.get(cheie) is not None and brut.get(cheie) not in valori:
            return _gol(), []
    banci = list(dict.fromkeys(banci))
    curat = _gol(brut["tip"])
    curat.update({k: brut.get(k) for k in permise})
    curat["banci"] = banci[:MAX_BANCI]
    curat["text_cautat"] = _text(brut.get("text_cautat"), 80)
    curat["clarificare"] = _text(brut.get("clarificare"), 300)
    if curat["tip"] == "cautare" and not (curat["banci"] and (curat["concept"] or curat["text_cautat"])):
        curat["tip"] = "neclar"
    return curat, banci[MAX_BANCI:]


def _categorie(r):
    return (r.get("cod_scenariu") or "").split("|")[0]


def rezuma(randuri):
    """Pe unitate și categorie: câte valori, intervalul, câte gratuite; fără cele ambigue, ca în Sertar.

    Pe categorie, nu doar pe unitate: `nominala` e și dobânda de depozit, și cea de credit, iar fără
    categorie în întrebare un singur interval le-ar amesteca (6,5% la depozit cu 9,9% la ipotecar).
    """
    grupe = {}
    for r in randuri:
        v = r.get("valoare")
        if r.get("ambiguu") or v is None:
            continue
        cheie = (r.get("unitate") or "", _categorie(r))
        g = grupe.setdefault(cheie, {"unitate": cheie[0], "categorie": cheie[1], "n": 0,
                                     "minim": v, "maxim": v, "gratuite": 0})
        g["n"] += 1
        g["minim"] = min(g["minim"], v)
        g["maxim"] = max(g["maxim"], v)
        g["gratuite"] += int(v == 0)
    return sorted(grupe.values(), key=lambda g: (-g["n"], g["categorie"], g["unitate"]))
```

- [ ] **Pasul 1.4: rulează testele, să vezi că trec**

Rulează: `python app/test_intreaba.py`
Aștepți: `Ran 13 tests` … `OK`.

- [ ] **Pasul 1.5: commit**

```bash
git add app/intreaba.py app/test_intreaba.py
git commit -m "app: nucleul paginii „Întreabă datele” (schema strictă din bază, validarea, rezumatul pe categorie)"
```

---

### Task 2: apelul la model, costul și jurnalul

**Fișiere:**
- Modificare: `app/intreaba.py` (importuri, `EroareModel`, `mesaj_eroare`, `class Intrebari`)
- Modificare: `extragere_produse_bancare/preturi.py` (dicționarul `PRETURI`)
- Modificare: `app/test_intreaba.py` (clasele `ClientFals`, `Intrebari`, `Preturi`)
- Modificare: `.gitignore`, `.env.example`

**Interfețe:**
- Consumă (din Task 1): `verifica_intrebarea`, `verifica_anterior`, `prompt`, `schema`, `valideaza`,
  `rezuma`, `_gol`, `model`, `activ`, `MAX_RANDURI`.
- Produce:
  - `class EroareModel(Exception)`; mesajul e text românesc pentru utilizator;
  - `mesaj_eroare(exc) -> str`;
  - `class Intrebari(context, cauta, stare_banca, client=None, dir_jurnal=DIR_JURNAL)` cu:
    - atributele `token: str` și `_client`;
    - metodele `stare() -> {"activ", "model"}` și `intreaba(intrebare, anterior=None) -> dict`.
  - Semnăturile funcțiilor injectate:
    - `context() -> ctx`;
    - `cauta(banca, concept, categorie, termen, produs, text) -> list[dict]` (rânduri ca `/api/celula`);
    - `stare_banca(banca) -> "blocata" | "fara_surse" | None`.
  - Răspunsul lui `intreaba`:
    `{"interpretare", "ignorate", "raspunsuri": [{"banca", "mod", "total", "limitat", "ambigue", "rezumat", "randuri", "stare_banca"}], "model", "tokeni": {"intrare", "iesire", "citire_cache", "scriere_cache"}, "cost_usd"}`.

- [ ] **Pasul 2.1: scrie testele care eșuează**

În `app/test_intreaba.py`, adaugă după funcția `rand(...)`:

```python
class ClientFals:
    """Un client Anthropic fals: întoarce JSON-ul dat și ține minte cererile."""

    def __init__(self, raspuns=None, stop="end_turn", exceptie=None):
        self.cereri = []
        self._raspuns, self._stop, self._exceptie = raspuns, stop, exceptie
        self.messages = self

    def create(self, **kw):
        self.cereri.append(kw)
        if self._exceptie:
            raise self._exceptie
        return types.SimpleNamespace(
            content=[types.SimpleNamespace(type="text", text=json.dumps(self._raspuns))],
            stop_reason=self._stop,
            usage=types.SimpleNamespace(input_tokens=1200, output_tokens=60,
                                        cache_read_input_tokens=7000, cache_creation_input_tokens=0))


def fara_init(clasa, **atribute):
    """O excepție a SDK-ului fără răspunsul HTTP real: serverul se uită doar la clasă și la status_code."""
    e = clasa.__new__(clasa)
    for k, v in atribute.items():
        setattr(e, k, v)
    return e
```

Apoi adaugă, înaintea blocului `if __name__ == "__main__":`:

```python
class Intrebari(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="intreaba_test_")
        self.cautari = []
        self.randuri = {"bcr": [rand(0), rand(15)], "brd": []}
        self.model_vechi = os.environ.pop("MIP_INTREABA_MODEL", None)

    def tearDown(self):
        if self.model_vechi is not None:
            os.environ["MIP_INTREABA_MODEL"] = self.model_vechi

    def fa(self, client, stare_banca=lambda b: None):
        def cauta(banca, concept, categorie, termen, produs, text):
            self.cautari.append((banca, concept, categorie, termen, produs, text))
            return self.randuri.get(banca, [])
        return intreaba.Intrebari(context=lambda: CTX, cauta=cauta, stare_banca=stare_banca,
                                  client=client, dir_jurnal=self.dir)

    def test_cautare_pe_concept(self):
        c = ClientFals(interp(banci=["bcr"]))
        d = self.fa(c).intreaba("Cât costă administrarea contului la BCR?")
        self.assertEqual(self.cautari, [("bcr", "administrare_cont", None, None, None, None)])
        r = d["raspunsuri"][0]
        self.assertEqual((r["banca"], r["mod"], r["total"], r["stare_banca"]), ("bcr", "concept", 2, None))
        self.assertEqual(r["rezumat"][0]["maxim"], 15)
        self.assertEqual(d["model"], "claude-haiku-4-5")
        self.assertEqual(d["tokeni"], {"intrare": 1200, "iesire": 60, "citire_cache": 7000, "scriere_cache": 0})
        self.assertAlmostEqual(d["cost_usd"], (1200 * 1 + 60 * 5 + 7000 * 0.1) / 1e6)
        cerere = c.cereri[0]
        self.assertEqual(cerere["model"], "claude-haiku-4-5")
        self.assertNotIn("thinking", cerere)                       # Haiku 4.5: fără gândire extinsă
        self.assertEqual(set(cerere["output_config"]), {"format"})  # și fără `effort`, care dă eroare
        self.assertEqual(cerere["output_config"]["format"]["type"], "json_schema")
        self.assertEqual(cerere["system"][0]["cache_control"], {"type": "ephemeral"})
        self.assertEqual(cerere["messages"],
                         [{"role": "user", "content": "Cât costă administrarea contului la BCR?"}])

    def test_cautare_dupa_text(self):
        self.fa(ClientFals(interp(concept=None, text_cautat="datoria vamală"))).intreaba("vama la BCR?")
        self.assertEqual(self.cautari, [("bcr", None, None, None, None, "datoria vamală")])

    def test_anterior_ajunge_la_model(self):
        c = ClientFals(interp(banci=["brd"]))
        self.fa(c).intreaba("și la BRD?", interp())
        continut = c.cereri[0]["messages"][0]["content"]
        self.assertIn('"concept": "administrare_cont"', continut)
        self.assertIn("și la BRD?", continut)

    def test_zero_valori_spune_de_ce(self):
        d = self.fa(ClientFals(interp(banci=["brd"])), stare_banca=lambda b: "blocata").intreaba("BRD?")
        self.assertEqual((d["raspunsuri"][0]["total"], d["raspunsuri"][0]["stare_banca"]), (0, "blocata"))

    def test_multe_randuri_taiate_la_50(self):
        self.randuri["bcr"] = [rand(i) for i in range(120)]
        r = self.fa(ClientFals(interp())).intreaba("BCR?")["raspunsuri"][0]
        self.assertEqual((r["total"], len(r["randuri"]), r["rezumat"][0]["n"], r["limitat"]), (120, 50, 120, False))

    def test_text_limitat(self):
        self.randuri["bcr"] = [rand(i) for i in range(50)]
        r = self.fa(ClientFals(interp(concept=None, text_cautat="vamală"))).intreaba("BCR?")["raspunsuri"][0]
        self.assertTrue(r["limitat"])

    def test_in_afara_si_neclar_fara_cautare(self):
        for brut in (interp(tip="in_afara", banci=[]), interp(tip="neclar", banci=[], clarificare="Ce bancă?")):
            d = self.fa(ClientFals(brut)).intreaba("ceva")
            self.assertEqual(d["raspunsuri"], [])
        self.assertEqual(self.cautari, [])

    def test_refuz_sau_taiat_devine_neclar(self):
        for stop in ("refusal", "max_tokens"):
            d = self.fa(ClientFals(interp(), stop=stop)).intreaba("BCR?")
            self.assertEqual(d["interpretare"]["tip"], "neclar")
        self.assertEqual(self.cautari, [])

    def test_erorile_modelului(self):
        import anthropic
        cazuri = [
            (fara_init(anthropic.AuthenticationError, status_code=401), "401"),
            (fara_init(anthropic.RateLimitError, status_code=429), "429"),
            (fara_init(anthropic.APITimeoutError), "30 s"),
            (fara_init(anthropic.APIConnectionError), "api.anthropic.com"),
            (fara_init(anthropic.InternalServerError, status_code=529), "529"),
        ]
        for exc, text in cazuri:
            with self.assertRaises(intreaba.EroareModel) as e:
                self.fa(ClientFals(exceptie=exc)).intreaba("BCR?")
            self.assertIn(text, str(e.exception))

    def test_jurnal(self):
        import anthropic
        self.fa(ClientFals(interp())).intreaba("BCR?")
        with self.assertRaises(intreaba.EroareModel):
            self.fa(ClientFals(exceptie=fara_init(anthropic.APIConnectionError))).intreaba("BRD?")
        fisiere = os.listdir(self.dir)
        self.assertEqual(len(fisiere), 1)
        self.assertRegex(fisiere[0], r"^\d{4}-\d{2}\.jsonl$")
        with open(os.path.join(self.dir, fisiere[0]), encoding="utf-8") as f:
            randuri = [json.loads(x) for x in f]
        self.assertEqual([r["intrebare"] for r in randuri], ["BCR?", "BRD?"])
        self.assertEqual(randuri[0]["randuri"], {"bcr": 2})
        self.assertIn("api.anthropic.com", randuri[1]["eroare"])

    def test_stare_si_token(self):
        q = self.fa(ClientFals(interp()))
        self.assertEqual(set(q.stare()), {"activ", "model"})
        self.assertGreaterEqual(len(q.token), 32)
        self.assertNotEqual(q.token, self.fa(ClientFals(interp())).token)


class Preturi(unittest.TestCase):
    def test_modelele_de_ales_au_pret(self):
        """MIP_INTREABA_MODEL poate fi schimbat; fără preț, costul ar apărea „necunoscut”."""
        for m in ("claude-haiku-4-5", "claude-sonnet-5-5", "claude-opus-5-5"):
            self.assertIsNotNone(intreaba.preturi.cost(m, 1000, 100), m)
        self.assertAlmostEqual(intreaba.preturi.cost("claude-opus-5-5", 1_000_000, 0), 4.0)
```

- [ ] **Pasul 2.2: rulează testele, să vezi că eșuează**

Rulează: `python app/test_intreaba.py`
Aștepți: erori `AttributeError: module 'intreaba' has no attribute 'Intrebari'` (și `preturi`, `EroareModel`).

- [ ] **Pasul 2.3: adaugă prețurile modelelor noi**

În `extragere_produse_bancare/preturi.py`, în `PRETURI`, după linia `"claude-fable-5": (10.0, 50.0),`, adaugă:

```python
    # adăugate pe 06.10.2026 pentru MIP_INTREABA_MODEL („Întreabă datele”), din tabelul de prețuri
    # Anthropic din 25.09.2026
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
```

- [ ] **Pasul 2.4: scrie apelul, jurnalul și clasa**

În `app/intreaba.py`, înlocuiește blocul de importuri

```python
import json
import os
```

cu

```python
import datetime
import importlib.util
import json
import os
import secrets
import threading

RADACINA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_JURNAL = os.path.join(RADACINA, "loguri", "intreaba")
MAX_TOKENS = 400        # interpretarea are sub 200 de tokeni; marja e pentru `clarificare`
TIMEOUT_S = 30.0


def _incarca_preturi():
    # tabelul de prețuri al fluxului de comparație, un singur loc; încărcat după cale, nu prin
    # sys.path, ca modulele din extragere_produse_bancare/ să nu acopere modulele din app/ și ingest/
    spec = importlib.util.spec_from_file_location(
        "preturi", os.path.join(RADACINA, "extragere_produse_bancare", "preturi.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


preturi = _incarca_preturi()
```

Apoi, după `class Respins`, adaugă:

```python
class EroareModel(Exception):
    """Apelul la model n-a reușit (502); mesajul e pentru utilizator."""


def mesaj_eroare(exc):
    """Mesajul pentru utilizator, de la eroarea cea mai specifică la cea generală (retryable sau nu)."""
    import anthropic
    if isinstance(exc, anthropic.AuthenticationError):
        return "Cheia Anthropic e respinsă (401). Verifică ANTHROPIC_API_KEY din .env."
    if isinstance(exc, anthropic.RateLimitError):
        return "Prea multe cereri la Anthropic (429). Încearcă din nou peste un minut."
    if isinstance(exc, anthropic.APITimeoutError):
        return f"Modelul n-a răspuns în {int(TIMEOUT_S)} s. Încearcă din nou."
    if isinstance(exc, anthropic.APIConnectionError):
        return "Nu s-a putut ajunge la api.anthropic.com (rețea sau proxy)."
    if isinstance(exc, anthropic.APIStatusError):
        return f"API-ul Anthropic a răspuns cu eroarea {exc.status_code}."
    return f"Eroare la apelul modelului ({exc.__class__.__name__})."


def _acum():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")
```

La sfârșitul fișierului, adaugă clasa:

```python
class Intrebari:
    """O întrebare → interpretarea modelului → valorile din bază. Fără HTTP și fără SQL: serverul
    dă funcțiile de citire (`context`, `cauta`, `stare_banca`), ca la `rulari.Rulari`."""

    def __init__(self, context, cauta, stare_banca, client=None, dir_jurnal=DIR_JURNAL):
        self._sursa_context = context
        self._cauta = cauta
        self._stare_banca = stare_banca
        self._client = client
        self.dir = dir_jurnal
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
            self._client = anthropic.Anthropic(timeout=TIMEOUT_S, max_retries=2)
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
                system=[{"type": "text", "text": sistem, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": continut}],
                output_config={"format": {"type": "json_schema", "schema": sch}},
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

    def _raspuns(self, banca, interp):
        text = None if interp["concept"] else interp["text_cautat"]
        randuri = self._cauta(banca, interp["concept"], interp["categorie"], interp["termen"],
                              interp["produs_credit"], text)
        return {
            "banca": banca,
            "mod": "text" if text else "concept",
            "total": len(randuri),
            # căutarea după text e tăiată la MAX_RANDURI în SQL, deci totalul real poate fi mai mare
            "limitat": bool(text) and len(randuri) >= MAX_RANDURI,
            "ambigue": sum(1 for r in randuri if r.get("ambiguu")),
            "rezumat": rezuma(randuri),
            "randuri": randuri[:MAX_RANDURI],
            "stare_banca": None if randuri else self._stare_banca(banca),
        }

    def intreaba(self, intrebare, anterior=None):
        intrebare = verifica_intrebarea(intrebare)
        anterior = verifica_anterior(anterior)
        ctx, sistem, sch = self._context()
        m = model()
        rand = {"data": _acum(), "intrebare": intrebare, "model": m}
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
        raspunsuri = [self._raspuns(b, interp) for b in interp["banci"]] if interp["tip"] == "cautare" else []
        cost = preturi.cost(m, tokeni["intrare"], tokeni["iesire"], tokeni["citire_cache"], tokeni["scriere_cache"])
        rand.update(interpretare=interp, stop=stop, randuri={r["banca"]: r["total"] for r in raspunsuri},
                    tokeni=tokeni, cost_usd=cost)
        self._jurnal(rand)
        return {"interpretare": interp, "ignorate": ignorate, "raspunsuri": raspunsuri,
                "model": m, "tokeni": tokeni, "cost_usd": cost}

    def _jurnal(self, rand):
        """Un rând pe întrebare, ca să se vadă unde greșește interpretarea. Nu oprește răspunsul."""
        try:
            os.makedirs(self.dir, exist_ok=True)
            with self._lacat_jurnal:
                with open(os.path.join(self.dir, rand["data"][:7] + ".jsonl"), "a", encoding="utf-8") as f:
                    f.write(json.dumps(rand, ensure_ascii=False, default=str) + "\n")
        except OSError:
            pass
```

- [ ] **Pasul 2.5: rulează testele, să vezi că trec**

Rulează: `python app/test_intreaba.py`
Aștepți: `Ran 25 tests` … `OK`.

- [ ] **Pasul 2.6: `.gitignore` și `.env.example`**

În `.gitignore`, după linia `loguri/rulari/`, adaugă:

```
# „Întreabă datele” (app/intreaba.py): jurnalul întrebărilor, pe laptopul care le-a pus
loguri/intreaba/
```

În `.env.example`, după linia `MIP_PERMITE_RULARI=0`, adaugă (fișierul e scris fără diacritice,
păstrează stilul):

```
# „Intreaba datele” (pagina #/intreaba, app/intreaba.py). 1 = intrebarile merg la modelul
# Anthropic, cu cheia de mai sus (reala, nu placeholder). DOAR local, pe laptop: pe serverul
# comun ramane 0, fiindca acolo nu avem inca autentificare.
MIP_PERMITE_INTREBARI=0
# Modelul care interpreteaza intrebarea; implicit claude-haiku-4-5.
MIP_INTREABA_MODEL=claude-haiku-4-5
```

- [ ] **Pasul 2.7: commit**

```bash
git add app/intreaba.py app/test_intreaba.py extragere_produse_bancare/preturi.py .gitignore .env.example
git commit -m "app: „Întreabă datele” cheamă modelul cu schemă strictă, fără effort pe Haiku; cost din preturi.py, jurnal local"
```

---

### Task 3: datele din bază (contextul, căutarea după text, starea băncii)

**Fișiere:**
- Modificare: `app/server.py`:
  - importurile (`import re`, `import intreaba`);
  - `celula` (`app/server.py:561-640`);
  - funcțiile noi `_cuvinte_cautare`, `_context_intrebari`, `_cauta_intrebari`, `_stare_banca_intrebari`;
  - instanța `INTREBARI`.
- Modificare: `app/test_intreaba.py` (clasa `CuvinteCautare`)

**Interfețe:**
- Consumă (din Task 2): `intreaba.Intrebari`, `intreaba.MAX_RANDURI`.
- Produce:
  - `server.celula(q)` acceptă în plus `text` (și `camp` gol); fără `text` se comportă exact ca înainte;
  - `server._cuvinte_cautare(text) -> list[str]`, `server._context_intrebari() -> ctx`;
  - `server._cauta_intrebari(banca, concept, categorie, termen, produs, text) -> list[dict]`;
  - `server._stare_banca_intrebari(banca) -> str | None`, `server.INTREBARI`.

- [ ] **Pasul 3.1: notează ce întoarce acum `celula` (ca să verifici după că nu s-a schimbat)**

Rulează:
```bash
PYTHONIOENCODING=utf-8 python -c "import sys; sys.path.insert(0, 'app'); import server; print(len(server.celula({'banca': ['bcr'], 'camp': ['administrare_cont']})), len(server.celula({'banca': ['ing'], 'camp': ['nominala'], 'scenariu': ['depozite'], 'termen': ['12']})))"
```
Aștepți două numere, de pildă `316 4`. Le notezi. Depind de baza din `MIP_DSN`.

- [ ] **Pasul 3.2: scrie testul care eșuează**

În `app/test_intreaba.py`, înaintea blocului `if __name__ == "__main__":`, adaugă:

```python
class CuvinteCautare(unittest.TestCase):
    def test_cuvinte_cautare(self):
        import server
        self.assertEqual(server._cuvinte_cautare("Plată facturi"), ["plata", "facturi"])
        self.assertEqual(server._cuvinte_cautare("ȘTERGERE Ţară"), ["stergere", "tara"])
        # niciun wildcard LIKE (%, _) și niciun semn ajung în parametru
        self.assertEqual(server._cuvinte_cautare("100% gratuit_x'; drop--"), ["100", "gratuit", "drop"])
        self.assertEqual(server._cuvinte_cautare("a de la card card"), ["card"])
        self.assertEqual(server._cuvinte_cautare("unu doi trei patru cinci sase sapte"),
                         ["unu", "doi", "trei", "patru", "cinci"])
        self.assertEqual(server._cuvinte_cautare(None), [])
        self.assertEqual(server._cuvinte_cautare(""), [])
```

Rulează: `python app/test_intreaba.py`
Aștepți: `AttributeError: module 'server' has no attribute '_cuvinte_cautare'`.

- [ ] **Pasul 3.3: importurile din server**

În `app/server.py`, după `import os` (linia 19), adaugă `import re`. După linia
`import rulari  # noqa: E402  (app/, langa server)`, adaugă:

```python
import intreaba  # noqa: E402  (app/, langa server)
```

- [ ] **Pasul 3.4: căutarea după text în `celula`**

În `app/server.py`, imediat **înainte** de `def celula(q):`, adaugă:

```python
# Căutarea după text („Întreabă datele”): ce nu are concept stă în găleata `comision` (3.859 de
# valori în observatii_curente, baza mip, 06.10.2026) și n-ar fi găsit de nicio căutare pe `camp`.
# Fără diacritice pe ambele părți: întrebarea vine adesea scrisă fără ele, tarifele cu ele.
_DIACRITICE = str.maketrans("ăâîșşțţ", "aaisstt")
_TEXT_CAUTARE = ("translate(lower(coalesce(o.serviciu, '') || ' ' || coalesce(o.citat, '')), "
                 "'ăâîșşțţ', 'aaisstt')")


def _cuvinte_cautare(text):
    """Cuvintele unei căutări după text: litere și cifre (fără `%` sau `_`, care în LIKE ar fi
    wildcard-uri), de cel puțin 3 caractere, fără dubluri, cel mult 5."""
    cuvinte = []
    for c in re.findall(r"[^\W_]+", (text or "").lower().translate(_DIACRITICE)):
        if len(c) >= 3 and c not in cuvinte:
            cuvinte.append(c)
    return cuvinte[:5]
```

În `celula`:

1. Înlocuiește
```python
    if not (q.get("banca") and q.get("camp")):
        return {"eroare": "lipsește banca sau camp"}
```
cu
```python
    # cu `text` și fără `camp` („Întreabă datele”): toate conceptele băncii, filtrate după cuvinte,
    # cel mult intreaba.MAX_RANDURI rânduri; fără `text` totul rămâne ca înainte
    camp = (q.get("camp") or [""])[0]
    cuvinte = _cuvinte_cautare((q.get("text") or [""])[0])
    if not (q.get("banca") and (camp or cuvinte)):
        return {"eroare": "lipsește banca sau camp"}
```

2. După blocul
```python
    if produs in PRODUSE_CREDIT:
        extra += f" AND {PRODUS_CREDIT} = %s"
        p_extra = (produs,)
```
adaugă
```python
    for c in cuvinte:
        extra += f" AND {_TEXT_CAUTARE} LIKE %s"
        p_extra += ("%" + c + "%",)
```

3. În SQL-ul din `celula`, înlocuiește `WHERE b.slug = %s AND o.camp = %s` cu
`WHERE b.slug = %s AND (%s = '' OR o.camp = %s)`.

4. Înlocuiește
```python
           ORDER BY o.ambiguu, coalesce(o.serviciu, ''), o.valoare_num""",
        (q["banca"][0], q["camp"][0],
```
cu
```python
           ORDER BY o.ambiguu, coalesce(o.serviciu, ''), o.valoare_num"""
        + (f" LIMIT {intreaba.MAX_RANDURI}" if cuvinte else ""),
        (q["banca"][0], camp, camp,
```

- [ ] **Pasul 3.5: contextul, căutarea și starea băncii pentru `Intrebari`**

În `app/server.py`, după linia `RULARI = rulari.Rulari(slugs=_slugs_rulari, produse=_produse_rulari)`
(cam pe la linia 1869), adaugă:

```python
def _context_intrebari():
    """Băncile și conceptele pe care le vede modelul din „Întreabă datele”. Doar concepte cu valori
    numerice (127 în baza mip, 06.10.2026), fără găleata `comision`; fiecare cu 2–3 denumiri reale
    din tarife, ca modelul să lege „retragere de la bancomat” de `retragere_numerar` fără să
    dublăm etichetele din interfață sau vocabularul."""
    banci = interoghează("SELECT slug, nume FROM banci ORDER BY slug")
    concepte = interoghează(
        """SELECT o.camp, count(*)::int AS n,
                  array_agg(DISTINCT coalesce(o.unitate, '')) AS unitati,
                  array_agg(DISTINCT split_part(coalesce(o.cod_scenariu, ''), '|', 1)) AS categorii
           FROM observatii_curente o
           WHERE o.valoare_num IS NOT NULL AND o.camp IS NOT NULL AND o.camp <> 'comision'
           GROUP BY 1 ORDER BY 1""")
    exemple = interoghează(
        """SELECT camp, serviciu FROM (
             SELECT o.camp, o.serviciu,
                    row_number() OVER (PARTITION BY o.camp ORDER BY count(*) DESC, o.serviciu) AS rn
             FROM observatii_curente o
             WHERE o.valoare_num IS NOT NULL AND o.camp <> 'comision'
               AND coalesce(o.serviciu, '') <> ''
             GROUP BY 1, 2) x
           WHERE rn <= 3 ORDER BY camp, rn""")
    pe_camp = {}
    for e in exemple:
        pe_camp.setdefault(e["camp"], []).append(e["serviciu"])
    for c in concepte:
        c["unitati"] = sorted(u for u in c["unitati"] if u)
        c["categorii"] = sorted(x for x in c["categorii"] if x)
        c["exemple"] = pe_camp.get(c["camp"], [])
    return {
        "banci": banci,
        "concepte": concepte,
        "categorii": {k: v["titlu"] for k, v in GRUPURI_RATE.items()},
        "termene": {**{k: v[0] for k, v in TERMENE.items()}, "necunoscut": "termen nespecificat"},
        "produse": dict(PRODUSE_CREDIT),
    }


def _cauta_intrebari(banca, concept, categorie, termen, produs, text):
    """Valorile unei bănci pentru „Întreabă datele”, prin `celula`: aceleași rânduri, linkuri și
    nivele de dovadă ca Sertar-ul din 2.1, o singură interogare de întreținut."""
    r = celula({"banca": [banca], "camp": [concept or ""], "scenariu": [categorie or ""],
                "termen": [termen or ""], "produs": [produs or ""], "text": [text or ""]})
    return r if isinstance(r, list) else []


def _stare_banca_intrebari(banca):
    """De ce n-are banca valori: toate sursele blocate (WAF, robots.txt) sau nicio sursă. Altfel
    „nu avem valori” s-ar citi ca „banca nu are comisionul”."""
    r = interoghează(
        """SELECT count(s.id)::int AS n, count(s.id) FILTER (WHERE s.status = 'blocat')::int AS blocate
           FROM banci b LEFT JOIN surse s ON s.id_banca = b.id
           WHERE b.slug = %s""", (banca,))
    if not r:
        return None
    n, blocate = r[0]["n"], r[0]["blocate"]
    return "fara_surse" if n == 0 else "blocata" if blocate == n else None


INTREBARI = intreaba.Intrebari(context=_context_intrebari, cauta=_cauta_intrebari,
                               stare_banca=_stare_banca_intrebari)
```

- [ ] **Pasul 3.6: rulează testele, să vezi că trec**

Rulează: `python app/test_intreaba.py`
Aștepți: `Ran 26 tests` … `OK`.

Rulează: `python app/test_rulari.py`
Aștepți: `OK`.

- [ ] **Pasul 3.7: verifică pe baza reală**

Rulează aceeași comandă ca la pasul 3.1.
Aștepți **exact** cele două numere notate atunci.

Rulează:
```bash
PYTHONIOENCODING=utf-8 python -c "import sys; sys.path.insert(0, 'app'); import server; r = server.celula({'banca': ['bcr'], 'text': ['datoria vamală']}); print(len(r)); print([x['serviciu'] for x in r[:3]])"
```
Aștepți între 1 și 50 de rânduri. Pe `mip`, la 06.10.2026, existau 13 valori cu „Decontarea
electronică a datoriei vamale” la BCR. Primele servicii conțin „datori” și „vamal”.

Rulează:
```bash
PYTHONIOENCODING=utf-8 python -c "import sys; sys.path.insert(0, 'app'); import server, intreaba; c = server._context_intrebari(); print(len(c['banci']), len(c['concepte'])); print(len(intreaba.prompt(c)), 'caractere'); print(server._stare_banca_intrebari('cec'), server._stare_banca_intrebari('banorient'), server._stare_banca_intrebari('bcr'))"
```
Aștepți, pe `mip` la 06.10.2026: `30 127`, apoi lungimea promptului (o notezi pentru README),
apoi `blocata fara_surse None`.

- [ ] **Pasul 3.8: commit**

```bash
git add app/server.py app/test_intreaba.py
git commit -m "app: celula caută și după text (valorile fără concept), contextul și starea băncii pentru „Întreabă datele”"
```

---

### Task 4: rutele `GET` / `POST /api/intreaba`

**Fișiere:**
- Modificare: `app/rulari.py`, `verifica_cerere` (`app/rulari.py:146-169`)
- Modificare: `app/server.py`, clasa `Handler` (`app/server.py:2086-2215`)
- Modificare: `app/test_rulari.py`, clasa `Securitate`
- Modificare: `app/test_intreaba.py`, clasa `Http`

**Interfețe:**
- Consumă: `server.INTREBARI` (Task 3), `intreaba.activ`, `intreaba.PORT_VITE`, `intreaba.Respins`,
  `intreaba.EroareModel`.
- Produce:
  - `rulari.verifica_cerere(antete, port, token=None, porturi_extra=())`;
  - `GET /api/intreaba` → `{activ, model, token?}`;
  - `POST /api/intreaba` cu `{intrebare, anterior?}` → răspunsul lui `Intrebari.intreaba`, cu
    codurile 400, 403, 415 sau 502 și `{eroare}` la refuz.

- [ ] **Pasul 4.1: testul pentru portul Vite în `verifica_cerere`**

În `app/test_rulari.py`, în clasa `Securitate`, după `test_token`, adaugă:

```python
    def test_port_vite_doar_cand_e_cerut(self):
        """`porturi_extra` e doar pentru „Întreabă datele”; rulările rămân pe portul serverului."""
        vite = {"Host": "localhost:5173", "Origin": "http://localhost:5173"}
        self.assertIsNotNone(rulari.verifica_cerere(vite, 8765))
        self.assertIsNone(rulari.verifica_cerere(vite, 8765, porturi_extra=(5173,)))
        self.assertIsNotNone(rulari.verifica_cerere(
            {"Host": "localhost:8765", "Origin": "http://localhost:5173"}, 8765, porturi_extra=(5173,)))
        self.assertIsNotNone(rulari.verifica_cerere({"Host": "evil.com:5173"}, 8765, porturi_extra=(5173,)))
```

- [ ] **Pasul 4.2: testele HTTP**

În `app/test_intreaba.py`, înaintea blocului `if __name__ == "__main__":`, adaugă:

```python
class Http(unittest.TestCase):
    """Rutele din server, pe un port liber, cu un client fals în locul modelului."""

    @classmethod
    def setUpClass(cls):
        import server
        cls.server_mod = server
        cls.vechi = server.INTREBARI
        cls.client = ClientFals(interp())
        server.INTREBARI = intreaba.Intrebari(
            context=lambda: CTX, cauta=lambda *a: [rand(5)], stare_banca=lambda b: None,
            client=cls.client, dir_jurnal=tempfile.mkdtemp(prefix="intreaba_http_"))
        cls.srv = server.Server(("::", 0), server.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.env_vechi = {k: os.environ.get(k) for k in ("MIP_PERMITE_INTREBARI", "ANTHROPIC_API_KEY")}

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.server_mod.INTREBARI = cls.vechi
        for k, v in cls.env_vechi.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def setUp(self):
        os.environ["MIP_PERMITE_INTREBARI"] = "1"
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-" + "x" * 90

    def cere(self, metoda, cale, corp=None, antete=None, host=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        h = {"Host": host or f"localhost:{self.port}"}
        if corp is not None:
            h["Content-Type"] = "application/json"
            corp = json.dumps(corp)
        h.update(antete or {})
        c.request(metoda, cale, body=corp, headers=h)
        r = c.getresponse()
        d = r.read().decode("utf-8")
        c.close()
        try:
            return r.status, json.loads(d)
        except ValueError:
            return r.status, d

    def token(self):
        return self.cere("GET", "/api/intreaba")[1]["token"]

    def test_get(self):
        cod, d = self.cere("GET", "/api/intreaba")
        self.assertEqual((cod, d["activ"], d["model"]), (200, True, "claude-haiku-4-5"))
        self.assertEqual(d["token"], self.server_mod.INTREBARI.token)
        self.assertNotEqual(d["token"], self.server_mod.RULARI.token)

    def test_get_inactiv_fara_token(self):
        os.environ["ANTHROPIC_API_KEY"] = "placehold1"
        cod, d = self.cere("GET", "/api/intreaba")
        self.assertEqual((cod, d["activ"]), (200, False))
        self.assertNotIn("token", d)

    def test_get_host_strain(self):
        self.assertEqual(self.cere("GET", "/api/intreaba", host=f"evil.com:{self.port}")[0], 403)

    def test_post_merge_si_din_vite(self):
        t = self.token()
        for host in (f"localhost:{self.port}", "localhost:5173"):
            cod, d = self.cere("POST", "/api/intreaba", {"intrebare": "BCR?"},
                               {"X-MIP-Token": t, "Origin": f"http://{host}"}, host)
            self.assertEqual(cod, 200, (host, d))
            self.assertEqual(d["raspunsuri"][0]["banca"], "bcr")

    def test_post_refuzat(self):
        t = self.token()
        ok = {"X-MIP-Token": t}
        cazuri = [
            ({}, None),                                                   # fără token
            ({"X-MIP-Token": "gresit"}, None),                            # token greșit
            ({"X-MIP-Token": self.server_mod.RULARI.token}, None),        # tokenul rulărilor nu e bun aici
            (ok, f"evil.com:{self.port}"),                                # Host străin
            (ok, "localhost:5174"),                                       # alt port
            (dict(ok, Origin="http://evil.com"), None),                   # Origin străin
            (dict(ok, Origin="http://localhost:5173"), None),             # Origin diferit de Host
            (dict(ok, **{"Sec-Fetch-Site": "cross-site"}), None),
        ]
        n = len(self.client.cereri)
        for antete, host in cazuri:
            cod, _ = self.cere("POST", "/api/intreaba", {"intrebare": "BCR?"}, antete, host)
            self.assertEqual(cod, 403, (antete, host))
        self.assertEqual(len(self.client.cereri), n)   # niciun apel plătit

    def test_post_inactiv(self):
        t = self.token()
        os.environ["MIP_PERMITE_INTREBARI"] = "0"
        cod, d = self.cere("POST", "/api/intreaba", {"intrebare": "BCR?"}, {"X-MIP-Token": t})
        self.assertEqual(cod, 403)
        self.assertIn("MIP_PERMITE_INTREBARI", d["eroare"])

    def test_post_forma(self):
        ok = {"X-MIP-Token": self.token()}
        self.assertEqual(self.cere("POST", "/api/intreaba", {"intrebare": ""}, ok)[0], 400)
        self.assertEqual(self.cere("POST", "/api/intreaba", {"intrebare": "a" * 501}, ok)[0], 400)
        self.assertEqual(self.cere("POST", "/api/intreaba", ["BCR?"], ok)[0], 400)
        self.assertEqual(self.cere("POST", "/api/intreaba", {"intrebare": "x" * 5000}, ok)[0], 400)
        cod, _ = self.cere("POST", "/api/intreaba", None, dict(ok, **{"Content-Type": "text/plain"}))
        self.assertEqual(cod, 415)

    def test_eroare_model_502(self):
        import anthropic
        ok = {"X-MIP-Token": self.token()}
        vechi = self.server_mod.INTREBARI._client
        self.server_mod.INTREBARI._client = ClientFals(exceptie=fara_init(anthropic.APIConnectionError))
        try:
            cod, d = self.cere("POST", "/api/intreaba", {"intrebare": "BCR?"}, ok)
        finally:
            self.server_mod.INTREBARI._client = vechi
        self.assertEqual(cod, 502)
        self.assertIn("api.anthropic.com", d["eroare"])
```

- [ ] **Pasul 4.3: rulează testele, să vezi că eșuează**

Rulează: `python app/test_rulari.py`
Aștepți: `test_port_vite_doar_cand_e_cerut` eșuează cu
`TypeError: verifica_cerere() got an unexpected keyword argument 'porturi_extra'`.

Rulează: `python app/test_intreaba.py`
Aștepți: testele `Http` eșuează. `GET /api/intreaba` dă 404, iar `json.loads` nu reușește, deci
`KeyError` / `TypeError`.

- [ ] **Pasul 4.4: `porturi_extra` în `verifica_cerere`**

În `app/rulari.py`, înlocuiește semnătura și verificarea Host-ului:

```python
def verifica_cerere(antete, port, token=None, porturi_extra=()):
```

În docstring, înainte de `"""` de final, adaugă paragraful:

```
    `porturi_extra`: doar pentru „Întreabă datele”, care merge și din `npm run dev`: proxy-ul Vite
    păstrează Host-ul paginii (localhost:5173), iar Origin trebuie să fie tot pagina din Host.
    Rulările nu-l primesc, deci pentru ele nu se schimbă nimic.
```

Înlocuiește

```python
    if gazda not in {f"{g}:{port}" for g in GAZDE}:
```

cu

```python
    if gazda not in {f"{g}:{p}" for g in GAZDE for p in (port, *porturi_extra)}:
```

- [ ] **Pasul 4.5: corpul JSON într-un singur loc, apoi rutele**

În `app/server.py`, clasa `Handler`, după metoda `_refuz_rulari`, adaugă:

```python
    def _refuz_intrebari(self, cu_token):
        """Ca la rulări, dar permite și pagina din `npm run dev` (Host localhost:5173)."""
        return rulari.verifica_cerere(self.headers, self.server.server_address[1],
                                      INTREBARI.token if cu_token else None,
                                      porturi_extra=(intreaba.PORT_VITE,))

    def _corp_json(self, limita):
        """Corpul JSON al unui POST, sau None după ce eroarea a fost deja trimisă.

        JSON obligatoriu: un formular de pe alt site nu poate trimite application/json fără
        preflight CORS, pe care nu-l acceptăm."""
        if (self.headers.get("Content-Type") or "").split(";")[0].strip() != "application/json":
            self._json(415, {"eroare": "se acceptă doar application/json"})
            return None
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = -1
        if not 0 <= n <= limita:
            self._json(400, {"eroare": "corp prea mare"})
            return None
        try:
            corp = json.loads(self.rfile.read(n) or b"{}")
            if not isinstance(corp, dict):
                raise ValueError
        except ValueError:
            self._json(400, {"eroare": "JSON invalid"})
            return None
        return corp

    def _post_intreaba(self):
        if not intreaba.activ():
            self._json(403, {"eroare": "Întrebările sunt oprite pe acest server (MIP_PERMITE_INTREBARI sau cheia Anthropic)"})
            return
        motiv = self._refuz_intrebari(cu_token=True)
        if motiv:
            self._json(403, {"eroare": motiv})
            return
        corp = self._corp_json(4096)    # întrebarea (500) + interpretarea anterioară (1000), cu marjă
        if corp is None:
            return
        try:
            self._json(200, INTREBARI.intreaba(corp.get("intrebare"), corp.get("anterior")))
        except intreaba.Respins as exc:
            self._json(400, {"eroare": str(exc)})
        except intreaba.EroareModel as exc:
            self._json(502, {"eroare": str(exc)})
        except Exception as exc:
            self._json(500, {"eroare": f"{exc.__class__.__name__}: {exc}"})
```

Înlocuiește tot `do_POST` cu:

```python
    def do_POST(self):
        cale = urllib.parse.urlparse(self.path).path
        if cale == "/api/intreaba":
            self._post_intreaba()
            return
        if cale not in ("/api/rulari/porneste", "/api/rulari/opreste"):
            self.send_error(404)
            return
        if not rulari.activ():
            self._json(403, {"eroare": "Rulările manuale sunt oprite pe acest server (MIP_PERMITE_RULARI)"})
            return
        motiv = self._refuz_rulari(cu_token=True)
        if motiv:
            self._json(403, {"eroare": motiv})
            return
        corp = self._corp_json(2048)
        if corp is None:
            return
        try:
            if cale.endswith("/porneste"):
                self._json(200, RULARI.porneste(corp.get("id"), corp.get("banca"), corp.get("produs")))
            else:
                self._json(200, RULARI.opreste())
        except rulari.Respins as exc:
            self._json(400, {"eroare": str(exc)})
        except rulari.Ocupat as exc:
            self._json(409, {"eroare": str(exc)})
        except Exception as exc:
            self._json(500, {"eroare": f"{exc.__class__.__name__}: {exc}"})
```

În `do_GET`, imediat după `parsed = urllib.parse.urlparse(self.path)`, adaugă:

```python
        if parsed.path == "/api/intreaba":
            # tot cu Host/Origin, ca /api/rulari: răspunsul poartă tokenul de scriere
            motiv = self._refuz_intrebari(cu_token=False)
            if motiv:
                self._json(403, {"eroare": motiv})
                return
            date = INTREBARI.stare()
            if date["activ"]:
                date["token"] = INTREBARI.token
            self._json(200, date)
            return
```

- [ ] **Pasul 4.6: rulează testele, să vezi că trec**

Rulează: `python app/test_rulari.py`
Aștepți: `OK`, cu noul `test_port_vite_doar_cand_e_cerut`.

Rulează: `python app/test_intreaba.py`
Aștepți: `Ran 34 tests` … `OK`.

- [ ] **Pasul 4.7: verifică paginile vechi**

Pornește serverul într-un terminal separat: `python app/server.py`. Apoi rulează
`python app/verifica_pagini.py`.
Aștepți: toate paginile randate, fără erori.

- [ ] **Pasul 4.8: commit**

```bash
git add app/rulari.py app/server.py app/test_rulari.py app/test_intreaba.py
git commit -m "app: rutele /api/intreaba (token propriu, Host și Origin și din Vite, doar cu MIP_PERMITE_INTREBARI); corpul JSON citit într-un singur loc"
```

---

### Task 5: contractul în `shared/` și cererea din `web/`

**Fișiere:**
- Creare: `shared/src/celula.ts` (mutat din `shared/src/index.ts:198-227`)
- Creare: `shared/src/intreaba.ts`
- Modificare: `shared/src/index.ts`
- Modificare: `web/src/api/client.ts`
- Creare: `web/src/api/intreaba.ts`

**Interfețe:**
- Consumă: forma răspunsurilor din Task 4.
- Produce (exportate din `@mcc/shared`):
  - `ValoareDovada` și `Celula`, neschimbate;
  - `IntrebariStare`, `Interpretare`, `GrupaRezumat`, `RaspunsBanca`, `RaspunsIntrebare` (scheme și tipuri).
- Produce (în `web/src/api/`):
  - `apiPostValidat(cale, corp, token, schema)` în `client.ts`;
  - `useStareIntrebari()` și `trimiteIntrebarea(intrebare, anterior, token)` în `intreaba.ts`.

- [ ] **Pasul 5.1: mută `ValoareDovada` într-un fișier propriu**

`shared/src/intreaba.ts` are nevoie de `ValoareDovada`. Dacă l-ar importa din `./index`, care
re-exportă `./intreaba`, importul ar fi circular, iar `ValoareDovada` ar fi încă nedefinit la
evaluare.

Creează `shared/src/celula.ts` cu antetul de mai jos, urmat de blocul **mutat** din
`shared/src/index.ts`: de la comentariul `/** O valoare din sertarul cu dovezi (/api/celula). */`
până la `export const Celula = z.array(ValoareDovada)` inclusiv. Blocul se mută neschimbat.

```ts
/**
 * Rândurile din spatele unei celule (/api/celula), folosite de Sertar și de „Întreabă datele”.
 * Separat de index.ts ca alte fișiere din shared să le poată importa fără import circular.
 */
import { z } from 'zod'

```

În `shared/src/index.ts`, șterge blocul mutat. În locul lui, înaintea liniei
`export * from './rate_mobil'`, pune:

```ts
export * from './celula'
```

La sfârșitul listei de `export * from …` din `shared/src/index.ts`, adaugă:

```ts
export * from './intreaba'
```

- [ ] **Pasul 5.2: schemele răspunsului**

Creează `shared/src/intreaba.ts`:

```ts
/**
 * „Întreabă datele” (/api/intreaba): starea funcției și răspunsul la o întrebare, scrise după
 * app/intreaba.py din 06.10.2026. Interpretarea vine de la model, dar trece prin validarea
 * serverului; valorile (`randuri`) au forma rândurilor din /api/celula.
 */
import { z } from 'zod'
import { ValoareDovada } from './celula'

export const IntrebariStare = z
  .object({ activ: z.boolean(), model: z.string(), token: z.string().optional() })
  .passthrough()
export type IntrebariStare = z.infer<typeof IntrebariStare>

export const Interpretare = z.object({
  tip: z.enum(['cautare', 'neclar', 'in_afara']),
  banci: z.array(z.string()),
  concept: z.string().nullable(),
  categorie: z.string().nullable(),
  termen: z.string().nullable(),
  produs_credit: z.string().nullable(),
  text_cautat: z.string().nullable(),
  clarificare: z.string().nullable(),
})
export type Interpretare = z.infer<typeof Interpretare>

/** Pe unitate și categorie (primul segment din cod_scenariu), fără valorile ambigue. */
export const GrupaRezumat = z.object({
  unitate: z.string(),
  categorie: z.string(),
  n: z.number(),
  minim: z.number(),
  maxim: z.number(),
  gratuite: z.number(),
})
export type GrupaRezumat = z.infer<typeof GrupaRezumat>

export const RaspunsBanca = z
  .object({
    banca: z.string(),
    mod: z.enum(['concept', 'text']),
    total: z.number(),
    limitat: z.boolean(),
    ambigue: z.number(),
    rezumat: z.array(GrupaRezumat),
    randuri: z.array(ValoareDovada),
    stare_banca: z.enum(['blocata', 'fara_surse']).nullable(),
  })
  .passthrough()
export type RaspunsBanca = z.infer<typeof RaspunsBanca>

export const RaspunsIntrebare = z
  .object({
    interpretare: Interpretare,
    ignorate: z.array(z.string()),
    raspunsuri: z.array(RaspunsBanca),
    model: z.string(),
    tokeni: z.object({ intrare: z.number(), iesire: z.number(), citire_cache: z.number(), scriere_cache: z.number() }),
    cost_usd: z.number().nullable(),
  })
  .passthrough()
export type RaspunsIntrebare = z.infer<typeof RaspunsIntrebare>
```

- [ ] **Pasul 5.3: `apiPostValidat` în client**

În `web/src/api/client.ts`, înlocuiește funcția `api` cu varianta de mai jos. Validarea trece
într-o funcție comună, pe care o folosește și POST-ul nou:

```ts
/** Răspunsul, validat cu schema; aceleași reguli de eroare pentru GET și POST. */
async function dinRaspuns<S extends z.ZodTypeAny>(res: Response, cale: string, schema: S): Promise<z.infer<S>> {
  const corp = (await res.json().catch(() => null)) as unknown
  if (corp && typeof corp === 'object' && 'eroare' in corp && (corp as { eroare: unknown }).eroare) {
    throw new ApiError(res.status, String((corp as { eroare: unknown }).eroare))
  }
  // Fără corp JSON și cu eroare: serverul de date nu răspunde (în dezvoltare, proxy-ul Vite
  // întoarce 500 gol când app/server.py e oprit). Pagina arată atunci un mesaj clar, nu „HTTP 500”.
  if (!res.ok && corp === null) throw new ApiError(res.status, SERVER_OPRIT)
  if (!res.ok) throw new ApiError(res.status, `HTTP ${res.status}`)
  const rez = schema.safeParse(corp)
  if (!rez.success) {
    const p = rez.error.issues[0]
    throw new ApiError(res.status, `${cale}: ${p?.path.join('.') ?? ''} ${p?.message ?? ''}`)
  }
  return rez.data
}

export async function api<S extends z.ZodTypeAny>(cale: string, schema: S, params?: Record<string, unknown>): Promise<z.infer<S>> {
  const url = new URL(cale, window.location.origin)
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null) url.searchParams.set(k, String(v))
    }
  }
  return dinRaspuns(await fetch(url), cale, schema)
}
```

La sfârșitul fișierului, după `apiPost`, adaugă:

```ts
/**
 * POST cu răspuns validat („Întreabă datele”): aceleași antete ca apiPost (JSON + token), dar
 * erorile se aruncă, ca la `api`, iar răspunsul trece prin schemă. Ruta permite și Vite (:5173).
 */
export async function apiPostValidat<S extends z.ZodTypeAny>(cale: string, corp: unknown, token: string, schema: S): Promise<z.infer<S>> {
  const res = await fetch(cale, {
    method: 'POST',
    body: JSON.stringify(corp),
    headers: { 'Content-Type': 'application/json', 'X-MIP-Token': token },
  })
  return dinRaspuns(res, cale, schema)
}
```

- [ ] **Pasul 5.4: cererile paginii**

Creează `web/src/api/intreaba.ts`:

```ts
import { useQuery } from '@tanstack/react-query'
import { IntrebariStare, RaspunsIntrebare, type Interpretare } from '@mcc/shared'
import { api, apiPostValidat } from './client'

/** Starea funcției (activă doar local, cu MIP_PERMITE_INTREBARI=1 și cheia reală) și tokenul POST-ului. */
export function useStareIntrebari() {
  return useQuery({ queryKey: ['intreaba'], queryFn: () => api('/api/intreaba', IntrebariStare) })
}

/** O întrebare = un apel plătit la model: doar la clic, niciodată la randare (deci nu prin useQuery). */
export function trimiteIntrebarea(intrebare: string, anterior: Interpretare | null, token: string) {
  return apiPostValidat('/api/intreaba', { intrebare, anterior }, token, RaspunsIntrebare)
}
```

- [ ] **Pasul 5.5: verifică tipurile**

Rulează: `npm run typecheck`
Aștepți: 0 erori.

- [ ] **Pasul 5.6: commit**

```bash
git add shared/src/celula.ts shared/src/intreaba.ts shared/src/index.ts web/src/api/client.ts web/src/api/intreaba.ts
git commit -m "shared, web: schemele „Întreabă datele”; ValoareDovada în celula.ts ca să nu fie import circular; POST validat"
```

---

### Task 6: pagina `#/intreaba`

**Fișiere:**
- Creare: `web/src/i18n/dict/intreaba.ts`
- Modificare: `web/src/i18n/dict/index.ts`
- Modificare: `web/src/pagini.ts`, `web/src/App.tsx`
- Creare: `web/src/pages/Intreaba.tsx`, `web/src/styles/intreaba.css`

**Interfețe:**
- Consumă:
  - din Task 5: `useStareIntrebari`, `trimiteIntrebarea` și tipurile din `@mcc/shared`;
  - componente existente: `Sertar` (cu `CerereSertar`), `LinkSursa`, `EtichetaBanca`, `Pill`,
    `Eroare`, `SeIncarca`;
  - funcții existente: `etNume`, `unitTxt`, `num`, `deLaServer`, `areCheie`.
- Produce: ruta `/intreaba` și intrarea din meniu (grupul Analiză).

- [ ] **Pasul 6.1: textele**

Creează `web/src/i18n/dict/intreaba.ts`:

```ts
/**
 * „Întreabă datele” (#/intreaba). Cheile `server.intreaba.*` sunt mesajele românești trimise de
 * app/intreaba.py și app/server.py, traduse la afișare de `deLaServer`: textul român trebuie să
 * rămână identic cu cel din Python.
 */
export const intreaba = {
  "pagini.intreaba.nume_meniu": ["Întreabă datele", "Ask the data"],
  "pagini.intreaba.titlu": ["Întreabă datele", "Ask the data"],
  "pagini.intreaba.descriere": ["Întrebi despre o valoare a unei bănci, un comision sau o dobândă, și primești valorile din baza noastră, fiecare cu citatul și documentul ei. Modelul doar înțelege întrebarea; nicio cifră nu e scrisă de el.", "Ask about one bank's value, a fee or an interest rate, and get the values from our database, each with its quote and document. The model only understands the question; it writes none of the figures."],

  "intreaba.oprit": ["Întrebările sunt oprite pe acest server: cer MIP_PERMITE_INTREBARI=1 și cheia Anthropic reală în .env, doar pe laptop.", "Questions are turned off on this server: they need MIP_PERMITE_INTREBARI=1 and the real Anthropic key in .env, on the laptop only."],
  "intreaba.placeholder": ["De exemplu: Cât costă administrarea contului la BCR?", "For example: How much is the account maintenance fee at BCR?"],
  "intreaba.trimite": ["Întreabă", "Ask"],
  "intreaba.exemplu.1": ["Cât costă administrarea contului la BCR?", "How much is the account maintenance fee at BCR?"],
  "intreaba.exemplu.2": ["Ce dobândă dă ING la depozitul pe 12 luni?", "What rate does ING pay on a 12-month deposit?"],
  "intreaba.exemplu.3": ["Cât costă retragerea de numerar de la ATM-ul altei bănci la Raiffeisen?", "What does Raiffeisen charge for a cash withdrawal at another bank's ATM?"],
  "intreaba.model": ["Model: {model}. Fiecare întrebare e un apel plătit.", "Model: {model}. Each question is a paid call."],
  "intreaba.cost_total": ["costul sesiunii: {cost}", "session cost: {cost}"],
  "intreaba.se_gandeste": ["Se interpretează întrebarea…", "Interpreting the question…"],

  "intreaba.am_inteles": ["Am înțeles:", "Understood as:"],
  "intreaba.text": ["căutare după text „{text}”", "text search “{text}”"],
  "intreaba.ignorate": ["Răspund la cel mult 3 bănci odată; am lăsat deoparte: {banci}.", "I answer for at most 3 banks at a time; left out: {banci}."],
  "intreaba.in_afara": ["Răspund doar la valori: o bancă și un comision sau o dobândă. Comparațiile între bănci sunt în paginile 2.1 și 2.2. De exemplu:", "I only answer about values: one bank and a fee or an interest rate. Comparisons between banks are on pages 2.1 and 2.2. For example:"],
  "intreaba.neclar": ["N-am înțeles ce valoare cauți. Spune banca și comisionul sau dobânda.", "I could not tell which value you are after. Name the bank and the fee or the rate."],
  "intreaba.clarificare_eticheta": ["întrebare de la model", "question from the model"],
  "intreaba.clarificare_tooltip": ["Singurul text scris de model: o întrebare înapoi, când nu e clar ce cauți.", "The only text written by the model: a question back, when it is unclear what you are after."],

  "intreaba.zero": ["Nu avem valori pentru {concept} la {banca}.", "We have no values for {concept} at {banca}."],
  "intreaba.stare.blocata": ["Banca e documentată ca blocată (WAF sau robots.txt): n-am luat nimic de pe site-ul ei.", "The bank is documented as blocked (WAF or robots.txt): we took nothing from its website."],
  "intreaba.stare.fara_surse": ["Pentru această bancă n-avem încă nicio sursă.", "We have no source for this bank yet."],
  "intreaba.mod_text": ["căutare după text", "text search"],
  "intreaba.mod_text_tooltip": ["Întrebarea nu se potrivește cu niciun concept comparabil, deci am căutat cuvintele în denumirile și citatele băncii. Valorile nu sunt comparabile între bănci.", "The question matches no comparable concept, so the words were searched in the bank's own service names and quotes. The values are not comparable across banks."],
  "intreaba.rezumat_1": ["1 valoare: {min}", "1 value: {min}"],
  "intreaba.rezumat_n": ["{n} valori, între {min} și {max}", "{n} values, from {min} to {max}"],
  "intreaba.rezumat_egal_1": ["1 valoare: {val}", "1 value: {val}"],
  "intreaba.rezumat_egal_n": ["{n} valori, toate {val}", "{n} values, all {val}"],
  "intreaba.gratuite_1": ["1 gratuită", "1 free"],
  "intreaba.gratuite_n": ["{n} gratuite", "{n} free"],
  "intreaba.ambigue_1": ["1 valoare ambiguă, lăsată în afara intervalului (vezi coada de verificare).", "1 ambiguous value, left out of the range (see the review queue)."],
  "intreaba.ambigue_n": ["{n} valori ambigue, lăsate în afara intervalului (vezi coada de verificare).", "{n} ambiguous values, left out of the range (see the review queue)."],
  "intreaba.ambiguu": ["ambiguă", "ambiguous"],
  "intreaba.vezi_dovezi": ["Vezi toate dovezile", "See all evidence"],
  "intreaba.arata_toate_1": ["Arată toate ({n})", "Show all ({n})"],
  "intreaba.arata_toate_n": ["Arată toate ({n})", "Show all ({n})"],
  "intreaba.arata_mai_putine": ["Arată mai puține", "Show fewer"],
  "intreaba.limitat": ["Sunt afișate primele {n}; restrânge căutarea cu încă un cuvânt.", "Showing the first {n}; narrow the search with one more word."],
  "intreaba.subsol": ["{model} · {intrare} tokeni la intrare, {iesire} la ieșire · {cost}", "{model} · {intrare} input tokens, {iesire} output · {cost}"],
  "intreaba.cost_necunoscut": ["cost necunoscut (modelul nu e în preturi.py)", "unknown cost (model not in preturi.py)"],

  "intreaba.categorie.comision": ["comision", "fee"],
  "intreaba.categorie.comisioane": ["comisioane", "fees"],
  "intreaba.categorie.limita": ["limită", "limit"],
  "intreaba.categorie.dobanda": ["dobândă", "interest"],
  "intreaba.categorie.nota": ["notă", "note"],
  "intreaba.categorie.credite": ["credite", "loans"],
  "intreaba.categorie.depozite": ["depozite", "deposits"],
  "intreaba.categorie.conturi_carduri": ["conturi și carduri", "accounts and cards"],
  "intreaba.categorie.curs": ["curs valutar", "exchange rate"],
  "intreaba.termen.scurt": ["1–3 luni", "1–3 months"],
  "intreaba.termen.6": ["4–6 luni", "4–6 months"],
  "intreaba.termen.12": ["7–12 luni", "7–12 months"],
  "intreaba.termen.lung": ["peste 12 luni", "over 12 months"],
  "intreaba.termen.necunoscut": ["termen nespecificat", "unspecified term"],
  "intreaba.produs.ipotecar": ["credit ipotecar", "mortgage"],
  "intreaba.produs.nevoi_personale": ["nevoi personale", "personal loan"],
  "intreaba.produs.card": ["card de credit / overdraft", "credit card / overdraft"],
  "intreaba.produs.rate_magazin": ["rate fără dobândă în magazine", "interest-free instalments in shops"],
  "intreaba.produs.altele": ["credit nespecificat", "unspecified loan"],

  "server.intreaba.oprit": ["Întrebările sunt oprite pe acest server (MIP_PERMITE_INTREBARI sau cheia Anthropic)", "Questions are turned off on this server (MIP_PERMITE_INTREBARI or the Anthropic key)"],
  "server.intreaba.goala": ["Scrie o întrebare.", "Write a question."],
  "server.intreaba.lunga": ["Întrebarea are peste {n} de caractere.", "The question is over {n} characters long."],
  "server.intreaba.anterior": ["Interpretarea anterioară nu e validă.", "The previous interpretation is not valid."],
  "server.intreaba.401": ["Cheia Anthropic e respinsă (401). Verifică ANTHROPIC_API_KEY din .env.", "The Anthropic key was rejected (401). Check ANTHROPIC_API_KEY in .env."],
  "server.intreaba.429": ["Prea multe cereri la Anthropic (429). Încearcă din nou peste un minut.", "Too many requests to Anthropic (429). Try again in a minute."],
  "server.intreaba.timeout": ["Modelul n-a răspuns în {s} s. Încearcă din nou.", "The model did not answer within {s} s. Try again."],
  "server.intreaba.retea": ["Nu s-a putut ajunge la api.anthropic.com (rețea sau proxy).", "Could not reach api.anthropic.com (network or proxy)."],
  "server.intreaba.status": ["API-ul Anthropic a răspuns cu eroarea {cod}.", "The Anthropic API answered with error {cod}."],
  "server.intreaba.alta": ["Eroare la apelul modelului ({clasa}).", "Error calling the model ({clasa})."],
} as const
```

În `web/src/i18n/dict/index.ts`, adaugă `import { intreaba } from './intreaba'` după importul lui
`rulare_manuala`. Adaugă și `...intreaba,` după `...rulare_manuala,` în `DICT`.

- [ ] **Pasul 6.2: meniul și ruta**

În `web/src/pagini.ts`, în grupul `pagini.grup.analiza`, după `{ id: 'istoric', pdf: '', mutata: true },`, adaugă:

```ts
      { id: 'intreaba', pdf: '', mutata: true },
```

În `web/src/App.tsx`, după `import RulareManuala from './pages/RulareManuala'`, adaugă
`import Intreaba from './pages/Intreaba'`. Apoi, după
`<Route path="/istoric" element={<Istoric />} />`, adaugă:

```tsx
        <Route path="/intreaba" element={<Intreaba />} />
```

- [ ] **Pasul 6.3: stilurile**

Creează `web/src/styles/intreaba.css`:

```css
/* „Întreabă datele” (#/intreaba): întrebarea sus, fișele de răspuns dedesubt, cele noi jos */
.intreaba-oprit { margin-bottom: 14px; max-width: 900px }
.intreaba-intrebare { max-width: 900px; margin-bottom: 18px }
.intreaba-butoane { display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0 }
.intreaba-mesaje { display: flex; flex-direction: column; gap: 14px; max-width: 900px }
.intreaba-mesaj { border: 1px solid var(--line); border-radius: 9px; background: var(--surface); padding: 12px 16px }
.intreaba-q { font-family: var(--serif); font-size: 15px; margin: 0 0 8px; color: var(--ink) }
.intreaba-inteles { margin: 0 0 10px }
.intreaba-fisa { border-top: 1px solid var(--line-2); padding: 10px 0 }
.intreaba-fisa-cap { display: flex; align-items: center; gap: 10px; margin-bottom: 6px }
.intreaba-rezumat { margin: 4px 0 8px; padding-left: 18px }
.intreaba-valori { width: 100%; border-collapse: collapse; font-size: 12.5px }
.intreaba-valori td { padding: 5px 8px 5px 0; border-top: 1px solid var(--line-2); vertical-align: top }
.intreaba-valori td.valoare { font-family: var(--mono); white-space: nowrap }
.intreaba-valori tr.ambiguu { opacity: .7 }
.intreaba-eroare { color: var(--warn) }
.intreaba-subsol { margin: 8px 0 0 }
@media (max-width: 640px) {
  .intreaba-valori td.valoare { white-space: normal }
}
```

- [ ] **Pasul 6.4: pagina**

Creează `web/src/pages/Intreaba.tsx`:

```tsx
import { useState } from 'react'
import { Button, Input, Tooltip } from 'antd'
import type { Interpretare, RaspunsBanca, RaspunsIntrebare, ValoareDovada } from '@mcc/shared'
import { SERVER_OPRIT } from '../api/client'
import { trimiteIntrebarea, useStareIntrebari } from '../api/intreaba'
import { useMeta, type Meta } from '../api/meta'
import { EtichetaBanca, Eroare, Pill, SeIncarca } from '../components/comune'
import { LinkSursa } from '../components/Dovezi'
import Sertar, { type CerereSertar } from '../components/Sertar'
import { etNume, unitTxt } from '../components/valori'
import { areCheie, useLang, type DictKey } from '../i18n'
import { deLaServer } from '../i18n/server'
import { num } from '../util/format'
import '../styles/intreaba.css'

/**
 * „Întreabă datele”: o întrebare despre o valoare a unei bănci. Modelul (app/intreaba.py) doar
 * traduce textul în banca și conceptul căutat; cifrele, citatele și documentele vin din bază, prin
 * aceeași funcție ca Sertar-ul din 2.1, deci fișa nu conține niciun număr scris de model.
 * Conversația stă doar în memoria paginii, nu în adresă: un link deschis ar porni un apel plătit
 * (abatere asumată de la „filtrele stau în adresă”, specificația din 06.10.2026).
 */

interface Mesaj {
  id: number
  intrebare: string
  raspuns?: RaspunsIntrebare
  eroare?: string
}

type Tr = (k: DictKey, p?: Record<string, string | number>) => string

const EXEMPLE: DictKey[] = ['intreaba.exemplu.1', 'intreaba.exemplu.2', 'intreaba.exemplu.3']
const PRIMELE = 5

/** O întrebare costă miimi de dolar: `usd` din Logging ar arăta orice sub un cent ca „< $0,01”. */
const dolari = (v: number, locale: string) => '$' + num(v, locale, 4)

/** Eticheta unei chei din vocabular; o cheie nouă, fără traducere, apare cum vine, nu dispare. */
function eticheta(k: string, rezerva: string, t: Tr): string {
  return areCheie(k) ? t(k) : rezerva
}

export default function Intreaba() {
  const { t, lang, locale } = useLang()
  const meta = useMeta()
  const stare = useStareIntrebari()
  const [text, setText] = useState('')
  const [mesaje, setMesaje] = useState<Mesaj[]>([])
  const [seTrimite, setSeTrimite] = useState(false)
  const [cerere, setCerere] = useState<CerereSertar | null>(null)

  const err = meta.error ?? stare.error
  if (err) return <Eroare e={err} />
  if (!meta.data || !stare.data) return <SeIncarca />
  const m = meta.data
  const st = stare.data
  const cost = mesaje.reduce((s, x) => s + (x.raspuns?.cost_usd ?? 0), 0)

  async function trimite(intrebare: string) {
    const q = intrebare.trim()
    if (!q || seTrimite || !st.activ) return
    // „și la BRD?” continuă ultima căutare reușită, nu o clarificare sau o eroare
    const anterior = [...mesaje].reverse().find((x) => x.raspuns?.interpretare.tip === 'cautare')?.raspuns?.interpretare ?? null
    const id = Date.now()
    setMesaje((x) => [...x, { id, intrebare: q }])
    setSeTrimite(true)
    try {
      const r = await trimiteIntrebarea(q, anterior, st.token ?? '')
      setMesaje((x) => x.map((y) => (y.id === id ? { ...y, raspuns: r } : y)))
      setText('')
    } catch (e) {
      const mesaj = (e as Error).message
      const afisat = mesaj === SERVER_OPRIT ? t('comun.server_oprit') : deLaServer(mesaj, lang)
      setMesaje((x) => x.map((y) => (y.id === id ? { ...y, eroare: afisat } : y)))
      // serverul repornit are alt token: îl ia din nou, întrebarea rămâne în câmp
      if (mesaj.includes('token')) void stare.refetch()
    } finally {
      setSeTrimite(false)
    }
  }

  return (
    <>
      {!st.activ && <div className="callout warn intreaba-oprit">{t('intreaba.oprit')}</div>}
      <section className="intreaba-intrebare">
        <Input.TextArea
          value={text}
          onChange={(e) => setText(e.target.value)}
          maxLength={500}
          autoSize={{ minRows: 2, maxRows: 5 }}
          placeholder={t('intreaba.placeholder')}
          disabled={!st.activ}
          onPressEnter={(e) => {
            if (!e.shiftKey) {
              e.preventDefault()
              void trimite(text)
            }
          }}
        />
        <div className="intreaba-butoane">
          <Button type="primary" onClick={() => void trimite(text)} loading={seTrimite} disabled={!st.activ || !text.trim()}>
            {t('intreaba.trimite')}
          </Button>
          {EXEMPLE.map((k) => (
            <Button key={k} size="small" disabled={!st.activ || seTrimite} onClick={() => { setText(t(k)); void trimite(t(k)) }}>
              {t(k)}
            </Button>
          ))}
        </div>
        <p className="note">
          {t('intreaba.model', { model: st.model })}
          {mesaje.length > 0 && ` · ${t('intreaba.cost_total', { cost: dolari(cost, locale) })}`}
        </p>
      </section>
      <section className="intreaba-mesaje">
        {mesaje.map((x) => (
          <article key={x.id} className="intreaba-mesaj">
            <p className="intreaba-q">{x.intrebare}</p>
            {!x.raspuns && !x.eroare && <p className="note">{t('intreaba.se_gandeste')}</p>}
            {x.eroare && <p className="note intreaba-eroare">{x.eroare}</p>}
            {x.raspuns && <Raspuns r={x.raspuns} m={m} onDovezi={setCerere} onExemplu={(q) => void trimite(q)} />}
          </article>
        ))}
      </section>
      <Sertar cerere={cerere} onClose={() => setCerere(null)} />
    </>
  )
}

function Raspuns({ r, m, onDovezi, onExemplu }: {
  r: RaspunsIntrebare; m: Meta; onDovezi: (c: CerereSertar) => void; onExemplu: (q: string) => void
}) {
  const { t, locale } = useLang()
  const i = r.interpretare
  const tk = r.tokeni
  const subsol = (
    <p className="note intreaba-subsol">
      {t('intreaba.subsol', {
        model: r.model,
        intrare: num(tk.intrare + tk.citire_cache + tk.scriere_cache, locale, 0),
        iesire: num(tk.iesire, locale, 0),
        cost: r.cost_usd === null ? t('intreaba.cost_necunoscut') : dolari(r.cost_usd, locale),
      })}
    </p>
  )
  if (i.tip === 'in_afara') {
    return (
      <>
        <p>{t('intreaba.in_afara')}</p>
        <div className="intreaba-butoane">
          {EXEMPLE.map((k) => <Button key={k} size="small" onClick={() => onExemplu(t(k))}>{t(k)}</Button>)}
        </div>
        {subsol}
      </>
    )
  }
  if (i.tip === 'neclar') {
    return (
      <>
        {i.clarificare
          ? <p><Pill title={t('intreaba.clarificare_tooltip')}>{t('intreaba.clarificare_eticheta')}</Pill> {i.clarificare}</p>
          : <p>{t('intreaba.neclar')}</p>}
        {subsol}
      </>
    )
  }
  return (
    <>
      <p className="intreaba-inteles">
        {t('intreaba.am_inteles')} <b>{i.banci.map((b) => m.nume[b] ?? b).join(', ')}</b>
        {' · '}{i.concept ? etNume(i.concept, t) : t('intreaba.text', { text: i.text_cautat ?? '' })}
        {i.categorie && <> · {eticheta(`intreaba.categorie.${i.categorie}`, i.categorie, t)}</>}
        {i.termen && <> · {eticheta(`intreaba.termen.${i.termen}`, i.termen, t)}</>}
        {i.produs_credit && <> · {eticheta(`intreaba.produs.${i.produs_credit}`, i.produs_credit, t)}</>}
      </p>
      {r.ignorate.length > 0 && <p className="note">{t('intreaba.ignorate', { banci: r.ignorate.map((b) => m.nume[b] ?? b).join(', ') })}</p>}
      {r.raspunsuri.map((rb) => <FisaBanca key={rb.banca} rb={rb} i={i} m={m} onDovezi={onDovezi} />)}
      {subsol}
    </>
  )
}

function FisaBanca({ rb, i, m, onDovezi }: { rb: RaspunsBanca; i: Interpretare; m: Meta; onDovezi: (c: CerereSertar) => void }) {
  const { t, tn, locale } = useLang()
  const [toate, setToate] = useState(false)
  const concept = i.concept ? etNume(i.concept, t) : t('intreaba.text', { text: i.text_cautat ?? '' })
  if (rb.total === 0) {
    return (
      <div className="intreaba-fisa">
        <EtichetaBanca slug={rb.banca} m={m} fisa />
        <p>
          {t('intreaba.zero', { concept, banca: m.nume[rb.banca] ?? rb.banca })}
          {rb.stare_banca && <> {t(rb.stare_banca === 'blocata' ? 'intreaba.stare.blocata' : 'intreaba.stare.fara_surse')}</>}
        </p>
      </div>
    )
  }
  const vizibile = toate ? rb.randuri : rb.randuri.slice(0, PRIMELE)
  const cuUnitate = (v: number, u: string) => num(v, locale) + unitTxt(u, t)
  return (
    <div className="intreaba-fisa">
      <div className="intreaba-fisa-cap">
        <EtichetaBanca slug={rb.banca} m={m} fisa />
        {rb.mod === 'text' && (
          <Tooltip title={t('intreaba.mod_text_tooltip')}>
            <span><Pill tip="amb">{t('intreaba.mod_text')}</Pill></span>
          </Tooltip>
        )}
      </div>
      <ul className="intreaba-rezumat">
        {rb.rezumat.map((g) => (
          <li key={`${g.unitate}|${g.categorie}`}>
            {g.minim === g.maxim
              ? tn('intreaba.rezumat_egal', g.n, { val: cuUnitate(g.minim, g.unitate) })
              : tn('intreaba.rezumat', g.n, { min: cuUnitate(g.minim, g.unitate), max: cuUnitate(g.maxim, g.unitate) })}
            {g.gratuite > 0 && <> · {tn('intreaba.gratuite', g.gratuite)}</>}
            {rb.rezumat.length > 1 && <> · <span className="note">{eticheta(`intreaba.categorie.${g.categorie}`, g.categorie, t)}</span></>}
            {rb.mod === 'concept' && i.concept && (
              <Button size="small" type="link" onClick={() => onDovezi({
                banca: rb.banca, camp: i.concept!, unitate: g.unitate, scenariu: g.categorie,
                termen: i.termen ?? '', produs: i.produs_credit ?? '',
              })}>
                {t('intreaba.vezi_dovezi')}
              </Button>
            )}
          </li>
        ))}
      </ul>
      {rb.ambigue > 0 && <p className="note">{tn('intreaba.ambigue', rb.ambigue)}</p>}
      <table className="intreaba-valori">
        <tbody>{vizibile.map((v, k) => <Rand key={k} v={v} />)}</tbody>
      </table>
      {rb.randuri.length > PRIMELE && (
        <Button size="small" type="link" onClick={() => setToate(!toate)}>
          {toate ? t('intreaba.arata_mai_putine') : tn('intreaba.arata_toate', rb.randuri.length)}
        </Button>
      )}
      {rb.limitat && <p className="note">{t('intreaba.limitat', { n: rb.randuri.length })}</p>}
    </div>
  )
}

/** Un rând: serviciul și condiția băncii (date, netraduse), valoarea, dovada. */
function Rand({ v }: { v: ValoareDovada }) {
  const { t, locale } = useLang()
  const valoare = v.valoare !== null ? num(v.valoare, locale) + unitTxt(v.unitate, t) : (v.valoare_text ?? '—')
  return (
    <tr className={v.ambiguu ? 'ambiguu' : undefined}>
      <td>{v.serviciu ?? '—'}{v.conditie && <div className="note">{v.conditie}</div>}</td>
      <td className="valoare">{valoare}{v.frecventa && <div className="note">{v.frecventa}</div>}</td>
      <td>
        {v.ambiguu && <Pill tip="amb" title={v.motiv_ambiguu ?? undefined}>{t('intreaba.ambiguu')}</Pill>}{' '}
        <LinkSursa r={v} />
      </td>
    </tr>
  )
}
```

`t` primește doar chei `DictKey`. Cheile construite din date (categorie, termen, produs) trec prin
`eticheta`, care le verifică cu `areCheie`. `tn` primește baza ca `string` și alege `_1` / `_n`.
Nu ocoli o eroare de tip cu `as any`.

- [ ] **Pasul 6.5: tipurile și build-ul**

Rulează: `npm run typecheck && npm run build`
Aștepți: 0 erori. Avertismentul despre chunk-ul de 1,8 MB e mai vechi și rămâne.

- [ ] **Pasul 6.6: verifică în browser**

1. Pornește serverul într-un terminal separat (`python app/server.py`), fără `MIP_PERMITE_INTREBARI`
   în `.env`. Pornește interfața cu `npm run dev`. Deschide `http://localhost:5173/#/intreaba`.
   - Aștepți: pagina „Întreabă datele” în meniul Analiză, avertismentul „Întrebările sunt oprite…”,
     câmpul și butoanele dezactivate, consola curată.
   - Comută pe EN: aștepți textele în engleză.
2. **Oprește-te și cere-i lui Nicolae acordul pentru apelurile reale.** Estimarea: 6 întrebări ×
   ~$0,01 = ~$0,06. Cu acordul lui, pune în `.env` `MIP_PERMITE_INTREBARI=1` și cheia reală, apoi
   repornește serverul.
3. Din `http://localhost:5173/#/intreaba` (asta verifică și Host/Origin prin proxy-ul Vite), pune pe
   rând întrebările de mai jos. Aștepți:
   - „Cât costă administrarea contului la BCR?” → „Am înțeles: BCR · Administrare cont”, rezumatul
     pe unitate, primele 5 valori cu link. „Vezi toate dovezile” deschide Sertar-ul cu aceleași
     valori ca în 2.1.
   - „blabla” → mesajul „N-am înțeles…” sau o întrebare de la model, etichetată.
   - „și la BRD?” → **BRD · Administrare cont**. Asta arată că s-a continuat ultima *căutare*, nu
     mesajul neclar.
   - „Ce dobândă dă ING la depozitul pe 12 luni?” → ING · categoria depozite · termen 7–12 luni.
   - „Cât costă decontarea datoriei vamale la BCR?” → eticheta „căutare după text”, cu valori care
     conțin „vamal”.
   - „Care bancă are cel mai mic comision?” → mesajul „Răspund doar la valori…”, cu exemplele.
4. Deschide `http://localhost:8765/app/#/intreaba` (după `npm run build`) și pune o întrebare.
   Aștepți: merge și de pe originea serverului.
5. Verifică `loguri/intreaba/2026-10.jsonl`: un rând pe întrebare, fără cheia API.
6. Notează din subsolul fișelor tokenii de intrare și costul primei întrebări, apoi al doua (cu
   cache). Le vei pune în README la Task 7.

- [ ] **Pasul 6.7: commit**

```bash
git add web/src/i18n/dict/intreaba.ts web/src/i18n/dict/index.ts web/src/pagini.ts web/src/App.tsx web/src/pages/Intreaba.tsx web/src/styles/intreaba.css
git commit -m "web: pagina „Întreabă datele” (fișa pe bancă cu rezumat și dovezi, Sertar-ul existent, RO/EN)"
```

---

### Task 7: evaluarea și documentația

**Fișiere:**
- Creare: `app/intreaba_exemple.json`, `app/eval_intreaba.py`
- Modificare: `README.md`, `CLAUDE.md`

**Interfețe:**
- Consumă: `intreaba.Intrebari`, `intreaba.cheie_reala`, `intreaba.model`, `server._context_intrebari`.
- Produce: cifrele măsurate din README.

- [ ] **Pasul 7.1: setul de evaluare**

Creează `app/intreaba_exemple.json`. În `asteptat` intră doar câmpurile care trebuie să se
potrivească; `banci` se compară fără ordine; `text_cautat_nenul` cere doar ca modelul să fi
scris un text de căutare.

```json
[
  {"intrebare": "Cât costă administrarea contului la BCR?",
   "asteptat": {"tip": "cautare", "banci": ["bcr"], "concept": "administrare_cont"}},
  {"intrebare": "Ce comision are ING la retragerea de numerar de la ATM-ul altei bănci?",
   "asteptat": {"tip": "cautare", "banci": ["ing"], "concept": "retragere_numerar"}},
  {"intrebare": "Cât costă emiterea unui card de debit la BRD?",
   "asteptat": {"tip": "cautare", "banci": ["brd"], "concept": "emitere_card"}},
  {"intrebare": "Cât mă costă extrasul de cont la Raiffeisen?",
   "asteptat": {"tip": "cautare", "banci": ["raiffeisen"], "concept": "extras_de_cont"}},
  {"intrebare": "Ce dobândă are Libra la depozitul pe 12 luni?",
   "asteptat": {"tip": "cautare", "banci": ["libra"], "concept": "nominala", "categorie": "depozite", "termen": "12"}},
  {"intrebare": "What is ING's 6-month deposit rate?",
   "asteptat": {"tip": "cautare", "banci": ["ing"], "concept": "nominala", "categorie": "depozite", "termen": "6"}},
  {"intrebare": "Cât costă un transfer în lei către altă bancă la BT?",
   "asteptat": {"tip": "cautare", "banci": ["banca-transilvania"], "concept": "transfer_credit"}},
  {"intrebare": "Ce DAE are BCR la creditul ipotecar?",
   "asteptat": {"tip": "cautare", "banci": ["bcr"], "concept": "dae", "categorie": "credite", "produs_credit": "ipotecar"}},
  {"intrebare": "How much does Revolut charge to replace a card?",
   "asteptat": {"tip": "cautare", "banci": ["revolut"], "concept": "reemitere_card"}},
  {"intrebare": "Cât costă schimbarea PIN-ului la Garanti?",
   "asteptat": {"tip": "cautare", "banci": ["garanti"], "concept": "schimbare_pin"}},
  {"intrebare": "Comisionul de închidere a contului la CEC?",
   "asteptat": {"tip": "cautare", "banci": ["cec"], "concept": "inchidere_cont"}},
  {"intrebare": "Cât costă alertele SMS la BCR?",
   "asteptat": {"tip": "cautare", "banci": ["bcr"], "concept": "alerta_sms"}},
  {"intrebare": "Ce comision are UniCredit la depunerea de numerar?",
   "asteptat": {"tip": "cautare", "banci": ["unicredit"], "concept": "depunere_numerar"}},
  {"intrebare": "Cât costă interogarea soldului la ATM la Patria Bank?",
   "asteptat": {"tip": "cautare", "banci": ["patria"], "concept": "interogare_sold"}},
  {"intrebare": "What does BRD charge for an incoming payment?",
   "asteptat": {"tip": "cautare", "banci": ["brd"], "concept": "incasare"}},
  {"intrebare": "Cât costă administrarea contului la BCR și la BRD?",
   "asteptat": {"tip": "cautare", "banci": ["bcr", "brd"], "concept": "administrare_cont"}},
  {"intrebare": "și la BRD?",
   "anterior": {"tip": "cautare", "banci": ["bcr"], "concept": "administrare_cont", "categorie": null, "termen": null, "produs_credit": null, "text_cautat": null, "clarificare": null},
   "asteptat": {"tip": "cautare", "banci": ["brd"], "concept": "administrare_cont"}},
  {"intrebare": "dar pe 6 luni?",
   "anterior": {"tip": "cautare", "banci": ["libra"], "concept": "nominala", "categorie": "depozite", "termen": "12", "produs_credit": null, "text_cautat": null, "clarificare": null},
   "asteptat": {"tip": "cautare", "banci": ["libra"], "concept": "nominala", "categorie": "depozite", "termen": "6"}},
  {"intrebare": "Cât e dobânda la creditul de nevoi personale la Raiffeisen?",
   "asteptat": {"tip": "cautare", "banci": ["raiffeisen"], "categorie": "credite", "produs_credit": "nevoi_personale"}},
  {"intrebare": "Cât costă decontarea electronică a datoriei vamale la BCR?",
   "asteptat": {"tip": "cautare", "banci": ["bcr"]}},
  {"intrebare": "Cât costă abonamentul TrezoNet la BCR?",
   "asteptat": {"tip": "cautare", "banci": ["bcr"]}},
  {"intrebare": "Care bancă are cel mai mic comision de administrare?",
   "asteptat": {"tip": "in_afara"}},
  {"intrebare": "Ce notă are aplicația Libra în App Store?",
   "asteptat": {"tip": "in_afara"}},
  {"intrebare": "Scrie-mi un e-mail pentru un client nemulțumit.",
   "asteptat": {"tip": "in_afara"}},
  {"intrebare": "Cât costă administrarea contului?",
   "asteptat": {"tip": "neclar"}}
]
```

Ultimele două căutări (datoria vamală, TrezoNet) cer doar banca. Modelul poate alege corect fie
căutarea după text, fie un concept apropiat (`administrare_banking_distanta` la TrezoNet).

- [ ] **Pasul 7.2: scriptul de evaluare**

Creează `app/eval_intreaba.py`:

```python
"""Evaluarea interpretării din „Întreabă datele”: întrebări reale, cu interpretarea așteptată
(app/intreaba_exemple.json). Compară doar câmpurile scrise în `asteptat`.

Fiecare întrebare e un apel real la model, deci costă. Fără `--da`, scriptul arată doar câte
întrebări sunt și estimarea. Contextul (băncile, conceptele) vine din baza din MIP_DSN, ca la
server; valorile nu se caută (evaluarea e doar a interpretării), iar jurnalul merge într-un
director temporar, nu în loguri/intreaba/.

Rulare:  python app/eval_intreaba.py          # estimarea, fără niciun apel
         python app/eval_intreaba.py --da     # apelurile reale
"""

import argparse
import json
import os
import sys
import tempfile

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AICI)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import intreaba  # noqa: E402
import server  # noqa: E402  (funcțiile de citire din bază)

# estimat, nemăsurat: ~8.000 de tokeni de intrare la $1/M plus ieșirea, la Haiku 4.5, fără cache;
# după prima rulare, înlocuiește-l cu costul mediu măsurat
COST_ESTIMAT = 0.01


def potriveste(asteptat, primit):
    gresite = []
    for k, v in asteptat.items():
        if k == "text_cautat_nenul":
            if bool(primit.get("text_cautat")) != v:
                gresite.append(k)
        elif k == "banci":
            if sorted(primit.get("banci") or []) != sorted(v):
                gresite.append(k)
        elif primit.get(k) != v:
            gresite.append(k)
    return gresite


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--da", action="store_true", help="fă apelurile reale (costă)")
    a = p.parse_args()
    with open(os.path.join(AICI, "intreaba_exemple.json"), encoding="utf-8") as f:
        exemple = json.load(f)
    print(f"{len(exemple)} întrebări, model {intreaba.model()}, cost estimat ~${len(exemple) * COST_ESTIMAT:.2f}")
    if not a.da:
        print("Fără --da nu se face niciun apel.")
        return 0
    if not intreaba.cheie_reala():
        print("ANTHROPIC_API_KEY din .env nu e o cheie reală.")
        return 2
    q = intreaba.Intrebari(context=server._context_intrebari, cauta=lambda *x: [],
                           stare_banca=lambda b: None, dir_jurnal=tempfile.mkdtemp(prefix="eval_intreaba_"))
    corecte, cost, intrare = 0, 0.0, 0
    for i, e in enumerate(exemple, 1):
        d = q.intreaba(e["intrebare"], e.get("anterior"))
        gresite = potriveste(e["asteptat"], d["interpretare"])
        corecte += not gresite
        cost += d["cost_usd"] or 0
        intrare += d["tokeni"]["intrare"] + d["tokeni"]["citire_cache"] + d["tokeni"]["scriere_cache"]
        print(f"{i:>2}. {'✓' if not gresite else '✗ ' + ', '.join(gresite)}  {e['intrebare']}")
        if gresite:
            print("    primit:", json.dumps(d["interpretare"], ensure_ascii=False))
    print(f"\n{corecte}/{len(exemple)} corecte · cost ${cost:.4f} (${cost / len(exemple):.4f} pe întrebare)"
          f" · {intrare // len(exemple)} tokeni de intrare pe întrebare")
    return 0 if corecte == len(exemple) else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Pasul 7.3: rulează fără apeluri**

Rulează: `python app/eval_intreaba.py`
Aștepți: `25 întrebări, model claude-haiku-4-5, cost estimat ~$0.25`, apoi
`Fără --da nu se face niciun apel.`

- [ ] **Pasul 7.4: rulează evaluarea reală, cu acordul lui Nicolae**

**Arată-i lui Nicolae estimarea de la pasul 7.3 și așteaptă acordul.** Apoi rulează:
`python app/eval_intreaba.py --da`.
Aștepți: 25 de rânduri ✓/✗ și ultima linie cu corecte, cost și tokeni. Copiază ultima linie.
Pentru fiecare ✗, uită-te la `primit`:
- dacă interpretarea modelului e corectă și așteptarea greșită, corectezi exemplul și scrii motivul
  în mesajul commit-ului;
- dacă modelul greșește, **nu** schimba exemplul. Scrii eșecul în README (pasul 7.5).

Înlocuiește `COST_ESTIMAT` din script cu costul mediu măsurat pe întrebare și schimbă
comentariul în „măsurat pe <data>”.

- [ ] **Pasul 7.5: README**

În `README.md`, după secțiunea „### Rulări manuale (pagina „Rulare manuală”)” (înainte de
„### Pachetul Playwright (`crawler/`)”), adaugă secțiunea de mai jos. Valorile dintre `<…>` vin
din ce ai măsurat: lungimea promptului de la pasul 3.7, tokenii și costul de la pasul 6.6 și
ultima linie de la pasul 7.4. Data e cea a măsurătorii.

```markdown
### Întreabă datele (pagina `#/intreaba`)

O întrebare despre **o valoare** a unei bănci („Cât costă administrarea contului la BCR?”), în
română sau engleză. Modelul (`app/intreaba.py`) doar traduce întrebarea în banca, conceptul,
categoria și termenul căutat, cu schemă strictă; valorile, citatele și documentele vin din
`observatii_curente` prin `celula()`, ca Sertar-ul din 2.1. Modelul nu vede nicio valoare și nu
scrie nicio cifră. Ce n-are concept (găleata `comision`) se caută după text în denumirile
băncii și apare marcat „căutare după text”. Comparațiile, aplicațiile și campaniile nu intră:
pagina răspunde că sunt în afara ei.

- Activă **doar local**: `MIP_PERMITE_INTREBARI=1` și cheia reală `ANTHROPIC_API_KEY` în `.env`,
  apoi repornește serverul. Pe `mcc-test` rămâne oprită: serverul n-are încă autentificare.
- Modelul: `claude-haiku-4-5` (`MIP_INTREABA_MODEL`). Măsurat pe <data>: promptul de sistem are
  <caractere> de caractere, adică <tokeni> tokeni de intrare pe întrebare. Costul e <cost> la prima
  întrebare și <cost cu cache> după, cu promptul în cache.
- Evaluarea interpretării (`python app/eval_intreaba.py --da`, 25 de întrebări reale): <corecte>
  din 25 corecte pe <data>, $<cost total>. <Ce a greșit, dacă a greșit ceva.>
- Lista băncilor și a conceptelor se citește din bază la prima întrebare. După o încărcare de date
  nouă, repornește serverul.
- Conversația nu se salvează și nu intră în adresă: un link deschis ar porni un apel plătit.
  Jurnalul întrebărilor e local, în `loguri/intreaba/AAAA-LL.jsonl`.
- Teste fără rețea: `python app/test_intreaba.py`.
```

În secțiunea „## Structură” din README, înlocuiește
`app/          server.py (API read-only) · rulari.py (rulările manuale) · index.html (SPA, 12 pagini)` cu
`app/          server.py (API read-only) · rulari.py (rulările manuale) · intreaba.py (Întreabă datele) · index.html (SPA, 12 pagini)`.

- [ ] **Pasul 7.6: CLAUDE.md**

În `CLAUDE.md`, la paragraful „**Serverul e read-only.**”, după fraza care se termină cu
„…(Host/Origin/token, un proces odată); nu slăbi verificările.”, adaugă:

```
Tot cu o variabilă, `MIP_PERMITE_INTREBARI=1` (și o cheie reală), `POST /api/intreaba` cheamă
modelul doar ca să interpreteze întrebarea (`app/intreaba.py`): nu scrie în bază, iar cifrele vin
din bază, niciodată de la model.
```

- [ ] **Pasul 7.7: verificările finale**

Rulează:
```bash
python app/test_intreaba.py && python app/test_rulari.py && npm run typecheck && npm run build
```
Aștepți: `OK`, `OK`, 0 erori, build reușit. Cu serverul pornit, rulează și
`python app/verifica_pagini.py`. Aștepți: toate paginile randate.

- [ ] **Pasul 7.8: commit**

```bash
git add app/intreaba_exemple.json app/eval_intreaba.py README.md CLAUDE.md
git commit -m "app, docs: evaluarea „Întreabă datele” pe 25 de întrebări reale și cifrele măsurate în README"
```

- [ ] **Pasul 7.9: memoriile Serena**

Rulează skill-ul `/actualizeaza-memoria`. Se schimbă cel puțin:
- `cod/harta`: `app/intreaba.py`, rutele `/api/intreaba`, `celula` cu `text`, `shared/src/celula.ts`;
- `web/sectiune_noua`: `apiPostValidat`; `ValoareDovada` se importă din `./celula` în `shared/`;
- `stare/ultima_actualizare`.

Commit-ul memoriilor e separat, ca în istoricul repo-ului: `serena: …`.
