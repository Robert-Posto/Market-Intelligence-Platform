# Vox: clasamente pe comisioane și dobânzi — planul de implementare

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Vox răspunde la „care bancă are cel mai mic…” / „unde stă Libra la…” cu un clasament din bază, cu aceleași cifre ca 2.1 și 2.2, Libra evidențiată, dovezi pe fiecare rând și băncile fără date cu motivul lor.

**Architecture:** interogarea celulelor din `matrice` și `rate` devine `celule_matrice` / `celule_rate`, comune paginilor și lui Vox. `_clasament_vox` alege sursa (comision în lei sau dobândă cu categorie) și întoarce blocurile de celule; `app/vox.py` le ordonează (`clasa`: sens, mediană sau cea mai bună variantă, locuri comune la egalitate). Modelul primește tipul `clasament` și câmpurile `segment` și `metrica`; interfața are fișa nouă `web/src/pages/vox/Clasament.tsx`.

**Tech Stack:** Python 3.12 (`unittest`, psycopg2), Anthropic SDK (Haiku 4.5, schemă strictă), React 18 + AntD 5 + TanStack Query + Zod, Playwright (Edge).

**Spec:** `docs/superpowers/specs/2026-10-07-vox-clasamente-design.md`

`SCRATCH` = dosarul temporar al sesiunii; în Git Bash:
`S="C:/Users/NICOLA~1.CHE/AppData/Local/Temp/claude/c--Users-nicolae-cherascu-Desktop-Market-Intelligence-Platform/e6a2503b-45f0-43b2-91ba-6b16a4fdc1ef/scratchpad"`.

## Global Constraints

- Buget pentru apeluri plătite: **cel mult $1 în total**, aprobat de Nicolae pe 07.10.2026. Apeluri plătite doar în Task 4 (`eval_vox.py --da`, ~$0,08 pe rulare, cel mult 3 rulări) și Task 6 (testul cap-coadă, ~$0,03). Costul fiecărei rulări se trece în registru; peste $0,60 cumulat, nu se mai rulează nimic plătit.
- Testele și verificările de interfață nu cheamă modelul: `ClientFals`, model fals în scripturi, `GET`/`POST /api/vox` răspunse din fișier în Playwright.
- Serverele utilizatorului (:8765, :5173) nu se opresc și nu se repornesc; `npm run build` nu se rulează; serverul temporar: `MIP_PORT=8797 MCC_AUTH_LOCAL=admin MIP_PERMITE_VOX=0 .venv/Scripts/python.exe app/server.py`. Testul cap-coadă plătit nu trece prin HTTP: un script cu `vox.Vox`, cititorii reali și jurnalul într-un dosar temporar (nu în `loguri/vox/`, deci nu în istoricul utilizatorului).
- Serverul rămâne read-only; în SQL doar parametri `%s`; `segment` și `metrica` doar din listele lor.
- Aceleași cifre ca paginile: `matrice` și `rate` dau rezultate identice înainte și după extragerea interogărilor (verificat pe `mip_merge`).
- Valori: `TIPURI = ("cautare", "clasament", "neclar", "in_afara")`; `segment` ∈ `ORDINE_SEGMENT`; `METRICI = ("mediana", "cea_mai_buna")`; bloc `tip` ∈ `exact` / `nespecificat`.
- Identificatori în română fără diacritice; texte prin `t` / `tn`, perechi `[română, engleză]`; niciun pachet nou.
- Comentariile spun de ce, cu cifra măsurată (`mip_merge`, 07.10.2026); commit-uri „zonă: ce și de ce”, fără `Co-Authored-By`, prin `git commit -F`.
- `app/server.py` are CRLF; scripturile Python cu `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe`, din rădăcina repo-ului. Nu se citește `.env`.

## Review Focus

- Conversațiile salvate (fără `clasament`, interpretări fără `segment` / `metrica`) se redeschid fără eroare Zod, iar continuarea uneia vechi trimite un `anterior` valid — Playwright pe conversațiile vechi în Task 5; `verifica_anterior` cu interpretarea veche, test în Task 3.
- „și pentru firme?” după un clasament ajunge la model cu clasamentul ca `anterior` (pagina lua `anterior` doar din căutări) — cazul din evaluare în Task 4 și pasul din pagină în Task 5.
- Sertarul deschis dintr-un rând de clasament arată exact celula din 2.1 / 2.2 (regula din 2.1, fără `strict`; termenul și tipul de credit ale blocului) — Playwright în Task 5.
- Egalitățile: locul comun și ordinea alfabetică stabilă, inclusiv Libra în egalitate — test `test_egalitati_loc_comun` în Task 3.
- O dobândă fără categorie la clasament (`nominala`) nu produce un clasament amestecat depozit + credit — test în Task 3.

---

### Task 1: celulele din 2.1 și 2.2 într-un singur loc

**Files:**
- Modify: `app/server.py` (`celule_matrice` înaintea lui `matrice`; `_filtre_rate`, `_baza_rate`, `celule_rate` înaintea lui `rate`; `matrice` și `rate` le apelează)
- Test: `app/test_celula.py` (clasa nouă `CeluleSQL`)
- Script: `SCRATCH/verifica_celule_db.py`

**Interfaces:**
- Produces: `celule_matrice(campuri: list[str], unitate: str, segment: str) -> list[dict]` (cheile de azi ale `matrice()["celule"]`); `celule_rate(campuri: list[str], categorie: str, termen: str, produs: str) -> list[dict]` (cheile de azi ale `rate()["celule"]`).

- [ ] **Step 1: fotografia de dinainte**

`SCRATCH/verifica_celule_db.py`:

```python
"""matrice() și rate() pe mip_merge, înainte și după extragerea interogării celulelor (07.10.2026).

  python verifica_celule_db.py inainte   → celule_inainte.json
  python verifica_celule_db.py dupa      → identic / DIFERIT pe fiecare apel
"""
import json, os, sys
sys.stdout.reconfigure(encoding="utf-8")
RAD = r"C:\Users\nicolae.cherascu\Desktop\Market-Intelligence-Platform"
AICI = os.path.dirname(os.path.abspath(__file__))
os.chdir(RAD); sys.path.insert(0, os.path.join(RAD, "app"))
import server

APELURI = [("matrice", {"grup": [g], "segment": [s], "unitate": [u]})
           for g in server.GRUPURI for s in ("pf", "pj", "pfa", "toate") for u in ("lei", "eur")]
APELURI += [("rate", {"categorie": ["depozite"], "termen": [t]}) for t in ("", "scurt", "6", "12", "lung", "necunoscut")]
APELURI += [("rate", {"categorie": ["credite"], "termen": [t], "produs": [p]})
            for t in ("", "lung", "necunoscut") for p in ("", "ipotecar", "nevoi_personale", "card", "rate_magazin", "altele")]
APELURI += [("rate", {"categorie": ["conturi_carduri"]})]
FIS = os.path.join(AICI, "celule_inainte.json")


def ruleaza():
    return {f"{f}|{json.dumps(q, sort_keys=True)}": json.loads(json.dumps(getattr(server, f)(q), default=str))
            for f, q in APELURI}


if sys.argv[1] == "inainte":
    json.dump(ruleaza(), open(FIS, "w", encoding="utf-8"), ensure_ascii=False)
    print("scris", FIS, len(APELURI), "apeluri")
    sys.exit()
vechi, nou = json.load(open(FIS, encoding="utf-8")), ruleaza()
diferite = [k for k in vechi if vechi[k] != nou.get(k)]
print(f"{len(vechi) - len(diferite)} identice din {len(vechi)}")
for k in diferite:
    print("DIFERIT", k)
```

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe "$S/verifica_celule_db.py" inainte`
Expected: `scris …/celule_inainte.json 49 apeluri`

- [ ] **Step 2: testele care pică**

În `app/test_celula.py`, înainte de `if __name__ == "__main__":`:

```python
class CeluleSQL(unittest.TestCase):
    """Celulele din 2.1 și 2.2, scoase din `matrice` și `rate` ca să le folosească și clasamentele Vox."""

    def setUp(self):
        self.cereri, self.vechi = [], server.interoghează
        server.interoghează = lambda sql, params=None: self.cereri.append((sql, tuple(params or ()))) or []

    def tearDown(self):
        server.interoghează = self.vechi

    def test_matrice_segment_si_prag(self):
        server.celule_matrice(["administrare_cont"], "lei", "pf")
        sql, params = self.cereri[-1]
        self.assertIn(f"AND ({server.COND_SEG})", sql)
        self.assertIn(f"<= {server.PRAGURI['suma']}", sql)
        self.assertEqual(params, (["administrare_cont"], "lei", "pf"))

    def test_matrice_toate_fara_segment(self):
        server.celule_matrice(["administrare_cont"], "lei", "toate")
        sql, params = self.cereri[-1]
        self.assertNotIn(server.COND_SEG, sql)
        self.assertEqual(params, (["administrare_cont"], "lei"))

    def test_rate_termen_si_produs(self):
        server.celule_rate(["dae"], "credite", "lung", "ipotecar")
        sql, params = self.cereri[-1]
        self.assertIn(f"{server.TERMEN_LUNI} > 12", sql)
        self.assertIn(f"{server.PRODUS_CREDIT} = %s", sql)
        self.assertIn(f"<= {server.GRUPURI_RATE['credite']['prag']}", sql)
        self.assertEqual(params, (["dae"], "credite", "ipotecar"))

    def test_rate_fara_filtre(self):
        server.celule_rate(["nominala"], "depozite", "", "")
        sql, params = self.cereri[-1]
        self.assertNotIn(server.TERMEN_LUNI, sql.split("WITH randuri AS")[1].split("), agregat")[0].split("AS luni")[1])
        self.assertEqual(params, (["nominala"], "depozite"))

    def test_paginile_folosesc_celulele(self):
        apeluri = []
        server.celule_matrice, vechi_m = (lambda *a: apeluri.append(("m",) + a) or ["M"]), server.celule_matrice
        server.celule_rate, vechi_r = (lambda *a: apeluri.append(("r",) + a) or ["R"]), server.celule_rate
        # `rate` citește și meniul de filtre (luni, produs) din aceeași interogare falsă
        server.interoghează = lambda sql, params=None: [{"n": 0, "luni": None, "produs": "altele"}]
        try:
            m = server.matrice({"grup": ["carduri"], "segment": ["pj"], "unitate": ["eur"]})
            r = server.rate({"categorie": ["credite"], "termen": ["lung"], "produs": ["ipotecar"]})
        finally:
            server.celule_matrice, server.celule_rate = vechi_m, vechi_r
        self.assertEqual((m["celule"], r["celule"]), (["M"], ["R"]))
        self.assertEqual(apeluri, [("m", server.GRUPURI["carduri"]["campuri"], "eur", "pj"),
                                   ("r", server.GRUPURI_RATE["credite"]["campuri"], "credite", "lung", "ipotecar")])
