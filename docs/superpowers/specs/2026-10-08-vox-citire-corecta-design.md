# Vox: citește corect datele pe care le avem; continuări fără model

Data: 08.10.2026. Ramura `vox-chatbot`. Design aprobat în discuție cu Nicolae Cherascu, pe secțiuni.
Cifrele sunt măsurate pe `mip_merge`, 08.10.2026.

## Ce vrea utilizatorul

În conversația de test din 08.10.2026 (`35b2f7f797944207`, 18 întrebări), trei răspunsuri erau
corecte față de bază, dar se citeau greșit: depozitul Libra amesteca monedele, administrarea contului la
BCR punea sume anuale lângă cele lunare, iar „schimbarea PIN-ului” la Garanti arăta limite drept
comision. Curățarea datelor o face altcineva, altă dată. Aici Vox trebuie să citească corect ce există,
presupunând că datele sunt adevărate. În plus, Vox devine mai ieftin și mai sigur: butoane de
continuare care nu cheamă modelul și cache-ul promptului ținut o oră.

Criterii de reușită:
- „Ce dobândă are Libra la depozitul pe 12 luni?” (cade pe termen nespecificat) arată trei carduri pe
  monedă: lei 4,75% (1 valoare), euro 1,95% (1) și monedă nespusă 2,2–5,5% (9). Moneda vine doar din
  coloana `valuta`: rândul „dolari - dobândă 2.25%” n-are moneda în bază, deci stă la „monedă nespusă”.
- „Cât costă administrarea contului la BCR?”: cardul PF în lei arată intervalul pe frecvență, pe lună
  0–100 lei (16), pe an 0–1.200 lei (6) și fără frecvență 0–100 lei (11), în loc de „0 – 1.200 lei”.
- „Cât costă schimbarea PIN-ului la Garanti?”: niciun card de comision, ci „Nicio valoare de comision;
  am găsit doar limite (7)”, iar limitele (100–700 lei) stau în blocul „Alte valori găsite”, cu eticheta
  „limită”.
- Rândurile din tabelul fișei arată data intrării în vigoare când sursa o are (la BCR · administrare
  cont, 467 din 570 de rânduri).
- „Cine dă cea mai mare dobândă la depozitul pe 12 luni?” păstrează cifrele din 2.2 și adaugă nota de
  monedă: în blocul „12 luni”, Raiffeisen are 2 din 2 valori în altă monedă decât lei; în blocul
  „termen nespecificat”, Libra are 1 din 11, iar Vista 1 din 35.
- După „Cât costă administrarea contului la BCR?”, butonul „Pentru firme” dă același răspuns ca „… pentru
  firme la BCR?” (PJ primul), fără niciun apel la model, cu cost 0. După clasamentul de administrare,
  „Pentru firme” dă clasamentul PJ (Libra pe locurile 8–10). „Compară cu Libra” după BCR arată fișele
  BCR și Libra.
- Cache-ul promptului ține o oră, iar costul afișat folosește prețul scrierii de o oră.
- Conversațiile salvate înainte se redeschid neschimbate; evaluarea rămâne 44 din 44.

## Ce nu intră

- Curățarea datelor: bannerul Libra cu 7,81%, exemplul BRD din 2017, limitele Garanti legate de PIN,
  moneda lipsă din `valuta`. Se fac în altă parte, altă dată.
- Paginile 2.1, 2.2, Versus și sertarul de dovezi rămân neschimbate (decizia lui Nicolae, 08.10.2026).
  Clasamentele Vox păstrează cifrele paginilor și primesc doar nota de monedă.
- Ghicirea monedei din text: moneda vine doar din `valuta`.
- Marcajul „veche” pe date: se arată doar data (decizia lui Nicolae).
- O notă pentru limite sau note în clasamentele de comisioane (decizia lui Nicolae).
- Butoanele pentru PFA / IMM, alt termen la dobânzi și clasamentul din fișa băncii (neselectate).
- Schimbările de preț, aplicațiile, indicii BNR: sub-proiecte separate.

## Fișa băncii

Toate regulile stau în `vox.rezuma`, o funcție pură peste rândurile pe care `celula` le întoarce deja;
`Vox._raspuns` o cheamă ca acum. Paginile nu folosesc `rezuma`, deci nu se schimbă.

- **Tipul valorii.** Tipul e prima parte din `cod_scenariu`. Valorile serviciului sunt rândurile de tip
  `comision` / `comisioane` sau din categoriile 2.2 (`depozite`, `credite`, `conturi_carduri`, cheile
  din `ctx["categorii"]`). Celelalte tipuri (`nota`, `limita`, `curs`, `dobanda` și orice alt tip) intră
  într-o listă separată, `alte`, cu aceeași formă de grupă. Măsurat: 397 de rânduri neambigue în lei sau
  euro, trecute la concepte de comision, au alt tip (208 note, 141 limite, 41 dobânzi, 7 cursuri).
