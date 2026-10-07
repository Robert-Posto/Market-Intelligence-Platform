# Vox: răspunsuri pe segment, căderea filtrelor și motivul lipsei — planul de implementare

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** un răspuns Vox nu mai amestecă persoanele fizice cu firmele, nu spune „nu avem” când avem valori fără termen în sursă și spune de ce lipsește o bancă; sertarul din 2.1 și Versus arată exact rândurile celulei.

**Architecture:** regula segmentului stă o dată în `app/server.py` (`COND_SEG`, mutată din `matrice`, și `SEGMENT_RAND`); `celula` primește `segment` și `strict` și întoarce segmentul pe rând. `app/vox.py` grupează rezumatul pe segment (`ORDINE_SEGMENT`, PF primul), ordonează rândurile, cade pe „termen / credit nespecificat” și cere motivul lipsei de la `_stare_banca_vox`. Interfața citește câmpurile noi, toate opționale, ca răspunsurile salvate înainte să se redeschidă neschimbate.

**Tech Stack:** Python 3.12 (`unittest`, psycopg2), React 18 + Vite 6 + AntD 5 + TanStack Query + Zod (`@mcc/shared`), Playwright (Edge) pentru verificarea paginii.

**Spec:** `docs/superpowers/specs/2026-10-07-vox-raspunsuri-design.md`

`SCRATCH` = dosarul temporar al sesiunii (scratchpad); scripturile de verificare stau acolo, nu în repo.
În Git Bash: `S="C:/Users/NICOLA~1.CHE/AppData/Local/Temp/claude/c--Users-nicolae-cherascu-Desktop-Market-Intelligence-Platform/e6a2503b-45f0-43b2-91ba-6b16a4fdc1ef/scratchpad"`.

## Global Constraints

- Niciun apel plătit: testele folosesc `ClientFals`, scripturile un model fals, iar Playwright răspunde singur la `GET`/`POST /api/vox`. `python app/eval_vox.py --da` nu se rulează: promptul și schema modelului nu se schimbă.
- Serverele utilizatorului (:8765, :5173) nu se opresc și nu se repornesc; `npm run build` nu se rulează. Serverul temporar: `MIP_PORT=8797 MCC_AUTH_LOCAL=admin MIP_PERMITE_VOX=0 .venv/Scripts/python.exe app/server.py` (`config.incarca` folosește `setdefault`, deci variabilele date la pornire bat `.env`).
- Serverul rămâne read-only; în SQL intră doar parametri `%s`: `segment` se compară cu `vox.ORDINE_SEGMENT` și trece ca parametru, niciodată ca text.
- Valorile de segment: `pf`, `pfa`, `imm`, `pj`, `nemarcat`; ordinea în răspuns: PF, PFA, IMM, PJ, apoi fără segment. `filtre_relaxate` ∈ `[]`, `["termen"]`, `["produs"]`, `["termen", "produs"]`.
- Identificatori în română, fără diacritice; textele prin `t` / `tn`, perechi `[română, engleză]`; niciun pachet nou, niciun CDN.
- Comentariile spun de ce, cu cifra măsurată (`mip_merge`, 07.10.2026); commit-uri „zonă: ce și de ce”, fără `Co-Authored-By`, mesajele cu „…” prin `git commit -F <fișier>`.
- `app/server.py` are terminații CRLF: înlocuirile de text țin cont de `\r\n`.
- Scripturile Python: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe …`, din rădăcina repo-ului.
- Nu se ating `date/`, `db/`, `ingest/`, `.env`.

## Review Focus

- Conversațiile salvate înainte (răspunsuri fără `segment`, `filtre_relaxate`, `blocaje`) se redeschid fără eroare Zod și arată ca înainte, fără capete de segment și fără pastile — verificare în Task 4, pasul Playwright, pe `f829ad3c5a2732e5` și `0064ce56dddf70ac`.
- Răspunsurile în care niciun rând n-are segment (dobânzile, băncile ca BRD) nu arată „Fără segment în sursă” nici ca titlu, nici ca pastilă, iar „Vezi dovezile” nu trimite segment — test `test_fara_segment_un_singur_bloc` în Task 2 și cazul Libra în Task 4.
- „Vezi dovezile” după o cădere cere sertarului `termen=necunoscut` / `produs=altele`, altfel sertarul se deschide gol — cazul Libra în Task 4.
- O întrebare de continuare după o cădere („și pe 6 luni?”) pleacă de la interpretarea omului: `interpretare.termen` rămâne `12`, doar `filtre_relaxate` spune ce a căzut — test `test_termen_cade_pe_necunoscut` în Task 2.
- Un `segment` necunoscut sau vechi în `/api/celula` (`PF`, `x`, `toate`, `strict=1` fără segment, o încercare de injecție) se ignoră: nici 500, nici sertar gol — teste `test_segment_necunoscut_ignorat`, `test_strict_fara_segment_ignorat` în Task 1.

---

### Task 1: `/api/celula` cu segment și `strict`

**Files:**
- Modify: `app/vox.py` (constanta `ORDINE_SEGMENT`, după `MAX_RANDURI`)
- Modify: `app/server.py` (`COND_SEG` și `SEGMENT_RAND` înaintea lui `def matrice`, scoase din corpul `matrice`; `celula`)
- Create: `app/test_celula.py`
- Script: `SCRATCH/verifica_celula_db.py`

**Interfaces:**
- Produces: `vox.ORDINE_SEGMENT = ("pf", "pfa", "imm", "pj")`; `server.COND_SEG` (str SQL cu un `%s`); `server.SEGMENT_RAND` (expresie SQL, `NULL` fără segment); `/api/celula` acceptă `segment` (`pf|pfa|imm|pj` = regula din 2.1, `nemarcat`) și `strict=1`; fiecare rând are cheia `segment` (`"pf"|"pfa"|"imm"|"pj"|None`).

- [ ] **Step 1: fotografia de dinainte, pe `mip_merge`**

`SCRATCH/verifica_celula_db.py`:

```python
"""celula pe mip_merge, înainte și după segment (07.10.2026).

  python verifica_celula_db.py inainte   → celula_inainte.json, pe un eșantion de celule
  python verifica_celula_db.py dupa      → aceleași rânduri fără parametri noi + segmentul pe date reale
"""
import json, os, sys
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8")
RAD = r"C:\Users\nicolae.cherascu\Desktop\Market-Intelligence-Platform"
AICI = os.path.dirname(os.path.abspath(__file__))
os.chdir(RAD); sys.path.insert(0, os.path.join(RAD, "app"))
import server

# (banca, camp, unitate, scenariu, termen, produs, text): celule din 2.1, 2.2, Versus și Vox
ESANTION = [
    ("bcr", "administrare_cont", "lei", "", "", "", ""),
    ("brd", "administrare_cont", "lei", "", "", "", ""),
    ("libra", "retragere_numerar", "lei", "", "", "", ""),
    ("ing", "nominala", "procent", "depozite", "", "", ""),
    ("raiffeisen", "nominala", "procent", "depozite", "12", "", ""),
    ("libra", "dae", "procent", "credite", "", "ipotecar", ""),
    ("bcr", "", "", "", "", "", "datoria vamala"),
]
FIS = os.path.join(AICI, "celula_inainte.json")


def cere(b, c, u, s, t, p, x, **extra):
    q = {"banca": [b], "camp": [c], "unitate": [u], "scenariu": [s], "termen": [t], "produs": [p], "text": [x]}
    q.update({k: [v] for k, v in extra.items()})
    return json.loads(json.dumps(server.celula(q), ensure_ascii=False, default=str))


if sys.argv[1] == "inainte":
    with open(FIS, "w", encoding="utf-8") as f:
        json.dump({"|".join(e): cere(*e) for e in ESANTION}, f, ensure_ascii=False)
    print("scris", FIS)
    sys.exit()

vechi = json.load(open(FIS, encoding="utf-8"))
for e in ESANTION:
    nou = [{k: v for k, v in r.items() if k != "segment"} for r in cere(*e)]
    print("identic" if nou == vechi["|".join(e)] else "DIFERIT", len(nou), e)
toate = cere("bcr", "administrare_cont", "", "", "", "", "")
print("BCR · administrare cont:", Counter(r["segment"] for r in toate))           # pj 302, pfa 234, pf 33, None 1
strict = cere("bcr", "administrare_cont", "", "", "", "", "", segment="pf", strict="1")
print("strict pf:", len(strict), all(r["segment"] == "pf" for r in strict))      # 33 True
print("pf + nemarcate:", len(cere("bcr", "administrare_cont", "", "", "", "", "", segment="pf")))  # 34
nem = cere("bcr", "administrare_cont", "", "", "", "", "", segment="nemarcat")
print("nemarcat:", len(nem), all(r["segment"] is None for r in nem))             # 1 True
# sertarul din 2.1 pe PF = celula PF a matricei (aceleași filtre: lei, neambigue, cu cifră, sub prag)
m = server.matrice({"grup": ["cont_curent"], "segment": ["pf"], "unitate": ["lei"]})
cel = next(c for c in m["celule"] if c["banca"] == "bcr" and c["camp"] == "administrare_cont")
pf = [r for r in cere("bcr", "administrare_cont", "lei", "", "", "", "", segment="pf")
      if not r["ambiguu"] and r["valoare"] is not None and r["valoare"] <= server.PRAGURI["suma"]]
print("celula 2.1 PF:", cel["n"], "· sertarul PF filtrat ca matricea:", len(pf))  # egale
```

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe "$S/verifica_celula_db.py" inainte`
Expected: `scris …/celula_inainte.json`

