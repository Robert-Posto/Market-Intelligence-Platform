# Handoff: branch-ul `next-js-base`

Stare la **5 octombrie 2026**, scrisă de George Dinu (george.dinu@librabank.ro).

Branch-ul mută interfața aplicației MIP pe **Next.js**, pagină cu pagină. API-ul
Python (`app/server.py`) rămâne neschimbat ca rol: e singurul loc care citește
baza. Crawler-ul și ingest-ul rămân în Python. Aplicația veche (`app/index.html`)
merge mai departe în paralel, până se portează toate paginile.

---

## 1. Arhitectura

```
browser ──► Next.js  :3001  (web/)
              │  next.config.mjs rescrie /api/*, /logos/*, /pdf
              ▼
            app/server.py  :8765  (read-only, interogări parametrizate)
              │
              ▼
            Postgres 16 în Docker, containerul `mip-db`
```

De ce peste API-ul Python, nu cu rute API în Next.js:
- regulile serverului (read-only, parametri `%s`, `/pdf` servește doar URL-uri
  înregistrate în `surse`) rămân într-un singur loc, nu se dublează în JS;
- cele 26 de rute SQL existente nu trebuie rescrise ca să pornești;
- browserul vede o singură origine (:3001), deci nu e nevoie de CORS.

Next.js e App Router, JavaScript simplu (fără TypeScript, fără Tailwind).
Stilurile sunt cele din `app/index.html`, copiate în `web/app/globals.css`, deci
paginile arată la fel în ambele aplicații.

---

## 2. Cum pornești

Ai nevoie de: Docker Desktop, Python 3.12+, Node 20+ (testat pe Node 24).

```bash
# 1. baza (o dată pe sesiune) — pornește Docker Desktop; containerul mip-db urcă singur
docker ps | grep mip-db

# 2. API-ul Python, din rădăcina repo-ului
pip install -r requirements.txt
python app/server.py                  # http://localhost:8765  (aplicația veche)

# 3. interfața Next.js, alt terminal
cd web
npm install                           # doar prima dată
npm run dev                           # http://localhost:3001
```

Variabile opționale:
- `MIP_API` — unde e API-ul Python (implicit `http://localhost:8765`);
- `NEXT_PUBLIC_MIP_VECHI` — aplicația veche, unde trimite meniul paginile încă
  neportate (implicit tot `http://localhost:8765`).

`.env` din rădăcină **nu e în repo** și nu se trimite pe chat sau mail necriptat
(conține cheia Anthropic și `MIP_SALT`). Next.js nu are nevoie de el.

Dacă pagina arată „Eroare: OperationalError … port 5432”, nu merge Docker /
`mip-db`, nu Next.js.

---

## 3. Ce e portat

| Pagina | În Next.js | Observații |
|---|---|---|
| **Produse & prețuri** (`/produse`) | da, complet | comparația cu Libra; tabul „Comisioane pe bănci” (matricea veche) duce încă la aplicația veche |
| **Descoperă concurența** (`/concurenta`) | da, pagină nouă | există doar în Next.js, nu și în aplicația veche |
| celelalte 11 pagini | nu | meniul le deschide în aplicația veche (:8765) |

`/` redirecționează la `/produse`, fiindcă Overview nu e portat.

### Produse & prețuri

Fiecare produs din catalogul Libra (57) față de produsul **echivalent** găsit la
fiecare bancă. Date din tabela `comparatie_libra`, prin `/api/comparatie_libra`.

- slider cu produsele, filtre PF / PJ, categorie, căutare;
- tabel câmp × bancă, cu antet fix (se derulează doar corpul tabelului) și logourile băncilor;
- sub fiecare valoare, etichetele scenariului cu iconițe (valută, sumă, perioadă,
  „Ofertă”, „referință / ≈ referință / alt exemplu”);
- clic pe o valoare = modal cu citatul exact, linkul spre paragraful din document,
  corecțiile automate aplicate și încrederea;
- filtrele stau în URL (`?cat=DEPOZITE&ref=1`), deci o vedere se poate trimite ca link.

### Descoperă concurența

Produse de pe site-urile băncilor pentru care **nu există echivalent** în
catalogul Libra (ex. cont pentru copii, fonduri de investiții, factoring). Date
din tabela `products_discovery`, prin `/api/products_discovery`. Carduri grupate
pe categorie, filtre PF/PJ, categorie, bancă, „apărute luna asta”.

---

## 4. Structura `web/`

```
web/
├─ next.config.mjs        rescrierile spre API-ul Python
├─ app/
│  ├─ layout.jsx          bara laterală + fonturile
│  ├─ globals.css         toate stilurile (din app/index.html) + cele noi
│  ├─ page.jsx            redirect la /produse
│  ├─ produse/page.jsx
│  └─ concurenta/page.jsx
├─ components/
│  ├─ Meniu.jsx           meniul; paginile neportate = link spre aplicația veche
│  ├─ Antet.jsx           titlul paginii + <Despre>
│  ├─ produse/            ProduseLibra, Celula, ModalDovada, Iconita
│  └─ concurenta/         ProduseConcurenta
└─ lib/
   ├─ pagini.js           registrul paginilor + PORTATE (ce e deja în Next.js)
   ├─ api.js              ia(), meta() (numele și logourile băncilor), num()
   ├─ produse.js          logica paginii Produse & prețuri, fără HTML
   ├─ etichete.js         numele afișate ale câmpurilor
   └─ iconite.js          iconițele (desenate după Lucide, licență ISC, inline)
```

### Cum portezi următoarea pagină

Pe scurt (detalii în `web/README.md`):
1. logica fără HTML în `lib/<pagina>.js`, componentele în `components/<pagina>/`,
   ruta în `app/<id>/page.jsx` cu `<Antet id="<id>" />`;
