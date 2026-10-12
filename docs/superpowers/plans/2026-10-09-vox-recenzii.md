# Vox: recenziile aplicațiilor — planul de implementare

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Vox arată recenziile aplicațiilor, așa cum le-au scris clienții: la o bancă, căutate după cuvinte la o bancă sau la toate, cu Libra alături. Modelul nu rezumă nimic.

**Architecture:**
- **Tipul existent `aplicatii`** primește `aspect = recenzii`. `text_cautat` ține cuvintele căutate.
- **Cititorul `_aplicatii_vox(cu_recenzii=True)`** aduce recenziile din App Store (`app_review`) și din Google Play (`date/google_play_recenzii.json`).
- **Funcțiile pure din `vox.py`** potrivesc recenziile, la început de cuvânt, și construiesc vederea `recenzii`.
- **Interfața:** o componentă nouă, `pages/vox/Recenzii.tsx`, refolosește `CardRecenzie` din 2.3.

**Tech Stack:** Python 3.12 (`unittest`, psycopg2), Anthropic SDK (Haiku 4.5), React 18 + AntD 5 + Zod, Playwright (Edge).

**Spec:** `docs/superpowers/specs/2026-10-09-vox-recenzii-design.md`

**`S`** e dosarul temporar al sesiunii (Git Bash):
`S="C:/Users/NICOLA~1.CHE/AppData/Local/Temp/claude/c--Users-nicolae-cherascu-Desktop-Market-Intelligence-Platform/2a9027a5-dce6-4121-9bd5-057bfc4e8009/scratchpad"`.
Acolo stau deja `cu_server_8797.sh`, `raspunsuri_aplicatii.py`, `verifica_aplicatii_ui.py` și `test_tintit.py`, din planul aplicațiilor.

**Decizii luate la scrierea planului** (spec-ul rămâne autoritatea):
- **Textul promptului.** Recenziile intră în fraza despre `aspect` din regula `aplicatii`, acolo unde precizarea „(stelele și numărul de note)” nu a stricat nimic. Nu intră în capul regulii, unde o frază a stricat întrebarea #36 pe 09.10.2026.
  - Fraza „cele despre recenzii sau campanii rămân in_afara”, din regula „care bancă…”, devine „cele despre campanii rămân in_afara”. Altfel promptul s-ar contrazice.
- **`play = None` înseamnă doar „fișierul lipsește”.** O bancă fără recenzii în fișier are `{"recenzii": [], "din": 0}`.
- **`evidentiata` e adevărat doar la Libra**, în ambele moduri: cu bănci și doar cu căutare.
- **Jurnalul:** `rand["aplicatii"]` = câte blocuri arată răspunsul, iar `rand["recenzii"]` = câte recenzii.
- **La zero potriviri la o bancă**, blocul spune o singură frază pe bancă, de pildă „Nicio recenzie din eșantion nu conține «logare» (28 de recenzii la Libra Internet Bank)”, nu câte o frază pe magazin.

## Global Constraints

- **Apelurile plătite.** Niciunul fără „da” explicit de la Nicolae, cu costul spus înainte. Task 9 se oprește și întreabă: testul țintit costă ~$0,05, evaluarea completă ~$0,10 (pe 09.10.2026, 53 de întrebări au costat $0,0972).
- **Testele și verificările de interfață** nu cheamă modelul: `ClientFals`, model fals în scripturi, `POST /api/vox` răspuns din fișier în Playwright.
- **Serverele lui Nicolae (:8765, :5173)** nu se opresc. `npm run build` nu se rulează; build-ul de verificare merge în `"$S/dist_verif"`.
- **Serverul rămâne read-only**, cu SQL fix, fără parametri veniți din cerere.
- **Valorile fixe:** `ASPECTE = ("functii", "note", "recenzii")`; `FISIER_GOOGLE_PLAY_RECENZII` = `date/google_play_recenzii.json`; 5 recenzii vizibile pe magazin; texte scurtate la 400 de caractere.
- **Potrivirea:** fiecare rădăcină din `cuvinte_cautare(text_cautat)` e începutul unui cuvânt din text, fără diacritice și cu litere mici. Fără cuvinte, totul se potrivește.
- **Codul și textele:**
  - identificatorii sunt în română, fără diacritice;
  - textele trec prin `t`, ca perechi `[română, engleză]`; recenziile nu se traduc;
  - niciun pachet nou.
- **Comentariile și commit-urile.** Un comentariu spune de ce, cu cifra măsurată (09.10.2026). Commit-urile au forma „zonă: ce și de ce”, fără `Co-Authored-By`, cu `git commit -F "$S/mesaj.txt"`.
- **Rularea.** Scripturile Python merg cu `PYTHONIOENCODING=utf-8 python`, din rădăcina repo-ului. Nu se citește `.env`.

## Review Focus

1. **O recenzie din fișier cu tipuri greșite** (nota „5” ca text, textul număr, fără dată) se sare, fără 500 și fără o conversație care nu se mai deschide. Testul: `test_google_play_recenzii_tipuri_gresite` (Task 4).
2. **Fișierul de recenzii Google Play lipsește:** fișa arată App Store și „Google Play necolectat”. Testele: `test_recenzii_fara_google_play` (Task 5) și cazul din Playwright (Task 7).
3. **Căutarea prinde cuvinte fără legătură** („lent” în „excelent”), în server sau la îngroșarea din pagină. Testul: `test_potrivire_la_inceput_de_cuvant` (Task 3) și verificarea textului îngroșat din Playwright (Task 7).
4. **Schimbarea de prompt strică o întrebare fără legătură**, cum s-a întâmplat la #36 pe 09.10.2026. Verificarea: testul țintit cu #36, înaintea evaluării complete (Task 9).
5. **O conversație salvată înainte**, cu `aspect` doar `functii` / `note` și fără `blocuri`, se redeschide. Verificarea: conversația `35b2f7f797944207` în Playwright (Task 7).

---

### Task 1: contractul (`ASPECTE`, `_aplicatii_curat`)

**Files:**
- Modify: `app/vox.py` (`ASPECTE`; `_aplicatii_curat`)
- Test: `app/test_vox.py` (clasa `ValidareAplicatii`)

**Interfaces:**
- Produces: `vox.ASPECTE` cu `recenzii`. `valideaza` acceptă `aspect = recenzii`: golește `functie` și `prag_note`, iar fără bancă și fără text dă `neclar`.

- [ ] **Step 1: testele care pică.** Metode noi în `ValidareAplicatii`:

```python
    def test_recenzii_cu_banca_sau_cautare(self):
        i, _ = vox.valideaza(apl(banci=["bcr"], aspect="recenzii"), CTX)
        self.assertEqual((i["tip"], i["aspect"], i["banci"]), ("aplicatii", "recenzii", ["bcr"]))
        i, _ = vox.valideaza(apl(banci=[], aspect="recenzii", text_cautat="logare"), CTX)
        self.assertEqual((i["tip"], i["aspect"], i["text_cautat"]), ("aplicatii", "recenzii", "logare"))

    def test_recenzii_golesc_functia_si_pragul(self):
        """„Ce scriu clienții despre RoPay?”: ce se caută în recenzii stă în text_cautat, nu în functie."""
        i, _ = vox.valideaza(apl(banci=["bcr"], aspect="recenzii", functie="ropay", prag_note=100), CTX)
        self.assertEqual((i["aspect"], i["functie"], i["prag_note"]), ("recenzii", None, None))

    def test_recenzii_fara_nimic_e_neclar(self):
        """„Ce scriu clienții?”: fără aplicație și fără ce se caută, recenziile tuturor celor 22 de aplicații ar fi
        peste 500 de carduri."""
        for brut in (apl(banci=[], aspect="recenzii"), apl(banci=[], aspect="recenzii", text_cautat="AI")):
            i, _ = vox.valideaza(brut, CTX)
            self.assertEqual((i["tip"], i["aspect"]), ("neclar", None), brut)

    def test_schema_are_recenzii(self):
        self.assertEqual(vox.schema(CTX)["properties"]["aspect"]["anyOf"][0]["enum"], ["functii", "note", "recenzii"])
```

- [ ] **Step 2: rulează și vezi că pică.**
Run: `PYTHONIOENCODING=utf-8 python app/test_vox.py ValidareAplicatii`
Expected: FAIL (`recenzii` nu e în `ASPECTE`, deci valideaza dă `neclar`).

- [ ] **Step 3: implementarea.** `ASPECTE = ("functii", "note", "recenzii")`, cu comentariul de deasupra completat: „…, notele din magazine sau recenziile (decizia lui Nicolae, 09.10.2026)”. În `_aplicatii_curat`, blocul `if curat["functie"]: … elif curat["aspect"] != "note": …` devine:

```python
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
```

- [ ] **Step 4: toate testele.**
Run: `PYTHONIOENCODING=utf-8 python app/test_vox.py`
Expected: OK.

- [ ] **Step 5: commit.**
```bash
printf '%s\n' "app: Vox primește aspect = recenzii, cu banca sau cuvintele căutate; fără ele, cere lămurire" > "$S/mesaj.txt"
git add app/vox.py app/test_vox.py && git commit -q -F "$S/mesaj.txt"
```

---

### Task 2: promptul

**Files:**
- Modify: `app/vox.py` (`prompt`)
- Test: `app/test_vox.py` (`Schema.test_prompt_aplicatii`)

- [ ] **Step 1: testul care pică.** În `test_prompt_aplicatii`, aserțiunea
`self.assertIn("recenziile aplicațiilor și ce scriu sau spun clienții despre o aplicație, trackere, permisiuni, " "campanii", text)`
devine:

```python
        # recenziile sunt răspuns din 09.10.2026 (aspect = recenzii); in_afara rămâne pentru ce nu avem deloc
        self.assertIn("aspect = recenzii pentru ce scriu sau spun clienții despre o aplicație (recenzii, comentarii, "
                      "păreri, plângeri)", text)
        self.assertIn("text_cautat = cuvintele căutate în recenzii", text)
        self.assertIn("tip = in_afara: orice altceva (trackere, permisiuni, campanii", text)
        self.assertNotIn("cele despre recenzii sau campanii rămân in_afara", text)
```

- [ ] **Step 2: rulează și vezi că pică.**
Run: `PYTHONIOENCODING=utf-8 python app/test_vox.py Schema`
Expected: FAIL.

- [ ] **Step 3: implementarea** în `prompt`:
1. `"aplicație?”) sunt aplicatii, iar cele despre recenzii sau campanii rămân in_afara. "` devine
   `"aplicație?”) sunt aplicatii, iar cele despre campanii rămân in_afara. "`.
2. Descrierea de la început: `"Android și notele din magazine (Google Play, App Store).",` devine
   `"Android, notele din magazine (Google Play, App Store) și recenziile lor.",`.
3. Fraza despre `aspect`:
```python
        "aspect = note pentru notă (stelele și numărul de note) și clasamentul ei („cea mai bună aplicație” = cea mai "
        "bună notă); aspect = recenzii pentru ce scriu sau spun clienții despre o aplicație (recenzii, comentarii, "
        "păreri, plângeri), cu functie = null și text_cautat = cuvintele căutate în recenzii, doar dacă întrebarea "
        "caută ceva anume („Se plâng clienții de logare la Libra?” → logare); altfel "
```
   Rândul următor (`"functii. prag_note = …`) rămâne neschimbat.
4. Regula `in_afara`:
```python
        "- tip = in_afara: orice altceva (trackere, permisiuni, campanii, sfaturi, texte de scris, întrebări "
        "generale).",
```

- [ ] **Step 4: toate testele.** Run: `PYTHONIOENCODING=utf-8 python app/test_vox.py` → OK.

- [ ] **Step 5: commit.**
```bash
printf '%s\n' "app: promptul Vox trimite ce scriu clienții la aspect = recenzii, nu la in_afara" > "$S/mesaj.txt"
git add app/vox.py app/test_vox.py && git commit -q -F "$S/mesaj.txt"
```

---

### Task 3: potrivirea (`potriveste_recenzia`)

**Files:**
- Modify: `app/vox.py` (`potriveste_recenzia`, nou, după `cuvinte_cautare`)
- Test: `app/test_vox.py` (clasa nouă `PotrivireRecenzii`, după `CuvinteCautare`)

**Interfaces:**
- Produces: `vox.potriveste_recenzia(text, cuvinte) -> bool`.

- [ ] **Step 1: testele care pică.**

```python
class PotrivireRecenzii(unittest.TestCase):
    """Căutarea în recenzii (09.10.2026): rădăcina trebuie să fie începutul unui cuvânt."""

    def test_potrivire_la_inceput_de_cuvant(self):
        """Cu subșir, „lentă” (rădăcina „lent”) potrivea 13 recenzii, dintre care 12 erau „excelent”."""
        lent = vox.cuvinte_cautare("lentă")
        self.assertFalse(vox.potriveste_recenzia("Excelentă aplicație!", lent))
        self.assertTrue(vox.potriveste_recenzia("Aplicația e lentă", lent))

    def test_flexiune_si_diacritice(self):
        self.assertTrue(vox.potriveste_recenzia("Logarea nu merge", vox.cuvinte_cautare("logare")))
        self.assertTrue(vox.potriveste_recenzia("Nu pot face plăți", vox.cuvinte_cautare("plati")))

    def test_toate_cuvintele(self):
        c = vox.cuvinte_cautare("card blocat")
        self.assertTrue(vox.potriveste_recenzia("Mi-a blocat cardul", c))
        self.assertFalse(vox.potriveste_recenzia("Cardul merge", c))

    def test_fara_cuvinte_totul_se_potriveste(self):
        self.assertTrue(vox.potriveste_recenzia("orice", []))
        self.assertTrue(vox.potriveste_recenzia(None, []))
        self.assertFalse(vox.potriveste_recenzia(None, ["card"]))
```

- [ ] **Step 2: rulează și vezi că pică.**
Run: `PYTHONIOENCODING=utf-8 python app/test_vox.py PotrivireRecenzii` → FAIL (`AttributeError`).

