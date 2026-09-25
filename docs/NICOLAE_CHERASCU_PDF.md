# Extragerea comisioanelor din PDF-uri: ce am schimbat (Nicolae Cherascu, 24–25.09.2026)

Pentru echipă, după push-ul din 24.09.2026, cu actualizarea din 25.09. Acoperă doar extragerea comisioanelor
din PDF-urile băncilor: `crawler/parser_pdf.py`, `crawler/parser_tarife.py` și
`crawler/vocabular.py`. Popularea bazei, harta și App Store sunt în
`docs/HANDOFF_POPULARE.md` (Robert).

## Pe scurt

„Mapat” înseamnă că un comision are un concept canonic din vocabular
(`retragere_numerar`, `caseta_valori`...), deci poate intra în comparația dintre bănci.

| | dimineață (`a669676`) | acum |
|---|---:|---:|
| **setul fix** (50 de liste de tarife + 18 formulare PAD), comisioane mapate | 80,2% | **95,6%** |
| valori extrase din setul fix | 6.797 | 7.308 |
| comisioane în setul fix | 6.489 | 6.835 |
| **lanțul complet** (`output/comisioane_unificate.json`), comisioane mapate | 80,2% | **95,6%** |
| lanțul complet, comisioane în vigoare mapate | 80,1% | 95,6% |
| linii de încredere în `comparatie_comisioane.md` (comparabile între bănci) | 85 | 103 |
| linii prea eterogene (dispersie mare între bănci) | 71 | 84 |

**În baza de date**, refăcută cu `populare_initiala.py --din-bronze` și măsurată cu
`scripts/raport_calitate.py` (scriptul din `docs/IMBUNATATIRI.md`):

| | 23.09 (Robert) | 24.09 seara |
|---|---:|---:|
| concept comparabil | 59% | **76%** |
| valori „curate” | 46% | **64%** |
| datate | 57% | 69% |
| ambigue | 24% | 19% |

Baza are mult mai multe documente decât setul fix; BCR singură are 171 de PDF-uri.
Pe comisioanele din documentele românești, 84% au concept. Pe versiunile în engleză ale
listelor BCR PJ („Fees and commissions”, „Tariffs for legal entities”), doar 47%
(rezolvat pe 25.09, vezi mai jos).

## 25.09: ce s-a mai schimbat

| | 24.09 seara | 25.09 |
|---|---:|---:|
| setul fix, comisioane mapate | 95,6% (6.536 / 6.835) | **96,0%** (6.568 / 6.839) |
| baza, valori curente (ce vede aplicația) | 27.569 | 22.926 |
| baza, concept comparabil | 76% (pe toate valorile) | 76% pe toate, **83% pe cele curente** |
| baza, valori „curate” din cele curente | 65% | **71%** |
| teste (`scripts/test_validare.py`) | 480 | 506 |

1. **Documentele doar în engleză sunt `DUBLURA`** (`crawler/data_document.py`). Legea
   cere listele de prețuri în română, iar fiecare listă în engleză din bază avea
   geamănul românesc de aceeași dată (BCR PJ, Raiffeisen corporații și IMM, Garanti
   T0012). Se încarcă în continuare, dar nu intră în comparații și nici în Istoric.
   - Limba se citește din textul primelor pagini, nu din nume. Pe cele 567 de PDF-uri
     din bază, listele bilingve (Techventures, TBI, PKO) au cel mult 63% cuvinte de
     legătură englezești, traducerile cel puțin 91%; pragul e 85%.
   - 67 de documente, 4.633 de valori: 48 la BCR, 6 la PKO (de pe pkobp.pl), 5 la
     Raiffeisen, apoi formularele IRS, raportul Revolut, fișa Bank of China.
2. **Reparația „celule”, unită** (merge `f5b4395`). Rândurile aceleiași celule cu
   bordură se lipesc într-o etichetă, chiar dacă al doilea începe cu majusculă, iar
   muchia dintre două fundaluri de aceeași culoare nu mai e bordură.
   - Refăcută peste codul de acum, cu trei condiții noi, fiecare măsurată: exact un preț
     în celulă, rândul rupt de lățime, rânduri vecine.
   - Pe setul fix: +28 mapate, 9 mutate, 4 valori noi, niciuna pierdută. Toate cele 41
     de schimbări verificate în PDF.