```

- [ ] **Step 3: rulează, trebuie să pice**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe app/test_celula.py`
Expected: ERROR `AttributeError: module 'server' has no attribute 'celule_matrice'` (și `celule_rate`) la testele noi; cele 9 vechi trec.

- [ ] **Step 4: implementarea (mutare, fără schimbarea SQL-ului)**

În `app/server.py`, înaintea lui `def matrice(q):`:

```python
def celule_matrice(campuri, unitate, segment):
    """Celulele matricei din 2.1 (bancă × concept): câte valori, intervalul, câte gratuite și rândul de
    la mediană. Le folosesc 2.1, Versus, fișa de bancă și clasamentele din Vox: o singură interogare,
    deci aceleași cifre peste tot."""
    filtru_seg = "" if segment == "toate" else f" AND ({COND_SEG})"
    p_seg = () if segment == "toate" else (segment,)
    PLAUZIBIL = PRAGURI["suma"]
    # <aici se mută, neschimbat, comentariul „Valoarea reprezentativa + CE reprezinta …” din matrice>
    return interoghează(
        f"""WITH randuri AS (
        <aici se mută, caracter cu caracter, interogarea `celule` din matrice, de la „WITH randuri AS (”
         până la „FROM agregat a JOIN reprezentativ r USING (banca, camp)”>""",
        (campuri, unitate) + p_seg,
    )
```

iar în `matrice`, după calculul lui `PLAUZIBIL` (care rămâne, cu comentariul lui, pentru celelalte interogări), atribuirea `celule = interoghează(…)` devine:

```python
    celule = celule_matrice(campuri, unitate, segment)
```

Înaintea lui `def rate(q):`:

```python
def _filtre_rate(termen, produs):
    """Filtrele de termen și tip de credit din 2.2, ca text SQL și parametri."""
    filtru = ""
    if termen in TERMENE:
        filtru += f" AND {TERMEN_LUNI} {TERMENE[termen][1]}"
    elif termen == "necunoscut":
        filtru += f" AND {TERMEN_LUNI} IS NULL"
    if produs in PRODUSE_CREDIT:
        filtru += f" AND {PRODUS_CREDIT} = %s"
    return filtru, ((produs,) if produs in PRODUSE_CREDIT else ())


def _baza_rate(prag):
    return f"""FROM observatii_curente o
                  JOIN surse s ON s.id = o.id_sursa
                  JOIN banci b ON b.id = s.id_banca
                  WHERE o.unitate = 'procent' AND o.camp = ANY(%s)
                    AND split_part(o.cod_scenariu, '|', 1) = %s
                    AND NOT o.ambiguu AND o.valoare_num IS NOT NULL
                    AND o.valoare_num <= {prag}"""


def celule_rate(campuri, categorie, termen, produs):
    """Celulele din 2.2 (bancă × concept, pe o categorie), cu termenul și tipul de credit: câte valori,
    intervalul și rândul de la mediană. Le folosesc 2.2, Versus și clasamentele din Vox."""
    filtru, p_extra = _filtre_rate(termen, produs)
    baza_cat = _baza_rate(GRUPURI_RATE[categorie]["prag"])
    return interoghează(
        f"""WITH randuri AS (
        <aici se mută, caracter cu caracter, interogarea `celule` din rate, cu comentariul despre mediană>""",
        (campuri, categorie) + p_extra,
    )
```

iar în `rate`, blocul care construia `filtru` și `p_extra` dispare, `baza_cat = _baza_rate(prag)` ia locul șirului scris de mână, și `"celule": interoghează(…)` devine `"celule": celule_rate(campuri, categorie, termen, produs)`.

- [ ] **Step 5: testele trec, paginile neschimbate**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe app/test_celula.py && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe "$S/verifica_celule_db.py" dupa`
Expected: `OK` (14 teste); `49 identice din 49`.

- [ ] **Step 6: commit**

```bash
printf '%s\n' "app: celulele din 2.1 și 2.2 se calculează într-un singur loc (celule_matrice, celule_rate)" "" "Clasamentele din Vox trebuie să dea aceleași cifre ca 2.1 și Versus; interogarea e mutată neschimbată, iar cele 49 de apeluri matrice/rate dau aceleași rezultate (mip_merge, 07.10.2026)." > "$S/msg_c1.txt"
git add app/server.py app/test_celula.py && git commit -F "$S/msg_c1.txt"
```

---

### Task 2: cititorii serverului pentru clasamente

**Files:**
- Modify: `app/server.py` (`_clasament_vox` și `_stare_banci_vox` după `_stare_banca_vox`, care trece prin `_stare_banci_vox`; `_context_vox` primește `clasabile`; `VOX` primește cititorii)
- Test: `app/test_vox.py` (clasa `StareBanca` primește `slug` în rândurile false; clasa nouă `CititoriClasament` după ea)
- Script: `SCRATCH/verifica_clasament_db.py`

**Interfaces:**
- Consumes: `celule_matrice`, `celule_rate` (Task 1).
- Produces: `_clasament_vox(concept, categorie, termen, produs, segment) -> dict | None` = `{"sursa": "matrice"|"rate", "grup": str, "unitate": "lei"|"procent", "sens": "mic_bun"|"mare_bun", "segment": str|None, "blocuri": [{"tip": "exact"|"nespecificat", "termen": str, "produs": str, "celule": list}]}`; `_stare_banci_vox(banca=None) -> dict[slug, {"stare", "surse", "robots", "refuzate", "pdf"}]`; `_context_vox()["clasabile"] = {"comisioane": list[str], "dobanzi": dict[str, list[str]]}`.

- [ ] **Step 1: testele care pică**

În `class StareBanca`, rândurile false primesc `slug` (interogarea grupează pe bancă):

```python
    def stare(self, numere):
        self.server.interoghează = lambda sql, params=None: self.cereri.append((sql, params)) or [{"slug": "ing", **numere}]
        return self.server._stare_banca_vox("ing")
```

și, după `StareBanca`:

```python
class CititoriClasament(unittest.TestCase):
    """Cititorii din server pentru clasamente: sursa celulelor, blocurile, motivul pe toate băncile."""

    def setUp(self):
        import server
        self.s, self.apeluri = server, []
        self.vechi = (server.celule_matrice, server.celule_rate, server.interoghează)
        server.celule_matrice = lambda *a: self.apeluri.append(("m",) + a) or [{"banca": "bcr"}]
        server.celule_rate = lambda *a: self.apeluri.append(("r",) + a) or [{"banca": "ing"}]

    def tearDown(self):
        self.s.celule_matrice, self.s.celule_rate, self.s.interoghează = self.vechi

    def test_comision_pe_pf_implicit(self):
        c = self.s._clasament_vox("administrare_cont", None, None, None, None)
        self.assertEqual((c["sursa"], c["grup"], c["unitate"], c["sens"], c["segment"]),
                         ("matrice", "cont_curent", "lei", "mic_bun", "pf"))
        self.assertEqual(c["blocuri"], [{"tip": "exact", "termen": "", "produs": "", "celule": [{"banca": "bcr"}]}])
        self.assertEqual(self.apeluri, [("m", ["administrare_cont"], "lei", "pf")])

    def test_comision_segment_cerut_sau_necunoscut(self):
        self.s._clasament_vox("emitere_card", None, None, None, "pj")
        self.s._clasament_vox("emitere_card", None, None, None, "PF")
        self.assertEqual([a[3] for a in self.apeluri], ["pj", "pf"])

    def test_dobanda_cu_termen_doua_blocuri(self):
        """Pe 7–12 luni doar 2 bănci au termenul scris în sursă, 9 au dobânzi fără termen (07.10.2026):
        al doilea bloc le arată separat, fără să amestece termenele."""
        c = self.s._clasament_vox("nominala", "depozite", "12", None, None)
        self.assertEqual((c["sursa"], c["grup"], c["unitate"], c["sens"]), ("rate", "depozite", "procent", "mare_bun"))
        self.assertEqual([(b["tip"], b["termen"], b["produs"]) for b in c["blocuri"]],
                         [("exact", "12", ""), ("nespecificat", "necunoscut", "")])
        self.assertEqual(self.apeluri, [("r", ["nominala"], "depozite", "12", ""),
                                        ("r", ["nominala"], "depozite", "necunoscut", "")])

    def test_credit_cu_produs(self):
        c = self.s._clasament_vox("dae", "credite", None, "ipotecar", None)
        self.assertEqual([(b["tip"], b["termen"], b["produs"]) for b in c["blocuri"]],
                         [("exact", "", "ipotecar"), ("nespecificat", "", "altele")])

    def test_dobanda_fara_filtre_un_bloc(self):
        c = self.s._clasament_vox("dae", "credite", None, None, None)
        self.assertEqual(len(c["blocuri"]), 1)

    def test_neclasabil(self):
        for args in (("schimbare_pin", None, None, None, None), ("nominala", None, None, None, None),
                     ("dae", "depozite", None, None, None), (None, None, None, None, None)):
            self.assertIsNone(self.s._clasament_vox(*args), args)
        self.assertEqual(self.apeluri, [])

    def test_stare_pe_toate_bancile(self):
        self.s.interoghează = lambda sql, params=None: [
            {"slug": "ing", "surse": 158, "blocate": 48, "robots": 48, "pdf": 48},
            {"slug": "cec", "surse": 1, "blocate": 1, "robots": 0, "pdf": 0}]
        s = self.s._stare_banci_vox()
        self.assertEqual(s["ing"], {"stare": None, "surse": 158, "robots": 48, "refuzate": 0, "pdf": 48})
        self.assertEqual(s["cec"]["stare"], "blocata")

    def test_context_clasabile_din_grupuri(self):
        self.s.interoghează = lambda sql, params=None: []
        cl = self.s._context_vox()["clasabile"]
        self.assertEqual(len(cl["comisioane"]), 14)
        self.assertIn("administrare_cont", cl["comisioane"])
        self.assertEqual(cl["dobanzi"]["dae"], ["credite"])
        self.assertEqual(cl["dobanzi"]["nominala"], ["conturi_carduri", "credite", "depozite"])
