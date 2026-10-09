# Vox: citește corect datele pe care le avem; continuări fără model — planul de implementare

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fișa băncii din Vox separă moneda la dobânzi, frecvența la comisioane și valorile care nu sunt prețul serviciului, arată data fiecărei valori; clasamentele de dobânzi spun când o celulă are și alte monede; butoanele „Pentru firme / persoane fizice” și „Compară cu Libra” continuă fără model; promptul stă în cache o oră.

**Architecture:** Regulile de citire stau în `app/vox.py` (`separa`, `rezuma`), peste rândurile pe care `celula` le întoarce deja; paginile nu le folosesc. Serverul adaugă la `celula` câmpul `data_vigoare` și filtrul opțional `valuta` (trimis doar de Vox), iar la clasamentele de dobânzi câmpul `alte_monede` pe bancă (`_alte_monede_rate`). Butoanele: `vox.butoane` (ce butoane are un răspuns), `vox.din_buton` (interpretarea nouă), `Vox.continua` (răspunsul fără model), `POST /api/vox` cu `buton` + `anterior`. Cache-ul: `ttl: "1h"`, cu factorul 2,0 în `preturi.py`.

**Tech Stack:** Python 3.12 (`unittest`, psycopg2), Anthropic SDK (Haiku 4.5), React 18 + AntD 5 + TanStack Query + Zod, Playwright (Edge).

**Spec:** `docs/superpowers/specs/2026-10-08-vox-citire-corecta-design.md`

`SCRATCH` = dosarul temporar al sesiunii; în Git Bash:
`S="C:/Users/NICOLA~1.CHE/AppData/Local/Temp/claude/c--Users-nicolae-cherascu-Desktop-Market-Intelligence-Platform/e6a2503b-45f0-43b2-91ba-6b16a4fdc1ef/scratchpad"`.
`bash "$S/cu_server_8797.sh" <comandă>` pornește serverul temporar pe :8797 (codul din arbore, Vox oprit,
`MCC_AUTH_LOCAL=admin`), rulează comanda și îl oprește. `python` = interpretorul din `.venv` (activ în Git Bash).

**Decizii luate la scrierea planului** (nu sunt în spec; spec-ul rămâne autoritatea):
- „Vezi dovezile” de pe un card de monedă cere și moneda: `celula` primește filtrul opțional `valuta`
  (`lei`, `eur`, `usd`, `gbp`, `chf`, `nespusa`). Fără el, sertarul deschis de pe „în euro · 1 valoare” arăta
  toate cele 11 dobânzi de depozit ale Libra, fără moneda vizibilă. Paginile nu trimit parametrul, deci
  rămân neschimbate, cum cere spec-ul.
- Nota de monedă din clasament spune „valorile includ dobânzi în altă monedă decât lei”, nu „mediana
  amestecă”: la Raiffeisen, în blocul „12 luni”, ambele valori sunt în altă monedă, deci nu se amestecă nimic.
- Un rând cu tipul gol în `cod_scenariu` ar intra la „alte valori”; pe `mip_merge` (08.10.2026) sunt 0 astfel
  de rânduri, deci regula nu ascunde nimic azi.

## Global Constraints

- Buget pentru apeluri plătite: **cel mult $1 în total**, aprobat de Nicolae pe 08.10.2026. Apeluri plătite doar în Task 11 (`eval_vox.py --da`, ~$0,10 pe rulare, cel mult 3 rulări; testul cap-coadă, ~$0,04). Costul fiecărei rulări se trece în registru; peste $0,60 cumulat, nu se mai rulează nimic plătit.
- Testele și verificările de interfață nu cheamă modelul: `ClientFals`, model fals în scripturi, `GET`/`POST /api/vox` răspunse din fișier în Playwright.
- Serverele utilizatorului (:8765, :5173) nu se opresc și nu se repornesc; `npm run build` nu se rulează (build-ul de verificare merge în `"$S/dist_verif"`); serverul temporar e doar cel din `cu_server_8797.sh`.
- Paginile 2.1, 2.2, Versus și ce afișează sertarul rămân neschimbate (decizia lui Nicolae, 08.10.2026): `celula` primește doar câmpul `data_vigoare` (pe care sertarul nu-l arată) și filtrul `valuta`, trimis doar de Vox.
- Serverul rămâne read-only; în SQL doar parametri `%s`; `valuta` și `buton` doar din listele lor.
- Valori: butoanele `firme`, `pf`, `libra`; tipurile de preț `comision`, `comisioane` și cheile din `ctx["categorii"]` (`depozite`, `credite`, `conturi_carduri`); monedele `MONEDE = {"LEI": "lei", "RON": "lei", "EUR": "eur", "USD": "usd", "GBP": "gbp", "CHF": "chf"}`.
- Identificatori în română fără diacritice; texte prin `t` / `tn`, perechi `[română, engleză]`; niciun pachet nou.
- Comentariile spun de ce, cu cifra măsurată (`mip_merge`, 08.10.2026); commit-uri „zonă: ce și de ce”, fără `Co-Authored-By`, prin `git commit -F` (mesajul într-un fișier din `$S`).
- `app/server.py` are CRLF; scripturile Python cu `PYTHONIOENCODING=utf-8 python`, din rădăcina repo-ului. Nu se citește `.env`.

## Review Focus

- Conversațiile salvate înainte (fără `alte`, `moneda`, `frecvente`, `butoane`, `buton`, cu `model` mereu text) se redeschid fără eroare Zod și fără butoane — Playwright pe trei conversații vechi în Task 10.
- O bancă la care nicio dobândă nu are moneda în `valuta` (8.559 de rânduri goale) arată un singur card „monedă nespusă”, nu o fișă goală — `test_moneda_toata_nespusa` în Task 1.
- Un buton apăsat după repornirea serverului (token nou) e refuzat ca o întrebare și pagina ia tokenul din nou — 403 fără token în Task 5; în pagină, butonul și întrebarea trec prin aceeași funcție (`ruleaza`, Task 10).
- O întrebare scrisă după un buton continuă interpretarea butonului („și la BRD?” după „Pentru firme” păstrează PJ) — pasul din Playwright în Task 10.
- „Vezi dovezile” de pe un card de monedă deschide doar moneda lui (`valuta=eur`), iar de pe un card din „alte valori”, doar tipul lui (`scenariu=limita`) — Playwright în Task 8.

---

### Task 1: fișa băncii — tipul, moneda, frecvența (`app/vox.py`)

**Files:**
- Modify: `app/vox.py` (după `CATEGORII_COMISION`: `MONEDE`, `ORDINE_MONEDA`, `_moneda`, `_ordine_moneda`, `separa`; `rezuma`; `Vox._raspuns` și apelul lui din `intreaba`)
- Test: `app/test_vox.py` (clasele `Rezumat`, `Intrebari`)

**Interfaces:**
- Produces: `vox.separa(randuri, categorii_rate) -> (pret, alte)` (rândurile din `alte` primesc `tip_alt`); `vox.rezuma(randuri, primul=None, categorii_rate=())` (grupe cu `moneda` la dobânzi și `frecvente` la comisioanele cu mai multe frecvențe); `Vox._raspuns(banca, interp, ctx)` întoarce și `alte`; `vox.MONEDE`.

- [ ] **Step 1: testele care pică**

În `app/test_vox.py`, la sfârșitul clasei `Rezumat`:

```python
    def test_moneda_la_dobanzi(self):
        """Libra · depozit (mip_merge, 08.10.2026): 4,75% în lei, 1,95% în euro și 9 valori fără monedă
        stăteau într-un singur interval; acum un card pe monedă, lei primul, nespusă la final."""
        def d(v, valuta):
            return dict(rand(v, "procent", "depozite|x"), valuta=valuta)
        r = vox.rezuma([d(2.2, None), d(1.95, "EUR"), d(5.5, None), d(4.75, "LEI"), d(4.5, "RON")],
                       categorii_rate=("depozite", "credite", "conturi_carduri"))
        self.assertEqual([(g["moneda"], g["n"], g["minim"], g["maxim"]) for g in r],
                         [("lei", 2, 4.5, 4.75), ("eur", 1, 1.95, 1.95), (None, 2, 2.2, 5.5)])

    def test_moneda_toata_nespusa(self):
        """8.559 de rânduri curente n-au moneda în `valuta` (08.10.2026): un singur card, „monedă nespusă”."""
        r = vox.rezuma([rand(2.2, "procent", "depozite|x"), rand(5.5, "procent", "depozite|x")],
                       categorii_rate=("depozite",))
        self.assertEqual([(g["moneda"], g["n"]) for g in r], [(None, 2)])

    def test_moneda_nu_la_comisioane(self):
        """La comisioane unitatea e moneda prețului: „Administrarea contului (EURO): 20 Lei” are `valuta` EUR."""
        r = vox.rezuma([dict(rand(20), valuta="EUR"), dict(rand(5), valuta="LEI")], categorii_rate=("depozite",))
        self.assertEqual(len(r), 1)
        self.assertNotIn("moneda", r[0])

    def test_frecvente_cand_sunt_mai_multe(self):
        """BCR · administrare cont PF (mip_merge, 08.10.2026): 16 valori lunare 0–100 lei, 6 anuale 0–1.200 și
        11 fără frecvență dădeau un singur „0 – 1.200 lei”."""
        def f(v, frecventa):
            return dict(rand(v), frecventa=frecventa)
        r = vox.rezuma([f(20, "lunar"), f(100, "lunar"), f(240, "anual"), f(0, None), f(1200, "anual"),
                        f(5, "lunar")])
        self.assertEqual(r[0]["frecvente"], [
            {"frecventa": "lunar", "n": 3, "minim": 5, "maxim": 100},
            {"frecventa": "anual", "n": 2, "minim": 240, "maxim": 1200},
            {"frecventa": None, "n": 1, "minim": 0, "maxim": 0}])
        self.assertEqual((r[0]["minim"], r[0]["maxim"]), (0, 1200))

    def test_o_singura_frecventa_fara_camp(self):
        r = vox.rezuma([dict(rand(20), frecventa="lunar"), dict(rand(5), frecventa="lunar")])
        self.assertNotIn("frecvente", r[0])

    def test_separa_tipurile(self):
        """Garanti · schimbarea PIN-ului: toate cele 7 valori neambigue sunt limite contactless (08.10.2026)."""
        limita = rand(100, "lei", "limita|x")
        pret, alte = vox.separa([rand(5), limita, rand(6.5, "procent", "depozite|12"), rand(1, "lei", "nota|y")],
                                ("depozite",))
        self.assertEqual([vox._categorie(x) for x in pret], ["comision", "depozite"])
        self.assertEqual([x["tip_alt"] for x in alte], ["limita", "nota"])
        self.assertIs(alte[0], limita)              # același rând: tabelul fișei îl arată cu eticheta
```

În clasa `Intrebari`, după `test_cautare_dupa_text`:

```python
    def test_fisa_doar_limite(self):
        """Garanti · schimbarea PIN-ului: niciun comision, doar limite; rezumatul gol, limitele în `alte`."""
        self.randuri["bcr"] = [rand(100, "lei", "limita|x"), rand(700, "lei", "limita|x")]
        r = self.fa(ClientFals(interp())).intreaba("PIN la BCR?")["raspunsuri"][0]
        self.assertEqual(r["rezumat"], [])
        self.assertEqual([(g["categorie"], g["n"], g["minim"], g["maxim"]) for g in r["alte"]],
                         [("limita", 2, 100, 700)])
        self.assertEqual([v.get("tip_alt") for v in r["randuri"]], ["limita", "limita"])

    def test_fisa_dobanzi_pe_moneda(self):
        self.randuri["bcr"] = [dict(rand(4.75, "procent", "depozite|12"), valuta="LEI"),
                               dict(rand(1.95, "procent", "depozite|12"), valuta="EUR")]
        r = self.fa(ClientFals(interp(concept="nominala", categorie="depozite"))).intreaba("depozit BCR?")
        rb = r["raspunsuri"][0]
        self.assertEqual([g["moneda"] for g in rb["rezumat"]], ["lei", "eur"])
        self.assertEqual(rb["alte"], [])
```

- [ ] **Step 2: rulează testele**

Run: `PYTHONIOENCODING=utf-8 python app/test_vox.py 2>&1 | grep -E "^(FAIL|ERROR|Ran|OK|FAILED)"`
Expected: FAIL / ERROR la cele 8 teste noi (`separa` nu există, `rezuma` nu primește `categorii_rate`, răspunsul n-are `alte`); celelalte trec.

