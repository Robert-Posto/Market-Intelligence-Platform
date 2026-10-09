# Vox: recenziile aplicațiilor, așa cum le-au scris clienții

Data: 09.10.2026. Ramura `vox-chatbot`. Design aprobat în discuție cu Nicolae Cherascu, pe secțiuni.
Cifrele sunt măsurate pe `mip_merge` și pe `date/google_play_recenzii.json`, 09.10.2026.

## Ce vrea utilizatorul

În evaluarea din 09.10.2026, întrebarea „Ce scriu clienții despre BT Pay?” a arătat că oamenii întreabă ce scriu
clienții, nu doar ce notă are aplicația. Azi Vox o trimite la `in_afara`. Aplicația are însă recenziile:
- **App Store**, în bază (`app_review`): 109 recenzii la 15 bănci, cel mult 8 pe bancă. Le alege Apple, iar unele sunt
  vechi (din 2011 până în 2026). 36 au răspunsul băncii.
- **Google Play**, în `date/google_play_recenzii.json` (colectat pe 06.10.2026, autorii pseudonimizați cu `MIP_SALT`):
  394 de recenzii la 22 de aplicații, cel mult 20 pe aplicație, cele mai noi (mediana datelor: 14.09.2026).
  169 au răspunsul băncii. Notele sunt polarizate: 178 de 1★ și 162 de 5★.

Vox trebuie să arate aceste recenzii așa cum le-au scris clienții, cu nota, data, versiunea și răspunsul băncii.
Modelul doar interpretează întrebarea și nu rezumă nimic. Fișa spune limpede că recenziile sunt un eșantion ales de
magazine, nu o măsurătoare a părerii clienților.

Criterii de reușită (măsurate pe 09.10.2026):

| Întrebarea | Răspunsul |
|---|---|
| „Ce scriu clienții despre BT Pay?” | 20 de recenzii Google Play și 8 din App Store, cele mai noi întâi, cu răspunsul băncii unde există |
| „Se plâng clienții de logare la Libra?” | 0 potriviri în cele 28 de recenzii Libra; fișa spune asta, cu avertismentul despre eșantion |
| „Ce scriu clienții despre logare?” | 7 recenzii la 5 bănci (BRD, Garanti, Nexent, Patria, Vista), grupate pe bancă, fără clasament |
| „Ce scriu clienții despre RoPay?” | 0 potriviri la toate băncile |
| „card”, la toate băncile | 48 de recenzii la 16 bănci |
| „lentă”, la toate băncile | 1 recenzie; „excelent” nu se mai potrivește (cu subșir, 12 din 13 potriviri erau „excelent”) |

Mai trebuie să meargă:
- **Butoanele:** „Compară cu Libra” adaugă recenziile Libra alături; după o căutare la o bancă, „La toate băncile”
  repetă aceeași căutare la toate. Ambele merg fără model, cu cost 0.
- **Fără `google_play_recenzii.json`:** fișa arată recenziile App Store și spune „Google Play necolectat”.
- **Întrebările rămase în afara lui Vox:** „Câte trackere are aplicația ING?” rămâne `in_afara`, iar „Ce scriu
  clienții?” (fără aplicație și fără ce caută) iese `neclar`.
- **Evaluarea:** trece 57 din 57, inclusiv „Care e cea mai ieftină variantă de administrare a contului?”, întrebare pe
  care o frază din regula `aplicatii` a mai stricat o dată pe 09.10.2026.

## Ce nu intră

- **Filtrul „doar plângeri” / „doar laude”** (nu a fost ales, 09.10.2026).
- **Clasamente între bănci după recenzii.** Eșantioanele nu sunt reprezentative: cel mult 20 pe aplicație și cel mult
  8 alese de Apple.
- **Rezumate, sentimente sau teme scrise de model.** Rămâne regula „cifrele și textele vin din date”.
- **Autorii recenziilor.** Avem doar un hash, care nu ajută la nimic.
- **Traducerea recenziilor.** Sunt date ale băncilor și nu se traduc.

## Interpretarea

- **`ASPECTE`** devine `("functii", "note", "recenzii")`; schema primește doar valoarea nouă.
- **Promptul, regula `aplicatii`:**
  - `aspect = recenzii` acoperă ce scriu sau spun clienții despre o aplicație (recenzii, comentarii, păreri, plângeri);
  - `text_cautat` primește cuvintele căutate în recenzii, doar dacă întrebarea caută ceva anume („logare”, „RoPay”);
    altfel e `null`;
  - la recenzii, `functie = null`.
- **Promptul, regula `in_afara`:** iese fraza adăugată pe 09.10.2026 („recenziile aplicațiilor și ce scriu sau spun
  clienții despre o aplicație”). Rămân trackerele, permisiunile, campaniile, sfaturile, textele de scris și
  întrebările generale.