```

- [ ] **Step 2: rulează, trebuie să pice**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe app/test_vox.py`
Expected: ERROR la `CititoriClasament` (`_clasament_vox`, `_stare_banci_vox` lipsesc; `KeyError: 'clasabile'`); `StareBanca` pică (interogarea veche nu citește `slug`).

- [ ] **Step 3: implementarea**

`_stare_banca_vox` și funcțiile noi:

```python
_SQL_STARE_BANCI = """SELECT b.slug, count(s.id)::int AS surse,
                  count(s.id) FILTER (WHERE s.status = 'blocat')::int AS blocate,
                  count(s.id) FILTER (WHERE s.status = 'blocat'
                                        AND s.nota_extractie LIKE 'ROBOTS%%')::int AS robots,
                  count(s.id) FILTER (WHERE s.status = 'blocat' AND s.format = 'pdf')::int AS pdf
           FROM banci b LEFT JOIN surse s ON s.id_banca = b.id
           {unde}
           GROUP BY b.slug"""


def _stare_banci_vox(banca=None):
    """De ce n-are o bancă valori, din `surse`: nicio sursă, toate blocate (WAF, robots.txt), sau câte
    sunt blocate și de ce. ING avea 48 de PDF-uri interzise de robots.txt din 158 de surse, printre
    ele lista de taxe și comisioane, iar fișa spunea doar „nu avem valori” (mip_merge, 07.10.2026). O
    interogare pentru toate băncile: clasamentele arată motivul fiecărei bănci fără date. Nota
    `ROBOTS: …` o scrie `ingest/populare_initiala.py`."""
    rows = interoghează(_SQL_STARE_BANCI.format(unde="WHERE b.slug = %s" if banca else ""),
                        (banca,) if banca else ())
    return {x["slug"]: {"stare": "fara_surse" if x["surse"] == 0 else "blocata" if x["blocate"] == x["surse"] else None,
                        "surse": x["surse"], "robots": x["robots"], "refuzate": x["blocate"] - x["robots"],
                        "pdf": x["pdf"]}
            for x in rows}


def _stare_banca_vox(banca):
    return _stare_banci_vox(banca).get(banca)


def _clasament_vox(concept, categorie, termen, produs, segment):
    """Celulele unui clasament, din aceleași interogări ca 2.1 și 2.2: un comision în lei pe un segment
    (PF dacă întrebarea nu-l spune, ca Versus), sau o dobândă pe o categorie. Cu termen sau tip de
    credit, al doilea bloc are valorile la care sursa nu le spune: pe 7–12 luni doar 2 bănci au termenul
    scris, 9 au dobânzi fără termen (mip_merge, 07.10.2026). None = conceptul nu se poate clasa."""
    grup = next((g for g, v in GRUPURI.items() if concept in v["campuri"]), None)
    if grup:
        seg = segment if segment in vox.ORDINE_SEGMENT else "pf"
        return {"sursa": "matrice", "grup": grup, "unitate": "lei", "sens": GRUPURI[grup]["sens"],
                "segment": seg,
                "blocuri": [{"tip": "exact", "termen": "", "produs": "",
                             "celule": celule_matrice([concept], "lei", seg)}]}
    if categorie not in GRUPURI_RATE or concept not in GRUPURI_RATE[categorie]["campuri"]:
        return None
    termen, produs = termen or "", produs or ""
    blocuri = [{"tip": "exact", "termen": termen, "produs": produs,
                "celule": celule_rate([concept], categorie, termen, produs)}]
    if (termen and termen != "necunoscut") or (produs and produs != "altele"):
        t2, p2 = ("necunoscut" if termen else ""), ("altele" if produs else "")
        blocuri.append({"tip": "nespecificat", "termen": t2, "produs": p2,
                        "celule": celule_rate([concept], categorie, t2, p2)})
    return {"sursa": "rate", "grup": categorie, "unitate": "procent",
            "sens": GRUPURI_RATE[categorie]["sens"], "segment": None, "blocuri": blocuri}
```

În `_context_vox`, în dicționarul întors:

```python
        # ce se poate clasa: conceptele matricelor din 2.1 (comisioane, în lei) și din 2.2 (dobânzi, pe
        # categorie), deci clasamentul folosește exact celulele paginilor
        "clasabile": {
            "comisioane": sorted({c for g in GRUPURI.values() for c in g["campuri"]}),
            "dobanzi": {c: sorted(k for k, v in GRUPURI_RATE.items() if c in v["campuri"])
                        for c in sorted({c for v in GRUPURI_RATE.values() for c in v["campuri"]})},
        },
```

`VOX` primește cititorii (parametrii noi ai lui `Vox` vin în Task 3; până atunci serverul nu-i transmite):
în Task 3, pasul 3, `VOX = vox.Vox(context=_context_vox, cauta=_cauta_vox, stare_banca=_stare_banca_vox, clasament=_clasament_vox, stare_banci=_stare_banci_vox)`.

- [ ] **Step 4: testele trec**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe app/test_vox.py && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe app/test_celula.py`
Expected: `OK` la amândouă.

- [ ] **Step 5: pe `mip_merge`**

`SCRATCH/verifica_clasament_db.py`:

```python
"""_clasament_vox dă exact celulele din 2.1 / 2.2; _stare_banci_vox = _stare_banca_vox (07.10.2026)."""
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
RAD = r"C:\Users\nicolae.cherascu\Desktop\Market-Intelligence-Platform"
os.chdir(RAD); sys.path.insert(0, os.path.join(RAD, "app"))
import server

ctx = server._context_vox()
cl, rau = ctx["clasabile"], 0
for c in cl["comisioane"]:
    for seg in ("pf", "pj"):
        grup = next(g for g, v in server.GRUPURI.items() if c in v["campuri"])
        din_matrice = [x for x in server.matrice({"grup": [grup], "segment": [seg], "unitate": ["lei"]})["celule"] if x["camp"] == c]
        if server._clasament_vox(c, None, None, None, seg)["blocuri"][0]["celule"] != din_matrice:
            rau += 1; print("DIFERIT comision", c, seg)
for c, cats in cl["dobanzi"].items():
    for cat in cats:
        for termen, produs in (("", ""), ("12", ""), ("", "ipotecar")):
            din_rate = [x for x in server.rate({"categorie": [cat], "termen": [termen], "produs": [produs]})["celule"] if x["camp"] == c]
            if server._clasament_vox(c, cat, termen, produs, None)["blocuri"][0]["celule"] != din_rate:
                rau += 1; print("DIFERIT dobândă", c, cat, termen, produs)
stari = server._stare_banci_vox()
rau += sum(stari[b["slug"]] != server._stare_banca_vox(b["slug"]) for b in ctx["banci"])
print("clasabile:", len(cl["comisioane"]), "comisioane,", len(cl["dobanzi"]), "dobânzi;", "diferențe:", rau)
c = server._clasament_vox("nominala", "depozite", "12", None, None)
print("depozit 12 luni:", [len(b["celule"]) for b in c["blocuri"]], "bănci în blocuri")
```

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe "$S/verifica_clasament_db.py"`
Expected: `clasabile: 14 comisioane, 4 dobânzi; diferențe: 0`; `depozit 12 luni: [2, 9] bănci în blocuri`.

- [ ] **Step 6: commit**

```bash
printf '%s\n' "app: cititorii pentru clasamentele Vox (_clasament_vox, motivul pe toate băncile, conceptele clasabile)" "" "Celulele vin din celule_matrice / celule_rate, deci aceleași cifre ca 2.1 și 2.2; pe 7–12 luni doar 2 bănci au termenul scris în sursă, iar al doilea bloc le arată pe cele 9 fără termen (mip_merge, 07.10.2026)." > "$S/msg_c2.txt"
git add app/server.py app/test_vox.py && git commit -F "$S/msg_c2.txt"
```

---

### Task 3: contractul cu modelul și clasamentul în `vox.py`

**Files:**
- Modify: `app/vox.py` (`TIPURI`, `CHEI`, `METRICI`, `_gol`, `schema`, `prompt`, `valideaza`, `_ordine_segment`, `rezuma`, `clasa`, `Vox.__init__`, `Vox._clasament_raspuns`, `Vox.intreaba`, `Vox._raspuns`)
- Modify: `app/server.py` (`VOX` cu cititorii noi)
- Test: `app/test_vox.py` (`CTX` cu `dae` și `clasabile`; `Schema`, `Validare`, `Rezumat`, `Intrebari`, clasa nouă `Clasa`)

