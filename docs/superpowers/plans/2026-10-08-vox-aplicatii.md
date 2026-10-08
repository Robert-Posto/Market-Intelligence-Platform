# Vox: aplicațiile băncilor (funcțiile și notele) — planul de implementare

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Vox răspunde la întrebările despre aplicațiile băncilor: funcțiile din analiza Android (verdict, dovadă), notele din App Store și Google Play, clasamentul notelor fără prag, cu întrebarea despre prag. Tipul nou se numește `aplicatii`, iar modelul nu scrie nicio cifră.

**Architecture:**
- **`app/vox.py`:** contractul (`TIPURI`, `CHEI` plus `functie` / `aspect` / `prag_note`, schema, `valideaza`) și regulile pure (`clasa_note`, `putine_note`, `diferente`, butoanele).
- **Serverul:** dă contextul (`functii`, `aplicatii`) și cititorul `_aplicatii_vox`, care citește din bază și din `date/google_play.json`.
- **`Vox._aplicatii_raspuns`:** construiește una din cele patru vederi.
- **Interfața:** `web/src/pages/vox/Aplicatii.tsx`, chemată din `Raspuns`, cu componentele și textele paginii Android.

**Tech Stack:** Python 3.12 (`unittest`, psycopg2), Anthropic SDK (Haiku 4.5), React 18 + AntD 5 + Zod, Playwright (Edge).

**Spec:** `docs/superpowers/specs/2026-10-08-vox-aplicatii-design.md`

**`S`** e dosarul temporar al sesiunii; în Git Bash:
`S="C:/Users/NICOLA~1.CHE/AppData/Local/Temp/claude/c--Users-nicolae-cherascu-Desktop-Market-Intelligence-Platform/2a9027a5-dce6-4121-9bd5-057bfc4e8009/scratchpad"`.
`python` e interpretorul din `.venv`, activ în Git Bash.

**Decizii luate la scrierea planului** (spec-ul rămâne autoritatea):
- **Numele câmpului de evidențiere** e `evidentiata`, ca în `vox.clasa` și în `RandClasament`. Spec-ul scria `evidentiat`.
- **Aplicațiile fără notă** stau în lista separată `fara_nota`, nu la finalul lui `randuri`, pentru că rândurile din `randuri` au mereu loc (Zod). Azi nu există niciuna.
- **Un `prag_note` invalid se ignoră** (devine `null`): bool, text, zecimal, sub 1 sau peste 100.000.000. Nu face interpretarea `neclar`, pentru că pragul rafinează întrebarea, nu-i schimbă sensul.
- **Nota despre prag ocolește acordul cu „de”**, ca să nu apară „cu doar 26 note”: „În App Store, ProCredit Bank e pe locul 1, cu un număr mic de note: 6. Aplicații cu sub 100 de note: 7 în App Store, 3 în Google Play. Ce prag vrei să pui?”. Din același motiv, numerele apar după două puncte („aplicații: 22”, „note: 3.083”).
- **`putine_note` primește și `prag`** (100), ca fișa să nu scrie cifra de mână.
- **`din_buton` tratează explicit fiecare buton.** Cu cheile noi în `BUTOANE`, ramura de azi ar fi adăugat Libra la un `toate` trimis pe o căutare.
- **Fără cititor de aplicații** (evaluarea), răspunsul are `aplicatii: null`, iar fișa spune „Datele despre aplicații nu sunt disponibile.”.
- **Clasamentele de note** arată primele 10 rânduri, plus Libra și băncile numite, cu „Arată toate” pentru rest, ca `Clasament.tsx`.

## Global Constraints

- **Apelurile plătite.** Niciunul fără „da” explicit de la Nicolae, cu costul spus înainte. Evaluarea (`eval_vox.py --da`, 53 de întrebări) se doar propune în Task 9, cu estimarea scriptului, și nu se rulează din plan.
- **Testele și verificările de interfață nu cheamă modelul.** Se folosesc `ClientFals`, un model fals în scripturi și `POST /api/vox` răspuns din fișier în Playwright.
- **Serverele lui Nicolae (:8765, :5173)** nu se opresc și nu se repornesc. :5173 e Vite-ul lui, cu HMR, și ia singur modificările din `web/`.
  - `npm run build` nu se rulează; build-ul de verificare merge în `"$S/dist_verif"`.
  - Serverul temporar e doar cel din `"$S/cu_server_8797.sh"`.
- **Serverul rămâne read-only.** Interogările noi n-au parametri veniți din cerere.
- **Valorile fixe:**
  - `TIPURI = ("cautare", "clasament", "aplicatii", "neclar", "in_afara")`;
  - `ASPECTE = ("functii", "note")`;
  - `PRAGURI_NOTE = (100, 1000)`, `PRAG_AVERTIZARE = 100`, `PRAG_NOTE_MAX = 100_000_000`;
  - `VERDICTE = ("sigur", "probabil", "absent", "neconcludent")`;
  - butoanele noi: `toate`, `prag_100`, `prag_1000`, `fara_prag`.
- **Regula notei:** rotunjită la o zecimală, cu `ROUND_HALF_UP` pe valoarea din sursă (4,65 → 4,7). La aceeași notă rotunjită, loc comun, în ordinea numelui băncii. Fără prag implicit.
- **Codul și textele:**
  - identificatorii sunt în română, fără diacritice;
  - textele trec prin `t`, ca perechi `[română, engleză]`; datele băncilor nu se traduc;
  - niciun pachet nou.
- **Comentariile și commit-urile.** Un comentariu spune de ce, cu cifra măsurată (`mip_merge`, 08.10.2026). Commit-urile au forma „zonă: ce și de ce”, fără `Co-Authored-By`, și se fac cu `git commit -F "$S/mesaj.txt"`.
- **CRLF.** `app/server.py`, `app/vox.py` și `app/test_vox.py` au CRLF: după editare, `git diff --stat` trebuie să arate doar liniile schimbate. După orice editare cu `\uXXXX`, caută U+0300–U+036F în fișier.
- **Rularea.** Scripturile Python merg cu `PYTHONIOENCODING=utf-8 python`, din rădăcina repo-ului. Nu se citește `.env`.

## Review Focus

1. **Fișierul Google Play lipsește sau e stricat** (alt laptop, `mcc-test`). Vox răspunde cu analiza și cu App Store, iar fișa spune „Google Play necolectat”, fără 500. Testele: `test_google_play_lipsa_sau_stricat` (Task 4) și `test_note_fara_google_play` (Task 5).
2. **O conversație salvată înainte** (interpretare fără `functie` / `aspect` / `prag_note`, răspuns fără `aplicatii`) se redeschide fără eroare Zod. Testele: `test_interpretare_veche_fara_campurile_noi` (Task 1) și redeschiderea conversației `35b2f7f797944207` în Playwright (Task 8).
3. **O bancă numită fără aplicație** („Ce funcții are aplicația PKO?”, „Ce notă are PKO?”) primește „fără aplicație analizată”, fără să cadă. Testele: `test_secundare_si_banca_fara_aplicatie`, `test_banca_fara_aplicatie` (Task 5) și cazul PKO din Task 8.
4. **Un client modificat trimite un buton nepotrivit** (`prag_100` sub funcții, `toate` fără bănci, `libra` cu 3 bănci, `toate` sub o căutare). Răspunsul e 400, nu 500 și nu un răspuns greșit. Testele: `test_din_buton_aplicatii_refuza` și `test_post_buton_aplicatii` (Task 6).
5. **Modelul scrie un prag ciudat** (text, zecimal, bool, negativ, uriaș). Se acceptă doar întregi între 1 și 100.000.000, iar restul se ignoră. Testul: `test_prag_note` (Task 1).

---

### Task 1: contractul interpretării (`app/vox.py`)

**Files:**
- Modify: `app/vox.py` (constantele de lângă `TIPURI` / `CHEI` / `METRICI`; `_gol`; `schema`; `valideaza`; `_aplicatii_curat` nou, după `valideaza`)
- Test: `app/test_vox.py` (`CTX`; `apl` nou, după `interp`; clasa nouă `ValidareAplicatii`, după `Validare`)

**Interfaces:**
- Produces: `vox.TIPURI` (cu `aplicatii`), `vox.CHEI` (cu `functie`, `aspect`, `prag_note`), `vox.ASPECTE`, `vox.PRAGURI_NOTE`, `vox.PRAG_AVERTIZARE`, `vox.PRAG_NOTE_MAX`; `vox._gol(tip)` are cele trei chei noi pe `None`; `vox.valideaza(brut, ctx)` cere `ctx["functii"] = [{"functie", "titlu"}]`; helper-ul de test `apl(**k)`.

- [ ] **Step 1: testele care pică**

În `app/test_vox.py`, `CTX` primește două chei noi, după `"clasabile"`:

```python
    "functii": [{"functie": "hce_contactless", "titlu": "Plată contactless direct din aplicație"},
                {"functie": "in_app_chat", "titlu": "Chat cu banca în aplicație"},
                {"functie": "ropay", "titlu": "RoPay (plăți instant din cont)"}],
    "aplicatii": [{"banca": "bcr", "aplicatie": "George Romania"}, {"banca": "brd", "aplicatie": "YOU BRD"},
                  {"banca": "brd", "aplicatie": "MyBRD Mobile"}, {"banca": "libra", "aplicatie": "Libra Bank"}],
```

Imediat după funcția `interp`:

```python
def apl(**k):
    """O interpretare de tip `aplicatii`, cu toate cheile din CHEI."""
    baza = dict(vox._gol("aplicatii"), banci=["bcr"], aspect="functii")
    baza.update(k)
    return baza
```

Imediat după clasa `Validare`:

```python
class ValidareAplicatii(unittest.TestCase):
    """Tipul `aplicatii` (decizia lui Nicolae, 08.10.2026): funcțiile din analiza Android sau notele din magazine."""

    def test_schema_are_campurile_noi(self):
        s = vox.schema(CTX)
        p = s["properties"]
        self.assertIn("aplicatii", p["tip"]["enum"])
        self.assertEqual(p["functie"]["anyOf"][0]["enum"], ["hce_contactless", "in_app_chat", "ropay"])
        self.assertEqual(p["aspect"]["anyOf"][0]["enum"], ["functii", "note"])
        self.assertEqual(p["prag_note"], {"anyOf": [{"type": "integer"}, {"type": "null"}]})
        self.assertEqual(sorted(s["required"]), sorted(vox.CHEI))

    def test_functie_fara_banci(self):
        i, _ = vox.valideaza(apl(banci=[], functie="ropay", aspect=None), CTX)
        self.assertEqual((i["tip"], i["functie"], i["aspect"], i["banci"]), ("aplicatii", "ropay", "functii", []))

    def test_functia_inseamna_functii(self):
        i, _ = vox.valideaza(apl(functie="ropay", aspect="note", prag_note=100), CTX)
        self.assertEqual((i["aspect"], i["prag_note"]), ("functii", None))

    def test_aspect_implicit(self):
        self.assertEqual(vox.valideaza(apl(aspect=None), CTX)[0]["aspect"], "functii")
        i, _ = vox.valideaza(apl(banci=[], aspect=None, text_cautat="Apple Pay"), CTX)
        self.assertEqual((i["tip"], i["aspect"], i["text_cautat"]), ("aplicatii", "functii", "Apple Pay"))

    def test_fara_nimic_e_neclar(self):
        i, _ = vox.valideaza(apl(banci=[], aspect=None), CTX)
        self.assertEqual((i["tip"], i["clarificare"]), ("neclar", None))

    def test_note_cu_si_fara_banci(self):
        self.assertEqual(vox.valideaza(apl(banci=[], aspect="note"), CTX)[0]["tip"], "aplicatii")
        self.assertEqual(vox.valideaza(apl(banci=["libra"], aspect="note"), CTX)[0]["banci"], ["libra"])

    def test_prag_note(self):
        """Un prag scris de model sau adus de un client modificat: doar întreg între 1 și 100.000.000, altfel se
        ignoră; pragul rafinează întrebarea, nu-i schimbă sensul."""
        self.assertEqual(vox.valideaza(apl(aspect="note", prag_note=1000), CTX)[0]["prag_note"], 1000)
        for rau in (True, "1000", 99.5, 0, -5, 10 ** 12, [100]):
            i, _ = vox.valideaza(apl(aspect="note", prag_note=rau), CTX)
            self.assertEqual((i["tip"], i["prag_note"]), ("aplicatii", None), rau)

    def test_campurile_comisioanelor_se_golesc(self):
        i, _ = vox.valideaza(apl(concept="administrare_cont", segment="pj", metrica="cea_mai_buna",
                                 clarificare="?"), CTX)
        self.assertEqual((i["concept"], i["segment"], i["metrica"], i["clarificare"]), (None, None, None, None))

    def test_alte_tipuri_golesc_campurile_noi(self):
        i, _ = vox.valideaza(dict(interp(), functie="ropay", aspect="note", prag_note=100), CTX)
        self.assertEqual((i["tip"], i["functie"], i["aspect"], i["prag_note"]), ("cautare", None, None, None))

    def test_functie_necunoscuta_e_neclar(self):
        self.assertEqual(vox.valideaza(apl(functie="apple_pay"), CTX)[0]["tip"], "neclar")

    def test_trei_banci(self):
        i, ignorate = vox.valideaza(apl(banci=["bcr", "brd", "ing", "libra"]), CTX)
        self.assertEqual((i["banci"], ignorate), (["bcr", "brd", "ing"], ["libra"]))

    def test_interpretare_veche_fara_campurile_noi(self):
        """Conversațiile salvate înainte de 08.10.2026 n-au `functie`, `aspect`, `prag_note`."""
        vechi = interp(segment=None, metrica=None)
        curat = vox.verifica_anterior(vechi)
        self.assertEqual((curat["functie"], curat["aspect"], curat["prag_note"]), (None, None, None))
        self.assertEqual(vox.valideaza(curat, CTX)[0]["tip"], "cautare")
```

- [ ] **Step 2: rulează și vezi că pică**

Run: `PYTHONIOENCODING=utf-8 python app/test_vox.py ValidareAplicatii`
Expected: FAIL (`KeyError: 'functie'` / `AttributeError: ... ASPECTE`).

- [ ] **Step 3: implementarea**

În `app/vox.py`, `TIPURI` și `CHEI` devin:

```python
TIPURI = ("cautare", "clasament", "aplicatii", "neclar", "in_afara")
CHEI = ("tip", "banci", "concept", "categorie", "termen", "produs_credit", "text_cautat", "clarificare",
        "segment", "metrica", "functie", "aspect", "prag_note")
```

După `METRICI = (...)`:

```python
# Aplicațiile (decizia lui Nicolae, 08.10.2026): funcțiile din analiza aplicațiilor Android sau notele din magazine
ASPECTE = ("functii", "note")
# Pragurile oferite ca butoane sub clasamentul notelor. Fără prag (decizia lui Nicolae, 08.10.2026), ProCredit iese
# primul în App Store cu 5,0 din 6 note (24.09.2026): sub cel mai mic prag, Vox spune asta și întreabă ce prag vrea
PRAGURI_NOTE = (100, 1000)
PRAG_AVERTIZARE = min(PRAGURI_NOTE)
# Revolut are 4.147.313 note în Google Play (06.10.2026); un prag peste atât nu mai lasă nimic de clasat
PRAG_NOTE_MAX = 100_000_000
```

`_gol` devine:

```python
def _gol(tip="neclar"):
    return {"tip": tip, "banci": [], "concept": None, "categorie": None, "termen": None,
            "produs_credit": None, "text_cautat": None, "clarificare": None, "segment": None, "metrica": None,
            "functie": None, "aspect": None, "prag_note": None}
```

În `schema`, după `"metrica": optional(METRICI),`:

```python
            "functie": optional(f["functie"] for f in ctx["functii"]),
            "aspect": optional(ASPECTE),
            "prag_note": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
```

În `valideaza`:
- `permise` primește două chei noi: `"functie": {f["functie"] for f in ctx["functii"]}, "aspect": set(ASPECTE)`.
- Imediat după blocul care golește `categorie` (`if curat["categorie"] not in categorii: curat["categorie"] = None`), înainte de `if curat["tip"] == "clasament":`:

```python
    if curat["tip"] == "aplicatii":
        return _aplicatii_curat(curat, brut.get("prag_note")), banci[MAX_BANCI:]
    curat["functie"] = curat["aspect"] = None
```

După funcția `valideaza`:

```python
def _aplicatii_curat(curat, prag):
    """`aplicatii` (decizia lui Nicolae, 08.10.2026): banca, funcția, aspectul și pragul; câmpurile comisioanelor
    n-au sens aici. Un prag invalid se ignoră: rafinează întrebarea, nu-i schimbă sensul."""
    for k in ("concept", "categorie", "termen", "produs_credit", "segment", "metrica", "clarificare"):
        curat[k] = None
    if curat["functie"]:
        curat["aspect"] = "functii"          # o funcție e mereu despre funcții, nu despre note
    elif curat["aspect"] is None and (curat["banci"] or curat["text_cautat"]):
        curat["aspect"] = "functii"
    valid = isinstance(prag, int) and not isinstance(prag, bool) and 1 <= prag <= PRAG_NOTE_MAX
    curat["prag_note"] = prag if valid and curat["aspect"] == "note" else None
    if curat["aspect"] is None:
        curat["tip"] = "neclar"              # fără funcție, aplicație sau note: pagina arată mesajul ei fix
    return curat
```

- [ ] **Step 4: rulează toate testele**

Run: `PYTHONIOENCODING=utf-8 python app/test_vox.py`
Expected: OK (cele 128 de dinainte și cele 12 noi).

- [ ] **Step 5: commit**

```bash
printf '%s\n' "app: Vox primește tipul aplicatii (funcție, aspect, prag de note), validat ca restul interpretării" > "$S/mesaj.txt"
git add app/vox.py app/test_vox.py && git commit -q -F "$S/mesaj.txt"
```

---

### Task 2: promptul (`app/vox.py`)

**Files:**
- Modify: `app/vox.py` (`prompt`)
- Test: `app/test_vox.py` (`Schema.test_prompt_contine_listele_si_regula`; `Schema.test_prompt_aplicatii`, nou)

**Interfaces:**
- Consumes: `ctx["functii"]`, `ctx["aplicatii"]` (Task 1 în teste, Task 4 în server).
- Produces: un prompt cu regula `tip = aplicatii` și cu listele „Funcțiile aplicațiilor” și „Aplicațiile”.

- [ ] **Step 1: testele care pică**

În `test_prompt_contine_listele_si_regula`, linia
`self.assertIn("(„care bancă are cea mai bună aplicație?”) rămân in_afara", text)` devine:

```python
        self.assertIn("cele despre aplicații („care bancă are cea mai bună aplicație?”) sunt aplicatii", text)
```

Metodă nouă în clasa `Schema`:

```python
    def test_prompt_aplicatii(self):
        text = vox.prompt(CTX)
        self.assertIn("tip = aplicatii", text)
        self.assertIn("Funcțiile aplicațiilor (slug: titlu): hce_contactless: Plată contactless direct din aplicație; "
                      "in_app_chat: Chat cu banca în aplicație; ropay: RoPay (plăți instant din cont)", text)
        self.assertIn("Aplicațiile (bancă: nume): bcr: George Romania; brd: YOU BRD; brd: MyBRD Mobile; "
                      "libra: Libra Bank", text)
        self.assertIn("(„Apple Pay”) → functie = null și numele ei în text_cautat", text)
        self.assertIn("(„cu cel puțin 1.000 de note” → 1000)", text)
        self.assertIn("recenziile aplicațiilor, trackere, permisiuni, campanii", text)
        self.assertNotIn("(aplicații, recenzii, campanii", text)
```

- [ ] **Step 2: rulează și vezi că pică**

Run: `PYTHONIOENCODING=utf-8 python app/test_vox.py Schema`
Expected: FAIL (textele noi lipsesc).

- [ ] **Step 3: implementarea**

În `prompt`:

1. A doua linie din `linii` devine:

```python
        "Utilizatorul întreabă, în română sau în engleză, despre o valoare publicată de o bancă din "
        "România (un comision, o dobândă, o limită) sau compară băncile între ele pe o astfel de valoare. "
        "Poate întreba și despre aplicațiile mobile ale băncilor: funcțiile găsite în analiza aplicațiilor "
        "Android și notele din magazine (Google Play, App Store).",
```

2. În regula cu „care bancă…”, fragmentul
`"o dobândă) sunt întotdeauna clasament; cele despre aplicații, recenzii sau campanii („care bancă are "`
`"cea mai bună aplicație?”) rămân in_afara. "`
devine:

```python
        "o dobândă) sunt întotdeauna clasament; cele despre aplicații („care bancă are cea mai bună "
        "aplicație?”) sunt aplicatii, iar cele despre recenzii sau campanii rămân in_afara. "
```

3. Înaintea regulii `"- tip = neclar: ..."`, regula nouă:

```python
        "- tip = aplicatii: întrebarea e despre aplicația mobilă a unei bănci: ce funcții are („Are George "
        "RoPay?”, „Ce funcții are aplicația BRD?”, „Ce bănci au plata cu telefonul?”, „Ce are BT Pay și n-are "
        "Libra?”) sau ce notă are în magazine („Ce notă are aplicația Libra?”, „Care bancă are cea mai bună "
        "aplicație?”). banci = băncile numite sau ale aplicațiilor numite (lista „Aplicațiile” de la final: "
        "„George” → bcr), altfel []. functie = funcția din lista „Funcțiile aplicațiilor”, dacă întrebarea "
        "numește una; o funcție care nu e în listă („Apple Pay”) → functie = null și numele ei în text_cautat. "
        "aspect = note pentru note și clasamentul lor („cea mai bună aplicație” = cea mai bună notă), altfel "
        "functii. prag_note = numărul minim de note, doar dacă întrebarea îl cere („cu cel puțin 1.000 de "
        "note” → 1000), altfel null. La aplicatii, concept, categorie, termen, produs_credit, segment și "
        "metrica sunt null.",
```

4. Regula `in_afara` devine:

```python
        "- tip = in_afara: orice altceva (recenziile aplicațiilor, trackere, permisiuni, campanii, sfaturi, "
        "texte de scris, întrebări generale).",
```

5. Înainte de `return "\n".join(linii)`:

```python
    linii += [
        "Funcțiile aplicațiilor (slug: titlu): " + "; ".join(f"{f['functie']}: {f['titlu']}" for f in ctx["functii"]),
        "Aplicațiile (bancă: nume): " + "; ".join(f"{a['banca']}: {a['aplicatie']}" for a in ctx["aplicatii"]),
    ]
```

- [ ] **Step 4: rulează toate testele**

Run: `PYTHONIOENCODING=utf-8 python app/test_vox.py`
Expected: OK.

- [ ] **Step 5: commit**

```bash
printf '%s\n' "app: promptul Vox știe de aplicații: funcțiile, numele aplicațiilor și pragul de note" > "$S/mesaj.txt"
git add app/vox.py app/test_vox.py && git commit -q -F "$S/mesaj.txt"
```

---

### Task 3: regulile pure — notele și diferențele (`app/vox.py`)

**Files:**
- Modify: `app/vox.py` (importul `decimal`; `VERDICTE`, `ARE`, `_nota_zecimala`, `clasa_note`, `putine_note`, `diferente`, după `clasa`)
- Test: `app/test_vox.py` (`nota`, `NUME`, `coloana` și clasele `Note`, `Diferente`, după clasa `Clasa`)

**Interfaces:**
- Produces:
  - `vox.clasa_note(randuri, evidentiate, nume, prag=None) -> {"randuri", "sub_prag", "fara_nota"}`, unde `randuri` primesc `nota_afisata`, `evidentiata`, `loc`, `loc_pana`;
  - `vox.putine_note(clasamente) -> None | {"app_store": n, "play": n, "prag": 100, "primul": {magazin, banca, loc, loc_pana, evaluari}}`;
  - `vox.diferente(coloane) -> [{"functie", "nivel", "au", "n_au"}]`;
  - `vox.VERDICTE`.

- [ ] **Step 1: testele care pică**

```python
def nota(banca, valoare, evaluari, **k):
    return {"banca": banca, "nota": valoare, "evaluari": evaluari, **k}


NUME = {"bcr": "BCR", "brd": "BRD — Groupe Société Générale", "ing": "ING Bank", "libra": "Libra Internet Bank",
        "procredit": "ProCredit Bank", "revolut": "Revolut"}


class Note(unittest.TestCase):
    """Clasamentul notelor (decizia lui Nicolae, 08.10.2026): fără prag, loc comun la aceeași notă cu o zecimală."""

    def test_loc_comun_in_ordinea_numelui(self):
        """BRD 4,83, BCR 4,81 și ING 4,79 au toate 4,8 în Google Play (06.10.2026): locurile 1–3, după nume."""
        c = vox.clasa_note([nota("ing", 4.79, 182106), nota("brd", 4.83, 234221), nota("bcr", 4.81, 155826),
                            nota("libra", 4.59, 3083)], {"libra"}, NUME)
        self.assertEqual([(r["banca"], r["loc"], r["loc_pana"], r["nota_afisata"]) for r in c["randuri"]],
                         [("bcr", 1, 3, 4.8), ("brd", 1, 3, 4.8), ("ing", 1, 3, 4.8), ("libra", 4, 4, 4.6)])
        self.assertEqual([r["evidentiata"] for r in c["randuri"]], [False, False, False, True])
        self.assertEqual((c["sub_prag"], c["fara_nota"]), ([], []))

    def test_rotunjire_in_sus_de_la_cinci(self):
        """`round(4.25, 1)` dă 4,2 (rotunjire la par); magazinul arată 4,3. TBI are 4,65 în Google Play: 4,7."""
        c = vox.clasa_note([nota("ing", 4.25, 10), nota("bcr", 4.65, 10)], set(), NUME)
        self.assertEqual([(r["banca"], r["nota_afisata"]) for r in c["randuri"]], [("bcr", 4.7), ("ing", 4.3)])

    def test_fara_prag_toate_clasate(self):
        """În App Store, ProCredit e pe locul 1 cu 5,0 din 6 note (24.09.2026): fără prag, rămâne acolo."""
        c = vox.clasa_note([nota("procredit", 5.0, 6), nota("revolut", 4.91, 332368)], set(), NUME)
        self.assertEqual([(r["banca"], r["loc"]) for r in c["randuri"]], [("procredit", 1), ("revolut", 2)])

    def test_cu_prag_sub_prag_separat(self):
        c = vox.clasa_note([nota("procredit", 5.0, 6), nota("revolut", 4.91, 332368), nota("libra", 4.47, 971)],
                           {"libra"}, NUME, prag=1000)
        self.assertEqual([(r["banca"], r["loc"]) for r in c["randuri"]], [("revolut", 1)])
        self.assertEqual([(r["banca"], r["evidentiata"]) for r in c["sub_prag"]],
                         [("libra", True), ("procredit", False)])
        self.assertNotIn("loc", c["sub_prag"][0])

    def test_fara_nota_la_final(self):
        c = vox.clasa_note([nota("bcr", None, 0), nota("ing", 4.0, 5)], set(), NUME)
        self.assertEqual([r["banca"] for r in c["randuri"]], ["ing"])
        self.assertEqual([(r["banca"], r["nota_afisata"]) for r in c["fara_nota"]], [("bcr", None)])

    def test_putine_note(self):
        play = vox.clasa_note([nota("bcr", 4.81, 155826), nota("procredit", 2.5, 16)], set(), NUME)
        ios = vox.clasa_note([nota("procredit", 5.0, 6), nota("ing", 4.85, 125858), nota("brd", 4.0, 4)], set(), NUME)
        self.assertEqual(vox.putine_note({"play": play, "app_store": ios}),
                         {"app_store": 2, "play": 1, "prag": 100,
                          "primul": {"magazin": "app_store", "banca": "procredit", "loc": 1, "loc_pana": 1, "evaluari": 6}})

    def test_putine_note_nimic_sau_fara_magazin(self):
        play = vox.clasa_note([nota("bcr", 4.81, 155826)], set(), NUME)
        self.assertIsNone(vox.putine_note({"play": play, "app_store": None}))


def coloana(banca, **verdicte):
    return {"banca": banca, "fara_aplicatie": False,
            "functii": {f: {"verdict": v, "surse": [], "dovada_text": None} for f, v in verdicte.items()}}


class Diferente(unittest.TestCase):
    """Diferențele pe două niveluri (decizia lui Nicolae, 08.10.2026)."""

    def test_bt_pay_si_libra(self):
        """BT Pay vs Libra (mip_merge, 08.10.2026): RoPay sigură; chatul, marketingul și asistentul vocal, probabile;
        Huawei și Google Wallet le au amândouă („sigur” / „probabil”), deci nu sunt diferențe."""
        bt = coloana("banca-transilvania", ropay="sigur", in_app_chat="probabil", marketing="probabil",
                     voice="absent", huawei="probabil", wallet_provisioning="sigur")
        libra = coloana("libra", ropay="absent", in_app_chat="absent", marketing="absent",
                        voice="probabil", huawei="sigur", wallet_provisioning="probabil")
        self.assertEqual([(x["functie"], x["nivel"], x["au"], x["n_au"]) for x in vox.diferente([bt, libra])],
                         [("in_app_chat", "probabil", ["banca-transilvania"], ["libra"]),
                          ("marketing", "probabil", ["banca-transilvania"], ["libra"]),
                          ("ropay", "sigur", ["banca-transilvania"], ["libra"]),
                          ("voice", "probabil", ["libra"], ["banca-transilvania"])])

    def test_neconcludent_nu_intra(self):
        self.assertEqual(vox.diferente([coloana("bcr", ropay="sigur"), coloana("brci", ropay="neconcludent")]), [])

    def test_trei_aplicatii_nivel_dupa_cea_sigura(self):
        d = vox.diferente([coloana("bcr", ropay="probabil"), coloana("brd", ropay="sigur"),
                           coloana("libra", ropay="absent")])
        self.assertEqual(d, [{"functie": "ropay", "nivel": "sigur", "au": ["bcr", "brd"], "n_au": ["libra"]}])

    def test_banca_fara_aplicatie_nu_intra(self):
        d = vox.diferente([coloana("bcr", ropay="sigur"), {"banca": "pko", "fara_aplicatie": True, "functii": {}}])
        self.assertEqual(d, [])
```

- [ ] **Step 2: rulează și vezi că pică**

Run: `PYTHONIOENCODING=utf-8 python app/test_vox.py Note Diferente`
Expected: FAIL (`AttributeError: module 'vox' has no attribute 'clasa_note'`).

- [ ] **Step 3: implementarea**

Importul, lângă celelalte: `from decimal import ROUND_HALF_UP, Decimal`.

După funcția `clasa`:

```python
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
```

- [ ] **Step 4: rulează toate testele**

Run: `PYTHONIOENCODING=utf-8 python app/test_vox.py`
Expected: OK.

- [ ] **Step 5: commit**

```bash
printf '%s\n' "app: clasamentul notelor fără prag, nota despre aplicațiile cu puține note și diferențele pe două niveluri" > "$S/mesaj.txt"
git add app/vox.py app/test_vox.py && git commit -q -F "$S/mesaj.txt"
```

---

### Task 4: serverul — contextul și cititorul (`app/server.py`)

**Files:**
- Modify: `app/server.py` (`_context_vox`; `FISIER_GOOGLE_PLAY`, `_google_play`, `_aplicatii_vox`, noi, după `_stare_banci_vox`)
- Test: `app/test_vox.py` (clasa nouă `CititoriAplicatii`, după `CititoriClasament`)

**Interfaces:**
- Produces:
  - `_context_vox()` primește `functii: [{functie, titlu}]` și `aplicatii: [{banca, aplicatie}]`;
  - `server._aplicatii_vox() -> {"aplicatii": [{banca, package, aplicatie, rol, versiune_analizata, framework, data_analizei}], "functii": [{package, functie, verdict, surse, dovada_text}], "app_store": [{banca, app_id, nota, evaluari, distributie_stele, versiune, observat_la}], "play": None | {"colectat_la", "aplicatii": {slug: {...}}}}`;
  - `server._google_play()` și `server.FISIER_GOOGLE_PLAY`.

