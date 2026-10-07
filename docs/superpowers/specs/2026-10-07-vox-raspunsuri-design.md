# Vox: răspunsuri care nu induc în eroare (segment, termen, motivul lipsei)

Data: 07.10.2026. Ramura `vox-chatbot` (unită deja în `main` prin PR #4). Design aprobat în discuție
cu Nicolae Cherascu, pe secțiuni. Cifrele sunt măsurate pe baza `mip_merge`, 07.10.2026.

## Ce vrea utilizatorul

Un răspuns Vox pe care cineva din marketing îl citește fără să fie indus în eroare. Azi, trei lucruri
îl induc:

1. **Persoanele fizice și firmele sunt amestecate.** „Cât costă administrarea contului la BCR?” dă
   570 de valori: 302 PJ, 234 PFA, 33 PF, 1 fără segment. Fișa arată un singur interval (0–1.200 lei),
   iar rândurile nu spun segmentul. Pagina 2.1 are filtru de segment; `celula` și Vox nu știu de el.
   Aceeași lipsă e și în sertarul din 2.1 și Versus: filtrat pe PF, arată și valorile PJ.
2. **Termenul cerut golește răspunsul.** „Dobânda la depozit pe 12 luni” dă 0 valori la 28 din 30 de
   bănci, inclusiv Libra, BCR, BRD, ING. Din 91 de dobânzi la depozite, doar 29 au termen citit
   (4 bănci). La Libra, citatul e „lei - dobândă 4.75%”: termenul s-a pierdut la extracție.
3. **„Nu avem valori” nu spune de ce.** `_stare_banca_vox` explică doar „toate sursele blocate” și
   „nicio sursă”. ING are 48 de PDF-uri interzise de `robots.txt` (printre ele lista de taxe și
   comisioane) din 158 de surse, deci fișa tace; se poate citi „ING nu percepe comisionul”.

Criterii de reușită (verificate cu scriptul de acoperire, fără model):
- BCR · administrare cont: rândurile se împart PF 33 / PFA 234 / PJ 302 / fără segment 1, grupele
  rezumatului vin în ordinea PF, PFA, PJ, fără segment, iar fiecare rând are pastila segmentului;
- Libra · depozit 12 luni: 11 valori (cele fără termen în sursă), cu nota care spune ce filtru a căzut;
  BCR 2, ING 2, BRD 1; băncile cu 0 scad de la 28 la 20;
- ING · administrare cont: fișa spune că 48 de documente PDF ale ING sunt interzise de `robots.txt`;
- sertarul din 2.1 filtrat pe PF și cel din Versus arată exact rândurile celulei;
- sertarul deschis dintr-o grupă Vox arată exact rândurile ei (același segment, unitate și
  categorie), plus cele ambigue, marcate, ca azi.

## Ce nu intră

- Prompt sau schemă nouă pentru model: modelul nu află de segment, deci nu e nevoie de evaluare
  plătită. „Pentru firme” arată tot toate segmentele, PF primul.
- Migrare sau coloane noi în `observatii_curente`.
- Problema 3 (bannerul Libra cu 7,81% citit pe 31 de pagini): sub-proiect separat, în `ingest/`,
  după acesta.
- Extragerea termenului din citat sau din antetul tabelului (extracție, nu afișare).

## 1. Segmentul

### O singură regulă, pe server

În `app/server.py`, înaintea lui `matrice`:
- `SEGMENT_RAND`: expresia SQL care scoate segmentul rândului din `cod_scenariu`:
  `substring(coalesce(o.cod_scenariu, '') from '(?:^|\|)(pf|pj|pfa|imm)(?:\||$)')`, `NULL` când sursa
  nu-l marchează. Verificat: `SEGMENT_RAND = 'pf' OR SEGMENT_RAND IS NULL` dă exact rândurile lui
  `COND_SEG` din `matrice` (10.975 = 10.975 pe toată baza).
- `COND_SEG` iese din `matrice` în modul (aceeași regulă, aceeași valoare); `matrice` o folosește ca
  înainte, deci 2.1, Versus și fișa de bancă nu se schimbă.
- `ORDINE_SEGMENT = ("pf", "pfa", "imm", "pj")`, apoi rândurile fără segment. Stă în `app/vox.py`:
  serverul importă `vox`, nu invers, iar `celula` acceptă la `segment` doar valorile de aici.

### `celula` (`/api/celula`)

Parametri noi, opționali:
- `segment`: gol sau `toate` = fără filtru (ca azi); `pf` / `pfa` / `imm` / `pj` = regula din 2.1
  (segmentul plus rândurile fără segment în sursă, `COND_SEG`); `nemarcat` = doar rândurile fără
  segment. Altă valoare se ignoră (ca `termen` și `produs`).
- `strict`: `1` = doar segmentul cerut, fără rândurile nemarcate. Îl trimite doar Vox.

Fiecare rând întors capătă `segment` (`pf` / `pfa` / `imm` / `pj` / `null`).

### Vox

- `rezuma` grupează pe `(segment, unitate, categorie)`; grupa are în plus `segment` (null = fără
  segment în sursă). Ordinea: segmentul în `ORDINE_SEGMENT`, nemarcatele la final, apoi după număr.
- Fiecare segment are grupa lui: un rând nemarcat nu intră și la PF (fără dublări).
- `_raspuns` ordonează rândurile stabil după segment înainte de tăierea la `MAX_RANDURI`, ca primele 50
  să fie PF. La căutarea după text, SQL-ul se oprește la 50 înainte, deci ordonarea e doar între ele.
- Butonul „Vezi dovezi” al unei grupe deschide sertarul cu `segment` = segmentul grupei (sau
  `nemarcat`) și `strict=1`: 251 din 752 de perechi bancă·concept au și rânduri marcate, și nemarcate,
  iar fără `strict` grupa „33 PF” ar deschide un sertar mai lung.

### Interfața

- Fișa Vox: grupele pe rânduri, câte unul pe segment (eticheta segmentului, apoi plăcuțele pe
  unitate și categorie); în tabel, pastila segmentului pe fiecare rând (`Pill`).
- `Sertar`: `CerereSertar` primește `segment?` și `strict?`, trimise la `/api/celula`; rândul arată
  pastila segmentului când există.
- 2.1 (`Produse.tsx`) trimite segmentul ales în filtru (nimic la `toate`); Versus trimite `pf` la
  grupele din `matrice` (matricea lui e pe `pf`), nimic la cele din `rate`. Fișa de bancă rămâne pe
  `toate`, ca azi.
- Etichetele segmentelor în `i18n` (perechi RO / EN), refolosite unde există deja.

## 2. Termenul și tipul de credit

Când răspunsul exact iese gol, `_raspuns` încearcă, în ordine, oprindu-se la primul care aduce valori:
1. `termen` → `necunoscut` (dacă întrebarea are termen): doar dobânzile al căror termen nu e scris în
   sursă (`TERMEN_LUNI IS NULL`, filtrul existent din `celula` și 2.2). Nu aduce dobânzile cu alt
   termen recunoscut: BCR are 6% pe 5 luni, care ar răspunde greșit la „12 luni”.
2. în plus `produs_credit` → `altele` („nespecificat în sursă”, din `PRODUSE_CREDIT`), dacă întrebarea
   are tip de credit.
3. nimic: rămâne ca azi, `fara_filtre` = câte valori sunt fără niciun filtru, cu butonul spre ele.

Câmp nou `filtre_relaxate`: `[]`, `["termen"]` sau `["termen", "produs"]` (ori `["produs"]` când
întrebarea n-are termen). Fișa arată direct valorile, cu o notă din `i18n`, de pildă „Nicio dobândă
pe 7–12 luni cu termenul scris în sursă. Sunt cele 11 la care sursa nu spune termenul.” Interpretarea
rămâne cea a modelului, deci „și pe 6 luni?” continuă corect.

## 3. De ce lipsește o bancă

`_stare_banca_vox(banca)` întoarce, în loc de un text:
`{"stare": "blocata" | "fara_surse" | null, "surse": n, "robots": k, "refuzate": m, "pdf": p}`,
numărate din `surse`:
- `robots`: blocate cu nota care începe cu `ROBOTS` (scrisă de `populare_initiala.py`);
- `refuzate`: celelalte blocate („blocat de bancă…”: WAF, HTTP 403);
- `pdf`: câte dintre cele blocate au `format = 'pdf'`.

`RaspunsBanca` păstrează `stare_banca` și primește `blocaje: {surse, robots, refuzate, pdf} | null`
(doar când banca are 0 valori). Fișa goală:
- `blocata` / `fara_surse`: textul de azi;
- altfel, cu blocaje: „48 de documente PDF ale ING sunt interzise de robots.txt; ce e în ele nu
  colectăm.” / „16 din 136 de surse ale Patria sunt interzise de robots.txt.”;
- fără blocaje: „Valoarea n-a apărut în cele N surse colectate ale băncii.”;
- mereu, la final: „Lipsa din bază nu înseamnă că banca nu are produsul sau comisionul.”

Măsurat azi: blocaje parțiale la ING (48 robots, toate PDF), Patria (16 robots, 1 PDF), Revolut
(3 robots), BRD (1 robots, PDF), Nexent (2 refuzate, PDF); BT, CEC, Intesa, UniCredit rămân „blocată”.

## Compatibilitate

Conversațiile salvate (`loguri/vox/conversatii/`) au răspunsurile în forma veche. Câmpurile noi sunt
opționale în Zod (`segment` pe `ValoareDovada` și `GrupaRezumat`, `filtre_relaxate`, `blocaje` pe
`RaspunsBanca`): o conversație veche se redeschide și arată ca atunci, fără pastile de segment.
Fără `segment` / `strict`, `/api/celula` întoarce aceleași rânduri ca azi, cu câmpul `segment` în plus.

## Teste și verificări (toate fără cost)

- `app/test_vox.py` (client fals): gruparea și ordinea pe segment; ordonarea rândurilor înainte de
  tăiere; lanțul exact → termen necunoscut → și produs necunoscut → `fara_filtre`; `blocaje` și
  `stare_banca`; o tură în forma veche se citește.
- Script pe `mip_merge`: `celula` cu `segment=pf` dă rândurile celulei PF din 2.1 (BCR · administrare
  cont); cu `strict=1` doar PF; `nemarcat` doar nemarcatele; fără parametri, aceleași rânduri ca
  înainte de schimbare pe un eșantion de celule din 2.1, 2.2 și Versus.
- Scriptul de acoperire, cu criteriile de reușită de mai sus.
- `npm run typecheck`; `MIP_URL=http://localhost:8797 python app/verifica_pagini.py`; Playwright pe
  :8797 (POST-urile spre `/api/vox` blocate, răspunsuri false): fișa nouă, sertarul din 2.1 pe PF,
  ambele teme, RO și EN. `npm run build` îl rulează Nicolae.

## Documentație

README (secțiunea „Vox”), memoria Serena `cod/harta` (`celula` cu `segment` / `strict`,
`SEGMENT_RAND`), planul în `docs/superpowers/plans/2026-10-07-vox-raspunsuri.md`.

## Fișiere

- `app/server.py`: `SEGMENT_RAND`, `COND_SEG`; `matrice` (constanta mutată);
  `celula` (`segment`, `strict`, câmpul `segment`); `_stare_banca_vox`. `_cauta_vox` rămâne fără
  segment: Vox ia toate rândurile și le grupează el.
- `app/vox.py`: `ORDINE_SEGMENT`, `rezuma`, `Vox._raspuns`.
- `app/test_vox.py`; `app/test_celula.py` (nou: ce intră în SQL-ul lui `celula`, fără bază).
- `shared/src/celula.ts`, `shared/src/vox.ts`.
- `web/src/components/Sertar.tsx`, `web/src/components/valori.ts` (`etSegment`),
  `web/src/pages/Produse.tsx`, `web/src/api/versus.ts` (`SEGMENT_VERSUS`),
  `web/src/pages/versus/Sectiune.tsx`, `web/src/pages/Vox.tsx`, `web/src/styles/vox.css`,
  `web/src/i18n/dict/vox.ts`, `web/src/i18n/dict/comun.ts` (etichetele segmentelor, comune
  sertarului și lui Vox).