**Interfaces:**
- Consumes: `_clasament_vox`, `_stare_banci_vox`, `clasabile` (Task 2).
- Produces: interpretarea are în plus `segment` și `metrica`; `clasa(celule, sens, metrica, evidentiate, nume) -> list[dict]` (`loc`, `loc_pana`, `banca`, `valoare`, `minim`, `maxim`, `n`, `serviciu`, `frecventa`, `conditie`, `segment_necunoscut`, `evidentiata`); răspunsul are cheia `clasament` (`None` la alte tipuri) = `{concept, sursa, grup, unitate, sens, metrica, segment, categorie, termen, produs, blocuri: [{tip, termen, produs, randuri}], libra: {loc, loc_pana, din} | None, fara_date: [{banca, stare, surse, robots, refuzate, pdf}]}` sau `{concept, text, neclasabil: True}`.

- [ ] **Step 1: testele care pică**

`CTX` primește conceptul `dae` (după `nominala`) și conceptele clasabile:

```python
        {"camp": "dae", "n": 120, "unitati": ["procent"], "categorii": ["credite"],
         "exemple": ["DAE credit ipotecar"]},
    ],
```

```python
    "clasabile": {"comisioane": ["administrare_cont"],
                  "dobanzi": {"dae": ["credite"], "nominala": ["conturi_carduri", "credite", "depozite"]}},
```

În `Schema.test_enum_din_liste`: `["administrare_cont", "nominala", "dae"]`, plus:

```python
        self.assertEqual(p["tip"]["enum"], list(vox.TIPURI))
        self.assertEqual(p["segment"]["anyOf"][0]["enum"], list(vox.ORDINE_SEGMENT))
        self.assertEqual(p["metrica"]["anyOf"][0]["enum"], list(vox.METRICI))
```

În `Schema.test_prompt_contine_listele_si_regula`, înainte de ultima aserțiune:

```python
        # „Care bancă are cel mai mic comision?” era refuzată de 3 ori în octombrie: clasamentul are tipul lui
        self.assertIn("tip = clasament", text)
        self.assertIn("Clasabile: comisioane (în lei): administrare_cont; dobânzi (cu categoria): dae (credite)", text)
        self.assertNotIn("clasamente de tipul", text)
```

În `Validare`, la final:

```python
    def test_clasament_bun_fara_banci(self):
        curat, _ = vox.valideaza(interp(tip="clasament", banci=[], segment="pj", metrica="cea_mai_buna"), CTX)
        self.assertEqual((curat["tip"], curat["banci"], curat["segment"], curat["metrica"]),
                         ("clasament", [], "pj", "cea_mai_buna"))

    def test_clasament_dobanda_categoria_implicita_sau_neclar(self):
        """`dae` e doar la credite; `nominala` e și depozit, și credit: fără categorie, un clasament ar
        amesteca 6,5% la depozit cu 9,9% la ipotecar."""
        curat, _ = vox.valideaza(interp(tip="clasament", banci=[], concept="dae"), CTX)
        self.assertEqual((curat["tip"], curat["categorie"]), ("clasament", "credite"))
        curat, _ = vox.valideaza(interp(tip="clasament", banci=[], concept="nominala"), CTX)
        self.assertEqual(curat["tip"], "neclar")

    def test_clasament_fara_concept_dar_cu_text_ramane_clasament(self):
        curat, _ = vox.valideaza(interp(tip="clasament", banci=[], concept=None, text_cautat="datoria vamală"), CTX)
        self.assertEqual(curat["tip"], "clasament")
        self.assertEqual(vox.valideaza(interp(tip="clasament", banci=[], concept=None), CTX)[0]["tip"], "neclar")

    def test_segment_si_metrica_necunoscute(self):
        for rau in (interp(segment="firme"), interp(metrica="maxim")):
            self.assertEqual(vox.valideaza(rau, CTX)[0]["tip"], "neclar", rau)

    def test_anterior_vechi_fara_campurile_noi(self):
        """O conversație salvată înainte de 07.10.2026 are interpretări fără `segment` și `metrica`."""
        vechi = {k: v for k, v in interp().items() if k not in ("segment", "metrica")}
        self.assertEqual(vox.verifica_anterior(vechi)["segment"], None)
```

În `Rezumat`, la final:

```python
    def test_segmentul_cerut_primul(self):
        """„… pentru firme la BCR?” arată grupa PJ prima; celelalte rămân, în ordinea obișnuită."""
        r = vox.rezuma([dict(rand(5), segment="pf"), dict(rand(30), segment="pj"), rand(7)], primul="pj")
        self.assertEqual([g["segment"] for g in r], ["pj", "pf", None])
```

Clasa nouă, după `Rezumat`:

```python
class Clasa(unittest.TestCase):
    NUME = {"bcr": "BCR", "brd": "BRD", "ing": "ING Bank", "libra": "Libra Internet Bank"}

    def celula(self, banca, valoare, minim=None, maxim=None):
        return {"banca": banca, "camp": "x", "n": 3, "valoare": valoare,
                "minim": valoare if minim is None else minim, "maxim": valoare if maxim is None else maxim,
                "serviciu": f"serviciu {banca}", "frecventa": "lunar", "conditie": None, "segment_necunoscut": False}

    def test_comision_crescator_depozit_descrescator(self):
        c = [self.celula("bcr", 8.5), self.celula("brd", 3), self.celula("ing", 5)]
        self.assertEqual([r["banca"] for r in vox.clasa(c, "mic_bun", "mediana", set(), self.NUME)], ["brd", "ing", "bcr"])
        self.assertEqual([r["banca"] for r in vox.clasa(c, "mare_bun", "mediana", set(), self.NUME)], ["bcr", "ing", "brd"])

    def test_egalitati_loc_comun(self):
        """La administrarea contului PF, 7 din 14 bănci au mediana 0 lei (mip_merge, 07.10.2026):
        „Libra pe locul 4” ar fi un loc arbitrar."""
        r = vox.clasa([self.celula("libra", 0), self.celula("bcr", 8.5), self.celula("brd", 0)],
                      "mic_bun", "mediana", {"libra"}, self.NUME)
        self.assertEqual([(x["banca"], x["loc"], x["loc_pana"], x["evidentiata"]) for x in r],
                         [("brd", 1, 2, False), ("libra", 1, 2, True), ("bcr", 3, 3, False)])

    def test_cea_mai_buna_varianta(self):
        c = [self.celula("bcr", 8.5, minim=0, maxim=35), self.celula("brd", 3, minim=1, maxim=5)]
        r = vox.clasa(c, "mic_bun", "cea_mai_buna", set(), self.NUME)
        self.assertEqual([(x["banca"], x["valoare"], x["serviciu"]) for x in r], [("bcr", 0, None), ("brd", 1, None)])
        r = vox.clasa(c, "mare_bun", "cea_mai_buna", set(), self.NUME)
        self.assertEqual([(x["banca"], x["valoare"]) for x in r], [("bcr", 35), ("brd", 5)])
```

În `Intrebari`, `fa` primește cititorii (cu valori implicite) și testele noi la final:

```python
    def fa(self, client, stare_banca=lambda b: None, clasament=None, stare_banci=lambda: {}):
        def cauta(banca, concept, categorie, termen, produs, text):
            self.cautari.append((banca, concept, categorie, termen, produs, text))
            return self.randuri.get(banca, [])
        return vox.Vox(context=lambda: CTX, cauta=cauta, stare_banca=stare_banca,
                       clasament=clasament, stare_banci=stare_banci, client=client, dir_jurnal=self.dir)
```

```python
    def celule_clasament(self, *args):
        self.cautari.append(args)
        cel = lambda b, v: {"banca": b, "camp": "administrare_cont", "n": 2, "valoare": v, "minim": v, "maxim": v,
                            "serviciu": None, "frecventa": None, "conditie": None, "segment_necunoscut": False}
        return {"sursa": "matrice", "grup": "cont_curent", "unitate": "lei", "sens": "mic_bun", "segment": "pf",
                "blocuri": [{"tip": "exact", "termen": "", "produs": "", "celule": [cel("bcr", 8.5), cel("libra", 0)]}]}

    def test_clasament(self):
        stari = {"brd": {"stare": "blocata", "surse": 1, "robots": 0, "refuzate": 1, "pdf": 0}}
        d = self.fa(ClientFals(interp(tip="clasament", banci=[])), clasament=self.celule_clasament,
                    stare_banci=lambda: stari).intreaba("Care bancă are cel mai mic comision de administrare?")
        c = d["clasament"]
        self.assertEqual((d["raspunsuri"], c["metrica"], c["segment"], c["libra"]),
                         ([], "mediana", "pf", {"loc": 1, "loc_pana": 1, "din": 2}))
        self.assertEqual([(r["banca"], r["loc"]) for r in c["blocuri"][0]["randuri"]], [("libra", 1), ("bcr", 2)])
        self.assertEqual([f["banca"] for f in c["fara_date"]], ["brd", "ing"])
        self.assertEqual(c["fara_date"][0]["stare"], "blocata")
        self.assertEqual(self.cautari, [("administrare_cont", None, None, None, None)])

    def test_clasament_neclasabil(self):
        d = self.fa(ClientFals(interp(tip="clasament", banci=[], concept=None, text_cautat="datoria vamală")),
                    clasament=lambda *a: None).intreaba("Cine are cel mai mic comision la vamă?")
        self.assertEqual(d["clasament"], {"concept": None, "text": "datoria vamală", "neclasabil": True})

    def test_cautare_fara_clasament(self):
        self.assertIsNone(self.fa(ClientFals(interp())).intreaba("BCR?")["clasament"])

    def test_cautare_segmentul_cerut_primul(self):
        self.randuri["bcr"] = [dict(rand(1), segment="pf"), dict(rand(2), segment="pj")]
        r = self.fa(ClientFals(interp(segment="pj"))).intreaba("BCR, firme?")["raspunsuri"][0]
        self.assertEqual([x["segment"] for x in r["randuri"]], ["pj", "pf"])
        self.assertEqual([g["segment"] for g in r["rezumat"]], ["pj", "pf"])
```

