# Vox: clasamente pe comisioane și dobânzi

Data: 07.10.2026. Ramura `vox-chatbot`. Design aprobat în discuție cu Nicolae Cherascu, pe secțiuni.
Primul sub-proiect din „Vox răspunde și din alte zone”; celelalte (schimbări de preț, aplicații,
indici BNR) vin separat. Cifrele sunt măsurate pe `mip_merge`, 07.10.2026.

## Ce vrea utilizatorul

Vox răspunde și la întrebările de comparație între bănci, pe care azi le refuză („în afara mea”):
„Care bancă are cel mai mic comision de administrare?” a fost refuzată de 3 ori în jurnalul din
octombrie. Răspunsul e un clasament din bază, cu aceleași cifre ca paginile 2.1 și 2.2, cu Libra
evidențiată și cu dovezile fiecărei bănci.

Criterii de reușită:
- „Care bancă are cel mai mic comision de administrare?” dă clasamentul PF pe mediană: 14 bănci cu
  date, BRCI, BRD, Creditcoop, Libra, ProCredit, Salt și TBI pe „locurile 1–7” (0 lei), Raiffeisen
  ultima (20 lei), iar cifra fiecărei bănci e cea din celula ei din 2.1 pe PF;
- „Care e cea mai ieftină variantă de administrare a contului?” ordonează pe minimul fiecărei bănci;
- „… pentru firme?” refă clasamentul pe PJ;
- „Cine are cea mai mare dobândă la depozitul pe 12 luni?” arată 2 bănci cu termenul scris în sursă
  (Raiffeisen, Vista) și, separat, 9 bănci cu termen nespecificat în sursă;
- „Unde stă Libra la DAE pentru ipotecar?” arată clasamentul celor 7 bănci, cu Libra evidențiată
  (locul 5);
- băncile fără date apar cu motivul (blocate, fără surse, PDF-uri interzise de robots.txt);
- conversațiile salvate înainte se redeschid neschimbate.

## Ce nu intră

- Celelalte zone (schimbări de preț, aplicații și recenzii, indici BNR, campanii): sub-proiecte separate.
- Clasamente pe mai multe servicii deodată („cel mai ieftin cont curent, per total”).
- Comisioanele în EUR: 2.1 compară doar în lei, iar clasamentul folosește aceeași matrice.
- Servicii fără concept (găsite prin căutarea după text): n-au o cifră comparabilă între bănci.
- Proză scrisă de model: și clasamentul vine integral din bază; textele fixe din `i18n`.

## Contractul cu modelul

- `tip` primește valoarea `clasament` (lângă `cautare`, `neclar`, `in_afara`). Regula „clasamente de
  tipul «cine are cel mai mic…»” iese din lista `in_afara` a promptului.
- Câmpuri noi în schemă, ambele cu `null` permis, deci `cautare` nu se schimbă:
  - `segment`: `pf` / `pfa` / `imm` / `pj`; `null` = PF la clasamentele de comisioane. Folosit și la
    căutare: segmentul cerut vine primul în rezumat și în rânduri (restul rămân, în ordinea PF, PFA,
    IMM, PJ, fără segment).
  - `metrica`: `mediana` / `cea_mai_buna`; `null` = mediana. „Cea mai ieftină variantă”, „cel mai mic
    comision posibil”, „cea mai mare dobândă oferită” cer `cea_mai_buna`: minimul la comisioane și
    credite, maximul la depozite.
- `banci` într-un clasament = băncile evidențiate (cel mult 3); Libra e evidențiată mereu. „Unde stă
  Libra la …?” e un clasament.
- Continuări: „și pentru firme?” după un clasament rămâne clasament, cu alt segment; o bancă numită în
  continuarea unui clasament („dar la BCR?”) face o căutare la acea bancă, pe același concept.
- Ce se poate clasa: conceptele din grupurile 2.1 (`GRUPURI`: 14 comisioane, în lei) și 2.2
  (`GRUPURI_RATE`: `nominala`, `dae`, `marja_ircc`, `comision_procent`, cu categorie). Promptul le
  marchează; lista vine din `_context_vox` (cheia `clasabile`), construită din `GRUPURI` și
  `GRUPURI_RATE`, deci nu se scrie de mână.
