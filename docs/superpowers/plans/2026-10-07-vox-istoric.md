# Vox: istoricul conversațiilor — planul de implementare

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** conversațiile Vox se păstrează pe laptop, se redeschid gratuit, se continuă, se caută, se redenumesc și se șterg din coloana „Conversații” a paginii Vox.

**Architecture:** `app/vox.py` primește clasa `Istoric` (un fișier JSONL pe conversație în `loguri/vox/conversatii/`, doar adăugare), `Vox.intreaba` salvează fiecare tură, iar `app/server.py` expune lista, citirea, redenumirea și ștergerea pe `/api/vox/conversatii…`, cu aceleași verificări ca `/api/vox`. Interfața citește lista cu TanStack Query, conversația deschisă stă în adresă (`#/vox?c=<id>`), iar coloana e o componentă separată, `web/src/pages/vox/Conversatii.tsx`.

**Tech Stack:** Python 3.12 (`http.server`, `unittest`), React 18 + Vite 6 + AntD 5 + TanStack Query + Zod (`@mcc/shared`), Playwright (Edge) pentru capturi.

**Spec:** `docs/superpowers/specs/2026-10-07-vox-istoric-design.md`

## Global Constraints

- Serverul nu scrie în bază; conversațiile sunt doar fișiere în `loguri/vox/conversatii/` (deja în `.gitignore`).
- Niciun apel plătit în dezvoltare: testele folosesc `ClientFals`, capturile `page.route`. `python app/eval_vox.py --da` nu se rulează (interpretarea nu se schimbă).
- Serverele utilizatorului (:8765, :5173) nu se opresc și nu se repornesc; `npm run build` nu se rulează (rescrie `web/dist`, servit de :8765). Servere temporare doar pe alte porturi.
- Identificatori în română, fără diacritice; textele pentru utilizator prin `t` / `tn` ca perechi `[română, engleză]`; mesajele românești ale serverului identice în `server.vox.*`.
- Niciun pachet nou (AntD, @ant-design/icons, TanStack Query, Zod sunt deja în stack).
- Comentariile spun de ce, cu cifra măsurată; commit-uri în română, „zonă: ce și de ce”, fără `Co-Authored-By`.
- `id`: `^[0-9a-f]{16}$`; titlu: cel mult 120 de caractere; mesaje: „Conversația nu mai există.”, „Titlul are peste 120 de caractere.”, „Titlul nu e valid.”

## Review Focus

- Trecerea la ora de iarnă (25.10.2026): lista se ordonează după ora reală, nu după text (`03:10+02:00` e după `03:30+03:00`) — test în Task 1.
- O scriere întreruptă lasă un rând JSON neterminat: se sare rândul, nu toată conversația — test în Task 1.
- Clic pe altă conversație cât o întrebare așteaptă răspunsul: coloana e blocată, răspunsul nu ajunge în conversația greșită — verificare în Task 5 (pasul de capturi).
- „Înapoi” în browser spre o conversație ștearsă: 404 → nota „Conversația din adresă nu mai există…”, chat gol, `c` scos din adresă — verificare în Task 5.
- Căutare cu majuscule și fără diacritice („BANCA”, „vamala”) găsește „bancă”, „vamale” — verificare în Task 5.

---

### Task 1: `Istoric` — conversațiile ca fișiere

**Files:**
- Modify: `app/vox.py` (constante după `CHEI`, excepția `ConversatieLipsa` după `EroareModel`, `_moment` și clasa `Istoric` înainte de `class Vox`)
- Test: `app/test_vox.py` (clasa nouă `IstoricConversatii`, după `class Rezumat`)

**Interfaces:**
- Produces: `vox.ID_CONVERSATIE`, `vox.TITLU_MAX = 120`, `vox.CONVERSATIE_LIPSA`, `class vox.ConversatieLipsa(Exception)`, `class vox.Istoric(dir)` cu `valid(id) -> bool` (static), `id_nou() -> str` (static), `exista(id) -> bool`, `adauga(id, intrebare, raspuns, data=None)`, `citeste(id) -> dict | None` (`{id, titlu, redenumita, ture: [{data, intrebare, raspuns}]}`), `lista() -> list[dict]` (`{id, titlu, redenumita, intrebari, texte, inceputa, ultima, cost_usd}`), `redenumeste(id, titlu) -> {titlu, redenumita}` (aruncă `Respins` / `ConversatieLipsa`), `sterge(id) -> bool`.

- [ ] **Step 1: testele care pică**

În `app/test_vox.py`, după `class Rezumat`:

```python
class IstoricConversatii(unittest.TestCase):
    def setUp(self):
        self.rad = tempfile.mkdtemp(prefix="vox_ist_")
        self.ist = vox.Istoric(os.path.join(self.rad, "conversatii"))

    def raspuns(self, cost=0.0015):
        return {"interpretare": interp(), "ignorate": [], "raspunsuri": [], "model": "claude-haiku-4-5",
                "tokeni": {"intrare": 1, "iesire": 1, "citire_cache": 0, "scriere_cache": 0}, "cost_usd": cost}

    def test_lista_goala_fara_dosar(self):
        self.assertEqual(self.ist.lista(), [])

    def test_adauga_citeste_lista(self):
        a = self.ist.id_nou()
        self.assertTrue(vox.Istoric.valid(a))
        self.ist.adauga(a, "Cât costă administrarea contului la BCR?", self.raspuns(0.0147))
        self.ist.adauga(a, "și la BRD?", self.raspuns(0.0015))
        c = self.ist.citeste(a)
        self.assertEqual((c["titlu"], c["redenumita"], [t["intrebare"] for t in c["ture"]]),
                         ("Cât costă administrarea contului la BCR?", False,
                          ["Cât costă administrarea contului la BCR?", "și la BRD?"]))
        self.assertEqual(c["ture"][1]["raspuns"]["cost_usd"], 0.0015)
        (rez,) = self.ist.lista()
        self.assertEqual((rez["id"], rez["intrebari"], rez["texte"]), (a, 2, [t["intrebare"] for t in c["ture"]]))
        self.assertAlmostEqual(rez["cost_usd"], 0.0162)
        self.assertEqual((rez["inceputa"], rez["ultima"]), (c["ture"][0]["data"], c["ture"][1]["data"]))

    def test_lista_dupa_ultima_intrebare_si_ora_de_iarna(self):
        """Ordinea e după ora reală, nu după text: la ora de iarnă (25.10.2026) „03:10+02:00” vine
        după „03:30+03:00”, deși ca text e înainte."""
        a, b = self.ist.id_nou(), self.ist.id_nou()
        self.ist.adauga(a, "A?", self.raspuns(), data="2026-10-25T03:30:00+03:00")
        self.ist.adauga(b, "B?", self.raspuns(), data="2026-10-25T03:10:00+02:00")
        self.assertEqual([r["id"] for r in self.ist.lista()], [b, a])

    def test_redenumire(self):
        a, b = self.ist.id_nou(), self.ist.id_nou()
        self.ist.adauga(a, "Cât costă administrarea contului la BCR?", self.raspuns(), data="2026-10-07T12:37:00+03:00")
        self.ist.adauga(b, "Altă întrebare?", self.raspuns(), data="2026-10-07T12:40:00+03:00")
        self.assertEqual(self.ist.redenumeste(a, "  Administrare cont BCR "),
                         {"titlu": "Administrare cont BCR", "redenumita": True})
        self.ist.redenumeste(a, "Comisioane BCR")
        lista = self.ist.lista()
        self.assertEqual([r["id"] for r in lista], [b, a])        # redenumirea nu mută conversația
        self.assertEqual((lista[1]["titlu"], lista[1]["redenumita"]), ("Comisioane BCR", True))
        self.assertEqual(self.ist.redenumeste(a, "   "),
                         {"titlu": "Cât costă administrarea contului la BCR?", "redenumita": False})
        for rau in ("x" * 121, 42):
            with self.assertRaises(vox.Respins):
                self.ist.redenumeste(a, rau)
        with self.assertRaises(vox.ConversatieLipsa):
            self.ist.redenumeste(self.ist.id_nou(), "titlu")

    def test_sterge(self):
        a = self.ist.id_nou()
        self.ist.adauga(a, "A?", self.raspuns())
        self.ist.lista()
        self.assertTrue(self.ist.sterge(a))
        self.assertEqual((self.ist.citeste(a), self.ist.lista(), self.ist.sterge(a)), (None, [], False))

    def test_id_invalid_nu_atinge_discul(self):
        afara = os.path.join(self.rad, "secret.jsonl")
        with open(afara, "w", encoding="utf-8") as f:
            f.write(json.dumps({"data": "2026-10-07T12:00:00+03:00", "intrebare": "secret", "raspuns": None}) + "\n")
        for rau in ("../secret", "..\\secret", "ABCDEF0123456789", "abc", "0123456789abcdef0", "", None, 7):
            self.assertIsNone(self.ist.citeste(rau), rau)
            self.assertFalse(self.ist.sterge(rau), rau)
            self.assertFalse(self.ist.exista(rau), rau)
            with self.assertRaises(vox.ConversatieLipsa):
                self.ist.adauga(rau, "x", self.raspuns())
        self.assertTrue(os.path.exists(afara))

    def test_rand_stricat_sarit(self):
        """O scriere întreruptă lasă un rând neterminat: se sare el, nu toată conversația."""
        a = self.ist.id_nou()
        self.ist.adauga(a, "A?", self.raspuns())
        with open(os.path.join(self.ist.dir, a + ".jsonl"), "a", encoding="utf-8") as f:
            f.write('{"data": "2026-10-07T12:00:00+03:00", "intreb')
        self.assertEqual([t["intrebare"] for t in self.ist.citeste(a)["ture"]], ["A?"])
        self.assertEqual(self.ist.lista()[0]["intrebari"], 1)

    def test_lista_tine_minte_rezumatul(self):
        """Lista se cere după fiecare întrebare: un fișier neschimbat nu se recitește."""
        a = self.ist.id_nou()
        self.ist.adauga(a, "A?", self.raspuns())
        self.ist.lista()
        citiri, citeste = [], self.ist.citeste
        self.ist.citeste = lambda id: citiri.append(id) or citeste(id)
        self.ist.lista()
        self.assertEqual(citiri, [])
        self.ist.adauga(a, "B?", self.raspuns())
        self.assertEqual(self.ist.lista()[0]["intrebari"], 2)
        self.assertEqual(citiri, [a])
```