- **Riscul cunoscut:** pe 09.10.2026, o frază pusă în regula `aplicatii` a făcut ca „Care e cea mai ieftină variantă de
  administrare a contului?” să iasă `neclar` de 3 ori din 3. Testul țintit include întrebarea asta și rulează înaintea
  evaluării complete.
- **`valideaza`, la `aspect = recenzii`:**
  - `functie` și `prag_note` devin `null`;
  - fără bancă și fără cuvânt de căutat, tipul devine `neclar`, cu mesajul fix al paginii;
  - un cuvânt prea scurt pentru `cuvinte_cautare` („AI”) dispare, ca la tarife.
- **Continuările** („și la BRD?” după recenziile BT Pay) păstrează aspectul și cuvântul căutat; e regula existentă.

## Cititorul

`_aplicatii_vox(cu_recenzii=False)` din `app/server.py`. Doar `Vox._aplicatii_raspuns` cere recenziile, și doar la
`aspect = recenzii`; celelalte vederi nu le încarcă. Cu `cu_recenzii=True`, cititorul mai întoarce:
- **`recenzii_app_store`**, din `app_review`: banca, nota, versiunea, textul, data (`postat_la`) și răspunsul băncii,
  cele mai noi întâi. Autorul nu se citește.
- **`recenzii_play`**, din `date/google_play_recenzii.json` (`FISIER_GOOGLE_PLAY_RECENZII`): `colectat_la` și, pe
  aplicație, nota, textul, data, versiunea, răspunsul băncii și data lui.
  - O intrare cu tipuri greșite se sare: nota trebuie să fie un întreg de la 1 la 5, textul și data, texte.
  - Fișierul lipsă sau stricat dă `null`.

## Răspunsul

Vederea `recenzii`, construită în `Vox._aplicatii_raspuns`. Regulile stau în funcții pure din `vox.py`.

- **Potrivirea.** `vox.potriveste_recenzia(text, cuvinte)` întoarce adevărat dacă fiecare cuvânt din
  `cuvinte_cautare(text_cautat)` e începutul unui cuvânt din textul recenziei (fără diacritice, cu litere mici).
  Subșirul nu ajunge: pentru „lentă”, potrivea 13 recenzii, dintre care 12 erau „excelent”; la început de cuvânt
  rămâne 1 (09.10.2026). Fără `text_cautat`, toate recenziile se potrivesc.
- **`blocuri`**, câte unul pe bancă:
  - fiecare are `banca`, `aplicatie`, `fara_aplicatie`, `play` și `app_store`;
  - fiecare magazin are `recenzii` (doar cele potrivite, cele mai noi întâi) și `din` (câte are eșantionul băncii);
  - `play` e `null` dacă fișierul lipsește.
  - **Cu bănci în întrebare:** câte un bloc pentru fiecare, în ordinea din întrebare.
  - **Fără bănci, doar cu căutare:** doar băncile cu cel puțin o potrivire, în ordinea numelui; Libra e evidențiată.
    Câmpul `fara_potriviri` spune în câte aplicații s-a căutat fără niciun rezultat.
- **Câmpuri comune:** `text_cautat`, `cuvinte` (rădăcinile căutate), `play_la` (data colectării) și
  `banci_fara_aplicatie`.
- **Butoanele:**
  - `libra`, cu aceeași regulă ca la celelalte aspecte: întrebarea are bănci, Libra nu e printre ele și sunt mai puțin
    de 3;
  - `toate`: întrebarea are bănci și `text_cautat`. Fără căutare nu apare, pentru că recenziile tuturor celor 22 de
    aplicații ar fi peste 500 de carduri.
- **Jurnalul** primește câte recenzii arată răspunsul.

## Interfața

- **Componenta nouă `web/src/pages/vox/Recenzii.tsx`**, chemată din `Aplicatii.tsx` pentru `vedere = recenzii`.
  Importă `rate_mobil.css`, unde stau stilurile cardului de recenzie.
- **Cardul de recenzie** refolosește `CardRecenzie` din `pages/rate_mobil/Recenzii.tsx`. Prop-ul lui `text` devine
  `ReactNode`, compatibil cu 2.3, ca Vox să poată îngroșa cuvintele găsite și scurta textele lungi. E singura
  atingere a paginii 2.3.
- **Pe fiecare bancă:**
  - sigla, numele și aplicația;
  - un bloc pe magazin, de forma „Google Play · 20 de recenzii” sau „App Store · 3 din 8 conțin «card»”;
  - primele 5 recenzii, cu „Arată toate”.
- **Textele mai lungi de 400 de caractere** se scurtează, cu „mai mult”. App Store are recenzii de până la 1.811
  caractere, 45 trec de 500.