- [ ] **Step 2: rulează, trebuie să pice**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe app/test_vox.py`
Expected: FAIL/ERROR la testele noi (`segment`, `metrica`, `clasa`, `clasament` lipsesc; `Vox()` nu primește `clasament`).

- [ ] **Step 3: implementarea**

`app/vox.py`:

```python
TIPURI = ("cautare", "clasament", "neclar", "in_afara")
CHEI = ("tip", "banci", "concept", "categorie", "termen", "produs_credit", "text_cautat", "clarificare",
        "segment", "metrica")
# „cea mai ieftină variantă” cere cea mai bună valoare a fiecărei bănci, nu mediana: decizia lui
# Nicolae, 07.10.2026; mediana rămâne implicită, ca în 2.1 și Versus
METRICI = ("mediana", "cea_mai_buna")
```

`_gol` întoarce și `"segment": None, "metrica": None`.

`schema`: în `properties`, după `text_cautat`:

```python
            "segment": optional(ORDINE_SEGMENT),
            "metrica": optional(METRICI),
```

`prompt`: lista `linii` devine (regulile vechi rămân, cu modificările marcate):

```python
    linii = [
        "Ești interpretul paginii Vox din Marketing Command Center (Libra Bank).",
        "Utilizatorul întreabă, în română sau în engleză, despre o valoare publicată de o bancă din "
        "România (un comision, o dobândă, o limită) sau compară băncile între ele pe o astfel de valoare.",
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
        "- tip = neclar: lipsește banca sau nu se înțelege ce valoare; scrie atunci în clarificare "
        "o întrebare scurtă, în limba utilizatorului. O întrebare fără bancă și fără comparație "
        "(„Cât costă administrarea contului?”) e neclar.",
        "- tip = in_afara: orice altceva (aplicații, recenzii, campanii, sfaturi, texte de scris, "
        "întrebări generale).",
        # regula `concept`, cea despre servicii fără concept, cea despre `categorie` și cea despre
        # termenii englezești rămân neschimbate; la `categorie` se adaugă:
        # "La un clasament de dobânzi categoria e obligatorie; dacă întrebarea n-o spune, tip = neclar, "
        # "cu o clarificare scurtă (depozit, credit sau cont?).",
        "- termen și produs_credit: doar dacă întrebarea le spune.",
        "- segment: pf (persoane fizice), pfa, imm, pj (firme, companii, persoane juridice); doar dacă "
        "întrebarea îl spune, altfel null.",
        "- metrica: cea_mai_buna dacă întrebarea cere cea mai ieftină sau cea mai avantajoasă variantă "
        "oferită („cea mai ieftină variantă”, „cel mai mic comision posibil”, „cea mai mare dobândă "
        "oferită”); altfel null.",
        # regula despre interpretarea anterioară rămâne; după ea:
        "- După un clasament, „și pentru firme?” rămâne clasament, cu alt segment; o bancă numită "
        "(„dar la BCR?”) face o căutare la acea bancă, pentru același concept.",
        "",
        "Băncile (slug: nume):",
    ]
```

și, la finalul funcției, înainte de `return`:

```python
    cl = ctx["clasabile"]
    linii.append("Clasabile: comisioane (în lei): " + ", ".join(cl["comisioane"]) + "; dobânzi (cu categoria): "
                 + "; ".join(f"{k} ({', '.join(v)})" for k, v in cl["dobanzi"].items()))
```

`valideaza`: `permise` primește `"segment": set(ORDINE_SEGMENT), "metrica": set(METRICI)`; după linia care curăță categoria, înaintea calculului `cu_ce`:

```python
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
```

`_ordine_segment` și `rezuma` primesc segmentul cerut:

```python
def _ordine_segment(segment, primul=None):
    if primul and segment == primul:
        return -1
    return ORDINE_SEGMENT.index(segment) if segment in ORDINE_SEGMENT else len(ORDINE_SEGMENT)
```

`rezuma(randuri, primul=None)`: cheia de sortare folosește `_ordine_segment(g["segment"], primul)`.

`clasa`, după `rezuma`:

```python
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
                "evidentiata": c["banca"] in evidentiate}
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
```

`Vox.__init__(self, context, cauta, stare_banca, client=None, dir_jurnal=DIR_JURNAL, dir_conversatii=None, clasament=None, stare_banci=None)` păstrează `self._clasament = clasament`, `self._stare_banci = stare_banci`. Metoda nouă:

```python
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
        primul = blocuri[0]["randuri"]
        libra = next(({"loc": r["loc"], "loc_pana": r["loc_pana"], "din": len(primul)}
                      for r in primul if r["banca"] == "libra"), None)
        cu_date = {r["banca"] for b in blocuri for r in b["randuri"]}
        stari = self._stare_banci() if self._stare_banci else {}
        fara_date = [{"banca": b["slug"], **(stari.get(b["slug"]) or {})}
                     for b in ctx["banci"] if b["slug"] not in cu_date]
        return {"concept": interp["concept"], "sursa": cel["sursa"], "grup": cel["grup"],
                "unitate": cel["unitate"], "sens": cel["sens"], "metrica": metrica, "segment": cel["segment"],
                "categorie": interp["categorie"], "termen": interp["termen"], "produs": interp["produs_credit"],
                "blocuri": blocuri, "libra": libra, "fara_date": fara_date}
```

În `Vox.intreaba`, în blocul `try` al răspunsurilor:

```python
            raspunsuri = [self._raspuns(b, interp) for b in interp["banci"]] if interp["tip"] == "cautare" else []
            clasament = self._clasament_raspuns(interp, ctx) if interp["tip"] == "clasament" else None
```

iar după `rand["randuri"] = …`:

```python
        if clasament and clasament.get("blocuri"):
            rand["clasate"] = len(clasament["blocuri"][0]["randuri"])
```

și `rezultat` primește `"clasament": clasament`.

În `Vox._raspuns`: ordonarea rândurilor devine `sorted(randuri, key=lambda r: _ordine_segment(r.get("segment"), interp["segment"]))`, iar rezumatul `rezuma(randuri, interp["segment"])`.

`app/server.py`: `VOX = vox.Vox(context=_context_vox, cauta=_cauta_vox, stare_banca=_stare_banca_vox, clasament=_clasament_vox, stare_banci=_stare_banci_vox)`.

- [ ] **Step 4: testele trec**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe app/test_vox.py && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe app/test_celula.py`
Expected: `OK` la amândouă.

- [ ] **Step 5: criteriile pe `mip_merge`, cu model fals**

`SCRATCH/raspunsuri_clasament.py` (ca `raspunsuri_noi.py`, cu `clasament=server._clasament_vox, stare_banci=server._stare_banci_vox` în `vox.Vox(…)`), cazurile:

```python
CAZURI = [
    ("Care bancă are cel mai mic comision de administrare?", i(tip="clasament", concept="administrare_cont")),
    ("Care e cea mai ieftină variantă de administrare a contului?", i(tip="clasament", concept="administrare_cont", metrica="cea_mai_buna")),
    ("și pentru firme?", i(tip="clasament", concept="administrare_cont", segment="pj")),
    ("Cine dă cea mai mare dobândă la depozitul pe 12 luni?", i(tip="clasament", concept="nominala", categorie="depozite", termen="12")),
    ("Unde stă Libra la DAE pentru creditul ipotecar?", i(tip="clasament", banci=["libra"], concept="dae", categorie="credite", produs_credit="ipotecar")),
    ("Care bancă are cel mai mic comision la decontarea datoriei vamale?", i(tip="clasament", text_cautat="datoria vamală")),
    ("Cât costă administrarea contului pentru firme la BCR?", i(banci=["bcr"], concept="administrare_cont", segment="pj")),
]
```