- [ ] **Step 2: testele care pică**

`app/test_celula.py`:

```python
"""Teste fără bază pentru `/api/celula`: segmentul celulei și `strict`.

`interoghează` e înlocuit cu o funcție care ține minte interogarea, deci se verifică ce intră în SQL;
aceleași rânduri pe date reale le verifică scriptul pe `mip_merge` din planul
docs/superpowers/plans/2026-10-07-vox-raspunsuri.md.

Rulare:  python app/test_celula.py
"""

import os
import sys
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AICI)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import server  # noqa: E402

# parametrii interogării de bază: banca, camp ×2, unitate ×2, categorie ×2
BAZA = ("bcr", "administrare_cont", "administrare_cont", "", "", "", "")


class Celula(unittest.TestCase):
    def setUp(self):
        self.cereri = []
        self.vechi = server.interoghează
        server.interoghează = lambda sql, params=None: self.cereri.append((sql, tuple(params or ()))) or []

    def tearDown(self):
        server.interoghează = self.vechi

    def cere(self, **q):
        server.celula({"banca": ["bcr"], "camp": ["administrare_cont"], **{k: [v] for k, v in q.items()}})
        sql, params = self.cereri[-1]
        self.assertEqual(sql.count("%s"), len(params))      # niciun parametru rătăcit
        return sql, params

    def fara_filtru_de_segment(self, sql):
        self.assertNotIn(server.COND_SEG, sql)
        self.assertNotIn(f"{server.SEGMENT_RAND} =", sql)
        self.assertNotIn(f"{server.SEGMENT_RAND} IS NULL", sql)

    def test_fara_segment_ca_inainte(self):
        sql, params = self.cere()
        self.fara_filtru_de_segment(sql)
        self.assertEqual(params, BAZA)

    def test_fiecare_rand_are_segmentul(self):
        sql, _ = self.cere()
        self.assertIn(f"{server.SEGMENT_RAND} AS segment", sql)

    def test_segmentul_cu_regula_din_2_1(self):
        """Sertarul din 2.1 filtrat pe PF arăta și valorile PJ: celula cere acum segmentul, cu aceeași
        regulă ca matricea (segmentul plus rândurile nemarcate)."""
        sql, params = self.cere(segment="pf")
        self.assertIn(f"AND ({server.COND_SEG})", sql)
        self.assertEqual(params, BAZA + ("pf",))

    def test_strict_doar_segmentul(self):
        sql, params = self.cere(segment="pj", strict="1")
        self.assertIn(f"AND {server.SEGMENT_RAND} = %s", sql)
        self.assertNotIn(server.COND_SEG, sql)
        self.assertEqual(params, BAZA + ("pj",))

    def test_nemarcat_doar_randurile_fara_segment(self):
        sql, params = self.cere(segment="nemarcat")
        self.assertIn(f"AND {server.SEGMENT_RAND} IS NULL", sql)
        self.assertEqual(params, BAZA)

    def test_segment_necunoscut_ignorat(self):
        """O adresă veche sau scrisă de mână („PF”, „toate”) nu dă 500 și nici un sertar gol."""
        for seg in ("toate", "PF", "x", "pf' OR 1=1 --"):
            sql, params = self.cere(segment=seg, strict="1")
            self.fara_filtru_de_segment(sql)
            self.assertEqual(params, BAZA)

    def test_strict_fara_segment_ignorat(self):
        sql, params = self.cere(strict="1")
        self.fara_filtru_de_segment(sql)
        self.assertEqual(params, BAZA)

    def test_parametrii_in_ordinea_conditiilor(self):
        """Produsul, cuvintele și segmentul își adaugă parametrii în ordinea în care intră în SQL."""
        sql, params = self.cere(camp="", text="datoria vamala", produs="ipotecar", segment="pf")
        self.assertEqual(params[7], "ipotecar")
        self.assertEqual(params[-1], "pf")
        self.assertTrue(params[8:-1] and all(p.startswith("%") for p in params[8:-1]))


class Matrice(unittest.TestCase):
    def test_matricea_foloseste_aceeasi_regula(self):
        cereri, vechi = [], server.interoghează
        server.interoghează = lambda sql, params=None: cereri.append((sql, tuple(params or ()))) or [{"n": 0}]
        try:
            server.matrice({"grup": ["cont_curent"], "segment": ["pf"], "unitate": ["lei"]})
        finally:
            server.interoghează = vechi
        self.assertIn(f"AND ({server.COND_SEG})", cereri[0][0])
        self.assertEqual(cereri[0][1][-1], "pf")


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

- [ ] **Step 3: rulează, trebuie să pice**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe app/test_celula.py`
Expected: FAIL / ERROR cu `AttributeError: module 'server' has no attribute 'COND_SEG'` (sau `SEGMENT_RAND`).

- [ ] **Step 4: implementarea**

`app/vox.py`, după `MAX_RANDURI = 50`:

```python
# PF primul: la BCR · administrare cont, 302 valori PJ, 234 PFA și 33 PF stăteau într-un singur interval,
# 0–1.200 lei (mip_merge, 07.10.2026); rândurile fără segment în sursă vin la final. `celula` din server
# acceptă la `segment` doar aceste valori, plus `nemarcat`.
ORDINE_SEGMENT = ("pf", "pfa", "imm", "pj")
```

`app/server.py`, înaintea lui `def matrice(q):` (comentariul despre rândurile nemarcate se mută din `matrice`, neschimbat):

```python
# Rndurile FARA segment marcat in sursa se includ, nu se arunca.
#
# Motivul e masurat: BRD are 13 valori pentru `administrare_cont`, dintre
# care 0 marcate `pf` si 12 fara nicio marcare. Exim, la fel: 7 valori, 0
# marcate. Filtrul strict le arunca in silenta, iar in Versus coloana BRD
# aparea goala - ceea ce se citea ca „nu s-a putut extrage", cand de fapt
# extractia reusise si filtrul le ascundea.
#
# Nu se pretinde ca sunt PF: interfata le marcheaza „segment nemarcat in
# sursa", iar `segment_necunoscut` spune per celula daca reprezentativa
# vine dintr-un rnd nemarcat.
#
# Un singur loc pentru regulă: o folosesc `matrice` (2.1, Versus, fișa de bancă) și `celula`, ca
# sertarul deschis dintr-o celulă să arate exact rândurile cifrei pe care s-a dat clic.
COND_SEG = ("%s = ANY(string_to_array(coalesce(o.cod_scenariu, ''), '|')) "
            "OR NOT (coalesce(o.cod_scenariu, '') ~ '(^|\\|)(pf|pj|pfa|imm)(\\||$)')")
# Segmentul unui rând (NULL când sursa nu-l spune), pentru câmpul `segment` din `celula` și pentru
# `strict`. Pe mip_merge (07.10.2026) dă aceleași rânduri ca `COND_SEG` pe toate cele 4 segmente
# (pf 10.975, pj 15.281, pfa 9.729, imm 7.633), iar niciun rând nu are două segmente.
SEGMENT_RAND = r"substring(coalesce(o.cod_scenariu, '') from '(?:^|\|)(pf|pj|pfa|imm)(?:\||$)')"
```

În `matrice`, se șterg comentariul de mai sus și cele două linii `COND_SEG = (…)`; rămân, neschimbate:

```python
    filtru_seg = "" if segment == "toate" else f" AND ({COND_SEG})"
    p_seg = () if segment == "toate" else (segment,)
```

În `celula`, după `produs = (q.get("produs") or [""])[0]`:

```python
    segment = (q.get("segment") or [""])[0]
    strict = (q.get("strict") or [""])[0] == "1"
```

după bucla `for c in cuvinte:` (parametrul segmentului e ultimul, ca în SQL):

```python
    # segmentul: `pf` / `pfa` / `imm` / `pj` cu regula din 2.1 (`COND_SEG`: plus rândurile nemarcate),
    # ca sertarul din 2.1 și Versus să arate rândurile celulei; `nemarcat` = doar rândurile fără
    # segment; `strict=1` (grupele din Vox) = doar segmentul cerut: 251 din 752 de perechi bancă·concept
    # au și rânduri marcate, și nemarcate (mip_merge, 07.10.2026), iar grupa „33 PF” ar fi deschis un
    # sertar mai lung decât ea. Altă valoare se ignoră, ca la `termen` și `produs`.
    if segment == "nemarcat":
        extra += f" AND {SEGMENT_RAND} IS NULL"
    elif segment in vox.ORDINE_SEGMENT:
        extra += f" AND {SEGMENT_RAND} = %s" if strict else f" AND ({COND_SEG})"
        p_extra += (segment,)
```

iar prima linie a interogării devine f-string, cu segmentul în listă (restul interogării neschimbat):

```python
        f"""SELECT o.valoare_num::float8 AS valoare, o.valoare_text, o.unitate,
                  {SEGMENT_RAND} AS segment,
                  o.valuta, o.cod_scenariu, o.citat, o.confidence::float8,
```

- [ ] **Step 5: testele trec**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe app/test_celula.py && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe app/test_vox.py`
Expected: `OK` la amândouă (10 teste noi, 69 vechi).

- [ ] **Step 6: aceleași rânduri pe `mip_merge`**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe "$S/verifica_celula_db.py" dupa`
Expected: `identic` pe toate cele 7 celule; `BCR · administrare cont: Counter({'pj': 302, 'pfa': 234, 'pf': 33, None: 1})`; `strict pf: 33 True`; `pf + nemarcate: 34`; `nemarcat: 1 True`; cele două cifre de pe ultima linie egale.