- [ ] **Step 3: implementarea**, după `cuvinte_cautare`:

```python
def potriveste_recenzia(text, cuvinte):
    """Adevărat dacă fiecare cuvânt căutat (rădăcina din `cuvinte_cautare`) e începutul unui cuvânt din recenzie. Subșirul
    nu ajunge: „lentă” (rădăcina „lent”) potrivea 13 recenzii, dintre care 12 erau „excelent” (09.10.2026)."""
    if not cuvinte:
        return True
    norm = (text or "").lower().translate(DIACRITICE)
    return all(re.search(r"\b" + re.escape(c), norm) for c in cuvinte)
```

- [ ] **Step 4: toate testele.** → OK.

- [ ] **Step 5: commit.**
```bash
printf '%s\n' "app: căutarea în recenzii cere începutul cuvântului; cu subșir, „lentă” prindea „excelent”" > "$S/mesaj.txt"
git add app/vox.py app/test_vox.py && git commit -q -F "$S/mesaj.txt"
```

---

### Task 4: cititorul (`app/server.py`)

**Files:**
- Modify: `app/server.py` (`FISIER_GOOGLE_PLAY_RECENZII`, `_recenzie_play`, `_google_play_recenzii`, noi, după `_google_play`; `_aplicatii_vox(cu_recenzii=False)`)
- Test: `app/test_vox.py` (clasa `CititoriAplicatii`)

**Interfaces:**
- Produces: `server._aplicatii_vox(cu_recenzii=False)`. Cu `True` mai întoarce:
  - `recenzii_app_store: [{banca, nota, versiune, text, data, raspuns_banca}]`, cele mai noi întâi;
  - `recenzii_play: None | {"colectat_la", "aplicatii": {slug: [{nota, text, data, versiune, raspuns_banca, raspuns_data}]}}`.

- [ ] **Step 1: testele care pică.**
  - În `CititoriAplicatii.setUp`, `self.vechi` primește și `server.FISIER_GOOGLE_PLAY_RECENZII`.
  - `tearDown` îl reface.
  - `baza` primește, înaintea lui `return []`:

```python
        if "FROM app_review" in sql:
            return [{"banca": "bcr", "nota": 1, "versiune": "26.30", "text": "Logarea nu merge",
                     "data": "2026-09-20", "raspuns_banca": None}]
```

Metode noi:

```python
    def recenzii(self, continut):
        cale = os.path.join(self.dir, "google_play_recenzii.json")
        with open(cale, "w", encoding="utf-8") as f:
            f.write(continut)
        self.s.FISIER_GOOGLE_PLAY_RECENZII = cale

    def test_recenzii_doar_la_cerere(self):
        self.s.interoghează = self.baza
        self.s.FISIER_GOOGLE_PLAY = os.path.join(self.dir, "nu_exista.json")
        self.recenzii(json.dumps({"colectat_la": "2026-10-06T09:39:43Z", "aplicatii": {"bcr": {"package": "x", "recenzii": [
            {"nota": 2, "text": "lentă", "data": "2026-10-01", "versiune": "1", "raspuns_banca": None, "raspuns_data": None}]}}}))
        self.assertNotIn("recenzii_play", self.s._aplicatii_vox())
        d = self.s._aplicatii_vox(cu_recenzii=True)
        self.assertEqual(d["recenzii_app_store"][0]["text"], "Logarea nu merge")
        self.assertEqual(d["recenzii_play"], {"colectat_la": "2026-10-06", "aplicatii": {"bcr": [
            {"nota": 2, "text": "lentă", "data": "2026-10-01", "versiune": "1", "raspuns_banca": None, "raspuns_data": None}]}})

    def test_google_play_recenzii_tipuri_gresite(self):
        """Fișierul nu e în bază, deci nimic nu-l validează: o intrare greșită nu trebuie să dea 500 și nici să strice o
        conversație salvată (revizia din 08.10.2026, la note)."""
        bune = {"nota": 5, "text": "ok", "data": "2026-10-01"}
        rele = [{"nota": "5", "text": "x", "data": "2026-10-01"}, {"nota": 6, "text": "x", "data": "2026-10-01"},
                {"nota": True, "text": "x", "data": "2026-10-01"}, {"nota": 4, "text": 123, "data": "2026-10-01"},
                {"nota": 4, "text": "x"}, "nu e obiect"]
        self.recenzii(json.dumps({"aplicatii": {"bcr": {"recenzii": [bune, *rele]}, "brd": {"recenzii": "nu e listă"}}}))
        d = self.s._google_play_recenzii()
        self.assertEqual([r["text"] for r in d["aplicatii"]["bcr"]], ["ok"])
        self.assertNotIn("brd", d["aplicatii"])
        self.s.FISIER_GOOGLE_PLAY_RECENZII = os.path.join(self.dir, "lipsa.json")
        self.assertIsNone(self.s._google_play_recenzii())
        self.recenzii("{")
        self.assertIsNone(self.s._google_play_recenzii())
```

- [ ] **Step 2: rulează și vezi că pică.**
Run: `PYTHONIOENCODING=utf-8 python app/test_vox.py CititoriAplicatii`
Expected: FAIL (`AttributeError: ... FISIER_GOOGLE_PLAY_RECENZII`).

- [ ] **Step 3: implementarea**, după `_google_play`:

```python
# Recenziile din Google Play (ingest/google_play_app.mjs --salveaza), același fișier pe care 2.3 îl citește la build:
# 394 de recenzii la 22 de aplicații, cel mult 20 pe aplicație, autorii pseudonimizați (06.10.2026)
FISIER_GOOGLE_PLAY_RECENZII = os.path.join(os.path.dirname(AICI), "date", "google_play_recenzii.json")


def _recenzie_play(r):
    """O recenzie din fișier sau None dacă are tipuri greșite: fișierul nu e în bază, deci nimic altceva nu-l validează."""
    if not isinstance(r, dict):
        return None
    nota, text, data = r.get("nota"), r.get("text"), r.get("data")
    if isinstance(nota, bool) or not isinstance(nota, int) or not 1 <= nota <= 5:
        return None
    if not (text is None or isinstance(text, str)) or not isinstance(data, str):
        return None

    def txt(k):
        v = r.get(k)
        return v if isinstance(v, str) else None

    return {"nota": nota, "text": text, "data": data[:10], "versiune": txt("versiune"),
            "raspuns_banca": txt("raspuns_banca"), "raspuns_data": (txt("raspuns_data") or "")[:10] or None}


def _google_play_recenzii():
    """{colectat_la, aplicatii: {slug: [recenzie]}} sau None dacă fișierul lipsește ori nu are forma așteptată."""
    try:
        with open(FISIER_GOOGLE_PLAY_RECENZII, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(d, dict) or not isinstance(d.get("aplicatii"), dict):
        return None
    aplicatii = {}
    for slug, a in d["aplicatii"].items():
        lista = a.get("recenzii") if isinstance(a, dict) else None
        if isinstance(lista, list):
            aplicatii[slug] = [x for x in map(_recenzie_play, lista) if x]
    return {"colectat_la": str(d.get("colectat_la") or "")[:10] or None, "aplicatii": aplicatii}
```