(funcția `i` primește și `segment=None, metrica=None` în dicționarul de bază). Scriptul tipărește, pe caz: `libra`, primele 8 rânduri `(banca, loc, loc_pana, valoare)`, câte rânduri are fiecare bloc, băncile fără date pe motiv; cu un argument, scrie răspunsurile în JSON.

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe "$S/raspunsuri_clasament.py" "$S/raspunsuri_clasament.json"`
Expected: administrare PF — 14 bănci, primele 7 pe `loc 1, loc_pana 7`, `libra {loc 1, loc_pana 7, din 14}`, Raiffeisen ultima (20.0); depozit 12 luni — blocuri `[2, 9]`; DAE ipotecar — `libra {loc 5, loc_pana 5, din 7}`; vamă — `neclasabil`; căutarea „pentru firme” — primul rând și prima grupă `pj`.

- [ ] **Step 6: commit**

```bash
printf '%s\n' "app: Vox face clasamente (tipul clasament, segment și metrica citite din întrebare)" "" "„Care bancă are cel mai mic comision?” era refuzată de 3 ori în octombrie; clasamentul folosește celulele din 2.1 / 2.2, cu locuri comune la egalitate (7 din 14 bănci la 0 lei pe administrarea contului PF, mip_merge, 07.10.2026)." > "$S/msg_c3.txt"
git add app/vox.py app/server.py app/test_vox.py && git commit -F "$S/msg_c3.txt"
```

---

### Task 4: evaluarea interpretării (plătită, cu buget)

**Files:**
- Modify: `app/vox_exemple.json` (exemplul 23 devine clasament; 10 exemple noi)
- Modify: `app/eval_vox.py` (cititorii falși pentru clasament; estimarea)

**Interfaces:**
- Consumes: contractul din Task 3.

- [ ] **Step 1: exemplele**

Exemplul 23 („Care bancă are cel mai mic comision de administrare?”) devine `{"tip": "clasament", "concept": "administrare_cont", "segment": null, "metrica": null}`. Exemple noi, la final (`ANT` = interpretarea clasamentului de administrare: `{"tip": "clasament", "banci": [], "concept": "administrare_cont", "categorie": null, "termen": null, "produs_credit": null, "text_cautat": null, "clarificare": null, "segment": null, "metrica": null}`):

```json
  {"intrebare": "Cine dă cea mai mare dobândă la depozitul pe 12 luni?",
   "asteptat": {"tip": "clasament", "concept": "nominala", "categorie": "depozite", "termen": "12"}},
  {"intrebare": "Unde stă Libra la DAE pentru creditul ipotecar?",
   "asteptat": {"tip": "clasament", "banci": ["libra"], "concept": "dae", "categorie": "credite", "produs_credit": "ipotecar"}},
  {"intrebare": "Care e cea mai ieftină variantă de administrare a contului?",
   "asteptat": {"tip": "clasament", "concept": "administrare_cont", "metrica": "cea_mai_buna"}},
  {"intrebare": "Which bank has the lowest card issuance fee?",
   "asteptat": {"tip": "clasament", "concept": "emitere_card"}},
  {"intrebare": "Clasamentul băncilor la retragerea de numerar de la ATM",
   "asteptat": {"tip": "clasament", "concept": "retragere_numerar"}},
  {"intrebare": "Ce bancă are cea mai mică dobândă la creditul de nevoi personale?",
   "asteptat": {"tip": "clasament", "concept": "nominala", "categorie": "credite", "produs_credit": "nevoi_personale"}},
  {"intrebare": "și pentru firme?", "anterior": ANT,
   "asteptat": {"tip": "clasament", "concept": "administrare_cont", "segment": "pj"}},
  {"intrebare": "dar la BCR?", "anterior": ANT,
   "asteptat": {"tip": "cautare", "banci": ["bcr"], "concept": "administrare_cont"}},
  {"intrebare": "Cât costă administrarea contului pentru firme la BCR?",
   "asteptat": {"tip": "cautare", "banci": ["bcr"], "concept": "administrare_cont", "segment": "pj"}},
  {"intrebare": "Care bancă are cel mai mic comision la decontarea datoriei vamale?",
   "asteptat": {"tip": "clasament", "concept": null, "text_cautat_nenul": true}}
```

(`ANT` se scrie de fiecare dată întreg; JSON n-are referințe.)

- [ ] **Step 2: `eval_vox.py`**

`vox.Vox(context=server._context_vox, cauta=lambda *x: [], stare_banca=lambda b: None, clasament=lambda *x: None, stare_banci=lambda: {}, dir_jurnal=…)`: evaluarea e doar a interpretării.

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe app/eval_vox.py`
Expected: `40 întrebări, model claude-haiku-4-5, cost estimat ~$0.07` și „Fără --da nu se face niciun apel.”

- [ ] **Step 3: rularea plătită**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe app/eval_vox.py --da`
Expected: `40/40 corecte`, cost ~$0,07. La o greșeală: se corectează regula din `prompt` (cu testul ei în `test_prompt_contine_listele_si_regula`), `test_vox.py` trece, se rulează din nou — cel mult 3 rulări în total; costul fiecăreia intră în registru.

- [ ] **Step 4: commit**

```bash
printf '%s\n' "app: evaluarea Vox cu 10 întrebări de clasament (40 în total)" "" "<rezultatul și costul rulării, din ieșirea eval_vox.py>" > "$S/msg_c4.txt"
git add app/vox_exemple.json app/eval_vox.py app/vox.py app/test_vox.py && git commit -F "$S/msg_c4.txt"
```

---

### Task 5: fișa clasamentului în pagină

**Files:**
- Modify: `shared/src/vox.ts` (`Interpretare`: `tip` cu `clasament`, `segment`, `metrica`; `RandClasament`, `BlocClasament`, `Clasament`; `RaspunsIntrebare.clasament`)
- Create: `web/src/pages/vox/Clasament.tsx`
- Modify: `web/src/pages/Vox.tsx` (`Raspuns`: ramura clasament, cipul de segment; `anterior` și din clasamente)
- Modify: `web/src/i18n/dict/vox.ts` (`vox.clasament.*`, `vox.in_afara`, exemplul 6)
- Modify: `web/src/styles/vox.css`
- Script: `SCRATCH/verifica_clasament_ui.py`

**Interfaces:**
- Consumes: răspunsul din Task 3; `etSegment`, `CerereSertar.segment` (lucrarea anterioară).

- [ ] **Step 1: verificarea care pică (Playwright, pe :8797, înainte de modificări)**

`SCRATCH/verifica_clasament_ui.py`: ca `verifica_vox_ui.py` (GET/POST `/api/vox` răspunse din `raspunsuri_clasament.json`, restul spre :8797, cererile `/api/celula` ținute minte, pagină nouă pe temă și limbă), cu pașii:

```python
        fisa = intreaba(pg, "Care bancă are cel mai mic comision de administrare?")
        randuri = fisa.locator(".vox-clas tbody tr")
        print(f"[{tema}/{lang}] rânduri vizibile: {randuri.count()}; primul loc: {randuri.first.locator('td').first.inner_text()}")
        assert randuri.first.locator("td").first.inner_text() == "1–7"
        assert fisa.locator(".vox-clas tr.evidentiata").count() >= 1
        libra = fisa.locator(".vox-clas tr.evidentiata").first
        q = sertar(pg, libra.locator(".vox-link"))
        assert q.get("segment") == ["pf"] and "strict" not in q and q.get("unitate") == ["lei"], q
        assert "#/produse?grup=cont_curent&segment=pf" in fisa.locator("a.vox-clas-pagina").get_attribute("href")
        fisa.locator(".vox-clas-toate").click()
        assert fisa.locator(".vox-clas tbody tr").count() == 14
        print("   fără date:", fisa.locator(".vox-clas-fara").inner_text())
        # „și pentru firme?” trimite clasamentul ca `anterior`
        intreaba(pg, "și pentru firme?")
        assert ultimul_post["anterior"]["tip"] == "clasament", ultimul_post
        fisa = intreaba(pg, "Cine dă cea mai mare dobândă la depozitul pe 12 luni?")
        assert fisa.locator(".vox-clas").count() == 2
        q = sertar(pg, fisa.locator(".vox-clas").nth(1).locator(".vox-link").first)
        assert q.get("termen") == ["necunoscut"] and q.get("scenariu") == ["depozite"] and q.get("unitate") == ["procent"], q
        fisa = intreaba(pg, "Care bancă are cel mai mic comision la decontarea datoriei vamale?")
        print("   neclasabil:", fisa.inner_text()[:160])
```

(`intreaba` ține minte corpul ultimului POST în `ultimul_post`; conversațiile vechi și consola se verifică la fel ca în `verifica_vox_ui.py`.)

Run (serverul temporar pornit; `raspunsuri_clasament.json` din Task 3):
`PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe "$S/verifica_clasament_ui.py" "$S/raspunsuri_clasament.json" "$S"`
Expected: pică (fișa nu are `.vox-clas`).

- [ ] **Step 2: schemele**

`shared/src/vox.ts`:

```ts
export const Interpretare = z.object({
  tip: z.enum(['cautare', 'clasament', 'neclar', 'in_afara']),
  banci: z.array(z.string()),
  concept: z.string().nullable(),
  categorie: z.string().nullable(),
  termen: z.string().nullable(),
  produs_credit: z.string().nullable(),
  text_cautat: z.string().nullable(),
  clarificare: z.string().nullable(),
  /** lipsesc în conversațiile salvate înainte de clasamente (07.10.2026) */
  segment: z.string().nullable().optional(),
  metrica: z.enum(['mediana', 'cea_mai_buna']).nullable().optional(),
})

/** Un rând de clasament (app/vox.py, `clasa`). */
export const RandClasament = z
  .object({
    loc: z.number(), loc_pana: z.number(), banca: z.string(), valoare: z.number(),
    minim: z.number(), maxim: z.number(), n: z.number(),
    serviciu: z.string().nullable(), frecventa: z.string().nullable(), conditie: z.string().nullable(),
    segment_necunoscut: z.boolean().nullable().optional(), evidentiata: z.boolean(),
  })
  .passthrough()
export type RandClasament = z.infer<typeof RandClasament>

export const BlocClasament = z
  .object({ tip: z.enum(['exact', 'nespecificat']), termen: z.string(), produs: z.string(), randuri: z.array(RandClasament) })
  .passthrough()
export type BlocClasament = z.infer<typeof BlocClasament>

/** Clasamentul unei întrebări; `neclasabil` = conceptul nu are o cifră comparabilă între bănci. */
export const Clasament = z
  .object({
    concept: z.string().nullable(),
    text: z.string().nullable().optional(),
    neclasabil: z.boolean().optional(),
    sursa: z.enum(['matrice', 'rate']).optional(),
    grup: z.string().optional(),
    unitate: z.string().optional(),
    sens: z.enum(['mic_bun', 'mare_bun']).optional(),
    metrica: z.enum(['mediana', 'cea_mai_buna']).optional(),
    segment: z.string().nullable().optional(),
    categorie: z.string().nullable().optional(),
    termen: z.string().nullable().optional(),
    produs: z.string().nullable().optional(),
    blocuri: z.array(BlocClasament).optional(),
    libra: z.object({ loc: z.number(), loc_pana: z.number(), din: z.number() }).nullable().optional(),
    fara_date: z
      .array(z.object({
        banca: z.string(), stare: z.string().nullable().optional(), surse: z.number().optional(),
        robots: z.number().optional(), refuzate: z.number().optional(), pdf: z.number().optional(),
      }).passthrough())
      .optional(),
  })
  .passthrough()
