# Care preț e cel de azi

*21 septembrie 2026. Generat manual, nu de un script.*

Documentul ăsta descrie un mecanism adăugat în 21 septembrie: **fiecare comision
știe acum din ce versiune de document vine și dacă acea versiune mai e în
vigoare.** E scris pentru cineva care va integra datele astea cu alte surse, nu
doar pentru cine a scris codul.

---

## Problema

Băncile nu șterg de pe site versiunile vechi ale listelor de tarife. Le lasă
alături de cele noi. Crawlul le descarcă pe toate, parserul le citește pe toate,
iar comisioanele intră în aceeași grămadă.

BCR, măsurat:

```
BCR_Tarife-si-Comisioane-PJ_RO_1-martie-2026.pdf    490 comisioane
BCR_Tarife-si-Comisioane-PJ_RO_1-iulie-2026.pdf     496 comisioane
BCR_Tarife-si-Comisioane-PJ_RO_1-august-2026.pdf    496 comisioane
```

Toate trei erau în tabelul comparativ. Două din trei sunt prețuri care nu se mai
practică. Nimic din date nu spunea care e care.

### A doua problemă, găsită pe drum

```
808 fișiere pe disc  ->  doar 464 conținuturi distincte
```

**344 de fișiere sunt copii identice, octet cu octet.** Nu e o ciudățenie a
băncilor — e urma noastră. Până la schimbarea de numire (care a adăugat un
prefix de unicitate ca să nu se mai suprascrie două adrese diferite), fișierele
se salvau după numele de bază. După schimbare, aceleași documente au venit a
doua oară cu prefix, iar copiile vechi au rămas pe disc.

Parserul formularelor standardizate nu dedublează, deci fiecare copie își aducea
comisioanele din nou: **427 de valori numărate de două ori.**

---

## Cum se citește data

Trei surse, în ordinea încrederii:

| sursă | ce e | de ce e pe locul ăsta |
|---|---|---|
| **textul documentului** | „în vigoare începând cu data de 21.09.2026" | singura care exprimă o **decizie**, nu o operație tehnică |
| **numele fișierului** | `..._1-iulie-2026.pdf` | convenție internă a băncii; poate rămâne neschimbată la o reîncărcare |
| ~~`Last-Modified`~~ | momentul fișierului pe server | **nefolosit aici** — minte; la multe origini e ora umplerii cache-ului |

Textul bate numele. Unde ambele există și **nu sunt de acord**, se păstrează
amândouă și se marchează `dezacord` — nu se alege în tăcere.

### Numele fișierului nu e opțional

Tarifele BCR **nu conțin nicio dată în text.** Verificat pe toate cele 9 pagini
ale unui exemplar: coperta e doar titlul, iar în corp nu apare nimic. Data
trăiește exclusiv în nume. Fără sursa asta, BCR — a doua bancă după numărul de
comisioane pe care ni le dă — rămâne întreg nedatat.

---

## Cele trei capcane

Regulile nu au fost scrise din cap. Un inventar peste **toate cele 808
documente** ([scripts/inventar_date.py](../scripts/inventar_date.py)) a găsit
trei feluri în care o căutare naivă ar fi produs date **greșite**. O dată greșită
e mai rea decât niciuna: arată exact ca una bună.

```
"valabil PANA LA 30.09.2026"
    data de SFARSIT, luata drept inceput. Ar fi intinerit un document mort.

"clientii care au depus cerere incepand cu data de 15 iulie 2026"
    conditie de eligibilitate din corpul actului, nu data actului.

"versiunea 12", "versiunea v_1.4"
    numar de versiune, nu data.
```

Apărări, în ordine: se citește doar **antetul** (primele 1.200 de caractere),
fiindcă data de intrare în vigoare stă pe copertă iar capcanele stau în corp;
ancorele de sfârșit (`până la`) sunt respinse explicit; ancorele slabe
(`versiunea`, `actualizat`) vin ultimele.

Inventarul a scos la iveală și două forme pe care nu le acopeream deloc: câmpul
`Data:` din formularul standardizat impus prin lege, și lunile prescurtate
(`oct.2024`).

### Un bug care raporta liniștit un rezultat fals

