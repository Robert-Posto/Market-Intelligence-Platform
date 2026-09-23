# Market Intelligence Platform

Monitorizare a concurenței bancare din România: colectăm date publice de la 30
de bănci și fintech-uri, le normalizăm într-un vocabular comun și le comparăm.

Doar date publice. Se respectă `robots.txt`, User-Agent onest, fără ocolirea
WAF-urilor sau a captcha. Autorii recenziilor se pseudonimizează la ingest
(hash cu sare) — Apple întoarce numele real, deci anonimizarea o facem noi.

> **Prototip funcțional, în construcție activă.** Cifrele de mai jos sunt o
> fotografie de la **23 septembrie 2026**, după terminarea extracției din
> PDF-uri pe toate băncile.

---

## Ce e în bază acum

| | |
|---|---|
| bănci | 30 |
| surse (URL-uri + documente) | 903 |
| observații (prețuri, dobânzi) | 19.104 |
| în coada de verificare umană | 1.491 |
| schimbări de preț detectate | 18 |

Patru variante de colectare, cu acoperiri diferite — de aceea rulează toate:

| proveniență | observații | ce acoperă |
|---|---|---|
| `pdf` | 11.894 | comisioane din PDF-uri de tarife (reprezintă 15.111 celule — duplicatele sunt strânse) |
| `playwright` | 6.518 | pachetul colegului, gata extras (JSON) |
| `bs4` | 511 | depozite, scraperul propriu |
| `bs4_llm` | 181 | BS4 peste URL-urile găsite de discovery-ul LLM |

Pe secțiunile din PDF-ul de arhitectură:

| secțiune | acoperire |
|---|---|
| 2.1 Produse & prețuri | 19 bănci din 30 |
| 2.2 Rate & indicatori | 23 bănci |
| 2.3 Aplicații mobile | **19 bănci**, 130 capturi |
| 2.4 Campanii & marketing | **0 — necolectat** |
| 2.5 Rețea & operațional | 66 locații, **toate mock** |
| 2.6 Context de piață | 140 valori ROBOR/ROBID reale |
| 2.7 Sentiment | 3 bănci, 112 recenzii — limitat de feed, nu de cod |

---

## ⚠️ În lucru acum — scrieți înainte să prindeți ceva de aici

Ca să nu ne călcăm pe picioare.

| zonă | stare |
|---|---|
| `router.py --pas pdf` pe toate băncile | **terminat** — 96 PDF-uri, 15.111 comisioane |
| încărcarea aplicațiilor în 2.3 / 2.7 | **terminat** — 19 bănci |
| cascada de transport (Playwright) | **blocat: cere decizie de conformitate** |
| măsurare pentru 2.4 (campanii) | planificat, neînceput |

### Zonă înghețată deliberat

**Stratul autonom nu se atinge**: scheduler, rulări periodice, butoanele de
rulare din pagina Overview. Butoanele sunt `disabled` intenționat și sunt
**singurul mockup din aplicație**. Prioritatea curentă e doar popularea
inițială — cât de multe date reale se pot aduna. Automatizarea peste o
acoperire proastă ar ascunde golurile.

---

## Pornire

```bash
docker compose up -d                 # PostgreSQL 16
psql < db/schema.sql                 # apoi migrările 002..011, în ordine
psql < db/sincronizeaza_vederi.sql   # DUPĂ orice migrare care adaugă coloane

cp .env.exemplu .env                 # completează cheile
python app/server.py                 # http://localhost:8765
```

`.env` nu e versionat. Cere `MIP_DSN`, `MIP_SALT` (obligatoriu — scripturile
refuză să ruleze fără el) și `ANTHROPIC_API_KEY` pentru discovery.

> `sincronizeaza_vederi.sql` nu e opțional. Vederea `observatii_curente` e
> definită cu `SELECT *`, iar Postgres îngheață lista de coloane la creare: o
> coloană adăugată ulterior nu apare, și API-ul cade cu 500 deși tabela o are.

### Colectare

```bash
python ingest/router.py --pas playwright    # citește pachetul colegului
python ingest/router.py --pas bs4           # depozite
python ingest/router.py --pas descoperite   # BS4 peste URL-urile LLM (rețea)
python ingest/router.py --pas pdf           # comisioane din PDF-uri (rețea)
```

Pași auxiliari, care pregătesc sursele:

```bash
python ingest/recolteaza_pdf_banci.py   # găsește PDF-urile de tarife pe site-uri
python ingest/cauta_app_id.py           # id-uri de App Store
python ingest/fetch_logos_site.py       # sigle, de pe site-ul fiecărei bănci
```

Fiecare pas e **idempotent**: șterge doar ce a scris aceeași proveniență, apoi
rescrie. Rularea repetată nu dublează. `--banca <slug>` restrânge la o bancă.

### Înainte de commit

```bash
python app/verifica_pagini.py    # randează fiecare pagină într-un V8 real
```