3. **Vocabularul după etichetele întregi** (`8ab873d`): când celula numește două servicii,
   decide primul. „Interogare sold … /Schimbare PIN” (Salt, 5 valori) e interogare de
   sold, „card (emitere și reînnoire)” (Garanti) e emitere, „Verificare/ confirmare/ …
   semnături” (Libra) e verificare de semnătură.

**De ce scad unele cifre din `raport_calitate.py`.**
- **„Curate” pe toate valorile (64% → 58%):** scriptul împarte la toate valorile,
  inclusiv cele `DUBLURA`, deci scoaterea traducerilor din comparații arată ca o scădere.
  Pe valorile curente, cifra crește de la 65% la 71%. Ar merita împărțit la curente.
- **Libra, −34 de rânduri:** e același serviciu, care înainte apărea de două ori, o
  dată cu eticheta întreagă și o dată ruptă („RECOM Alte servicii…”, „Juridice”).
  Acum ambele au eticheta întreagă și se strâng într-un rând cu `nr_aparitii = 2`.
  Extracția dă aceleași 1.878 de valori brute cu codul vechi și cu cel nou.

Liniile prea eterogene cresc odată cu numărul de linii: intră concepte noi și 500 de
valori recuperate. Nu le-am analizat încă una câte una. Dimineață, creșterea venea din
dispersie reală în date (TBI „min. 5 LEI” lângă BCR „min. 30 LEI”), nu din parser.

Pe bancă, setul fix:

| bancă | dimineață | acum |
|---|---:|---:|
| BCR | 82% | 95% |
| Libra | 78% | 95% |
| Vista | 81% | 97% |
| Nexent | 73% | 97% |
| BRD | 73% | 89% |
| Raiffeisen | 79% | 96% |
| BRCI | 95% | 99% |
| Eximbank | 86% | 95% |
| Techventures | 87% | 97% |
| ProCredit | 61% | 97% |
| Salt | 89% | 99% |
| TBI | 82% | 91% |
| Garanti | 74% | 93% |
| CreditCoop | 99% | 99% |
| BCR Locuințe | 0% | 33% |

## Cum am măsurat și cât de sigure sunt cifrele

- **Setul fix:** 68 de documente alese o dată și păstrate între rulări, ca două versiuni
  ale parserului să se compare pe aceleași PDF-uri.
- **Clasificarea de mână:** cele 1.077 de comisioane nemapate de dimineață au fost
  verificate una câte una, în PDF. A ieșit o listă de lucru, nu o estimare:

  | ce era | valori |
  |---|---:|
  | serviciu clar, fără concept în vocabular | 438 |
  | etichetă greșită (defect de parser) | 338 |
  | concept existent, dar tiparul nu-l prindea | 138 |
  | nu e comision (condiție, dobândă, limită) | 87 |
  | valoare falsă (cuprins, notă de subsol) | 38 |
  | notă de sub tabel cu valoare | 29 |
  | neclar | 9 |

- **Precizia:** fiecare schimbare a fost verificată în PDF, pe eșantion aleator sau pe
  toate valorile atinse:

  | ce | verificate | corecte |
  |---|---:|---:|
  | mapări noi din vocabular (eșantion aleator) | 77 comisioane | 74 (96%) |
  | parser: rândurile de grilă | 80 | 78 |
  | parser: valori recuperate | 509 | 487 |
  | parser: subpunctele și părintele lor | 83 | 81 |
  | parser: valori false scoase din comisioane | 175 | 169 |
  | parser: secțiunile (titlurile) | 74 | 72 |
  | parser: eticheta aleasă din rând | 45 | 40 |

- **Teste:** `python scripts/test_validare.py` dă 480 trecute, 0 eșuate (246 la `e3e7d48`,
  după rundele de dimineață).

## Ce s-a schimbat

### 1. Vocabularul (`crawler/vocabular.py`)

**33 de concepte noi**, fiecare cu etichetele reale din PDF-uri. Au și eticheta
românească în `app/index.html`.