Gruparea documentelor în „familii" (două fișiere = două versiuni ale aceluiași
act) nu funcționa deloc. Motivul: `\b` nu există între `_` și `iulie`, fiindcă
underscore e caracter de cuvânt. Tiparele de lună nu prindeau nimic, nicio
familie BCR nu se forma, iar scriptul raporta:

```
0 documente depasite
```

Un rezultat fals care arată exact ca unul bun. Prins doar fiindcă cifra părea
prea curată. Există acum un test dedicat pentru cazul cu underscore.

---

## Rezultatul

**73 de documente** produc comisioane (din 808 pe disc — restul sunt contracte,
broșuri și regulamente de promoție).

| stare document | nr. | nr. valori |
|---|---:|---:|
| `IN_VIGOARE` | 34 | **3.387** |
| `DATA_NECUNOSCUTA` | 18 | 1.733 |
| `DUBLURA` | 16 | 427 |
| `ISTORIC` | 5 | 31 |

Totalul e 5.578, nu 7.201 ca in prima versiune a acestui document. Diferenta
nu e o corectie de numarare: intre timp `parseaza_tarife` a fost reparat si nu
mai lasa versiunile depasite sa intre deloc in date. De aceea `ISTORIC` a scazut
de la 1.304 la 31 — marcajul de aici prinde acum doar ce scapa la sursa, adica
formularele standardizate, singurele care nu trec prin dedublarea aceea.

Data citită la **55 din 73 = 75%** din documentele cu cifre (48 din text, 7 din
nume).

### Ce iese din tabelul comparativ

Doar `ISTORIC` și `DUBLURA` — cele două stări despre care avem **dovadă** că
sunt greșite.

`DATA_NECUNOSCUTA` **rămâne**, deliberat. Tentația e s-o scoatem și pe ea — „dacă
nu știm data, nu știm dacă e prețul de azi". Dar măsurat, regula aia ar fi tăiat
Libra de la 876 de valori la 65, și ar fi șters cu totul Eximbank, Salt și BCR
Locuințe. **A nu ști data unui document nu e o dovadă că e vechi; e o dovadă că
banca nu și-a datat documentul.**

### Ce s-a schimbat în comparație

Șase mediane, izolate pe cauze:

```
DIN COPIILE DUBLE
  bcr    administrare cont       15,00  ->  11,99 lei/luna
  bcr    transfer credit          3,50  ->   4,00 lei
  bcr    transfer credit          0,20% ->   0,175%
  brci   transfer interbancar     5,00  ->   5,50 lei

DIN VERSIUNILE DEPASITE
  bcr dispare de pe 3 linii — singurele lui valori acolo veneau
  din tarifele de martie si iulie. O linie moare complet
  (retragere ATM, prag minim): fara BCR raman doua banci, sub pragul de trei.
```

Pierderea unei linii e un cost real și e corect: mai bine nicio linie decât una
construită pe prețul din iulie.

*(Partea cu versiunile depășite a fost măsurată înainte de a repara
`parseaza_tarife`. Efectul e acelaşi, doar că acum se produce mai devreme:
documentele vechi nu mai ajung să fie parsate deloc.)*

### Numele fișierului nu poate decide care versiune e mai nouă

Reparaţia din `parseaza_tarife` a scos la iveală ceva ce merită ştiut. BRD are
trei fişiere cu acelaşi nume de bază şi **fără nicio dată în nume**:

```
158b3251_Ghid_tarife_comisioane.pdf   ->  "in vigoare din 21.09.2026"
8bfeb70d_Ghid_tarife_comisioane.pdf   ->  "in vigoare din 01.09.2026"
Ghid_tarife_comisioane.pdf            ->  identic cu al doilea
```

Sortarea după nume cădea pe ordinea alfabetică a prefixelor, deci păstra
versiunea din **1 septembrie** şi o arunca pe cea din 21 cu motivul „versiune
mai veche". Exact pe dos.

Selecţia foloseşte acum data citită din document, cu numele doar ca rezervă. E
al doilea loc din proiect unde o convenţie de numire părea suficientă şi nu
era.

**58 de linii de încredere, neschimbat.** Datele vechi nu adăugau putere de
comparație — adăugau doar risc.

---