Obligatoriu după orice modificare în `app/`. O eroare de JavaScript lasă pagina
complet albă, iar serverul răspunde vesel cu 200 — din terminal arată identic
cu „merge". S-a întâmplat de două ori, ambele din același motiv: un ghilimet
`"` ASCII pus în loc de `”` într-un text românesc, care închide șirul devreme
și doboară tot blocul `<script>`. Verificatorul localizează automat bucata.

---

## Probleme cunoscute

Ordonate după cât dor.

### Date

**16 bănci n-au avut niciodată comisioane** fiindcă pipeline-ul nu citea
PDF-uri. Corelația măsurată era perfectă: comisioane în bază exact la băncile
care aveau un PDF adus de pachetul colegului, zero la restul. Rezolvat
structural (`din_pdf` + `vocabular.canonic`), iar 2.1 a crescut de la 13 la 19
bănci.

**11 bănci rămân la zero**, din trei cauze care cer soluții diferite:

| cauză | bănci | ce ar rezolva |
|---|---|---|
| au PDF-uri, dar descărcarea dă 403 | intesa, unicredit, cec, banca-transilvania | browser real — **decizie de conformitate în așteptare** |
| au pagini, dar niciun PDF de tarife găsit pe ele | patria (38 pagini), credex, cetelem, citibank, bid | recoltare mai bună sau tarife publicate doar în HTML |
| fără nicio sursă descoperită | banorient | lipsește discovery-ul, nu extracția |

Despre cele patru cu 403: **nu e o problemă de antete.** Verificat — refuză și
cu antete HTTP complete, deci e detectare reală de bot. Singura cale rămasă e
un browser real (Playwright), iar asta cere o decizie de conformitate: un
browser nu e o ocolire de WAF, dar e accesarea unui site care ne-a refuzat
explicit prin alt canal. Falsificarea User-Agent-ului **nu** e o opțiune — ar
fi evaziune de detecție, interzisă de regulile proiectului.

`bnpparibas` e un caz aparte: are 2 PDF-uri și a extras 1 singură valoare, în
procente — deci nu apare la comisioane.

**2.7 e limitat de feed-ul Apple, nu de codul nostru.** Feed-ul RSS de
recenzii răspunde diferit la fiecare apel: BCR și Revolut au returnat 50 de
recenzii fiecare într-o rulare și **zero** în următoarea, la o oră distanță.
Secțiunea nu se poate umple într-o singură rulare — se acumulează în timp. De
aceea încărcarea **nu șterge niciodată** recenzii, doar adaugă ce e nou
(`ON CONFLICT DO NOTHING`). Prima versiune ștergea înainte de rescriere și a
distrus 106 recenzii, irecuperabile.

Ratingul agregat vine din Lookup API și e stabil — de aceea 2.3 s-a umplut
complet la 19 bănci, iar 2.7 nu.

**11 bănci fără id de aplicație confirmat.** Patru probabil n-au aplicație
(bcr-locuinte, bid, cec, creditcoop). Șapte au aplicația *grupului*, dar de pe
altă piață: BANOtouch e a mamei franceze, IKO e cea poloneză, iar `tbi`
potrivea „TBI Banking" publicat de **Trade Bank of Iraq**. Nu se scriu —
recenziile unor clienți francezi sau irakieni arată ca date bune și nu sunt.
Singura pe care aș paria că e corectă și totuși e respinsă: **techventures**,
doar fiindcă aplicația declară interfață numai în engleză. Cere confirmare
umană.

**5 bănci fără siglă**: intesa, revolut, techventures, citibank, banorient.
WAF sau timeout.

**2.5 e integral mock.** 66 de locații generate pentru hartă, în forma Google
Places. Nu sunt date reale și nu trebuie citite ca atare. Pe hartă se arată
doar nota, nu și texte de recenzii: o notă mock se citește ca cifră de
umplutură, un comentariu mock se citește ca părere reală de client.

### Calitate

**Rata de mapare la vocabularul canonic scade pe măsură ce adăugăm bănci.**
Pe ING singur ieșise 74,9%, peste cele 71,9% ale pachetului colegului. Pe toate
cele 21 de bănci împreună e **58,8%** — deci ~41% din comisioanele extrase
rămân în găleata generică `comision` și **nu apar în nicio comparație**.

Cel mai prost stau:

| bancă | valori | mapate |
|---|---|---|
| revolut | 64 | 7,8% |
| bcr | 4.068 | 45,7% |
| bankofchina | 72 | 51,4% |
| libra | 434 | 56,5% |
| brd | 733 | 56,8% |

BCR contează cel mai mult: 4.068 de valori la 45,7% înseamnă ~2.200 de
comisioane extrase corect dar invizibile. **Ăsta e cel mai valoros lucru de
lucrat la 2.1** — nu mai multă extracție, ci extinderea vocabularului canonic
peste denumirile pe care nu le acoperă.