- Validare (`valideaza`): `segment` și `metrica` doar din listele lor; la clasament, `dae` și
  `marja_ircc` primesc categoria `credite`, `comision_procent` primește `conturi_carduri`; `nominala`
  fără categorie devine `neclar` (ca orice interpretare incompletă); un concept care nu se poate clasa
  rămâne `clasament`, iar serverul răspunde cu `neclasabil`.
- Evaluarea: ~10 întrebări de clasament noi în `app/vox_exemple.json` (RO și EN, mediana și „cea mai
  ieftină variantă”, „pentru firme”, „unde stă Libra”, o continuare, un concept neclasabil). O rulare
  `python app/eval_vox.py --da` (~$0,08), la final, doar cu acordul lui Nicolae.

## Serverul

**O singură interogare pentru celule, comună paginilor și lui Vox.** Interogarea `celule` din
`matrice` devine `celule_matrice(campuri, unitate, segment)` (pragul `PRAGURI["suma"]`, `COND_SEG`,
rândul de la mediană), iar cea din `rate` devine `celule_rate(campuri, categorie, termen, produs)`
(pragul categoriei, termenul, tipul de credit, mediana). `matrice` și `rate` le apelează; rezultatele
lor rămân identice, verificat înainte și după pe `mip_merge` (toate grupurile × segmentele `pf`,
`pj`, `pfa`, `toate` × unitățile; toate categoriile × termenele × produsele).

**Cititorul pentru Vox:** `_clasament_vox(concept, categorie, termen, produs, segment)` →
- comision (conceptul e într-un grup din `GRUPURI`): `celule_matrice([concept], "lei", segment or "pf")`;
- dobândă (conceptul e în `GRUPURI_RATE[categorie]["campuri"]`): `celule_rate([concept], categorie,
  termen, produs)` și, dacă întrebarea are termen sau tip de credit, al doilea bloc cu termenul →
  `necunoscut` și tipul de credit → `altele` („nespecificat în sursă”);
- întoarce `{sursa: "matrice" | "rate", grup, unitate, sens, blocuri: [{tip: "exact" | "nespecificat",
  celule}]}` sau `None` dacă nu se poate clasa.

**Băncile fără date:** `_stare_banci_vox()` = o interogare grupată pe bancă (surse, blocate, din care
`ROBOTS…`, din care PDF). `_stare_banca_vox(banca)` o folosește, deci regula motivului stă într-un loc.

**Clasamentul, în `app/vox.py`** (funcție pură, testabilă fără bază), peste blocurile primite:
- cifra: mediana (`valoare`) sau cea mai bună variantă (`minim` la `mic_bun`, `maxim` la `mare_bun`);
- ordinea după `sens`: crescător la comisioane și credite, descrescător la depozite; la egalitate,
  după numele băncii;
- locuri comune la egalitate: `loc` și `loc_pana` („locurile 1–5”);
- `evidentiata` pe Libra și pe băncile din `banci`; `libra`: locul și din câte bănci;
- `fara_date`: băncile din `banci` (context) fără niciun rând în niciun bloc, cu motivul lor.

**Răspunsul:** cheia nouă `clasament` (lângă `raspunsuri`, care rămâne gol la un clasament):
`{concept, sursa, grup, unitate, sens, metrica, segment, categorie, termen, produs, blocuri: [{tip,
randuri: [{loc, loc_pana, banca, valoare, minim, maxim, n, serviciu, frecventa, conditie,
segment_necunoscut, evidentiata}]}], libra, fara_date}` sau `{concept, neclasabil: true}`. Tura se
salvează în istoric ca orice răspuns; jurnalul de costuri primește numărul de bănci clasate.

## Interfața

- Componentă nouă `web/src/pages/vox/Clasament.tsx` (pagina Vox are deja ~600 de linii).
- Antet: conceptul · segmentul (la comisioane) · termenul / tipul de credit · cifra („mediana” sau
  „cea mai bună variantă”) · „de la cel mai avantajos pentru client” · câte bănci au date.