export type Clasament = z.infer<typeof Clasament>
```

`RaspunsIntrebare` primește `clasament: Clasament.nullable().optional(),`.

- [ ] **Step 3: textele**

`web/src/i18n/dict/vox.ts`: `vox.exemplu_tip.6` → `["Clasament", "Ranking"]`; `vox.exemplu.6` → `["Care bancă are cel mai mic comision de administrare?", "Which bank has the lowest account maintenance fee?"]`; `vox.in_afara` → `["Răspund la valorile unei bănci (un comision sau o dobândă) și la clasamente între bănci. Aplicațiile, recenziile și campaniile nu sunt încă aici. De exemplu:", "I answer about a bank's values (a fee or an interest rate) and rank banks against each other. Apps, reviews and campaigns are not here yet. For example:"]`; cheile noi:

```ts
  "vox.clasament.chip": ["clasament", "ranking"],
  "vox.clasament.metrica.mediana": ["mediana (prețul obișnuit)", "median (the usual price)"],
  "vox.clasament.metrica.cea_mai_buna": ["cea mai bună variantă oferită", "best option offered"],
  "vox.clasament.sens": ["de la cel mai avantajos pentru client", "from the best deal for the customer"],
  "vox.clasament.n_banci_1": ["1 bancă cu date", "1 bank with data"],
  "vox.clasament.n_banci_n": ["{n} bănci cu date", "{n} banks with data"],
  "vox.clasament.libra": ["Libra: locul {loc} din {din}.", "Libra: rank {loc} of {din}."],
  "vox.clasament.libra_egal": ["Libra: locurile {loc}–{pana} din {din}, la egalitate.", "Libra: ranks {loc}–{pana} of {din}, tied."],
  "vox.clasament.libra_lipsa": ["Libra n-are valori aici.", "Libra has no values here."],
  "vox.clasament.col.loc": ["Loc", "Rank"],
  "vox.clasament.col.banca": ["Bancă", "Bank"],
  "vox.clasament.col.valoare": ["Valoare", "Value"],
  "vox.clasament.col.interval": ["Interval", "Range"],
  "vox.clasament.col.valori": ["Valori", "Values"],
  "vox.clasament.dovezi": ["Dovezi", "Evidence"],
  "vox.clasament.bloc.termen": ["Termen nespecificat în sursă", "Term not stated in the source"],
  "vox.clasament.bloc.produs": ["Tip de credit nespecificat în sursă", "Loan type not stated in the source"],
  "vox.clasament.bloc.ambele": ["Termen și tip de credit nespecificate în sursă", "Term and loan type not stated in the source"],
  "vox.clasament.fara_date": ["Fără date ({n}):", "No data ({n}):"],
  "vox.clasament.motiv.blocata": ["blocate", "blocked"],
  "vox.clasament.motiv.fara_surse": ["fără surse", "no sources"],
  "vox.clasament.motiv.robots": ["cu surse interzise de robots.txt", "with sources disallowed by robots.txt"],
  "vox.clasament.motiv.refuzate": ["cu surse refuzate de site", "with sources refused by the site"],
  "vox.clasament.motiv.fara_valoare": ["fără valoare în sursele colectate", "no value in the collected sources"],
  "vox.clasament.deschide_21": ["Deschide în 2.1 →", "Open in 2.1 →"],
  "vox.clasament.deschide_22": ["Deschide în 2.2 →", "Open in 2.2 →"],
  "vox.clasament.arata_toate": ["Arată toate ({n})", "Show all ({n})"],
  "vox.clasament.neclasabil": ["Pentru {concept} nu avem un clasament; întreabă de o bancă anume.", "We have no ranking for {concept}; ask about a specific bank."],
  "vox.clasament.gol": ["Nicio bancă nu are valori aici.", "No bank has values here."],
```

- [ ] **Step 4: componenta**

`web/src/pages/vox/Clasament.tsx`:

```tsx
import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { BlocClasament, Clasament as ClasamentT, RandClasament } from '@mcc/shared'
import type { Meta } from '../../api/meta'
import { EtichetaBanca } from '../../components/comune'
import type { CerereSertar } from '../../components/Sertar'
import { etNume, etSegment, unitTxt } from '../../components/valori'
import { areCheie, useLang, type DictKey } from '../../i18n'
import { num } from '../../util/format'

/**
 * Clasamentul unei întrebări din Vox (app/vox.py, `clasa`), cu celulele din 2.1 / 2.2: aceleași cifre
 * ca paginile. Primele 10 rânduri plus Libra și băncile numite; „Arată toate” pentru restul (cel mult
 * 15 bănci cu date pe un concept, mip_merge, 07.10.2026).
 */
const PRIMELE = 10

function eticheta(k: string, rezerva: string, t: (k: DictKey) => string): string {
  return areCheie(k) ? t(k) : rezerva
}

export default function Clasament({ c, m, onDovezi }: { c: ClasamentT; m: Meta; onDovezi: (q: CerereSertar) => void }) {
  const { t, tn } = useLang()
  if (c.neclasabil || !c.blocuri) {
    const ce = c.concept ? etNume(c.concept, t) : t('vox.text', { text: c.text ?? '' })
    return <p className="vox-nota"><span className="vox-punct" />{t('vox.clasament.neclasabil', { concept: ce })}</p>
  }
  const primul = c.blocuri[0]!
  const cap = [
    c.concept ? etNume(c.concept, t) : '',
    c.sursa === 'matrice' && c.segment ? etSegment(c.segment, t) : '',
    c.termen ? eticheta(`vox.termen.${c.termen}`, c.termen, t) : '',
    c.produs ? eticheta(`vox.produs.${c.produs}`, c.produs, t) : '',
    t(`vox.clasament.metrica.${c.metrica ?? 'mediana'}` as DictKey),
  ].filter(Boolean)
  const libra = c.libra
    ? c.libra.loc === c.libra.loc_pana
      ? t('vox.clasament.libra', { loc: c.libra.loc, din: c.libra.din })
      : t('vox.clasament.libra_egal', { loc: c.libra.loc, pana: c.libra.loc_pana, din: c.libra.din })
    : t('vox.clasament.libra_lipsa')
  const pagina = c.sursa === 'matrice'
    ? `/produse?grup=${c.grup}&segment=${c.segment ?? 'pf'}`
    : `/rate?categorie=${c.grup}${primul.termen ? `&termen=${primul.termen}` : ''}${primul.produs ? `&produs=${primul.produs}` : ''}`
  return (
    <div className="vox-fisa">
      <div className="vox-clas-antet">
        <b>{cap.join(' · ')}</b>
        <span className="vox-meta">{t('vox.clasament.sens')} · {tn('vox.clasament.n_banci', primul.randuri.length)}</span>
      </div>
      <p className="vox-nota"><span className="vox-punct gri" />{libra}</p>
      {c.blocuri.map((b, k) => <Bloc key={k} b={b} c={c} m={m} onDovezi={onDovezi} />)}
      <FaraDate c={c} m={m} />
      <Link className="vox-link vox-clas-pagina" to={pagina}>{t(c.sursa === 'matrice' ? 'vox.clasament.deschide_21' : 'vox.clasament.deschide_22')}</Link>
    </div>
  )
}

