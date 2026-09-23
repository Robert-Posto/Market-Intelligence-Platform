# Briefing 3: 17–18 septembrie — de la extragere la comparație

<!-- antet-vechime -->
> **Cifrele din documentul ăsta sunt cele de pe 18 septembrie 2026 și nu au fost
> actualizate.** Se păstrează ca jurnal de lucru: arată ce se știa atunci și
> cum s-a ajuns acolo. **Totalurile curente sunt în
> [CONSTATARI.md](CONSTATARI.md)**, iar regulile de filtrare pentru integrare
> în [CITESTE_PENTRU_MERGE.md](CITESTE_PENTRU_MERGE.md).

Continuarea lui [BRIEFING_BEAUTIFULSOUP_2.md](BRIEFING_BEAUTIFULSOUP_2.md), care
rămâne valabil în întregime. Ce s-a adăugat în două zile e altceva decât înainte:
**nu mai e extragere, e normalizare și comparație.**

Pe scurt, ca să știi imediat dacă te privește:

| | 16 sept (briefing 2) | acum |
|---|---|---|
| valori extrase din PDF | 4.445 | 4.438 |
| etichete de serviciu curate | 62% / 63% | **83% / 79%** |
| valori mapate pe un concept canonic | — | **2.703 (62%)** |
| tabel de comparație între bănci | — | **76 de linii, 48 de încredere** |
| vocabular canonic | — | 29 servicii, 10 canale, 6 destinații, 18 produse |

**Dacă tu lucrezi doar pe extragere, secțiunea 1 îți spune ce nu mai are rost să
faci, iar secțiunea 3 sunt capcane care te prind oricum.** Secțiunea 2 e ce ar
trebui să facem împreună dacă vrem ca cele trei abordări să fie comparabile.

---

## 1. GATA — nu implementa

### 1.1 Atribuirea etichetei prin poziții verticale

**Cea mai importantă reparație din ambele zile, și se aplică oricărei unelte.**

Într-un tabel de tarife, numele serviciului și prețul lui **nu sunt pe același rând
de text**. Coloana de preț e centrată vertical, coloana de nume aliniată sus, deci
în ordinea de citire ele se împletesc:

```
 576,7–588,7  nume:  "Retrageri de numerar în lei de la ghişeul"
 583,7–595,7  preț:  "2,5% min. 25 Lei"
 590,5–602,5  nume:  "băncii"
 611,3–623,3  preț:  "0 Lei"
 618,1–630,1  nume:  "Depuneri de numerar în contul clientului"
```

Citind în ordine, `0 Lei` pleacă la serviciul precedent și numele se lipesc între
ele. Regula corectă:

1. rândurile de nume se grupează în **blocuri**, ținute laolaltă de golul vertical
   mic (măsurat: 1,8 puncte în interiorul unui nume, 15,6 între două servicii —
   pragul de 6 stă comod între ele). **Rândurile de preț nu închid blocul.**
2. fiecare valoare merge la blocul cu care se **suprapune** vertical; dacă nu se
   suprapune cu niciunul, la cel mai apropiat centru. Marginea măsurată: 6,8 puncte
   față de eticheta corectă, 27,7 față de cea greșită.

Efect: 62% → 83% pe formularul standardizat, 63% → 79% pe listele de tarife.

**Pentru tine, cu BeautifulSoup:** în HTML asta nu te lovește la fel, fiindcă `<tr>`
îți dă rândul. Dar te lovește **ruda ei**: celulele cu `rowspan` și tabelele unde
numele serviciului e într-un `<td>` care acoperă mai multe rânduri de preț. Verifică
explicit că nu pierzi rânduri acolo — e același tipar logic.

### 1.2 Vocabularul canonic — patru axe, nu una

Legea 258/2017 standardizează **structura** formularului, nu formularea. Măsurat pe
cele 16 documente standardizate: toate cele 5 secțiuni apar **literal** la toate cele
5 bănci, dar doar **4 denumiri de serviciu din 116** sunt folosite de 3 bănci din 5.