Mai apar și rânduri de gunoi de la parserul de tarife nestandardizate
(„√ produsul / serviciul este"), necuantificate.

**1.529 de valori în coada de verificare.** Nu e o listă de bug-uri, e o
funcție a sistemului: un extractor care n-ar produce niciodată cazuri de
verificat ar însemna că nu verifică nimic. Două motive domină, amândouă
pierderi de *structură* la citirea tabelului, nu greșeli de citire a cifrei:
*antet de coloană pierdut* (nu se știe pentru care pachet e prețul) și
*prag de sumă pierdut* (avem 1, 3, 5, 15 lei fără să știm de la ce sumă).

**Doar ~51% din valori au link direct la documentul sursă.** Pachetul original
reține calea locală a PDF-ului, nu URL-ul de descărcare, iar PDF-urile nu sunt
incluse. Unde nu avem documentul exact, arătăm pagina de pe care banca îl
publică — marcată vizual diferit, fiindcă **nu e** documentul.

### Arhitectură

Față de arhitectura din artefactul de design, lipsesc:

- **Bronze** — octeții bruți nu se salvează nicăieri
- **sanitizare** înainte de extracție
- **hash-skip** — `hashes` are rânduri, dar nimic nu le citește înainte de
  procesare, deci se reprocesează tot de fiecare dată
- **cascada de transport** `http → playwright`
- **LLM ca ultimă treaptă** de extracție, pentru ce niciun parser determinist
  nu citește
- **`surse_produse`** — 583 de perechi URL×produs în bază, zero referințe în cod
- **`change_events` e gol** — schimbările de preț sunt o *vedere*
  (`schimbari_pret`), nu evenimente. Se recalculează din observații, deci nu
  pot fi desincronizate, dar nu declanșează nimic.

Primele trei există doar pentru rerulări, deci sunt în afara priorității
curente (populare inițială).

---

## Cum e construit

```
                    ┌─ citire pachet   (JSON gata extras)          ─┐
surse (tabelă) ──►  ├─ extractor HTML  (BS4 + parser_rate)          ─┼─► înregistrare
     ▲              ├─ extractor PDF   (parser_pdf / parser_tarife) ─┤     brută
     │              └─ extractor store (iTunes Lookup)               ─┘      │
     └── discovery LLM propune URL-uri                                       ▼
                                                                    normalizeaza.py
                                                                             │
                                                                             ▼
                                                                      observations
```

Două reguli care țin totul curat:

1. **Un extractor nu știe nimic despre baza de date.** Produce o înregistrare
   brută („am găsit 7,5 pe pagina asta, la serviciul ăsta") și atât.
2. **`normalizeaza.py` e singurul loc** care traduce brut → rând de bază:
   slug-ul băncii, conceptul canonic, unitatea, `cod_scenariu`, pragurile.
   Înainte existau trei copii ale acestor reguli, în trei loadere — de aceea
   196 de pagini găsite de discovery n-au fost extrase de nimeni: niciun
   script nu le avea în listă.

Detalii în [PIPELINE.md](PIPELINE.md).

### Praguri de plauzibilitate

Într-un singur loc, `normalizeaza.PRAGURI`. Fiecare are un motiv măsurat:

| prag | de ce |
|---|---|
| sumă > 10.000 lei | limitele de retragere și capitalul social ieșeau ca preț |
| depozite > 12% | TBI apărea cu „dobândă tipică 20%" dintr-o taxă |
| credite > 30% | mai sus sunt penalități |
| carduri > 40% | dobânda reală la cardul de credit ajunge la ~28% |

Ce depășește pragul **nu se aruncă**: se marchează ambiguu, se exclude din
comparații și apare în coadă, cu citatul din document.

---

## Structură

```
app/          server.py (API read-only) · index.html (SPA, 12 pagini)
              harta.html · pdf.html (vizualizator propriu) · verifica_pagini.py
ingest/       router.py · normalizeaza.py · extractoare.py + scripturi auxiliare
db/           schema.sql + migrările 002..011 · sincronizeaza_vederi.sql
date/         ieșiri intermediare (JSON)
```

Serverul e **strict read-only**: nicio rută nu scrie în bază. Interogările
folosesc parametri (`%s`), nu interpolare de text.

PDF-urile se deschid într-un **vizualizator propriu** (`pdf.html`, PDF.js), nu
în cititorul sistemului. Motivul: parametrii de deschidere Adobe (`#page=`,
`search=`) sunt implementați de plugin-ul clasic, care nu mai există în Chrome;
extensia Adobe pierde fragmentul din URL, iar Chrome ignoră `search=`. Cu
vizualizator propriu, saltul la pagină și evidențierea citatului merg
indiferent ce are instalat cititorul.

Ruta `/pdf` are **listă albă din baza de date** — servește doar documente
înregistrate ca surse. Fără ea ar fi un proxy deschis către orice adresă,
inclusiv din rețeaua internă.