| grup | concepte |
|---|---|
| carduri | `tranzactie_gambling` (separat de plata cu cardul: 1% + 10 lei), `card_pierdut_furat`, `inchidere_card`, `acces_lounge` |
| servicii | `caseta_valori`, `eliberare_document` (adeverințe, confirmări de sold, scrisori de bonitate), `curierat_posta`, `investigatie`, `imputernicire`, `verificare_semnatura`, `portabilitate_cont` |
| numerar | `depunere_moneda` (alt preț decât bancnotele), `neridicare_numerar`, `miniextras_atm` |
| canale la distanță | `activare_banking_distanta`, `token`, `notificare_push`, `notificare_email`, `terminal_pos` |
| credite | `acordare_credit`, `administrare_credit`, `rambursare_anticipata`, `modificare_credit`, `evaluare_garantie`, `neplata_credit`, `garantare_credit`, `inregistrare_garantie` (RNPM/AEGRM) |
| asigurări și titluri | `plata_asigurare`, `asigurare_credit`, `asigurare_card`, `custodie_titluri`, `tranzactionare_titluri` |

**Mapări greșite reparate** (concept greșit → concept corect):

- **Libra:** 55 de valori „utilizare mijloc de plată (card) la ATM” erau transferuri,
  acum sunt retrageri.
- **Investigații:** ~34 de valori erau transferuri, încasări sau cecuri, după obiectul
  lor. Acum au conceptul lor, deci nu mai strică liniile de preț ale transferurilor.
- **„franco de plată”:** eliberarea documentelor „franco de plată” e serviciu
  documentar, nu plată (16 valori la 6 bănci).
- **Avizele RNPM** nu mai sunt `modificare_anulare`.
- **Tipare prea largi:** „aval” nu mai prinde „contravaloare”, iar canalul „mobil” nu
  mai prinde „imobil” (42 de valori aveau canalul `mobile_banking` fără să fie).
- **Alte greșeli de concept:** „BCR Alert” e alertă SMS, „extras duplicat aferent
  cardului” e extras, nu card nou.
- **Liste scrise altfel:** lista TBI în engleză („Statement of account”, „Swift fees”),
  „monet” (internet bankingul Nexent) și benzile Vista „≥ 50.000 LEI și urgente”.

### 2. Parserul (`crawler/parser_tarife.py`, `crawler/parser_pdf.py`)

Șase reparații, fiecare măsurată separat pe setul fix și apoi unite:

1. **Rândurile de grilă.** Cuvântul cu exponent de notă („plată¹”, „RON1”) nu mai rupe
   rândul: se grupează după linia de bază. Pagina Raiffeisen scanată la 300 dpi e adusă
   la A4 înainte de orice toleranță.
2. **Valori recuperate** (+508 pe setul fix):
   - „0” fără monedă, felul în care Nexent, Vista, TBI și BCR scriu „gratuit”;
   - mii scrise cu virgulă („3,000 euro” ieșea 0);
   - moneda înaintea sumei („RON 4”);
   - intervalele („550 – 3.300 lei”, păstrate ca minim și maxim);
   - minimul sau maximul rupt pe două rânduri.
3. **Subpunctele își recapătă părintele,** după indentare, după celula din stânga și
   după ierarhia marcajelor („–” peste „•”).
4. **Valorile false ies din comisioane, fără să se arunce.** Primesc altă categorie:
   - **`nota`:** notele de sub tabel („*Comisionul Transfond de 0,51 LEI…”);
   - **`dobanda`:** IRCC, EURIBOR, ROBOR;
   - **`limita`:** limite per tranzacție și sume minime;
   - **`taxa_stat`:** coloana „Taxa către bugetul de stat” (AEGRM).

   Tot aici: „inclus” nu mai înseamnă gratuit în titluri, cuprins și proză. Cele 30 de
   valori „gratuit” false au dispărut, iar 18 dintre ele erau mapate greșit.
5. **Secțiunile:**
   - index fără punct final („7.1 Scrisori de garanție”): „Executare” și „Cesiune” de
     la Nexent sunt acum documentar;
   - capitolele cu cifre romane;
   - numerotarea reluată sub un capitol;
   - punctele numerotate din celulele de preț nu mai devin titluri.
6. **Eticheta rândului.**
   - Eticheta e celula de text cea mai apropiată la stânga prețului, nu cel mai lung
     text de pe rând. La BRD, eticheta nu mai vine din coloana de dobânzi alăturată.
   - Suma scrisă în numele serviciului („sold mai mare de 500 RON”) e condiție, nu preț.

### 3. Baza de date

