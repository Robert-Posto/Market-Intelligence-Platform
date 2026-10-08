# Vox: întrebări despre aplicațiile băncilor (funcțiile și notele)

Data: 08.10.2026. Ramura `vox-chatbot`. Design aprobat în discuție cu Nicolae Cherascu, pe secțiuni.
Cifrele sunt măsurate pe `mip_merge` și pe `date/google_play.json`, 08.10.2026.

## Ce vrea utilizatorul

Azi Vox răspunde `in_afara` la orice întrebare despre aplicații, deși aplicația are datele:
- analiza statică a 24 de aplicații Android (22 de bănci), cu 13 funcții, fiecare cu verdict și dovadă;
- notele din App Store, în bază: 19 aplicații;
- notele din Google Play, în `date/google_play.json`, fișierul pe care îl citește și 2.3: 22 de aplicații.

Vox trebuie să răspundă despre funcțiile unei aplicații și despre notele ei, cu aceleași verdicte și
aceleași note ca 2.3 și pagina Android. Modelul doar interpretează întrebarea. Verdictele și notele vin
din datele colectate, niciodată de la model.

Criterii de reușită:
- **„Ce bănci au RoPay?”:** băncile grupate pe verdict, după aplicația principală, cu Libra evidențiată:
  - sigur 8: BT, BCR, BRD, CEC, ING, Raiffeisen, Salt, Vista;
  - probabil 1: UniCredit;
  - absent 6: Credex, Garanti, Intesa, Libra, ProCredit, Revolut;
  - neconcludent 7: BRCI, Citibank, Exim, Nexent, Patria, TBI, TechVentures.
  Sub grupe apar cele 8 bănci fără aplicație analizată.
- **„Ce are BT Pay și n-are Libra?”:** tabelul celor 13 funcții, cu BT Pay și Libra Bank pe coloane. Sunt
  marcate 4 rânduri: chatul, marketingul și RoPay (BT da, Libra nu), apoi asistentul vocal (Libra da,
  BT nu).
- **„Ce notă are aplicația Libra?”:**
  - Google Play: 4,59 din 3.083 de note (06.10.2026), locurile 8–10 din 22, împreună cu BT și CEC;
  - App Store: 4,47 din 971 de note (24.09.2026), locurile 10–11 din 19, împreună cu Intesa.
- **„Care bancă are cea mai bună aplicație?”:** două clasamente, după nota din magazine.
  - Google Play: locurile 1–5 la 4,8, în ordinea numărului de note: Revolut, BRD, ING, BCR, UniCredit.
  - App Store: ProCredit pe locul 1, cu 5,0 din 6 note. E urmarea deciziei „fără prag”; numărul de note
    stă lângă notă. Urmează locurile 2–4 la 4,9: Revolut, ING, Citibank.
- **„Are BCR Apple Pay?”:** fișa spune că Apple Pay nu e printre funcțiile analizate și arată aplicația
  George, cu cele 13 funcții.
- **Rămân `in_afara`:** „Ce scriu clienții despre BT Pay?” și „Câte trackere are aplicația ING?”.
- **Butonul „La toate băncile”:** după „Are George plata contactless?”, arată plata contactless la toate
  băncile, fără model, cu cost 0.
- **Compatibilitate:** conversațiile salvate înainte se redeschid neschimbate, iar evaluarea trece 52
  din 52.

## Ce nu intră

- **Restul datelor despre aplicații** rămân în 2.3 și pe pagina Android, iar întrebările despre ele ies
  `in_afara`:
  - recenziile, inclusiv rezumatele AI;
  - trackerele și permisiunile;
  - portofelele și bibliotecile;
  - textele de ecran și istoricul versiunilor.
- **Aplicațiile secundare** (MyBRD Mobile, Avantaj): fișa spune doar că există și trimite la pagina Android.
- **Un prag de note în clasament.** Decizia lui Nicolae din 08.10.2026: fără prag, cu numărul de note alături.
- **Vox pe `mcc-test`.**
- **Paginile 2.3 și Android** rămân neschimbate. Singura atingere e exportul lui `FUNCTII` din `model.ts`.

