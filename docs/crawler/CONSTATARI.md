# Unde stă Libra față de piață

21 septembrie 2026. Din 5.578 de comisioane (13 bănci) și 1.015 rate (20 bănci),
culese de pe site-urile a 23 de bănci.

**Citiți întâi secțiunea 7.** Ea spune ce *nu* susțin datele, iar fără ea
cifrele de mai jos par mai solide decât sunt.

> **Ce s-a schimbat față de versiunea din 18 septembrie.** Trei constatări au
> căzut sau s-au mutat, și merită citite ca atare:
>
> - **Comisionul de retragere la ATM nu mai e o constatare.** Verificarea
>   manuală pe care o ceream atunci s-a putut face din date: cei 2,5 lei ai
>   Librei sunt pentru ATM-ul *altor bănci*, iar zeroul ProCredit e pentru
>   ATM-ul *propriu*. Linia compara lucruri diferite. Vezi §2.3.
> - **La ipotecarul variabil, Libra e a cincea din opt, nu a șasea din
>   șapte.** BCR a intrat în comparație, iar cifrele BRD s-au mutat după ce am
>   eliminat versiunile depășite de documente.
> - **Libra apare acum pe 40 de linii de comisioane, nu pe 14.** Baza de
>   comparație e de aproape trei ori mai largă.
> - **Argumentul de la ipotecar s-a mutat, verificat la sursă.** „Concurenții
>   coboară sub 5% pe variabil" era imprecis: acele cifre sunt oferte fixe pe
>   primii 3 ani, clasificate greșit. Comparația corectă e tot în defavoarea
>   noastră, dar pe alt produs — Libra 6,99% fixă la intrare față de 4,70–5,20%
>   la restul pieței. Vezi §3.1 și §3.1.b.
>
> Cifrele vechi nu erau greșit citite; unele documente din care veneau erau
> depășite. Vezi [DATAREA_DOCUMENTELOR.md](DATAREA_DOCUMENTELOR.md).

---

## 1. Ce se poate afirma, și pe ce temei

Din 103 linii de comisioane comparabile, **58** trec amândouă testele de
omogenitate. Din 19 linii de rate, **14**. Restul se exclud fie pentru că
băncile nu vând același lucru, fie pentru că celula adună servicii diferite.

Pe comisioane, Libra apare pe **40 de linii de încredere** alături de cel puțin
trei alte bănci. Alea sunt comparațiile propriu-zise.

## 2. Comisioane: Libra e la sau sub piață pe 38 din 40 de linii

```
la 0 lei ............................ 17 linii
cea mai ieftină dintre toate ........  8 linii
la egalitate cu cea mai ieftină ..... 22 linii
la mijloc ...........................  8 linii
CEA MAI SCUMPĂ ......................  2 linii
```

*(Categoriile se suprapun: o linie la 0 lei e de obicei și la egalitate cu cea
mai ieftină.)*

### 2.1. Unde Libra e la zero

| serviciu | Libra | ceilalți |
|---|---|---|
| administrare cont PF, lunar/anual, LEI | **0** | BCR 240 · BRCI 60 · CreditCoop 60 · ProCredit 0 · Salt 0 |
| administrare cont PF, EUR | **0** | BRCI 36 · ProCredit 0 |
| internet banking, PF | **0** | CreditCoop 60 · BRCI 0 · ProCredit 0 · Salt 0 |
| deschidere cont PF și PJ | **0** | toți 0 |
| depunere numerar PF | **0** | BRCI 0 · ProCredit 0 |
| încasare interbancară PF, LEI | **0** | Garanti 6 · restul 0 |
| interogare sold la ATM | **0** | Eximbank 1 · TechVentures 5 |
| plată programată PF | **0** | BCR 0 · Raiffeisen 1,5 |

### 2.2. Unde Libra e sub piață, dar nu la zero

| serviciu | Libra | ceilalți |
|---|---|---|
| poprire PF | **20** | BCR 25 · Raiffeisen 25 · Salt 30 · TechVentures 50 |
| transfer credit PJ, EUR, minim | **25** | TBI 25 · BCR 50 · BRCI 50 |
| transfer credit PJ, EUR, maxim | **300** | BRCI 550 · BCR 1.500 |
| documentar PJ, minim EUR | **30** | BCR 50 · BRCI 75 · TBI 150 |
| documentar PF, maxim EUR | **300** | Garanti 500 · BCR 750 |
| refuz plată, EUR | **8** | Eximbank 12 · TechVentures 25 |
| conversie valutară, procent | **1** | BCR 2 · Eximbank 2 |
| administrare cont PJ, LEI | **10** | TBI 10 · BCR 42,5 |
| modificare/anulare PJ, EUR | **20** | TBI 20 · BCR 25 · BRCI 25 |