- [ ] **Step 3: implementarea**

În `app/vox.py`, imediat după `CATEGORII_COMISION = ("comision", "comisioane")`:

```python
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
```

Înlocuiește toată funcția `rezuma`:

```python
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
            f = pe_frecventa.setdefault(cheie, {}).setdefault(
                frecventa, {"frecventa": frecventa, "n": 0, "minim": v, "maxim": v})
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
```

În `Vox._raspuns`: semnătura devine `def _raspuns(self, banca, interp, ctx):`; după linia
`randuri = sorted(randuri, key=lambda r: _ordine_segment(r.get("segment"), interp["segment"]))` adaugă:

```python
        categorii_rate = ctx["categorii"]
        pret, alte = separa(randuri, categorii_rate)
```

și în dicționarul întors înlocuiește `"rezumat": rezuma(randuri, interp["segment"]),` cu:

```python
            "rezumat": rezuma(pret, interp["segment"], categorii_rate),
            # notele, limitele, cursurile: separat, ca să nu treacă drept prețul cerut
            "alte": rezuma(alte, interp["segment"], categorii_rate),
```

În `intreaba`, apelul devine `self._raspuns(b, interp, ctx)`.

- [ ] **Step 4: rulează testele**

Run: `PYTHONIOENCODING=utf-8 python app/test_vox.py 2>&1 | grep -E "^(FAIL|ERROR|Ran|OK|FAILED)"`
Expected: `Ran 109 tests` și `OK` (101 vechi + 8 noi; cele 6 teste vechi din `Rezumat` trec neschimbate).

- [ ] **Step 5: commit**

```bash
cat > "$S/mesaj_t1.txt" <<'EOF'
app: fișa Vox separă moneda la dobânzi, frecvența la comisioane și valorile care nu sunt prețul

Libra · depozit punea 4,75% în lei, 1,95% în euro și 9 valori fără monedă într-un singur interval;
BCR · administrare cont PF punea 16 valori lunare lângă 6 anuale („0 – 1.200 lei”); la Garanti,
limitele contactless apăreau drept comisionul de schimbare a PIN-ului (mip_merge, 08.10.2026).
EOF
git add app/vox.py app/test_vox.py && git commit -q -F "$S/mesaj_t1.txt"
```

---

### Task 2: `celula` — data valorii și filtrul de monedă (`app/server.py`)

**Files:**
- Modify: `app/server.py` (`celula`: `o.data_vigoare` în SELECT; filtrul `valuta` după cel de segment)
- Test: `app/test_celula.py` (clasa `Celula`)

**Interfaces:**
- Consumes: `vox.MONEDE` (Task 1).
- Produces: fiecare rând din `/api/celula` și din `_cauta_vox` are `data_vigoare` (dată sau `null`); `/api/celula?...&valuta=lei|eur|usd|gbp|chf|nespusa`.

- [ ] **Step 1: testele care pică**

În `app/test_celula.py`, la sfârșitul clasei `Celula`:

```python
    def test_data_vigoare_in_select(self):
        """Vox arată data intrării în vigoare lângă fiecare rând (69% din rândurile curente o au, 08.10.2026)."""
        sql, _ = self.cere()
        self.assertIn("o.data_vigoare", sql)

    def filtru(self, sql):
        return sql.split("WHERE", 1)[1]

    def test_valuta_lei_include_ron(self):
        sql, params = self.cere(valuta="lei")
        self.assertIn("upper(coalesce(o.valuta, '')) IN ('LEI', 'RON')", self.filtru(sql))
        self.assertEqual(params, BAZA)

    def test_valuta_eur(self):
        """„Vezi dovezile” de pe cardul „în euro” al Libra · depozit (1 valoare) deschidea toate cele 11 dobânzi."""
        sql, params = self.cere(valuta="eur")
        self.assertIn("AND upper(o.valuta) = %s", self.filtru(sql))
        self.assertEqual(params, BAZA + ("EUR",))

    def test_valuta_nespusa(self):
        sql, params = self.cere(valuta="nespusa")
        self.assertIn("coalesce(o.valuta, '') = ''", self.filtru(sql))
        self.assertEqual(params, BAZA)

    def test_valuta_necunoscuta_ignorata(self):
        sql, params = self.cere(valuta="xyz")
        self.assertNotIn("o.valuta", self.filtru(sql))
        self.assertEqual(params, BAZA)
```

- [ ] **Step 2: rulează testele**

Run: `PYTHONIOENCODING=utf-8 python app/test_celula.py 2>&1 | grep -E "^(FAIL|ERROR|Ran|OK|FAILED)"`
Expected: FAIL la 4 teste (`test_data_vigoare_in_select`, `test_valuta_lei_include_ron`, `test_valuta_eur`, `test_valuta_nespusa`); `test_valuta_necunoscuta_ignorata` trece deja.

- [ ] **Step 3: implementarea**

În `celula`, în SELECT, linia `o.serviciu, o.sectiune, o.conditie, o.frecventa, o.detaliu,` devine
`o.serviciu, o.sectiune, o.conditie, o.frecventa, o.detaliu, o.data_vigoare,`.

După blocul de segment (`elif segment in vox.ORDINE_SEGMENT: … p_extra += (segment,)`):

```python
    # moneda unei dobânzi, cerută doar de cardurile pe monedă din Vox: fără ea, „Vezi dovezile” de pe cardul
    # „în euro” al Libra · depozit (1 valoare) deschidea toate cele 11 dobânzi (mip_merge, 08.10.2026).
    # `lei` = LEI sau RON, `nespusa` = coloana goală; altă valoare se ignoră, ca `termen` și `produs`.
    valuta = (q.get("valuta") or [""])[0]
    if valuta == "lei":
        extra += " AND upper(coalesce(o.valuta, '')) IN ('LEI', 'RON')"
    elif valuta == "nespusa":
        extra += " AND coalesce(o.valuta, '') = ''"
    elif valuta in vox.MONEDE.values():
        extra += " AND upper(o.valuta) = %s"
        p_extra += (valuta.upper(),)
```

- [ ] **Step 4: rulează testele și verificarea pe bază**

Run: `PYTHONIOENCODING=utf-8 python app/test_celula.py 2>&1 | grep -E "^(FAIL|ERROR|Ran|OK|FAILED)"`
Expected: `Ran 20 tests`, `OK`.

Run (pe bază, doar citire):
```bash
PYTHONIOENCODING=utf-8 python -c "
import sys; sys.path.insert(0, 'app'); import server
q = lambda **k: server.celula({'banca': ['libra'], 'camp': ['nominala'], 'scenariu': ['depozite'], 'termen': ['necunoscut'], **{a: [b] for a, b in k.items()}})
print('toate', len(q()), '| lei', len(q(valuta='lei')), '| eur', len(q(valuta='eur')), '| nespusa', len(q(valuta='nespusa')))
print('cu data:', sum(1 for r in server.celula({'banca': ['bcr'], 'camp': ['administrare_cont']}) if r['data_vigoare']))"
```
Expected: `toate 11 | lei 1 | eur 1 | nespusa 9`; `cu data: 467`.

- [ ] **Step 5: commit**

```bash
cat > "$S/mesaj_t2.txt" <<'EOF'
app: celula întoarce data intrării în vigoare și acceptă filtrul de monedă cerut de Vox

Cardul „în euro” al Libra · depozit (1 valoare) deschidea toate cele 11 dobânzi, fără moneda vizibilă;
paginile nu trimit `valuta`, deci rămân neschimbate. 467 din 570 de rânduri BCR · administrare cont au
data (mip_merge, 08.10.2026).
EOF
git add app/server.py app/test_celula.py && git commit -q -F "$S/mesaj_t2.txt"
```

---

### Task 3: clasamentele de dobânzi — `alte_monede` (`app/server.py`, `app/vox.py`)

**Files:**
- Modify: `app/server.py` (`_alte_monede_rate` nouă, înaintea lui `_clasament_vox`; ramura de dobânzi din `_clasament_vox`)
- Modify: `app/vox.py` (`clasa`: copiază `alte_monede`)
- Test: `app/test_vox.py` (`CititoriClasament`, `Clasa`), `app/test_celula.py` (clasă nouă `AlteMonede`)

**Interfaces:**
- Produces: `server._alte_monede_rate(campuri, categorie, termen, produs) -> {banca: {"n", "din"}}` (doar băncile cu `n > 0`); rândul de clasament are `alte_monede: {"n", "din"}` doar când `n > 0`.

- [ ] **Step 1: testele care pică**

În `app/test_vox.py`, clasa `CititoriClasament`: în `setUp`, după cele două `lambda`, adaugă

```python
        self.monede = []
        self.vechi_monede = server._alte_monede_rate
        server._alte_monede_rate = lambda *a: self.monede.append(a) or {"ing": {"n": 1, "din": 4}}
```

în `tearDown` adaugă `self.s._alte_monede_rate = self.vechi_monede`, apoi testele:

```python
    def test_dobanda_spune_alte_monede(self):
        """La depozitul pe 12 luni, ambele valori Raiffeisen sunt în altă monedă (mip_merge, 08.10.2026):
        clasamentul păstrează cifra din 2.2, dar o marchează, în fiecare bloc."""
        c = self.s._clasament_vox("nominala", "depozite", "12", None, None)
        self.assertEqual([b["celule"] for b in c["blocuri"]],
                         [[{"banca": "ing", "alte_monede": {"n": 1, "din": 4}}]] * 2)
        self.assertEqual(self.monede, [(["nominala"], "depozite", "12", ""),
                                       (["nominala"], "depozite", "necunoscut", "")])

    def test_comision_fara_alte_monede(self):
        self.s._clasament_vox("administrare_cont", None, None, None, None)
        self.assertEqual(self.monede, [])
```

Clasa `Clasa`, la sfârșit:

```python
    def test_alte_monede_trec_in_rand(self):
        c = [dict(self.celula("raiffeisen", 2.25), alte_monede={"n": 2, "din": 2}), self.celula("brd", 3)]
        r = {x["banca"]: x for x in vox.clasa(c, "mare_bun", "mediana", set(), self.NUME)}
        self.assertEqual(r["raiffeisen"]["alte_monede"], {"n": 2, "din": 2})
        self.assertNotIn("alte_monede", r["brd"])
```

În `app/test_celula.py`, o clasă nouă la sfârșit (înainte de `if __name__`):

```python
class AlteMonede(unittest.TestCase):
    def setUp(self):
        self.cereri = []
        self.vechi = server.interoghează
        server.interoghează = lambda sql, params=None: self.cereri.append((sql, tuple(params or ()))) or []

    def tearDown(self):
        server.interoghează = self.vechi

    def test_numara_doar_monedele_straine(self):
        """Golul din `valuta` nu e altă monedă: 8.559 de rânduri curente n-o spun (08.10.2026)."""
        self.assertEqual(server._alte_monede_rate(["nominala"], "depozite", "12", ""), {})
        sql, params = self.cereri[-1]
        self.assertEqual(sql.count("%s"), len(params))
        self.assertIn("NOT IN ('', 'LEI', 'RON')", sql)
        self.assertEqual(params, (["nominala"], "depozite"))

    def test_cu_tip_de_credit(self):
        server._alte_monede_rate(["dae"], "credite", "", "ipotecar")
        sql, params = self.cereri[-1]
        self.assertEqual(sql.count("%s"), len(params))
        self.assertEqual(params, (["dae"], "credite", "ipotecar"))
```

- [ ] **Step 2: rulează testele**

Run: `PYTHONIOENCODING=utf-8 python app/test_vox.py 2>&1 | grep -E "^(FAIL|ERROR|Ran|OK|FAILED)"; PYTHONIOENCODING=utf-8 python app/test_celula.py 2>&1 | grep -E "^(FAIL|ERROR|Ran|OK|FAILED)"`
Expected: ERROR în `CititoriClasament` (`_alte_monede_rate` lipsește din `server`), FAIL la `test_alte_monede_trec_in_rand`, ERROR la cele 2 teste din `AlteMonede`.

- [ ] **Step 3: implementarea**

În `app/server.py`, înaintea lui `def _clasament_vox`:

```python
def _alte_monede_rate(campuri, categorie, termen, produs):
    """Pe bancă, câte rânduri ale celulei din 2.2 au altă monedă decât lei (EUR, USD, GBP, CHF în `valuta`;
    golul nu se numără) și din câte. Clasamentul păstrează cifrele paginii, dar spune când o celulă are și
    alte monede: la depozitul pe 12 luni, ambele valori Raiffeisen sunt în altă monedă (mip_merge, 08.10.2026)."""
    filtru, p_extra = _filtre_rate(termen, produs)
    rows = interoghează(
        f"""SELECT b.slug AS banca, count(*)::int AS din,
                   count(*) FILTER (WHERE upper(coalesce(o.valuta, '')) NOT IN ('', 'LEI', 'RON'))::int AS n
            {_baza_rate(GRUPURI_RATE[categorie]["prag"])}{filtru}
            GROUP BY 1""",
        (campuri, categorie) + p_extra)
    return {x["banca"]: {"n": x["n"], "din": x["din"]} for x in rows if x["n"]}
```

În `_clasament_vox`, în ramura de dobânzi, înainte de `return {"sursa": "rate", …}`:

```python
    # cifra rămâne a celulei din 2.2; rândul băncii spune doar câte valori sunt în altă monedă
    for b in blocuri:
        alte = _alte_monede_rate([concept], categorie, b["termen"], b["produs"])
        for c in b["celule"]:
            if c["banca"] in alte:
                c["alte_monede"] = alte[c["banca"]]
```

În `app/vox.py`, în `clasa`, ultima cheie din dicționarul fiecărui rând devine:

```python
                "evidentiata": c["banca"] in evidentiate,
                **({"alte_monede": c["alte_monede"]} if c.get("alte_monede") else {})}
```

- [ ] **Step 4: rulează testele și verificarea pe bază**

Run: aceeași comandă ca la Step 2.
Expected: `test_vox`: `Ran 112 tests`, `OK`; `test_celula`: `Ran 22 tests`, `OK`.

Run (pe bază, doar citire):
```bash
PYTHONIOENCODING=utf-8 python -c "
import sys; sys.path.insert(0, 'app'); import server
print(server._alte_monede_rate(['nominala'], 'depozite', '12', ''))
print(server._alte_monede_rate(['nominala'], 'depozite', 'necunoscut', ''))"
```
Expected: `{'raiffeisen': {'n': 2, 'din': 2}}` și `{'libra': {'n': 1, 'din': 11}, 'vista': {'n': 1, 'din': 35}}`.

- [ ] **Step 5: commit**

```bash
cat > "$S/mesaj_t3.txt" <<'EOF'
app: clasamentele de dobânzi spun la ce bănci celula are și alte monede decât lei

Cifra rămâne a celulei din 2.2; la depozitul pe 12 luni, ambele valori Raiffeisen sunt în altă monedă,
iar Libra (1 din 11) și Vista (1 din 35) au câte una (mip_merge, 08.10.2026).
EOF
git add app/server.py app/vox.py app/test_vox.py app/test_celula.py && git commit -q -F "$S/mesaj_t3.txt"
```

---

### Task 4: butoanele în `app/vox.py` — `butoane`, `din_buton`, `Vox.continua`

**Files:**
- Modify: `app/vox.py` (după `clasa`: `BUTOANE`, `butoane`, `din_buton`; în `Vox`: `_raspunde` nou, `intreaba` îl folosește, `continua` nou)
- Test: `app/test_vox.py` (clasă nouă `Butoane`; `Intrebari`)

**Interfaces:**
- Consumes: `Vox._raspuns(banca, interp, ctx)` (Task 1).
- Produces: `vox.BUTOANE = {"firme": "Pentru firme", "pf": "Pentru persoane fizice", "libra": "Compară cu Libra"}`; `vox.butoane(interp, raspunsuri, clasament) -> list[str]`; `vox.din_buton(anterior, buton) -> dict` (ridică `Respins`); `Vox.continua(anterior, buton, conversatie=None) -> dict` (ca `intreaba`: `model = None`, `cost_usd = 0.0`, plus `buton`); orice răspuns are `butoane`.

- [ ] **Step 1: testele care pică**

În `app/test_vox.py`, o clasă nouă după `Clasa`:

```python
class Butoane(unittest.TestCase):
    """Butoanele de sub un răspuns (decizia lui Nicolae, 08.10.2026): fără model, deci gratuite."""

    def rasp(self, *segmente):
        return [{"rezumat": [{"segment": s} for s in segmente]}]

    def test_cautare_comision_cu_segmente(self):
        self.assertEqual(vox.butoane(interp(), self.rasp("pf", None), None), ["firme", "libra"])
        self.assertEqual(vox.butoane(interp(segment="pj"), self.rasp("pj"), None), ["pf", "libra"])
        self.assertEqual(vox.butoane(interp(segment="pfa"), self.rasp("pfa"), None), ["firme", "pf", "libra"])

    def test_fara_segment_in_rezumat_doar_libra(self):
        self.assertEqual(vox.butoane(interp(), self.rasp(None), None), ["libra"])

    def test_dobanzi_fara_segment(self):
        """Rândurile de dobânzi n-au segment în sursă: „Pentru firme” n-ar schimba nimic."""
        self.assertEqual(vox.butoane(interp(concept="nominala", categorie="depozite"), self.rasp("pf"), None),
                         ["libra"])

    def test_libra_deja_sau_trei_banci(self):
        self.assertEqual(vox.butoane(interp(banci=["libra"]), self.rasp(None), None), [])
        self.assertEqual(vox.butoane(interp(banci=["bcr", "brd", "ing"]), self.rasp(None), None), [])

    def test_clasament(self):
        i = interp(tip="clasament", banci=[])
        self.assertEqual(vox.butoane(i, [], {"sursa": "matrice"}), ["firme"])
        self.assertEqual(vox.butoane(dict(i, segment="pj"), [], {"sursa": "matrice"}), ["pf"])
        self.assertEqual(vox.butoane(dict(i, concept="nominala", categorie="depozite"), [], {"sursa": "rate"}), [])
        self.assertEqual(vox.butoane(i, [], {"concept": None, "neclasabil": True}), [])

    def test_neclar_in_afara(self):
        for tip in ("neclar", "in_afara"):
            self.assertEqual(vox.butoane(interp(tip=tip), [], None), [])

    def test_din_buton(self):
        self.assertEqual(vox.din_buton(interp(), "firme")["segment"], "pj")
        self.assertEqual(vox.din_buton(interp(segment="pj"), "pf")["segment"], "pf")
        self.assertEqual(vox.din_buton(interp(), "libra")["banci"], ["bcr", "libra"])
        self.assertEqual(vox.din_buton(interp(tip="clasament", banci=[]), "firme")["tip"], "clasament")

    def test_din_buton_refuza(self):
        for i, b in ((interp(), "toate"), (interp(concept="nominala", categorie="depozite"), "firme"),
                     (interp(tip="clasament", banci=[]), "libra"), (interp(banci=["libra"]), "libra"),
                     (interp(banci=["bcr", "brd", "ing"]), "libra"), (interp(tip="neclar"), "firme")):
            with self.assertRaises(vox.Respins, msg=(i, b)):
                vox.din_buton(i, b)
```

În `Intrebari`, după testele din Task 1:

```python
    def test_intrebarea_are_butoane(self):
        self.randuri["bcr"] = [dict(rand(5), segment="pf")]
        self.assertEqual(self.fa(ClientFals(interp())).intreaba("BCR?")["butoane"], ["firme", "libra"])

    def test_continua_fara_model(self):
        """„Pentru firme” sub „Cât costă administrarea contului la BCR?”: același drum ca o întrebare, fără model."""
        self.randuri["bcr"] = [dict(rand(5), segment="pf"), dict(rand(20), segment="pj")]
        c = ClientFals(interp())
        v = self.fa(c)
        d = v.continua(interp(), "firme")
        self.assertEqual(c.cereri, [])
        self.assertEqual((d["model"], d["cost_usd"], d["buton"]), (None, 0.0, "firme"))
        self.assertEqual(d["interpretare"]["segment"], "pj")
        self.assertEqual([g["segment"] for g in d["raspunsuri"][0]["rezumat"]], ["pj", "pf"])
        self.assertEqual(d["butoane"], ["pf", "libra"])
        tura = v.istoric.citeste(d["conversatie"])["ture"][0]
        self.assertEqual((tura["intrebare"], tura["raspuns"]["buton"]), ("Pentru firme", "firme"))

    def test_continua_refuza(self):
        v = self.fa(ClientFals(interp()))
        with self.assertRaises(vox.Respins):
            v.continua(None, "firme")                               # fără răspunsul de sub buton
        with self.assertRaises(vox.Respins):
            v.continua(interp(), "firme", "0" * 16)                 # conversație ștearsă
        with self.assertRaises(vox.Respins):
            v.continua(interp(banci=["libra"]), "libra")            # Libra e deja acolo
```

- [ ] **Step 2: rulează testele**

Run: `PYTHONIOENCODING=utf-8 python app/test_vox.py 2>&1 | grep -E "^(FAIL|ERROR|Ran|OK|FAILED)"`
Expected: ERROR la cele 8 teste din `Butoane` (`vox.butoane` lipsește) și la cele 3 din `Intrebari` (`butoane` / `continua` lipsesc).

- [ ] **Step 3: implementarea**

În `app/vox.py`, după funcția `clasa`:

```python
# Butoanele de sub un răspuns (decizia lui Nicolae, 08.10.2026): continuă fără model, deci gratuit și fără
# riscul unei interpretări greșite. Eticheta română e textul turei în conversație.
BUTOANE = {"firme": "Pentru firme", "pf": "Pentru persoane fizice", "libra": "Compară cu Libra"}
NEPOTRIVIT = "Butonul nu se potrivește răspunsului."


def butoane(interp, raspunsuri, clasament):
    """Ce butoane are un răspuns. Segmentul doar la comisioane: rândurile de dobânzi n-au segment în sursă,
    deci „Pentru firme” n-ar schimba nimic."""
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


def din_buton(anterior, buton):
    """Interpretarea nouă după un buton, fără model. Un buton care nu se potrivește ridică `Respins`."""
    if buton not in BUTOANE or anterior["tip"] not in ("cautare", "clasament"):
        raise Respins(NEPOTRIVIT)
    nou = dict(anterior, clarificare=None)
    if buton in ("firme", "pf"):
        if anterior["categorie"]:
            raise Respins(NEPOTRIVIT)
        nou["segment"] = "pj" if buton == "firme" else "pf"
    elif anterior["tip"] != "cautare" or "libra" in anterior["banci"] or len(anterior["banci"]) >= MAX_BANCI:
        raise Respins(NEPOTRIVIT)
    else:
        nou["banci"] = anterior["banci"] + ["libra"]
    return nou
```

În clasa `Vox`, înlocuiește partea din `intreaba` de la `try: raspunsuri = …` până la `return {**rezultat, "conversatie": id}` cu `return self._raspunde(rand, intrebare, interp, ignorate, ctx)`, și adaugă metodele:

```python
    def _raspunde(self, rand, intrebare, interp, ignorate, ctx, buton=None):
        """Valorile din bază pentru o interpretare, tura salvată în conversație și rândul din jurnal: același
        drum pentru o întrebare și pentru un buton."""
        try:
            raspunsuri = [self._raspuns(b, interp, ctx) for b in interp["banci"]] if interp["tip"] == "cautare" else []
            clasament = self._clasament_raspuns(interp, ctx) if interp["tip"] == "clasament" else None
        except Exception as exc:
            # apelul la model s-a plătit deja: întrebarea intră în jurnal și când cade baza
            rand["eroare"] = f"{exc.__class__.__name__}: {exc}"
            self._jurnal(rand)
            raise
        rand["randuri"] = {r["banca"]: r["total"] for r in raspunsuri}
        if clasament and clasament.get("blocuri"):
            rand["clasate"] = len(clasament["blocuri"][0]["randuri"])
        rezultat = {"interpretare": interp, "ignorate": ignorate, "raspunsuri": raspunsuri,
                    "clasament": clasament, "model": rand["model"], "tokeni": rand["tokeni"],
                    "cost_usd": rand["cost_usd"], "butoane": butoane(interp, raspunsuri, clasament)}
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
```

(`rand` din `intreaba` are deja `model`, `conversatie`, `tokeni` și `cost_usd` înainte de `_raspunde`.)

- [ ] **Step 4: rulează testele**

Run: `PYTHONIOENCODING=utf-8 python app/test_vox.py 2>&1 | grep -E "^(FAIL|ERROR|Ran|OK|FAILED)"`
Expected: `Ran 123 tests`, `OK`.

- [ ] **Step 5: commit**