## Interpretarea

- **Contractul.** `TIPURI` primește `aplicatii`, iar `CHEI` primește `functie` și `aspect`. În schemă,
  ambele pot fi `null`:
  - `functie` are un `enum` construit din `android_functionalitati` (13 funcții azi). Lista vine din
    `_context_vox`, în `ctx["functii"]`, cu titlul din bază („RoPay (plăți instant din cont)”).
  - `aspect` ia `functii` sau `note` (constanta `ASPECTE`).
- **Contextul.** `_context_vox` mai dă `ctx["aplicatii"]`: banca și numele fiecărei aplicații din
  `android_aplicatii` (24, cu tot cu secundarele). Așa, „George” duce la `bcr`, iar „MyBRD” la `brd`.
- **Promptul:**
  - Descrierea de la început spune că întrebarea poate fi și despre aplicațiile băncilor: funcțiile
    găsite în analiza aplicațiilor Android și notele din magazine.
  - **Regula nouă:** `tip = aplicatii` pentru funcțiile unei aplicații sau pentru nota ei.
    - `functie` e funcția din listă.
    - `aspect = note` acoperă notele și clasamentul lor; „cea mai bună aplicație” înseamnă „după notă”.
    - `banci` conține băncile numite sau cele ale aplicațiilor numite.
    - O funcție care nu e în listă primește `functie = null`, iar numele ei merge în `text_cautat`.
  - **Regula `in_afara`** se restrânge la: recenzii, trackere, permisiuni, campanii, sfaturi, texte de
    scris, întrebări generale. Exemplul „care bancă are cea mai bună aplicație?” trece la `aplicatii`.
  - **Listele noi** vin din bază, în ordine fixă, pentru că cache-ul cere un prefix stabil: „Funcțiile
    aplicațiilor (slug: titlu)” și „Aplicațiile (bancă: nume)”.
  - Tokenii și costul promptului se măsoară după implementare.
- **`valideaza`:**
  - `functie` se acceptă doar din `ctx["functii"]`, iar `aspect` doar din `ASPECTE`. La celelalte tipuri,
    ambele devin `null`.
  - La `aplicatii`:
    - cu `functie`, `aspect` devine `functii`;
    - fără `aspect`, devine `functii` dacă sunt bănci sau `text_cautat`;
    - fără funcție, bănci, `text_cautat` și `note`, tipul devine `neclar`, iar pagina arată mesajul ei fix;
    - `clarificare = null`, ca la clasament;
    - cel mult 3 bănci (`MAX_BANCI`).
- **Continuările** („și la BRD?”, „dar Google Wallet?”) urmează regula existentă din prompt.
  Interpretarea anterioară primită de model conține și câmpurile noi.
- **Compatibilitatea.** `verifica_anterior` acceptă deja o interpretare fără câmpurile noi, pentru că
  cere doar ca toate cheile ei să fie din `CHEI`.

## Cititorul

Funcția nouă `_aplicatii_vox()` din `app/server.py` ajunge la `Vox` prin parametrul nou `aplicatii=`,
la fel cum ajunge `clasament`. Întoarce toate aplicațiile, pentru că sunt puține: 24 de aplicații ×
13 funcții, plus 19 note App Store și 22 Google Play. Filtrarea pe bănci se face în `vox.py`.
Interogările trec prin `interoghează`.
- **Aplicația unei bănci** e cea cu `rol` `principal` din `android_aplicatii`, sau `reper` la Libra.
  - Secundarele (`rol = secundar`) contribuie doar cu numele, în `secundare`.
  - Pachetul aplicației principale e chiar cel din Google Play, la toate cele 22 de bănci (verificat pe
    08.10.2026).