- [ ] **Step 2: rulează, trebuie să pice**

Run: `.venv\Scripts\python.exe app/test_vox.py IstoricConversatii`
Expected: ERROR pe toate, `AttributeError: module 'vox' has no attribute 'Istoric'`.

- [ ] **Step 3: implementarea**

În `app/vox.py`, după `CHEI = (...)`:

```python
# Istoricul conversațiilor (coloana „Conversații” din pagina Vox): fișiere pe laptop, nu în bază
ID_CONVERSATIE = re.compile(r"[0-9a-f]{16}")
TITLU_MAX = 120
CONVERSATIE_LIPSA = "Conversația nu mai există."
```

După `class EroareModel`:

```python
class ConversatieLipsa(Exception):
    """Conversația cerută nu există (404): ștearsă sau un id greșit în adresă."""
```

Înainte de `class Vox`:

```python
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
            with open(self._cale(id), encoding="utf-8") as f:
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
```

- [ ] **Step 4: rulează, trebuie să treacă**

Run: `.venv\Scripts\python.exe app/test_vox.py IstoricConversatii`
Expected: `Ran 9 tests … OK`. Apoi toată suita: `.venv\Scripts\python.exe app/test_vox.py` → OK.

- [ ] **Step 5: commit**

```bash
git add app/vox.py app/test_vox.py
git commit -m "app: Istoric, conversațiile Vox ca fișiere JSONL pe laptop (doar adăugare, id verificat, rezumat ținut minte)"
```

### Task 2: `Vox.intreaba` salvează tura și continuă o conversație

**Files:**
- Modify: `app/vox.py` (`Vox.__init__`, `Vox.intreaba`)
- Modify: `app/server.py` (`Handler._post_vox`)
- Test: `app/test_vox.py` (clasa `Intrebari`; `test_jurnal`; clasa `Http`)

**Interfaces:**
- Consumes: `vox.Istoric`, `vox.CONVERSATIE_LIPSA` (Task 1).
- Produces: `Vox(..., dir_jurnal=DIR_JURNAL, dir_conversatii=None)` cu `self.istoric`; `Vox.intreaba(intrebare, anterior=None, conversatie=None)` → răspunsul de azi plus `conversatie: str | None`; `POST /api/vox` acceptă `conversatie` în corp; rândul din jurnal are `conversatie`.

- [ ] **Step 1: testele care pică**

În `class Intrebari`, după `test_stare_si_token`:

```python
    def test_conversatie_noua_si_continuata(self):
        q = self.fa(ClientFals(interp()))
        d = q.intreaba("Cât costă administrarea contului la BCR?")
        c = d["conversatie"]
        self.assertTrue(vox.Istoric.valid(c))
        q._client = ClientFals(interp(banci=["brd"]))
        d2 = q.intreaba("și la BRD?", d["interpretare"], c)
        self.assertEqual(d2["conversatie"], c)
        conv = q.istoric.citeste(c)
        self.assertEqual([t["intrebare"] for t in conv["ture"]],
                         ["Cât costă administrarea contului la BCR?", "și la BRD?"])
        self.assertEqual(conv["ture"][1]["raspuns"]["raspunsuri"][0]["banca"], "brd")
        self.assertNotIn("conversatie", conv["ture"][1]["raspuns"])
        self.assertEqual(len(q.istoric.lista()), 1)

    def test_conversatie_stearsa_nu_se_plateste(self):
        """Ștearsă în alt tab sau id greșit: refuzul vine înainte de model, deci nimic plătit."""
        c = ClientFals(interp())
        q = self.fa(c)
        for rau in (q.istoric.id_nou(), "../x", 42, ""):
            with self.assertRaises(vox.Respins) as e:
                q.intreaba("și la BRD?", None, rau)
            self.assertEqual(str(e.exception), "Conversația nu mai există.")
        self.assertEqual(c.cereri, [])

    def test_eroarea_modelului_nu_intra_in_conversatie(self):
        import anthropic
        q = self.fa(ClientFals(exceptie=fara_init(anthropic.APIConnectionError)))
        with self.assertRaises(vox.EroareModel):
            q.intreaba("BCR?")
        self.assertEqual(q.istoric.lista(), [])

    def test_fara_disc_raspunsul_vine_oricum(self):
        q = self.fa(ClientFals(interp()))

        def cade(*a, **k):
            raise OSError("disc plin")
        q.istoric.adauga = cade
        d = q.intreaba("BCR?")
        self.assertEqual((d["conversatie"], d["raspunsuri"][0]["banca"]), (None, "bcr"))

    def test_jurnalul_leaga_intrebarea_de_conversatie(self):
        d = self.fa(ClientFals(interp())).intreaba("BCR?")
        (jurnal,) = [f for f in os.listdir(self.dir) if f.endswith(".jsonl")]
        with open(os.path.join(self.dir, jurnal), encoding="utf-8") as f:
            self.assertEqual(json.loads(f.readline())["conversatie"], d["conversatie"])
```

În `test_jurnal`, linia `fisiere = os.listdir(self.dir)` devine (conversațiile stau acum în subdosarul `conversatii` al jurnalului):

```python
        fisiere = [f for f in os.listdir(self.dir) if f.endswith(".jsonl")]
```

În `class Http`, după `test_eroare_model_502`:

```python
    def test_post_salveaza_si_continua(self):
        ok = {"X-MIP-Token": self.token()}
        cod, d = self.cere("POST", "/api/vox", {"intrebare": "BCR?"}, ok)
        self.assertEqual(cod, 200)
        c = d["conversatie"]
        cod, d2 = self.cere("POST", "/api/vox",
                            {"intrebare": "și la BRD?", "anterior": d["interpretare"], "conversatie": c}, ok)
        self.assertEqual((cod, d2["conversatie"]), (200, c))
        self.assertEqual([t["intrebare"] for t in self.server_mod.VOX.istoric.citeste(c)["ture"]],
                         ["BCR?", "și la BRD?"])
        n = len(self.client.cereri)
        cod, d3 = self.cere("POST", "/api/vox", {"intrebare": "BCR?", "conversatie": "0" * 16}, ok)
        self.assertEqual((cod, d3["eroare"], len(self.client.cereri)), (400, "Conversația nu mai există.", n))
```

- [ ] **Step 2: rulează, trebuie să pice**

Run: `.venv\Scripts\python.exe app/test_vox.py Intrebari Http`
Expected: `AttributeError: 'Vox' object has no attribute 'istoric'` / `TypeError: … unexpected argument` / `KeyError: 'conversatie'`.

- [ ] **Step 3: implementarea**

`Vox.__init__` primește `dir_conversatii=None` și, după `self.dir = dir_jurnal`:

```python
        # lângă jurnal: în teste și la evaluare jurnalul e într-un dosar temporar, deci și conversațiile
        self.istoric = Istoric(dir_conversatii or os.path.join(dir_jurnal, "conversatii"))
```

`Vox.intreaba`:

```python
    def intreaba(self, intrebare, anterior=None, conversatie=None):
        intrebare = verifica_intrebarea(intrebare)
        anterior = verifica_anterior(anterior)
        if conversatie is not None and not self.istoric.exista(conversatie):
            # înainte de model: o conversație ștearsă în alt tab nu se mai plătește
            raise Respins(CONVERSATIE_LIPSA)
        ctx, sistem, sch = self._context()
        m = model()
        rand = {"data": _acum(), "intrebare": intrebare, "model": m, "conversatie": conversatie}
        # … neschimbat până la rand["randuri"] = …
        rand["randuri"] = {r["banca"]: r["total"] for r in raspunsuri}
        rezultat = {"interpretare": interp, "ignorate": ignorate, "raspunsuri": raspunsuri,
                    "model": m, "tokeni": tokeni, "cost_usd": cost}
        id = conversatie or self.istoric.id_nou()
        try:
            self.istoric.adauga(id, intrebare, rezultat)
        except OSError:
            # disc plin sau fără drept de scriere: răspunsul se arată oricum, doar nu se păstrează
            id = None
        rand["conversatie"] = id
        self._jurnal(rand)
        return {**rezultat, "conversatie": id}
```

În `app/server.py`, `Handler._post_vox`:

```python
            self._json(200, VOX.intreaba(corp.get("intrebare"), corp.get("anterior"), corp.get("conversatie")))
```

- [ ] **Step 4: rulează, trebuie să treacă**

Run: `.venv\Scripts\python.exe app/test_vox.py` și `.venv\Scripts\python.exe app/test_rulari.py`
Expected: ambele OK.

- [ ] **Step 5: commit**

```bash
git add app/vox.py app/server.py app/test_vox.py
git commit -m "app: Vox salvează fiecare tură în conversația ei și o continuă; o conversație ștearsă e refuzată înainte de model"
```

### Task 3: rutele `/api/vox/conversatii…`

**Files:**
- Modify: `app/server.py` (`Handler._get_conversatii`, `Handler._post_conversatie`, `do_GET`, `do_POST`)
- Test: `app/test_vox.py` (clasa `Http`)

**Interfaces:**
- Consumes: `VOX.istoric` (Task 2), `vox.ConversatieLipsa`, `vox.Respins`, `vox.CONVERSATIE_LIPSA`.
- Produces: `GET /api/vox/conversatii` → listă; `GET /api/vox/conversatii/<id>` → conversație sau 404; `POST /api/vox/conversatii/<id>/redenumeste` `{titlu}` → `{titlu, redenumita}` / 400 / 404; `POST /api/vox/conversatii/<id>/sterge` `{}` → `{sters: true}` / 404.

- [ ] **Step 1: testele care pică**

În `class Http`:

```python
    def test_conversatii_lista_citire_redenumire_stergere(self):
        ok = {"X-MIP-Token": self.token()}
        c = self.cere("POST", "/api/vox", {"intrebare": "Cât costă administrarea contului la BCR?"}, ok)[1]["conversatie"]
        cod, lista = self.cere("GET", "/api/vox/conversatii")
        self.assertEqual(cod, 200)
        self.assertIn(c, [x["id"] for x in lista])
        cod, conv = self.cere("GET", f"/api/vox/conversatii/{c}")
        self.assertEqual((cod, conv["titlu"], len(conv["ture"])), (200, "Cât costă administrarea contului la BCR?", 1))
        cod, d = self.cere("POST", f"/api/vox/conversatii/{c}/redenumeste", {"titlu": "BCR, cont"}, ok)
        self.assertEqual((cod, d), (200, {"titlu": "BCR, cont", "redenumita": True}))
        cod, d = self.cere("POST", f"/api/vox/conversatii/{c}/redenumeste", {"titlu": "x" * 121}, ok)
        self.assertEqual((cod, d["eroare"]), (400, "Titlul are peste 120 de caractere."))
        cod, d = self.cere("POST", f"/api/vox/conversatii/{c}/sterge", {}, ok)
        self.assertEqual((cod, d), (200, {"sters": True}))
        self.assertEqual(self.cere("GET", f"/api/vox/conversatii/{c}")[0], 404)
        self.assertEqual(self.cere("POST", f"/api/vox/conversatii/{c}/sterge", {}, ok)[0], 404)
        self.assertEqual(self.cere("POST", f"/api/vox/conversatii/{c}/redenumeste", {"titlu": "y"}, ok)[0], 404)

    def test_conversatii_protejate(self):
        ok = {"X-MIP-Token": self.token()}
        c = self.cere("POST", "/api/vox", {"intrebare": "BCR?"}, ok)[1]["conversatie"]
        for antete, host in (({}, None), ({"X-MIP-Token": "gresit"}, None),
                             ({"X-MIP-Token": self.server_mod.RULARI.token}, None),
                             (dict(ok, Origin="http://evil.com"), None), (ok, f"evil.com:{self.port}")):
            for actiune, corp in (("sterge", {}), ("redenumeste", {"titlu": "x"})):
                cod, _ = self.cere("POST", f"/api/vox/conversatii/{c}/{actiune}", corp, antete, host)
                self.assertEqual(cod, 403, (antete, host, actiune))
        cod, _ = self.cere("POST", f"/api/vox/conversatii/{c}/sterge", None, dict(ok, **{"Content-Type": "text/plain"}))
        self.assertEqual(cod, 415)
        self.assertEqual(self.cere("GET", "/api/vox/conversatii", host=f"evil.com:{self.port}")[0], 403)
        self.assertEqual(self.cere("GET", f"/api/vox/conversatii/{c}", antete={"Origin": "http://evil.com"})[0], 403)
        self.assertEqual(self.cere("GET", f"/api/vox/conversatii/{c}")[0], 200)     # nimic șters

    def test_conversatii_id_invalid(self):
        ok = {"X-MIP-Token": self.token()}
        for cale in ("/api/vox/conversatii/..%2F..%2Fserver", "/api/vox/conversatii/../../app/server.py",
                     "/api/vox/conversatii/ABCDEF0123456789", "/api/vox/conversatii/"):
            self.assertEqual(self.cere("GET", cale)[0], 404, cale)
        self.assertEqual(self.cere("POST", "/api/vox/conversatii/../x/sterge", {}, ok)[0], 404)
        self.assertEqual(self.cere("POST", f"/api/vox/conversatii/{'0' * 16}/altceva", {}, ok)[0], 404)

    def test_conversatii_si_cu_vox_oprit(self):
        """Lista doar citește fișiere locale: merge și fără cheie (istoricul rămâne de citit)."""
        os.environ["MIP_PERMITE_VOX"] = "0"
        self.assertEqual(self.cere("GET", "/api/vox/conversatii")[0], 200)
```