```bash
cat > "$S/mesaj_t4.txt" <<'EOF'
app: butoanele Vox „Pentru firme / persoane fizice” și „Compară cu Libra” răspund fără model

Interpretarea nouă se face din cea a răspunsului, deci tura costă 0 și nu poate fi înțeleasă greșit;
serverul decide ce butoane are fiecare răspuns (decizia lui Nicolae, 08.10.2026).
EOF
git add app/vox.py app/test_vox.py && git commit -q -F "$S/mesaj_t4.txt"
```

---

### Task 5: `POST /api/vox` cu `buton` + `anterior` (`app/server.py`)

**Files:**
- Modify: `app/server.py` (`Handler._post_vox`)
- Test: `app/test_vox.py` (clasa `Http`)

**Interfaces:**
- Consumes: `VOX.continua(anterior, buton, conversatie)` (Task 4).
- Produces: `POST /api/vox` cu `{buton, anterior, conversatie}` → 200 cu răspunsul de la `continua`; `intrebare` și `buton` deodată → 400.

- [ ] **Step 1: testele care pică**

În clasa `Http`, după `test_post_salveaza_si_continua`:

```python
    def test_post_buton_fara_model(self):
        """„Compară cu Libra” sub un răspuns: același drum ca întrebarea, fără apel la model (08.10.2026)."""
        ok = {"X-MIP-Token": self.token()}
        n = len(self.client.cereri)
        cod, d = self.cere("POST", "/api/vox", {"buton": "libra", "anterior": interp()}, ok)
        self.assertEqual(cod, 200, d)
        self.assertEqual((d["model"], d["cost_usd"], d["buton"]), (None, 0, "libra"))
        self.assertEqual([r["banca"] for r in d["raspunsuri"]], ["bcr", "libra"])
        self.assertEqual(len(self.client.cereri), n)

    def test_post_buton_refuzat(self):
        ok = {"X-MIP-Token": self.token()}
        n = len(self.client.cereri)
        for corp in ({"buton": "toate", "anterior": interp()},
                     {"buton": "firme", "anterior": interp(concept="nominala", categorie="depozite")},
                     {"buton": "libra", "anterior": interp(), "intrebare": "BCR?"},
                     {"buton": "libra"}):
            self.assertEqual(self.cere("POST", "/api/vox", corp, ok)[0], 400, corp)
        self.assertEqual(self.cere("POST", "/api/vox", {"buton": "libra", "anterior": interp()})[0], 403)
        self.assertEqual(len(self.client.cereri), n)               # niciun apel plătit
```

- [ ] **Step 2: rulează testele**

Run: `PYTHONIOENCODING=utf-8 python app/test_vox.py 2>&1 | grep -E "^(FAIL|ERROR|Ran|OK|FAILED)"`
Expected: FAIL la ambele (serverul cheamă `intreaba` cu `intrebare` lipsă → 400 la primul; la al doilea, cererea cu `intrebare` + `buton` ajunge la model).

- [ ] **Step 3: implementarea**

În `_post_vox`, blocul `try` devine:

```python
        try:
            if "buton" in corp:
                if corp.get("intrebare") is not None:
                    raise vox.Respins("Trimite o întrebare sau un buton, nu amândouă.")
                rezultat = VOX.continua(corp.get("anterior"), corp.get("buton"), corp.get("conversatie"))
            else:
                rezultat = VOX.intreaba(corp.get("intrebare"), corp.get("anterior"), corp.get("conversatie"))
            self._json(200, rezultat)
```

(restul, `except vox.Respins` / `EroareModel` / `Exception`, rămâne.)

- [ ] **Step 4: rulează testele**

Run: aceeași comandă.
Expected: `Ran 125 tests`, `OK`.

- [ ] **Step 5: commit**

```bash
cat > "$S/mesaj_t5.txt" <<'EOF'
app: POST /api/vox primește și butonul de sub un răspuns, cu aceleași verificări ca întrebarea

Token, Host, Origin și corpul de cel mult 4 KB rămân; o cerere cu întrebare și buton deodată e refuzată.
EOF
git add app/server.py app/test_vox.py && git commit -q -F "$S/mesaj_t5.txt"
```

---

### Task 6: cache-ul promptului de o oră (`app/vox.py`, `preturi.py`, `eval_vox.py`)

**Files:**
- Modify: `app/vox.py` (`_cheama`: `ttl`; `intreaba`: costul)
- Modify: `extragere_produse_bancare/preturi.py` (`FACTOR_SCRIERE_CACHE_1H`, `cost(..., scriere_cache_1h=0)`)
- Modify: `app/eval_vox.py` (`COST_PRIMA` și comentariul)
- Test: `app/test_vox.py` (`ClientFals`, `Intrebari.test_cautare_pe_concept`, `Preturi`)

**Interfaces:**
- Produces: `preturi.cost(model, intrare=0, iesire=0, citire_cache=0, scriere_cache=0, scriere_cache_1h=0)`.

- [ ] **Step 1: testele care pică**

`ClientFals.__init__` primește `scriere=0`: semnătura devine `def __init__(self, raspuns=None, stop="end_turn", exceptie=None, scriere=0):`, cu `self._scriere = scriere`, iar în `create`, `cache_creation_input_tokens=self._scriere`.

În `test_cautare_pe_concept`, aserțiunea pe cache devine:

```python
        # cache de o oră: în conversația din 08.10.2026, 3 din 18 întrebări au rescris promptul după pauze de
        # 5–9 minute și au costat 4,9 din cei 7,5 cenți
        self.assertEqual(cerere["system"][0]["cache_control"], {"type": "ephemeral", "ttl": "1h"})
```

În `Intrebari`, un test nou:

```python
    def test_scrierea_in_cache_de_o_ora(self):
        """Scrierea de o oră costă de 2 ori prețul de intrare, nu de 1,25 ori (documentația Anthropic)."""
        d = self.fa(ClientFals(interp(), scriere=12000)).intreaba("BCR?")
        self.assertAlmostEqual(d["cost_usd"], (1200 * 1 + 60 * 5 + 7000 * 0.1 + 12000 * 2) / 1e6)
```

În `Preturi`:

```python
    def test_scrierea_de_o_ora(self):
        self.assertAlmostEqual(vox.preturi.cost("claude-haiku-4-5", scriere_cache_1h=1_000_000), 2.0)
        self.assertAlmostEqual(vox.preturi.cost("claude-haiku-4-5", scriere_cache=1_000_000), 1.25)
```

- [ ] **Step 2: rulează testele**

Run: `PYTHONIOENCODING=utf-8 python app/test_vox.py 2>&1 | grep -E "^(FAIL|ERROR|Ran|OK|FAILED)"`
Expected: FAIL la `test_cautare_pe_concept` (fără `ttl`) și `test_scrierea_in_cache_de_o_ora` (1,25 în loc de 2), ERROR la `test_scrierea_de_o_ora` (`scriere_cache_1h` necunoscut).

- [ ] **Step 3: implementarea**

`extragere_produse_bancare/preturi.py`, după `FACTOR_SCRIERE_CACHE = 1.25`:

```python
# Scrierea cu `ttl: "1h"` (promptul lui Vox, din 08.10.2026): de 2 ori prețul de intrare (documentația
# Anthropic); citirea rămâne 0,1 indiferent de durată.
FACTOR_SCRIERE_CACHE_1H = 2.0
```

`cost` primește parametrul `scriere_cache_1h: int = 0` (ultimul) și termenul
`+ scriere_cache_1h / 1e6 * pi * FACTOR_SCRIERE_CACHE_1H` în sumă.

`app/vox.py`, în `_cheama`:

```python
                # o oră, nu 5 minute: în conversația din 08.10.2026, 3 din 18 întrebări au rescris promptul după
                # pauze de 5–9 minute și au costat 4,9 din cei 7,5 cenți; documentația recomandă ora pentru
                # întrebări la 5–60 de minute una de alta
                system=[{"type": "text", "text": sistem, "cache_control": {"type": "ephemeral", "ttl": "1h"}}],
```

În `intreaba`, costul:

```python
        # singurul marcaj de cache din cerere e cel de o oră, deci orice scriere e de o oră
        cost = preturi.cost(m, tokeni["intrare"], tokeni["iesire"], tokeni["citire_cache"],
                            scriere_cache_1h=tokeni["scriere_cache"])
```

`app/eval_vox.py`: comentariul și constanta devin

```python
# măsurat pe 08.10.2026 (Haiku 4.5, mip_merge): 12.842 de tokeni de intrare pe întrebare, $0,0020 pe întrebare
# cu promptul în cache; prima întrebare scrie cache-ul de o oră, de 2 ori prețul de intrare (~$0,026)
COST_PRIMA, COST_ESTIMAT = 0.026, 0.0020
```

- [ ] **Step 4: rulează testele**

Run: `PYTHONIOENCODING=utf-8 python app/test_vox.py 2>&1 | grep -E "^(FAIL|ERROR|Ran|OK|FAILED)"; PYTHONIOENCODING=utf-8 python app/eval_vox.py | tail -2`
Expected: `Ran 127 tests`, `OK`; estimarea: `44 întrebări, model claude-haiku-4-5, cost estimat ~$0.11`.

- [ ] **Step 5: commit**

```bash
cat > "$S/mesaj_t6.txt" <<'EOF'
app: promptul lui Vox stă în cache o oră, iar costul afișat folosește prețul scrierii de o oră

În conversația din 08.10.2026, 3 din 18 întrebări au rescris promptul după pauze de 5–9 minute și au
costat 4,9 din cei 7,5 cenți; cu ora, aceeași conversație costă ~5,3 cenți.
EOF
git add app/vox.py app/test_vox.py app/eval_vox.py extragere_produse_bancare/preturi.py && git commit -q -F "$S/mesaj_t6.txt"
```

---

### Task 7: criteriile din spec pe baza reală, cu un model fals

**Files:**
- Script: `SCRATCH/raspunsuri_citire.py` (nou), produce `SCRATCH/raspunsuri_citire.json` pentru Task 8–10

**Interfaces:**
- Consumes: Task 1–4.
- Produces: `raspunsuri_citire.json`: listă de `{intrebare, raspuns, butoane: {buton: raspuns}}`.

- [ ] **Step 1: scriptul**

`SCRATCH/raspunsuri_citire.py`:

```python
"""Fișa și clasamentele Vox pe baza reală (mip_merge), cu un model fals: criteriile de reușită din spec-ul
2026-10-08-vox-citire-corecta-design.md și fișierul pentru verificarea paginii. Niciun apel plătit.

  python raspunsuri_citire.py [<iesire.json>]
"""
import json, os, sys, tempfile, types
sys.stdout.reconfigure(encoding="utf-8")
RAD = r"C:\Users\nicolae.cherascu\Desktop\Market-Intelligence-Platform"
os.chdir(RAD); sys.path.insert(0, os.path.join(RAD, "app"))
import server, vox


class Fals:
    """Clientul Anthropic fals: întoarce interpretarea dată și numără apelurile."""

    def __init__(self, interp):
        self.interp, self.messages, self.apeluri = interp, self, 0

    def create(self, **kw):
        self.apeluri += 1
        return types.SimpleNamespace(
            content=[types.SimpleNamespace(type="text", text=json.dumps(self.interp))], stop_reason="end_turn",
            usage=types.SimpleNamespace(input_tokens=12, output_tokens=58, cache_read_input_tokens=12842,
                                        cache_creation_input_tokens=0))


def i(**k):
    b = {"tip": "cautare", "banci": [], "concept": None, "categorie": None, "termen": None,
         "produs_credit": None, "text_cautat": None, "clarificare": None, "segment": None, "metrica": None}
    b.update(k)
    return b


CAZURI = [
    ("Ce dobândă are Libra la depozitul pe 12 luni?",
     i(banci=["libra"], concept="nominala", categorie="depozite", termen="12"), ()),
    ("Cât costă administrarea contului la BCR?", i(banci=["bcr"], concept="administrare_cont"), ("firme", "libra")),
    ("Cât costă schimbarea PIN-ului la Garanti?", i(banci=["garanti"], concept="schimbare_pin"), ()),
    ("Cine dă cea mai mare dobândă la depozitul pe 12 luni?",
     i(tip="clasament", concept="nominala", categorie="depozite", termen="12"), ()),
    ("Care bancă are cel mai mic comision de administrare?",
     i(tip="clasament", concept="administrare_cont"), ("firme",)),
]
ctx = server._context_vox()
iesire, d = [], {}
for q, interp, apasate in CAZURI:
    client = Fals(interp)
    v = vox.Vox(context=lambda: ctx, cauta=server._cauta_vox, stare_banca=server._stare_banca_vox,
                clasament=server._clasament_vox, stare_banci=server._stare_banci_vox,
                client=client, dir_jurnal=tempfile.mkdtemp(prefix="vox_citire_"))
    r = v.intreaba(q)
    caz = {"intrebare": q, "raspuns": r, "butoane": {b: v.continua(r["interpretare"], b, r["conversatie"])
                                                     for b in apasate}}
    assert client.apeluri == 1, (q, client.apeluri)          # butoanele nu cheamă modelul
    iesire.append(caz)
    d[q] = caz

# 1. depozitul Libra: trei carduri pe monedă (cade pe termen nespecificat)
rb = d["Ce dobândă are Libra la depozitul pe 12 luni?"]["raspuns"]["raspunsuri"][0]
monede = [(g["moneda"], g["n"], g["minim"], g["maxim"]) for g in rb["rezumat"]]
print("Libra · depozit:", rb["filtre_relaxate"], monede)
assert rb["filtre_relaxate"] == ["termen"]
assert monede == [("lei", 1, 4.75, 4.75), ("eur", 1, 1.95, 1.95), (None, 9, 2.2, 5.5)], monede
# 2. BCR · administrare cont: cardul PF în lei, pe frecvență; data pe rânduri
rb = d["Cât costă administrarea contului la BCR?"]["raspuns"]["raspunsuri"][0]
pf = next(g for g in rb["rezumat"] if g["segment"] == "pf" and g["unitate"] == "lei")
frecvente = [(f["frecventa"], f["n"], f["minim"], f["maxim"]) for f in pf["frecvente"]]
print("BCR · PF în lei:", frecvente)
assert frecvente == [("lunar", 16, 0.0, 100.0), (None, 11, 0.0, 100.0), ("anual", 6, 0.0, 1200.0)], frecvente
cu_data = sum(1 for x in rb["randuri"] if x.get("data_vigoare"))
print("   rânduri cu dată în răspuns:", cu_data, "din", len(rb["randuri"]))
assert cu_data > 0
# 3. Garanti · PIN: doar limite
rb = d["Cât costă schimbarea PIN-ului la Garanti?"]["raspuns"]["raspunsuri"][0]
print("Garanti · PIN:", rb["rezumat"], [(g["segment"], g["categorie"], g["n"]) for g in rb["alte"]])
assert rb["rezumat"] == [] and sum(g["n"] for g in rb["alte"]) == 7
assert {g["categorie"] for g in rb["alte"]} == {"limita"}
assert all(x.get("tip_alt") == "limita" for x in rb["randuri"] if not x.get("ambiguu"))
# 4. clasamentul depozitelor pe 12 luni: nota de monedă
c = d["Cine dă cea mai mare dobândă la depozitul pe 12 luni?"]["raspuns"]["clasament"]
marcate = sorted((b["tip"], r["banca"], r["alte_monede"]["n"], r["alte_monede"]["din"])
                 for b in c["blocuri"] for r in b["randuri"] if r.get("alte_monede"))
print("12 luni, alte monede:", marcate)
assert marcate == [("exact", "raiffeisen", 2, 2), ("nespecificat", "libra", 1, 11),
                   ("nespecificat", "vista", 1, 35)], marcate
# 5. butoanele
caz = d["Cât costă administrarea contului la BCR?"]
assert caz["raspuns"]["butoane"] == ["firme", "libra"], caz["raspuns"]["butoane"]
f = caz["butoane"]["firme"]
print("buton firme:", f["interpretare"]["segment"], f["raspunsuri"][0]["rezumat"][0]["segment"], f["model"],
      f["cost_usd"], f["butoane"])
assert f["interpretare"]["segment"] == "pj" and f["raspunsuri"][0]["rezumat"][0]["segment"] == "pj"
assert (f["model"], f["cost_usd"], f["buton"]) == (None, 0.0, "firme")
assert [r["banca"] for r in caz["butoane"]["libra"]["raspunsuri"]] == ["bcr", "libra"]
libra = d["Care bancă are cel mai mic comision de administrare?"]["butoane"]["firme"]["clasament"]["libra"]
print("clasament PJ, Libra:", libra)
assert (libra["loc"], libra["loc_pana"]) == (8, 10), libra
if len(sys.argv) > 1:
    with open(sys.argv[1], "w", encoding="utf-8") as fis:
        json.dump(iesire, fis, ensure_ascii=False, default=str)
print("CRITERII: toate îndeplinite")
```

- [ ] **Step 2: rulează**

Run: `PYTHONIOENCODING=utf-8 python "$S/raspunsuri_citire.py" "$S/raspunsuri_citire.json"`
Expected: liniile de mai sus și `CRITERII: toate îndeplinite`. O aserțiune care pică e o constatare: cifra se compară cu măsurătoarea din spec (08.10.2026), cauza se caută cu superpowers:systematic-debugging, iar o abatere justificată se trece în registru ca `Ruling:`.

(Fără commit: scriptul și JSON-ul stau în `SCRATCH`.)

---

### Task 8: pagina — schemele și fișa care citește corect

**Files:**
- Modify: `shared/src/vox.ts` (`FrecventaGrupa`, `GrupaRezumat`, `RaspunsBanca.alte`, `RandClasament.alte_monede`, `Buton`, `RaspunsIntrebare`)
- Modify: `shared/src/celula.ts` (`ValoareDovada.data_vigoare`, `tip_alt`)
- Modify: `web/src/components/Sertar.tsx` (`CerereSertar.valuta`, parametrul cererii)
- Modify: `web/src/pages/Vox.tsx` (`FisaBanca`, `PlacaRezumat`, `Rand`, `textDoarAlte`, `etFrecventa`; importul `formatZi`)
- Modify: `web/src/i18n/dict/vox.ts`, `web/src/styles/vox.css`
- Script: `SCRATCH/verifica_citire_ui.py` (nou)

**Interfaces:**
- Consumes: răspunsurile din Task 1–4, `raspunsuri_citire.json` (Task 7).
- Produces: tipurile `Buton`, `FrecventaGrupa`; `CerereSertar.valuta`; `verifica_citire_ui.py` cu părțile `fisa`, `clasament`, `butoane`.

- [ ] **Step 1: verificarea care pică (Playwright, înainte de modificări în `web/`)**

`SCRATCH/verifica_citire_ui.py`:

```python
"""Fișa Vox care citește corect (monedă, frecvență, tip, dată), nota de monedă din clasament și butoanele
fără model, în pagina de pe :5173; API-ul spre serverul temporar de pe :8797, POST /api/vox din
raspunsuri_citire.json. Niciun apel plătit.

  python verifica_citire_ui.py <raspunsuri_citire.json> <dosar capturi> <fisa,clasament,butoane>
"""
import json, os, sys
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
CAZURI = json.load(open(sys.argv[1], encoding="utf-8"))
OUT, PARTI = sys.argv[2], set(sys.argv[3].split(","))
TINTA = "http://localhost:8797"
PE_INTREBARE = {c["intrebare"]: c for c in CAZURI}
# un răspuns valid pentru întrebările fără fișier (se verifică doar corpul cererii): fără abort, consola rămâne curată
ORICARE = CAZURI[1]["butoane"]["firme"]
celule, posturi, probleme, erori = [], [], [], []
TEXTE = {
    "ro": {"lei": "în lei", "eur": "în euro", "nespusa": "monedă nespusă", "lunar": "pe lună", "anual": "pe an",
           "doar": "Nicio valoare de comision", "limita": "limită", "din": "din ", "monede": "Raiffeisen (2 din 2)",
           "firme": "Pentru firme", "libra": "Compară cu Libra", "fara_model": "fără model"},
    "en": {"lei": "in lei", "eur": "in euro", "nespusa": "currency not stated", "lunar": "per month",
           "anual": "per year", "doar": "No fee values", "limita": "limit", "din": "since ",
           "monede": "Raiffeisen (2 of 2)", "firme": "For businesses", "libra": "Compare with Libra",
           "fara_model": "no model call"},
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
    if u.path == "/api/celula":
        celule.append(parse_qs(u.query))
    route.fulfill(response=route.fetch(url=TINTA + u.path + (f"?{u.query}" if u.query else "")))


def pagina(b, tema, lang):
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"try {{ localStorage.setItem('mcc-tema', '{tema}'); localStorage.setItem('mcc-lang', '{lang}') }} catch (e) {{}}")
    pg = ctx.new_page()
    pg.on("console", lambda m: probleme.append(f"{lang} {m.type}: {m.text}") if m.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: probleme.append(f"{lang} pageerror: {e}"))
    pg.route(e_server, ruta)
    pg.goto("http://localhost:5173/#/vox")
    pg.locator(".vox-conv-noua").first.wait_for(timeout=15000)
    return ctx, pg


def intreaba(pg, q):
    n = pg.locator(".vox-card, .vox-bula").count()
    camp = pg.locator(".vox-cutie textarea")
    camp.fill(q)
    camp.press("Enter")
    pg.wait_for_function(f"document.querySelectorAll('.vox-card, .vox-bula').length > {n}", timeout=15000)
    pg.wait_for_timeout(500)
    return pg.locator(".vox-card, .vox-bula").last


def sertar(pg, buton):
    inainte = len(celule)
    buton.click()
    pg.locator(".ant-drawer .s-rez").first.wait_for(timeout=15000)
    q = celule[-1] if len(celule) > inainte else {}
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(400)
    return q


def verifica_fisa(pg, lang):
    T = TEXTE[lang]
    card = intreaba(pg, "Ce dobândă are Libra la depozitul pe 12 luni?")
    kpi = card.locator(".vox-kpis .vox-kpi")
    texte = kpi.all_inner_texts()
    print(f"[{lang}] depozit Libra:", [x.replace("\n", " · ") for x in texte])
    if verifica(len(texte) == 3, f"[{lang}] depozit Libra: {len(texte)} carduri în loc de 3"):
        verifica(T["lei"] in texte[0] and T["eur"] in texte[1] and T["nespusa"] in texte[2], f"[{lang}] monedele: {texte}")
        q = sertar(pg, kpi.nth(1).locator(".vox-link"))
        verifica(q.get("valuta") == ["eur"], f"[{lang}] sertarul cardului „în euro” cere {q}")
    card = intreaba(pg, "Cât costă administrarea contului la BCR?")
    frecv = text(card.locator(".vox-kpi .vox-frecvente"))
    print(f"[{lang}] BCR PF:", frecv.replace("\n", " · "))
    verifica(T["lunar"] in frecv and T["anual"] in frecv, f"[{lang}] frecvențele: {frecv!r}")
    card.locator(".vox-fisa-jos button.vox-link").first.click()             # toate rândurile
    pg.wait_for_timeout(400)
    date = [x for x in card.locator(".vox-tabel td.val .sub").all_inner_texts() if x.startswith(T["din"])]
    print(f"[{lang}] rânduri cu dată: {len(date)}, de pildă {date[:2]}")
    verifica(len(date) > 0, f"[{lang}] niciun rând cu dată")
    card.screenshot(path=os.path.join(OUT, f"citire_bcr_{lang}.png"))
    card = intreaba(pg, "Cât costă schimbarea PIN-ului la Garanti?")
    note = card.locator(".vox-nota").all_inner_texts()
    print(f"[{lang}] Garanti:", note)
    verifica(any(T["doar"] in x for x in note), f"[{lang}] lipsește „{T['doar']}”: {note}")
    alte = card.locator(".vox-alte .vox-kpi")
    if verifica(alte.count() == 2, f"[{lang}] „alte valori”: {alte.count()} carduri în loc de 2"):
        q = sertar(pg, alte.first.locator(".vox-link"))
        verifica(q.get("scenariu") == ["limita"], f"[{lang}] sertarul limitelor cere {q}")
    pastile = card.locator(".vox-tabel .pill").all_inner_texts()
    verifica(T["limita"] in pastile, f"[{lang}] pastila de tip: {pastile}")
    card.screenshot(path=os.path.join(OUT, f"citire_garanti_{lang}.png"))


def verifica_clasament(pg, lang):
    T = TEXTE[lang]
    card = intreaba(pg, "Cine dă cea mai mare dobândă la depozitul pe 12 luni?")
    nota = text(card.locator(".vox-clas-monede"))
    print(f"[{lang}] nota de monedă:", nota)
    verifica(T["monede"] in nota, f"[{lang}] nota de monedă: {nota!r}")
    semne = card.locator(".vox-clas .vox-clas-moneda").count()
    verifica(semne == 3, f"[{lang}] semnele de monedă din tabel: {semne} în loc de 3")
    card.screenshot(path=os.path.join(OUT, f"citire_clasament_{lang}.png"))


def verifica_butoane(pg, lang):
    T = TEXTE[lang]
    card = intreaba(pg, "Cât costă administrarea contului la BCR?")
    etichete = card.locator(".vox-butoane button").all_inner_texts()
    print(f"[{lang}] butoane:", etichete)
    if not verifica(etichete == [T["firme"], T["libra"]], f"[{lang}] butoanele: {etichete}"):
        return
    n, carduri = len(posturi), pg.locator(".vox-card, .vox-bula").count()
    card.locator(".vox-butoane button").first.click()
    pg.wait_for_function(f"document.querySelectorAll('.vox-card, .vox-bula').length > {carduri}", timeout=15000)
    pg.wait_for_timeout(500)
    corp = posturi[-1] if len(posturi) > n else {}
    print(f"[{lang}] POST buton:", {k: corp.get(k) for k in ("buton", "intrebare")})
    verifica(corp.get("buton") == "firme" and "intrebare" not in corp
             and (corp.get("anterior") or {}).get("concept") == "administrare_cont", f"[{lang}] corpul POST: {corp}")
    q = pg.locator(".vox-q").last.inner_text()
    verifica(T["firme"] in q and T["fara_model"] in q, f"[{lang}] bula turei: {q!r}")
    verifica(T["fara_model"] in text(pg.locator(".vox-card").last.locator(".vox-card-jos")),
             f"[{lang}] subsolul turei date de buton")
    # o întrebare scrisă după buton continuă interpretarea butonului (segmentul PJ)
    camp = pg.locator(".vox-cutie textarea")
    camp.fill("și la BRD?")
    camp.press("Enter")
    pg.wait_for_timeout(1500)
    verifica((posturi[-1].get("anterior") or {}).get("segment") == "pj", f"[{lang}] anterior după buton: {posturi[-1]}")
    card = intreaba(pg, "Care bancă are cel mai mic comision de administrare?")
    verifica(card.locator(".vox-butoane button").all_inner_texts() == [T["firme"]], f"[{lang}] butoanele clasamentului")
    pg.screenshot(path=os.path.join(OUT, f"citire_butoane_{lang}.png"))


def conversatii_vechi(b):
    # salvate înainte de 08.10.2026: fără `alte`, `moneda`, `frecvente`, `butoane`; `model` mereu text
    for c in ("f829ad3c5a2732e5", "0064ce56dddf70ac", "35b2f7f797944207"):
        ctx, pg = pagina(b, "luminos", "ro")
        pg.goto(f"http://localhost:5173/#/vox?c={c}")
        pg.locator(".vox-fisa, .vox-bula").first.wait_for(timeout=15000)
        n = pg.locator(".vox-butoane button").count()
        print(f"conversația veche {c}: {pg.locator('.vox-fisa').count()} fișe, {n} butoane")
        verifica(n == 0, f"conversația veche {c} are butoane")
        ctx.close()


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge")
    for tema, lang in (("luminos", "ro"), ("intunecat", "en")):
        ctx, pg = pagina(b, tema, lang)
        if "fisa" in PARTI:
            verifica_fisa(pg, lang)
        if "clasament" in PARTI:
            verifica_clasament(pg, lang)
        if "butoane" in PARTI:
            verifica_butoane(pg, lang)
        ctx.close()
    if "butoane" in PARTI:
        conversatii_vechi(b)
    b.close()
print("PROBLEME CONSOLĂ:", json.dumps(probleme, ensure_ascii=False, indent=1) if probleme else "niciuna")
print("REZULTAT:", f"{len(erori)} eșecuri" if erori else "OK")
sys.exit(1 if erori or probleme else 0)
```