- **Funcțiile:** `android_functionalitati` (`verdict`, `surse`, `dovada_text`), pe pachetul aplicației
  principale. Versiunea analizată și data ei vin din `android_versiuni` (`data_extragere`: 01.10.2026 la
  toate cele 24).
- **App Store:** `app_release_curente`, cu `platforma = 'ios'`.
  - Câmpuri: `rating_agregat`, `volum_rating`, `distributie_stele`, `versiune`, `observat_la` (24.09.2026).
  - Linkul este `https://apps.apple.com/ro/app/id{app_id}`, ca în `ComparaLibra.tsx`.
- **Google Play:** `date/google_play.json`, cheia băncii din `aplicatii`.
  - Câmpuri: `nota`, `evaluari`, `distributie_stele`, `versiune`, `url`; data vine din `colectat_la`
    (06.10.2026).
  - Fișierul (52 KB) se citește la fiecare întrebare.
  - Dacă lipsește sau e stricat, `play = null`, iar răspunsul merge mai departe cu restul.
- **Băncile fără nicio aplicație** în cele trei surse sunt azi 8: BankOfChina, Banorient, BCR
  Locuințe, BID, BNP Paribas, Cetelem, Creditcoop, PKO.

## Răspunsul

`Vox._aplicatii_raspuns(interp, ctx)` construiește răspunsul din ce dă cititorul. `_raspunde` îl pune
în cheia nouă `aplicatii`, care e `null` la celelalte tipuri. Regulile stau în funcții pure din
`vox.py`, testate fără bază.

**Vederile (`vedere`):**
- **`functie`**, cu funcție și fără bănci:
  - `grupuri` pe verdict, în ordinea sigur, probabil, absent, neconcludent;
  - în fiecare grupă, aplicațiile în ordinea alfabetică a băncii, cu `banca`, `aplicatie`, `surse` și
    `dovada_text`.
- **`aplicatii`**, cu bănci, cu sau fără funcție:
  - `coloane`, câte una pe bancă, în ordinea din întrebare;
  - fiecare coloană are `aplicatie`, `versiune_analizata`, `data_analizei`, `framework`, `secundare`,
    `functii` (verdictul, sursele, textul găsit) și notele din cele două magazine, sau `null`;
  - o bancă numită fără aplicație analizată are `fara_aplicatie = true`;
  - `diferente` sunt funcțiile pe care o aplicație le are (sigur sau probabil), iar alta nu (absent).
    Un `neconcludent` nu face diferență.
  - Cu `text_cautat` și fără `functie`, vederea rămâne `aplicatii`, iar fișa spune că funcția nu e
    analizată.
- **`note`:**
  - `clasamente` pe magazin (`play`, `app_store`);
  - cu bănci, și `carduri`: nota, numărul de note, distribuția pe stele, versiunea, linkul și locul în
    fiecare clasament (`loc`, `loc_pana`, `din`).
- **`neanalizata`**, pentru o funcție care nu e în listă, fără bănci: doar `text_cautat`. Fișa arată
  atunci funcțiile analizate.

**Câmpuri comune tuturor vederilor:**
- `functie` și `text_cautat`;
- datele surselor: `analiza_la`, `app_store_la`, `play_la`;
- `banci_fara_aplicatie`, lista băncilor fără nicio aplicație.

**`vox.clasa_note(randuri, evidentiate)`**, funcție pură:
- Ordonează după nota rotunjită la o zecimală, cu `ROUND_HALF_UP` pe valoarea din sursă (4,65 → 4,7).
- Aplicațiile cu aceeași notă rotunjită au loc comun (`loc`, `loc_pana`). Între ele, ordinea e după
  numărul de note, descrescător.
- Nu există prag. Aplicațiile fără notă stau la final, fără loc.
- Libra și băncile numite primesc `evidentiat`.

**`vox.diferente(coloane)`**, funcție pură: întoarce funcțiile marcate în vederea `aplicatii`.

**Jurnalul** primește `aplicatii`: câte aplicații arată răspunsul.

## Butoanele