- [ ] **Step 1: testele care pică**

```python
class CititoriAplicatii(unittest.TestCase):
    """Cititorii din server pentru aplicații: contextul promptului, analiza APK, App Store, Google Play."""

    def setUp(self):
        import server
        self.s = server
        self.vechi = (server.interoghează, server.FISIER_GOOGLE_PLAY)
        self.dir = tempfile.mkdtemp(prefix="vox_play_")

    def tearDown(self):
        self.s.interoghează, self.s.FISIER_GOOGLE_PLAY = self.vechi

    def baza(self, sql, params=None):
        if "SELECT functie, min(titlu)" in sql:
            return [{"functie": "ropay", "titlu": "RoPay (plăți instant din cont)"}]
        if "SELECT b.slug AS banca, a.aplicatie FROM" in sql:
            return [{"banca": "bcr", "aplicatie": "George Romania"}]
        if "FROM android_aplicatii" in sql:
            return [{"banca": "bcr", "package": "ro.bcr.georgego", "aplicatie": "George Romania", "rol": "principal",
                     "versiune_analizata": "1.0", "framework": "nativ", "data_analizei": "2026-10-01"}]
        if "FROM android_functionalitati" in sql:
            return [{"package": "ro.bcr.georgego", "functie": "ropay", "verdict": "sigur", "surse": "cod|text",
                     "dovada_text": "RoPay"}]
        if "FROM app_release_curente" in sql:
            return [{"banca": "bcr", "app_id": "123", "nota": 4.84, "evaluari": 188573,
                     "distributie_stele": [1, 0, 0, 0, 0], "versiune": "26.30", "observat_la": "2026-09-24"}]
        return []

    def play(self, continut):
        cale = os.path.join(self.dir, "google_play.json")
        with open(cale, "w", encoding="utf-8") as f:
            f.write(continut)
        self.s.FISIER_GOOGLE_PLAY = cale

    def test_context_functii_si_aplicatii(self):
        self.s.interoghează = self.baza
        ctx = self.s._context_vox()
        self.assertEqual(ctx["functii"], [{"functie": "ropay", "titlu": "RoPay (plăți instant din cont)"}])
        self.assertEqual(ctx["aplicatii"], [{"banca": "bcr", "aplicatie": "George Romania"}])

    def test_aplicatii_din_baza_si_fisier(self):
        self.s.interoghează = self.baza
        self.play(json.dumps({"colectat_la": "2026-10-06T09:39:43Z",
                              "aplicatii": {"bcr": {"nota": 4.81, "evaluari": 155826}}}))
        d = self.s._aplicatii_vox()
        self.assertEqual(d["aplicatii"][0]["package"], "ro.bcr.georgego")
        self.assertEqual(d["functii"][0]["verdict"], "sigur")
        self.assertEqual(d["app_store"][0]["nota"], 4.84)
        self.assertEqual(d["play"], {"colectat_la": "2026-10-06", "aplicatii": {"bcr": {"nota": 4.81, "evaluari": 155826}}})

    def test_google_play_lipsa_sau_stricat(self):
        """`date/google_play.json` e în afara git: lipsește pe alt laptop și pe mcc-test; Vox merge fără el."""
        self.s.FISIER_GOOGLE_PLAY = os.path.join(self.dir, "nu_exista.json")
        self.assertIsNone(self.s._google_play())
        for stricat in ("{", "[]", json.dumps({"colectat_la": "2026-10-06"}), json.dumps({"aplicatii": []})):
            self.play(stricat)
            self.assertIsNone(self.s._google_play(), stricat)
```

- [ ] **Step 2: rulează și vezi că pică**

Run: `PYTHONIOENCODING=utf-8 python app/test_vox.py CititoriAplicatii`
Expected: FAIL (`AttributeError: ... FISIER_GOOGLE_PLAY`).

- [ ] **Step 3: implementarea**

În `_context_vox`, înainte de `return`:

```python
    # aplicațiile (decizia lui Nicolae, 08.10.2026): titlurile funcțiilor și numele aplicațiilor vin din bază, ca
    # modelul să lege „George” de BCR și „plata cu telefonul” de `hce_contactless` fără să dublăm etichetele paginii
    functii = interoghează(
        "SELECT functie, min(titlu) AS titlu FROM android_functionalitati GROUP BY functie ORDER BY functie")
    aplicatii = interoghează(
        """SELECT b.slug AS banca, a.aplicatie FROM android_aplicatii a JOIN banci b ON b.id = a.id_banca
           ORDER BY b.slug, (a.rol = 'secundar'), a.aplicatie""")
```

iar în dicționarul întors, după `"clasabile": {...},`: `"functii": functii, "aplicatii": aplicatii,`.
Prima frază din docstring devine „Băncile, conceptele și aplicațiile pe care le vede modelul din Vox.”.

După `_stare_banci_vox`:

```python
# Notele din Google Play (ingest/google_play_app.mjs), același fișier pe care 2.3 îl citește la build. Nu e în bază
# și e în afara git (`date/*.json`): pe alt laptop sau pe mcc-test lipsește, iar Vox merge fără el
FISIER_GOOGLE_PLAY = os.path.join(os.path.dirname(AICI), "date", "google_play.json")


def _google_play():
    """{colectat_la, aplicatii: {slug: {...}}} sau None dacă fișierul lipsește ori nu are forma așteptată."""
    try:
        with open(FISIER_GOOGLE_PLAY, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(d, dict) or not isinstance(d.get("aplicatii"), dict):
        return None
    return {"colectat_la": str(d.get("colectat_la") or "")[:10] or None, "aplicatii": d["aplicatii"]}


def _aplicatii_vox():
    """Aplicațiile băncilor pentru Vox (decizia lui Nicolae, 08.10.2026): analiza APK (funcțiile, cu verdict), App
    Store din bază și Google Play din fișier. Toate odată, fiindcă sunt puține: 24 de aplicații × 13 funcții, 19 note
    App Store și 22 Google Play (mip_merge, 08.10.2026); filtrarea pe bănci o face `vox`."""
    return {
        "aplicatii": interoghează(
            """SELECT b.slug AS banca, a.package, a.aplicatie, a.rol, a.versiune_analizata, a.framework,
                      v.data_extragere::text AS data_analizei
               FROM android_aplicatii a
               JOIN banci b ON b.id = a.id_banca
               LEFT JOIN android_versiuni v ON v.package = a.package AND v.version_name = a.versiune_analizata
               ORDER BY b.slug, (a.rol = 'secundar'), a.aplicatie"""),
        "functii": interoghează(
            """SELECT package, functie, verdict, coalesce(surse, '') AS surse, coalesce(dovada_text, '') AS dovada_text
               FROM android_functionalitati ORDER BY package, functie"""),
        "app_store": interoghează(
            """SELECT b.slug AS banca, ar.app_id, ar.rating_agregat::float8 AS nota, ar.volum_rating AS evaluari,
                      ar.distributie_stele, ar.versiune, ar.observat_la::date::text AS observat_la
               FROM app_release_curente ar JOIN banci b ON b.id = ar.id_banca
               WHERE ar.platforma = 'ios' ORDER BY b.slug"""),
        "play": _google_play(),
    }
```

- [ ] **Step 4: rulează testele, apoi cititorul pe baza reală**

Run: `PYTHONIOENCODING=utf-8 python app/test_vox.py`
Expected: OK.

Run (baza `mip_merge`, doar citire):
```bash
PYTHONIOENCODING=utf-8 python -c "import sys; sys.path.insert(0, 'app'); import server; d = server._aplicatii_vox(); print(len(d['aplicatii']), len(d['functii']), len(d['app_store']), len(d['play']['aplicatii']), d['play']['colectat_la']); c = server._context_vox(); print(len(c['functii']), len(c['aplicatii']))"
```
Expected: `24 312 19 22 2026-10-06` și `13 24`.

- [ ] **Step 5: commit**

```bash
printf '%s\n' "app: serverul dă lui Vox aplicațiile: analiza APK și App Store din bază, Google Play din date/" > "$S/mesaj.txt"
git add app/server.py app/test_vox.py && git commit -q -F "$S/mesaj.txt"
```

---

### Task 5: răspunsul cu cele patru vederi (`Vox._aplicatii_raspuns`)

**Files:**
- Modify: `app/vox.py` (`_magazin_play`, `_magazin_app_store`, `_cate_aplicatii`, noi, după `diferente`; `Vox.__init__`; `Vox._aplicatii_raspuns`, nou, după `_clasament_raspuns`; `Vox._raspunde`)
- Modify: `app/server.py` (`VOX = vox.Vox(..., aplicatii=_aplicatii_vox)`)
- Test: `app/test_vox.py` (`APLICATII` și clasa nouă `RaspunsAplicatii`, după `Intrebari`)

**Interfaces:**
- Consumes: `clasa_note`, `putine_note`, `diferente`, `VERDICTE` (Task 3); forma lui `_aplicatii_vox()` (Task 4).
- Produces:
  - răspunsul are cheia `aplicatii` (`null` la celelalte tipuri), cu `vedere` ∈ `functie` / `aplicatii` / `note` / `neanalizata` și câmpurile comune `functie`, `text_cautat`, `analiza_la`, `app_store_la`, `play_la`, `banci_fara_aplicatie`;
  - `functie`: `grupuri: [{verdict, aplicatii: [{banca, aplicatie, verdict, surse, dovada_text, evidentiata}]}]`;
  - `aplicatii`: `coloane: [{banca, fara_aplicatie, aplicatie, versiune_analizata, data_analizei, framework, secundare, functii: {f: {verdict, surse, dovada_text}}, play, app_store}]`, plus `diferente`;
  - `note`: `prag`, `clasamente: {play, app_store}` (fiecare `null` sau ce dă `clasa_note`), `putine_note`, `carduri: [{banca, aplicatie, fara_aplicatie, play, app_store}]`; un magazin al cardului are `nota, evaluari, distributie_stele, versiune, url, loc, loc_pana, din, sub_prag`;
  - `neanalizata`: `functii: [slug]`;
  - jurnalul primește `aplicatii` (câte aplicații arată răspunsul);
  - `vox.Vox(..., aplicatii=None)`.

- [ ] **Step 1: testele care pică**

După clasa `Intrebari`:

```python
APLICATII = {
    "aplicatii": [
        {"banca": "bcr", "package": "ro.bcr.georgego", "aplicatie": "George Romania", "rol": "principal",
         "versiune_analizata": "26.30", "framework": "nativ", "data_analizei": "2026-10-01"},
        {"banca": "brd", "package": "ro.brd.udp.prd", "aplicatie": "YOU BRD", "rol": "principal",
         "versiune_analizata": "16.3", "framework": "nativ", "data_analizei": "2026-10-01"},
        {"banca": "brd", "package": "ro.brd.mybrd", "aplicatie": "MyBRD Mobile", "rol": "secundar",
         "versiune_analizata": "5.0", "framework": "nativ", "data_analizei": "2026-10-01"},
        {"banca": "libra", "package": "libra.mobile.banking", "aplicatie": "Libra Bank", "rol": "reper",
         "versiune_analizata": "4.23.0", "framework": "React Native", "data_analizei": "2026-10-01"},
    ],
    "functii": [
        {"package": "ro.bcr.georgego", "functie": "ropay", "verdict": "sigur", "surse": "cod|text", "dovada_text": "RoPay"},
        {"package": "ro.bcr.georgego", "functie": "in_app_chat", "verdict": "probabil", "surse": "text", "dovada_text": "chat"},
        {"package": "ro.brd.udp.prd", "functie": "ropay", "verdict": "neconcludent", "surse": "", "dovada_text": ""},
        {"package": "ro.brd.udp.prd", "functie": "in_app_chat", "verdict": "absent", "surse": "", "dovada_text": ""},
        {"package": "libra.mobile.banking", "functie": "ropay", "verdict": "absent", "surse": "", "dovada_text": ""},
        {"package": "libra.mobile.banking", "functie": "in_app_chat", "verdict": "absent", "surse": "", "dovada_text": ""},
    ],
    "app_store": [
        {"banca": "bcr", "app_id": "1", "nota": 4.84, "evaluari": 188573, "distributie_stele": [5, 0, 0, 0, 0],
         "versiune": "26.30", "observat_la": "2026-09-24"},
        {"banca": "brd", "app_id": "2", "nota": 5.0, "evaluari": 6, "distributie_stele": [6, 0, 0, 0, 0],
         "versiune": "16.3", "observat_la": "2026-09-24"},
        {"banca": "libra", "app_id": "691914413", "nota": 4.47, "evaluari": 971,
         "distributie_stele": [790, 46, 26, 18, 91], "versiune": "4.23", "observat_la": "2026-09-24"},
    ],
    "play": {"colectat_la": "2026-10-06", "aplicatii": {
        "bcr": {"nota": 4.81, "evaluari": 155826, "distributie_stele": [1, 0, 0, 0, 0], "versiune": "26.30",
                "url": "https://play.google.com/store/apps/details?id=ro.bcr.georgego"},
        "brd": {"nota": 4.83, "evaluari": 234221, "distributie_stele": None, "versiune": "16.3", "url": "u-brd"},
        "libra": {"nota": 4.59, "evaluari": 3083, "distributie_stele": None, "versiune": "4.23.0", "url": "u-libra"}}},
}


class RaspunsAplicatii(unittest.TestCase):
    """Răspunsul la `aplicatii`, pe un cititor fals: cele patru vederi și butoanele lor. ING n-are nicio aplicație."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="vox_apl_")
        self.date = json.loads(json.dumps(APLICATII))          # o copie: unele teste o schimbă

    def fa(self, i, aplicatii=True):
        v = vox.Vox(context=lambda: CTX, cauta=lambda *a: [], stare_banca=lambda b: None, client=ClientFals(i),
                    dir_jurnal=self.dir, aplicatii=(lambda: self.date) if aplicatii else None)
        return v.intreaba("aplicații?"), v

    def test_functie_la_toate_bancile(self):
        d, _ = self.fa(apl(banci=[], functie="ropay"))
        a = d["aplicatii"]
        self.assertEqual(a["vedere"], "functie")
        self.assertEqual([(g["verdict"], [x["banca"] for x in g["aplicatii"]]) for g in a["grupuri"]],
                         [("sigur", ["bcr"]), ("probabil", []), ("absent", ["libra"]), ("neconcludent", ["brd"])])
        bcr = a["grupuri"][0]["aplicatii"][0]
        self.assertEqual((bcr["aplicatie"], bcr["surse"], bcr["dovada_text"], bcr["evidentiata"]),
                         ("George Romania", ["cod", "text"], "RoPay", False))
        self.assertTrue(a["grupuri"][2]["aplicatii"][0]["evidentiata"])            # Libra
        self.assertEqual((a["analiza_la"], a["app_store_la"], a["play_la"], a["banci_fara_aplicatie"]),
                         ("2026-10-01", "2026-09-24", "2026-10-06", ["ing"]))
        self.assertEqual((d["clasament"], d["raspunsuri"], d["butoane"]), (None, [], []))

    def test_aplicatii_cu_libra(self):
        d, _ = self.fa(apl(banci=["bcr", "libra"]))
        a = d["aplicatii"]
        self.assertEqual(a["vedere"], "aplicatii")
        bcr = a["coloane"][0]
        self.assertEqual((bcr["aplicatie"], bcr["framework"], bcr["secundare"], bcr["fara_aplicatie"]),
                         ("George Romania", "nativ", [], False))
        self.assertEqual(bcr["functii"]["ropay"], {"verdict": "sigur", "surse": ["cod", "text"], "dovada_text": "RoPay"})
        self.assertEqual((bcr["play"]["nota"], bcr["app_store"]["url"]), (4.81, "https://apps.apple.com/ro/app/id1"))
        self.assertEqual([(x["functie"], x["nivel"]) for x in a["diferente"]], [("in_app_chat", "probabil"), ("ropay", "sigur")])
        self.assertEqual(d["butoane"], [])                 # Libra e deja numită; fără funcție, fără „La toate băncile”

    def test_secundare_si_banca_fara_aplicatie(self):
        d, _ = self.fa(apl(banci=["brd", "ing"]))
        brd, ing = d["aplicatii"]["coloane"]
        self.assertEqual((brd["aplicatie"], brd["secundare"]), ("YOU BRD", ["MyBRD Mobile"]))
        self.assertEqual((ing["fara_aplicatie"], ing["functii"], ing["play"], ing["app_store"]), (True, {}, None, None))
        self.assertEqual(d["butoane"], ["libra"])

    def test_functie_numita_la_o_banca(self):
        d, _ = self.fa(apl(banci=["bcr"], functie="ropay"))
        self.assertEqual((d["aplicatii"]["vedere"], d["aplicatii"]["functie"]), ("aplicatii", "ropay"))
        self.assertEqual(d["butoane"], ["libra", "toate"])

    def test_functie_neanalizata(self):
        d, _ = self.fa(apl(banci=[], aspect=None, text_cautat="Apple Pay"))
        a = d["aplicatii"]
        self.assertEqual((a["vedere"], a["text_cautat"], a["functii"]),
                         ("neanalizata", "Apple Pay", ["hce_contactless", "in_app_chat", "ropay"]))
        d, _ = self.fa(apl(banci=["bcr"], text_cautat="Apple Pay"))
        self.assertEqual((d["aplicatii"]["vedere"], d["aplicatii"]["text_cautat"]), ("aplicatii", "Apple Pay"))

    def test_note_fara_banci_intreaba_pragul(self):
        d, _ = self.fa(apl(banci=[], aspect="note"))
        a = d["aplicatii"]
        self.assertEqual((a["vedere"], a["prag"], a["carduri"]), ("note", None, []))
        self.assertEqual([(r["banca"], r["loc"]) for r in a["clasamente"]["app_store"]["randuri"]],
                         [("brd", 1), ("bcr", 2), ("libra", 3)])
        self.assertEqual([(r["banca"], r["loc"], r["loc_pana"]) for r in a["clasamente"]["play"]["randuri"]],
                         [("bcr", 1, 2), ("brd", 1, 2), ("libra", 3, 3)])
        self.assertEqual(a["putine_note"], {"app_store": 1, "play": 0, "prag": 100,
                                            "primul": {"magazin": "app_store", "banca": "brd", "loc": 1,
                                                       "loc_pana": 1, "evaluari": 6}})
        self.assertEqual(d["butoane"], ["prag_100", "prag_1000"])

    def test_note_cu_prag(self):
        d, _ = self.fa(apl(banci=[], aspect="note", prag_note=1000))
        a = d["aplicatii"]
        self.assertEqual([r["banca"] for r in a["clasamente"]["app_store"]["randuri"]], ["bcr"])
        self.assertEqual([r["banca"] for r in a["clasamente"]["app_store"]["sub_prag"]], ["brd", "libra"])
        self.assertIsNone(a["putine_note"])
        self.assertEqual(d["butoane"], ["prag_100", "fara_prag"])

    def test_note_cu_banca_card_si_loc(self):
        d, _ = self.fa(apl(banci=["libra"], aspect="note"))
        card = d["aplicatii"]["carduri"][0]
        self.assertEqual((card["banca"], card["aplicatie"], card["fara_aplicatie"]), ("libra", "Libra Bank", False))
        self.assertEqual((card["play"]["loc"], card["play"]["loc_pana"], card["play"]["din"]), (3, 3, 3))
        self.assertEqual((card["app_store"]["loc"], card["app_store"]["din"], card["app_store"]["sub_prag"]), (3, 3, False))
        self.assertEqual(d["butoane"], ["toate", "prag_100", "prag_1000"])

    def test_note_cu_banca_sub_prag(self):
        d, _ = self.fa(apl(banci=["libra"], aspect="note", prag_note=1000))
        card = d["aplicatii"]["carduri"][0]
        self.assertEqual((card["app_store"]["loc"], card["app_store"]["sub_prag"]), (None, True))
        self.assertEqual(card["play"]["loc"], 3)

    def test_note_fara_google_play(self):
        self.date["play"] = None
        d, _ = self.fa(apl(banci=["bcr"], aspect="note"))
        a = d["aplicatii"]
        self.assertEqual((a["clasamente"]["play"], a["play_la"], a["carduri"][0]["play"]), (None, None, None))
        self.assertEqual(a["carduri"][0]["app_store"]["loc"], 2)

    def test_banca_fara_aplicatie(self):
        d, _ = self.fa(apl(banci=["ing"], aspect="note"))
        card = d["aplicatii"]["carduri"][0]
        self.assertEqual((card["fara_aplicatie"], card["play"], card["app_store"]), (True, None, None))

    def test_fara_cititor(self):
        """Evaluarea construiește Vox fără cititorul de aplicații: contează interpretarea, nu datele."""
        d, _ = self.fa(apl(banci=[], functie="ropay"), aplicatii=False)
        self.assertEqual((d["aplicatii"], d["butoane"]), (None, []))

    def test_jurnal_si_conversatie(self):
        d, v = self.fa(apl(banci=[], functie="ropay"))
        with open(os.path.join(self.dir, vox._acum()[:7] + ".jsonl"), encoding="utf-8") as f:
            rand = json.loads(f.readlines()[-1])
        self.assertEqual(rand["aplicatii"], 3)
        tura = v.istoric.citeste(d["conversatie"])["ture"][0]
        self.assertEqual(tura["raspuns"]["aplicatii"]["vedere"], "functie")

    def test_alte_tipuri_au_aplicatii_null(self):
        d, _ = self.fa(interp())
        self.assertIsNone(d["aplicatii"])
```

- [ ] **Step 2: rulează și vezi că pică**

Run: `PYTHONIOENCODING=utf-8 python app/test_vox.py RaspunsAplicatii`
Expected: FAIL (`TypeError: Vox.__init__() got an unexpected keyword argument 'aplicatii'`).

- [ ] **Step 3: implementarea**

După `diferente`:

```python
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
    return 0
```

În `Vox.__init__`, semnătura primește `aplicatii=None` (după `stare_banci=None`), iar în corp, după `self._stare_banci = stare_banci`:

```python
        # aplicațiile (app/server.py, `_aplicatii_vox`); fără cititor, răspunsul are `aplicatii: null` (evaluarea)
        self._aplicatii = aplicatii
```

După `_clasament_raspuns`:

```python
    def _aplicatii_raspuns(self, interp, ctx):
        """Una din cele patru vederi (spec 2026-10-08-vox-aplicatii): o funcție la toate băncile, aplicațiile
        băncilor numite, notele din magazine sau o funcție care nu e analizată."""
        if not self._aplicatii:
            return None
        date = self._aplicatii()
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
```

În `_raspunde`:
- în `try`, după linia `clasament = ...`:

```python
            aplicatii = self._aplicatii_raspuns(interp, ctx) if interp["tip"] == "aplicatii" else None
```

- după blocul `if clasament and clasament.get("blocuri"): ...`:

```python
        if aplicatii:
            rand["aplicatii"] = _cate_aplicatii(aplicatii)
```

- `rezultat` primește `"aplicatii": aplicatii,` după `"clasament": clasament,`, iar `butoane(interp, raspunsuri, clasament)` devine `butoane(interp, raspunsuri, clasament, aplicatii)`. Semnătura lui `butoane` primește `aplicatii=None` deja aici (corpul vine în Task 6), ca apelul să meargă.

În `app/server.py`:

```python
VOX = vox.Vox(context=_context_vox, cauta=_cauta_vox, stare_banca=_stare_banca_vox,
              clasament=_clasament_vox, stare_banci=_stare_banci_vox, aplicatii=_aplicatii_vox)
```

- [ ] **Step 4: rulează toate testele**

Run: `PYTHONIOENCODING=utf-8 python app/test_vox.py`
Expected: OK, cu o excepție așteptată: testele care cer butoane (`d["butoane"]`) pică până la Task 6. Dacă pică doar ele, treci la Task 6 înainte de commit și fă commit-ul după Task 6, pentru ambele task-uri.

- [ ] **Step 5: commit** (împreună cu Task 6, dacă au picat doar butoanele)

```bash
printf '%s\n' "app: răspunsul Vox la aplicații, în patru vederi: funcția la toate băncile, aplicațiile, notele, funcția neanalizată" > "$S/mesaj.txt"
git add app/vox.py app/server.py app/test_vox.py && git commit -q -F "$S/mesaj.txt"
```

---

### Task 6: butoanele (`app/vox.py`)

**Files:**
- Modify: `app/vox.py` (`BUTOANE`, `PRAG_BUTON`, `butoane`, `_butoane_aplicatii`, `din_buton`, `_din_buton_aplicatii`)
- Test: `app/test_vox.py` (clasa nouă `ButoaneAplicatii`, după `Butoane`; `Http.test_post_buton_aplicatii`, nou)

**Interfaces:**
- Consumes: `aplicatii["putine_note"]` (Task 5).
- Produces: `vox.butoane(interp, raspunsuri, clasament, aplicatii=None)`; `vox.din_buton(anterior, buton)` acceptă tipul `aplicatii`; `vox.BUTOANE` cu `toate`, `prag_100`, `prag_1000`, `fara_prag`; `vox.PRAG_BUTON = {"prag_100": 100, "prag_1000": 1000}`.

- [ ] **Step 1: testele care pică**

```python
class ButoaneAplicatii(unittest.TestCase):
    """Butoanele la `aplicatii` (decizia lui Nicolae, 08.10.2026): fără model, deci gratuite."""

    def test_butoane(self):
        cu_putine = {"vedere": "note", "putine_note": {"app_store": 1}}
        fara_putine = {"vedere": "note", "putine_note": None}
        functii = {"vedere": "aplicatii"}
        self.assertEqual(vox.butoane(apl(banci=["bcr"]), [], None, functii), ["libra"])
        self.assertEqual(vox.butoane(apl(banci=["bcr"], functie="ropay"), [], None, functii), ["libra", "toate"])
        self.assertEqual(vox.butoane(apl(banci=[], functie="ropay"), [], None, {"vedere": "functie"}), [])
        self.assertEqual(vox.butoane(apl(banci=[], aspect="note"), [], None, cu_putine), ["prag_100", "prag_1000"])
        self.assertEqual(vox.butoane(apl(banci=[], aspect="note"), [], None, fara_putine), [])
        self.assertEqual(vox.butoane(apl(banci=[], aspect="note", prag_note=100), [], None, fara_putine),
                         ["prag_1000", "fara_prag"])
        self.assertEqual(vox.butoane(apl(banci=[], aspect="note", prag_note=500), [], None, fara_putine),
                         ["prag_100", "prag_1000", "fara_prag"])
        self.assertEqual(vox.butoane(apl(banci=["bcr"], aspect="note"), [], None, cu_putine),
                         ["libra", "toate", "prag_100", "prag_1000"])
        self.assertEqual(vox.butoane(apl(banci=["bcr"]), [], None, None), [])        # fără cititor

    def test_din_buton(self):
        self.assertEqual(vox.din_buton(apl(banci=["bcr"]), "libra")["banci"], ["bcr", "libra"])
        n = vox.din_buton(apl(banci=["bcr"], functie="ropay"), "toate")
        self.assertEqual((n["banci"], n["functie"], n["tip"]), ([], "ropay", "aplicatii"))
        n = vox.din_buton(apl(banci=["bcr"], aspect="note", prag_note=100), "toate")
        self.assertEqual((n["banci"], n["prag_note"]), ([], 100))
        self.assertEqual(vox.din_buton(apl(banci=[], aspect="note"), "prag_100")["prag_note"], 100)
        self.assertEqual(vox.din_buton(apl(banci=[], aspect="note"), "prag_1000")["prag_note"], 1000)
        self.assertIsNone(vox.din_buton(apl(banci=[], aspect="note", prag_note=100), "fara_prag")["prag_note"])

    def test_din_buton_aplicatii_refuza(self):
        for i, b in ((apl(banci=["bcr"]), "prag_100"), (apl(banci=["bcr"]), "fara_prag"),
                     (apl(banci=[], functie="ropay"), "toate"), (apl(banci=["bcr"]), "toate"),
                     (apl(banci=["libra"]), "libra"), (apl(banci=["bcr", "brd", "ing"]), "libra"),
                     (apl(banci=["bcr"]), "firme"), (apl(banci=["bcr"]), "pf"),
                     (interp(), "toate"), (interp(), "prag_100"), (interp(tip="clasament", banci=[]), "fara_prag")):
            with self.assertRaises(vox.Respins, msg=(i, b)):
                vox.din_buton(i, b)

    def test_etichete_pentru_toate_pragurile(self):
        self.assertEqual(set(vox.PRAG_BUTON), {f"prag_{p}" for p in vox.PRAGURI_NOTE})
        self.assertTrue(set(vox.PRAG_BUTON) | {"toate", "fara_prag"} <= set(vox.BUTOANE))
```

În clasa `Http`:

```python
    def test_post_buton_aplicatii(self):
        """„Cel puțin 100 de note” sub clasamentul notelor: fără model; un prag sub o întrebare de funcții, 400."""
        ok = {"X-MIP-Token": self.token()}
        n = len(self.client.cereri)
        anterior = dict(vox._gol("aplicatii"), aspect="note")
        cod, d = self.cere("POST", "/api/vox", {"buton": "prag_100", "anterior": anterior}, ok)
        self.assertEqual(cod, 200, d)
        self.assertEqual((d["model"], d["cost_usd"], d["buton"], d["interpretare"]["prag_note"]),
                         (None, 0, "prag_100", 100))
        self.assertIsNone(d["aplicatii"])                     # serverul de test n-are cititor de aplicații
        rau = dict(anterior, aspect="functii", banci=["bcr"])
        self.assertEqual(self.cere("POST", "/api/vox", {"buton": "prag_100", "anterior": rau}, ok)[0], 400)
        self.assertEqual(len(self.client.cereri), n)
```

- [ ] **Step 2: rulează și vezi că pică**

Run: `PYTHONIOENCODING=utf-8 python app/test_vox.py ButoaneAplicatii Http`
Expected: FAIL (`AttributeError: ... PRAG_BUTON` și 400 la `prag_100`).

- [ ] **Step 3: implementarea**

```python
BUTOANE = {"firme": "Pentru firme", "pf": "Pentru persoane fizice", "libra": "Compară cu Libra",
           "toate": "La toate băncile", "prag_100": "Cel puțin 100 de note",
           "prag_1000": "Cel puțin 1.000 de note", "fara_prag": "Fără prag"}
PRAG_BUTON = {f"prag_{p}": p for p in PRAGURI_NOTE}
```

`butoane` primește `aplicatii=None`, iar prima linie din corp, după docstring, e:

```python
    if interp["tip"] == "aplicatii":
        return _butoane_aplicatii(interp, aplicatii)
```

După `butoane`:

```python
def _butoane_aplicatii(interp, aplicatii):
    """La aplicații: Libra lângă băncile numite, aceeași întrebare la toate băncile și pragul de note. Fără prag,
    pragurile apar doar când clasamentul are aplicații cu puține note (`putine_note`)."""
    if not aplicatii:
        return []
    banci, rez = interp["banci"], []
    if banci and "libra" not in banci and len(banci) < MAX_BANCI:
        rez.append("libra")
    if banci and (interp["functie"] or interp["aspect"] == "note"):
        rez.append("toate")
    if interp["aspect"] == "note":
        prag = interp.get("prag_note")
        if prag is None:
            rez += list(PRAG_BUTON) if aplicatii.get("putine_note") else []
        else:
            rez += [b for b, p in PRAG_BUTON.items() if p != prag] + ["fara_prag"]
    return rez
```

`din_buton` devine (fiecare buton tratat explicit; cu cheile noi în `BUTOANE`, ramura de azi ar fi adăugat Libra la un `toate` trimis pe o căutare):

```python
def din_buton(anterior, buton):
    """Interpretarea nouă după un buton, fără model. Un buton care nu se potrivește ridică `Respins`."""
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
    elif buton == "toate" and banci and (nou["functie"] or nou["aspect"] == "note"):
        nou["banci"] = []
    elif (buton in PRAG_BUTON or buton == "fara_prag") and nou["aspect"] == "note":
        nou["prag_note"] = PRAG_BUTON.get(buton)
    else:
        raise Respins(NEPOTRIVIT)
    return nou
```

- [ ] **Step 4: rulează toate testele**

Run: `PYTHONIOENCODING=utf-8 python app/test_vox.py && PYTHONIOENCODING=utf-8 python app/test_celula.py`
Expected: OK în ambele.

- [ ] **Step 5: commit**

```bash
printf '%s\n' "app: butoanele Vox pentru aplicații: Compară cu Libra, La toate băncile și pragul de note, fără model" > "$S/mesaj.txt"
git add app/vox.py app/test_vox.py && git commit -q -F "$S/mesaj.txt"
```

---

### Task 7: interfața (`shared/`, `web/`)

**Files:**
- Modify: `shared/src/vox.ts`
- Modify: `web/src/pages/rate_mobil/android/model.ts` (`export const FUNCTII`)
- Create: `web/src/pages/vox/Aplicatii.tsx`
- Modify: `web/src/pages/Vox.tsx` (`Raspuns`: ramura `aplicatii`; importul `Aplicatii`)
- Modify: `web/src/i18n/dict/vox.ts`
- Modify: `web/src/styles/vox.css`

**Interfaces:**
- Consumes: forma răspunsului din Task 5 și butoanele din Task 6.
- Produces: tipurile Zod `Aplicatii`, `ColoanaAplicatie`, `NotaMagazin`, `RandNota`, `ClasamentNote`, `CardNote`, `Diferenta`; componenta `Aplicatii({ a, m })`.

- [ ] **Step 1: tipurile Zod (`shared/src/vox.ts`)**

`Interpretare`: `tip` devine `z.enum(['cautare', 'clasament', 'aplicatii', 'neclar', 'in_afara'])`, iar după `metrica`:

```ts
  /** lipsesc în conversațiile salvate înainte de aplicații (08.10.2026) */
  functie: z.string().nullable().optional(),
  aspect: z.enum(['functii', 'note']).nullable().optional(),
  prag_note: z.number().nullable().optional(),