2. adaugi `id`-ul în `PORTATE` din `lib/pagini.js` — meniul trece singur pe ruta nouă;
3. stilurile există deja în `globals.css`;
4. starea filtrelor în URL (`useSearchParams`), într-o graniță `<Suspense>`;
5. `npm run build` fără erori, apoi pagina deschisă pe :3001 cu date reale.

Candidații firești: matricea „Comisioane pe bănci” (tabul din Produse & prețuri) sau Overview.

---

## 5. Modificări în `app/server.py`

Două rute noi, ambele read-only, ambele întorc `{"disponibil": false}` (nu 500)
dacă tabela lipsește din bază:

| Rută | Tabela | Ce întoarce |
|---|---|---|
| `/api/comparatie_libra` | `comparatie_libra`, `produse_libra`, `surse_libra` | lista produselor + acoperirea pe bănci; cu `?produs=COD`, și valorile |
| `/api/products_discovery` | `products_discovery` | produsele fără echivalent Libra, cu `nou` / `retras` calculate |

---

## 6. De unde vin datele (important)

Tabelele de mai sus **nu sunt create de migrările din acest repo**. Vin din
fluxul de extracție din proiectul `proiect-it`, folderul
`extragere_produse_bancare/` (repo separat, deocamdată doar local la George):

- `migrari/migration_023 … 030` — `produse_libra`, `surse_libra`, `comparatie_libra`,
  `hashes_libra`, `products_discovery`, coloana `banci.acces_restricted`;
- `descopera_surse_libra.py` — pentru fiecare produs Libra, găsește pagina
  produsului echivalent la fiecare bancă;
- `extrage_comparatie_libra.py` — extrage valorile acelui produs (model Claude),
  apoi reguli deterministe (`reguli_valori.py`) și scenariul de referință;
- `descopera_produse.py` — produsele concurenței fără echivalent Libra.

Fără acele migrări, ambele pagini arată mesajul că tabelele lipsesc. Ca să le
ai și tu: cere migrările și JSON-urile din `inventare-libra/` și
`inventare-produse/`; baza se reconstruiește din JSON fără apeluri la model
(`extrage_comparatie_libra.py --banca <b> --din-json`, `descopera_produse.py --banca <b> --din-json`).

**Atenție la numerotare:** migrările 023–029 de acolo se suprapun ca număr cu
023–026 ale lui Robert din `db/`. Înainte de un PR spre `main`, trebuie
renumerotate (de la următorul număr liber).

Datele din bază la 05.10.2026:
- `comparatie_libra`: 2.116 valori, extrase la 01.10.2026 — Libra 398, BCR 517,
  Raiffeisen 489, BRD 439, ING 264, BT 9. Toate sunt **propuneri**, niciuna
  validată de un om.
- `products_discovery`: 21 de produse — Raiffeisen 13, BCR 4, ING 4 (pilot; la BCR
  s-au clasificat doar 60 din 186 de candidați).

---

## 7. Probleme deschise

1. **Nimic nu e împins.** Branch-ul e doar local. Commit-urile: `feab8c9` (pagina
   Produse & prețuri, pe `main` și aici) și `93908a7` (baza Next.js). Pagina
   „Descoperă concurența” și ruta `/api/products_discovery` sunt încă necommise
   la data scrierii.
2. **ING și robots.txt.** `ing.ro/robots.txt` interzice `*.pdf` și `*.xml`, dar
   fluxul de extracție a descărcat 31 de PDF-uri ING, din care au ieșit 94 de
   valori. Extracția nu verifica robots.txt (doar noul `candidati_produse.py` o
   face). De decis: se scot cele 94 de valori și se adaugă verificarea în
   extracție.
3. **Bănci blocate (regula echipei: 403 = stop, nu se ocolește).** BT răspunde
   403 pe site-ul principal (9 valori în total); `raiffeisen-leasing.ro` dă 403,
   de aceea Raiffeisen n-are valori la Leasing financiar. `acces_restricted`
   pentru BT e încă nedecis.
4. **Dubluri în catalogul Libra.** Perechile `CREDIT_NEVOI_PERSONALE` /
   `CREDIT_LIBRA_WAY`, `CREDIT_IMM_IPOTECA` / `CREDIT_IMOBILIAR_PJ`,
   `CARD_CREDIT_BUSINESS` / `CARD_CREDIT_PJ` au aceeași pagină la Libra, deci
   valorile concurenței apar de două ori. Decizie de catalog, nu de cod.
5. **Descrierile din „Descoperă concurența” sunt rezumate scrise de model**, nu
   text copiat din pagina băncii, și pagina nu spune asta. De ales: citatul
   băncii, rezumatul etichetat, sau amândouă.
6. **Matricea „Comisioane pe bănci”** nu e portată și e goală pe baza locală
   (lipsesc datele colectate de Robert).
7. Avertismentul `autoprefixer: end value has mixed support` la build vine din
   CSS-ul copiat; e inofensiv.

---

## 8. Reguli de păstrat

Din `CLAUDE.md` (citește-l întreg):
- serverul e read-only; interogări cu parametri, niciodată text interpolat;
- `web/` nu citește baza direct și nu are rute API proprii;
- în `app/index.html`, textele din `<script>` folosesc „…” sau ”, niciodată `"`
  ASCII într-un șir (o ghilimea greșită lasă pagina albă);
- doar date publice, robots.txt respectat, o bancă blocată se documentează ca
  blocată;
- commit-uri în română, de forma „zonă: ce și de ce”, fără `Co-Authored-By`.

Verificări înainte de commit:
- `web/`: `npm run build` fără erori și pagina deschisă pe :3001 cu date reale;
- `app/`: `python app/verifica_pagini.py`, cu serverul Python pornit.