- `BUTOANE` primește `toate: "La toate băncile"`.
- `butoane()` la tipul `aplicatii`:
  - `libra`: întrebarea are bănci, Libra nu e printre ele și sunt mai puțin de 3;
  - `toate`: întrebarea are bănci și, în plus, are `functie` sau `aspect = note`.
- `din_buton` la tipul `aplicatii`:
  - `libra` dă `banci + [libra]`;
  - `toate` dă `banci = []` și păstrează `functie` și `aspect`;
  - `firme`, `pf` și orice buton nepotrivit ridică `Respins`, adică 400.
- Restul drumului nu se schimbă: `Vox.continua`, fără model, cu cost 0.

## Interfața

- **Componenta nouă** `web/src/pages/vox/Aplicatii.tsx` e chemată din `Raspuns` (`Vox.tsx`) când
  răspunsul are `aplicatii`.
- **Ce refolosește:**
  - `Verdict`, din `pages/rate_mobil/android/comune.tsx`;
  - `BareStele`, din `components/BareStele.tsx`;
  - `Stele`, din `pages/rate_mobil/Piese.tsx`;
  - `SiglaBanca`, din `components/comune.tsx`;
  - textele `mobil.android_f.*`, `mobil.android_fs.*`, `mobil.android_verdict.*`,
    `mobil.android_verdict_d.*`, `mobil.android_sursa.*` și `mobil.note_google_play`;
  - ordinea funcțiilor din `FUNCTII` (`pages/rate_mobil/android/model.ts`), care devine exportată.
- **Vederea `functie`:**
  - patru grupe, fiecare cu numărul de aplicații și cu explicația verdictului sub titlu;
  - aplicațiile apar ca pastile: sigla și numele băncii; în tooltip, numele aplicației, sursele și
    textul găsit;
  - Libra e evidențiată;
  - dedesubt, nota paginii Android („o bifă spune că aplicația are funcția, nu că e activă pentru toți
    clienții”), un link spre pagina Android și lista „fără aplicație analizată: …”.
- **Vederea `aplicatii`:**
  - un antet pe fiecare coloană: aplicația, notele, versiunea analizată, framework-ul, secundarele;
  - dedesubt, tabelul funcțiilor, cu `Verdict` și cu tooltip (sursele, textul găsit);
  - rândurile din `diferente` sunt marcate;
  - funcția din întrebare stă pe primul rând, evidențiată;
  - nu există total.
- **Vederea `note`:**
  - două tabele, Google Play și App Store;
  - coloane: locul (comun, de forma „1–5”), banca, aplicația, nota cu o zecimală (valoarea din sursă în
    tooltip), numărul de note, linkul;
  - Libra și băncile numite sunt evidențiate;
  - când întrebarea are bănci, cardurile lor stau deasupra.
- **Funcția neanalizată:** o propoziție și lista celor 13 funcții.
- **Sursa și data** apar în fiecare vedere: „analiza APK, 01.10.2026”, „App Store, 24.09.2026”, „Google
  Play, 06.10.2026”. Fără fișierul Google Play, apare „Google Play necolectat”.
- **Textele noi** stau în `i18n/dict/vox.ts`, sub `vox.aplicatii.*`, ca perechi RO / EN. Datele băncilor
  (numele aplicațiilor, textul găsit) nu se traduc.
- **Zod** (`shared/src/vox.ts`): `functie` și `aspect` sunt opționale în interpretare, iar `aplicatii`
  e opțional în răspuns.
- **Stilurile** stau în `styles/vox.css`.

## Teste și verificări