- [ ] **Step 2: rulează, trebuie să pice**

Run: `.venv\Scripts\python.exe app/test_vox.py Http`
Expected: FAIL (404 de la `SimpleHTTPRequestHandler` sau 404 din `do_POST` în loc de 200/403).

- [ ] **Step 3: implementarea**

În `Handler`, după `_post_vox`:

```python
    def _get_conversatii(self, cale):
        """Lista și o conversație: doar citesc fișiere locale, deci merg și cu Vox oprit; tot cu
        Host/Origin, ca GET /api/vox (întrebările sunt ale utilizatorului)."""
        motiv = self._refuz_vox(cu_token=False)
        if motiv:
            self._json(403, {"eroare": motiv})
            return
        parti = cale.split("/")      # ["", "api", "vox", "conversatii", <id>]
        if len(parti) == 4:
            self._json(200, VOX.istoric.lista())
            return
        c = VOX.istoric.citeste(parti[4]) if len(parti) == 5 else None
        if c is None:
            self._json(404, {"eroare": vox.CONVERSATIE_LIPSA})
            return
        self._json(200, c)

    def _post_conversatie(self, cale):
        """Redenumirea și ștergerea: aceleași verificări ca întrebarea (token, Host/Origin, JSON)."""
        motiv = self._refuz_vox(cu_token=True)
        if motiv:
            self._json(403, {"eroare": motiv})
            return
        parti = cale.split("/")      # ["", "api", "vox", "conversatii", <id>, <acțiune>]
        if len(parti) != 6 or parti[5] not in ("redenumeste", "sterge"):
            self.send_error(404)
            return
        corp = self._corp_json(1024)
        if corp is None:
            return
        try:
            if parti[5] == "sterge":
                if not VOX.istoric.sterge(parti[4]):
                    raise vox.ConversatieLipsa(vox.CONVERSATIE_LIPSA)
                self._json(200, {"sters": True})
            else:
                self._json(200, VOX.istoric.redenumeste(parti[4], corp.get("titlu")))
        except vox.ConversatieLipsa as exc:
            self._json(404, {"eroare": str(exc)})
        except vox.Respins as exc:
            self._json(400, {"eroare": str(exc)})
        except Exception as exc:
            self._json(*_eroare_server(exc))
```

În `do_POST`, după blocul `if cale == "/api/vox":`:

```python
        if cale.startswith("/api/vox/conversatii/"):
            self._post_conversatie(cale)
            return
```

În `do_GET`, înainte de `if parsed.path == "/api/vox":`:

```python
        if parsed.path == "/api/vox/conversatii" or parsed.path.startswith("/api/vox/conversatii/"):
            self._get_conversatii(parsed.path)
            return
```

- [ ] **Step 4: rulează, trebuie să treacă**

Run: `.venv\Scripts\python.exe app/test_vox.py` și `.venv\Scripts\python.exe app/test_rulari.py`
Expected: ambele OK.

- [ ] **Step 5: commit**

```bash
git add app/server.py app/test_vox.py
git commit -m "app: rutele /api/vox/conversatii (listă, citire, redenumire, ștergere), cu verificările lui /api/vox"
```

### Task 4: schemele și cererile din interfață

**Files:**
- Modify: `shared/src/vox.ts`
- Modify: `web/src/api/vox.ts`
- Modify: `web/src/i18n/dict/vox.ts` (mesajele serverului)

**Interfaces:**
- Consumes: forma răspunsurilor din Task 2–3.
- Produces (`@mcc/shared`): `RaspunsVox`, `Tura`, `Conversatie`, `ConversatieRezumat`, `Redenumire`, `Stergere`. (`web/src/api/vox.ts`): `CHEIE_CONVERSATII`, `useConversatii()`, `citesteConversatia(id)`, `trimiteIntrebarea(intrebare, anterior, conversatie, token)`, `redenumesteConversatia(id, titlu, token)`, `stergeConversatia(id, token)`.

- [ ] **Step 1: schemele** (după `RaspunsIntrebare` în `shared/src/vox.ts`)

```ts
/** Răspunsul la POST /api/vox: ca cel salvat, plus conversația (null dacă n-a putut fi salvată). */
export const RaspunsVox = RaspunsIntrebare.extend({ conversatie: z.string().nullable() })
export type RaspunsVox = z.infer<typeof RaspunsVox>

/** O întrebare dintr-o conversație salvată (loguri/vox/conversatii/<id>.jsonl). */
export const Tura = z.object({ data: z.string(), intrebare: z.string(), raspuns: RaspunsIntrebare })
export type Tura = z.infer<typeof Tura>

export const Conversatie = z
  .object({ id: z.string(), titlu: z.string(), redenumita: z.boolean(), ture: z.array(Tura) })
  .passthrough()
export type Conversatie = z.infer<typeof Conversatie>

/** Un rând din coloana „Conversații”; `texte` = toate întrebările, pentru căutare. */
export const ConversatieRezumat = z
  .object({
    id: z.string(),
    titlu: z.string(),
    redenumita: z.boolean(),
    intrebari: z.number(),
    texte: z.array(z.string()),
    inceputa: z.string(),
    ultima: z.string(),
    cost_usd: z.number(),
  })
  .passthrough()
export type ConversatieRezumat = z.infer<typeof ConversatieRezumat>

export const Redenumire = z.object({ titlu: z.string(), redenumita: z.boolean() })
export const Stergere = z.object({ sters: z.literal(true) })
```

- [ ] **Step 2: cererile** (`web/src/api/vox.ts`, tot fișierul)

```ts
import { useQuery } from '@tanstack/react-query'
import { z } from 'zod'
import { Conversatie, ConversatieRezumat, RaspunsVox, Redenumire, Stergere, VoxStare, type Interpretare } from '@mcc/shared'
import { api, apiPostValidat } from './client'

/** Starea funcției (activă doar local, cu MIP_PERMITE_VOX=1 și cheia reală) și tokenul POST-ului. */
export function useStareVox() {
  return useQuery({ queryKey: ['vox'], queryFn: () => api('/api/vox', VoxStare) })
}

/** Lista se reîncarcă după o întrebare, o redenumire sau o ștergere. */
export const CHEIE_CONVERSATII = ['vox-conversatii']

/** Conversațiile salvate pe laptop: doar citește fișiere, nu cheamă modelul. */
export function useConversatii() {
  return useQuery({ queryKey: CHEIE_CONVERSATII, queryFn: () => api('/api/vox/conversatii', z.array(ConversatieRezumat)) })
}

export function citesteConversatia(id: string) {
  return api(`/api/vox/conversatii/${encodeURIComponent(id)}`, Conversatie)
}

/** O întrebare = un apel plătit la model: doar la clic, niciodată la randare; `conversatie` null începe una. */
export function trimiteIntrebarea(intrebare: string, anterior: Interpretare | null, conversatie: string | null, token: string) {
  return apiPostValidat('/api/vox', { intrebare, anterior, conversatie }, token, RaspunsVox)
}

export function redenumesteConversatia(id: string, titlu: string, token: string) {
  return apiPostValidat(`/api/vox/conversatii/${encodeURIComponent(id)}/redenumeste`, { titlu }, token, Redenumire)
}

export function stergeConversatia(id: string, token: string) {
  return apiPostValidat(`/api/vox/conversatii/${encodeURIComponent(id)}/sterge`, {}, token, Stergere)
}
```