function Bloc({ b, c, m, onDovezi }: { b: BlocClasament; c: ClasamentT; m: Meta; onDovezi: (q: CerereSertar) => void }) {
  const { t, locale } = useLang()
  const [toate, setToate] = useState(false)
  const u = unitTxt(c.unitate, t)
  const titlu = b.tip === 'nespecificat'
    ? t(b.termen && b.produs ? 'vox.clasament.bloc.ambele' : b.termen ? 'vox.clasament.bloc.termen' : 'vox.clasament.bloc.produs')
    : null
  const vizibile = toate ? b.randuri : b.randuri.filter((r, i) => i < PRIMELE || r.evidentiata)
  // sertarul cere exact celula: la comisioane regula din 2.1 (segmentul plus rândurile nemarcate, fără
  // `strict`), la dobânzi categoria, termenul și tipul de credit ale blocului
  const cerere = (r: RandClasament): CerereSertar => c.sursa === 'matrice'
    ? { banca: r.banca, camp: c.concept!, unitate: 'lei', scenariu: '', segment: c.segment ?? 'pf' }
    : { banca: r.banca, camp: c.concept!, unitate: 'procent', scenariu: c.grup ?? '', termen: b.termen, produs: b.produs }
  if (!b.randuri.length) return <p className="vox-nota"><span className="vox-punct gri" />{titlu ? `${titlu}: ` : ''}{t('vox.clasament.gol')}</p>
  return (
    <div className="vox-clas-bloc">
      {titlu && <span className="vox-segment-cap">{titlu}</span>}
      <div className="vox-tabel-cutie">
        <table className="vox-tabel vox-clas">
          <thead>
            <tr>
              <th>{t('vox.clasament.col.loc')}</th>
              <th>{t('vox.clasament.col.banca')}</th>
              <th className="dr">{t('vox.clasament.col.valoare')}</th>
              <th className="dr">{t('vox.clasament.col.interval')}</th>
              <th className="dr">{t('vox.clasament.col.valori')}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {vizibile.map((r) => (
              <tr key={r.banca} className={r.evidentiata ? 'evidentiata' : undefined}>
                <td className="loc">{r.loc === r.loc_pana ? r.loc : `${r.loc}–${r.loc_pana}`}</td>
                <td><EtichetaBanca slug={r.banca} m={m} fisa tag /></td>
                <td className="dr val">
                  {num(r.valoare, locale)}{u}
                  {r.serviciu && <span className="sub">{r.serviciu}{r.frecventa ? ` · ${r.frecventa}` : ''}</span>}
                </td>
                <td className="dr">{r.minim === r.maxim ? '—' : `${num(r.minim, locale)} – ${num(r.maxim, locale)}`}</td>
                <td className="dr">{r.n}</td>
                <td><button type="button" className="vox-link" onClick={() => onDovezi(cerere(r))}>{t('vox.clasament.dovezi')}</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {b.randuri.length > vizibile.length && (
        <button type="button" className="vox-link vox-clas-toate" onClick={() => setToate(true)}>
          {t('vox.clasament.arata_toate', { n: b.randuri.length })}
        </button>
      )}
    </div>
  )
}

/** Băncile fără nicio valoare, grupate pe motiv (app/server.py, `_stare_banci_vox`). */
function FaraDate({ c, m }: { c: ClasamentT; m: Meta }) {
  const { t } = useLang()
  const fara = c.fara_date ?? []
  if (!fara.length) return null
  const grupe = new Map<string, string[]>()
  for (const f of fara) {
    const motiv = f.stare === 'blocata' ? 'blocata' : f.stare === 'fara_surse' ? 'fara_surse'
      : (f.robots ?? 0) > 0 ? 'robots' : (f.refuzate ?? 0) > 0 ? 'refuzate' : 'fara_valoare'
    grupe.set(motiv, [...(grupe.get(motiv) ?? []), m.nume[f.banca] ?? f.banca])
  }
  return (
    <p className="vox-nota vox-clas-fara">
      <span className="vox-punct gri" />
      <span>
        {t('vox.clasament.fara_date', { n: fara.length })}{' '}
        {[...grupe].map(([motiv, banci]) => `${banci.join(', ')} (${t(`vox.clasament.motiv.${motiv}` as DictKey)})`).join(' · ')}
      </span>
    </p>
  )
}
```

- [ ] **Step 5: pagina**

`web/src/pages/Vox.tsx`:
- import: `import Clasament from './vox/Clasament'`;
- `anterior` (linia cu `.find((x) => x.raspuns?.interpretare.tip === 'cautare')`) devine `.find((x) => ['cautare', 'clasament'].includes(x.raspuns?.interpretare.tip ?? ''))` — „și pentru firme?” continuă clasamentul;
- în `Raspuns`, `filtre` se calculează înaintea ramurilor `in_afara` / `neclar` și primește segmentul: `i.segment && etSegment(i.segment, t)`; după ramura `neclar`:

```tsx
  if (i.tip === 'clasament') {
    return (
      <article className="vox-card">
        <div className="vox-inteles">
          <span className="vox-et">{t('vox.am_inteles')}</span>
          <span className="vox-chip">{t('vox.clasament.chip')}</span>
          {i.banci.map((b) => <span key={b} className="vox-chip banca">{m.nume[b] ?? b}</span>)}
          <span className="vox-chip">{i.concept ? etNume(i.concept, t) : t('vox.text_chip', { text: i.text_cautat ?? '' })}</span>
          {filtre.map((f) => <span key={f} className="vox-chip">{f}</span>)}
          {i.metrica === 'cea_mai_buna' && <span className="vox-chip">{t('vox.clasament.metrica.cea_mai_buna')}</span>}
        </div>
        {r.clasament && <Clasament c={r.clasament} m={m} onDovezi={onDovezi} />}
        <div className="vox-card-jos">{subsol}</div>
      </article>
    )
  }
```

`web/src/styles/vox.css`, după regulile `.vox-segment`:

```css
/* clasamentele: rândul Libra și băncile numite, ca rândul Libra din tabelele aplicației (global.css) */
.vox-clas-antet { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 6px 12px }
.vox-clas-bloc { display: flex; flex-direction: column; gap: 6px }
.vox-clas td.loc { font-family: var(--mono); white-space: nowrap; color: var(--muted) }
.vox-clas tr.evidentiata td { background: var(--accent-tint) }
.vox-clas tr.evidentiata td:first-child { box-shadow: inset 4px 0 var(--accent) }
```

- [ ] **Step 6: typecheck și verificarea în pagină**

Run: `npm run typecheck` → 0 erori; apoi scriptul din pasul 1 → toate aserțiunile trec, „PROBLEME CONSOLĂ: niciuna”; capturile (BCR / depozit / neclasabil, ambele teme, RO și EN) se privesc. `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe "$S/verifica_vox_ui.py" "$S/raspunsuri_noi.json" "$S"` trece în continuare (căutările și conversațiile vechi).

- [ ] **Step 7: commit**

```bash
printf '%s\n' "web: fișa clasamentului în Vox (loc comun la egalitate, Libra evidențiată, dovezi pe rând, băncile fără date)" "" "Sertarul unui rând cere exact celula din 2.1 / 2.2, iar „și pentru firme?” continuă clasamentul: pagina lua interpretarea anterioară doar din căutări." > "$S/msg_c5.txt"
git add shared/src/vox.ts web/src/pages/vox/Clasament.tsx web/src/pages/Vox.tsx web/src/i18n/dict/vox.ts web/src/styles/vox.css && git commit -F "$S/msg_c5.txt"
```

---

### Task 6: testul cap-coadă cu modelul real (plătit, ~$0,03)

**Files:**
- Script: `SCRATCH/e2e_clasament.py`

- [ ] **Step 1: scriptul**

```python
"""Cap-coadă cu modelul real și baza reală (mip_merge), fără HTTP: Vox cu cititorii serverului și
jurnalul într-un dosar temporar, deci nimic în loguri/vox/. Costă (~$0,03)."""
import json, os, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
RAD = r"C:\Users\nicolae.cherascu\Desktop\Market-Intelligence-Platform"
os.chdir(RAD); sys.path.insert(0, os.path.join(RAD, "app"))
import server, vox

v = vox.Vox(context=server._context_vox, cauta=server._cauta_vox, stare_banca=server._stare_banca_vox,
            clasament=server._clasament_vox, stare_banci=server._stare_banci_vox,
            dir_jurnal=tempfile.mkdtemp(prefix="e2e_vox_"))
total, anterior, conv = 0.0, None, None
for q in ("Care bancă are cel mai mic comision de administrare?", "și pentru firme?", "dar la BCR?",
          "Cine dă cea mai mare dobândă la depozitul pe 12 luni?", "Unde stă Libra la DAE pentru creditul ipotecar?",
          "Which bank has the lowest card issuance fee?"):
    d = v.intreaba(q, anterior, conv)
    total += d["cost_usd"] or 0
    i, c = d["interpretare"], d["clasament"]
    anterior, conv = i, d["conversatie"]
    rez = ([(r["banca"], r["loc"], r["valoare"]) for r in c["blocuri"][0]["randuri"][:4]] if c and c.get("blocuri")
           else c or [(r["banca"], r["total"]) for r in d["raspunsuri"]])
    print(f"{q}\n   {json.dumps({k: i[k] for k in ('tip', 'banci', 'concept', 'categorie', 'termen', 'produs_credit', 'segment', 'metrica')}, ensure_ascii=False)}\n   {rez}")
print(f"cost total: ${total:.4f}")
```

- [ ] **Step 2: rularea**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe "$S/e2e_clasament.py"`
Expected: clasament administrare (PF, Libra pe 1–7); „și pentru firme?” → clasament cu `segment: pj`; „dar la BCR?” → căutare la BCR; depozit 12 luni → clasament cu 2 blocuri; DAE ipotecar → Libra locul 5; engleză → clasament `emitere_card`; cost total ~$0,03 (în registru, cu suma cumulată).

---

### Task 7: documentația și verificarea întregului

**Files:**
- Modify: `README.md` (secțiunea „Vox”)
- Modify: `.serena/memories/cod/harta.md`, `.serena/memories/stare/ultima_actualizare.md`

- [ ] **Step 1: README** — în secțiunea Vox, „Comparațiile, aplicațiile și campaniile nu intră: pagina răspunde că sunt în afara ei.” devine „Aplicațiile și campaniile nu intră: pagina răspunde că sunt în afara ei.”, și un punct nou:

```markdown
- **Clasamente.** „Care bancă are cel mai mic comision de administrare?”, „Unde stă Libra la DAE pentru
  ipotecar?”: Vox ordonează băncile cu celulele din 2.1 (comisioane, în lei, PF dacă întrebarea nu spune
  altfel) și 2.2 (dobânzi, pe categorie), deci aceleași cifre ca paginile (`celule_matrice`,
  `celule_rate`). Implicit pe mediană; „cea mai ieftină variantă” ordonează pe cea mai bună valoare.
  Egalitățile au loc comun (la administrarea contului PF, 7 din 14 bănci au mediana 0 lei, `mip_merge`,
  07.10.2026); Libra și băncile numite sunt evidențiate; cu termen sau tip de credit, un al doilea bloc
  arată valorile la care sursa nu le spune; băncile fără date apar cu motivul.
```

- [ ] **Step 2: memoria Serena** — în `cod/harta`: `celule_matrice` / `celule_rate` (o singură interogare a celulelor pentru 2.1, 2.2, Versus și clasamente), `_clasament_vox`, `_stare_banci_vox` (motivul pe toate băncile; `_stare_banca_vox` trece prin ea), tipul `clasament`, `clasa`, câmpurile `segment` / `metrica`, fișa `pages/vox/Clasament.tsx`; în `stare/ultima_actualizare`, commit-ul de referință.

- [ ] **Step 3: verificarea întregului** — `test_vox`, `test_celula`, `test_rulari`, `test_autentificare`, `test_server_autentificare`, `npm run typecheck`, `MIP_URL=http://localhost:8797 python app/verifica_pagini.py` (0 pagini cu erori), cele trei scripturi Playwright (`verifica_sertar_ui.py`, `verifica_vox_ui.py`, `verifica_clasament_ui.py`), `git status --short`. Se oprește serverul temporar.

- [ ] **Step 4: commit**

```bash
printf '%s\n' "docs, serena: clasamentele Vox (README, harta codului)" > "$S/msg_c7.txt"
git add README.md .serena/memories/cod/harta.md .serena/memories/stare/ultima_actualizare.md && git commit -F "$S/msg_c7.txt"
```