- **`app/test_vox.py`**, fără rețea și fără bază:
  - schema: `functie` are `enum` din context, iar `aspect` există; promptul conține funcțiile,
    aplicațiile și regula `in_afara` nouă;
  - `valideaza`: valorile din liste, golirea câmpurilor la alte tipuri, `functie` → `aspect = functii`,
    `neclar` fără nimic, cel mult 3 bănci;
  - o interpretare veche, fără câmpurile noi, e acceptată;
  - `clasa_note`: 4,83 / 4,81 / 4,79 dau locurile 1–3; la aceeași notă, ordinea e după numărul de
    note; 4,65 → 4,7; fără notă, la final;
  - `diferente`: sigur + absent fac diferență; sigur + probabil și orice `neconcludent`, nu;
  - `butoane` și `din_buton`: `libra`, `toate` și refuzurile (`firme` la `aplicatii`, `toate` fără bănci);
  - `_raspunde` cu un cititor fals: forma răspunsului în cele patru vederi și cazul `play = null`;
  - HTTP: un `POST` cu butonul `toate` primește 200, fără apel la model.
- **Pe baza reală, cu un model fals:** criteriile de reușită (RoPay, BT Pay vs Libra, notele Libra,
  clasamentele, Apple Pay, butonul).
- **Pagina:** Playwright pe :5173, cu API-ul pe serverul temporar :8797 și răspunsurile `POST` luate din
  fișiere. Se verifică cele patru vederi și butoanele, în RO și EN, cu tema luminoasă și cu cea
  întunecată, cu consola curată. Conversațiile vechi trebuie să se redeschidă.
- **Build și pagini:**
  - `npm run typecheck`;
  - build-ul de verificare într-un dosar temporar: `npm -w web exec -- vite build --outDir <tmp> --emptyOutDir`;
  - `python app/verifica_pagini.py` pe :8797.
- **Evaluarea**, în `app/vox_exemple.json`:
  - 8 întrebări noi: RoPay; George și plata contactless; funcțiile BRD; BT Pay vs Libra; Apple Pay la
    BCR; recenziile BT Pay (`in_afara`); trackerele ING (`in_afara`); „și la BRD?” după întrebarea despre
    George;
  - două întrebări își schimbă așteptarea din `in_afara` în `aplicatii` cu `aspect = note`: „Ce notă
    are aplicația Libra în App Store?” și „Care bancă are cea mai bună aplicație?”;
  - în total, 52 de întrebări;
  - `python app/eval_vox.py --da` rulează doar cu acordul lui Nicolae, după ce i se spune estimarea.
    Reper: cele 44 de întrebări au costat $0,0963 pe 08.10.2026.

## Documentație

- **README, secțiunea Vox:** aplicațiile, adică sursele cu datele lor, vederile, clasamentul fără prag și
  costul măsurat. Fraza „Aplicațiile și campaniile nu intră” se schimbă.
- **`CLAUDE.md`:** regula Vox spune „cifrele vin din bază”. Se reformulează așa încât să cuprindă și
  notele Google Play din `date/google_play.json`, ca în 2.3, păstrând „niciodată de la model”. Numărul de
  linii nu crește.
- **Harta Serena (`cod/harta`):** tipul `aplicatii`, `_aplicatii_vox`, `clasa_note`, `diferente` și
  butonul `toate`.
- **`docs/HANDOFF_VOX.md`** (necomis): starea.

## Fișiere

- `app/vox.py`: `TIPURI`, `CHEI`, `ASPECTE`, `schema`, `prompt`, `valideaza`, `clasa_note`, `diferente`,
  `BUTOANE`, `butoane`, `din_buton`, `Vox` (`aplicatii=`, `_aplicatii_raspuns`, `_raspunde`).
- `app/server.py`: `_context_vox` (`functii`, `aplicatii`), `_aplicatii_vox`, instanța `VOX`.
- `app/test_vox.py`, `app/vox_exemple.json`.
- `shared/src/vox.ts`.
- `web/src/pages/Vox.tsx`, `web/src/pages/vox/Aplicatii.tsx` (nou),
  `web/src/pages/rate_mobil/android/model.ts` (exportul lui `FUNCTII`), `web/src/i18n/dict/vox.ts`,
  `web/src/styles/vox.css`.
- `README.md`, `CLAUDE.md`, `.serena/memories/cod/harta.md`.