- **`db/migration_018_metoda_populare.sql`:** `ingest/populare_initiala.py` scrie
  `metoda_extractie = 'populare'`, dar CHECK-ul din migrarea 007 nu permitea valoarea.
  Pe o bază adusă doar cu migrările din repo, popularea de la zero pica la scriere
  (9 bănci la prima rulare). **Robert:** migrarea trebuie trecută în lista din README;
  n-am atins README-ul tău.
- **Categorii noi:** `nota` și `taxa_stat` ajung în `cod_scenariu` ca prim segment.
  `normalizeaza.py` nu le respinge, dar în aplicație apar ca scenarii noi.

## Ce rămâne

1. **Versiunile vechi ale aceleiași liste nu sunt marcate `ISTORIC` în bază (pentru
   Robert).** Lanțul de măsurare are regula (`scripts/date_documente.py`,
   `marcheaza_versiuni_depasite`), dar `populare_initiala.py` n-o aplică, iar vederea
   `observatii_curente` exclude doar ce e marcat. Lista PJ BCR din martie, iulie și
   august 2026 sunt toate „în vigoare”, deci prețurile din martie intră în aceeași
   celulă cu cele din august.
   - Măsurat pe 25.09, doar pe versiunile cu nume identic (`familie_document`), deci o
     limită de jos: 4.742 de valori curente vin din versiuni depășite (BCR 3.991, din
     care 1.261 din listele în engleză, acum `DUBLURA`; Garanti 442; BRCI 292; BRD 17).
   - Propunere: funcția din `date_documente.py` mutată în `crawler/data_document.py`
     și aplicată pe înregistrările brute ale unei bănci înainte de scriere. N-am atins
     `populare_initiala.py`.
2. **Conceptul luat din secțiune.** `RE_ETICHETA_FRAGMENT` e compilat cu `re.I`, deci
   aproape orice etichetă nemapată își ia conceptul din secțiune.
   - Verificat în PDF pe 80 de astfel de mapări: 56 corecte, 16 greșite, 8 nu erau
     comisioane (78% precizie).
   - Reparat pe loc ce ținea de vocabular (investigare, schimb de valută efectivă,
     schimb de bancnote).
   - Restul vine din etichete pierdute de parser.
3. **Nemapate rămase pe setul fix: 271 din 6.839** (299 pe 24.09).
   - Etichete încă greșite: cea mai mare parte.
   - Servicii izolate, câte unul la o singură bancă, fără concept (de exemplu
     certificatele de depozit BCR, TrezoNet, „Free-Way” la Raiffeisen).
   - BCR Locuințe: dobânzi într-o matrice al cărei antet se pierde.
4. **Conceptele noi nu apar încă în matricele de comparație.** `app/server.py` (GRUPURI)
   are doar grupurile Cont curent, Carduri și Transferuri. Un grup „Credite
   (comisioane)” și unul „Servicii” ar fi următorul pas în interfață.
5. **Documentele de pe altă piață.** Lista de prețuri PKO în poloneză („Taryfa prowizji”)
   intră încă în bază; detectorul de limbă prinde doar engleza.

## Cum refaci

```bash
python scripts/test_validare.py            # 506 trecute (25.09)
python ingest/populare_initiala.py --din-bronze --paralel 6   # baza, cu parserele noi, fără rețea
# lanțul de măsurare pe PDF-urile din output/crawl/pdf (~10 min):
python scripts/parseaza_pdf.py && python scripts/parseaza_tarife.py
python scripts/unifica_comisioane.py && python scripts/date_documente.py
python scripts/unifica_comisioane.py
```

Commit-urile zilei, în ordine:
- **dimineață:** `a669676`, `a30783d`, `7739311`, `390a572`, `e3e7d48`;
- **merge cu popularea lui Robert:** `b3b2f4f`;
- **vocabularul:** `e283d4f`, `507acf8`, `50ed833`, `fd05965`;
- **reparațiile de parser:** merge-urile `a7b166b` (rânduri), `4f65ecf` (valori),
  `e5d38c2` (părinte), `deccae3` (valori false), `328fd18` (secțiuni), `e163788`
  (etichetă);
- **25.09:** `dea1d33` (traducerile sunt `DUBLURA`), merge-ul `f5b4395` (celule),
  `8ab873d` (vocabular după celule).