Deci comparația nu se poate face pe textul denumirii. Trebuie o mapare — și un
singur concept nu ajunge:

```
concept    - CE serviciu        (retragere_numerar, transfer_credit, file_cec, ...)
canal      - PRIN CE se face    (ghiseu, atm, pos, internet_banking, swift, hartie, ...)
destinatie - CATRE UNDE         (intrabancar, interbancar, national, ue, sepa, extern)
segment    - PENTRU CINE        (pf, pj, imm, pfa)
```

**Cum am aflat că nu ajunge un concept:** la poprire, Libra are **20 lei la persoane
fizice și 50 la juridice**. Cu un singur concept, mediana le amestecă într-un număr
care nu descrie niciuna. Gruparea pe un cuvânt-cheie acoperă 66% din volum dar
grupele nu înseamnă nimic („administrar" adună contul, cardul și internet bankingul,
care diferă cu un ordin de mărime); pe două cuvinte grupele sunt corecte dar
acoperirea scade la 33%.

E în [crawler/vocabular.py](../crawler/vocabular.py), 421 de linii, în arhivă.
**Ia-l ca punct de plecare, nu-l rescrie** — fiecare tipar are în comentariu
măsurătoarea care l-a impus.

### 1.3 Ordinea din vocabular: substantivul-cap decide

Regula care m-a costat cel mai mult, pentru că greșeala e **tăcută**: potrivirea
merge pe prima regulă din listă, deci ordinea *este* semantica.

```
"Încasare interbancară prin ordin de plată"  -> este o INCASARE, nu un ordin de plată
"Anulare ordin de plată"                     -> este o ANULARE
"Plată/negociere/manipulare documente"       -> este serviciu DOCUMENTAR
"Remitere la încasare a cecurilor"           -> este o INCASARE, nu file_cec
"Anulare serviciu SMS Alert"                 -> este o ANULARE, nu alerta_sms
```

Prima versiune avea `transfer_credit` înaintea tuturor și înghițea **901 de valori**
într-un singur concept. Aceeași capcană la produse: `credit_ipotecar` înghițea
„credit de nevoi personale **cu ipotecă**".

Regula: **acțiunea e capul, instrumentul e obiectul.** Conceptele de instrument
(`file_cec`, `alerta_sms`) merg la **sfârșitul** listei. Măsurat: puse mai sus,
furau 22 de valori corect mapate; puse la sfârșit, zero deplasări și 47 de valori
câștigate.

### 1.4 Dovada locală bate contextul

**Am avut nevoie de aceeași regulă de trei ori, în trei locuri diferite.** Dacă
implementezi orice mapare pe text, o vei avea și tu.

Când o valoare se poate descrie fie din eticheta ei, fie din contextul din jur
(titlul paginii, secțiunea, antetul coloanei), **eticheta câștigă** — fiindcă
valoarea a venit din ea.

```
1. rate web:   o știre despre mașini electrice, aflată pe pagina Noua Casă, era
               raportată drept dobânda Noua Casă
2. moneda:     antetul "NOIR LEI" cu textul "2.000 EUR (echiv.)" — antetul numește
               moneda CONTULUI, nu a comisionului
3. destinatia: "Retragere de numerar ATM local" primea `ue`, fiindcă secțiunea
               paginii e "ÎNCASĂRI ȘI PLĂȚI CĂTRE STATE MEMBRE ALE UE"
```

Contextul se folosește **doar** când eticheta e un fragment. Iar criteriul de
„fragment" nu e lungimea — e forma:

```
1.573 etichete nemapate incep cu litera mica   ("îndeplinirea tuturor criteriilor")
  180 incep cu semn de lista                    ("- de la ATM-uri BCR tranzacție")
```

„- de la ATM-uri BCR tranzacție" are 30 de caractere, deci trecea pragul de 28 cu
două și nu primea contextul, deși despre serviciu nu spune nimic. Cu criteriul
structural: +178 de valori, verificat 13 din 14 corecte de mână.

