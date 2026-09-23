# Ce preț s-a schimbat

Generat de `scripts/compara_versiuni.py`. Fiecare secțiune e un document
pe care sonda l-a găsit schimbat și pentru care avem păstrată și versiunea
dinainte. Cele două se parsează **acum, cu același parser**, deci ce vezi
aici vine din document, nu din codul nostru.

## bcr — ce693831_Dobanzi_indicative.pdf

`https://cdn.erstegroup.com/content/dam/ro/bcr/www_bcr_ro/Persoane-fizice/Documente-importante/Dobanzi_indicative.pdf`

- versiunea veche: **2026-09-01**, 10 valori extrase
- versiunea nouă: **2026-09-01**, 10 valori extrase
- detectat de sondă la 2026-09-21T06:49

### Niciun preț schimbat **din ce extragem**

Documentul s-a schimbat pe octeți, dar nicio valoare pe care o
citim noi nu s-a mișcat. Două explicații, și diferă mult:

1. schimbarea e cosmetică — dată nouă pe copertă, reformatare,
   o randare cu alt font;
2. **schimbarea e într-o parte a documentului pe care parserul
   nu o citește.**

A doua s-a întâmplat deja. La `Dobanzi_indicative.pdf` de la BCR,
tabelul de indici (IRCC, ROBOR, EURIBOR) chiar a rămas identic —
dar tabelul de dedesubt, cu dobânzile de referință proprii, a urcat
de la 12,57% la 12,70% pe RON. Parserul nu scoate nicio valoare din
el, deci comparația nu avea ce compara.

**Absența unei schimbări aici nu e o dovadă că banca n-a schimbat
nimic.** E o dovadă că n-a schimbat nimic din ce știm să citim.

## brd — 158b3251_Ghid_tarife_comisioane.pdf

`https://www.brd.ro/sites/default/files/_files/pdf/Ghid_tarife_comisioane.pdf`

- versiunea veche: **2026-09-01**, 502 valori extrase
- versiunea nouă: **2026-09-21**, 500 valori extrase
- detectat de sondă la 2026-09-21T06:49

### Prețuri schimbate (1)

| serviciu | vechi | nou |
|---|---|---|
| debit(cecurisibiletelaordin)lei(500-50.000)lei  LEI  peoperatiune  [suma] | 4, 8, 8, 11, 16, 22 | 8, 16 |

### Praguri mutate sau apărute (1)

Aici **nu se poate decide automat** dacă banca a mutat un prag sau
dacă pragul exista dinainte și abia acum s-a putut citi. Ghidul BRD
din 1 septembrie nu avea glifele `≥` și `≤` în font, deci pragurile
scrise cu ele lipseau cu totul din text.

| serviciu | prag vechi | prag nou | valori |
|---|---|---|---|
| procesateinstant.6listatarilorincluseinzonaunicadeplatii  LEI  [suma] | — | ≥50.000lei | 6, 50000 → 6 |

### Rânduri dispărute (1)

Banca a încetat să perceapă ceva — sau am încetat noi să-l citim.

| serviciu | prag | valori |
|---|---|---|
| debitaredirectaintrabancarasimplisdebit(brd–brd)  LEI  peoperatiune  [suma] | — | 1.5 _suma_ |

### Rânduri apărute (4)

Un tarif nou — sau un rând pe care versiunea veche nu-l dădea.

| serviciu | prag | valori |
|---|---|---|
| debit(cecurisibiletelaordin)lei≥50.000lei  LEI  peoperatiune  [suma] | — | 22 _suma_ |
| debit(cecurisibiletelaordin)lei≥50.000lei  LEI  peoperatiune  [suma] | ≥50.000lei | 11 _suma_ |
| debit(cecurisibiletelaordin)lei≤500lei  LEI  peoperatiune  [suma] | — | 8 _suma_ |
| debit(cecurisibiletelaordin)lei≤500lei  LEI  peoperatiune  [suma] | ≤500lei | 4 _suma_ |

*9 rânduri au aceleași valori și același
prag, dar alt nume de serviciu: documentul a fost re-randat și
despărțirile în cuvinte s-au mutat. Nu e o schimbare de preț.*
