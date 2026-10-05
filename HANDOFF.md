# Handoff: branch-ul `george-branch`

Stare la **5 octombrie 2026**, scrisă de George Dinu (george.dinu@librabank.ro).

Branch-ul conține două lucruri, ambele gata de rulat după clonare:
1. **Comparația produselor Libra cu concurența**, cap-coadă: fluxul care găsește
   produsul echivalent la fiecare bancă și îi extrage valorile
   (`extragere_produse_bancare/`), datele colectate (inventarele JSON) și
   migrările bazei (`db/migration_027 … 034`).
2. **O interfață Next.js** (`web/`) cu două pagini: „Produse & prețuri”
   (comparația cu Libra) și „Descoperă concurența” (produsele concurenței pe care
   Libra nu le are în catalog).

> **Atenție:** pe `main`, interfața a trecut între timp pe React + Vite + Ant
> Design (`docs/HANDOFF_REACT.md`, PR #1, 05.10.2026), tot în `web/`. Branch-ul
> acesta pornește dinaintea acelui merge și are în `web/` aplicația Next.js, deci
> **nu se poate unifica direct cu `main`**: la un merge, `web/` intră în conflict.
> Fluxul de date, migrările și rutele API nu depind de interfață și se pot muta
> oricând peste `main`.

---

## 1. Pornire, de la zero

Ai nevoie de: Docker Desktop, Python 3.12+, Node 20+ (testat pe Node 24).

```bash
git clone https://github.com/Robert-Posto/Market-Intelligence-Platform.git
cd Market-Intelligence-Platform
git switch george-branch
pip install -r requirements.txt
```

### 1.1 Baza MIP

Ai nevoie de baza MIP (containerul `mip-db`, Postgres 16) cu tabelele de bază
(`banci`, `surse`, `observations`…) și migrările 002–026. Două variante, vezi
`README.md` („Migrări”) și `deploy/importa_baza_docker.ps1`:
- importi copia bazei lui Robert (cea mai simplă), sau
- creezi baza din `db/schema.sql`, seed-uri și migrări.

Conexiunea implicită: `host=localhost port=5432 dbname=mip user=mip password=mip`
(se schimbă cu variabila `MIP_DSN`).

### 1.2 Datele comparației — o singură comandă

```bash
python extragere_produse_bancare/incarca_baza.py
```

Face tot, **fără descărcări și fără apeluri la model**:
1. aplică migrările 027–034, doar dacă tabelele lipsesc;
2. încarcă cele 57 de produse Libra (`produse_libra.json`);
3. sursele găsite la fiecare bancă (`inventare-libra/<banca>/*.json`);
4. valorile extrase (`inventare-libra/valori-<banca>.json`), cu regulile deterministe;
5. produsele concurenței (`inventare-produse/produse-<banca>.json`).

Verificat pe 05.10.2026 pe o bază nouă (copia fără tabelele fluxului): iese exact ce
era pe baza originală — **710 surse, 2.116 valori, 21 de produse ale concurenței**,
fiecare valoare legată de același URL. Se poate rula de mai multe ori.

### 1.3 Aplicația

```bash
python app/server.py              # API-ul, http://localhost:8765 (și aplicația veche)

cd web                            # alt terminal
npm ci                            # doar prima dată
npm run dev                       # http://localhost:3001
```

Paginile noi: http://localhost:3001/produse și http://localhost:3001/concurenta.
Celelalte pagini din meniu se deschid în aplicația veche (:8765).

Dacă pagina arată „Eroare: OperationalError … port 5432”, nu rulează baza (Docker /
`mip-db`), nu Next.js.

### 1.4 Cheia Anthropic (doar pentru rulări noi)

Ca să încarci datele și să vezi paginile **nu** ai nevoie de cheie. Doar ca să
re-rulezi discovery-ul sau extracția: copiază `extragere_produse_bancare/.env.exemplu`
în `extragere_produse_bancare/.env` și pune `ANTHROPIC_API_KEY`. `.env` nu intră
în git și nu se trimite pe chat sau mail necriptat.

---

## 2. Arhitectura

```
browser ──► Next.js :3001 (web/)
              │  next.config.mjs rescrie /api/*, /logos/*, /pdf
              ▼
            app/server.py :8765   read-only, interogări parametrizate
              ▼
            Postgres 16 (mip-db) ◄── extragere_produse_bancare/*.py (scriu tabelele fluxului)
```

Next.js e doar interfață: nu citește baza direct și nu are rute API proprii.
Regulile serverului (read-only, parametri `%s`, `/pdf` doar pentru URL-uri din
`surse`) rămân într-un singur loc. Două rute noi în `app/server.py`:

| Rută | Ce întoarce |
|---|---|
| `/api/comparatie_libra` | produsele Libra și acoperirea pe bănci; cu `?produs=COD`, și valorile, cu citat, link și scenariu |
| `/api/products_discovery` | produsele concurenței fără echivalent Libra, cu `nou` / `retras` |

Ambele întorc `{"disponibil": false}` (nu 500) dacă tabelele lipsesc.

---

## 3. Fluxul de date (`extragere_produse_bancare/`)

| Pas | Script | Scrie în |
|---|---|---|
| 1. Pentru fiecare produs Libra × bancă, pagina produsului echivalent | `descopera_surse_libra.py --banca bcr` | `surse_libra`, `inventare-libra/<banca>/` |
| 2. Valorile acelui produs (DAE, dobânzi, comisioane…), cu citat verificat | `extrage_comparatie_libra.py --banca bcr` | `comparatie_libra`, `hashes_libra`, `inventare-libra/valori-<banca>.json` |
| 3. Produsele concurenței pe care Libra nu le are în catalog | `descopera_produse.py --banca bcr` | `products_discovery`, `inventare-produse/` |

Toate au `--simulare` (fără cost) și `--din-json` (rescrie baza din JSON, fără rețea).
Extracția compară amprenta documentului (`hashes_libra`): un document neschimbat nu
se mai trimite la model, deci o re-rulare costă doar ce s-a schimbat.

Fișiere de configurare:
- `produse_bancare_v2.json`, `mapare_libra_v2.json` — câmpurile căutate pe tip de produs;
- `reguli_valori.py` — reguli fără model aplicate fiecărei valori: un 0 doar cu
  dovadă în citat, „negociabil” / „nelimitat” ca text, dobânda minimă / maximă în
  câmpul ei, dobânda penalizatoare respinsă, perioadele în luni. Ce se respinge
  ajunge în `inventare-libra/respinse-reguli-<banca>.json`;
- `axa_libra.json` — la Libra, paginile altor produse Libra se exclud, variantele
  (ex. „locuință în construcție”) se etichetează;
- `referinte_libra.json` — scenariul de referință per produs (ex. ipotecar
  350.000 lei / 300 luni), ca DAE-urile să se compare pe același exemplu;
- `surse_produse.json` — de unde pornește descoperirea produselor concurenței.

---

## 4. Ce date sunt în repo

- **Valorile**: extrase la 01.10.2026 — Libra 398, BCR 517, Raiffeisen 489, BRD 439,
  ING 264, BT 9. Toate sunt **propuneri** (`stare = 'propus'`), niciuna validată de un om.
- **Produsele concurenței**: 21 (Raiffeisen 13, BCR 4, ING 4). Pilot: la BCR s-au
  clasificat 60 din 186 de candidați; BRD și Libra încă nerulate.
- **Fără date interne Libra.** Descrierile din catalogul intern (prețuri și condiții
  interne) au fost scoase din inventare, iar extracția nu le mai scrie în JSON;
  `produse_libra.json` are doar coduri, denumiri, segment și categorie.

---

## 5. Probleme deschise

1. **Repo-ul e public** (răspunde fără autentificare). Inventarele conțin doar date
   publice ale băncilor, dar împreună sunt o comparație structurată Libra vs.
   concurență. De discutat dacă trece în `Libra-Bank/marketing-command-center`
   (privat), cum cere `docs/HANDOFF_REACT.md`.
2. **Interfața: Next.js aici, React pe `main`.** De decis cu echipa dacă cele două
   pagini se portează pe stack-ul React, ca să intre în `main`.
3. **ING și robots.txt.** `ing.ro/robots.txt` interzice `*.pdf`; extracția a
   descărcat totuși 31 de PDF-uri ING (94 de valori), fiindcă nu verifica robots.txt
   (doar `candidati_produse.py` o face). De decis: se scot cele 94 de valori și se
   adaugă verificarea în extracție.
4. **Bănci blocate (403 = stop, nu se ocolește).** BT pe site-ul principal (9 valori
   în total); `raiffeisen-leasing.ro`, deci Raiffeisen n-are Leasing financiar.
5. **Dubluri în catalogul Libra:** `CREDIT_NEVOI_PERSONALE` / `CREDIT_LIBRA_WAY`,
   `CREDIT_IMM_IPOTECA` / `CREDIT_IMOBILIAR_PJ`, `CARD_CREDIT_BUSINESS` /
   `CARD_CREDIT_PJ` au aceeași pagină la Libra, deci valorile concurenței apar de două ori.
6. **Descrierile din „Descoperă concurența”** sunt rezumate scrise de model, nu text
   copiat din pagina băncii, și pagina nu spune asta.
7. **Tabul „Comisioane pe bănci”** din Produse & prețuri nu e portat în Next.js (duce
   la aplicația veche) și e gol fără datele colectate de Robert.

---

## 6. Reguli de păstrat

Din `CLAUDE.md` (citește-l întreg): doar date publice, robots.txt respectat, o bancă
blocată se documentează ca blocată; serverul read-only; commit-uri în română, de
forma „zonă: ce și de ce”.

Verificări înainte de commit:
- `web/`: `npm run build` fără erori, apoi pagina deschisă pe :3001 cu date reale;
- `app/`: `python app/verifica_pagini.py`, cu serverul Python pornit;
- fluxul: `incarca_baza.py` pe o bază nouă trebuie să dea aceleași cifre ca mai sus.