În `web/src/pages/Vox.tsx`, apelul existent devine `trimiteIntrebarea(q, anterior, null, st.token ?? '')` (Task 5 îl leagă de conversație).

- [ ] **Step 3: mesajele serverului** (în `web/src/i18n/dict/vox.ts`, lângă `server.vox.*`)

```ts
  "server.vox.conversatie_lipsa": ["Conversația nu mai există.", "The conversation no longer exists."],
  "server.vox.titlu_lung": ["Titlul are peste {n} de caractere.", "The title is over {n} characters long."],
  "server.vox.titlu_invalid": ["Titlul nu e valid.", "The title is not valid."],
```

- [ ] **Step 4: verificare**

Run: `npm run typecheck`
Expected: 0 erori.

- [ ] **Step 5: commit**

```bash
git add shared/src/vox.ts web/src/api/vox.ts web/src/i18n/dict/vox.ts web/src/pages/Vox.tsx
git commit -m "shared, web: schemele și cererile istoricului Vox (listă, conversație, redenumire, ștergere)"
```

### Task 5: coloana „Conversații” și pagina legată de conversație

**Files:**
- Create: `web/src/pages/vox/Conversatii.tsx`
- Modify: `web/src/pages/Vox.tsx`
- Modify: `web/src/styles/vox.css`
- Modify: `web/src/i18n/dict/vox.ts`
- Verify: script Playwright în scratchpad, `captura_istoric.py`

**Interfaces:**
- Consumes: tot din Task 4.
- Produces: `default Conversatii(props)`, `ziua(iso, acum?)`, `ora(iso, locale)`, `cand(iso, baza, t, locale)`, `filtreaza(lista, cauta)` din `pages/vox/Conversatii.tsx`.

- [ ] **Step 1: textele** (în `web/src/i18n/dict/vox.ts`; `vox.subsol_sesiune` se înlocuiește cu `vox.subsol_conversatie`)

```ts
  "vox.placeholder_continua": ["Continuă conversația, de pildă „și la ING?”…", "Continue the conversation, e.g. “and at ING?”…"],
  "vox.subsol_conversatie": ["{model} · conversația: {cost}", "{model} · this conversation: {cost}"],
  "vox.conv.titlu_coloana": ["Conversații", "Conversations"],
  "vox.conv.noua": ["Conversație nouă", "New conversation"],
  "vox.conv.cauta": ["Caută în conversații", "Search conversations"],
  "vox.conv.azi": ["Azi", "Today"],
  "vox.conv.ieri": ["Ieri", "Yesterday"],
  "vox.conv.vechi": ["Mai vechi", "Older"],
  "vox.conv.n_intrebari_1": ["1 întrebare", "1 question"],
  "vox.conv.n_intrebari_n": ["{n} întrebări", "{n} questions"],
  "vox.conv.nimic": ["Nicio conversație cu „{q}”.", "No conversation with “{q}”."],
  "vox.conv.goala": ["Nicio conversație salvată încă: prima întrebare o începe.", "No saved conversation yet: your first question starts one."],
  "vox.conv.unde": ["Salvate pe acest laptop. Redeschiderea nu cheamă modelul, deci nu costă nimic.", "Saved on this laptop. Reopening does not call the model, so it costs nothing."],
  "vox.conv.redenumeste": ["Redenumește", "Rename"],
  "vox.conv.titlu_nou": ["Titlul conversației (gol = prima întrebare)", "Conversation title (empty = first question)"],
  "vox.conv.sterge": ["Șterge", "Delete"],
  "vox.conv.sterge_confirm": ["Ștergi conversația? Nu se poate reface.", "Delete this conversation? This cannot be undone."],
  "vox.conv.renunta": ["Renunță", "Cancel"],
  "vox.conv.eroare_lista": ["Lista conversațiilor nu s-a putut citi.", "The conversation list could not be read."],
  "vox.conv.lipsa": ["Conversația din adresă nu mai există; începi una nouă.", "The conversation in the address no longer exists; you are starting a new one."],
  "vox.conv.istoric_btn": ["Conversații ({n})", "Conversations ({n})"],
  "vox.conv.se_incarca": ["Se încarcă conversația…", "Loading the conversation…"],
  "vox.conv.ora_azi": ["azi, {ora}", "today, {ora}"],
  "vox.conv.ora_ieri": ["ieri, {ora}", "yesterday, {ora}"],
  "vox.conv.ora_vechi": ["{zi}, {ora}", "{zi}, {ora}"],
  "vox.conv.inceputa_azi": ["începută azi la {ora}", "started today at {ora}"],
  "vox.conv.inceputa_ieri": ["începută ieri la {ora}", "started yesterday at {ora}"],
  "vox.conv.inceputa_vechi": ["începută pe {zi} la {ora}", "started on {zi} at {ora}"],
```

- [ ] **Step 2: coloana** (`web/src/pages/vox/Conversatii.tsx`)