### 2.3. Cele două linii unde Libra e cea mai scumpă — și numai una ține

**Retragere numerar în EUR la ghișeu — aici constatarea e reală:**

| bancă | cum e scris în document | minim |
|---|---|---|
| BRCI | 0,5%, min. 2 EUR | **2** |
| BCR | 2,5% min. 5 EUR / min. 6 EUR | **5,5** |
| **Libra** | **1%, min. 10 EURO** | **10** |

Procentul Librei (1%) e sub al BCR (2,5%) și peste al BRCI (0,5%). Dar
**minimul e dublu față de BCR și de cinci ori cel al BRCI.** Pentru retrageri
mici Libra e cea mai scumpă de pe linie; pentru retrageri mari, BCR devine.

**Retragere numerar la ATM — constatarea CADE.**

Versiunea din 18 septembrie o dădea drept „singura excepție" și cerea
verificare manuală. Verificarea s-a putut face din date, fiindcă acum avem
denumirea completă a serviciului la fiecare bancă:

```
libra      2,5 lei   "Retrageri de numerar in Lei de la ATM-ul ALTOR BANCI *"
procredit  0 LEI     "gratuite de la ATM-urile PROCREDIT"
bcr        0 Lei     "de la ATM-ul BCR" SI "ATM-ul altor banci"
brci       1 Leu     "la ATM-uri din Romania"
```

**Linia compară lucruri diferite.** Cifra Librei e pentru ATM străin, cea a
ProCredit pentru ATM propriu. Nu se poate spune că Libra e mai scumpă la ATM —
comisionul Librei la ATM propriu nu apare deloc în comparație.

Asta e o corecție a unei constatări, nu o constatare nouă.

## 3. Rate

### 3.1. Creditul ipotecar variabil — cea mai solidă comparație din tot setul

Opt bănci, dispersie 2× între ele:

| bancă | nominală | interval găsit |
|---|---|---|
| Eximbank | 4,99 | — |
| Patria | 6,30 | 4,77–8,46 |
| Raiffeisen | 7,56 | 4,90–7,66 |
| ProCredit | 7,66 | 4,89–8,06 |
| **Libra** | **7,71** | **7,71–8,31** |
| BCR | 7,86 | 7,66–7,86 |
| BRD | 8,03 | 7,66–8,21 |
| ING | 8,05 | — |

**Libra e a cincea din opt.** Trei bănci sunt mai scumpe. La 0,05 p.p. de
ProCredit, dar la 2,72 p.p. de Eximbank.

**Atenție la capătul de jos al intervalelor — l-am verificat și nu spune ce
pare.** Valorile sub 5% de pe linia asta nu sunt dobânzi variabile. Sunt
**oferte fixe pe primii 3 ani**, clasificate greșit ca variabile fiindcă
propoziția continuă cu „apoi variabilă":

```
procredit  4,89   "4,89% fixa in primii 3 ani, apoi variabila"
raiffeisen 4,90   "Dobanda fixa 3 ani, de la 4,90%, ulterior variabila"
eximbank   4,99   "dobanda fixa de 4,99% in primii 3 ani"
patria     4,768  "4,99% fixa / 4,768% variabila"   <- singura chiar variabila
```

Deci **Eximbank nu are de fapt o dobândă variabilă de 4,99%** — cifra din
tabelul de mai sus e oferta lui promoțională fixă. Singura bancă din set cu o
variabilă reală sub 5% e Patria.

Ce rămâne valabil, și e partea importantă: **intervalul Librei (7,71–8,31) e
cel mai îngust și cel mai sus poziționat din tot tabelul.** Libra nu coboară
sub 7,71 nici pe variabil, nici — vezi mai jos — pe oferta de intrare.

### 3.1.b. Oferta de intrare: aici e diferența adevărată

Comparația corectă pentru „de ce nu avem un produs de intrare" nu e pe
variabil, ci pe dobânda **fixă pe primii 3 ani** — produsul pe care clientul îl
vede primul. Citite direct din textul fiecărei pagini:

| bancă | fixă, primii 3 ani | produs |
|---|---|---|
| Raiffeisen | **4,70** | Casa Ta Verde |
| BCR | 4,79 / 4,99 | Casa Mea Natura / Casa Mea |
| ProCredit | 4,89 / 4,99 | credite în LEI |
| Eximbank | 4,99 | promoția Casa A+ |
| BRD | 5,20 | — |
| **Libra** | **6,99** | — |

**Libra e cu 1,8–2,3 puncte procentuale peste toți.** Nu e o diferență de
marjă — marja Librei e a doua cea mai mică din șase (§3.2). E o diferență de
ofertă promoțională de intrare.

### 3.2. Marja peste IRCC, partea pe care banca o controlează

```
Raiffeisen 2,10   Libra 2,15   ProCredit 2,15   BCR 2,30   BRD 2,47   ING 2,49
```

Libra e **a doua cea mai mică din șase**, într-un interval total de 0,39 p.p.
Deci diferența de la §3.1 nu vine din marjă — vine din gama de produse și din
condiții. (În versiunea trecută BRD apărea la 2,10; cifra venea dintr-un
document înlocuit între timp.)

### 3.3. Nevoi personale: Libra e practic singura numai pe variabil

```
numai fix:          BCR · BRD · ING · ProCredit · Raiffeisen · Salt
fix si variabil:    Patria
9 din 10 variabil:  Libra
```

Singura rată fixă a Librei la categoria asta e pe **„Credit de consum pentru
energie verde"** — un produs specializat, nu creditul de nevoi personale.
Constatarea din versiunea trecută se menține, cu nuanța asta.

Nu e o gaură în date, e poziționare — dar Libra e singură în poziția aceea.

**Atenție la citirea cifrelor de pe rândul fix.** Salt 5,49, BRD 6,10 și
Raiffeisen 5,95 sunt marcate „de la" — banca nu publică plafonul. Raiffeisen
are intervalul declarat până la **18,35%**, iar ING 10,99 până la 15,99%.
Mediana afișată nu e ce va plăti clientul.

## 4. Două anomalii verificate

### 4.1. Aritmetica de pe pagina Libra folosește un IRCC vechi