- Tabel: Loc (cu „1–5” la egalitate) · Bancă · Valoare · Interval · Valori · „Vezi dovezile”; serviciul
  de la mediană sub valoare, doar la mediană. Rândul Libra și băncile numite, evidențiate. Primele 10
  rânduri plus cele evidențiate, „Arată toate (N)”.
- Blocul „termen nespecificat în sursă”, dedesubt, cu același tabel și titlul lui.
- Băncile fără date, pe un rând, grupate pe motiv (blocate · fără surse · PDF-uri interzise de
  robots.txt · fără valoare în sursele colectate).
- „Vezi dovezile” deschide sertarul cu filtrele celulei: comision → `unitate: 'lei'`, `segment` (regula
  din 2.1, fără `strict`); dobândă → `unitate: 'procent'`, `scenariu: categorie`, termenul și tipul de
  credit ale blocului. Sertarul arată deci rândurile celulei din 2.1 / 2.2.
- Link „Deschide în 2.1” (`#/produse?grup=…&segment=…`) sau „Deschide în 2.2”
  (`#/rate?categorie=…&termen=…&produs=…`).
- `neclasabil`: mesaj fix, „Pentru {concept} nu avem un clasament; întreabă de o bancă anume.”
- Textele în `i18n/dict/vox.ts` (`vox.clasament.*`), perechi RO / EN.
- Zod: `Clasament` în `shared/src/vox.ts`; `RaspunsIntrebare.clasament` opțional, deci conversațiile
  salvate fără el se citesc ca acum.

## Teste și verificări

- `app/test_vox.py` (client fals): clasamentul (sens, mediana / cea mai bună, egalități, Libra și
  băncile evidențiate, blocul nespecificat, băncile fără date), `neclasabil`, validarea câmpurilor noi
  (categorie implicită, `nominala` fără categorie, segment și metrică necunoscute), segmentul cerut
  primul la căutare, interpretarea veche fără câmpurile noi ca `anterior`.
- `app/test_celula.py`, clasă nouă: ce intră în SQL-ul lui `celule_matrice` / `celule_rate` (segmentul,
  pragul, termenul, tipul de credit, parametrii în ordine).
- Script pe `mip_merge`: `matrice` și `rate` identice înainte și după; clasamentul fiecărui concept
  clasabil dă exact celulele lui din 2.1 / 2.2; `_stare_banci_vox` = `_stare_banca_vox` pe toate băncile;
  criteriile de reușită de mai sus.
- Playwright pe :8797 (POST-urile spre `/api/vox` răspunse din fișier, cu model fals): fișa
  clasamentului, sertarul unui rând = celula din 2.1, linkul cu filtrele, ambele teme, RO și EN,
  conversațiile vechi.
- `npm run typecheck`; `verifica_pagini.py` pe :8797. `npm run build` îl rulează Nicolae.
- Plătit: doar `eval_vox.py --da`, o dată, la final, cu acordul lui Nicolae (~$0,08).

## Documentație

README (secțiunea „Vox”: clasamentele), memoria Serena `cod/harta` (`celule_matrice`, `celule_rate`,
`_clasament_vox`, `_stare_banci_vox`, tipul `clasament`), planul în
`docs/superpowers/plans/2026-10-07-vox-clasamente.md`.

## Fișiere

- `app/server.py`: `celule_matrice`, `celule_rate` (scoase din `matrice` / `rate`), `_clasament_vox`,
  `_stare_banci_vox`, `_stare_banca_vox` (prin `_stare_banci_vox`), `_context_vox` (`clasabile`),
  `VOX` (cititorul nou).
- `app/vox.py`: `TIPURI`, `CHEI`, `schema`, `prompt`, `valideaza`, funcția de clasament, `rezuma` /
  `_ordine_segment` (segmentul cerut primul), `Vox.intreaba`.
- `app/test_vox.py`, `app/vox_exemple.json`.
- `shared/src/vox.ts`.
- `web/src/pages/vox/Clasament.tsx` (nou), `web/src/pages/Vox.tsx`, `web/src/styles/vox.css`,
  `web/src/i18n/dict/vox.ts`.