```tsx
import { useState } from 'react'
import { App, Input, Popconfirm, Tooltip } from 'antd'
import { DeleteOutlined, EditOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons'
import type { ConversatieRezumat } from '@mcc/shared'
import { useLang, type DictKey } from '../../i18n'
import { deLaServer } from '../../i18n/server'
import { faraDiacritice } from '../../util/format'

/**
 * Coloana „Conversații” din pagina Vox (macheta aprobată pe 07.10.2026): conversațiile salvate pe
 * laptop (loguri/vox/conversatii/), pe zile, cu căutare, redenumire și ștergere. Stă în pagina Vox,
 * nu în bara vișinie: aceea depășește deja ecranul la 800px înălțime, iar lista crește.
 */

type Tr = (k: DictKey, p?: Record<string, string | number>) => string
export type Zi = 'azi' | 'ieri' | 'vechi'
const ZILE: Zi[] = ['azi', 'ieri', 'vechi']

/** Ziua unei ore față de azi, în ora laptopului. */
export function ziua(iso: string, acum = new Date()): Zi {
  const inceput = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime()
  const zile = Math.round((inceput(acum) - inceput(new Date(iso))) / 86400000)
  return zile <= 0 ? 'azi' : zile === 1 ? 'ieri' : 'vechi'
}

export const ora = (iso: string, locale: string) =>
  new Date(iso).toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' })
const data = (iso: string, locale: string) =>
  new Date(iso).toLocaleDateString(locale, { day: '2-digit', month: '2-digit', year: 'numeric' })

/** „azi, 12:37” / „începută ieri la 18:20” …: cheile `<baza>_azi|_ieri|_vechi`. */
export function cand(iso: string, baza: 'vox.conv.ora' | 'vox.conv.inceputa', t: Tr, locale: string): string {
  return t(`${baza}_${ziua(iso)}` as DictKey, { ora: ora(iso, locale), zi: data(iso, locale) })
}

export interface RandConv extends ConversatieRezumat {
  /** prima întrebare care se potrivește, când potrivirea nu e în titlu */
  potrivire?: string
}

/** Fiecare cuvânt căutat trebuie să apară în titlu sau în întrebări, fără diacritice și majuscule. */
export function filtreaza(lista: ConversatieRezumat[], cauta: string): RandConv[] {
  const cuvinte = faraDiacritice(cauta).split(/\s+/).filter(Boolean)
  if (!cuvinte.length) return lista
  const are = (s: string, toate: boolean) => {
    const f = faraDiacritice(s)
    return toate ? cuvinte.every((w) => f.includes(w)) : cuvinte.some((w) => f.includes(w))
  }
  return lista.flatMap((c) => {
    if (!are([c.titlu, ...c.texte].join('\n'), true)) return []
    if (are(c.titlu, true)) return [c]
    return [{ ...c, potrivire: c.texte.find((x) => x !== c.titlu && are(x, false)) }]
  })
}

interface Props {
  lista: ConversatieRezumat[] | undefined
  eroare: boolean
  deschisa: string | null
  cauta: string
  /** cât o întrebare așteaptă răspunsul, conversația nu se schimbă */
  blocat: boolean
  /** fără tokenul lui Vox (Vox oprit) istoricul e doar de citit */
  poateModifica: boolean
  inSertar?: boolean
  onCauta: (q: string) => void
  onDeschide: (id: string) => void
  onNoua: () => void
  onRedenumeste: (id: string, titlu: string) => Promise<void>
  onSterge: (id: string) => Promise<void>
}

export default function Conversatii(p: Props) {
  const { t, tn, lang, locale } = useLang()
  const { message } = App.useApp()
  const [editez, setEditez] = useState<string | null>(null)
  const randuri = filtreaza(p.lista ?? [], p.cauta)
  const greseala = (e: unknown) => void message.error(deLaServer((e as Error).message, lang))
  const salveaza = async (id: string, titlu: string) => {
    setEditez(null)
    try {
      await p.onRedenumeste(id, titlu)
    } catch (e) {
      greseala(e)
    }
  }
  return (
    <aside className={p.inSertar ? 'vox-conv in-sertar' : 'vox-conv'} aria-label={t('vox.conv.titlu_coloana')}>
      <button type="button" className="vox-conv-noua" onClick={p.onNoua} disabled={p.blocat}>
        <PlusOutlined /> {t('vox.conv.noua')}
      </button>
      <Input
        allowClear
        prefix={<SearchOutlined />}
        value={p.cauta}
        onChange={(e) => p.onCauta(e.target.value)}
        placeholder={t('vox.conv.cauta')}
        aria-label={t('vox.conv.cauta')}
      />
      {p.eroare && <p className="vox-conv-nota">{t('vox.conv.eroare_lista')}</p>}
      {p.lista?.length === 0 && <p className="vox-conv-nota">{t('vox.conv.goala')}</p>}
      {!!p.lista?.length && randuri.length === 0 && <p className="vox-conv-nota">{t('vox.conv.nimic', { q: p.cauta })}</p>}
      {ZILE.map((zi) => {
        const grupa = randuri.filter((c) => ziua(c.ultima) === zi)
        if (!grupa.length) return null
        return (
          <div key={zi} className="vox-conv-grupa">
            <h3>{t(`vox.conv.${zi}` as DictKey)}</h3>
            <ul>
              {grupa.map((c) => {
                const activ = c.id === p.deschisa
                return (
                  <li key={c.id} className={activ ? 'activ' : undefined}>
                    {editez === c.id ? (
                      <Input
                        size="small"
                        autoFocus
                        maxLength={120}
                        defaultValue={c.redenumita ? c.titlu : ''}
                        placeholder={c.texte[0]}
                        aria-label={t('vox.conv.titlu_nou')}
                        onPressEnter={(e) => void salveaza(c.id, e.currentTarget.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Escape') setEditez(null)
                        }}
                        onBlur={() => setEditez(null)}
                      />
                    ) : (
                      <button
                        type="button"
                        className="vox-conv-deschide"
                        onClick={() => p.onDeschide(c.id)}
                        disabled={p.blocat}
                        aria-current={activ ? 'true' : undefined}
                      >
                        <span className="t">{c.titlu}</span>
                        {c.potrivire && <span className="potrivire">↳ {c.potrivire}</span>}
                        <span className="m">
                          {tn('vox.conv.n_intrebari', c.intrebari)} · {zi === 'vechi' ? data(c.ultima, locale) : ora(c.ultima, locale)}
                        </span>
                      </button>
                    )}
                    {p.poateModifica && editez !== c.id && (
                      <span className="vox-conv-actiuni">
                        <Tooltip title={t('vox.conv.redenumeste')}>
                          <button type="button" aria-label={t('vox.conv.redenumeste')} disabled={p.blocat} onClick={() => setEditez(c.id)}>
                            <EditOutlined />
                          </button>
                        </Tooltip>
                        <Popconfirm
                          title={t('vox.conv.sterge_confirm')}
                          okText={t('vox.conv.sterge')}
                          cancelText={t('vox.conv.renunta')}
                          okButtonProps={{ danger: true }}
                          onConfirm={async () => {
                            try {
                              await p.onSterge(c.id)
                            } catch (e) {
                              greseala(e)
                            }
                          }}
                        >
                          <button type="button" aria-label={t('vox.conv.sterge')} disabled={p.blocat}>
                            <DeleteOutlined />
                          </button>
                        </Popconfirm>
                      </span>
                    )}
                  </li>
                )
              })}
            </ul>
          </div>
        )
      })}
      <p className="vox-conv-unde">{t('vox.conv.unde')}</p>
    </aside>
  )
}
```

- [ ] **Step 3: pagina** (`web/src/pages/Vox.tsx`)

Importuri noi: `useQueryClient` din `@tanstack/react-query`, `useSearchParams` din `react-router-dom`, `Drawer` din `antd`, `HistoryOutlined` din `@ant-design/icons`, `ApiError` din `../api/client`, din `../api/vox` și `CHEIE_CONVERSATII, citesteConversatia, redenumesteConversatia, stergeConversatia, useConversatii`, iar `Conversatii, { cand }` din `./vox/Conversatii`.

`Mesaj` primește `data: string` (ora întrebării, ISO). Docblock-ul paginii înlocuiește fraza „Conversația stă doar în memoria paginii…” cu: „Conversațiile se păstrează pe laptop (loguri/vox/conversatii/, prin server) și se redeschid din coloana „Conversații”; cea deschisă stă în adresă (`?c=`), fiindcă redeschiderea citește fișierul și nu cheamă modelul.”

Componenta `Vox`, până la `return`:

```tsx
export default function Vox() {
  const { t, tn, lang, locale } = useLang()
  const qc = useQueryClient()
  const [sp, setSp] = useSearchParams()
  const c = sp.get('c')
  const cauta = sp.get('cauta') ?? ''
  const meta = useMeta()
  const stare = useStareVox()
  const conversatii = useConversatii()
  const [text, setText] = useState('')
  const [mesaje, setMesaje] = useState<Mesaj[]>([])
  const [seTrimite, setSeTrimite] = useState(false)
  const [seIncarca, setSeIncarca] = useState(false)
  const [lipsa, setLipsa] = useState(false)
  const [eroareConv, setEroareConv] = useState<string | null>(null)
  const [sertarConv, setSertarConv] = useState(false)
  const [cerere, setCerere] = useState<CerereSertar | null>(null)
  // conversația creată chiar acum de prima întrebare: e deja în `mesaje`, nu se recitește
  const creata = useRef<string | null>(null)
  const capat = useRef<HTMLDivElement>(null)

  const mergi = (k: Record<string, string | null>, inIstoric = false) =>
    setSp((p) => {
      const n = new URLSearchParams(p)
      for (const [cheie, v] of Object.entries(k)) {
        if (v) n.set(cheie, v)
        else n.delete(cheie)
      }
      return n
    }, { replace: !inIstoric })

  // tura nouă apare jos, deasupra câmpului fix: pagina coboară după ea
  useEffect(() => {
    if (mesaje.length) capat.current?.scrollIntoView({ block: 'end', behavior: 'smooth' })
  }, [mesaje])

  // conversația din adresă (clic în coloană, link, înapoi/înainte): se citește din fișier, fără model
  useEffect(() => {
    if (c && c === creata.current) {
      creata.current = null
      return
    }
    setMesaje([])
    setEroareConv(null)
    setSeIncarca(false)
    if (!c) return
    let anulat = false
    setLipsa(false)
    setSeIncarca(true)
    citesteConversatia(c)
      .then((conv) => {
        if (!anulat) setMesaje(conv.ture.map((x, i) => ({ id: i + 1, intrebare: x.intrebare, data: x.data, raspuns: x.raspuns })))
      })
      .catch((e: unknown) => {
        if (anulat) return
        if (e instanceof ApiError && e.status === 404) {
          setLipsa(true)
          mergi({ c: null })
          return
        }
        const mesaj = (e as Error).message
        setEroareConv(mesaj === SERVER_OPRIT ? t('comun.server_oprit') : deLaServer(mesaj, lang))
      })
      .finally(() => {
        if (!anulat) setSeIncarca(false)
      })
    return () => {
      anulat = true
    }
  }, [c])

  const err = meta.error ?? stare.error
  if (err) return <Eroare e={err} />
  if (!meta.data || !stare.data) return <SeIncarca />
  const m = meta.data
  const st = stare.data
  const poate = st.activ && !seTrimite && !seIncarca
  const cost = mesaje.reduce((s, x) => s + (x.raspuns?.cost_usd ?? 0), 0)
  const raspunse = mesaje.filter((x) => x.raspuns).length
  const titlu = conversatii.data?.find((x) => x.id === c)?.titlu ?? mesaje[0]?.intrebare ?? ''

  async function trimite(intrebare: string) {
    const q = intrebare.trim()
    if (!q || seTrimite || seIncarca || !st.activ) return
    // „și la BRD?” continuă ultima căutare reușită, nu o clarificare sau o eroare
    const anterior = [...mesaje].reverse().find((x) => x.raspuns?.interpretare.tip === 'cautare')?.raspuns?.interpretare ?? null
    const id = Date.now()
    setLipsa(false)
    setMesaje((x) => [...x, { id, intrebare: q, data: new Date().toISOString() }])
    setSeTrimite(true)
    try {
      const r = await trimiteIntrebarea(q, anterior, c, st.token ?? '')
      setMesaje((x) => x.map((y) => (y.id === id ? { ...y, raspuns: r } : y)))
      setText('')
      if (r.conversatie && r.conversatie !== c) {
        creata.current = r.conversatie
        mergi({ c: r.conversatie })
      }
    } catch (e) {
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

  const intreaba = (q: string) => {
    setText(q)
    void trimite(q)
  }
  const deschide = (id: string) => {
    setSertarConv(false)
    if (id !== c) mergi({ c: id }, true)
  }
  const noua = () => {
    setSertarConv(false)
    setText('')
    setMesaje([])
    setLipsa(false)
    if (c) mergi({ c: null }, true)
  }
  const redenumeste = async (id: string, titluNou: string) => {
    await redenumesteConversatia(id, titluNou, st.token ?? '')
    await qc.invalidateQueries({ queryKey: CHEIE_CONVERSATII })
  }
  const sterge = async (id: string) => {
    await stergeConversatia(id, st.token ?? '')
    if (id === c) noua()
    await qc.invalidateQueries({ queryKey: CHEIE_CONVERSATII })
  }
  const coloana = (inSertar: boolean) => (
    <Conversatii
      lista={conversatii.data}
      eroare={!!conversatii.error}
      deschisa={c}
      cauta={cauta}
      blocat={seTrimite}
      poateModifica={!!st.token}
      inSertar={inSertar}
      onCauta={(q) => mergi({ cauta: q || null })}
      onDeschide={deschide}
      onNoua={noua}
      onRedenumeste={redenumeste}
      onSterge={sterge}
    />
  )
```

`return`-ul: rădăcina `.vox` conține coloana, apoi `.vox-chat` cu tot ce era înainte în `.vox`, plus capul conversației, ora fiecărei ture, nota „lipsă” și butonul pentru ecranele înguste; sertarul cu coloana stă lângă `Sertar`:

```tsx
  return (
    <div className="vox">
      {coloana(false)}
      <div className="vox-chat">
        {!st.activ && <div className="callout warn">{t('vox.oprit')}</div>}
        <Button className="vox-istoric-btn" icon={<HistoryOutlined />} onClick={() => setSertarConv(true)}>
          {t('vox.conv.istoric_btn', { n: conversatii.data?.length ?? 0 })}
        </Button>
        {lipsa && <div className="callout warn">{t('vox.conv.lipsa')}</div>}
        {eroareConv && <div className="callout warn">{eroareConv}</div>}
        {c && mesaje.length > 0 && (
          <div className="vox-conv-cap">
            <b>{titlu}</b>
            <span>
              {tn('vox.conv.n_intrebari', raspunse)} · {dolari(cost, locale)} · {cand(mesaje[0]!.data, 'vox.conv.inceputa', t, locale)}
            </span>
          </div>
        )}
        {seIncarca && <div className="vox-bula vox-gandeste">{t('vox.conv.se_incarca')}</div>}
        {!seIncarca && mesaje.length === 0 && <BunVenit banci={Object.keys(m.nume).length} poate={poate} onExemplu={intreaba} />}
        {mesaje.map((x) => (
          <div key={x.id} className="vox-tura">
            <span className="vox-ora">{cand(x.data, 'vox.conv.ora', t, locale)}</span>
            <p className="vox-q">{x.intrebare}</p>
            {/* … rândul `.vox-r` neschimbat (avatar, se gândește, eroare, Raspuns) … */}
          </div>
        ))}
        <div ref={capat} className="vox-capat" />
        {/* … `.vox-compune` neschimbat, cu două diferențe: */}
        {/* placeholder={t(mesaje.length ? 'vox.placeholder_continua' : 'vox.placeholder')} */}
        {/* subsolul din dreapta: mesaje.length > 0 ? t('vox.subsol_conversatie', { model, cost }) : t('vox.subsol_gol', { model }) */}
      </div>
      <Drawer open={sertarConv} onClose={() => setSertarConv(false)} placement="left" width={320} title={t('vox.conv.titlu_coloana')}>
        {coloana(true)}
      </Drawer>
      <Sertar cerere={cerere} onClose={() => setCerere(null)} />
    </div>
  )
}
```

(Rândul `.vox-r` și blocul `.vox-compune` se copiază exact din versiunea de azi a fișierului; `BunVenit`, `Raspuns`, `FisaBanca`, `Rand` rămân neschimbate.)

- [ ] **Step 4: stilurile** (`web/src/styles/vox.css`)

Blocul de sus devine:

```css
main:has(> .vox) { display: flex; flex-direction: column; padding-bottom: 0 }
.vox { flex: 1 0 auto; display: flex; align-items: flex-start; gap: 22px }
.vox-chat { flex: 1 1 auto; align-self: stretch; min-width: 0; display: flex; flex-direction: column; gap: 16px }
.vox-chat > .callout { margin: 0 }
```

(regula veche `.vox > .callout` dispare), iar la final, înainte de `@media (max-width: 760px)`:

```css
/* coloana „Conversații”: în pagina Vox, nu în bara vișinie (care la 800px depășește deja ecranul);
   rămâne pe ecran la derulare */
.vox-conv { flex: 0 0 268px; position: sticky; top: 12px; max-height: calc(100vh - 24px); overflow: auto; box-sizing: border-box;
  display: flex; flex-direction: column; gap: 8px; padding: 12px; background: var(--surface); border: 1px solid var(--line);
  border-radius: 14px; box-shadow: var(--umbra) }
.vox-conv.in-sertar { position: static; max-height: none; padding: 0; border: 0; box-shadow: none; background: none }
.vox-conv-noua { display: flex; align-items: center; justify-content: center; gap: 8px; min-height: 40px; border: 1px dashed var(--line-2);
  border-radius: 10px; background: none; color: var(--accent); font: inherit; font-size: 13px; font-weight: 600; cursor: pointer }
.vox-conv-noua:hover:not(:disabled) { border-color: var(--accent); background: var(--accent-tint) }
.vox-conv-noua:disabled, .vox-conv-deschide:disabled { cursor: not-allowed; opacity: .7 }
.vox-conv h3 { margin: 8px 6px 2px; font-family: var(--mono); font-size: 9.5px; font-weight: 600; letter-spacing: .12em;
  text-transform: uppercase; color: var(--muted) }
.vox-conv ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 2px }
.vox-conv li { display: flex; align-items: flex-start; gap: 2px; border-radius: 9px }
.vox-conv li:hover, .vox-conv li:focus-within { background: var(--bg) }
.vox-conv li.activ { background: var(--accent-tint) }
.vox-conv li > .ant-input { margin: 6px }
.vox-conv-deschide { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; padding: 8px 10px; border: 0; background: none;
  color: var(--ink); font: inherit; text-align: left; cursor: pointer }
.vox-conv-deschide .t { font-size: 13px; line-height: 1.35; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2;
  -webkit-box-orient: vertical; overflow-wrap: anywhere }
.vox-conv li.activ .t { color: var(--nav-activ-ink); font-weight: 600 }
.vox-conv-deschide .potrivire { font-size: 11.5px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap }
.vox-conv-deschide .m { font-family: var(--mono); font-size: 10px; color: var(--muted) }
.vox-conv-actiuni { display: flex; gap: 2px; padding: 6px 6px 0 0; opacity: 0 }
.vox-conv li:hover .vox-conv-actiuni, .vox-conv li:focus-within .vox-conv-actiuni, .vox-conv li.activ .vox-conv-actiuni { opacity: 1 }
.vox-conv-actiuni button { width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; border: 0;
  border-radius: 7px; background: none; color: var(--muted); cursor: pointer }
.vox-conv-actiuni button:hover:not(:disabled) { background: var(--accent-tint); color: var(--accent) }
.vox-conv-noua:focus-visible, .vox-conv-deschide:focus-visible, .vox-conv-actiuni button:focus-visible { outline: 2px solid var(--accent);
  outline-offset: 1px }
.vox-conv-nota { margin: 4px 6px; font-size: 12px; color: var(--muted) }
.vox-conv-unde { margin: auto 6px 2px; padding-top: 10px; border-top: 1px solid var(--line); font-size: 11.5px; color: var(--muted) }
/* capul conversației deschise și ora fiecărei ture */
.vox-conv-cap { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 6px 16px; padding-bottom: 10px;
  border-bottom: 1px solid var(--line) }
.vox-conv-cap b { font-family: var(--serif); font-size: 17px; font-weight: 600; overflow-wrap: anywhere }
.vox-conv-cap span { font-family: var(--mono); font-size: 10.5px; color: var(--muted) }
.vox-ora { align-self: center; font-family: var(--mono); font-size: 10px; letter-spacing: .06em; text-transform: uppercase; color: var(--muted) }
/* sub 1100px coloana lasă loc chatului și se deschide dintr-un buton, într-un sertar */
.vox-istoric-btn.ant-btn { display: none }
@media (max-width: 1100px) {
  .vox > .vox-conv { display: none }
  .vox-istoric-btn.ant-btn { display: inline-flex; align-self: flex-start }
}
```

- [ ] **Step 5: typecheck**

Run: `npm run typecheck` → 0 erori.

- [ ] **Step 6: capturi și comportament, fără apeluri plătite**

Scriptul `captura_istoric.py` (scratchpad) deschide `http://localhost:5173/#/vox` în Edge cu `page.route` pentru `**/api/vox**`: `GET /api/vox` → `{activ: true, model, token}`; `GET /api/vox/conversatii` → o listă de 4 (2 azi, 1 ieri, 1 mai veche) construită din răspunsurile reale din `raspunsuri_vox.json`; `GET …/<id>` → conversația cu turele; `POST /api/vox` → răspunsul următor + `conversatie`, cu corpul cererii reținut; `POST …/redenumeste|sterge` → actualizează lista. Verifică și tipărește:
1. grupele „Azi / Ieri / Mai vechi” și rândurile;
2. căutarea „BANCA” și „vamala” (majuscule, fără diacritice) găsește conversațiile cu „bancă” / „vamale”; „zzz” → „Nicio conversație cu „zzz”.”; rândul cu potrivire în a doua întrebare arată „↳ …”;
3. clic pe o conversație: adresa are `c=<id>`, capul arată titlul și „N întrebări · $… · începută …”, turele au ora; niciun POST la `/api/vox`;
4. o întrebare nouă în conversația deschisă: corpul POST are `conversatie: <id>` și `anterior` = ultima interpretare;
5. cât POST-ul așteaptă (răspuns întârziat 1,5 s), butoanele din coloană sunt `disabled`;
6. redenumire: creion → câmp → Enter → POST cu `{titlu}`, rândul arată titlul nou; Esc renunță fără POST;
7. ștergere: coș → confirmare → POST `sterge`; ștergerea conversației deschise duce la conversație nouă (fără `c`);
8. „Înapoi” spre conversația ștearsă (`GET` → 404): nota „Conversația din adresă nu mai există…”, `c` dispare;
9. „+ Conversație nouă”: chat gol, bun venit, fără `c`; prima întrebare pune `c` în adresă fără să recitească fișierul (niciun `GET …/<id>` după POST);
10. la 1000px lățime: coloana ascunsă, butonul „Conversații (N)” deschide sertarul;
11. capturi RO, EN și întunecat; consola fără erori.

Expected: toate cele 11 trec; consola fără erori.

- [ ] **Step 7: commit**

```bash
git add web/src/pages/vox/Conversatii.tsx web/src/pages/Vox.tsx web/src/styles/vox.css web/src/i18n/dict/vox.ts
git commit -m "web: coloana „Conversații” în pagina Vox (pe zile, căutare, redenumire, ștergere); conversația deschisă în adresă"
```

### Task 6: documentația și verificarea întregului

**Files:**
- Modify: `CLAUDE.md` (rândul despre Vox de la „Serverul e read-only”)
- Modify: `README.md` (secțiunea Vox)
- Modify: `.serena/memories/cod/harta.md`, `.serena/memories/stare/ultima_actualizare.md`

- [ ] **Step 1: CLAUDE.md** — după „…iar cifrele vin din bază, niciodată de la model.” se adaugă: „Conversațiile lui Vox sunt fișiere pe laptop, în `loguri/vox/conversatii/`, nu în bază.”

- [ ] **Step 2: README** — punctul „Conversația nu se salvează și nu intră în adresă…” devine:

```markdown
- Istoricul: fiecare conversație e un fișier pe laptop, `loguri/vox/conversatii/<id>.jsonl` (un rând
  pe întrebare, cu răspunsul ei; o redenumire e tot un rând). Coloana „Conversații” din pagină le
  redeschide fără model (gratuit), le caută în titlu și în întrebări (fără diacritice), le redenumește
  și le șterge; cea deschisă stă în adresă (`#/vox?c=<id>`). Jurnalul de costuri rămâne separat, în
  `loguri/vox/AAAA-LL.jsonl`.
```

- [ ] **Step 3: memoriile Serena** — în `cod/harta.md`, rândul despre `app/vox.py` capătă „`Istoric` (conversațiile, fișiere în `loguri/vox/conversatii/`; rutele `GET /api/vox/conversatii[/<id>]`, `POST …/<id>/redenumeste|sterge`, tot în `Handler`)”, iar rândul despre `web/src/` capătă `vox/` printre folderele din `pages/`. Commit-ul de referință în `stare/ultima_actualizare.md`.

- [ ] **Step 4: verificarea întregului**

```
.venv\Scripts\python.exe app/test_vox.py          → OK
.venv\Scripts\python.exe app/test_rulari.py       → OK
npm run typecheck                                  → 0 erori
server temporar pe 8797 (mip_merge, MIP_PERMITE_VOX=0) + MIP_URL=http://localhost:8797 python app/verifica_pagini.py → 0 pagini cu erori din 12
```

- [ ] **Step 5: commit**

```bash
git add CLAUDE.md README.md .serena/memories/cod/harta.md .serena/memories/stare/ultima_actualizare.md
git commit -m "docs, serena: istoricul Vox (fișiere în loguri/vox/conversatii/, coloana din pagină)"
```