- [ ] **Step 7: commit**

```bash
printf '%s\n' "app: /api/celula primește segmentul (regula din 2.1) și strict; fiecare rând își spune segmentul" "" "Sertarul din 2.1 filtrat pe PF arăta și valorile PJ, iar o grupă PF din Vox n-ar fi avut sertarul ei: 251 din 752 de perechi bancă·concept au și rânduri marcate, și nemarcate (mip_merge, 07.10.2026). COND_SEG iese din matrice, neschimbată." > "$S/msg_t1.txt"
git add app/vox.py app/server.py app/test_celula.py
git commit -F "$S/msg_t1.txt"
```

---

### Task 2: Vox pe segment, cu căderea filtrelor și motivul lipsei

**Files:**
- Modify: `app/vox.py` (`_ordine_segment` și `rezuma`; `Vox._raspuns`)
- Modify: `app/server.py` (`_stare_banca_vox`)
- Test: `app/test_vox.py` (`Rezumat`, `Intrebari`, clasa nouă `StareBanca` după `Intrebari`)
- Script: `SCRATCH/raspunsuri_noi.py`

**Interfaces:**
- Consumes: `vox.ORDINE_SEGMENT`; rândurile din `celula` cu `segment` (Task 1).
- Produces: grupa din `rezumat` are în plus `"segment"` (`str | None`); `RaspunsBanca` are în plus `"filtre_relaxate"` (listă) și `"blocaje"` (`{"surse", "robots", "refuzate", "pdf"}` sau `None`); `stare_banca(banca)` (parametrul lui `Vox`) întoarce `{"stare": "blocata"|"fara_surse"|None, "surse", "robots", "refuzate", "pdf"}` sau `None`.

- [ ] **Step 1: testele care pică**

În `class Rezumat`, `test_pe_unitate_fara_ambigue` primește segmentul în dicționarul așteptat:

```python
        self.assertEqual(r[0], {"segment": None, "unitate": "lei", "categorie": "comision", "n": 3,
                                "minim": 0, "maxim": 15, "gratuite": 1})
```

și, la finalul clasei:

```python
    def test_pe_segment_pf_primul_fara_dublari(self):
        """BCR · administrare cont: 302 PJ, 234 PFA și 33 PF într-un singur interval (mip_merge, 07.10.2026).
        Un rând fără segment are grupa lui, nu intră și la PF."""
        r = vox.rezuma([dict(rand(30), segment="pj"), dict(rand(5), segment="pf"), rand(7),
                        dict(rand(10), segment="pfa"), dict(rand(0), segment="pf")])
        self.assertEqual([(g["segment"], g["n"]) for g in r], [("pf", 2), ("pfa", 1), ("pj", 1), (None, 1)])
        self.assertEqual((r[0]["minim"], r[0]["maxim"], r[0]["gratuite"]), (0, 5, 1))

    def test_fara_segment_un_singur_bloc(self):
        """La dobânzi sursele nu spun segmentul: grupele rămân ca înainte, pe număr de valori."""
        r = vox.rezuma([rand(6.5, "procent", "depozite|12"), rand(7, "procent", "depozite|12"),
                        rand(9.9, "procent", "credite|ipotecar")])
        self.assertEqual([(g["segment"], g["categorie"], g["n"]) for g in r],
                         [(None, "depozite", 2), (None, "credite", 1)])
```

În `class Intrebari`, se înlocuiesc `test_zero_valori_spune_de_ce` și `test_zero_cu_termen_spune_cate_sunt_fara`:

```python
    def test_zero_valori_spune_de_ce(self):
        lipsa = {"stare": "blocata", "surse": 1, "robots": 0, "refuzate": 1, "pdf": 0}
        r = self.fa(ClientFals(interp(banci=["brd"])), stare_banca=lambda b: lipsa).intreaba("BRD?")["raspunsuri"][0]
        self.assertEqual((r["total"], r["stare_banca"], r["blocaje"]),
                         (0, "blocata", {"surse": 1, "robots": 0, "refuzate": 1, "pdf": 0}))

    def test_zero_cu_termen_spune_cate_sunt_fara(self):
        """Nici pe „termen nespecificat” nu iese nimic: fișa spune câte sunt fără niciun filtru, ca
        „nu avem valori” să nu se citească „banca n-are depozite”."""
        def cauta(banca, concept, categorie, termen, produs, text):
            self.cautari.append(termen)
            return [] if termen else [rand(3.5, "procent", "depozite"), rand(3.6, "procent", "depozite")]
        c = ClientFals(interp(banci=["ing"], concept="nominala", categorie="depozite", termen="12"))
        q = vox.Vox(context=lambda: CTX, cauta=cauta, stare_banca=lambda b: None,
                    client=c, dir_jurnal=self.dir)
        r = q.intreaba("ING, depozit pe 12 luni?")["raspunsuri"][0]
        self.assertEqual((r["total"], r["fara_filtre"], r["filtre_relaxate"], self.cautari),
                         (0, 2, [], ["12", "necunoscut", None]))
```

și se adaugă, la finalul clasei:

```python
    def test_pf_primele_inainte_de_taiere(self):
        """La BCR · administrare cont primele 50 de rânduri erau 18 PF, 19 PFA și 13 PJ amestecate
        (mip_merge, 07.10.2026): PF vin acum primele, apoi PFA, IMM, PJ și cele fără segment."""
        self.randuri["bcr"] = ([dict(rand(i), segment="pj") for i in range(30)] + [rand(7)]
                               + [dict(rand(i), segment="pfa") for i in range(30)]
                               + [dict(rand(1), segment="pf")] * 3)
        r = self.fa(ClientFals(interp())).intreaba("BCR?")["raspunsuri"][0]
        segmente = [x.get("segment") for x in r["randuri"]]
        self.assertEqual((r["total"], len(segmente)), (64, 50))
        self.assertEqual(segmente[:4], ["pf", "pf", "pf", "pfa"])
        self.assertEqual(segmente[-1], "pj")       # cel fără segment vine după PJ, dincolo de 50
        self.assertEqual([g["segment"] for g in r["rezumat"]], ["pf", "pfa", "pj", None])

    def test_termen_cade_pe_necunoscut(self):
        """Libra avea 11 dobânzi la depozite fără termen în sursă și niciuna pe 7–12 luni, iar fișa spunea
        „nu avem valori” (mip_merge, 07.10.2026). Interpretarea rămâne a omului, ca „și pe 6 luni?” să
        continue de la ce a cerut el."""
        def cauta(banca, concept, categorie, termen, produs, text):
            self.cautari.append((termen, produs))
            return [rand(4.75, "procent", "depozite")] * 11 if termen == "necunoscut" else []
        c = ClientFals(interp(banci=["libra"], concept="nominala", categorie="depozite", termen="12"))
        d = vox.Vox(context=lambda: CTX, cauta=cauta, stare_banca=lambda b: self.fail("banca are valori"),
                    client=c, dir_jurnal=self.dir).intreaba("Libra, depozit pe 12 luni?")
        r = d["raspunsuri"][0]
        self.assertEqual(self.cautari, [("12", None), ("necunoscut", None)])
        self.assertEqual((r["total"], r["filtre_relaxate"], r["fara_filtre"], r["blocaje"]),
                         (11, ["termen"], None, None))
        self.assertEqual(d["interpretare"]["termen"], "12")

    def test_produs_cade_pe_altele(self):
        def cauta(banca, concept, categorie, termen, produs, text):
            self.cautari.append((termen, produs))
            return [rand(8.1, "procent", "credite")] if produs == "altele" else []
        c = ClientFals(interp(banci=["bcr"], concept="nominala", categorie="credite", produs_credit="ipotecar"))
        r = vox.Vox(context=lambda: CTX, cauta=cauta, stare_banca=lambda b: None,
                    client=c, dir_jurnal=self.dir).intreaba("BCR, ipotecar?")["raspunsuri"][0]
        self.assertEqual(self.cautari, [(None, "ipotecar"), (None, "altele")])
        self.assertEqual((r["total"], r["filtre_relaxate"]), (1, ["produs"]))

    def test_termen_si_produs_cad_pe_rand(self):
        def cauta(banca, concept, categorie, termen, produs, text):
            self.cautari.append((termen, produs))
            return [rand(9.2, "procent", "credite")] if (termen, produs) == ("necunoscut", "altele") else []
        c = ClientFals(interp(banci=["bcr"], concept="nominala", categorie="credite", termen="lung",
                              produs_credit="ipotecar"))
        r = vox.Vox(context=lambda: CTX, cauta=cauta, stare_banca=lambda b: None,
                    client=c, dir_jurnal=self.dir).intreaba("BCR, ipotecar pe 30 de ani?")["raspunsuri"][0]
        self.assertEqual(self.cautari,
                         [("lung", "ipotecar"), ("necunoscut", "ipotecar"), ("necunoscut", "altele")])
        self.assertEqual((r["total"], r["filtre_relaxate"]), (1, ["termen", "produs"]))

    def test_blocaje_doar_cand_banca_n_are_valori(self):
        """ING: 48 de PDF-uri interzise de robots.txt din 158 de surse, deci nu „toate blocate”: fișa
        spunea doar „nu avem valori” (mip_merge, 07.10.2026)."""
        lipsa = {"stare": None, "surse": 158, "robots": 48, "refuzate": 0, "pdf": 48}
        r = self.fa(ClientFals(interp(banci=["ing"])), stare_banca=lambda b: lipsa).intreaba("ING?")["raspunsuri"][0]
        self.assertEqual((r["stare_banca"], r["blocaje"]),
                         (None, {"surse": 158, "robots": 48, "refuzate": 0, "pdf": 48}))
        r = self.fa(ClientFals(interp()), stare_banca=lambda b: self.fail("BCR are valori")).intreaba("BCR?")["raspunsuri"][0]
        self.assertIsNone(r["blocaje"])
```