Run: `bash "$S/cu_server_8797.sh" python "$S/verifica_citire_ui.py" "$S/raspunsuri_citire.json" "$S" fisa`
Expected: `REZULTAT: N eșecuri` (monedele, `valuta`, frecvențele, data, „Nicio valoare de comision”, „alte valori”, pastila de tip).

- [ ] **Step 2: schemele**

`shared/src/celula.ts`, în `ValoareDovada`, după `ancora`:

```ts
    /** data intrării în vigoare (ISO), când sursa o are; o arată doar fișa din Vox */
    data_vigoare: z.string().nullable().optional(),
    /** tipul rândului când nu e prețul serviciului („limita”, „nota” …): îl pune Vox, nu /api/celula */
    tip_alt: z.string().nullable().optional(),
```

`shared/src/vox.ts`, înaintea lui `GrupaRezumat`:

```ts
/** O frecvență dintr-o grupă de comision (lunar, anual …; null = sursa n-o spune). */
export const FrecventaGrupa = z.object({ frecventa: z.string().nullable(), n: z.number(), minim: z.number(), maxim: z.number() })
export type FrecventaGrupa = z.infer<typeof FrecventaGrupa>

/** Butoanele de sub un răspuns, care continuă fără model (app/vox.py, `BUTOANE`). */
export const Buton = z.enum(['firme', 'pf', 'libra'])
export type Buton = z.infer<typeof Buton>
```

`GrupaRezumat` primește, după `categorie`, `moneda` și, după `gratuite`, `frecvente`:

```ts
  /** doar la dobânzi: lei / eur / usd / gbp / chf, null = monedă nespusă; lipsește la comisioane și în conversațiile vechi */
  moneda: z.string().nullable().optional(),
```
```ts
  /** doar la comisioanele cu mai multe frecvențe (de pildă lunar și anual); lipsește altfel */
  frecvente: z.array(FrecventaGrupa).optional(),
```

`RaspunsBanca`, după `rezumat`:

```ts
    /** notele, limitele, cursurile găsite la serviciu, separat de preț; lipsește în conversațiile vechi */
    alte: z.array(GrupaRezumat).optional(),
```

`RandClasament`, după `evidentiata`: `alte_monede: z.object({ n: z.number(), din: z.number() }).optional(),`

`RaspunsIntrebare`: `model: z.string().nullable(),` (cu comentariul `/** null = tură dată de un buton, fără model */`), iar după `cost_usd`:

```ts
    /** butoanele de sub răspuns; lipsesc în conversațiile salvate înainte de 08.10.2026 */
    butoane: z.array(Buton).optional(),
    /** butonul care a dat tura (fără model) */
    buton: Buton.optional(),
```

- [ ] **Step 3: sertarul și fișa**

`web/src/components/Sertar.tsx`: în `CerereSertar`, după `strict`:

```ts
  /** moneda unei dobânzi (lei / eur / usd / gbp / chf / nespusa): o trimit doar cardurile pe monedă din Vox */
  valuta?: string
```

iar în cererea `/api/celula`, după `strict: cerere!.strict ? 1 : undefined`, adaugă `, valuta: cerere!.valuta`.

`web/src/pages/Vox.tsx`: importul din `../util/format` devine `import { formatZi, num } from '../util/format'`. În `FisaBanca`, între `const vizibile = …` și `return (`:

```tsx
  const alte = rb.alte ?? []
  // „Vezi dovezile” de pe o grupă: aceeași bancă, concept, unitate și tip; la dobânzi, și moneda grupei
  const dovezi = (g: GrupaRezumat) => (rb.mod === 'concept' && i.concept ? () => onDovezi({
    banca: rb.banca, camp: i.concept!, unitate: g.unitate, scenariu: g.categorie, termen, produs,
    ...(cuSegmente ? { segment: g.segment ?? 'nemarcat', strict: true } : {}),
    ...(g.moneda !== undefined ? { valuta: g.moneda ?? 'nespusa' } : {}),
  }) : undefined)
```

Cardurile din `peSegmente(rb.rezumat)` devin
`<PlacaRezumat key={`${g.unitate}|${g.categorie}|${g.moneda ?? ''}`} g={g} multeCategorii={multeCategorii} onDovezi={dovezi(g)} />`,
iar imediat după blocul `peSegmente(...)` (înaintea notei `rb.limitat`):

```tsx
      {!rb.rezumat.length && alte.length > 0 && (
        <p className="vox-nota"><span className="vox-punct" />{textDoarAlte(alte, i, t)}</p>
      )}
      {alte.length > 0 && (
        <div className="vox-segment vox-alte">
          <span className="vox-segment-cap">{t('vox.alte.titlu')}</span>
          <div className="vox-kpis">
            {alte.map((g) => (
              <PlacaRezumat key={`${g.segment ?? ''}|${g.unitate}|${g.categorie}`} g={g} multeCategorii tip onDovezi={dovezi(g)} />
            ))}
          </div>
        </div>
      )}
```

Funcții noi, după `textBlocaje`:

```tsx
/** „Nicio valoare de comision; am găsit doar limite (7).”: Garanti · schimbarea PIN-ului (mip_merge, 08.10.2026). */
function textDoarAlte(alte: GrupaRezumat[], i: Interpretare, t: Tr): string {
  const n = alte.reduce((s, g) => s + g.n, 0)
  const tipuri = [...new Set(alte.map((g) => g.categorie))].map((c) => eticheta(`vox.alte.tipuri.${c}`, c, t)).join(', ')
  return t('vox.alte.doar', { ce: t(i.categorie ? 'vox.alte.ce_dobanda' : 'vox.alte.ce_comision'), tipuri, n })
}

/** Eticheta unei frecvențe din date („lunar”, „pe tranzacție”); una necunoscută rămâne cum e în date. */
function etFrecventa(f: string | null, t: Tr): string {
  if (!f) return t('vox.frecventa.fara')
  const k = f.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim().replace(/\s+/g, '_')
  return eticheta(`vox.frecventa.${k}`, f, t)
}
```

`PlacaRezumat` întreg:

```tsx
function PlacaRezumat({ g, multeCategorii, tip, onDovezi }: {
  g: GrupaRezumat; multeCategorii: boolean; tip?: boolean; onDovezi?: () => void
}) {
  const { t, tn, locale } = useLang()
  const unitate = unitTxt(g.unitate, t).trim()
  const egal = g.minim === g.maxim
  const interval = (a: number, b: number) => (a === b ? num(a, locale) : `${num(a, locale)} – ${num(b, locale)}`)
  return (
    <div className="vox-kpi">
      {g.frecvente?.length
        ? (
          // BCR · administrare cont PF: „0 – 1.200 lei” punea 6 sume anuale lângă 16 lunare (08.10.2026)
          <span className="vox-frecvente">
            {g.frecvente.map((f) => (
              <span key={f.frecventa ?? '-'}>
                <b>{interval(f.minim, f.maxim)}{unitate && <small> {unitate}</small>}</b>
                {' '}{etFrecventa(f.frecventa, t)} · {tn('vox.kpi', f.n)}
              </span>
            ))}
          </span>
        )
        : (
          <span className="v">
            {interval(g.minim, g.maxim)}
            {unitate && <small> {unitate}</small>}
          </span>
        )}
      <span className="l">
        {egal && g.n > 1 ? tn('vox.kpi_egal', g.n) : tn('vox.kpi', g.n)}
        {g.gratuite > 0 && <> · {tn('vox.gratuite', g.gratuite)}</>}
        {g.moneda !== undefined && <> · {eticheta(`vox.moneda.${g.moneda ?? 'nespusa'}`, g.moneda ?? '', t)}</>}
        {(multeCategorii || tip) && <> · {eticheta(tip ? `vox.tip.${g.categorie}` : `vox.categorie.${g.categorie}`, g.categorie, t)}</>}
      </span>
      {onDovezi && <button type="button" className="vox-link" onClick={onDovezi}>{t('vox.vezi_dovezi')}</button>}
    </div>
  )
}
```

În `Rand`, prima celulă primește, după pastila de segment,
`{v.tip_alt && <span className="vox-seg"><Pill>{eticheta(`vox.tip.${v.tip_alt}`, v.tip_alt, t)}</Pill></span>}`,
iar celula valorii devine:

```tsx
      <td className="dr val">
        {valoare}{v.frecventa && <span className="sub">{v.frecventa}</span>}
        {v.data_vigoare && <span className="sub">{t('vox.din_data', { data: formatZi(v.data_vigoare, locale) })}</span>}
      </td>
```

- [ ] **Step 4: textele și stilurile**

`web/src/i18n/dict/vox.ts`, lângă cheile `vox.kpi*`:

```ts
  "vox.moneda.lei": ["în lei", "in lei"],
  "vox.moneda.eur": ["în euro", "in euro"],
  "vox.moneda.usd": ["în dolari", "in US dollars"],
  "vox.moneda.gbp": ["în lire sterline", "in pounds sterling"],
  "vox.moneda.chf": ["în franci elvețieni", "in Swiss francs"],
  "vox.moneda.nespusa": ["monedă nespusă în sursă", "currency not stated in the source"],
  "vox.frecventa.lunar": ["pe lună", "per month"],
  "vox.frecventa.anual": ["pe an", "per year"],
  "vox.frecventa.zilnic": ["pe zi", "per day"],
  "vox.frecventa.trimestrial": ["pe trimestru", "per quarter"],
  "vox.frecventa.pe_card": ["pe card", "per card"],
  "vox.frecventa.pe_operatiune": ["pe operațiune", "per operation"],
  "vox.frecventa.pe_tranzactie": ["pe tranzacție", "per transaction"],
  "vox.frecventa.fara": ["fără frecvență în sursă", "no frequency in the source"],
  "vox.tip.limita": ["limită", "limit"],
  "vox.tip.nota": ["notă", "note"],
  "vox.tip.dobanda": ["dobândă", "interest rate"],
  "vox.tip.curs": ["curs valutar", "exchange rate"],
  "vox.alte.titlu": ["Alte valori găsite la acest serviciu", "Other values found for this service"],
  "vox.alte.doar": ["Nicio valoare de {ce}; am găsit doar {tipuri} ({n}).", "No {ce} values; we only found {tipuri} ({n})."],
  "vox.alte.ce_comision": ["comision", "fee"],
  "vox.alte.ce_dobanda": ["dobândă", "interest rate"],
  "vox.alte.tipuri.limita": ["limite", "limits"],
  "vox.alte.tipuri.nota": ["note", "notes"],
  "vox.alte.tipuri.dobanda": ["dobânzi", "interest rates"],
  "vox.alte.tipuri.curs": ["cursuri valutare", "exchange rates"],
  "vox.din_data": ["din {data}", "since {data}"],
```

`web/src/styles/vox.css`, după regulile `.vox-kpi`:

```css
.vox-kpi .vox-frecvente { display: flex; flex-direction: column; gap: 2px; font-size: 12px; color: var(--muted) }
.vox-kpi .vox-frecvente b { font-family: var(--mono); font-size: 15px; font-weight: 500; color: var(--ink) }
.vox-kpi .vox-frecvente small { font-size: 11px; font-weight: 400; color: var(--muted) }
.vox-alte { margin-top: 4px }
```

- [ ] **Step 5: verificarea**

Run: `npm run typecheck 2>&1 | tail -3`
Expected: fără erori de tip; `paleta: theme.ts și global.css au aceleași culori`.

Run: `bash "$S/cu_server_8797.sh" python "$S/verifica_citire_ui.py" "$S/raspunsuri_citire.json" "$S" fisa`
Expected: `PROBLEME CONSOLĂ: niciuna`, `REZULTAT: OK`. Capturile `citire_bcr_*.png` și `citire_garanti_*.png` se deschid și se privesc: carduri pe monedă, rândurile pe frecvență, blocul „Alte valori găsite”, data sub valoare.

Run: `bash "$S/cu_server_8797.sh" python "$S/verifica_pastile_segment.py" "$S/raspunsuri_noi.json" "$S/raspunsuri_clasament.json" "$S/capturi_pastile"`
Expected: `REZULTAT: OK` (pastilele de segment, neschimbate).

- [ ] **Step 6: commit**

```bash
cat > "$S/mesaj_t8.txt" <<'EOF'
web: fișa Vox arată moneda dobânzilor, intervalul pe frecvență, valorile de alt tip separat și data

La Libra · depozit, trei carduri (lei, euro, monedă nespusă); la BCR · administrare cont PF, pe lună,
pe an și fără frecvență; la Garanti, „Nicio valoare de comision; am găsit doar limite (7)”. „Vezi
dovezile” de pe un card de monedă cere doar moneda lui.
EOF
git add shared/src/vox.ts shared/src/celula.ts web/src/components/Sertar.tsx web/src/pages/Vox.tsx web/src/i18n/dict/vox.ts web/src/styles/vox.css
git commit -q -F "$S/mesaj_t8.txt"
```

---

### Task 9: pagina — nota de monedă din clasament (`web/src/pages/vox/Clasament.tsx`)

**Files:**
- Modify: `web/src/pages/vox/Clasament.tsx`
- Modify: `web/src/i18n/dict/vox.ts`
- Script: `SCRATCH/verifica_citire_ui.py`, partea `clasament` (scrisă în Task 8)

**Interfaces:**
- Consumes: `RandClasament.alte_monede` (Task 8), `alte_monede` din răspuns (Task 3).

- [ ] **Step 1: verificarea care pică**

Run: `bash "$S/cu_server_8797.sh" python "$S/verifica_citire_ui.py" "$S/raspunsuri_citire.json" "$S" clasament`
Expected: `REZULTAT: 2 eșecuri` pe fiecare limbă (nota lipsește, 0 semne în tabel).

- [ ] **Step 2: implementarea**

Importul devine `import { EtichetaBanca, Pill } from '../../components/comune'`. În `Clasament`, după `const libra = …`:

```tsx
  // cifra rămâne a celulei din 2.2, dar unele celule au și dobânzi în altă monedă decât lei: la depozitul pe
  // 12 luni, ambele valori Raiffeisen (mip_merge, 08.10.2026); nota numește băncile
  const monede = [...new Set(c.blocuri.flatMap((b) => b.randuri.flatMap((r) => (r.alte_monede
    ? [`${m.nume[r.banca] ?? r.banca} (${t('vox.clasament.din', { n: r.alte_monede.n, din: r.alte_monede.din })})`]
    : []))))]
```

și, în JSX, imediat după paragraful cu `{libra}`:

```tsx
      {monede.length > 0 && (
        <p className="vox-nota vox-clas-monede"><span className="vox-punct" />{tn('vox.clasament.monede', monede.length, { banci: monede.join(', ') })}</p>
      )}
```

În `Bloc`, celula băncii devine:

```tsx
                <td>
                  <EtichetaBanca slug={r.banca} m={m} fisa tag />
                  {r.alte_monede && (
                    <span className="vox-clas-moneda">
                      <Pill tip="amb" title={t('vox.clasament.monede_tooltip', { n: r.alte_monede.n, din: r.alte_monede.din })}>
                        {t('vox.clasament.monede_pill')}
                      </Pill>
                    </span>
                  )}
                </td>
```

`web/src/i18n/dict/vox.ts`, lângă celelalte `vox.clasament.*`:

```ts
  "vox.clasament.din": ["{n} din {din}", "{n} of {din}"],
  "vox.clasament.monede_1": ["La o bancă, valorile includ dobânzi în altă monedă decât lei: {banci}.", "At one bank, the values include rates in a currency other than lei: {banci}."],
  "vox.clasament.monede_n": ["La {n} bănci, valorile includ dobânzi în altă monedă decât lei: {banci}.", "At {n} banks, the values include rates in a currency other than lei: {banci}."],
  "vox.clasament.monede_pill": ["și alte monede", "other currencies too"],
  "vox.clasament.monede_tooltip": ["{n} din {din} valori sunt în altă monedă decât lei", "{n} of {din} values are in a currency other than lei"],
```

- [ ] **Step 3: verificarea**

Run: `npm run typecheck 2>&1 | tail -2; bash "$S/cu_server_8797.sh" python "$S/verifica_citire_ui.py" "$S/raspunsuri_citire.json" "$S" fisa,clasament`
Expected: fără erori de tip; `PROBLEME CONSOLĂ: niciuna`, `REZULTAT: OK`. Captura `citire_clasament_*.png` se privește.

- [ ] **Step 4: commit**

```bash
cat > "$S/mesaj_t9.txt" <<'EOF'
web: clasamentul de dobânzi spune la ce bănci valorile includ și alte monede decât lei

La depozitul pe 12 luni: Raiffeisen (2 din 2), Libra (1 din 11), Vista (1 din 35); cifrele rămân ale
paginii 2.2 (mip_merge, 08.10.2026).
EOF
git add web/src/pages/vox/Clasament.tsx web/src/i18n/dict/vox.ts && git commit -q -F "$S/mesaj_t9.txt"
```

---

### Task 10: pagina — butoanele fără model

**Files:**
- Modify: `web/src/api/vox.ts` (`trimiteButonul`)
- Modify: `web/src/pages/Vox.tsx` (`Mesaj.buton`, `ruleaza`, `trimite`, `apasa`, bula turei, conversațiile redeschise, `Raspuns`: butoanele și subsolul)
- Modify: `web/src/i18n/dict/vox.ts`, `web/src/styles/vox.css`
- Script: `SCRATCH/verifica_citire_ui.py`, partea `butoane`

**Interfaces:**
- Consumes: `Buton`, `RaspunsIntrebare.butoane` / `buton` / `model: string | null` (Task 8); `POST /api/vox` cu `buton` (Task 5).

- [ ] **Step 1: verificarea care pică**

Run: `bash "$S/cu_server_8797.sh" python "$S/verifica_citire_ui.py" "$S/raspunsuri_citire.json" "$S" butoane`
Expected: `REZULTAT: 2 eșecuri` (`[ro] butoanele: []`, `[en] butoanele: []`); conversațiile vechi trec.

- [ ] **Step 2: cererea**

`web/src/api/vox.ts`: `type Buton` intră în importul din `@mcc/shared`, iar după `trimiteIntrebarea`:

```ts
/** Un buton de sub răspuns: serverul aplică butonul pe `anterior` fără model, deci tura costă 0. */
export function trimiteButonul(buton: Buton, anterior: Interpretare, conversatie: string | null, token: string) {
  return apiPostValidat('/api/vox', { buton, anterior, conversatie }, token, RaspunsVox)
}
```

- [ ] **Step 3: pagina**

`web/src/pages/Vox.tsx`:
- `trimiteButonul` intră în importul din `../api/vox`; `Buton` și `RaspunsVox` în importul de tipuri din `@mcc/shared`.
- `interface Mesaj` primește `buton?: Buton`.
- Conversația redeschisă: `setMesaje(conv.ture.map((x, i) => ({ id: i + 1, intrebare: x.intrebare, data: x.data, raspuns: x.raspuns, buton: x.raspuns.buton })))`.
- `trimite` se înlocuiește cu:

```tsx
  // o întrebare și un buton trec prin același drum: tura apare imediat, răspunsul vine la ea, iar un token
  // vechi (server repornit) se ia din nou
  async function ruleaza(tura: { intrebare: string; buton?: Buton }, cere: () => Promise<RaspunsVox>) {
    if (seTrimite || seIncarca || !st.activ) return
    const id = Date.now()
    setLipsa(false)
    setMesaje((x) => [...x, { id, intrebare: tura.intrebare, data: new Date().toISOString(), buton: tura.buton }])
    setSeTrimite(true)
    try {
      const r = await cere()
      // între timp s-a deschis altă conversație: răspunsul e în fișierul lui, lista îl arată
      if (afisata.current !== c) return
      setMesaje((x) => x.map((y) => (y.id === id ? { ...y, raspuns: r } : y)))
      if (!tura.buton) setText('')
      if (r.conversatie && r.conversatie !== c) {
        creata.current = r.conversatie
        mergi({ c: r.conversatie })
      }
    } catch (e) {
      if (afisata.current !== c) return
      const mesaj = (e as Error).message
      const afisat = mesaj === SERVER_OPRIT ? t('comun.server_oprit') : deLaServer(mesaj, lang)
      setMesaje((x) => x.map((y) => (y.id === id ? { ...y, eroare: afisat } : y)))
      // serverul repornit are alt token: îl ia din nou, întrebarea rămâne în câmp
      if (mesaj.includes('token')) void stare.refetch()
    } finally {
      setSeTrimite(false)
      void qc.invalidateQueries({ queryKey: CHEIE_CONVERSATII })
    }
  }

  async function trimite(intrebare: string) {
    const q = intrebare.trim()
    if (!q) return
    // „și la BRD?” continuă ultimul răspuns reușit (căutare sau clasament, inclusiv unul dat de un buton),
    // nu o clarificare sau o eroare
    const anterior = [...mesaje].reverse().find((x) => ['cautare', 'clasament'].includes(x.raspuns?.interpretare.tip ?? ''))?.raspuns?.interpretare ?? null
    await ruleaza({ intrebare: q }, () => trimiteIntrebarea(q, anterior, c, st.token ?? ''))
  }

  // butonul pornește de la interpretarea răspunsului sub care stă, nu de la ultimul răspuns
  const apasa = (buton: Buton, interp: Interpretare) =>
    void ruleaza({ intrebare: t(`vox.buton.${buton}`), buton }, () => trimiteButonul(buton, interp, c, st.token ?? ''))
```