**Și o excludere obligatorie:** o notă de subsol nu e un serviciu fără nume. Fără
ea, „*Nota: pentru optiunea OUR se vor adauga comisioane*" primea `transfer_credit`
din secțiune — un punct de date **inventat**.

### 1.5 Cifrele care nu sunt prețuri, runda a doua

Briefing 2 §3.2 acoperea pragurile („0 – 49.999 Lei" nu e prețul). S-au adăugat
patru familii, toate găsite prin dispersia tabelului:

| familie | discriminant | exemplu |
|---|---|---|
| cerință de client | substantiv de bani deținuți/primiți + `minim` | „sunt deținute minimum 2.000 EUR" |
| definiție de client | `venit` + `depășește` | BRD: „venit care nu depășește 60%" |
| reducere | procent lipit de `reducere` | „100% reducere față de plățile standard" |
| tabel de limite | eticheta **începe** cu `limită`/`plafon` | Garanti: „limită zilnică" → „500.000 LEI" |
| prag rupt de coloană | eticheta deschide o paranteză pe care valoarea o închide | „(sub" → „50.000 LEI)" |

Un „comision" de **5.000.000 EUR** era condiția BRD de eligibilitate pentru un
pachet; 1.000.000 lei, limita zilnică a Garanti. 37 de valori marcate, toate 37
verificate de mână.

**Ce NU merge: filtrat pe cuvântul „minim".** Are două sensuri, iar măsurat, 56 din
cele 66 de apariții sunt plafoane reale, unde 15 din `0,1% min. 15 EUR` chiar *este*
prețul. Ce separă sensurile e substantivul care guvernează cifra.

**Și zeroul nu e niciodată o cerință.** Fără condiția asta, regula avea 12 falși
pozitivi din 23, toți cu valoarea 0: „0 Lei în limita primelor 5 retrageri" — acolo
zeroul *este* prețul, iar limita e condiția lui.

Valorile nu se aruncă: primesc `rol="conditie"` și ies din comparația de prețuri.

### 1.6 Două măsuri de eterogenitate, nu una

Dacă faci un tabel de comparație, vei avea nevoie de un criteriu care spune dacă
linia e o comparație sau o iluzie. `max/min` pe toate valorile la comun **nu
răspunde la nicio întrebare** — amestecă două lucruri:

```
între  - de câte ori diferă cifrele AFISATE (medianele) între bănci
intern - cea mai mare împrăștiere din interiorul unei singure bănci
```

O linie e de încredere doar dacă trec amândouă. Numărul de linii iese aproape la
fel (48 față de 45), dar clasificarea e corectă pe toate cazurile unde diferă, în
**ambele** direcții:

```
administrare_cont/pf/lunar   8 bănci   max/min=17×  între=4×    intern=5×
    -> comparabilă; cei 17 veneau din intervalul 0–50 al unui singur ProCredit
livrare_card/pf/LEI          3 bănci   max/min=3×   între=5,3×  intern=2×
    -> NU e comparabilă: Salt cere 30–50 lei, ceilalți 0–15
```

Câștigul real nu e numărul, e **diagnosticul**: `între` mare cere o cheie mai fină,
`intern` mare cere etichete mai bune. La noi: din 28 de linii eterogene, 20 au
`intern` mare și 18 `între` mare.

---

## 2. AL TĂU — și ce ar face comparația noastră corectă

### 2.1 Comparația pe care o facem acum e nedreaptă pentru amândoi

Eu am cinci straturi: crawler → scraper web → pdf reader → normalizator →
validator. Tu construiești (probabil) primele două-trei. Dacă punem cap la cap
rezultatele finale, nu comparăm uneltele, comparăm **cât a construit fiecare**.

**Propunerea mea, iar:** 15–20 de URL-uri fixate de comun acord, aceleași pentru
toți trei, și măsurăm doar stratul 2–3 — câte valori scoate fiecare și câte sunt
corecte la verificarea de mână. Restul lanțului îl împărțim, nu îl duplicăm.

### 2.2 Vocabularul e al nostru comun, nu al meu

Dacă tu mapezi denumirile separat, obținem două taxonomii care nu se pot uni, și
atunci n-avem nici un tabel de comparație, avem trei. [vocabular.py](../crawler/vocabular.py)
n-are nicio dependență de Playwright — e `re` și liste. **Importă-l direct.**

Dacă găsești un concept care lipsește, criteriul de admitere pe care l-am folosit:
**un serviciu nemapat merită concept doar dacă apare la 3 sau mai multe bănci.**
Sub atât nu se poate compara oricum, deci n-ar produce nicio linie.

*O excepție deliberată:* dacă valorile sunt **greșit** mapate, nu nemapate, merită
concept chiar sub prag — o mapare greșită e mai rea decât o lacună. Așa a intrat
`acceptare_carduri` cu 8 valori la 2 bănci (7 erau la `transfer_credit`), în timp ce
`aviz_garantie` (5 valori, 2 bănci, nemapate) a fost respins.

### 2.3 Unde ești tu mai bun, neschimbat din briefing 2

Lărgirea descoperirii la cele 14 bănci fără sitemap rămâne cel mai valoros lucru pe
care îl poți face. Plus tabelele HTML reale și BNR-ul pe XML.

---

## 3. Capcane care NU depind de unealtă

Cele 7 din briefing 2 rămân. Se adaugă:

### 3.8 Pluralul românesc, a cincea oară

```
"comision"  -> "comisioane"    stemul e "comisio", nu "comision"
"scrisoare" -> "scrisori"      stemul e "scriso", nu "scrisoar"
```

Tiparul `scrisoar\w*` nu potrivea „Eliberare **Scrisori** de confort". A cincea
apariție a aceleiași familii în proiect. **Scrie stemul, nu forma de singular.**

### 3.9 `\b` nu se declanșează lângă `_` — a treia oară

`_` e caracter de cuvânt în Python, deci `\bPF\b` **nu** potrivește în
`Tarife_si_Comisioane_PF.pdf`. La fel `\bvers\b` în `brci_vers_2026.pdf` — două
versiuni s-au numărat de două ori, 4.150 în loc de 4.044.

Soluția pe care o folosim: `(?<![A-Za-z])PF(?![A-Za-z])`.

### 3.10 Dar `\b` funcționează exact cum trebuie lângă diacritice — verifică

Invers de utile:

```
\bnational   NU potrivește în "internațional"   (înaintea lui e "r", fără graniță)
\bintern\b   NU potrivește în "internațional"   (urmează "a", caracter de cuvânt)
```

Ambele **verificate pe date**, nu presupuse. Nu ghici în ce direcție merge — testează.

### 3.11 Destinațiile se cuprind una pe alta

Dacă implementezi o axă de destinație: nu orice două potriviri se contrazic.

```
SEPA  ⊂  UE/SEE  ⊂  extern            se rezolvă la cea mai SPECIFICĂ
national | intrabancar | interbancar   se exclud reciproc -> nu alegi niciuna
```

BRD numește o plată SEPA „Plăți **externe** către beneficiari din țările care aparțin
**zonei unice de plăți în EUR**" — două potriviri, dar nu în conflict. Iar când
documentul numește explicit amândouă („Eliberare de numerar **în/afara** României",
„Națională **și** internațională"), **nu alegi niciuna**: comisionul se aplică la
ambele.

**Atenție la un bug pe care l-am introdus chiar cu regula asta:** tiparul pentru `ue`
conținea `\bUE\b`, care potrivește și în „în afara UE" și în „non-UE" — adică exact
direcția opusă. Cu regula de specificitate, „Plăți în afara UE" se rezolva la `ue`.
Tiparul era lax de la început, dar ordinea din listă îl acoperea; regula nouă a
transformat laxitatea în eroare activă.

### 3.12 Nu toate băncile scriu termenul, unele scriu definiția

```
SEPA        -> "zona unică de plăți în EUR", "Comunitatea Europeană"
în UE       -> vocabularul meu avea doar NEGAȚIA ("în afara UE", "non-UE"),
               deci o plată ÎN UE nu se potrivea nicăieri
```

### 3.13 Măsoară ținta înainte de acoperire

Am pierdut o jumătate de zi pe „antetele de matrice sunt completate doar la 37%".
Măsurând **ce merită** un antet — doar rândurile cu valori în ≥2 coloane sunt
matrici — ținta reală s-a dovedit 40% din valori. Acoperirea era deja la ~90% din
țintă. Problema n-a fost niciodată acoperirea, ci calitatea.

La fel cu moneda: raportasem „1.364 de valori fără monedă" ca lacună. Împărțite pe
fel: 815 sunt **procente** (nu au monedă prin natura lor), 649 sunt **zero/GRATUIT**.
**Zero lipsuri reale.** Trecusem un comportament corect drept defect.

### 3.14 Acoperirea greșită e mai puțin utilă decât acoperirea mai mică

Puteam raporta 41% la destinație. Cu regula „eticheta întâi" au ieșit 35% — dar fără
eroarea sistematică înăuntru. Am ales numărul mai mic.

---

## 4. Trei straturi de verificabilitate, și nu sunt egale

Cel mai important lucru de înțeles despre tot lanțul, dacă ajungi să raportezi un
`confidence` sau o acuratețe:

```
geometria  (a citit celula corect?)      -> AUTOMAT, 99% (4.409 din 4.438)
valoarea   (15 EUR e chiar 15 EUR?)      -> eșantion de mână, 94 din 96
maparea    (e același serviciu?)         -> JUDECATĂ, nu se poate verifica
```

Al treilea nu e măsurabil, oricât cod scrii. De aceea fiecare înregistrare mapată
**păstrează denumirea originală**, ca cineva să poată contesta maparea fără să reia
extragerea. Un singur număr de încredere pe o observație le amestecă pe toate trei
și devine o judecată îmbrăcată în măsurătoare.

---

## 5. Ce e în arhivă

```
crawler/          robots.py, banci.py, main.py, extractor.py,
                  parser_rate.py, parser_pdf.py, parser_tarife.py,
                  vocabular.py, validator.py, bnr.py, bnr_indici.py
scripts/          rularea, verificarea, etaloanele, tabelele de comparație
output/*.md       documentația, inclusiv briefing 1, 2 și ăsta
output/*.json     rezultatele: comisioane, rate, unificate, indici BNR
```

Fără PDF-urile descărcate (319 fișiere) — sunt publice, le iei singur cu
`scripts/parseaza_tot.py`, și oricum **ING interzice descărcarea PDF-urilor**
(`Disallow: *.pdf`), deci acolo nu avem și nici tu nu ar trebui.

Rularea, în ordine:

```
python scripts/parseaza_pdf.py          # 427 valori, formularul standardizat
python scripts/parseaza_tarife.py       # 4.011 valori, listele de tarife
python scripts/unifica_comisioane.py    # tabelul de comparație
python scripts/compara_rate.py          # tabelul de rate
python scripts/verifica_tarife.py       # verificarea automată (99%)
python scripts/test_validare.py         # 35 de teste
```

---

## 6. Ce aș vrea de la tine

Neschimbat din briefing 2, plus unul nou:

1. **Cele 15–20 de URL-uri comune**, ca să comparăm uneltele și nu straturile.
2. **Folosește `vocabular.py`, nu unul paralel** — altfel avem trei taxonomii care
   nu se unesc.
3. **Spune-mi dacă vreuna din capcanele de la §3 te-a prins și pe tine.** Dacă da,
   nu e o particularitate a Playwright sau a pdfplumber — e o proprietate a
   documentelor bancare românești, și merită scrisă o dată, pentru toți trei.