`_aplicatii_vox` primește parametrul `cu_recenzii=False`. Corpul construiește `rez = {...}` (dicționarul de azi), apoi:

```python
    if cu_recenzii:
        # doar la aspect = recenzii: celelalte vederi nu le citesc (109 rânduri App Store, 394 Google Play)
        rez["recenzii_app_store"] = interoghează(
            """SELECT b.slug AS banca, v.rating AS nota, v.versiune, v.text, v.postat_la::date::text AS data,
                      nullif(v.raspuns_banca, '') AS raspuns_banca
               FROM app_review v JOIN banci b ON b.id = v.id_banca
               ORDER BY v.postat_la DESC NULLS LAST""")
        rez["recenzii_play"] = _google_play_recenzii()
    return rez
```

- [ ] **Step 4: testele, apoi baza reală.**
Run: `PYTHONIOENCODING=utf-8 python app/test_vox.py` → OK.
Run: `PYTHONIOENCODING=utf-8 python -c "import sys; sys.path.insert(0, 'app'); import server; d = server._aplicatii_vox(cu_recenzii=True); print(len(d['recenzii_app_store']), sum(map(len, d['recenzii_play']['aplicatii'].values())), d['recenzii_play']['colectat_la'])"`
Expected: `109 394 2026-10-06`.

- [ ] **Step 5: commit.**
```bash
printf '%s\n' "app: serverul dă lui Vox recenziile, la cerere: App Store din bază, Google Play din date/, cu tipurile verificate" > "$S/mesaj.txt"
git add app/server.py app/test_vox.py && git commit -q -F "$S/mesaj.txt"
```

---

### Task 5: vederea `recenzii` și butoanele

**Files:**
- Modify: `app/vox.py` (`_recenzii_raspuns`, nou, după `_cate_aplicatii`; `_cate_aplicatii`; `Vox._aplicatii_raspuns`; `Vox._raspunde`; `_butoane_aplicatii`; `_din_buton_aplicatii`)
- Test: `app/test_vox.py` (`RECENZII`, nou, după `APLICATII`; `RaspunsAplicatii.setUp` și `fa`; metode noi; `ButoaneAplicatii`)

**Interfaces:**
- Consumes: `potriveste_recenzia` (Task 3); forma din Task 4.
- Produces: vederea `recenzii`, cu `blocuri: [{banca, aplicatie, fara_aplicatie, evidentiata, play: None | {recenzii, din}, app_store: {recenzii, din}}]`, `cuvinte`, `fara_potriviri`, `play_la`.
  - Fiecare recenzie are `nota`, `text`, `data`, `versiune`, `raspuns_banca` și, la Google Play, `raspuns_data`.
  - Butonul `toate` merge la recenzii doar cu `text_cautat`.

- [ ] **Step 1: testele care pică.** După `APLICATII`:

```python
RECENZII = {
    "recenzii_app_store": [
        {"banca": "bcr", "nota": 1, "versiune": "26.30", "text": "Logarea nu merge după actualizare",
         "data": "2026-09-20", "raspuns_banca": "Ne pare rău, scrieți-ne."},
        {"banca": "libra", "nota": 5, "versiune": "4.23", "text": "Excelentă aplicație", "data": "2025-01-10",
         "raspuns_banca": None},
    ],
    "recenzii_play": {"colectat_la": "2026-10-06", "aplicatii": {
        "bcr": [{"nota": 5, "text": "Super", "data": "2026-09-01", "versiune": "26.29", "raspuns_banca": "Mulțumim!",
                 "raspuns_data": "2026-09-02"},
                {"nota": 2, "text": "Aplicația e lentă la logare", "data": "2026-10-01", "versiune": "26.30",
                 "raspuns_banca": None, "raspuns_data": None}],
        "libra": [{"nota": 5, "text": "Excelent, rapidă", "data": "2026-10-04", "versiune": "4.23.0",
                   "raspuns_banca": None, "raspuns_data": None}],
        "brd": [{"nota": 1, "text": "Nu pot face transfer", "data": "2026-09-30", "versiune": "16.3",
                 "raspuns_banca": None, "raspuns_data": None}]}},
}
```

În `RaspunsAplicatii`:
- `setUp` ia `self.date = json.loads(json.dumps({**APLICATII, **RECENZII}))`;
- în `fa`, `aplicatii=(lambda: self.date)` devine `aplicatii=(lambda **k: self.date)`.

Metode noi:

```python
    def test_recenzii_unei_banci(self):
        d, _ = self.fa(apl(banci=["bcr"], aspect="recenzii"))
        a = d["aplicatii"]
        self.assertEqual((a["vedere"], a["cuvinte"], a["play_la"]), ("recenzii", [], "2026-10-06"))
        b = a["blocuri"][0]
        self.assertEqual((b["banca"], b["aplicatie"], b["fara_aplicatie"], b["evidentiata"]),
                         ("bcr", "George Romania", False, False))
        self.assertEqual([r["data"] for r in b["play"]["recenzii"]], ["2026-10-01", "2026-09-01"])   # cele mai noi întâi
        self.assertEqual((b["play"]["din"], b["app_store"]["din"], b["app_store"]["recenzii"][0]["nota"]), (2, 1, 1))
        self.assertNotIn("banca", b["app_store"]["recenzii"][0])
        self.assertEqual(d["butoane"], ["libra"])                       # fără căutare, fără „La toate băncile”

    def test_recenzii_cautare_la_o_banca(self):
        d, _ = self.fa(apl(banci=["bcr"], aspect="recenzii", text_cautat="logare"))
        b = d["aplicatii"]["blocuri"][0]
        self.assertEqual(d["aplicatii"]["cuvinte"], ["loga"])
        self.assertEqual(([r["text"] for r in b["play"]["recenzii"]], b["play"]["din"]),
                         (["Aplicația e lentă la logare"], 2))
        self.assertEqual([r["text"] for r in b["app_store"]["recenzii"]], ["Logarea nu merge după actualizare"])
        self.assertEqual(d["butoane"], ["libra", "toate"])

    def test_recenzii_cautare_la_toate(self):
        """„lentă” la toate: BCR are „lentă”; Libra are doar „Excelent…”, care nu se potrivește."""
        d, _ = self.fa(apl(banci=[], aspect="recenzii", text_cautat="lentă"))
        a = d["aplicatii"]
        self.assertEqual([b["banca"] for b in a["blocuri"]], ["bcr"])
        self.assertEqual(a["fara_potriviri"], 2)                         # brd și libra, căutate fără rezultat
        self.assertEqual(d["butoane"], [])

    def test_recenzii_zero_potriviri(self):
        d, _ = self.fa(apl(banci=["libra"], aspect="recenzii", text_cautat="logare"))
        b = d["aplicatii"]["blocuri"][0]
        self.assertEqual((b["play"]["recenzii"], b["play"]["din"], b["app_store"]["recenzii"], b["app_store"]["din"]),
                         ([], 1, [], 1))
        self.assertTrue(b["evidentiata"])

    def test_recenzii_fara_google_play(self):
        self.date["recenzii_play"] = None
        d, _ = self.fa(apl(banci=["bcr"], aspect="recenzii"))
        b = d["aplicatii"]["blocuri"][0]
        self.assertEqual((b["play"], d["aplicatii"]["play_la"], b["app_store"]["din"]), (None, None, 1))

    def test_recenzii_banca_fara_aplicatie(self):
        d, _ = self.fa(apl(banci=["ing"], aspect="recenzii"))
        b = d["aplicatii"]["blocuri"][0]
        self.assertEqual((b["fara_aplicatie"], b["play"], b["app_store"]), (True, {"recenzii": [], "din": 0},
                                                                          {"recenzii": [], "din": 0}))

    def test_recenzii_in_jurnal(self):
        d, _ = self.fa(apl(banci=["bcr"], aspect="recenzii"))
        with open(os.path.join(self.dir, vox._acum()[:7] + ".jsonl"), encoding="utf-8") as f:
            rand = json.loads(f.readlines()[-1])
        self.assertEqual((rand["aplicatii"], rand["recenzii"]), (1, 3))
```