- **Cuvintele găsite** sunt îngroșate, cu aceeași regulă ca potrivirea (început de cuvânt, fără diacritice).
- **Notele de pe fișă:**
  - avertismentul despre eșantion: „Google Play: cele mai noi 20 de recenzii pe aplicație (06.10.2026); App Store:
    cel mult 8, alese de Apple, unele vechi. Nu arată părerea tuturor clienților.”;
  - „Google Play necolectat”, când fișierul lipsește;
  - la zero potriviri: „Nicio recenzie din eșantion nu conține «logare» (28 de recenzii la Libra)”;
  - la căutarea fără bancă: „În celelalte N aplicații, nicio recenzie nu conține «…»”.
- **„Am înțeles”** arată eticheta „recenzii” și cuvântul căutat.
- **Textele noi** stau în `i18n/dict/vox.ts`, ca perechi RO / EN, sub `vox.aplicatii.recenzii.*`.
- **Zod** (`shared/src/vox.ts`): `vedere` primește `recenzii`, iar schema primește câmpurile de mai sus, opționale.
  `Aplicatii` își păstrează tipul numit (TS7056).

## Teste și verificări

- **`app/test_vox.py`**, fără rețea și fără bază:
  - **validarea:** `aspect = recenzii` cu bancă, doar cu căutare și fără nimic (`neclar`); `functie` și `prag_note`
    golite; „AI” scos;
  - **`potriveste_recenzia`:** „lent” nu prinde „excelent”; „logare” prinde „Logarea”; diacriticele contează ca
    literele fără ele; toate cuvintele trebuie să se potrivească; fără cuvinte, totul se potrivește;
  - **cititorul:** fișier lipsă, fișier stricat, o intrare cu nota „5” ca text sau cu textul număr se sare;
  - **vederea `recenzii`:** cu bănci, doar căutare (bănci în ordinea numelui, `fara_potriviri`), zero potriviri, fără
    Google Play;
  - **butoanele:** `libra`; `toate` doar cu căutare; refuzul lui `toate` fără căutare;
  - **promptul:** regula nouă; fraza despre recenzii a ieșit din `in_afara`.
- **Pe baza reală, cu un model fals:** criteriile de reușită de mai sus.
- **Pagina:** Playwright pe :5173, cu API-ul pe serverul temporar :8797. Se verifică în RO și EN, cu tema luminoasă și
  cu cea întunecată: cardurile, cuvântul îngroșat, „mai mult”, avertismentul, varianta fără Google Play și butoanele.
  Consola trebuie să fie curată, iar conversațiile vechi să se redeschidă.
- **Build:** `npm run typecheck`, build-ul de verificare într-un dosar temporar, `python app/verifica_pagini.py` pe
  :8797.
- **Evaluarea** (`app/vox_exemple.json`):
  - „Ce scriu clienții despre BT Pay?” trece de la `in_afara` la `aplicatii`, cu `aspect = recenzii` și
    `banci = [banca-transilvania]`;
  - 4 întrebări noi: „Se plâng clienții de logare la Libra?”; „Ce scriu clienții despre RoPay?” (fără bănci, cu
    text); „Ce recenzii are George?”; „Ce scriu clienții?” (`neclar`);
  - în total, 57 de întrebări.
  - Rularea plătită se face doar cu acordul lui Nicolae, cu costul spus înainte: întâi un test țintit care include
    „Care e cea mai ieftină variantă de administrare a contului?” (~$0,05), apoi evaluarea completă (~$0,10, măsurată
    pe 09.10.2026: $0,0972 pentru 53 de întrebări).

## Documentație

- **README, secțiunea Vox:** recenziile (sursele, eșantionul, potrivirea la început de cuvânt), apoi evaluarea
  măsurată.
- **`CLAUDE.md`:** în regula Vox, „notele Google Play din `date/google_play.json`” devine „datele Google Play din
  `date/`, ca 2.3”. Numărul de linii nu crește.
- **Harta Serena (`cod/harta`):** aspectul `recenzii`, `potriveste_recenzia`, `FISIER_GOOGLE_PLAY_RECENZII` și
  `pages/vox/Recenzii.tsx`.
- **`docs/HANDOFF_VOX.md`** (necomis): starea.

## Fișiere

- `app/vox.py`: `ASPECTE`, `prompt`, `_aplicatii_curat`, `potriveste_recenzia`, `Vox._aplicatii_raspuns`, `butoane` /
  `_butoane_aplicatii`, `din_buton` / `_din_buton_aplicatii`.
- `app/server.py`: `_aplicatii_vox(cu_recenzii=False)`, `_google_play_recenzii`, `FISIER_GOOGLE_PLAY_RECENZII`.
- `app/test_vox.py`, `app/vox_exemple.json`.
- `shared/src/vox.ts`.
- `web/src/pages/vox/Aplicatii.tsx`, `web/src/pages/vox/Recenzii.tsx` (nou), `web/src/pages/Vox.tsx` (eticheta din
  „Am înțeles”), `web/src/pages/rate_mobil/Recenzii.tsx` (`text` ca `ReactNode`), `web/src/i18n/dict/vox.ts`,
  `web/src/styles/vox.css`.
- `README.md`, `CLAUDE.md`, `.serena/memories/cod/harta.md`.