Clasa nouă, după `Intrebari`:

```python
class StareBanca(unittest.TestCase):
    """`_stare_banca_vox` din server: ce spune fișa când banca n-are valori."""

    def setUp(self):
        import server
        self.server, self.vechi, self.cereri = server, server.interoghează, []

    def tearDown(self):
        self.server.interoghează = self.vechi

    def stare(self, numere):
        self.server.interoghează = lambda sql, params=None: self.cereri.append((sql, params)) or [numere]
        return self.server._stare_banca_vox("ing")

    def test_blocaje_partiale_pe_motiv(self):
        s = self.stare({"surse": 158, "blocate": 48, "robots": 48, "pdf": 48})
        self.assertEqual(s, {"stare": None, "surse": 158, "robots": 48, "refuzate": 0, "pdf": 48})
        sql, params = self.cereri[0]
        self.assertEqual(params, ("ing",))
        self.assertIn("LIKE 'ROBOTS%%'", sql)   # un singur % strică o interogare cu parametri (psycopg2)

    def test_toate_blocate_si_fara_surse(self):
        s = self.stare({"surse": 1, "blocate": 1, "robots": 0, "pdf": 0})
        self.assertEqual((s["stare"], s["refuzate"]), ("blocata", 1))
        self.assertEqual(self.stare({"surse": 0, "blocate": 0, "robots": 0, "pdf": 0})["stare"], "fara_surse")
```

- [ ] **Step 2: rulează, trebuie să pice**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe app/test_vox.py`
Expected: FAIL la testele noi și la cele două înlocuite (`KeyError: 'segment'`, `KeyError: 'filtre_relaxate'`, `TypeError` la `lipsa["stare"]`).

- [ ] **Step 3: implementarea**

`app/vox.py`, înaintea lui `rezuma`:

```python
def _ordine_segment(segment):
    return ORDINE_SEGMENT.index(segment) if segment in ORDINE_SEGMENT else len(ORDINE_SEGMENT)
```

`rezuma` devine:

```python
def rezuma(randuri):
    """Pe segment, unitate și categorie: câte valori, intervalul, câte gratuite; fără cele ambigue, ca în Sertar.

    Pe categorie, nu doar pe unitate: `nominala` e și dobânda de depozit, și cea de credit, iar fără
    categorie în întrebare un singur interval le-ar amesteca (6,5% la depozit cu 9,9% la ipotecar).
    Pe segment, cu PF primul (`ORDINE_SEGMENT`); un rând fără segment în sursă are grupa lui, la final.
    """
    grupe = {}
    for r in randuri:
        v = r.get("valoare")
        if r.get("ambiguu") or v is None:
            continue
        cheie = (r.get("segment"), r.get("unitate") or "", _categorie(r))
        g = grupe.setdefault(cheie, {"segment": cheie[0], "unitate": cheie[1], "categorie": cheie[2],
                                     "n": 0, "minim": v, "maxim": v, "gratuite": 0})
        g["n"] += 1
        g["minim"] = min(g["minim"], v)
        g["maxim"] = max(g["maxim"], v)
        g["gratuite"] += int(v == 0 and cheie[2] in CATEGORII_COMISION)
    return sorted(grupe.values(),
                  key=lambda g: (_ordine_segment(g["segment"]), -g["n"], g["categorie"], g["unitate"]))
```

`Vox._raspuns` devine:

```python
    def _raspuns(self, banca, interp):
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
        randuri = sorted(randuri, key=lambda r: _ordine_segment(r.get("segment")))
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
            "rezumat": rezuma(randuri),
            "randuri": randuri[:MAX_RANDURI],
            "filtre_relaxate": relaxate,
            "stare_banca": lipsa["stare"] if lipsa else None,
            # câte surse ale băncii sunt blocate și de ce; doar când banca n-are nicio valoare
            "blocaje": {k: lipsa[k] for k in ("surse", "robots", "refuzate", "pdf")} if lipsa else None,
            "fara_filtre": fara_filtre,
        }
```

`app/server.py`, `_stare_banca_vox` devine:

```python
def _stare_banca_vox(banca):
    """De ce n-are banca valori, din `surse`: nicio sursă, toate blocate (WAF, robots.txt), sau câte
    sunt blocate și de ce. ING avea 48 de PDF-uri interzise de robots.txt din 158 de surse, printre
    ele lista de taxe și comisioane, iar fișa spunea doar „nu avem valori” (mip_merge, 07.10.2026): se
    citea „ING nu percepe comisionul”. Nota `ROBOTS: …` o scrie `ingest/populare_initiala.py`."""
    r = interoghează(
        """SELECT count(s.id)::int AS surse,
                  count(s.id) FILTER (WHERE s.status = 'blocat')::int AS blocate,
                  count(s.id) FILTER (WHERE s.status = 'blocat'
                                        AND s.nota_extractie LIKE 'ROBOTS%%')::int AS robots,
                  count(s.id) FILTER (WHERE s.status = 'blocat' AND s.format = 'pdf')::int AS pdf
           FROM banci b LEFT JOIN surse s ON s.id_banca = b.id
           WHERE b.slug = %s""", (banca,))
    if not r:
        return None
    x = r[0]
    stare = "fara_surse" if x["surse"] == 0 else "blocata" if x["blocate"] == x["surse"] else None
    return {"stare": stare, "surse": x["surse"], "robots": x["robots"],
            "refuzate": x["blocate"] - x["robots"], "pdf": x["pdf"]}
```

- [ ] **Step 4: testele trec**

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe app/test_vox.py && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe app/test_celula.py`
Expected: `OK` la amândouă.

- [ ] **Step 5: criteriile din spec, pe `mip_merge`, cu model fals**

`SCRATCH/raspunsuri_noi.py`:

```python
"""Răspunsuri Vox cu date reale (mip_merge) și un model fals: criteriile din spec și, cu un argument,
fișierul pentru verificarea paginii. Niciun apel plătit."""
import json, os, sys, tempfile, types
sys.stdout.reconfigure(encoding="utf-8")
RAD = r"C:\Users\nicolae.cherascu\Desktop\Market-Intelligence-Platform"
os.chdir(RAD); sys.path.insert(0, os.path.join(RAD, "app"))
import server, vox


class Fals:
    def __init__(self, interp):
        self.interp, self.messages = interp, self

    def create(self, **kw):
        return types.SimpleNamespace(
            content=[types.SimpleNamespace(type="text", text=json.dumps(self.interp))], stop_reason="end_turn",
            usage=types.SimpleNamespace(input_tokens=12, output_tokens=58, cache_read_input_tokens=11556,
                                        cache_creation_input_tokens=0))


def i(**k):
    b = {"tip": "cautare", "banci": [], "concept": None, "categorie": None, "termen": None,
         "produs_credit": None, "text_cautat": None, "clarificare": None}
    b.update(k)
    return b


CAZURI = [
    ("Cât costă administrarea contului la BCR?", i(banci=["bcr"], concept="administrare_cont")),
    ("Ce dobândă are Libra la depozitul pe 12 luni?", i(banci=["libra"], concept="nominala", categorie="depozite", termen="12")),
    ("Cât costă administrarea contului la ING?", i(banci=["ing"], concept="administrare_cont")),
    ("Cât costă administrarea contului la CEC?", i(banci=["cec"], concept="administrare_cont")),
    ("Cât costă decontarea electronică a datoriei vamale la BCR?", i(banci=["bcr"], text_cautat="decontarea electronică a datoriei vamale")),
]
ctx = server._context_vox()


def intreaba(q, interp):
    v = vox.Vox(context=lambda: ctx, cauta=server._cauta_vox, stare_banca=server._stare_banca_vox,
                client=Fals(interp), dir_jurnal=tempfile.mkdtemp(prefix="vox_raspunsuri_"))
    return v.intreaba(q)


iesire = []
for q, interp in CAZURI:
    d = intreaba(q, interp)
    iesire.append({"intrebare": q, "raspuns": d})
    for r in d["raspunsuri"]:
        print(f"{q}\n   {r['banca']}: total {r['total']}, relaxate {r['filtre_relaxate']}, "
              f"stare {r['stare_banca']}, blocaje {r['blocaje']}, fără filtre {r['fara_filtre']}")
        print("   grupe:", [(g["segment"], g["unitate"], g["n"]) for g in r["rezumat"]])
        print("   primele rânduri:", [x.get("segment") for x in r["randuri"][:5]])
zero = [b["slug"] for b in ctx["banci"]
        if not intreaba("depozit 12 luni", i(banci=[b["slug"]], concept="nominala", categorie="depozite",
                                            termen="12"))["raspunsuri"][0]["total"]]
print(f"depozit 12 luni: {len(zero)} bănci fără valori")
if len(sys.argv) > 1:
    with open(sys.argv[1], "w", encoding="utf-8") as f:
        json.dump(iesire, f, ensure_ascii=False, default=str)
```

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe "$S/raspunsuri_noi.py" "$S/raspunsuri_noi.json"`
Expected: BCR cu grupele în ordinea `pf`, `pfa`, `pj`, `None` și primele rânduri `pf`; Libra `total 11, relaxate ['termen']`; ING `blocaje {'surse': 158, 'robots': 48, 'refuzate': 0, 'pdf': 48}`; CEC `stare blocata`; `depozit 12 luni: 20 bănci fără valori`.

- [ ] **Step 6: commit**

```bash
printf '%s\n' "app: Vox grupează pe segment, cade pe „termen / credit nespecificat” și spune de ce lipsește o bancă" "" "BCR · administrare cont amesteca 302 PJ, 234 PFA și 33 PF într-un interval; depozitul pe 12 luni dădea 0 la 28 din 30 de bănci (acum 20); ING tăcea despre cele 48 de PDF-uri interzise de robots.txt (mip_merge, 07.10.2026)." > "$S/msg_t2.txt"
git add app/vox.py app/server.py app/test_vox.py
git commit -F "$S/msg_t2.txt"
```

---

### Task 3: sertarul din 2.1 și Versus cere segmentul celulei

**Files:**
- Modify: `shared/src/celula.ts` (`ValoareDovada.segment`)
- Modify: `web/src/i18n/dict/comun.ts` (cheile `segment.*`, după `"sertar.inchide"`)
- Modify: `web/src/components/valori.ts` (`etSegment`)
- Modify: `web/src/components/Sertar.tsx` (`CerereSertar.segment`, `.strict`; cererea; pastila pe rând)
- Modify: `web/src/pages/Produse.tsx` (sertarul primește segmentul filtrului)
- Modify: `web/src/api/versus.ts` (`SEGMENT_VERSUS`), `web/src/pages/versus/Sectiune.tsx`
- Script: `SCRATCH/verifica_sertar_ui.py`

**Interfaces:**
- Consumes: `/api/celula?segment=…&strict=1` și `segment` pe rând (Task 1).
- Produces: `etSegment(segment: string | null | undefined, t) => string` în `components/valori.ts`; `CerereSertar.segment?: string`, `CerereSertar.strict?: boolean`; cheile `segment.pf|pfa|imm|pj|nemarcat`.

- [ ] **Step 1: schema și etichetele**

`shared/src/celula.ts`, în `ValoareDovada`, după `cod_scenariu`:

```ts
    /** pf / pfa / imm / pj din `cod_scenariu`; null = sursa nu-l spune; lipsește în răspunsurile Vox
     * salvate înainte de 07.10.2026 */
    segment: z.string().nullable().optional(),