Pe [credit-nevoi-personale-fara-ipoteca](https://www.librabank.ro/credit-nevoi-personale-fara-ipoteca):

```
3,00% + IRCC = 8,68%    ->  IRCC implicit 5,68%
4,50% + IRCC = 10,18%   ->  IRCC implicit 5,68%
```

Dar nota de subsol a **aceleiași pagini**, plus BCR și Nexent, dau IRCC în
vigoare **5,56%**. Diferența e 0,12 p.p.

**Nou față de 18 septembrie:** BRD publică în exemplele sale reprezentative
exact valoarea 5,68% („dacă IRCC are valoarea de 5,68%…"). Deci 5,68% **a fost
o valoare reală, într-un trimestru anterior** — nu o greșeală de calcul.

Formularea corectă e deci: **totalurile afișate (8,68% și 10,18%) au fost
calculate cu IRCC-ul unui trimestru anterior și n-au fost reîmprospătate când
indicele s-a schimbat.** Starea rămâne `SUSPECT`, nu „eroare" — pentru
verdictul de vechime e nevoie de seria trimestrială BNR, care nu e accesibilă.

E singura constatare din tot setul care privește propria noastră bancă.

### 4.2. Garanti publică indici expirați

Pe pagina de [comisioane și dobânzi IMM și PFA](https://www.garantibbva.ro/imm-si-pfa/comisioane-si-dobanzi-credite-imm-si-pfa/):

| indice | pe site | în vigoare | diferență |
|---|---|---|---|
| IRCC | 4,05 și 4,06 | 5,56 | −1,50 p.p. |
| ROBOR | 7,86 · 7,97 · 8,08 | 5,84 | +2,0…2,2 p.p. |
| EURIBOR | 0,267 și 0,66 | 2,568 | −1,9…2,3 p.p. |

EURIBOR la 0,267% nu a mai existat de ani. Sunt indici lăsați pe site, nu erori
de extragere — fiecare valoare e verificată în textul-sursă.

## 5. Cât de recent își întreține fiecare bancă documentele

| bancă | cel mai nou document | zile | cea mai veche versiune lăsată pe site |
|---|---|---:|---|
| BRD | 2026-09-21 | 0 | 2026-08-03 (49 z) |
| BCR | 2026-09-18 | 2 | 2018-06-11 (3.023 z) |
| CreditCoop | 2026-09-10 | 10 | 2026-09-10 |
| Raiffeisen | 2026-08-31 | 20 | 2026-06-26 (86 z) |
| **Libra** | **2026-08-25** | **26** | **2024-05-16 (857 z)** |
| BRCI | 2026-08-17 | 34 | 2024-05-29 (845 z) |
| Salt | 2026-08-03 | 48 | 2026-08-03 |
| Eximbank | 2026-04-08 | 165 | 2026-04-08 |
| TechVentures | 2026-02-12 | 220 | 2025-11-11 (313 z) |
| Garanti | 2025-11-13 | 311 | 2025-11-13 |
| TBI | 2024-08-01 | 781 | 2024-07-31 |
| BCR Banca pentru Locuințe | 2020-07-08 | **2.265** | 2020-07-08 |

Libra e în prima treime. Două cazuri ies în evidență:

- **BCR Banca pentru Locuințe** are ca document curent o listă din **iulie
  2020**, legată din „Informații utile". Peste șase ani.
- **TBI** are lista PJ cu „în vigoare din 15.12.2019" în chiar numele
  fișierului.

Vechimea publicării se leagă de §4.2: Garanti are indici expirați **și**
documente de 311 zile. Cele două se explică reciproc.

### Ce nu spune niciun document: propria noastră dată

Documentele de tarife Libra nu conțin nicio dată — nici în text, nici în numele
fișierului. Doar `Versiunea V50` și `Versiunea V_52`. 13 bănci din 23 își
datează documentele; Libra nu. Nici noi, nici un client, nici un auditor nu
poate spune din PDF când s-a schimbat ultima oară un preț.

E singura observație din tot raportul care depinde numai de noi.

## 6. Prima schimbare de preț prinsă pe piață

Sonda de schimbări a rulat pe 21 septembrie, la trei zile după linia de bază.
Din 467 de documente urmărite, **două s-au schimbat**. Din cele 13 diferențe
din ghidul BRD, **una era un preț**:

```
brd   debitare directa Simplis Debit (BRD - BRD)
      1,50 lei/operatiune (exceptie pentru mandatele Electrica Furnizare)
      -> gratuit, fara exceptie
```

Restul erau fonturi, o dată pe copertă și reformatare. Detaliul complet e în
[SCHIMBARI_PRETURI.md](SCHIMBARI_PRETURI.md).

## 7. Ce NU susțin datele

Partea care contează cel mai mult, fiindcă fără ea tot ce e mai sus pare mai
solid decât e.

**Comparabil nu înseamnă tot.** 58 din 103 linii de comisioane și 14 din 19 de
rate. Restul sunt excluse pe criterii măsurate, nu ascunse — dar nu se pot
folosi.

**716 valori (12%) nu pot fi atribuite.** În același document, sub același
serviciu, apar mai multe prețuri și nimic nu spune care când se aplică:
antetul coloanei sau pragul de sumă s-a pierdut la extragere. Prețurile sunt
reale. În tabelul comparativ sunt marcate cu `?`. La Libra sunt 67 de astfel
de valori.

**65% dintre comisioane sunt mapate pe un concept.** Celelalte 35% (1.877 de
valori) au etichete fragmentare, tăiate la granița rândului de grilă în PDF.
Sunt extrase corect, dar nu se pot compara cu nimic. E plafonul actual, și e o
limită de extragere, nu de dicționar.

**Cifra afișată e mediana, nu prețul clientului.** Unde apare `(x–y)`, aia e
împrăștierea reală. La creditele de nevoi personale ea ajunge la 18,35%.

**Nouă rate sunt „de la X%" fără plafon publicat.** Nu se poate reconstitui;
sunt marcate cu `↓`.

**Trei bănci lipsesc complet** — Banca Transilvania, UniCredit și Intesa
blochează accesul automatizat, și nu am încercat să ocolim blocajul. Banorient
e exclusă prin `Disallow: /`. Deci nicio afirmație de aici nu e „despre toată
piața".

**ING nu are documente descărcate**, fiindcă `robots.txt` interzice
(`Disallow: *.pdf`). Cifrele ING vin doar din pagini HTML.

**18 documente n-au dată** — nici în text, nici în nume. Cifrele lor sunt în
comparație, marcate `DATA_NECUNOSCUTA`. Nu știm dacă sunt prețurile de azi.
Douăsprezece dintre ele sunt ale Librei.

**Clasificarea fix/variabil greșește pe ofertele mixte.** Când pagina scrie
„4,89% fixă în primii 3 ani, apoi variabilă", regula vede cuvântul „variabilă"
și pune toată linia pe variabil — deși cifra aparține părții fixe. Sunt patru
valori afectate, toate la ipotecar, toate identificate și explicate în §3.1.
**N-am schimbat codul** pentru asta cu o oră înainte de predare: o modificare a
clasificării mută cifre în tot tabelul de rate și ar cere reverificarea
tuturor. E de reparat la prima iterație, cu test.

**Maparea pe concepte nu e verificabilă automat.** Geometria tabelelor se
verifică, valorile se verifică pe eșantion, dar „acest serviciu e
`transfer_credit`" e o judecată. E singurul strat fără plasă.

**O comparație de trei zile nu e o tendință.** Avem prima schimbare reală
(§6), nu o serie.

## 8. Ce aș face cu asta

În ordinea în care datele susțin urgența:

1. **Oferta de intrare la ipotecar** (§3.1.b). Nu marja e problema — e a doua
   cea mai mică din șase. Problema e dobânda fixă pe primii 3 ani: Libra 6,99%,
   restul pieței 4,70–5,20%. Aia e cifra pe care o vede clientul în prima
   pagină de ofertă. Întrebarea pentru comercial nu e „reducem marja?", e „de
   ce nu avem o promoție de intrare?".
2. **Minimul de 10 EUR la retragerea de numerar la ghișeu** (§2.3). Singura
   linie unde Libra e cea mai scumpă și comparația chiar ține. Dublu față de
   BCR, de cinci ori BRCI. Afectează retragerile mici.
3. **De verificat aritmetica IRCC de pe pagina Libra** (§4.1). Totalurile
   afișate par calculate cu IRCC-ul unui trimestru anterior. E o corectură de
   pagină, nu o decizie comercială.
4. **De pus o dată în documentele de tarife** (§5). Suntem singura bancă mare
   din set fără dată nicăieri în PDF. Nu costă nimic.
5. **De decis dacă „doar variabil" la nevoi personale e o poziție** (§3.3).
   Șase bănci publică numai fix. Într-o piață cu IRCC în mișcare, e vizibil
   pentru client.

Ce **nu** mai e pe listă: verificarea comisionului de retragere la ATM. S-a
făcut, și constatarea a căzut (§2.3).

## Trasabilitate

| ce | unde |
|---|---|
| tabelul comisioanelor | [comparatie_comisioane.md](comparatie_comisioane.md) |
| tabelul ratelor | [comparatie_rate.md](comparatie_rate.md) |
| verdictele pe fiecare rată | `output/rate_validate.json` |
| care preț e cel de azi | [DATAREA_DOCUMENTELOR.md](DATAREA_DOCUMENTELOR.md) |
| vechimea documentelor | [VECHIME_DOCUMENTE.md](VECHIME_DOCUMENTE.md) |
| ce s-a schimbat pe piață | [SCHIMBARI_PRETURI.md](SCHIMBARI_PRETURI.md) |
| cum s-a extras, și ce a greșit | [COMISIOANE_PDF.md](COMISIOANE_PDF.md) |
| ce site-uri se pot accesa și de ce | [CONCLUZII.md](CONCLUZII.md) |

**Toate cele 5.578 de valori** păstrează textul-sursă din care au fost citite,
plus documentul și pagina. Orice cifră de aici se poate urmări până la fraza
din PDF.

Validare: 921 `OK`, 12 `SUSPECT`, 7 `SURSA_VECHE`. 147 de teste trec.

*Ultima corectură, 21 septembrie ora 12: regula de citire a procentelor accepta
cel mult trei zecimale și nu avea ancoră la stânga, deci pe un număr mai lung
renunța la începutul lui și prindea coada — „0,0125%” ieșea **125%**. O singură
valoare din tot setul era afectată (BCR, pachet extins), și nu intra în nicio
linie de încredere. Reparată, cu test.*