```

`Buton` devine `z.enum(['firme', 'pf', 'libra', 'toate', 'prag_100', 'prag_1000', 'fara_prag'])`.

Înainte de `RaspunsIntrebare`:

```ts
/** Aplicațiile băncilor (app/vox.py, `Vox._aplicatii_raspuns`): analiza APK, App Store, Google Play. */
const Verdict = z.enum(['sigur', 'probabil', 'absent', 'neconcludent'])

export const FunctieAplicatie = z.object({ verdict: Verdict, surse: z.array(z.string()), dovada_text: z.string().nullable() })
export type FunctieAplicatie = z.infer<typeof FunctieAplicatie>

/** Nota dintr-un magazin; `loc`…`sub_prag` doar în cardurile vederii `note`. */
export const NotaMagazin = z
  .object({
    nota: z.number().nullable(), evaluari: z.number(), distributie_stele: z.array(z.number()).nullable(),
    versiune: z.string().nullable(), url: z.string().nullable(),
    loc: z.number().nullable().optional(), loc_pana: z.number().nullable().optional(),
    din: z.number().nullable().optional(), sub_prag: z.boolean().optional(),
  })
  .passthrough()
export type NotaMagazin = z.infer<typeof NotaMagazin>

export const ColoanaAplicatie = z
  .object({
    banca: z.string(), fara_aplicatie: z.boolean(), aplicatie: z.string().nullable(),
    versiune_analizata: z.string().nullable(), data_analizei: z.string().nullable(), framework: z.string().nullable(),
    secundare: z.array(z.string()), functii: z.record(FunctieAplicatie),
    play: NotaMagazin.nullable(), app_store: NotaMagazin.nullable(),
  })
  .passthrough()
export type ColoanaAplicatie = z.infer<typeof ColoanaAplicatie>

export const Diferenta = z.object({
  functie: z.string(), nivel: z.enum(['sigur', 'probabil']), au: z.array(z.string()), n_au: z.array(z.string()),
})
export type Diferenta = z.infer<typeof Diferenta>

/** Un rând din clasamentul notelor (app/vox.py, `clasa_note`); fără `loc` sub prag sau fără notă. */
export const RandNota = z
  .object({
    banca: z.string(), aplicatie: z.string().nullable(), nota: z.number().nullable(),
    nota_afisata: z.number().nullable(), evaluari: z.number(), url: z.string().nullable(), evidentiata: z.boolean(),
    loc: z.number().optional(), loc_pana: z.number().optional(),
  })
  .passthrough()
export type RandNota = z.infer<typeof RandNota>

export const ClasamentNote = z.object({ randuri: z.array(RandNota), sub_prag: z.array(RandNota), fara_nota: z.array(RandNota) })
export type ClasamentNote = z.infer<typeof ClasamentNote>

export const CardNote = z
  .object({
    banca: z.string(), aplicatie: z.string().nullable(), fara_aplicatie: z.boolean(),
    play: NotaMagazin.nullable(), app_store: NotaMagazin.nullable(),
  })
  .passthrough()
export type CardNote = z.infer<typeof CardNote>

export const Aplicatii = z
  .object({
    vedere: z.enum(['functie', 'aplicatii', 'note', 'neanalizata']),
    functie: z.string().nullable(),
    text_cautat: z.string().nullable(),
    analiza_la: z.string().nullable(),
    app_store_la: z.string().nullable(),
    play_la: z.string().nullable(),
    banci_fara_aplicatie: z.array(z.string()),
    grupuri: z.array(z.object({
      verdict: Verdict,
      aplicatii: z.array(z.object({
        banca: z.string(), aplicatie: z.string().nullable(), verdict: Verdict, surse: z.array(z.string()),
        dovada_text: z.string().nullable(), evidentiata: z.boolean(),
      }).passthrough()),
    })).optional(),
    coloane: z.array(ColoanaAplicatie).optional(),
    diferente: z.array(Diferenta).optional(),
    prag: z.number().nullable().optional(),
    clasamente: z.object({ play: ClasamentNote.nullable(), app_store: ClasamentNote.nullable() }).optional(),
    putine_note: z.object({
      app_store: z.number().optional(), play: z.number().optional(), prag: z.number(),
      primul: z.object({
        magazin: z.enum(['play', 'app_store']), banca: z.string(), loc: z.number(), loc_pana: z.number(), evaluari: z.number(),
      }),
    }).nullable().optional(),
    carduri: z.array(CardNote).optional(),
    functii: z.array(z.string()).optional(),
  })
  .passthrough()
export type Aplicatii = z.infer<typeof Aplicatii>
```

În `RaspunsIntrebare`, după `clasament`:

```ts
    /** lipsește în conversațiile salvate înainte de aplicații (08.10.2026) */
    aplicatii: Aplicatii.nullable().optional(),