```

`web/src/i18n/dict/comun.ts`, după `"sertar.inchide"` (etichetele din 2.1 sunt de filtru, „Doar persoane fizice”, și n-au PFA, IMM, nemarcat):

```ts
  "segment.pf": ["Persoane fizice", "Individuals"],
  "segment.pfa": ["PFA", "Sole traders (PFA)"],
  "segment.imm": ["IMM", "SMEs"],
  "segment.pj": ["Firme (PJ)", "Businesses"],
  "segment.nemarcat": ["Fără segment în sursă", "No segment in the source"],
```

`web/src/components/valori.ts`, la final:

```ts
/** Pentru cine e prețul (pf / pfa / imm / pj, din `cod_scenariu`); fără segment = sursa nu-l spune. */
export function etSegment(segment: string | null | undefined, t: Tr): string {
  const k = `segment.${segment || 'nemarcat'}`
  return areCheie(k) ? t(k) : String(segment)
}
```

- [ ] **Step 2: sertarul**

`web/src/components/Sertar.tsx`:
- `CerereSertar` primește:

```ts
  /** pf / pfa / imm / pj cu regula din 2.1 (plus rândurile fără segment) sau `nemarcat`; lipsă = toate */
  segment?: string
  /** doar segmentul cerut, fără rândurile nemarcate: grupele din Vox, care nu le numără */
  strict?: boolean
```

- cererea trimite și segmentul (`api` sare peste `undefined`):

```ts
      api('/api/celula', Celula, { banca: cerere!.banca, camp: cerere!.camp, unitate: cerere!.unitate, scenariu: cerere!.scenariu, termen: cerere!.termen ?? '', produs: cerere!.produs ?? '', segment: cerere!.segment, strict: cerere!.strict ? 1 : undefined }),
```

- importul din `./valori` devine `import { etDesc, etNume, etSegment, unitTxt } from './valori'`;
- în `Rand`, în `<div className="rc">`, după `{ctx.length ? … }` și înaintea pastilei „de verificat”:

```tsx
        {r.segment && <> <Pill>{etSegment(r.segment, t)}</Pill></>}
```

- [ ] **Step 3: 2.1 și Versus trimit segmentul**

`web/src/pages/Produse.tsx`, în `onClick` al celulei:

```tsx
                    onClick: () => setSertar({ banca: b, camp: cp, unitate: 'lei', scenariu: '', segment: seg === 'toate' ? undefined : seg }) }
```

`web/src/api/versus.ts`: o constantă pentru segmentul matricei, folosită de cerere:

```ts
/** Versus compară prețurile pentru persoane fizice; sertarul celulei cere același segment. */
export const SEGMENT_VERSUS = 'pf'
```

iar în `useVersusMatrice`, `segment: 'pf'` devine `segment: SEGMENT_VERSUS`.

`web/src/pages/versus/Sectiune.tsx`: `import { SEGMENT_VERSUS } from '../../api/versus'`, iar `deschide(…)` primește:

```tsx
                  onClick={() => deschide({ banca: b, camp: r.camp, unitate: g.unitate, scenariu: g.api === 'rate' ? g.cheie : '', segment: g.api === 'matrice' ? SEGMENT_VERSUS : undefined })}>
```

- [ ] **Step 4: typecheck**

Run: `npm run typecheck`
Expected: 0 erori (`tsc --noEmit` și `verifica_tema.mjs` trec).

- [ ] **Step 5: verificarea în pagină**

Serverul temporar (în fundal, cu codul din Task 1–2): `MIP_PORT=8797 MCC_AUTH_LOCAL=admin MIP_PERMITE_VOX=0 .venv/Scripts/python.exe app/server.py`.

`SCRATCH/verifica_sertar_ui.py`:

```python
"""Sertarul din 2.1 și din Versus trimite segmentul celulei (07.10.2026). Pagina de pe :5173, cererile
API spre serverul temporar de pe :8797; niciun POST.

  python verifica_sertar_ui.py <dosar capturi>
"""
import os, sys
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
OUT = sys.argv[1]
TINTA = "http://localhost:8797"
celule, probleme = [], []


def e_server(url):
    c = urlparse(url).path
    return c.startswith(("/api/", "/logos/")) or c == "/pdf"


def ruta(route):
    req = route.request
    u = urlparse(req.url)
    if req.method != "GET":
        return route.abort()
    if u.path == "/api/celula":
        celule.append(parse_qs(u.query))
    route.fulfill(response=route.fetch(url=TINTA + u.path + (f"?{u.query}" if u.query else "")))


def deschide_sertar(pg, celula):
    celula.click()
    pg.locator(".ant-drawer .s-rez").first.wait_for(timeout=20000)
    if pg.locator(".ant-drawer .r").count() == 0:                # peste 3 grupe pornesc pliate
        pg.locator(".ant-drawer .s-bara button").last.click()      # „deschide / închide tot”
    pg.wait_for_timeout(500)
    return celule[-1], pg.locator(".ant-drawer .r .rc .pill").all_inner_texts()


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge")
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.on("console", lambda m: probleme.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: probleme.append(f"pageerror: {e}"))
    pg.route(e_server, ruta)
    for seg, asteptat in (("pf", ["pf"]), ("toate", None)):
        pg.goto(f"http://localhost:5173/#/produse?grup=cont_curent&segment={seg}")
        pg.locator("td.mc").first.wait_for(timeout=20000)
        q, pastile = deschide_sertar(pg, pg.locator("td.mc").first)
        print(f"2.1 segment={seg}: cerere segment={q.get('segment')} strict={q.get('strict')}; pastile {sorted(set(pastile))}")
        assert q.get("segment") == asteptat and "strict" not in q, q
        pg.screenshot(path=os.path.join(OUT, f"sertar_21_{seg}.png"))
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(400)
    pg.goto("http://localhost:5173/#/versus")
    pg.locator(".vs-cel .celula").first.wait_for(timeout=20000)
    q, pastile = deschide_sertar(pg, pg.locator(".vs-cel .celula").first)
    print(f"Versus: cerere segment={q.get('segment')} scenariu={q.get('scenariu')}; pastile {sorted(set(pastile))}")
    assert q.get("segment") == ["pf"], q
    pg.screenshot(path=os.path.join(OUT, "sertar_versus.png"))
    b.close()
print("PROBLEME CONSOLĂ:", probleme or "niciuna")
```

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe "$S/verifica_sertar_ui.py" "$S"`
Expected: 2.1 pe `pf` cere `segment=['pf']`, fără `strict`; pe `toate`, fără segment; Versus cere `segment=['pf']`; pastilele „Persoane fizice” apar pe rândurile marcate; `PROBLEME CONSOLĂ: niciuna`. Capturile se privesc.

- [ ] **Step 6: commit**

```bash
printf '%s\n' "web: sertarul din 2.1 și Versus cere segmentul celulei; rândurile își arată segmentul" "" "Filtrat pe PF, sertarul arăta și valorile PJ, deci altceva decât cifra pe care s-a dat clic. Segmentul vine din /api/celula, cu regula matricei." > "$S/msg_t3.txt"
git add shared/src/celula.ts web/src/i18n/dict/comun.ts web/src/components/valori.ts web/src/components/Sertar.tsx web/src/pages/Produse.tsx web/src/api/versus.ts web/src/pages/versus/Sectiune.tsx
git commit -F "$S/msg_t3.txt"
```