- Bula turei: `<p className="vox-q">{x.buton ? t(`vox.buton.${x.buton}`) : x.intrebare}{x.buton && <span className="vox-fara-model">{t('vox.fara_model')}</span>}</p>`.
- `<Raspuns … />` primește `onButon={apasa}`.
- `Raspuns`: semnătura primește `onButon: (b: Buton, i: Interpretare) => void`; subsolul devine

```tsx
  const subsol = (
    <span className="vox-meta">
      {r.model === null
        ? t('vox.subsol_fara_model')
        : t('vox.subsol', {
          model: r.model,
          tokeni: num(tk.intrare + tk.citire_cache + tk.scriere_cache + tk.iesire, locale, 0),
          cost: r.cost_usd === null ? t('vox.cost_necunoscut') : dolari(r.cost_usd, locale),
        })}
    </span>
  )
  const butoane = r.butoane?.length
    ? (
      <div className="vox-butoane">
        {r.butoane.map((b) => (
          <button key={b} type="button" className="vox-link" disabled={!poate} onClick={() => onButon(b, i)}>{t(`vox.buton.${b}`)}</button>
        ))}
      </div>
    )
    : null
```

  iar în cele două `article.vox-card` (clasament și căutare), `{butoane}` stă imediat înaintea `<div className="vox-card-jos">`.

`web/src/i18n/dict/vox.ts`:

```ts
  "vox.buton.firme": ["Pentru firme", "For businesses"],
  "vox.buton.pf": ["Pentru persoane fizice", "For individuals"],
  "vox.buton.libra": ["Compară cu Libra", "Compare with Libra"],
  "vox.fara_model": ["fără model", "no model call"],
  "vox.subsol_fara_model": ["fără model · gratuit", "no model call · free"],
```

`web/src/styles/vox.css`:

```css
.vox-butoane { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 12px }
.vox-butoane .vox-link { font-size: 13px }
.vox-fara-model { display: block; margin-top: 3px; font-family: var(--mono); font-size: 10.5px; color: var(--muted) }
```

- [ ] **Step 4: verificarea**

Run: `npm run typecheck 2>&1 | tail -2; bash "$S/cu_server_8797.sh" python "$S/verifica_citire_ui.py" "$S/raspunsuri_citire.json" "$S" fisa,clasament,butoane`
Expected: fără erori de tip; `PROBLEME CONSOLĂ: niciuna`, `REZULTAT: OK` (inclusiv cele trei conversații vechi, fără butoane). Captura `citire_butoane_*.png` se privește.

Run: `bash "$S/cu_server_8797.sh" python "$S/verifica_clasament_ui.py" "$S/raspunsuri_clasament.json" "$S"`
Expected: verificările clasamentelor din 07.10 trec, `PROBLEME CONSOLĂ: niciuna`.

- [ ] **Step 5: commit**

```bash
cat > "$S/mesaj_t10.txt" <<'EOF'
web: butoanele de sub un răspuns Vox („Pentru firme”, „Compară cu Libra”) continuă fără model

Tura apare cu eticheta butonului și nota „fără model”; o întrebare scrisă după ea continuă interpretarea
butonului. Butonul și întrebarea trec prin aceeași funcție, deci un token vechi se reia la fel.
EOF
git add web/src/api/vox.ts web/src/pages/Vox.tsx web/src/i18n/dict/vox.ts web/src/styles/vox.css
git commit -q -F "$S/mesaj_t10.txt"
```

---

### Task 11: evaluarea și testul cap-coadă cu modelul real (plătite)

**Files:**
- Script: `SCRATCH/e2e_citire.py` (nou)

**Interfaces:**
- Consumes: tot ce e mai sus. Costurile intră în registru (`Task 11: cost …`).

- [ ] **Step 1: evaluarea (~$0,11)**

Run: `PYTHONIOENCODING=utf-8 python app/eval_vox.py --da > "$S/eval_citire.log" 2>&1; grep -E "✗|primit:|corecte" "$S/eval_citire.log"`
Expected: `44/44 corecte` și costul (~$0,10–0,11). O greșeală nouă se analizează înainte de o a doua rulare (cel mult 3 rulări).

- [ ] **Step 2: testul cap-coadă (~$0,03–0,04)**

`SCRATCH/e2e_citire.py`:

```python
"""Cap-coadă cu modelul real și baza reală (mip_merge), fără HTTP: cele trei întrebări din conversația din
08.10.2026 care se citeau greșit, clasamentul pe 12 luni și un buton. Jurnalul într-un dosar temporar, deci
nimic în loguri/vox/. Costă ~$0,03–0,04: prima întrebare scrie cache-ul de o oră."""
import os, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
RAD = r"C:\Users\nicolae.cherascu\Desktop\Market-Intelligence-Platform"
os.chdir(RAD); sys.path.insert(0, os.path.join(RAD, "app"))
import server, vox

v = vox.Vox(context=server._context_vox, cauta=server._cauta_vox, stare_banca=server._stare_banca_vox,
            clasament=server._clasament_vox, stare_banci=server._stare_banci_vox,
            dir_jurnal=tempfile.mkdtemp(prefix="e2e_citire_"))
total, conv, rez = 0.0, None, {}
for q in ("Ce dobândă are Libra la depozitul pe 12 luni?", "Cât costă administrarea contului la BCR?",
          "Cât costă schimbarea PIN-ului la Garanti?", "Cine dă cea mai mare dobândă la depozitul pe 12 luni?"):
    d = v.intreaba(q, None, conv)
    conv, rez[q] = d["conversatie"], d
    total += d["cost_usd"] or 0
    print(f"{q}\n   tokeni {d['tokeni']} · ${d['cost_usd']:.4f} · butoane {d['butoane']}")
    for rb in d["raspunsuri"]:
        print("   ", rb["banca"], [(g["segment"], g["unitate"], g.get("moneda"), g["n"], len(g.get("frecvente") or []))
                                    for g in rb["rezumat"]][:5], "| alte:", [(g["categorie"], g["n"]) for g in rb["alte"]])
    c = d["clasament"]
    if c and c.get("blocuri"):
        print("    alte monede:", [(b["tip"], r["banca"], r["alte_monede"]) for b in c["blocuri"]
                                   for r in b["randuri"] if r.get("alte_monede")])
f = v.continua(rez["Cât costă administrarea contului la BCR?"]["interpretare"], "firme", conv)
print("buton firme:", f["interpretare"]["segment"], f["model"], f["cost_usd"])
prima, a_doua = (rez[q]["tokeni"] for q in list(rez)[:2])
print(f"cache: prima scrie {prima['scriere_cache']}, a doua citește {a_doua['citire_cache']}")
print(f"cost total: ${total:.4f}")
```

Run: `PYTHONIOENCODING=utf-8 python "$S/e2e_citire.py"`
Expected: interpretările corecte (Libra · `nominala` · `depozite` · `12`; BCR · `administrare_cont`; Garanti · `schimbare_pin`; clasament `nominala` · `depozite` · `12`); aceleași carduri ca în Task 7; butonul cu `pj`, `None`, `0.0`; prima întrebare scrie ~12.800 de tokeni în cache, a doua îi citește; costul total ~$0,03–0,04.

(Fără commit.)

---

### Task 12: documentația și verificarea întregului

**Files:**
- Modify: `README.md` (secțiunea Vox), `.serena/memories/cod/harta.md`, `.serena/memories/stare/ultima_actualizare.md`

- [ ] **Step 1: README**

În secțiunea Vox, linia cu cache-ul („Prima întrebare îl scrie: $0,0147 … cache-ul ține 5 minute de la ultima întrebare.”) se înlocuiește cu cifrele măsurate în Task 11 („promptul stă în cache o oră, din 08.10.2026: prima întrebare îl scrie, $… ; apoi $… pe întrebare; în conversația din 08.10.2026, cu 5 minute, 3 din 18 întrebări rescriseseră promptul”). După paragraful „**Clasamente.**” se adaugă:

```markdown
- **Fișa citește ce e în date** (08.10.2026). La dobânzi, câte un card pe monedă, din coloana `valuta`
  (fără ghicit din text; gol = „monedă nespusă”): Libra · depozit are 4,75% în lei, 1,95% în euro și 9
  valori fără monedă. La comisioanele cu mai multe frecvențe, intervalul se arată pe frecvență (BCR ·
  administrare cont PF: pe lună 0–100 lei, pe an 0–1.200, fără frecvență 0–100). Notele, limitele și
  cursurile stau separat, la „Alte valori găsite” (Garanti · schimbarea PIN-ului: doar limite
  contactless). Fiecare rând arată data intrării în vigoare, când sursa o are (69% din valori).
  Clasamentele de dobânzi păstrează cifrele din 2.2 și spun la ce bănci valorile includ și alte monede.
- **Butoane fără model.** Sub răspuns: „Pentru firme” / „Pentru persoane fizice” (la comisioane) și
  „Compară cu Libra” (la căutare). Serverul aplică butonul pe interpretarea răspunsului (`vox.din_buton`),
  deci tura costă 0 și nu poate fi înțeleasă greșit; `POST /api/vox` cu `buton` + `anterior`.
```

Linia despre evaluare primește costul măsurat în Task 11 („44 din 44, $…, cu cache-ul de o oră”).

- [ ] **Step 2: harta Serena**

`.serena/memories/cod/harta.md`, în paragraful `app/vox.py`: după „Răspunsul pe bancă (`Vox._raspuns`): …” se adaugă „`separa` desparte prețul (comision sau o categorie 2.2) de note, limite, cursuri (`alte`, rânduri cu `tip_alt`); `rezuma` grupează și pe monedă la dobânzi (`valuta` → `MONEDE`) și dă `frecvente` la comisioanele cu mai multe frecvențe; `celula` dă `data_vigoare` și acceptă `valuta`; la clasamentele de dobânzi, `_alte_monede_rate` pune `alte_monede` pe bancă. Butoanele: `vox.butoane` (ce are un răspuns), `vox.din_buton`, `Vox.continua` (fără model, cost 0), `POST /api/vox` cu `buton` + `anterior`; `_raspunde` e drumul comun întrebare / buton. Cache-ul promptului: `ttl: \"1h\"`, cost cu `preturi.cost(..., scriere_cache_1h=)`.” Numărul întrebărilor din evaluare rămâne 44.

`.serena/memories/stare/ultima_actualizare.md`: commit-ul de referință = ultimul commit de cod (Task 10), cu descrierea „fișa Vox citește corect, butoane fără model, cache de o oră”.

- [ ] **Step 3: verificarea întregului**

Run:
```bash
for t in app/test_vox.py app/test_celula.py app/test_rulari.py app/test_autentificare.py app/test_server_autentificare.py app/test_pdf_proxy.py; do
  PYTHONIOENCODING=utf-8 python "$t" > "$S/final_$(basename "$t" .py).log" 2>&1; echo "$t -> $? $(grep -E '^(Ran|OK|FAILED)' "$S/final_$(basename "$t" .py).log" | tr '\n' ' ')"
done
npm run typecheck 2>&1 | tail -2
npm -w web exec -- vite build --outDir "$S/dist_verif" --emptyOutDir 2>&1 | grep -E "built in|error"
bash "$S/cu_server_8797.sh" sh -c "MIP_URL=http://localhost:8797 PYTHONIOENCODING=utf-8 python app/verifica_pagini.py | tail -2"
bash "$S/cu_server_8797.sh" python "$S/verifica_citire_ui.py" "$S/raspunsuri_citire.json" "$S" fisa,clasament,butoane
bash "$S/cu_server_8797.sh" python "$S/verifica_pastile_segment.py" "$S/raspunsuri_noi.json" "$S/raspunsuri_clasament.json" "$S/capturi_pastile"
git status --short | grep -v "^??"
```
Expected: toate suitele `OK` (`test_vox` 127, `test_celula` 22, `test_rulari` 25, `test_autentificare` 66, `test_server_autentificare` 25, `test_pdf_proxy` 9); typecheck și build fără erori; `0 pagini cu erori din 12`; ambele scripturi Playwright `REZULTAT: OK`; niciun fișier urmărit nemodificat.

- [ ] **Step 4: commit**

```bash
cat > "$S/mesaj_t12.txt" <<'EOF'
docs, serena: fișa Vox care citește corect, butoanele fără model și cache-ul de o oră
EOF
git add README.md .serena/memories/cod/harta.md .serena/memories/stare/ultima_actualizare.md && git commit -q -F "$S/mesaj_t12.txt"
```