În `ButoaneAplicatii`:

```python
    def test_butoane_recenzii(self):
        rec = {"vedere": "recenzii"}
        self.assertEqual(vox.butoane(apl(banci=["bcr"], aspect="recenzii"), [], None, rec), ["libra"])
        self.assertEqual(vox.butoane(apl(banci=["bcr"], aspect="recenzii", text_cautat="logare"), [], None, rec),
                         ["libra", "toate"])
        n = vox.din_buton(apl(banci=["bcr"], aspect="recenzii", text_cautat="logare"), "toate")
        self.assertEqual((n["banci"], n["text_cautat"], n["aspect"]), ([], "logare", "recenzii"))
        with self.assertRaises(vox.Respins):
            vox.din_buton(apl(banci=["bcr"], aspect="recenzii"), "toate")
```

- [ ] **Step 2: rulează și vezi că pică.**
Run: `PYTHONIOENCODING=utf-8 python app/test_vox.py RaspunsAplicatii ButoaneAplicatii`
Expected: FAIL (vederea `recenzii` nu există).

- [ ] **Step 3: implementarea.** După `_cate_aplicatii`:

```python
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
```

- **`_cate_aplicatii`** primește ramura `if a["vedere"] == "recenzii": return len(a["blocuri"])`.
- **În `Vox._aplicatii_raspuns`:**
  - `date = self._aplicatii()` devine `date = self._aplicatii(cu_recenzii=True) if interp["aspect"] == "recenzii" else self._aplicatii()`;
  - imediat după funcția interioară `aplicatia`, înainte de `if interp["aspect"] == "note":`:

```python
        if interp["aspect"] == "recenzii":
            return {**rez, **_recenzii_raspuns(interp, date, aplicatia, nume)}
```

- **În `_raspunde`**, după `rand["aplicatii"] = _cate_aplicatii(aplicatii)`, tot în `if aplicatii:`:

```python
            if aplicatii["vedere"] == "recenzii":
                rand["recenzii"] = sum(len(m["recenzii"]) for b in aplicatii["blocuri"]
                                       for m in (b["play"], b["app_store"]) if m)
```

- **Condiția lui `toate`** se schimbă la fel în `_butoane_aplicatii` și în `_din_buton_aplicatii`: `(… functie or aspect == "note")` devine `(… functie or aspect == "note" or (aspect == "recenzii" and text_cautat))`. Concret:
  - în `_butoane_aplicatii`: `if banci and (interp["functie"] or interp["aspect"] == "note" or (interp["aspect"] == "recenzii" and interp["text_cautat"])):`;
  - în `_din_buton_aplicatii`: `elif buton == "toate" and banci and (nou["functie"] or nou["aspect"] == "note" or (nou["aspect"] == "recenzii" and nou["text_cautat"])):`.

- [ ] **Step 4: toate testele.** Run: `PYTHONIOENCODING=utf-8 python app/test_vox.py` → OK.

- [ ] **Step 5: commit.**
```bash
printf '%s\n' "app: vederea Vox de recenzii, pe bancă și pe magazin, cu căutarea la o bancă sau la toate" > "$S/mesaj.txt"
git add app/vox.py app/test_vox.py && git commit -q -F "$S/mesaj.txt"
```

---

### Task 6: interfața

**Files:**
- Modify: `shared/src/vox.ts` (`Interpretare.aspect`; `RecenzieVox`, `MagazinRecenzii`, `BlocRecenzii`, noi; `SchemaAplicatii`)
- Modify: `web/src/pages/rate_mobil/Recenzii.tsx` (`CardRecenzie`: `text: ReactNode`)
- Create: `web/src/pages/vox/Recenzii.tsx`
- Modify: `web/src/pages/vox/Aplicatii.tsx` (ramura `recenzii`, sursele, linkul, nota „fără aplicație analizată”)
- Modify: `web/src/pages/Vox.tsx` (eticheta „recenzii” din „Am înțeles”)
- Modify: `web/src/i18n/dict/vox.ts`, `web/src/styles/vox.css`

- [ ] **Step 1: RED prin tipuri.** În `Aplicatii.tsx`, importul `import Recenzii from './Recenzii'`, iar după `{a.vedere === 'neanalizata' && <Neanalizata a={a} />}`:
`{a.vedere === 'recenzii' && <Recenzii a={a} m={m} />}`.
Run: `npm run typecheck` → erori (modulul lipsește, `vedere` nu cunoaște `recenzii`).

- [ ] **Step 2: Zod (`shared/src/vox.ts`).**
  - `Interpretare.aspect` devine `z.enum(['functii', 'note', 'recenzii'])`.
  - În `SchemaAplicatii`, `vedere` primește `'recenzii'`, plus câmpurile `blocuri: z.array(BlocRecenzii).optional(), cuvinte: z.array(z.string()).optional(), fara_potriviri: z.number().optional(),`.
  - Înaintea lui `SchemaAplicatii`:

```ts
/** O recenzie, așa cum a scris-o clientul (App Store din bază, Google Play din date/google_play_recenzii.json). */
export const RecenzieVox = z
  .object({
    nota: z.number().nullable(), text: z.string().nullable(), data: z.string().nullable(), versiune: z.string().nullable(),
    raspuns_banca: z.string().nullable(), raspuns_data: z.string().nullable().optional(),
  })
  .passthrough()
export type RecenzieVox = z.infer<typeof RecenzieVox>

/** Recenziile unei bănci într-un magazin: cele potrivite și câte are eșantionul. */
export const MagazinRecenzii = z.object({ recenzii: z.array(RecenzieVox), din: z.number() })
export type MagazinRecenzii = z.infer<typeof MagazinRecenzii>

/** `play` = null: fișierul Google Play lipsește. */
export const BlocRecenzii = z
  .object({
    banca: z.string(), aplicatie: z.string().nullable(), fara_aplicatie: z.boolean(), evidentiata: z.boolean(),
    play: MagazinRecenzii.nullable(), app_store: MagazinRecenzii.nullable(),
  })
  .passthrough()
export type BlocRecenzii = z.infer<typeof BlocRecenzii>
```