- **Moneda, doar la dobânzi**: grupele de tip `depozite`, `credite` sau `conturi_carduri`. Cheia
  grupei primește `moneda` din `valuta`: `LEI` și `RON` → `lei`, `EUR` → `eur`, `USD` → `usd`,
  `GBP` → `gbp`, `CHF` → `chf`, gol → `null` (monedă nespusă). În același segment și tip, ordinea
  monedelor bate mărimea grupei: lei, euro, dolari, celelalte, nespusă la final, ca la segmente. La
  comisioane nu se schimbă nimic, nici la cele procentuale (1% la retragere): unitatea (`lei` / `eur`)
  e moneda prețului, iar `valuta` poate fi a contului („Administrarea contului (EURO): 20 Lei”).
  Măsurat pe toate rândurile curente: LEI 9.195, EUR 4.875, USD 458, RON 28, GBP 18, CHF 13, gol 8.559.
- **Frecvența, doar la comisioane.** O grupă de tip comision cu mai mult de o frecvență (inclusiv „fără
  frecvență”) primește `frecvente`: `[{frecventa, n, minim, maxim}]`, în ordinea mărimii; cu o singură
  frecvență, câmpul lipsește. Frecvența vine din `frecventa`. Măsurat: la comisioane, 812 rânduri
  lunare, 256 pe card, 235 anuale, 103 zilnice, 84 pe operațiune, 64 trimestriale, 60 pe tranzacție,
  11.912 fără frecvență.
- **Data.** `celula` întoarce și `o.data_vigoare`, ca text ISO sau `null`. 69% din rândurile curente o
  au. Sertarul primește câmpul, dar nu-l arată.
- Răspunsul pe bancă păstrează `rezumat` (acum doar grupele de preț, cu `moneda` și `frecvente` când
  e cazul) și primește `alte`. `total`, `ambigue`, `fara_cifra` și `randuri` nu se schimbă.

## Clasamentele

- Cifrele rămân cele din `celule_rate` / `celule_matrice`, deci identice cu paginile.
- La dobânzi (`sursa = rate`), `_clasament_vox` face, pentru fiecare bloc, o interogare pe aceleași
  filtre (`_baza_rate` și `_filtre_rate` ale blocului): pe bancă, câte rânduri au `valuta` în altă
  monedă decât lei (EUR, USD, GBP, CHF; golul nu se numără) și câte rânduri are celula. Rândul băncii
  din clasament primește `alte_monede: {n, din}` doar când `n > 0`.
- La comisioane nu se adaugă nimic.

## Butoanele de continuare

- `POST /api/vox` acceptă, în locul lui `intrebare`, perechea `buton` + `anterior`: interpretarea
  răspunsului sub care s-a apăsat butonul. `conversatie` rămâne ca acum. O cerere cu ambele, sau cu
  niciunul, primește 400.
- `vox.butoane(interp, raspunsuri, clasament)`, o funcție pură, spune ce butoane are un răspuns:
  - `firme`: la `cautare` fără categorie, când rezumatul are grupe cu segment, și la clasamentul de
    comisioane (`sursa = matrice`); doar când segmentul nu e deja `pj`;
  - `pf`: aceleași condiții, când segmentul e `pj`, `pfa` sau `imm`;
  - `libra`: la `cautare`, când Libra nu e printre bănci și sunt mai puțin de 3 bănci.
  Răspunsul obișnuit și cel dat de un buton primesc `butoane`; interfața nu decide singură. Turele
  salvate înainte n-au câmpul, deci n-au butoane.
- `vox.din_buton(anterior, buton)`, tot pură, face interpretarea nouă: `firme` → `segment = pj`,
  `pf` → `segment = pf`, `libra` → `banci + [libra]`. Un buton care nu se potrivește (alt buton decât
  cele trei, segment la o interpretare cu categorie, `libra` la clasament, cu Libra deja numită sau cu 3
  bănci) ridică `Respins`, adică 400.
- `Vox.continua(anterior, buton, conversatie)` verifică `anterior` (`verifica_anterior`, apoi
  `valideaza`), aplică butonul și răspunde pe drumul obișnuit (`_raspuns` / `_clasament_raspuns`), fără
  model: `model = null`, tokeni 0, `cost_usd = 0`. Tura se salvează în conversație cu `intrebare` =
  eticheta românească a butonului și cu `buton` = cheia; jurnalul primește `buton`.
- Cererea trece prin aceleași verificări ca o întrebare: token, Host, Origin, `Sec-Fetch-Site`, corp de
  cel mult 4 KB, `MIP_PERMITE_VOX=1`. Se citește doar din bază, ca la orice întrebare.

## Cache-ul de o oră

- `_cheama` trimite promptul cu `cache_control: {"type": "ephemeral", "ttl": "1h"}`, forma din
  documentația Anthropic (fără antet beta). Promptul are ~12.800 de tokeni, peste minimul de 4.096 al
  lui Haiku 4.5. Documentația recomandă cache-ul de o oră exact când întrebările vin la 5–60 de minute
  una de alta; sub 5 minute, cel de 5 minute ar fi fost puțin mai ieftin.