---

### Task 4: fișa Vox pe segmente, cu nota căderii și motivul lipsei

**Files:**
- Modify: `shared/src/vox.ts` (`GrupaRezumat.segment`, `RaspunsBanca.filtre_relaxate`, `.blocaje`)
- Modify: `web/src/i18n/dict/vox.ts` (cheile `vox.relaxat.*`, `vox.blocaje.*`, `vox.lipsa_nu_inseamna`, după `"vox.vezi_le_n"`)
- Modify: `web/src/pages/Vox.tsx` (importuri; `FisaBanca`, `Rand`; funcțiile noi `peSegmente`, `notaRelaxata`, `textBlocaje`, `PlacaRezumat`)
- Modify: `web/src/styles/vox.css`
- Script: `SCRATCH/verifica_vox_ui.py`

**Interfaces:**
- Consumes: câmpurile din Task 2; `etSegment` și `CerereSertar.segment` / `.strict` din Task 3.

- [ ] **Step 1: schemele (toate câmpurile noi sunt opționale: conversațiile salvate le n-au)**

`shared/src/vox.ts`, în `GrupaRezumat`, primul câmp:

```ts
  /** pf / pfa / imm / pj; null = fără segment în sursă; lipsește în conversațiile salvate înainte de 07.10.2026 */
  segment: z.string().nullable().optional(),
```

în `RaspunsBanca`, după `stare_banca`:

```ts
    /** câte surse ale băncii sunt blocate și de ce, doar la 0 valori; lipsește în conversațiile vechi */
    blocaje: z.object({ surse: z.number(), robots: z.number(), refuzate: z.number(), pdf: z.number() }).nullable().optional(),
    /** filtrele căzute pe „nespecificat în sursă” ca răspunsul să nu iasă gol; lipsește în conversațiile vechi */
    filtre_relaxate: z.array(z.enum(['termen', 'produs'])).optional(),
```

- [ ] **Step 2: textele**

`web/src/i18n/dict/vox.ts`, după `"vox.vezi_le_n"`:

```ts
  "vox.relaxat.termen_1": ["Nicio valoare pe {termen} cu termenul scris în sursă; aceasta e singura la care sursa nu spune termenul.", "No value for {termen} with the term stated in the source; this is the only one whose source does not state the term."],
  "vox.relaxat.termen_n": ["Nicio valoare pe {termen} cu termenul scris în sursă; acestea sunt cele {n} la care sursa nu spune termenul.", "No value for {termen} with the term stated in the source; these are the {n} whose source does not state the term."],
  "vox.relaxat.produs_1": ["Nicio valoare pentru {produs} cu tipul de credit scris în sursă; aceasta e singura la care sursa nu spune tipul.", "No value for {produs} with the loan type stated in the source; this is the only one whose source does not state the type."],
  "vox.relaxat.produs_n": ["Nicio valoare pentru {produs} cu tipul de credit scris în sursă; acestea sunt cele {n} la care sursa nu spune tipul.", "No value for {produs} with the loan type stated in the source; these are the {n} whose source does not state the type."],
  "vox.relaxat.ambele_1": ["Nicio valoare pe {termen}, {produs}, cu termenul și tipul de credit scrise în sursă; aceasta e singura la care sursa nu le spune.", "No value for {termen}, {produs}, with the term and loan type stated in the source; this is the only one whose source states neither."],
  "vox.relaxat.ambele_n": ["Nicio valoare pe {termen}, {produs}, cu termenul și tipul de credit scrise în sursă; acestea sunt cele {n} la care sursa nu le spune.", "No value for {termen}, {produs}, with the term and loan type stated in the source; these are the {n} whose source states neither."],
  "vox.blocaje.robots_1": ["1 din cele {surse} surse ale băncii e interzisă de robots.txt; ce e în ea nu colectăm.", "1 of the bank's {surse} sources is disallowed by robots.txt; we do not collect what it contains."],
  "vox.blocaje.robots_n": ["{n} din cele {surse} surse ale băncii sunt interzise de robots.txt; ce e în ele nu colectăm.", "{n} of the bank's {surse} sources are disallowed by robots.txt; we do not collect what they contain."],
  "vox.blocaje.refuzate_1": ["1 din cele {surse} surse ale băncii a refuzat colectarea (WAF, HTTP 403).", "1 of the bank's {surse} sources refused collection (WAF, HTTP 403)."],
  "vox.blocaje.refuzate_n": ["{n} din cele {surse} surse ale băncii au refuzat colectarea (WAF, HTTP 403).", "{n} of the bank's {surse} sources refused collection (WAF, HTTP 403)."],
  "vox.blocaje.pdf_1": ["Printre sursele blocate e 1 document PDF.", "Among the blocked sources is 1 PDF document."],
  "vox.blocaje.pdf_n": ["Printre sursele blocate sunt {n} documente PDF.", "Among the blocked sources are {n} PDF documents."],
  "vox.blocaje.niciuna_1": ["Valoarea n-a apărut în singura sursă colectată a băncii.", "The value did not appear in the bank's only collected source."],
  "vox.blocaje.niciuna_n": ["Valoarea n-a apărut în cele {n} surse colectate ale băncii.", "The value did not appear in the bank's {n} collected sources."],
  "vox.lipsa_nu_inseamna": ["Lipsa din bază nu înseamnă că banca nu are produsul sau comisionul.", "Missing from our data does not mean the bank lacks the product or fee."],
```

- [ ] **Step 3: fișa**

`web/src/pages/Vox.tsx`:
- importuri: `import type { GrupaRezumat, Interpretare, RaspunsBanca, RaspunsIntrebare, ValoareDovada } from '@mcc/shared'` și `import { etNume, etSegment, unitTxt } from '../components/valori'`;
- după `type Tr = …`: `type Tn = ReturnType<typeof useLang>['tn']`;
- `FisaBanca` și `Rand` se înlocuiesc cu:

```tsx
function FisaBanca({ rb, i, m, onDovezi }: { rb: RaspunsBanca; i: Interpretare; m: Meta; onDovezi: (c: CerereSertar) => void }) {
  const { t, tn } = useLang()
  const [toate, setToate] = useState(false)
  const cap = (
    <div className="vox-banca">
      <EtichetaBanca slug={rb.banca} m={m} fisa />
      {rb.mod === 'text' && (
        <Tooltip title={t('vox.mod_text_tooltip')}>
          <span><Pill tip="amb">{t('vox.mod_text')}</Pill></span>
        </Tooltip>
      )}
      {rb.total > 0 && <span className="vox-n">{tn('vox.n_valori', rb.total)}</span>}
    </div>
  )
  if (rb.total === 0) {
    const concept = i.concept ? etNume(i.concept, t) : t('vox.text', { text: i.text_cautat ?? '' })
    // filtrele intră în mesaj: „nu avem dobânda nominală la ING” era fals, ING avea 2, fără termen citit
    const filtre = [
      i.termen && eticheta(`vox.termen.${i.termen}`, i.termen, t),
      i.produs_credit && eticheta(`vox.produs.${i.produs_credit}`, i.produs_credit, t),
    ].filter(Boolean).join(' · ')
    return (
      <div className="vox-fisa">
        {cap}
        <div className="vox-gol">
          <p>
            <b>{t('vox.zero', { concept: filtre ? `${concept} · ${filtre}` : concept, banca: m.nume[rb.banca] ?? rb.banca })}</b>
            {rb.stare_banca && <> {t(rb.stare_banca === 'blocata' ? 'vox.stare.blocata' : 'vox.stare.fara_surse')}</>}
            {!rb.stare_banca && rb.blocaje && <> {textBlocaje(rb.blocaje, tn)}</>}
            {!!rb.fara_filtre && <> {tn('vox.fara_filtre', rb.fara_filtre)}</>}
            {' '}{t('vox.lipsa_nu_inseamna')}
          </p>
          {!!rb.fara_filtre && i.concept && (
            <button type="button" className="vox-link avertizare" onClick={() => onDovezi({
              banca: rb.banca, camp: i.concept!, unitate: '', scenariu: i.categorie ?? '', termen: '', produs: '',
            })}>
              {tn('vox.vezi_le', rb.fara_filtre)}
            </button>
          )}
        </div>
      </div>
    )
  }
  const relaxate = rb.filtre_relaxate ?? []
  // sertarul cere filtrele pe care s-au găsit rândurile: cu termenul cerut de om, după o cădere pe
  // „termen nespecificat”, s-ar deschide gol
  const termen = relaxate.includes('termen') ? 'necunoscut' : (i.termen ?? '')
  const produs = relaxate.includes('produs') ? 'altele' : (i.produs_credit ?? '')
  const nota = notaRelaxata(relaxate, rb.total, i, t, tn)
  // segmentul se arată doar când sursele îl spun: la dobânzi niciun rând nu-l are, iar „fără segment
  // în sursă” pe fiecare răspuns ar fi zgomot
  const cuSegmente = rb.rezumat.some((g) => g.segment) || rb.randuri.some((v) => v.segment)
  // categoria spune ceva doar când grupele diferă (dobândă de depozit vs. de credit)
  const multeCategorii = new Set(rb.rezumat.map((g) => g.categorie)).size > 1
  const vizibile = toate ? rb.randuri : rb.randuri.slice(0, PRIMELE)
  return (
    <div className="vox-fisa">
      {cap}
      {nota && <p className="vox-nota"><span className="vox-punct" />{nota}</p>}
      {peSegmente(rb.rezumat).map(([s, grupe]) => (
        <div key={s ?? '-'} className="vox-segment">
          {cuSegmente && <span className="vox-segment-cap">{etSegment(s, t)}</span>}
          <div className="vox-kpis">
            {grupe.map((g) => (
              <PlacaRezumat key={`${g.unitate}|${g.categorie}`} g={g} multeCategorii={multeCategorii}
                onDovezi={rb.mod === 'concept' && i.concept ? () => onDovezi({
                  banca: rb.banca, camp: i.concept!, unitate: g.unitate, scenariu: g.categorie, termen, produs,
                  ...(cuSegmente ? { segment: g.segment ?? 'nemarcat', strict: true } : {}),
                }) : undefined} />
            ))}
          </div>
        </div>
      ))}
      {/* la căutarea după text SQL-ul se oprește la 50: rezumatul e pe ele, nu pe toate */}
      {rb.limitat && <p className="vox-nota"><span className="vox-punct" />{t('vox.din_primele', { n: rb.randuri.length })}</p>}
      {rb.ambigue > 0 && <p className="vox-nota"><span className="vox-punct" />{tn('vox.ambigue', rb.ambigue)}</p>}
      {rb.fara_cifra > 0 && <p className="vox-nota"><span className="vox-punct gri" />{tn('vox.fara_cifra', rb.fara_cifra)}</p>}
      <div className="vox-tabel-cutie">
        <table className="vox-tabel">
          <thead>
            <tr>
              <th>{t('vox.col.serviciu')}</th>
              <th className="dr">{t('vox.col.valoare')}</th>
              <th>{t('vox.col.document')}</th>
            </tr>
          </thead>
          <tbody>{vizibile.map((v, k) => <Rand key={k} v={v} cuSegmente={cuSegmente} />)}</tbody>
        </table>
      </div>
      {(rb.randuri.length > PRIMELE || rb.limitat) && (
        <div className="vox-fisa-jos">
          {rb.randuri.length > PRIMELE && (
            <button type="button" className="vox-link" onClick={() => setToate(!toate)}>
              {toate
                ? t('vox.arata_mai_putine')
                // BCR · Administrare cont are 570 de valori, din care răspunsul aduce 50: „toate (50)” ar minți
                : rb.total > rb.randuri.length
                  ? t('vox.arata_primele', { n: rb.randuri.length, total: rb.total })
                  : tn('vox.arata_toate', rb.randuri.length)}
            </button>
          )}
          {rb.limitat && <span className="vox-meta">{t('vox.limitat', { n: rb.randuri.length })}</span>}
        </div>
      )}
    </div>
  )
}

/** Grupele rezumatului, pe segmente consecutive: serverul le trimite deja în ordinea PF, PFA, IMM, PJ,
 * fără segment. În conversațiile vechi grupele n-au `segment`, deci ies toate într-un singur bloc. */
function peSegmente(rezumat: GrupaRezumat[]): [string | null, GrupaRezumat[]][] {
  const blocuri: [string | null, GrupaRezumat[]][] = []
  for (const g of rezumat) {
    const s = g.segment ?? null
    const ultim = blocuri[blocuri.length - 1]
    if (ultim && ultim[0] === s) ultim[1].push(g)
    else blocuri.push([s, [g]])
  }
  return blocuri
}

/** Ce filtru a căzut pe „nespecificat în sursă” și câte valori au rămas (app/vox.py, `_raspuns`). */
function notaRelaxata(relaxate: string[], n: number, i: Interpretare, t: Tr, tn: Tn): string | null {
  const termen = i.termen ? eticheta(`vox.termen.${i.termen}`, i.termen, t) : ''
  const produs = i.produs_credit ? eticheta(`vox.produs.${i.produs_credit}`, i.produs_credit, t) : ''
  if (relaxate.length === 2) return tn('vox.relaxat.ambele', n, { termen, produs })
  if (relaxate[0] === 'termen') return tn('vox.relaxat.termen', n, { termen })
  if (relaxate[0] === 'produs') return tn('vox.relaxat.produs', n, { produs })
  return null
}

/** De ce n-are banca valori, cu cifrele din `surse` (app/server.py, `_stare_banca_vox`). */
function textBlocaje(b: NonNullable<RaspunsBanca['blocaje']>, tn: Tn): string {
  const parti = [
    b.robots > 0 ? tn('vox.blocaje.robots', b.robots, { surse: b.surse }) : '',
    b.refuzate > 0 ? tn('vox.blocaje.refuzate', b.refuzate, { surse: b.surse }) : '',
    b.pdf > 0 ? tn('vox.blocaje.pdf', b.pdf) : '',
  ].filter(Boolean)
  return parti.length ? parti.join(' ') : tn('vox.blocaje.niciuna', b.surse)
}

function PlacaRezumat({ g, multeCategorii, onDovezi }: { g: GrupaRezumat; multeCategorii: boolean; onDovezi?: () => void }) {
  const { t, tn, locale } = useLang()
  const unitate = unitTxt(g.unitate, t).trim()
  const egal = g.minim === g.maxim
  return (
    <div className="vox-kpi">
      <span className="v">
        {egal ? num(g.minim, locale) : `${num(g.minim, locale)} – ${num(g.maxim, locale)}`}
        {unitate && <small> {unitate}</small>}
      </span>
      <span className="l">
        {egal && g.n > 1 ? tn('vox.kpi_egal', g.n) : tn('vox.kpi', g.n)}
        {g.gratuite > 0 && <> · {tn('vox.gratuite', g.gratuite)}</>}
        {multeCategorii && <> · {eticheta(`vox.categorie.${g.categorie}`, g.categorie, t)}</>}
      </span>
      {onDovezi && <button type="button" className="vox-link" onClick={onDovezi}>{t('vox.vezi_dovezi')}</button>}
    </div>
  )
}

function Rand({ v, cuSegmente }: { v: ValoareDovada; cuSegmente: boolean }) {
  const { t, locale } = useLang()
  const valoare = v.valoare !== null ? num(v.valoare, locale) + unitTxt(v.unitate, t) : (v.valoare_text ?? '—')
  return (
    <tr className={v.ambiguu ? 'ambiguu' : undefined}>
      <td>
        {v.serviciu ?? '—'}{v.conditie && <span className="sub">{v.conditie}</span>}
        {cuSegmente && <span className="vox-seg"><Pill>{etSegment(v.segment, t)}</Pill></span>}
      </td>
      <td className="dr val">{valoare}{v.frecventa && <span className="sub">{v.frecventa}</span>}</td>
      <td>
        {v.ambiguu && <><Pill tip="amb" title={v.motiv_ambiguu ?? undefined}>{t('vox.ambiguu')}</Pill>{' '}</>}
        <LinkSursa r={v} />
      </td>
    </tr>
  )
}
```

`web/src/styles/vox.css`, după regula `.vox-kpi .vox-link`:

```css
/* grupele rezumatului pe segmente (PF, PFA, IMM, PJ, fără segment), doar când sursele le spun */
.vox-segment { display: flex; flex-direction: column; gap: 6px }
.vox-segment-cap { font-family: var(--mono); font-size: 10.5px; font-weight: 500; letter-spacing: .08em;
  text-transform: uppercase; color: var(--muted) }
.vox-tabel .vox-seg { display: block; margin-top: 4px }
```

- [ ] **Step 4: typecheck**

Run: `npm run typecheck`
Expected: 0 erori.

- [ ] **Step 5: verificarea în pagină (fără apel plătit)**

Serverul temporar pe :8797 (pornit în Task 3; repornit dacă `app/` s-a schimbat de atunci). Răspunsurile vin din `SCRATCH/raspunsuri_noi.json` (Task 2, pasul 5).

`SCRATCH/verifica_vox_ui.py`:

```python
"""Pagina Vox cu răspunsurile noi (segment, cădere, blocaje), fără niciun apel plătit: GET și POST
/api/vox primesc răspunsuri din raspunsuri_noi.json, restul cererilor merg la serverul temporar de pe
:8797 (codul curent, Vox oprit). Verifică și conversațiile salvate în forma veche.

  python verifica_vox_ui.py <raspunsuri_noi.json> <dosar capturi>
"""
import json, os, sys
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
RASPUNSURI = {x["intrebare"]: x["raspuns"] for x in json.load(open(sys.argv[1], encoding="utf-8"))}
OUT = sys.argv[2]
TINTA = "http://localhost:8797"
celule, probleme = [], []


def e_server(url):
    c = urlparse(url).path
    return c.startswith(("/api/", "/logos/")) or c == "/pdf"


def json_raspuns(route, corp):
    route.fulfill(status=200, content_type="application/json", body=json.dumps(corp, ensure_ascii=False))


def ruta(route):
    req = route.request
    u = urlparse(req.url)
    if u.path == "/api/vox" and req.method == "GET":
        return json_raspuns(route, {"activ": True, "model": "claude-haiku-4-5", "token": "test"})
    if u.path == "/api/vox" and req.method == "POST":
        intrebare = json.loads(req.post_data or "{}").get("intrebare", "")
        if intrebare not in RASPUNSURI:
            return route.abort()
        return json_raspuns(route, {**RASPUNSURI[intrebare], "conversatie": None})
    if req.method != "GET":
        return route.abort()
    if u.path == "/api/celula":
        celule.append(parse_qs(u.query))
    route.fulfill(response=route.fetch(url=TINTA + u.path + (f"?{u.query}" if u.query else "")))


def pagina(b, tema, lang):
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"try {{ localStorage.setItem('mcc-tema', '{tema}'); localStorage.setItem('mcc-lang', '{lang}') }} catch (e) {{}}")
    pg = ctx.new_page()
    pg.on("console", lambda m: probleme.append(f"{tema}/{lang} {m.type}: {m.text}") if m.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: probleme.append(f"{tema}/{lang} pageerror: {e}"))
    pg.route(e_server, ruta)
    return ctx, pg


def intreaba(pg, q):
    n = pg.locator(".vox-fisa").count()
    camp = pg.locator(".vox-cutie textarea")
    camp.fill(q)
    camp.press("Enter")
    pg.wait_for_function(f"document.querySelectorAll('.vox-fisa').length > {n}", timeout=15000)
    pg.wait_for_timeout(400)
    return pg.locator(".vox-fisa").last


def sertar(pg, buton):
    buton.click()
    pg.locator(".ant-drawer .s-rez").first.wait_for(timeout=15000)
    q = celule[-1]
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(400)
    return q


with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge")
    for tema, lang in (("luminos", "ro"), ("intunecat", "en")):
        ctx, pg = pagina(b, tema, lang)
        pg.goto("http://localhost:5173/#/vox")
        pg.locator(".vox-conv-noua").first.wait_for(timeout=15000)
        # BCR: grupe pe segmente, PF primul; „Vezi dovezile” cere segmentul, strict
        fisa = intreaba(pg, "Cât costă administrarea contului la BCR?")
        capete = [c.lower() for c in fisa.locator(".vox-segment-cap").all_inner_texts()]
        print(f"[{tema}/{lang}] BCR segmente: {capete}; pastile: {fisa.locator('.vox-seg').count()}")
        assert capete[0] in ("persoane fizice", "individuals"), capete
        q = sertar(pg, fisa.locator(".vox-segment").first.locator(".vox-link").first)
        print("   sertar:", {k: q.get(k) for k in ("segment", "strict", "unitate", "scenariu")})
        assert q.get("segment") == ["pf"] and q.get("strict") == ["1"], q
        fisa.screenshot(path=os.path.join(OUT, f"vox_bcr_{tema}_{lang}.png"))
        # Libra: nota căderii, fără segmente; sertarul cere termen=necunoscut
        fisa = intreaba(pg, "Ce dobândă are Libra la depozitul pe 12 luni?")
        print("   Libra:", fisa.locator(".vox-nota").first.inner_text())
        assert fisa.locator(".vox-segment-cap").count() == 0 and fisa.locator(".vox-seg").count() == 0
        q = sertar(pg, fisa.locator(".vox-kpi .vox-link").first)
        print("   sertar:", {k: q.get(k) for k in ("termen", "segment", "strict")})
        assert q.get("termen") == ["necunoscut"] and "segment" not in q, q
        fisa.screenshot(path=os.path.join(OUT, f"vox_libra_{tema}_{lang}.png"))
        # ING și CEC: motivul lipsei
        for intrebare in ("Cât costă administrarea contului la ING?", "Cât costă administrarea contului la CEC?"):
            fisa = intreaba(pg, intrebare)
            print("  ", fisa.locator(".vox-gol p").inner_text())
            fisa.screenshot(path=os.path.join(OUT, f"vox_{intrebare.split()[-1].strip('?').lower()}_{tema}_{lang}.png"))
        ctx.close()
    # conversațiile salvate în forma veche se redeschid fără erori și fără segmente
    for c in ("f829ad3c5a2732e5", "0064ce56dddf70ac"):
        ctx, pg = pagina(b, "luminos", "ro")
        pg.goto(f"http://localhost:5173/#/vox?c={c}")
        pg.locator(".vox-fisa").first.wait_for(timeout=15000)
        print(f"conversația veche {c}: {pg.locator('.vox-fisa').count()} fișe, "
              f"{pg.locator('.vox-segment-cap').count()} capete de segment, {pg.locator('.vox-seg').count()} pastile")
        assert pg.locator(".vox-segment-cap").count() == 0 and pg.locator(".vox-seg").count() == 0
        pg.screenshot(path=os.path.join(OUT, f"vox_veche_{c}.png"), full_page=True)
        ctx.close()
    b.close()
print("PROBLEME CONSOLĂ:", json.dumps(probleme, ensure_ascii=False, indent=1) if probleme else "niciuna")
```

Run: `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe "$S/verifica_vox_ui.py" "$S/raspunsuri_noi.json" "$S"`
Expected: toate aserțiunile trec; ING: „48 din cele 158 surse ale băncii sunt interzise de robots.txt…” (EN la fel); CEC: textul „blocată”; conversațiile vechi: 0 capete, 0 pastile; `PROBLEME CONSOLĂ: niciuna`. Capturile se privesc, în ambele teme.

- [ ] **Step 6: commit**

```bash
printf '%s\n' "web: fișa Vox pe segmente, nota căderii pe „nespecificat în sursă” și motivul lipsei unei bănci" "" "Câmpurile noi sunt opționale: conversațiile salvate înainte se redeschid neschimbate. „Vezi dovezile” cere segmentul grupei (strict) și filtrele pe care s-au găsit rândurile." > "$S/msg_t4.txt"
git add shared/src/vox.ts web/src/i18n/dict/vox.ts web/src/pages/Vox.tsx web/src/styles/vox.css
git commit -F "$S/msg_t4.txt"
```

---

### Task 5: documentația și verificarea întregului

**Files:**
- Modify: `README.md` (secțiunea „Vox (pagina `#/vox`)”)
- Modify: memoria Serena `cod/harta` (`.serena/memories/cod/harta.md`)

- [ ] **Step 1: README**

În secțiunea Vox, punctul „Când termenul sau tipul de credit golesc răspunsul, fișa spune câte valori sunt fără filtru: ING are 2 dobânzi la depozite, niciuna cu termen citit din textul băncii.” se înlocuiește cu:

```markdown
- **Segmentul.** Rezumatul și tabelul se împart pe persoane fizice, PFA, IMM, firme și „fără segment
  în sursă”, PF primul: BCR · administrare cont avea 302 valori PJ, 234 PFA și 33 PF într-un singur
  interval, 0–1.200 lei (`mip_merge`, 07.10.2026). Segmentul vine din `cod_scenariu`; la dobânzi
  sursele nu-l spun, deci acolo nu apare. „Vezi dovezile” deschide sertarul exact pe grupă
  (`/api/celula?segment=pf&strict=1`); sertarul din 2.1 și Versus folosește regula lui 2.1 (segmentul
  plus rândurile nemarcate).
- **Termenul și tipul de credit** se citesc din textul băncii, deci pot goli un răspuns: la „depozit
  pe 12 luni” 28 din 30 de bănci n-aveau nicio valoare. Când răspunsul exact iese gol, Vox cade pe
  „termen nespecificat”, apoi și pe „credit nespecificat”, și spune ce filtru a căzut (Libra: 11
  dobânzi fără termen în sursă; băncile fără valori scad la 20). Dacă nici așa nu iese nimic, fișa
  spune câte valori sunt fără niciun filtru.
- **De ce lipsește o bancă.** Fișa goală spune câte surse ale băncii sunt interzise de `robots.txt`
  sau refuzate de site și câte sunt PDF-uri (ING: 48 de PDF-uri interzise din 158 de surse), ori că
  valoarea n-a apărut în sursele colectate; și că lipsa din bază nu înseamnă că banca n-are produsul.
```

iar „Teste fără rețea: `python app/test_vox.py`.” devine „Teste fără rețea: `python app/test_vox.py` și `python app/test_celula.py` (segmentul din `/api/celula`).”

- [ ] **Step 2: memoria Serena `cod/harta`**

- la `celula(q)`: „acceptă și `segment` (`pf` / `pfa` / `imm` / `pj` cu regula din 2.1, `COND_SEG`, sau `nemarcat`) și `strict=1` (doar segmentul; îl trimit grupele Vox); fiecare rând are `segment` (`SEGMENT_RAND`)”;
- la `app/vox.py`: „răspunsul: rezumatul pe segment (`ORDINE_SEGMENT`, PF primul), căderea termen → `necunoscut` → produs → `altele` (`filtre_relaxate`), `blocaje` din `_stare_banca_vox` când banca n-are valori”;
- la teste: `app/test_celula.py`.

- [ ] **Step 3: verificarea întregului**

Run, pe rând:
- `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe app/test_vox.py` → OK
- `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe app/test_celula.py` → OK
- `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe app/test_rulari.py` → OK
- `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe app/test_autentificare.py` → OK
- `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe app/test_server_autentificare.py` → OK
- `npm run typecheck` → 0 erori
- `MIP_URL=http://localhost:8797 PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe app/verifica_pagini.py` → 0 pagini cu erori
- `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe "$S/acoperire_vox.py"` → la „dep. 12 luni” aceleași 28 de bănci la filtrul exact (scriptul cheamă `_cauta_vox` direct, fără cădere); căderea o arată `raspunsuri_noi.py` (20)
- `git status --short` → doar fișierele neurmărite de dinainte (docs, `output/reclame/`)

Apoi se oprește serverul temporar de pe :8797 (al nostru, nu al utilizatorului).

- [ ] **Step 4: commit**

```bash
printf '%s\n' "docs, serena: Vox pe segmente, căderea filtrelor și motivul lipsei (README, harta codului)" > "$S/msg_t5.txt"
git add README.md .serena/memories/cod/harta.md
git commit -F "$S/msg_t5.txt"
```

Utilizatorului i se spune: repornirea serverului de pe :8765 aduce codul nou, iar `npm run build` (rulat de el) actualizează `/app/`.