- [ ] **Step 3: `CardRecenzie`.** În `web/src/pages/rate_mobil/Recenzii.tsx`, `text: string | null` devine `text: ReactNode`, cu `import type { ReactNode } from 'react'`. Randarea `{text || t('mobil.fara_text')}` rămâne aceeași, pentru că un șir e tot un `ReactNode`.

- [ ] **Step 4: textele (`i18n/dict/vox.ts`)**, după `"vox.aplicatii.fara_magazin"`:

```ts
  "vox.aplicatii.chip_recenzii": ["recenzii", "reviews"],
  "vox.aplicatii.recenzii.titlu": ["Ce scriu clienții", "What customers write"],
  "vox.aplicatii.recenzii.titlu_cautare": ["Ce scriu clienții despre «{text}»", "What customers write about “{text}”"],
  "vox.aplicatii.recenzii.esantion": ["Eșantion: Google Play, cele mai noi 20 de recenzii pe aplicație ({data}); App Store, cel mult 8, alese de Apple, unele vechi. Nu arată părerea tuturor clienților.", "Sample: Google Play, the latest 20 reviews per app ({data}); App Store, at most 8, chosen by Apple, some old. It does not show what all customers think."],
  "vox.aplicatii.recenzii.magazin": ["{magazin} · recenzii: {n}", "{magazin} · reviews: {n}"],
  "vox.aplicatii.recenzii.magazin_cautare": ["{magazin} · {n} din {din} conțin «{text}»", "{magazin} · {n} of {din} contain “{text}”"],
  "vox.aplicatii.recenzii.nimic_banca": ["Nicio recenzie din eșantion nu conține «{text}» ({din} recenzii la {banca}).", "No review in the sample contains “{text}” ({din} reviews for {banca})."],
  "vox.aplicatii.recenzii.nimic": ["Nicio recenzie în eșantion.", "No review in the sample."],
  "vox.aplicatii.recenzii.nimic_nicaieri": ["Nicio recenzie din eșantion nu conține «{text}», la nicio bancă.", "No review in the sample contains “{text}”, at any bank."],
  "vox.aplicatii.recenzii.fara_potriviri": ["În celelalte aplicații ({n}), nicio recenzie nu conține «{text}».", "In the other apps ({n}), no review contains “{text}”."],
  "vox.aplicatii.recenzii.arata_toate": ["Arată toate ({n})", "Show all ({n})"],
  "vox.aplicatii.recenzii.mai_mult": ["mai mult", "more"],
  "vox.aplicatii.recenzii.deschide": ["Deschide recenziile din 2.3", "Open the reviews in 2.3"],
```

- [ ] **Step 5: componenta `web/src/pages/vox/Recenzii.tsx`:**

```tsx
import { useState, type ReactNode } from 'react'
import type { Aplicatii as AplicatiiT, BlocRecenzii, MagazinRecenzii } from '@mcc/shared'
import type { Meta } from '../../api/meta'
import { EtichetaBanca } from '../../components/comune'
import { useLang, type DictKey } from '../../i18n'
import { faraDiacritice, formatZi } from '../../util/format'
import { CardRecenzie } from '../rate_mobil/Recenzii'
import '../../styles/rate_mobil.css'

/**
 * Recenziile în Vox (app/vox.py, `_recenzii_raspuns`): așa cum le-au scris clienții, pe bancă și pe magazin. Primele 5 pe
 * magazin, cu „Arată toate”; textele de peste 400 de caractere se scurtează (în App Store, 45 trec de 500, cea mai lungă
 * are 1.811; 09.10.2026).
 */
const PRIMELE = 5
const LUNGIME = 400

/** Cuvintele găsite, îngroșate cu regula din server (`vox.potriveste_recenzia`): rădăcina e începutul cuvântului. */
function TextRecenzie({ text, cuvinte }: { text: string | null; cuvinte: string[] }) {
  const { t } = useLang()
  const [tot, setTot] = useState(false)
  if (!text) return null
  const scurt = !tot && text.length > LUNGIME
  const vizibil = scurt ? `${text.slice(0, LUNGIME).trimEnd()}…` : text
  const parti: ReactNode[] = []
  let ultim = 0
  if (cuvinte.length) {
    for (const m of vizibil.matchAll(/[\p{L}\p{N}]+/gu)) {
      if (cuvinte.some((c) => faraDiacritice(m[0]).startsWith(c))) {
        parti.push(vizibil.slice(ultim, m.index), <b key={m.index}>{m[0]}</b>)
        ultim = (m.index ?? 0) + m[0].length
      }
    }
  }
  parti.push(vizibil.slice(ultim))
  return (
    <>
      {parti}
      {scurt && <> <button type="button" className="vox-link" onClick={() => setTot(true)}>{t('vox.aplicatii.recenzii.mai_mult')}</button></>}
    </>
  )
}

function BlocMagazin({ k, mg, banca, m, cuvinte, cautat }: {
  k: 'play' | 'app_store'; mg: MagazinRecenzii; banca: string; m: Meta; cuvinte: string[]; cautat: string | null
}) {
  const { t } = useLang()
  const [toate, setToate] = useState(false)
  const magazin = t(`vox.aplicatii.magazin.${k}` as DictKey)
  const vizibile = toate ? mg.recenzii : mg.recenzii.slice(0, PRIMELE)
  return (
    <div className="vox-rec-magazin">
      <span className="vox-segment-cap">
        {cautat
          ? t('vox.aplicatii.recenzii.magazin_cautare', { magazin, n: mg.recenzii.length, din: mg.din, text: cautat })
          : t('vox.aplicatii.recenzii.magazin', { magazin, n: mg.din })}
      </span>
      {!mg.recenzii.length && !cautat && <p className="vox-nota"><span className="vox-punct gri" />{t('vox.aplicatii.recenzii.nimic')}</p>}
      {vizibile.map((r, i) => (
        <CardRecenzie key={`${r.data}-${i}`} banca={banca} m={m} nota={r.nota} data={r.data} versiune={r.versiune}
          magazin={magazin} text={<TextRecenzie text={r.text} cuvinte={cuvinte} />} raspuns={r.raspuns_banca}
          raspunsData={r.raspuns_data ?? null} />
      ))}
      {mg.recenzii.length > vizibile.length && (
        <button type="button" className="vox-link vox-clas-toate" onClick={() => setToate(true)}>
          {t('vox.aplicatii.recenzii.arata_toate', { n: mg.recenzii.length })}
        </button>
      )}
    </div>
  )
}

function BlocBanca({ b, m, cuvinte, cautat }: { b: BlocRecenzii; m: Meta; cuvinte: string[]; cautat: string | null }) {
  const { t } = useLang()
  const potriviri = (b.play?.recenzii.length ?? 0) + (b.app_store?.recenzii.length ?? 0)
  const din = (b.play?.din ?? 0) + (b.app_store?.din ?? 0)
  return (
    <section className={b.evidentiata ? 'vox-rec-banca evidentiata' : 'vox-rec-banca'}>
      <div className="vox-rec-cap">
        <EtichetaBanca slug={b.banca} m={m} tag />
        {b.aplicatie && <span className="vox-meta">{b.aplicatie}</span>}
      </div>
      {b.fara_aplicatie
        ? <p className="vox-nota"><span className="vox-punct gri" />{t('vox.aplicatii.fara_apk')}</p>
        : cautat && potriviri === 0
          ? <p className="vox-nota"><span className="vox-punct" />{t('vox.aplicatii.recenzii.nimic_banca', { text: cautat, din, banca: m.nume[b.banca] ?? b.banca })}</p>
          : (
            <>
              {b.play
                ? <BlocMagazin k="play" mg={b.play} banca={b.banca} m={m} cuvinte={cuvinte} cautat={cautat} />
                : <p className="vox-nota"><span className="vox-punct gri" />{t('vox.aplicatii.play_lipsa')}</p>}
              {b.app_store && <BlocMagazin k="app_store" mg={b.app_store} banca={b.banca} m={m} cuvinte={cuvinte} cautat={cautat} />}
            </>
          )}
    </section>
  )
}

export default function Recenzii({ a, m }: { a: AplicatiiT; m: Meta }) {
  const { t, locale } = useLang()
  const blocuri = a.blocuri ?? []
  const cuvinte = a.cuvinte ?? []
  const cautat = a.text_cautat
  return (
    <>
      <div className="vox-clas-antet">
        <b>{cautat ? t('vox.aplicatii.recenzii.titlu_cautare', { text: cautat }) : t('vox.aplicatii.recenzii.titlu')}</b>
      </div>
      <p className="vox-nota"><span className="vox-punct gri" />
        {t('vox.aplicatii.recenzii.esantion', { data: a.play_la ? formatZi(a.play_la, locale) : '—' })}
      </p>
      {!blocuri.length && cautat && (
        <p className="vox-nota"><span className="vox-punct" />{t('vox.aplicatii.recenzii.nimic_nicaieri', { text: cautat })}</p>
      )}
      {blocuri.map((b) => <BlocBanca key={b.banca} b={b} m={m} cuvinte={cuvinte} cautat={cautat} />)}
      {!!a.fara_potriviri && !!blocuri.length && cautat && (
        <p className="vox-nota"><span className="vox-punct gri" />{t('vox.aplicatii.recenzii.fara_potriviri', { n: a.fara_potriviri, text: cautat })}</p>
      )}
    </>
  )
}
```