```

- [ ] **Step 2: `FUNCTII` exportată**

În `web/src/pages/rate_mobil/android/model.ts`: `const FUNCTII: string[] = [` devine `export const FUNCTII: string[] = [`.

- [ ] **Step 3: textele (`web/src/i18n/dict/vox.ts`)**

`vox.in_afara` devine:

```ts
  "vox.in_afara": ["Răspund la valorile unei bănci (un comision sau o dobândă), la clasamente între bănci și la aplicațiile băncilor (funcții și note). Recenziile și campaniile nu sunt încă aici. De exemplu:", "I answer about a bank's values (a fee or an interest rate), rank banks against each other and cover the banks' apps (features and ratings). Reviews and campaigns are not here yet. For example:"],
```

După `"vox.buton.libra"`:

```ts
  "vox.buton.toate": ["La toate băncile", "All banks"],
  "vox.buton.prag_100": ["Cel puțin 100 de note", "At least 100 ratings"],
  "vox.buton.prag_1000": ["Cel puțin 1.000 de note", "At least 1,000 ratings"],
  "vox.buton.fara_prag": ["Fără prag", "No threshold"],
```

La final, înaintea acoladei de închidere a dicționarului:

```ts
  // ---- Aplicațiile (08.10.2026) ----
  "vox.aplicatii.chip": ["aplicații", "apps"],
  "vox.aplicatii.chip_note": ["note în magazine", "store ratings"],
  "vox.aplicatii.chip_prag": ["cel puțin {prag} de note", "at least {prag} ratings"],
  "vox.aplicatii.indisponibil": ["Datele despre aplicații nu sunt disponibile.", "App data is not available."],
  "vox.aplicatii.n_aplicatii": ["aplicații: {n}", "apps: {n}"],
  "vox.aplicatii.nota_bifa": ["O bifă spune că aplicația are funcția sau o are pregătită, nu că e activă pentru toți clienții; absența nu dovedește lipsa.", "A tick says the app contains the feature or has it ready, not that it is active for every customer; absence does not prove it is missing."],
  "vox.aplicatii.fara_aplicatie": ["Fără aplicație analizată ({n}): {banci}.", "No analysed app ({n}): {banci}."],
  "vox.aplicatii.fara_apk": ["fără aplicație analizată", "no analysed app"],
  "vox.aplicatii.sursa_analiza": ["analiza APK, {data}", "APK analysis, {data}"],
  "vox.aplicatii.sursa_app_store": ["App Store, {data}", "App Store, {data}"],
  "vox.aplicatii.sursa_play": ["Google Play, {data}", "Google Play, {data}"],
  "vox.aplicatii.play_lipsa": ["Google Play necolectat", "Google Play not collected"],
  "vox.aplicatii.deschide_android": ["Deschide analiza Android", "Open the Android analysis"],
  "vox.aplicatii.deschide_mobil": ["Deschide 2.3 Aplicații", "Open 2.3 Apps"],
  "vox.aplicatii.secundare": ["Banca are și: {nume} (pe pagina Android)", "The bank also has: {nume} (on the Android page)"],
  "vox.aplicatii.versiune": ["versiunea analizată {v}", "analysed version {v}"],
  "vox.aplicatii.col.functie": ["Funcție", "Feature"],
  "vox.aplicatii.dif_sigura": ["diferență sigură", "certain difference"],
  "vox.aplicatii.dif_probabila": ["diferență probabilă", "likely difference"],
  "vox.aplicatii.necomparabil": ["nu se poate compara", "cannot be compared"],
  "vox.aplicatii.are_nu": ["Are {x}, n-are {y}: {lista}.", "{x} has, {y} doesn't: {lista}."],
  "vox.aplicatii.probabil_si": ["probabil și {lista}", "likely also {lista}"],
  "vox.aplicatii.probabil": ["probabil {lista}", "likely {lista}"],
  "vox.aplicatii.nicio_diferenta": ["Nicio diferență sigură sau probabilă pe cele {n} funcții.", "No certain or likely difference across the {n} features."],
  "vox.aplicatii.necomparabile": ["Funcții care nu se pot compara: {n}.", "Features that cannot be compared: {n}."],
  "vox.aplicatii.neanalizata": ["„{text}” nu e printre funcțiile analizate. Funcțiile analizate:", "“{text}” is not among the analysed features. The analysed features:"],
  "vox.aplicatii.neanalizata_banca": ["„{text}” nu e printre funcțiile analizate; mai jos, tot ce știm despre aplicație.", "“{text}” is not among the analysed features; below is everything we know about the app."],
  "vox.aplicatii.note_titlu": ["Nota din magazine", "Store rating"],
  "vox.aplicatii.dupa_nota": ["după nota din magazine; nota nu măsoară funcțiile", "by store rating; the rating does not measure features"],
  "vox.aplicatii.magazin.play": ["Google Play", "Google Play"],
  "vox.aplicatii.magazin.app_store": ["App Store", "App Store"],
  "vox.aplicatii.col.aplicatia": ["Aplicația", "App"],
  "vox.aplicatii.col.nota": ["Nota", "Rating"],
  "vox.aplicatii.col.evaluari": ["Note", "Ratings"],
  "vox.aplicatii.deschide_magazin": ["în magazin", "in store"],
  "vox.aplicatii.nr_note": ["note: {n}", "ratings: {n}"],
  "vox.aplicatii.intreaba_prag": ["Clasamentul n-are prag. În {magazin}, {banca} e pe locul {loc}, cu un număr mic de note: {evaluari}. Aplicații cu sub {prag} de note: {n_app_store} în App Store, {n_play} în Google Play. Ce prag vrei să pui?", "The ranking has no threshold. On {magazin}, {banca} ranks {loc} with few ratings: {evaluari}. Apps with fewer than {prag} ratings: {n_app_store} on the App Store, {n_play} on Google Play. What threshold do you want?"],
  "vox.aplicatii.intreaba_prag_egal": ["Clasamentul n-are prag. În {magazin}, {banca} e pe locurile {loc}–{pana}, cu un număr mic de note: {evaluari}. Aplicații cu sub {prag} de note: {n_app_store} în App Store, {n_play} în Google Play. Ce prag vrei să pui?", "The ranking has no threshold. On {magazin}, {banca} ranks {loc}–{pana} with few ratings: {evaluari}. Apps with fewer than {prag} ratings: {n_app_store} on the App Store, {n_play} on Google Play. What threshold do you want?"],
  "vox.aplicatii.prag_activ": ["Prag: cel puțin {prag} de note.", "Threshold: at least {prag} ratings."],
  "vox.aplicatii.sub_prag": ["Sub prag ({n}): {lista}", "Below the threshold ({n}): {lista}"],
  "vox.aplicatii.fara_nota": ["Fără notă ({n}): {lista}", "No rating ({n}): {lista}"],
  "vox.aplicatii.card_loc": ["locul {loc} din {din}", "rank {loc} of {din}"],
  "vox.aplicatii.card_loc_egal": ["locurile {loc}–{pana} din {din}", "ranks {loc}–{pana} of {din}"],
  "vox.aplicatii.card_sub_prag": ["sub prag", "below the threshold"],
  "vox.aplicatii.fara_magazin": ["fără aplicație în {magazin}", "no app on {magazin}"],
```

- [ ] **Step 4: componenta `web/src/pages/vox/Aplicatii.tsx`**

```tsx
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Tooltip } from 'antd'
import type { Aplicatii as AplicatiiT, CardNote as CardNoteT, ClasamentNote, ColoanaAplicatie, Diferenta } from '@mcc/shared'
import type { Meta } from '../../api/meta'
import { BareStele } from '../../components/BareStele'
import { EtichetaBanca } from '../../components/comune'
import { areCheie, useLang, type DictKey } from '../../i18n'
import { formatZi, num } from '../../util/format'
import { Verdict } from '../rate_mobil/android/comune'
import { FUNCTII } from '../rate_mobil/android/model'
import '../../styles/android.css'

/**
 * Aplicațiile băncilor în Vox (app/vox.py, `Vox._aplicatii_raspuns`): o funcție la toate băncile, aplicațiile băncilor
 * numite, notele din magazine sau o funcție neanalizată. Verdictele, etichetele și ordinea funcțiilor sunt ale paginii
 * Android, ca să nu existe a doua listă. Primele 10 rânduri ale unui clasament de note, plus Libra și băncile numite,
 * ca în `Clasament.tsx`: 22 de aplicații în Google Play, 19 în App Store (08.10.2026).
 */
const PRIMELE = 10
type T = (k: DictKey, p?: Record<string, string | number>) => string

function etFunctie(f: string, t: T, scurt = false): string {
  const k = `mobil.android_${scurt ? 'fs' : 'f'}.${f}`
  return areCheie(k) ? t(k) : f
}

/** Ordinea paginii Android; o funcție nouă din bază, fără loc în listă, la final. */
function rang(f: string): number {
  const i = FUNCTII.indexOf(f)
  return i === -1 ? FUNCTII.length : i
}

function Dovada({ aplicatie, surse, dovada }: { aplicatie: string | null; surse: string[]; dovada: string | null }) {
  const { t } = useLang()
  const etSursa = (s: string) => (areCheie(`mobil.android_sursa.${s}`) ? t(`mobil.android_sursa.${s}` as DictKey) : s)
  return (
    <span className="vox-apl-dovada">
      {aplicatie && <b>{aplicatie}</b>}
      {surse.length > 0 && <span>{t('mobil.android_surse', { surse: surse.map(etSursa).join(', ') })}</span>}
      {dovada && <span>{t('mobil.android_dovada', { dovada })}</span>}
    </span>
  )
}

export default function Aplicatii({ a, m }: { a: AplicatiiT; m: Meta }) {
  const { t, locale } = useLang()
  const note = a.vedere === 'note' || a.vedere === 'aplicatii'
  const surse = [
    a.vedere !== 'note' && a.analiza_la ? t('vox.aplicatii.sursa_analiza', { data: formatZi(a.analiza_la, locale) }) : '',
    note && a.app_store_la ? t('vox.aplicatii.sursa_app_store', { data: formatZi(a.app_store_la, locale) }) : '',
    note ? (a.play_la ? t('vox.aplicatii.sursa_play', { data: formatZi(a.play_la, locale) }) : t('vox.aplicatii.play_lipsa')) : '',
  ].filter(Boolean)
  return (
    <div className="vox-fisa vox-apl">
      {a.vedere === 'functie' && <VedereFunctie a={a} m={m} />}
      {a.vedere === 'aplicatii' && <VedereAplicatii a={a} m={m} />}
      {a.vedere === 'note' && <VedereNote a={a} m={m} />}
      {a.vedere === 'neanalizata' && <Neanalizata a={a} />}
      {a.vedere !== 'aplicatii' && a.banci_fara_aplicatie.length > 0 && (
        <p className="vox-nota">
          <span className="vox-punct gri" />
          {t('vox.aplicatii.fara_aplicatie', {
            n: a.banci_fara_aplicatie.length, banci: a.banci_fara_aplicatie.map((b) => m.nume[b] ?? b).join(', '),
          })}
        </p>
      )}
      <div className="vox-fisa-jos">
        <span className="vox-meta">{surse.join(' · ')}</span>
        <Link className="vox-link" to={a.vedere === 'note' ? '/mobil' : '/mobil?platforma=android&s=functionalitati'}>
          {t(a.vedere === 'note' ? 'vox.aplicatii.deschide_mobil' : 'vox.aplicatii.deschide_android')}
        </Link>
      </div>
    </div>
  )
}

function VedereFunctie({ a, m }: { a: AplicatiiT; m: Meta }) {
  const { t } = useLang()
  const grupuri = a.grupuri ?? []
  return (
    <>
      <div className="vox-clas-antet">
        <b>{a.functie ? etFunctie(a.functie, t) : ''}</b>
        <span className="vox-meta">{t('vox.aplicatii.n_aplicatii', { n: grupuri.reduce((s, g) => s + g.aplicatii.length, 0) })}</span>
      </div>
      <div className="vox-apl-grupe">
        {grupuri.map((g) => (
          <section key={g.verdict} className="vox-apl-grupa">
            <div className="vox-apl-grupa-cap">
              <Verdict v={g.verdict} />
              <b>{t(`mobil.android_verdict.${g.verdict}` as DictKey)}</b>
              <span className="vox-meta">
                {t('vox.aplicatii.n_aplicatii', { n: g.aplicatii.length })} · {t(`mobil.android_verdict_d.${g.verdict}` as DictKey)}
              </span>
            </div>
            {g.aplicatii.length > 0 && (
              <div className="vox-apl-banci">
                {g.aplicatii.map((x) => (
                  <Tooltip key={x.banca} title={<Dovada aplicatie={x.aplicatie} surse={x.surse} dovada={x.dovada_text} />}>
                    <span className={x.evidentiata ? 'vox-apl-banca evidentiata' : 'vox-apl-banca'}>
                      <EtichetaBanca slug={x.banca} m={m} tag />
                    </span>
                  </Tooltip>
                ))}
              </div>
            )}
          </section>
        ))}
      </div>
      <p className="vox-nota"><span className="vox-punct gri" />{t('vox.aplicatii.nota_bifa')}</p>
    </>
  )
}

/** „Are X, n-are Y: …”, din diferențe și din verdictul lui X (sigur sau probabil), cu etichetele scurte. */
function propozitie(x: ColoanaAplicatie, y: ColoanaAplicatie, dif: Diferenta[], t: T): string | null {
  const ale = dif.filter((d) => d.au.includes(x.banca) && d.n_au.includes(y.banca)).sort((p, q) => rang(p.functie) - rang(q.functie))
  if (!ale.length) return null
  const sigure = ale.filter((d) => x.functii[d.functie]?.verdict === 'sigur').map((d) => etFunctie(d.functie, t, true))
  const probabile = ale.filter((d) => x.functii[d.functie]?.verdict === 'probabil').map((d) => etFunctie(d.functie, t, true))
  const parti = [sigure.join(', ')]
  if (probabile.length) parti.push(t(sigure.length ? 'vox.aplicatii.probabil_si' : 'vox.aplicatii.probabil', { lista: probabile.join(', ') }))
  return t('vox.aplicatii.are_nu', { x: x.aplicatie ?? x.banca, y: y.aplicatie ?? y.banca, lista: parti.filter(Boolean).join('; ') })
}

function NoteScurte({ c }: { c: ColoanaAplicatie }) {
  const { t, locale } = useLang()
  const parti = (['play', 'app_store'] as const)
    .map((k) => [k, c[k]] as const)
    .filter(([, n]) => n && n.nota !== null)
    .map(([k, n]) => `${t(`vox.aplicatii.magazin.${k}` as DictKey)} ${num(n!.nota, locale, 1)} (${num(n!.evaluari, locale, 0)})`)
  return parti.length ? <span className="sub">★ {parti.join(' · ')}</span> : null
}

function VedereAplicatii({ a, m }: { a: AplicatiiT; m: Meta }) {
  const { t } = useLang()
  const coloane = a.coloane ?? []
  const dif = a.diferente ?? []
  const peFunctie = new Map(dif.map((d) => [d.functie, d]))
  const cu = coloane.filter((c) => !c.fara_aplicatie)
  const randuri = [...new Set(coloane.flatMap((c) => Object.keys(c.functii)))]
    .sort((x, y) => (x === a.functie ? -1 : y === a.functie ? 1 : rang(x) - rang(y)))
  const necomparabile = randuri.filter((f) => !peFunctie.has(f) && cu.some((c) => c.functii[f]?.verdict === 'neconcludent'))
  const fraze = cu.length === 2
    ? [propozitie(cu[0]!, cu[1]!, dif, t), propozitie(cu[1]!, cu[0]!, dif, t)].filter((x): x is string => !!x)
    : []
  return (
    <>
      {a.text_cautat && !a.functie && (
        <p className="vox-nota"><span className="vox-punct" />{t('vox.aplicatii.neanalizata_banca', { text: a.text_cautat })}</p>
      )}
      {cu.length === 2 && (
        <p className="vox-apl-propozitie">
          {fraze.length ? fraze.join(' ') : t('vox.aplicatii.nicio_diferenta', { n: randuri.length })}
          {necomparabile.length > 0 && ` ${t('vox.aplicatii.necomparabile', { n: necomparabile.length })}`}
        </p>
      )}
      <div className="vox-tabel-cutie">
        <table className="vox-tabel vox-apl-tabel">
          <thead>
            <tr>
              <th>{t('vox.aplicatii.col.functie')}</th>
              {coloane.map((c) => (
                <th key={c.banca} className="vox-apl-col">
                  <EtichetaBanca slug={c.banca} m={m} tag />
                  {c.fara_aplicatie
                    ? <span className="sub">{t('vox.aplicatii.fara_apk')}</span>
                    : (
                      <span className="sub">
                        {[c.aplicatie, c.versiune_analizata && t('vox.aplicatii.versiune', { v: c.versiune_analizata }), c.framework]
                          .filter(Boolean).join(' · ')}
                      </span>
                    )}
                  <NoteScurte c={c} />
                  {c.secundare.length > 0 && <span className="sub">{t('vox.aplicatii.secundare', { nume: c.secundare.join(', ') })}</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {randuri.map((f) => {
              const d = peFunctie.get(f)
              const necomp = necomparabile.includes(f)
              const cls = [f === a.functie ? 'evidentiata' : '', d ? `dif-${d.nivel}` : necomp ? 'necomparabil' : ''].filter(Boolean).join(' ')
              return (
                <tr key={f} className={cls || undefined}>
                  <td>
                    {etFunctie(f, t)}
                    {d && <span className="sub">{t(d.nivel === 'sigur' ? 'vox.aplicatii.dif_sigura' : 'vox.aplicatii.dif_probabila')}</span>}
                    {!d && necomp && <span className="sub">{t('vox.aplicatii.necomparabil')}</span>}
                  </td>
                  {coloane.map((c) => {
                    const v = c.functii[f]
                    return (
                      <td key={c.banca} className="vox-apl-v">
                        {v
                          ? (
                            <Tooltip title={(
                              <span className="vox-apl-dovada">
                                <b>{t(`mobil.android_verdict.${v.verdict}` as DictKey)}</b>
                                <span>{t(`mobil.android_verdict_d.${v.verdict}` as DictKey)}</span>
                                <Dovada aplicatie={null} surse={v.surse} dovada={v.dovada_text} />
                              </span>
                            )}>
                              <span><Verdict v={v.verdict} /></span>
                            </Tooltip>
                          )
                          : <span className="gri">—</span>}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </>
  )
}

function VedereNote({ a, m }: { a: AplicatiiT; m: Meta }) {
  const { t, locale } = useLang()
  const p = a.putine_note
  const magazin = (k: 'play' | 'app_store') => t(`vox.aplicatii.magazin.${k}` as DictKey)
  return (
    <>
      <div className="vox-clas-antet">
        <b>{t('vox.aplicatii.note_titlu')}</b>
        <span className="vox-meta">{t('vox.aplicatii.dupa_nota')}</span>
      </div>
      {p && (
        <p className="vox-nota vox-apl-prag">
          <span className="vox-punct" />
          {t(p.primul.loc === p.primul.loc_pana ? 'vox.aplicatii.intreaba_prag' : 'vox.aplicatii.intreaba_prag_egal', {
            magazin: magazin(p.primul.magazin), banca: m.nume[p.primul.banca] ?? p.primul.banca,
            loc: p.primul.loc, pana: p.primul.loc_pana, evaluari: num(p.primul.evaluari, locale, 0),
            prag: num(p.prag, locale, 0), n_app_store: p.app_store ?? 0, n_play: p.play ?? 0,
          })}
        </p>
      )}
      {a.prag != null && (
        <p className="vox-nota"><span className="vox-punct gri" />{t('vox.aplicatii.prag_activ', { prag: num(a.prag, locale, 0) })}</p>
      )}
      {(a.carduri ?? []).length > 0 && (
        <div className="vox-apl-carduri">
          {(a.carduri ?? []).map((c) => <CardNote key={c.banca} c={c} m={m} />)}
        </div>
      )}
      {(['play', 'app_store'] as const).map((k) => (
        <TabelNote key={k} titlu={magazin(k)} c={a.clasamente?.[k] ?? null} m={m} />
      ))}
    </>
  )
}

function CardNote({ c, m }: { c: CardNoteT; m: Meta }) {
  const { t, locale } = useLang()
  return (
    <article className="vox-apl-card">
      <EtichetaBanca slug={c.banca} m={m} tag />
      {c.fara_aplicatie
        ? <span className="vox-meta">{t('vox.aplicatii.fara_apk')}</span>
        : (
          <>
            {c.aplicatie && <b>{c.aplicatie}</b>}
            {(['play', 'app_store'] as const).map((k) => {
              const n = c[k]
              const numeMagazin = t(`vox.aplicatii.magazin.${k}` as DictKey)
              if (!n) return <span key={k} className="vox-meta">{t('vox.aplicatii.fara_magazin', { magazin: numeMagazin })}</span>
              const loc = n.sub_prag
                ? t('vox.aplicatii.card_sub_prag')
                : n.loc == null
                  ? ''
                  : n.loc === n.loc_pana
                    ? t('vox.aplicatii.card_loc', { loc: n.loc, din: n.din ?? 0 })
                    : t('vox.aplicatii.card_loc_egal', { loc: n.loc, pana: n.loc_pana ?? n.loc, din: n.din ?? 0 })
              return (
                <div key={k} className="vox-apl-magazin">
                  <span className="vox-et">{numeMagazin}</span>
                  <span className="nr">{n.nota !== null ? num(n.nota, locale, 1) : '—'}</span>
                  <span className="vox-meta">{t('vox.aplicatii.nr_note', { n: num(n.evaluari, locale, 0) })}{loc ? ` · ${loc}` : ''}</span>
                  <BareStele dist={n.distributie_stele} latime={160} />
                  {n.url && <a className="vox-link" href={n.url} target="_blank" rel="noopener noreferrer">{t('vox.aplicatii.deschide_magazin')}</a>}
                </div>
              )
            })}
          </>
        )}
    </article>
  )
}

function TabelNote({ titlu, c, m }: { titlu: string; c: ClasamentNote | null; m: Meta }) {
  const { t, locale } = useLang()
  const [toate, setToate] = useState(false)
  if (!c) return <p className="vox-nota"><span className="vox-punct gri" />{titlu}: {t('vox.aplicatii.play_lipsa')}</p>
  const vizibile = toate ? c.randuri : c.randuri.filter((r, i) => i < PRIMELE || r.evidentiata)
  const lista = (rs: ClasamentNote['sub_prag']) => rs
    .map((r) => `${m.nume[r.banca] ?? r.banca} (${r.nota_afisata !== null ? num(r.nota_afisata, locale, 1) : '—'}; ${num(r.evaluari, locale, 0)})`)
    .join(', ')
  return (
    <div className="vox-clas-bloc">
      <span className="vox-segment-cap">{titlu}</span>
      <div className="vox-tabel-cutie">
        <table className="vox-tabel vox-clas vox-apl-note">
          <thead>
            <tr>
              <th>{t('vox.clasament.col.loc')}</th>
              <th>{t('vox.clasament.col.banca')}</th>
              <th>{t('vox.aplicatii.col.aplicatia')}</th>
              <th className="dr">{t('vox.aplicatii.col.nota')}</th>
              <th className="dr">{t('vox.aplicatii.col.evaluari')}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {vizibile.map((r) => (
              <tr key={r.banca} className={r.evidentiata ? 'evidentiata' : undefined}>
                <td className="loc">{r.loc === r.loc_pana ? r.loc : `${r.loc}–${r.loc_pana}`}</td>
                <td><EtichetaBanca slug={r.banca} m={m} tag /></td>
                <td>{r.aplicatie ?? '—'}</td>
                <td className="dr val">
                  <Tooltip title={r.nota !== null ? num(r.nota, locale) : ''}>
                    <span className="nr">{r.nota_afisata !== null ? num(r.nota_afisata, locale, 1) : '—'}</span>
                  </Tooltip>
                </td>
                <td className="dr">{num(r.evaluari, locale, 0)}</td>
                <td>{r.url && <a className="vox-link" href={r.url} target="_blank" rel="noopener noreferrer">{t('vox.aplicatii.deschide_magazin')}</a>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {c.randuri.length > vizibile.length && (
        <button type="button" className="vox-link vox-clas-toate" onClick={() => setToate(true)}>
          {t('vox.clasament.arata_toate', { n: c.randuri.length })}
        </button>
      )}
      {c.sub_prag.length > 0 && (
        <p className="vox-nota"><span className="vox-punct gri" />{t('vox.aplicatii.sub_prag', { n: c.sub_prag.length, lista: lista(c.sub_prag) })}</p>
      )}
      {c.fara_nota.length > 0 && (
        <p className="vox-nota"><span className="vox-punct gri" />{t('vox.aplicatii.fara_nota', { n: c.fara_nota.length, lista: lista(c.fara_nota) })}</p>
      )}
    </div>
  )
}

function Neanalizata({ a }: { a: AplicatiiT }) {
  const { t } = useLang()
  const lista = [...(a.functii ?? [])].sort((x, y) => rang(x) - rang(y))
  return (
    <>
      <p className="vox-nota"><span className="vox-punct" />{t('vox.aplicatii.neanalizata', { text: a.text_cautat ?? '' })}</p>
      <ul className="vox-apl-lista">{lista.map((f) => <li key={f}>{etFunctie(f, t)}</li>)}</ul>
    </>
  )
}
```

Dacă `t` din `useLang()` nu se potrivește cu tipul `T` (parametrii lui `t` sunt `Params`), `T` devine `ReturnType<typeof useLang>['t']`.

- [ ] **Step 5: ramura din `Raspuns` (`web/src/pages/Vox.tsx`)**

Importul, lângă `Clasament`: `import Aplicatii from './vox/Aplicatii'`.
În `Raspuns`, imediat după blocul `if (i.tip === 'neclar') { ... }`, înainte de `const filtre = [`:

```tsx
  if (i.tip === 'aplicatii') {
    return (
      <article className="vox-card">
        <div className="vox-inteles">
          <span className="vox-et">{t('vox.am_inteles')}</span>
          <span className="vox-chip">{t(i.aspect === 'note' ? 'vox.aplicatii.chip_note' : 'vox.aplicatii.chip')}</span>
          {i.banci.map((b) => <span key={b} className="vox-chip banca">{m.nume[b] ?? b}</span>)}
          {i.functie && (
            <span className="vox-chip">{areCheie(`mobil.android_fs.${i.functie}`) ? t(`mobil.android_fs.${i.functie}` as DictKey) : i.functie}</span>
          )}
          {i.text_cautat && <span className="vox-chip">{t('vox.text_chip', { text: i.text_cautat })}</span>}
          {i.prag_note != null && <span className="vox-chip">{t('vox.aplicatii.chip_prag', { prag: num(i.prag_note, locale, 0) })}</span>}
        </div>
        {r.ignorate.length > 0 && (
          <p className="vox-nota"><span className="vox-punct" />{t('vox.ignorate', { banci: r.ignorate.map((b) => m.nume[b] ?? b).join(', ') })}</p>
        )}
        {r.aplicatii
          ? <Aplicatii a={r.aplicatii} m={m} />
          : <p className="vox-nota"><span className="vox-punct" />{t('vox.aplicatii.indisponibil')}</p>}
        {butoane}
        <div className="vox-card-jos">{subsol}</div>
      </article>
    )
  }
```

- [ ] **Step 6: stilurile (`web/src/styles/vox.css`)**

La final:

```css
/* Aplicațiile (08.10.2026): verdictele refolosesc .an-v din android.css, clasamentele de note .vox-clas */
.vox-apl-grupe { display: grid; gap: 12px }
.vox-apl-grupa-cap { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 8px; margin-bottom: 6px }
.vox-apl-banci { display: flex; flex-wrap: wrap; gap: 6px }
.vox-apl-banca { display: inline-flex; padding: 2px 10px 2px 4px; border: 1px solid var(--line); border-radius: 999px; background: var(--bg) }
.vox-apl-banca.evidentiata { border-color: var(--accent); background: var(--accent-tint) }
.vox-apl-dovada { display: flex; flex-direction: column; gap: 2px }
.vox-apl-propozitie { margin: 0; font-size: 13.5px; line-height: 1.55 }
.vox-apl-tabel th.vox-apl-col { min-width: 170px; font-family: inherit; font-size: 12px; letter-spacing: 0; text-transform: none; vertical-align: top }
.vox-apl-tabel th .sub, .vox-apl-tabel td .sub { display: block; margin-top: 2px; font-weight: 400; color: var(--muted) }
.vox-apl-tabel td.vox-apl-v { text-align: center }
.vox-apl-tabel tr.dif-sigur td { background: var(--accent-tint) }
.vox-apl-tabel tr.dif-sigur td:first-child { box-shadow: inset 4px 0 var(--accent) }
.vox-apl-tabel tr.dif-probabil td:first-child { box-shadow: inset 4px 0 var(--line-2) }
.vox-apl-tabel tr.evidentiata td:first-child { font-weight: 600 }
.vox-apl-tabel tr.necomparabil td { color: var(--muted) }
.vox-apl-carduri { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 10px }
.vox-apl-card { display: flex; flex-direction: column; gap: 8px; padding: 12px 14px; border: 1px solid var(--line); border-radius: 10px; background: var(--bg) }
.vox-apl-magazin { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 8px }
.vox-apl-magazin .nr { font-family: var(--mono); font-size: 18px }
.vox-apl-lista { margin: 0; padding-left: 20px; columns: 2 220px; font-size: 13px }
```

- [ ] **Step 7: verificările de tip și build-ul de verificare**

Run: `npm run typecheck`
Expected: 0 erori (și verificarea temei trece).

Run: `npm -w web exec -- vite build --outDir "$S/dist_verif" --emptyOutDir`
Expected: build reușit, fără erori.

- [ ] **Step 8: commit**

```bash
printf '%s\n' "web, shared: fișa Vox pentru aplicații: funcția la toate băncile, aplicațiile alături, notele cu întrebarea despre prag" > "$S/mesaj.txt"
git add shared/src/vox.ts web/src/pages/vox/Aplicatii.tsx web/src/pages/Vox.tsx web/src/pages/rate_mobil/android/model.ts web/src/i18n/dict/vox.ts web/src/styles/vox.css
git commit -q -F "$S/mesaj.txt"
```

---

### Task 8: verificarea pe date reale și în pagină

**Files:**
- Create (în `$S`, în afara repo-ului): `cu_server_8797.sh`, `raspunsuri_aplicatii.py`, `verifica_aplicatii_ui.py`

**Interfaces:**
- Consumes: totul de mai sus; baza `mip_merge` (doar citire); :5173 (Vite-ul lui Nicolae, nu se repornește).

- [ ] **Step 1: serverul temporar**

```bash
cat > "$S/cu_server_8797.sh" <<'EOF'
#!/usr/bin/env bash
# Pornește serverul temporar pe :8797 (codul din arbore, Vox oprit), rulează comanda dată, apoi îl oprește.
# Serverele lui Nicolae (:8765, :5173) nu se ating.
SCR="$(cd "$(dirname "$0")" && pwd)"
cd /c/Users/nicolae.cherascu/Desktop/Market-Intelligence-Platform || exit 2
export PYTHONIOENCODING=utf-8
MIP_PORT=8797 MCC_AUTH_LOCAL=admin MIP_PERMITE_VOX=0 python app/server.py > "$SCR/server_8797.log" 2>&1 &
PID=$!
for i in $(seq 1 40); do
  curl -s -o /dev/null -w "%{http_code}" http://localhost:8797/api/sesiune | grep -q 200 && break
  sleep 1
done
"$@"; cod=$?
kill $PID 2>/dev/null
exit $cod
EOF
```

- [ ] **Step 2: răspunsurile reale, cu model fals (`$S/raspunsuri_aplicatii.py`)**

```python
"""Vox · aplicațiile pe baza reală (mip_merge), cu un model fals: criteriile de reușită din spec-ul
2026-10-08-vox-aplicatii-design.md și fișierul pentru verificarea paginii. Niciun apel plătit.

  python raspunsuri_aplicatii.py <iesire.json>
"""
import json, os, sys, tempfile, types
sys.stdout.reconfigure(encoding="utf-8")
RAD = r"C:\Users\nicolae.cherascu\Desktop\Market-Intelligence-Platform"
os.chdir(RAD); sys.path.insert(0, os.path.join(RAD, "app"))
import server, vox


class Fals:
    def __init__(self, interp):
        self.interp, self.messages, self.apeluri = interp, self, 0

    def create(self, **kw):
        self.apeluri += 1
        return types.SimpleNamespace(
            content=[types.SimpleNamespace(type="text", text=json.dumps(self.interp))], stop_reason="end_turn",
            usage=types.SimpleNamespace(input_tokens=12, output_tokens=60, cache_read_input_tokens=13400,
                                        cache_creation_input_tokens=0))


def a(**k):
    b = dict(vox._gol("aplicatii"), aspect="functii")
    b.update(k)
    return b


CAZURI = [
    ("Ce bănci au RoPay?", a(functie="ropay"), ()),
    ("Ce are BT Pay și n-are Libra?", a(banci=["banca-transilvania", "libra"]), ()),
    ("Are George plata contactless?", a(banci=["bcr"], functie="hce_contactless"), ("toate", "libra")),
    ("Ce notă are aplicația Libra?", a(banci=["libra"], aspect="note"), ("toate",)),
    ("Care bancă are cea mai bună aplicație?", a(aspect="note"), ("prag_100", "prag_1000")),
    ("Care e cea mai bine notată aplicație cu cel puțin 1.000 de note?", a(aspect="note", prag_note=1000), ()),
    ("Are BCR Apple Pay?", a(banci=["bcr"], text_cautat="Apple Pay"), ()),
    ("Ce funcții are aplicația PKO?", a(banci=["pko"]), ()),
]
ctx = server._context_vox()
iesire, d = [], {}
for q, interp, apasate in CAZURI:
    client = Fals(interp)
    v = vox.Vox(context=lambda: ctx, cauta=server._cauta_vox, stare_banca=server._stare_banca_vox,
                clasament=server._clasament_vox, stare_banci=server._stare_banci_vox, aplicatii=server._aplicatii_vox,
                client=client, dir_jurnal=tempfile.mkdtemp(prefix="vox_apl_"))
    r = v.intreaba(q)
    caz = {"intrebare": q, "raspuns": r, "butoane": {b: v.continua(r["interpretare"], b, r["conversatie"]) for b in apasate}}
    assert client.apeluri == 1, (q, client.apeluri)          # butoanele nu cheamă modelul
    iesire.append(caz)
    d[q] = caz

# 1. RoPay, pe aplicația principală
g = {x["verdict"]: [y["banca"] for y in x["aplicatii"]] for x in d["Ce bănci au RoPay?"]["raspuns"]["aplicatii"]["grupuri"]}
print("RoPay:", {k: len(v) for k, v in g.items()})
assert set(g["sigur"]) == {"banca-transilvania", "bcr", "brd", "cec", "ing", "raiffeisen", "salt", "vista"}, g
assert g["probabil"] == ["unicredit"], g
assert set(g["absent"]) == {"credex", "garanti", "intesa", "libra", "procredit", "revolut"}, g
assert set(g["neconcludent"]) == {"brci", "citibank", "exim", "nexent", "patria", "tbi", "techventures"}, g
assert len(d["Ce bănci au RoPay?"]["raspuns"]["aplicatii"]["banci_fara_aplicatie"]) == 8
# 2. BT Pay vs Libra
dif = [(x["functie"], x["nivel"], x["au"]) for x in d["Ce are BT Pay și n-are Libra?"]["raspuns"]["aplicatii"]["diferente"]]
print("BT Pay vs Libra:", dif)
assert dif == [("in_app_chat", "probabil", ["banca-transilvania"]), ("marketing", "probabil", ["banca-transilvania"]),
               ("ropay", "sigur", ["banca-transilvania"]), ("voice", "probabil", ["libra"])], dif
# 3. notele Libra
card = d["Ce notă are aplicația Libra?"]["raspuns"]["aplicatii"]["carduri"][0]
cifre = {k: (card[k]["nota"], card[k]["evaluari"], card[k]["loc"], card[k]["loc_pana"], card[k]["din"]) for k in ("play", "app_store")}
print("Libra:", cifre)
assert cifre == {"play": (4.59, 3083, 8, 10, 22), "app_store": (4.47, 971, 10, 11, 19)}, cifre
# 4. clasamentele fără prag și întrebarea despre prag
a4 = d["Care bancă are cea mai bună aplicație?"]["raspuns"]
play = [(r["banca"], r["loc"], r["loc_pana"]) for r in a4["aplicatii"]["clasamente"]["play"]["randuri"]]
ios = [(r["banca"], r["loc"], r["loc_pana"]) for r in a4["aplicatii"]["clasamente"]["app_store"]["randuri"]]
print("Play:", play[:6], "\nApp Store:", ios[:5], "\nputine_note:", a4["aplicatii"]["putine_note"])
assert play[:5] == [("bcr", 1, 5), ("brd", 1, 5), ("ing", 1, 5), ("revolut", 1, 5), ("unicredit", 1, 5)], play
assert ios[:4] == [("procredit", 1, 1), ("citibank", 2, 4), ("ing", 2, 4), ("revolut", 2, 4)], ios
assert a4["aplicatii"]["putine_note"] == {"app_store": 7, "play": 3, "prag": 100, "primul": {
    "magazin": "app_store", "banca": "procredit", "loc": 1, "loc_pana": 1, "evaluari": 6}}
assert a4["butoane"] == ["prag_100", "prag_1000"]
# 5. butoanele de prag
p100 = d["Care bancă are cea mai bună aplicație?"]["butoane"]["prag_100"]["aplicatii"]["clasamente"]
p1000 = d["Care bancă are cea mai bună aplicație?"]["butoane"]["prag_1000"]["aplicatii"]["clasamente"]
cnt = lambda c: (len(c["randuri"]), len(c["sub_prag"]))
libra = lambda c: next(((r["loc"], r["loc_pana"]) for r in c["randuri"] if r["banca"] == "libra"), "sub prag")
print("prag 100:", cnt(p100["play"]), cnt(p100["app_store"]), libra(p100["play"]), libra(p100["app_store"]))
print("prag 1000:", cnt(p1000["play"]), cnt(p1000["app_store"]), libra(p1000["play"]), libra(p1000["app_store"]))
assert cnt(p100["play"]) == (19, 3) and cnt(p100["app_store"]) == (12, 7)
assert cnt(p1000["play"]) == (13, 9) and cnt(p1000["app_store"]) == (8, 11)
assert libra(p100["play"]) == (8, 10) and libra(p100["app_store"]) == (9, 10)
assert libra(p1000["play"]) == (8, 10) and libra(p1000["app_store"]) == "sub prag"
assert [r["banca"] for r in p100["app_store"]["randuri"][:3]] == ["citibank", "ing", "revolut"]
# 6. pragul scris în întrebare = butonul de 1.000
assert d["Care e cea mai bine notată aplicație cu cel puțin 1.000 de note?"]["raspuns"]["aplicatii"]["clasamente"] == p1000
# 7. Apple Pay la BCR, PKO fără aplicație, „La toate băncile” după George
a7 = d["Are BCR Apple Pay?"]["raspuns"]["aplicatii"]
assert (a7["vedere"], a7["text_cautat"], a7["coloane"][0]["aplicatie"]) == ("aplicatii", "Apple Pay", "George Romania"), a7["vedere"]
assert d["Ce funcții are aplicația PKO?"]["raspuns"]["aplicatii"]["coloane"][0]["fara_aplicatie"] is True
t = d["Are George plata contactless?"]["butoane"]["toate"]
assert (t["aplicatii"]["vedere"], t["aplicatii"]["functie"], t["model"], t["cost_usd"]) == ("functie", "hce_contactless", None, 0.0)
json.dump(iesire, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, default=str)
print("OK, cazuri:", len(iesire))
```

Run: `PYTHONIOENCODING=utf-8 python "$S/raspunsuri_aplicatii.py" "$S/raspunsuri_aplicatii.json"`
Expected: `OK, cazuri: 8`, fără `AssertionError`.

- [ ] **Step 3: pagina, cu Playwright (`$S/verifica_aplicatii_ui.py`)**

```python
"""Fișa Vox pentru aplicații, în pagina de pe :5173: cele patru vederi, propoziția diferențelor, nota despre prag și
butoanele, în RO și EN, temă luminoasă și întunecată; API-ul spre serverul temporar :8797, POST /api/vox din
raspunsuri_aplicatii.json. La final, o conversație veche se redeschide. Niciun apel plătit.

  python verifica_aplicatii_ui.py <raspunsuri_aplicatii.json> <dosar capturi>
"""
import json, os, sys
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
CAZURI = json.load(open(sys.argv[1], encoding="utf-8"))
OUT = sys.argv[2]
os.makedirs(OUT, exist_ok=True)
TINTA = "http://localhost:8797"
PE_INTREBARE = {c["intrebare"]: c for c in CAZURI}
ORICARE = CAZURI[0]["raspuns"]
posturi, probleme, erori = [], [], []
TEXTE = {
    "ro": {"propozitie": "Are BT Pay, n-are Libra Bank: RoPay; probabil și Chat, Marketing.",
           "prag": "Ce prag vrei să pui?", "buton": "Cel puțin 100 de note", "activ": "Prag: cel puțin 100 de note",
           "neanalizata": "nu e printre funcțiile analizate"},
    "en": {"propozitie": "BT Pay has, Libra Bank doesn't: RoPay; likely also Chat, Marketing.",
           "prag": "What threshold do you want?", "buton": "At least 100 ratings", "activ": "Threshold: at least 100 ratings",
           "neanalizata": "is not among the analysed features"},
}


def verifica(cond, mesaj):
    if not cond:
        erori.append(mesaj)
        print("   EȘEC:", mesaj)
    return cond


def text(loc):
    return loc.first.inner_text() if loc.count() else ""


def e_server(url):
    c = urlparse(url).path
    return c.startswith(("/api/", "/logos/")) or c == "/pdf"


def json_raspuns(route, corp):
    route.fulfill(status=200, content_type="application/json", body=json.dumps(corp, ensure_ascii=False))


def acelasi(a, b):
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def ruta(route):
    req = route.request
    u = urlparse(req.url)
    if u.path == "/api/vox" and req.method == "GET":
        return json_raspuns(route, {"activ": True, "model": "claude-haiku-4-5", "token": "test"})
    if u.path == "/api/vox" and req.method == "POST":
        corp = json.loads(req.post_data or "{}")
        posturi.append(corp)
        if "buton" in corp:
            caz = next((c for c in CAZURI if acelasi(c["raspuns"]["interpretare"], corp.get("anterior"))), None)
            r = (caz or {}).get("butoane", {}).get(corp["buton"]) or ORICARE
        else:
            r = (PE_INTREBARE.get(corp.get("intrebare")) or {}).get("raspuns") or ORICARE
        return json_raspuns(route, {**r, "conversatie": None})
    if req.method != "GET":
        return route.abort()
    route.fulfill(response=route.fetch(url=TINTA + u.path + (f"?{u.query}" if u.query else "")))


def pagina(b, tema, lang, cale="/vox", astept=".vox-conv-noua"):
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"try {{ localStorage.setItem('mcc-tema', '{tema}'); localStorage.setItem('mcc-lang', '{lang}') }} catch (e) {{}}")
    pg = ctx.new_page()
    pg.on("console", lambda m: probleme.append(f"{lang}/{tema} {m.type}: {m.text}") if m.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: probleme.append(f"{lang}/{tema} pageerror: {e}"))
    pg.route(e_server, ruta)
    pg.goto("http://localhost:5173/#" + cale)
    pg.locator(astept).first.wait_for(timeout=15000)
    return ctx, pg


def asteapta_card_nou(pg, n):
    pg.wait_for_function(f"document.querySelectorAll('.vox-card, .vox-bula').length > {n}", timeout=15000)
    pg.wait_for_timeout(500)
    return pg.locator(".vox-card, .vox-bula").last


def intreaba(pg, q):
    n = pg.locator(".vox-card, .vox-bula").count()
    camp = pg.locator(".vox-cutie textarea")
    camp.fill(q)
    camp.press("Enter")
    return asteapta_card_nou(pg, n)


def captura(pg, loc, nume):
    """Elementul întreg, fără bara de întrebare (sticky); fereastra crește cât elementul pe durata capturii."""
    stil = pg.add_style_tag(content=".vox-compune { position: static !important; background: none !important }")
    fereastra = pg.viewport_size
    pg.set_viewport_size({"width": fereastra["width"], "height": max(fereastra["height"], int(loc.bounding_box()["height"]) + 200)})
    pg.wait_for_timeout(300)
    loc.scroll_into_view_if_needed()
    loc.screenshot(path=os.path.join(OUT, nume))
    pg.set_viewport_size(fereastra)
    stil.evaluate("e => e.remove()")


def verifica_tot(pg, lang, tema):
    T = TEXTE[lang]
    card = intreaba(pg, "Ce bănci au RoPay?")
    verifica(card.locator(".vox-apl-grupa").count() == 4, f"[{lang}/{tema}] RoPay: {card.locator('.vox-apl-grupa').count()} grupe")
    verifica(card.locator(".vox-apl-banca").count() == 22, f"[{lang}/{tema}] RoPay: {card.locator('.vox-apl-banca').count()} bănci")
    verifica(card.locator(".vox-apl-banca.evidentiata").count() == 1, f"[{lang}/{tema}] Libra neevidențiată")
    captura(pg, card, f"ropay_{lang}_{tema}.png")
    card = intreaba(pg, "Ce are BT Pay și n-are Libra?")
    prop = text(card.locator(".vox-apl-propozitie"))
    verifica(T["propozitie"] in prop, f"[{lang}/{tema}] propoziția: {prop!r}")
    sigure, probabile = card.locator("tr.dif-sigur").count(), card.locator("tr.dif-probabil").count()
    verifica((sigure, probabile) == (1, 3), f"[{lang}/{tema}] marcaje: {sigure} sigure, {probabile} probabile")
    captura(pg, card, f"bt_libra_{lang}_{tema}.png")
    card = intreaba(pg, "Care bancă are cea mai bună aplicație?")
    verifica(T["prag"] in text(card.locator(".vox-apl-prag")), f"[{lang}/{tema}] nota despre prag lipsește")
    randuri = card.locator(".vox-apl-note tbody tr").count()
    verifica(randuri == 21, f"[{lang}/{tema}] rânduri vizibile în clasamente: {randuri} (10 + 11, cu Libra)")
    captura(pg, card, f"note_{lang}_{tema}.png")
    n = pg.locator(".vox-card, .vox-bula").count()
    card.locator("button.vox-link", has_text=T["buton"]).click()
    card = asteapta_card_nou(pg, n)
    verifica(posturi[-1].get("buton") == "prag_100" and posturi[-1].get("anterior", {}).get("aspect") == "note",
             f"[{lang}/{tema}] corpul butonului: {posturi[-1]}")
    verifica(T["activ"] in card.inner_text(), f"[{lang}/{tema}] pragul activ nu apare")
    card = intreaba(pg, "Ce notă are aplicația Libra?")
    verifica(card.locator(".vox-apl-card").count() == 1, f"[{lang}/{tema}] cardul Libra lipsește")
    captura(pg, card, f"libra_{lang}_{tema}.png")
    card = intreaba(pg, "Are BCR Apple Pay?")
    verifica(T["neanalizata"] in card.inner_text(), f"[{lang}/{tema}] Apple Pay: lipsește nota de funcție neanalizată")
    card = intreaba(pg, "Ce funcții are aplicația PKO?")
    verifica(card.locator(".vox-apl-tabel").count() == 1, f"[{lang}/{tema}] PKO: tabelul lipsește")


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge")
    for lang, tema in (("ro", "luminos"), ("en", "intunecat")):
        ctx, pg = pagina(b, tema, lang)
        verifica_tot(pg, lang, tema)
        ctx.close()
    ctx, pg = pagina(b, "luminos", "ro", "/vox?c=35b2f7f797944207", ".vox-tura")
    verifica(pg.locator(".vox-tura").count() > 0, "conversația veche nu s-a redeschis")
    ctx.close()
    b.close()
for x in probleme:
    print("CONSOLĂ:", x)
print("erori:", len(erori), "· consolă:", len(probleme))
sys.exit(1 if erori or probleme else 0)
```

Run: `bash "$S/cu_server_8797.sh" env PYTHONIOENCODING=utf-8 python "$S/verifica_aplicatii_ui.py" "$S/raspunsuri_aplicatii.json" "$S/capturi_aplicatii"`
Expected: `erori: 0 · consolă: 0`. Capturile, verificate cu ochii, în `"$S/capturi_aplicatii"`.

Dacă valorile reale pentru teme sau limbă din `localStorage` sunt altele decât `luminos` / `intunecat`, se iau din `web/src/tema/` (scriptul din 08.10 folosea aceleași chei, `mcc-tema` și `mcc-lang`).

- [ ] **Step 4: paginile aplicației, pe serverul temporar**

Run: `bash "$S/cu_server_8797.sh" env MIP_URL=http://localhost:8797 PYTHONIOENCODING=utf-8 python app/verifica_pagini.py`
Expected: toate paginile randate, 0 erori.

- [ ] **Step 5: fără commit** (scripturile stau în `$S`). Ce s-a reparat în cod după verificare intră într-un commit „web: …” sau „app: …”, cu motivul.

---

### Task 9: setul de evaluare (`app/vox_exemple.json`)

**Files:**
- Modify: `app/vox_exemple.json`

- [ ] **Step 1: schimbă cele două așteptări**

```json
  {"intrebare": "Ce notă are aplicația Libra în App Store?",
   "asteptat": {"tip": "aplicatii", "banci": ["libra"], "aspect": "note"}},
```

și

```json
  {"intrebare": "Care bancă are cea mai bună aplicație?",
   "asteptat": {"tip": "aplicatii", "banci": [], "aspect": "note"}}
```

- [ ] **Step 2: adaugă cele 9 întrebări noi** (înainte de `]`; ultima intrare de dinainte primește virgulă)

```json
  {"intrebare": "Ce bănci au RoPay în aplicație?",
   "asteptat": {"tip": "aplicatii", "banci": [], "functie": "ropay", "aspect": "functii"}},
  {"intrebare": "Are George plata contactless?",
   "asteptat": {"tip": "aplicatii", "banci": ["bcr"], "functie": "hce_contactless"}},
  {"intrebare": "Ce funcții are aplicația BRD?",
   "asteptat": {"tip": "aplicatii", "banci": ["brd"], "functie": null, "aspect": "functii"}},
  {"intrebare": "Ce are BT Pay și n-are Libra?",
   "asteptat": {"tip": "aplicatii", "banci": ["banca-transilvania", "libra"], "functie": null, "aspect": "functii"}},
  {"intrebare": "Are BCR Apple Pay?",
   "asteptat": {"tip": "aplicatii", "banci": ["bcr"], "functie": null, "text_cautat_nenul": true}},
  {"intrebare": "Ce scriu clienții despre BT Pay?",
   "asteptat": {"tip": "in_afara"}},
  {"intrebare": "Câte trackere are aplicația ING?",
   "asteptat": {"tip": "in_afara"}},
  {"intrebare": "și la BRD?",
   "anterior": {"tip": "aplicatii", "banci": ["bcr"], "concept": null, "categorie": null, "termen": null, "produs_credit": null, "text_cautat": null, "clarificare": null, "segment": null, "metrica": null, "functie": "hce_contactless", "aspect": "functii", "prag_note": null},
   "asteptat": {"tip": "aplicatii", "banci": ["brd"], "functie": "hce_contactless"}},
  {"intrebare": "Care e cea mai bine notată aplicație cu cel puțin 1.000 de note?",
   "asteptat": {"tip": "aplicatii", "banci": [], "aspect": "note", "prag_note": 1000}}
```

- [ ] **Step 3: numără și cere estimarea (gratis, fără `--da`)**

Run: `PYTHONIOENCODING=utf-8 python -c "import json; print(len(json.load(open('app/vox_exemple.json', encoding='utf-8'))))"`
Expected: `53`.

Run: `PYTHONIOENCODING=utf-8 python app/eval_vox.py`
Expected: numărul de întrebări (53) și estimarea, fără niciun apel la model.

- [ ] **Step 4: commit**

```bash
printf '%s\n' "app: evaluarea Vox are 9 întrebări despre aplicații, iar cele două despre note nu mai așteaptă in_afara" > "$S/mesaj.txt"
git add app/vox_exemple.json && git commit -q -F "$S/mesaj.txt"
```

- [ ] **Step 5: propunerea pentru Nicolae.** Rularea plătită (`python app/eval_vox.py --da`) se face doar cu „da”, după ce i se spune estimarea de la Step 3.

---

### Task 10: documentația

**Files:**
- Modify: `README.md` (secțiunea „Vox”)
- Modify: `CLAUDE.md` (regula Vox; numărul de linii nu crește)
- Modify: `.serena/memories/cod/harta.md` (prin skill-ul `actualizeaza-memoria`)
- Modify: `docs/HANDOFF_VOX.md` (necomis)

- [ ] **Step 1: README.** În secțiunea Vox, fraza „Aplicațiile și campaniile nu intră: pagina răspunde că sunt în afara ei.” devine „Campaniile și recenziile nu intră: pagina răspunde că sunt în afara ei.”. După punctul „De ce lipsește o bancă”, un punct nou:

```markdown
- **Aplicațiile** (08.10.2026). „Ce bănci au RoPay?”, „Ce are BT Pay și n-are Libra?”, „Ce notă are aplicația
  Libra?”, „Care bancă are cea mai bună aplicație?”: tipul `aplicatii`. Funcțiile vin din analiza APK (24 de
  aplicații, 13 funcții, cu verdictul paginii Android: „sigur”, „probabil”, „absent”, „neconcludent”), notele din App
  Store (în bază, 19 aplicații, 24.09.2026) și din Google Play (`date/google_play.json`, 22 de aplicații, 06.10.2026;
  fără fișier, fișa spune „Google Play necolectat”). Diferențele dintre două aplicații sunt pe două niveluri: „sigur”
  față de „absent” e o diferență sigură, „probabil” față de „absent” una probabilă; „neconcludent” nu se compară
  (BT Pay vs Libra: RoPay sigură; chatul, marketingul și asistentul vocal probabile). Clasamentul notelor n-are prag:
  nota se compară rotunjită la o zecimală, cu loc comun (în Google Play, BCR, BRD, ING, Revolut și UniCredit au toate
  4,8). ProCredit e pe locul 1 în App Store cu 5,0 din 6 note, deci fișa spune asta și întreabă ce prag vrei, cu
  butoanele „Cel puțin 100 de note” (App Store: 12 aplicații clasate, 7 sub prag) și „Cel puțin 1.000 de note” (App
  Store: 8; Libra, cu 971, iese sub prag). Pragul se poate scrie și în întrebare.
```

Ultima frază din punctul despre evaluare primește numărul nou de întrebări (53) doar după o rulare plătită aprobată. Până atunci, rămâne cifra măsurată (44 din 44).

- [ ] **Step 2: CLAUDE.md.** Cele patru linii ale regulii Vox devin (tot patru linii):

```markdown
Tot cu o variabilă, `MIP_PERMITE_VOX=1` (și o cheie reală), `POST /api/vox` cheamă
modelul doar ca să interpreteze întrebarea (`app/vox.py`): nu scrie în bază, iar cifrele vin
din bază (notele Google Play din `date/google_play.json`, ca 2.3), niciodată de la model.
Conversațiile lui Vox sunt fișiere pe laptop, în `loguri/vox/conversatii/`, nu în bază.
```

Run: `wc -l CLAUDE.md` înainte și după. Expected: același număr de linii.

- [ ] **Step 3: harta Serena.** Invocă skill-ul `actualizeaza-memoria`, care ia commit-urile de la `stare/ultima_actualizare` încoace. În linia Vox din `cod/harta` trebuie să apară:
  - tipul `aplicatii`, cu `functie` / `aspect` / `prag_note`;
  - `_aplicatii_vox` și `FISIER_GOOGLE_PLAY` din server;
  - `clasa_note`, `putine_note` și `diferente`;
  - butoanele `toate`, `prag_100`, `prag_1000` și `fara_prag`;
  - fișa `web/src/pages/vox/Aplicatii.tsx`.

- [ ] **Step 4: handoff.** În `docs/HANDOFF_VOX.md`:
  - „Ce știe Vox acum” primește aplicațiile, în două rânduri;
  - la „Ce urmează”, ideea 4 se marchează făcută pentru aplicații (campaniile n-au date: 0 rânduri în `mip_merge`);
  - se notează schimbările de preț: vederea `schimbari_pret` are 783 de perechi false din 900 (08.10.2026).
  - Fișierul rămâne necomis.

- [ ] **Step 5: verificările finale și commit-ul**

Run: `PYTHONIOENCODING=utf-8 python app/test_vox.py && PYTHONIOENCODING=utf-8 python app/test_celula.py && PYTHONIOENCODING=utf-8 python app/test_rulari.py && PYTHONIOENCODING=utf-8 python app/test_autentificare.py && PYTHONIOENCODING=utf-8 python app/test_server_autentificare.py && PYTHONIOENCODING=utf-8 python app/test_pdf_proxy.py && npm run typecheck`
Expected: OK peste tot.

```bash
printf '%s\n' "docs, serena: Vox răspunde despre aplicații; regula „cifrele din bază” cuprinde notele Google Play din date/" > "$S/mesaj.txt"
git add README.md CLAUDE.md .serena/memories && git commit -q -F "$S/mesaj.txt"
```