## Patru margini

Ce **nu** e rezolvat. Ordinea e după cât de mult poate induce în eroare.

### 1. „În vigoare" nu înseamnă „cea mai nouă pe care banca a publicat-o"

Cea mai importantă. Comparăm doar ce am descărcat noi. Dacă BCR a pus pe site
tariful din septembrie și crawlul nu l-a găsit, cel din august rămâne
`IN_VIGOARE` și arată perfect curent.

Data spune **când a intrat în vigoare un document**. Nu spune că nu există unul
mai nou.

Apărarea e recrawlul: documentul nou apare, primește o dată mai mare, iar cel din
august devine `ISTORIC` automat. Între două rulări, riscul există și nu se vede.

### 2. 25% din documente n-au dată deloc

18 din 73, din care **12 sunt ale Librei**. Cifrele lor rămân în tabel, marcate
`DATA_NECUNOSCUTA`. Asta nu e rezolvat — e **făcut vizibil**. Diferența contează:
știm acum că nu știm, în loc să presupunem că e proaspăt.

### 3. Regula de versiune e strânsă intenționat

Doar 5 documente au ieșit `ISTORIC`. Se declanșează numai când două fișiere din
aceeași familie au amândouă dată. Dacă o bancă își redenumește lista de tarife —
`Lista_comisioane.pdf` devine `Tarife_2026_final.pdf` — nu le mai vede ca rude și
nu taie nimic. Preferă să rateze decât să șteargă un preț valid.

### 4. Ratele nu sunt acoperite, și structural n-au nevoie

Toate cele 1.015 rate vin din pagini web, zero din PDF-uri. O pagină n-are
„versiunea din iulie" lăsată alături de cea din august; are ce afișează azi, iar
noi știm data crawlului.

Problema lor e alta — valoarea **afișată** poate fi ea însăși veche, ca IRCC-ul
de 5,68% de la Libra care n-a fost reîmprospătat când indicele s-a schimbat. Aia
o prinde validatorul, nu datarea.

---

## Pentru cine integrează datele

Fiecare comision din `comisioane_unificate.json` are acum patru câmpuri în plus:

```json
{
  "data_vigoare": "2026-08-01",
  "sursa_data":   "nume",
  "stare_data":   "IN_VIGOARE"
}
```

`stare_data` ia una din cinci valori:

| valoare | ce înseamnă | de folosit? |
|---|---|---|
| `IN_VIGOARE` | dată citită, în trecut | da |
| `DATA_NECUNOSCUTA` | banca nu și-a datat documentul | da, dar marcat |
| `VIITOR` | preț anunțat, nu practicat încă | nu pentru azi |
| `ISTORIC` | există o versiune mai nouă a aceluiași act | **nu** |
| `DUBLURA` | același fișier numărat de două ori | **nu** |
| `NECITIT` | pasul de datare n-a rulat | — |

**Filtrați pe `stare_data`. Nu luați toate cele 5.578 de valori.** Dacă le luați pe
toate, băgați înapoi în date exact prețurile din martie pe care tocmai le-am
scos.

`date_documente.json` ține **dovada** pentru fiecare document — fragmentul exact
din care s-a citit data, plus amprenta sha256 și familia. Cine nu e de acord cu o
dată o poate verifica fără să redeschidă PDF-ul.

---

## Fișiere

| fișier | ce face |
|---|---|
| [crawler/data_document.py](../crawler/data_document.py) | citirea datei din text și din nume, gruparea în familii |
| [scripts/date_documente.py](../scripts/date_documente.py) | rulează peste documente, marchează `ISTORIC` / `DUBLURA` |
| [scripts/inventar_date.py](../scripts/inventar_date.py) | unealta de calibrare — ce formulări folosesc băncile |
| `output/date_documente.json` | verdictul pe document, cu dovadă |

`data_document.py` e în lista modulelor care compun **amprenta parserului**
(`crawler/urme.py`). Dacă se schimbă regulile de datare, sonda de schimbări știe
că o mediană s-a mutat din vina noastră, nu a băncii — poarta aia există tocmai
ca să nu raportăm propriile modificări drept mișcări de piață.

**120 de teste trec** (erau 77 înainte de lucrarea asta).