- [ ] **Step 6: `Aplicatii.tsx` și `Vox.tsx`.**
  - **În `Aplicatii`:**
    - sursa analizei apare doar dacă `a.vedere !== 'note' && a.vedere !== 'recenzii'`;
    - sursa Google Play apare și la `recenzii`: condiția `note ? (…) : ''` devine `note || a.vedere === 'recenzii' ? (…) : ''`;
    - nota „Fără aplicație analizată” apare doar dacă `a.vedere !== 'aplicatii' && a.vedere !== 'recenzii'`;
    - linkul: la `recenzii`, `/mobil?la=recenzii` cu textul `vox.aplicatii.recenzii.deschide`.
  - **În `Vox.tsx`**, eticheta din „Am înțeles” devine:
    `t(i.aspect === 'note' ? 'vox.aplicatii.chip_note' : i.aspect === 'recenzii' ? 'vox.aplicatii.chip_recenzii' : 'vox.aplicatii.chip')`.

- [ ] **Step 7: stilurile (`vox.css`)**, la final:

```css
/* Recenziile (09.10.2026): cardul vine din 2.3 (.rec, în rate_mobil.css) */
.vox-rec-banca { display: flex; flex-direction: column; gap: 8px; padding: 10px 12px; border: 1px solid var(--line); border-radius: 10px }
.vox-rec-banca.evidentiata { border-color: var(--accent); box-shadow: inset 4px 0 var(--accent) }
.vox-rec-cap { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 10px }
.vox-rec-magazin { display: flex; flex-direction: column; gap: 6px }
.vox-rec-magazin .rec b { background: var(--accent-tint) }
```

- [ ] **Step 8: verificările.**
Run: `npm run typecheck` → 0 erori.
Run: `npm -w web exec -- vite build --outDir "$S/dist_verif" --emptyOutDir` → reușit.

- [ ] **Step 9: commit.**
```bash
printf '%s\n' "web, shared: fișa Vox pentru recenzii: pe bancă și pe magazin, cuvintele găsite îngroșate, avertismentul despre eșantion" > "$S/mesaj.txt"
git add shared/src/vox.ts web/src/pages/vox/Recenzii.tsx web/src/pages/vox/Aplicatii.tsx web/src/pages/Vox.tsx web/src/pages/rate_mobil/Recenzii.tsx web/src/i18n/dict/vox.ts web/src/styles/vox.css
git commit -q -F "$S/mesaj.txt"
```

---

### Task 7: verificarea pe date reale și în pagină

**Files:**
- Create (în `$S`): `raspunsuri_recenzii.py`, `verifica_recenzii_ui.py`

- [ ] **Step 1: răspunsurile reale cu model fals (`$S/raspunsuri_recenzii.py`).** Scriptul copiază structura lui `raspunsuri_aplicatii.py`: clasa `Fals`, helper-ul `a(**k)` și `Vox` cu cititorii serverului. Cazurile:

```python
CAZURI = [
    ("Ce scriu clienții despre BT Pay?", a(banci=["banca-transilvania"], aspect="recenzii"), ("libra",)),
    ("Se plâng clienții de logare la Libra?", a(banci=["libra"], aspect="recenzii", text_cautat="logare"), ("toate",)),
    ("Ce scriu clienții despre logare?", a(aspect="recenzii", text_cautat="logare"), ()),
    ("Ce scriu clienții despre RoPay?", a(aspect="recenzii", text_cautat="RoPay"), ()),
    ("Ce scriu clienții despre card?", a(aspect="recenzii", text_cautat="card"), ()),
    ("Ce scriu clienții despre lentă?", a(aspect="recenzii", text_cautat="lentă"), ()),
]
```

Plus cazul „fără Google Play”, cu cititorul `lambda **k: {**server._aplicatii_vox(**k), "recenzii_play": None}`, pe întrebarea „Ce scriu clienții despre BT Pay? (fără Google Play)”. Aserțiunile, din criteriile spec-ului:

```python
nr = lambda caz: sum(len(m["recenzii"]) for b in d[caz]["raspuns"]["aplicatii"]["blocuri"] for m in (b["play"], b["app_store"]) if m)
banci = lambda caz: [b["banca"] for b in d[caz]["raspuns"]["aplicatii"]["blocuri"]]
b0 = d["Ce scriu clienții despre BT Pay?"]["raspuns"]["aplicatii"]["blocuri"][0]
assert (len(b0["play"]["recenzii"]), len(b0["app_store"]["recenzii"])) == (20, 8)
assert nr("Se plâng clienții de logare la Libra?") == 0
assert nr("Ce scriu clienții despre logare?") == 7 and sorted(banci("Ce scriu clienții despre logare?")) == ["brd", "garanti", "nexent", "patria", "vista"]
assert nr("Ce scriu clienții despre RoPay?") == 0
assert nr("Ce scriu clienții despre card?") == 48 and len(banci("Ce scriu clienții despre card?")) == 16
assert nr("Ce scriu clienții despre lentă?") == 1
assert d["Se plâng clienții de logare la Libra?"]["butoane"]["toate"]["aplicatii"]["blocuri"]          # „logare” la toate
```