- Cererea are un singur marcaj de cache, deci toate scrierile lui Vox sunt de o oră:
  `cache_creation_input_tokens` intră în cost ca scrieri de o oră.
- `extragere_produse_bancare/preturi.py`, singurul loc al prețurilor: `cost()` primește
  `scriere_cache_1h`, cu factorul 2,0 (scrierea de 5 minute rămâne 1,25). Completarea e compatibilă:
  apelurile fluxului de comparație nu se schimbă.
- `eval_vox.py`: estimarea primei întrebări trece pe prețul scrierii de o oră.
- Cost estimat: conversația din 08.10.2026, cu 18 întrebări și 3 scrieri în cache, ar trece de la 7,5
  la ~5,3 cenți. O întrebare izolată, după o pauză de peste o oră, ar trece de la ~1,6 la ~2,6 cenți.

## Interfața

- Cardul de dobândă arată moneda: „în lei”, „în euro”, „în dolari”, „monedă nespusă”.
- Cardul de comision cu `frecvente` arată, în locul intervalului mare, câte un rând pe frecvență, cu
  numărul de valori. Frecvențele cunoscute au etichetă în dicționar („pe lună”, „pe an” etc.); o
  frecvență necunoscută se arată așa cum e în date.
- Blocul „Alte valori găsite la acest serviciu” are grupele din `alte`, cu eticheta tipului. Când
  rezumatul e gol și `alte` nu, fișa spune „Nicio valoare de comision; am găsit doar limite (7)” (sau
  dobândă, după concept).
- Tabelul fișei: pastila tipului la rândurile de alt tip; data („din 15.03.2021”) sub valoare, lângă
  frecvență. Fără dată, nu apare nimic.
- Clasamentul: un semn pe rândul băncii cu `alte_monede` (tooltip „2 din 2 valori sunt în altă monedă
  decât lei”) și o notă în antet care numește băncile.
- Butoanele stau sub răspuns, ca linkuri mici. Un clic adaugă o tură: bula are eticheta în limba
  paginii și nota „fără model”, iar costul conversației nu crește.
- Textele stau în `i18n/dict/vox.ts`, ca perechi RO / EN. În Zod (`shared/src/vox.ts`, `celula.ts`),
  câmpurile noi sunt opționale: conversațiile salvate înainte se citesc neschimbate.

## Teste și verificări

- `app/test_vox.py`:
  - `rezuma`: doar limite → rezumat gol, `alte` cu limitele; moneda (lei, euro, nespusă, în ordine);
    trei frecvențe → `frecvente`, una singură → fără; gratuitele numărate doar la comisioane;
  - `butoane` și `din_buton`: `firme`, `pf`, `libra` și fiecare refuz;
  - `continua`: niciun apel la client, cost 0, tura salvată cu `buton`; o conversație ștearsă → `Respins`;
  - HTTP: `POST` cu `buton` + `anterior` trece prin verificările de token, Host și Origin, primește 400
    la un buton nepotrivit sau cu `intrebare` și `buton` deodată, și 200 fără apel la model;
  - cererea către model are `ttl: "1h"`, iar costul unei scrieri de o oră e de 2 ori prețul de intrare.
- `app/test_celula.py`: SELECT-ul din `celula` conține `data_vigoare`.
- Pe baza reală, cu un model fals: criteriile de reușită de mai sus (Libra, BCR, Garanti, clasamentul pe
  12 luni, butoanele).
- Pagina: Playwright pe :5173, cu API-ul pe serverul temporar :8797 și răspunsurile `POST` din fișiere.
  Se verifică cardurile pe monedă, frecvențele, blocul „alte valori”, data, nota de monedă, butoanele
  (corpul `POST` are `buton` și `anterior`), în RO și EN, cu consola curată. Conversațiile vechi se
  redeschid.
- `python app/verifica_pagini.py` pe :8797: 0 erori.
- Evaluarea reală, `python app/eval_vox.py --da`, o dată la final (~$0,09–0,10): 44 din 44.

## Documentație

- README, secțiunea Vox: fișa pe monedă, frecvență și tip, data, nota de monedă din clasamente,
  butoanele fără model, cache-ul de o oră și costurile măsurate.
- Harta Serena (`cod/harta`): regulile din `rezuma`, `butoane` / `din_buton` / `continua`, scrierile de
  o oră din `preturi`.

## Fișiere

- `app/vox.py`: `rezuma`, `butoane`, `din_buton`, `Vox.continua`, `_cheama` (cache).
- `app/server.py`: `celula` (`data_vigoare`), `_clasament_vox` (`alte_monede`), `POST /api/vox`
  (`buton` + `anterior`).
- `extragere_produse_bancare/preturi.py`, `app/eval_vox.py`.
- `app/test_vox.py`, `app/test_celula.py`.
- `shared/src/vox.ts`, `shared/src/celula.ts`.
- `web/src/pages/Vox.tsx`, `web/src/pages/vox/Clasament.tsx`, `web/src/api/vox.ts`,
  `web/src/i18n/dict/vox.ts`, `web/src/styles/vox.css`.
- `README.md`, `.serena/memories/cod/harta.md`.