Run: `PYTHONIOENCODING=utf-8 python "$S/raspunsuri_recenzii.py" "$S/raspunsuri_recenzii.json"`
Expected: fără `AssertionError`.

- [ ] **Step 2: pagina (`$S/verifica_recenzii_ui.py`).** Copiază structura lui `verifica_aplicatii_ui.py`: rutele, `pagina`, `intreaba`, `captura`. Pentru `ro/luminos` și `en/intunecat` verifică:
  - **BT Pay:**
    - 2 blocuri de magazin;
    - primele 5 carduri `.rec` în fiecare bloc;
    - butonul „Arată toate (20)”;
    - avertismentul despre eșantion.
  - **„logare” la Libra:** fraza „Nicio recenzie din eșantion…” / „No review in the sample…”.
  - **„logare” la toate:** 5 blocuri `.vox-rec-banca`, iar în fiecare `.rec` potrivit există un `b` al cărui text, fără diacritice, începe cu „loga”.
  - **„lentă” la toate:** niciun `b` cu „Excelent”.
  - **„mai mult”:** apare pe o recenzie App Store lungă și, după clic, textul crește.
  - **Fără Google Play:** „Google Play necolectat” / „Google Play not collected”.
  - **Butonul „Compară cu Libra”:** corpul `POST`-ului are `buton = libra` și `anterior.aspect = recenzii`.
  - **Continuarea:** după recenziile BT Pay, „și la BRD?” trimite `anterior.aspect = recenzii`.
  - **Consola** rămâne curată.
  - **La final:** conversația `35b2f7f797944207` se redeschide.
Run: `bash "$S/cu_server_8797.sh" env PYTHONIOENCODING=utf-8 python "$S/verifica_recenzii_ui.py" "$S/raspunsuri_recenzii.json" "$S/capturi_recenzii"`
Expected: `erori: 0 · consolă: 0`. Capturile se verifică cu ochii.

- [ ] **Step 3: paginile.** Run: `bash "$S/cu_server_8797.sh" env MIP_URL=http://localhost:8797 PYTHONIOENCODING=utf-8 python app/verifica_pagini.py` → `0 pagini cu erori`. Verifică cu ochii și 2.3, pentru că `CardRecenzie` s-a schimbat.

- [ ] **Step 4: fără commit** (scripturile stau în `$S`). O reparație găsită aici intră într-un commit „web: …” sau „app: …”, cu motivul.

---

### Task 8: setul de evaluare

**Files:** Modify: `app/vox_exemple.json`

- [ ] **Step 1: o așteptare schimbată și 4 întrebări noi.** „Ce scriu clienții despre BT Pay?” devine
`{"tip": "aplicatii", "banci": ["banca-transilvania"], "aspect": "recenzii"}`. Întrebările noi, la final:

```json
  {"intrebare": "Se plâng clienții de logare la Libra?",
   "asteptat": {"tip": "aplicatii", "banci": ["libra"], "aspect": "recenzii", "text_cautat_nenul": true}},
  {"intrebare": "Ce scriu clienții despre RoPay?",
   "asteptat": {"tip": "aplicatii", "banci": [], "aspect": "recenzii", "text_cautat_nenul": true}},
  {"intrebare": "Ce recenzii are George?",
   "asteptat": {"tip": "aplicatii", "banci": ["bcr"], "aspect": "recenzii"}},
  {"intrebare": "Ce scriu clienții?",
   "asteptat": {"tip": "neclar"}}
```

- [ ] **Step 2: numără și cere estimarea (gratis).**
Run: `PYTHONIOENCODING=utf-8 python -c "import json; print(len(json.load(open('app/vox_exemple.json', encoding='utf-8'))))"` → `57`.
Run: `PYTHONIOENCODING=utf-8 python app/eval_vox.py` → estimarea, fără niciun apel.

- [ ] **Step 3: commit.**
```bash
printf '%s\n' "app: evaluarea Vox are 4 întrebări despre recenzii, iar „Ce scriu clienții despre BT Pay?” așteaptă recenziile" > "$S/mesaj.txt"
git add app/vox_exemple.json && git commit -q -F "$S/mesaj.txt"
```

---

### Task 9: verificarea cu modelul real (plătită, doar cu acord)

- [ ] **Step 1: oprește-te și cere acordul lui Nicolae**, cu costul: testul țintit ~$0,05, apoi evaluarea completă ~$0,10.
- [ ] **Step 2: testul țintit.** `test_tintit.py` din `$S` alege #36, întrebările despre aplicații și cele 2 `in_afara`. Lista lui se extinde cu întrebările de recenzii (filtrul pe `asteptat.tip == "aplicatii"` le prinde deja) și cu „Ce scriu clienții?”.
Run: `PYTHONIOENCODING=utf-8 python "$S/test_tintit.py"`
Expected: toate corecte. Dacă #36 pică, fraza despre recenzii se mută din regula `aplicatii`, ca pe 09.10.2026, și testul se reia, tot cu acord.
- [ ] **Step 3: evaluarea completă.** Run: `PYTHONIOENCODING=utf-8 python app/eval_vox.py --da` → `57/57`. Se notează costul și tokenii.

---

### Task 10: documentația

- [ ] **README, secțiunea Vox:** un punct „**Recenziile** (09.10.2026)” cu:
  - sursele și eșantionul (394 Google Play, 109 App Store);
  - potrivirea la început de cuvânt (cu subșir, „lentă” prindea 12 „excelent” din 13);
  - criteriile măsurate;
  - evaluarea, cu cifrele din Task 9.
- [ ] **`CLAUDE.md`:** „notele Google Play din `date/google_play.json`, ca 2.3” devine „datele Google Play din `date/`, ca 2.3”. Numărul de linii rămâne 124.
- [ ] **Harta Serena:** prin skill-ul `actualizeaza-memoria`. În linia Vox din `cod/harta` intră aspectul `recenzii`, `potriveste_recenzia`, `_google_play_recenzii` / `FISIER_GOOGLE_PLAY_RECENZII` și `pages/vox/Recenzii.tsx`.
- [ ] **`docs/HANDOFF_VOX.md`** (necomis): starea și costurile.
- [ ] **Toate suitele.** Run: `test_vox`, `test_celula`, `test_rulari`, `test_autentificare`, `test_server_autentificare`, `test_pdf_proxy` și `npm run typecheck` → OK.
- [ ] **Commit:**
```bash
printf '%s\n' "docs, serena: Vox arată recenziile aplicațiilor; regula „cifrele din bază” cuprinde datele Google Play din date/" > "$S/mesaj.txt"
git add README.md CLAUDE.md .serena/memories && git commit -q -F "$S/mesaj.txt"
```
