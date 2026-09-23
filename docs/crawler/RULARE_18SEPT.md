# Rularea din 18 septembrie: limita 32 -> 80

<!-- antet-vechime -->
> **Cifrele din documentul ăsta sunt cele de pe 18 septembrie 2026 și nu au fost
> actualizate.** Se păstrează ca jurnal de lucru: arată ce se știa atunci și
> cum s-a ajuns acolo. **Totalurile curente sunt în
> [CONSTATARI.md](CONSTATARI.md)**, iar regulile de filtrare pentru integrare
> în [CITESTE_PENTRU_MERGE.md](CITESTE_PENTRU_MERGE.md).

Generat de `scripts/dupa_crawl.py` la 15:09.

**Acoperirea cerințelor: 178/460 = 39%** (era 170/460 = 37% la crawlul din 16 septembrie).

Bănci recrawlate: 23 din 23. Documente pe disc: 808 (erau 319).

| bancă | cerințe | pagini | descoperire | URL-uri | PDF |
|---|---:|---:|---|---:|---:|
| brd | 19/20 | 79 | sitemap | 1110 | 394 |
| raiffeisen | 18/20 | 80 | sitemap | 1222 | 142 |
| bcr | 17/20 | 80 | sitemap | 2565 | 144 |
| eximbank | 17/20 | 79 | sitemap | 1550 | 21 |
| ing | 13/20 | 80 | navigatie | 117 | 1 |
| libra | 13/20 | 60 | sitemap | 328 | 126 |
| patria | 13/20 | 80 | sitemap | 624 | 1 |
| procredit | 10/20 | 80 | sitemap | 315 | 172 |
| nexent | 8/20 | 42 | navigatie | 83 | 61 |
| tbi | 8/20 | 53 | sitemap | 1023 | 127 |
| creditcoop | 6/20 | 55 | navigatie | 65 | 23 |
| garanti | 6/20 | 32 | sitemap | 564 | 58 |
| brci | 5/20 | 17 | navigatie | 50 | 29 |
| revolut | 5/20 | 17 | navigatie | 82 | 17 |
| cetelem | 4/20 | 80 | sitemap | 178 | 8 |
| credex | 4/20 | 78 | sitemap | 107 | 94 |
| salt | 4/20 | 9 | navigatie | 51 | 22 |
| techventures | 4/20 | 42 | navigatie | 62 | 209 |
| vista | 2/20 | 6 | navigatie | 32 | 30 |
| bcrlocuinte | 1/20 | 7 | sitemap | 109 | 11 |
| bid | 1/20 | 7 | navigatie | 28 | 1 |
| bankofchina | 0/20 | 0 | navigatie | 49 | 0 |
| bnpparibas | 0/20 | 0 | sitemap | 38 | 0 |

## Pașii de după crawl

| pas | cod | secunde |
|---|---|---:|
| parseaza_pdf | ok | 37 |
| parseaza_tarife | ok | 64 |
| unifica_comisioane | ok | 2 |
| ruleaza_validare | ok | 1 |
| compara_rate | ok | 0 |
| urmareste | ok | 17 |
| raport | ok | 0 |
| teste | ok | 1 |
| teste_robots | ok | 0 |
| arhiva | ok | 2 |

## Ieșirile pașilor

<details><summary>parseaza_pdf</summary>

```
0cu_20priv_20la_20c
    28 comisioane  creditcoop   28dc50f3_Document_Informare_Comisioane_cont-APIA.pdf
    29 comisioane  creditcoop   2dc8d9c3_Document_Informare_Comisioane_cont-de-plati
    11 comisioane  creditcoop   4a5a3b52_Document_Informare_Comisioane_cont-de-plati
    26 comisioane  creditcoop   baf6df0b_Document_Informare_Comisioane_contul-de-pla
    28 comisioane  creditcoop   Document_Informare_Comisioane_cont-APIA.pdf
    20 comisioane  creditcoop   Document_Informare_Comisioane_cont-de-plati-pentru-c
    11 comisioane  creditcoop   Document_Informare_Comisioane_cont-de-plati-pentru-c
    29 comisioane  creditcoop   Document_Informare_Comisioane_cont-de-plati.pdf
    26 comisioane  creditcoop   Document_Informare_Comisioane_contul-de-plati-pentru
    20 comisioane  creditcoop   fc4f4205_Document_Informare_Comisioane_cont-de-plati
    26 comisioane  libra        6126521f_informare-comisioane-cont-plati-euro.pdf
    39 comisioane  libra        ac7e62e4_informare-comisioane-cont-plati.pdf
    26 comisioane  libra        informare-comisioane-cont-plati-euro.pdf
    39 comisioane  libra        informare-comisioane-cont-plati.pdf
    22 comisioane  procredit    1be2f1df_Document_informare_comisioane_Cont_Plati_Se
    92 comisioane  procredit    cd15a9d4_Document_informare_comisioane_ProActive_Pla
    24 comisioane  procredit    dc64273e_Document_informare_comisioane_Cont_Plati_Se
    92 comisioane  procredit    Document_informare_comisioane_ProActive_Platinum_Pro

total: 900 comisioane din 34/34 documente

pe tip:     {'comision_suma': 698, 'comision_procent': 110, 'gratuit': 92}
pe moneda:  {'LEI': 573, None: 202, 'EUR': 125}
pe banca:   {'bcr': 224, 'brci': 88, 'creditcoop': 228, 'libra': 130, 'procredit': 230}
frecvente:  {'lunar': 158, 'anual': 82, 'pe operațiune': 162, 'pe card': 2}
cu conditie de suma: 20

servicii distincte: 184
cele mai frecvente:
   20  Administrarea contului (EURO)
   18  Administrarea contului
   18  Administrare Internet Banking
   16  George, conţinȃnd: - administrarea Cont curent în lei; - furnizarea 
   16  • Visa Classic Standard (național/internațional)
   16  • Visa Classic VIP (național/internațional)
   14  Depuneri de numerar în contul clientului
   14  Plati interbancare in Lei
   13  Plăți instant ≤ LEI 5.000
   12  Depuneri de numerar în alt cont
   12  Retrageri de numerar în euro de la ghișeul băncii
   12  Plăți interbancare în EUR¹  Plăti in afara UE/SEE2 sau in UE/SEE in

>> output\comisioane_pdf.json
```

</details>

<details><summary>parseaza_tarife</summary>

```
199 comisioane libra        5a7975c2_Tarife_si_Comisioane_PF.pdf
     28 comisioane libra        876e2aa4_comisioane_card_Avanpost_Gold_Eur.pdf
     29 comisioane libra        aec9a86c_comisioane_card_Avanpost_Gold_Junior.pdf
     29 comisioane libra        bfb4ebc5_comisioane_Libra_Business_Gold.pdf
     28 comisioane libra        c0cb9bfa_comisioane_Libra_Business_Standard_Credit.p
     29 comisioane libra        c1a9db96_comisioane_Libra_Business_Standard.pdf
     28 comisioane libra        dd97d4d2_comisioane_Libra_Business_Gold_Credit.pdf
     74 comisioane procredit    b87c9032_lista-de-dobanzi-si-comisioane-produse-de-c
    187 comisioane raiffeisen   1ccc76d7_20260901-Tarife-si-comisioane-standard-pers
    138 comisioane raiffeisen   6f118df0_tarife-si-comisioane-imm-si-profesii-libera
    156 comisioane raiffeisen   dfb01cea_tarife-si-comisioane-standard.sv.pdf
    221 comisioane salt         f2722489_lista-taxelor-si-comisioanelor-aplicate-cli
     79 comisioane tbi          2a19e4de_Lista-de-dobanzi-taxe-si-comisioane-pentru-
     17 comisioane tbi          3c340cb8_List_of_interest_rates_taxes_and_fees_for_p
     67 comisioane tbi          ca45679b_Lista_de_dobanzi_taxe_si_comisioane_pentru_
    111 comisioane techventures 431b244d_lista-de-tarife-si-comisioane-persoane-fizi
    149 comisioane techventures 88db1c81_lista-de-tarife-si-comisioane-aplicabile-en

!! 1 documente au dat ZERO comisioane:
     bcr          bd6e5812_Click24Banking_PlataImpoziteTaxe.pdf

total: 6301 comisioane din 39/40 documente

pe tip:      {'comision_suma': 4089, 'comision_procent': 1311, 'gratuit': 901}
pe moneda:   {'LEI': 2854, None: 2212, 'EUR': 1235}
pe banca:    {'bcr': 2479, 'bcrlocuinte': 24, 'brci': 708, 'brd': 584, 'eximbank': 283, 'garanti': 213, 'libra': 811, 'procredit': 74, 'raiffeisen': 481, 'salt': 221, 'tbi': 163, 'techventures': 260}
geometrie:   {'bordura': 5866, 'unic': 152, 'gol': 283}
categorie:   {'comision': 6112, 'limita': 81, 'dobanda': 98, 'curs': 10} (doar 'comision' intra in comparatie)
cu sectiune: 5906
cu coloana:  1888
cu serviciu: 6301
cu conditie: 334

servicii distincte: 2015
    45  Avizare
    45  - de la ATM-uri ale Erste Group7
    42  - de la ATM-uri BCR tranzacție
    42  tranzacție
    38  - 50.000 LEI, exclusiv
    36  îndeplinirea tuturor criteriilor de la 7.3)
    36  Cumpărare bunuri/servicii
    36  Blocare card furat/pierdut
    36  Regenerare PIN
    36  Comision schimbare PIN la ATM

>> output\comisioane_tarife.json
```

</details>

<details><summary>unifica_comisioane</summary>

```
total valori:            7201
  din care comisioane:   7012
  mapate pe un concept:  4496 (64%)
  cu canal:              1127
  cu destinație:         845

concepte folosite: 29 din 29
   1142 valori  12 bănci  transfer_credit
    468 valori  10 bănci  retragere_numerar
    424 valori   8 bănci  documentar
    284 valori  10 bănci  incasare
    258 valori  12 bănci  administrare_cont
    197 valori  10 bănci  emitere_card
    180 valori  10 bănci  modificare_anulare
    167 valori   6 bănci  schimbare_pin
    158 valori   8 bănci  administrare_card
    139 valori   3 bănci  tranzactie_card
    136 valori   9 bănci  reemitere_card
    117 valori   7 bănci  depunere_numerar
    110 valori   9 bănci  interogare_sold
    100 valori  11 bănci  extras_de_cont
     78 valori   9 bănci  deschidere_cont
     76 valori   7 bănci  administrare_banking_distanta
     65 valori   4 bănci  blocare_card
     64 valori   7 bănci  livrare_card
     57 valori   7 bănci  file_cec
     53 valori   5 bănci  conversie_valutara
     38 valori   5 bănci  debitare_directa
     36 valori   5 bănci  refuz_plata
     30 valori   6 bănci  interogare_baze_date
     27 valori   6 bănci  speze_swift
     25 valori   3 bănci  plata_programata
     21 valori   7 bănci  poprire
     20 valori   5 bănci  inchidere_cont
     14 valori   2 bănci  acceptare_carduri
     12 valori   4 bănci  alerta_sms

NEMAPATE: 2516 — cele mai frecvente denumiri:
    45  - de la ATM-uri ale Erste Group7
    42  - de la ATM-uri BCR tranzacție
    42  tranzacție
    38  - 50.000 LEI, exclusiv
    33  USD/ tranzacție
    33  Comision contestare nejustificată a unei tranzacții
    30  Peste 50.000 LEI, inclusiv
    27  efectuate în altă monedă decât cea a contului de card
    24  USD card
    21  - suplimentar pentru utilizator autorizat
    21  nepermisă
    20  Contestare nejustificată a unei tranzacţii

linii comparabile (>=3 bănci): 105

>> output\comisioane_unificate.json
>> output\comparatie_comisioane.md
```

</details>

<details><summary>ruleaza_validare</summary>

```
https://www.garantibbva.ro/imm-si-pfa/comisioane-si-dobanzi-credite-imm-si-pfa/
  [garanti   ] robor_valoare       7.86%
      difera de BNR cu 2.02 p.p. (5.84%) -> informatie probabil depasita pe site
      https://www.garantibbva.ro/imm-si-pfa/comisioane-si-dobanzi-credite-imm-si-pfa/

=== CONFIRMATE CU BNR ===
  [patria    ] euribor_valoare    2.568%  confirmat cu BNR (2.568%)

=== INDICE IMPLICIT (total - marja, citit din pagina) ===
  [eximbank  ] indice implicit din pagina: 9.06% - 3.5% = 5.56% (IRCC); coincide cu IRCC in vigoare (5.56%)
      https://www.eximbank.ro/calculator-dobanda-anuala-efectiva/
  [ing       ] indice implicit din pagina: 8.05% - 2.49% = 5.56% (IRCC); coincide cu IRCC in vigoare (5.56%)
      https://ing.ro/persoane-fizice/credite/ipotecar
  [libra     ] indice implicit din pagina: 8.68% - 3.0% = 5.68% (IRCC); IRCC in vigoare e 5.56% — aritmetica paginii nu se potrivește cu indicele declarat de restul pieței; de verificat manual
      https://www.librabank.ro/credit-nevoi-personale-fara-ipoteca
  [libra     ] indice implicit din pagina: 10.18% - 4.5% = 5.68% (IRCC); IRCC in vigoare e 5.56% — aritmetica paginii nu se potrivește cu indicele declarat de restul pieței; de verificat manual
      https://www.librabank.ro/credit-nevoi-personale-fara-ipoteca
  [patria    ] indice implicit din pagina: 5.818% - 3.25% = 2.568% (EURIBOR); coincide cu EURIBOR in vigoare (2.568%)
      https://www.patriabank.ro/persoane-fizice/credite/credit-de-consum-econom

=== CONSISTENTE ARITMETIC (indice + marja = nominala) ===
  [libra] consistent aritmetic: IRCC 5.56% + marja 12.25% = 17.81% (regasit in pagina)
  [patria] consistent aritmetic: IRCC 5.56% + marja 3.17% = 8.73% (regasit in pagina)
  [patria] consistent aritmetic: IRCC 5.56% + marja 2.5% = 8.06% (regasit in pagina)
  [patria] consistent aritmetic: IRCC 5.56% + marja 2.9% = 8.46% (regasit in pagina)
  [patria] consistent aritmetic: IRCC 5.56% + marja 2.5% = 8.06% (regasit in pagina)
  [patria] consistent aritmetic: IRCC 5.56% + marja 3.77% = 9.33% (regasit in pagina)

=== SUSPECTE ===
  [libra] marja_ircc=3.0% :: indice implicit din pagina: 8.68% - 3.0% = 5.68% (IRCC); IRCC in vigoare e 5.56% — aritmet
      - Cu condiția încasării salariului la Libra: 3% + IRCC (8.68%)
  [libra] marja_ircc=4.5% :: indice implicit din pagina: 10.18% - 4.5% = 5.68% (IRCC); IRCC in vigoare e 5.56% — aritme
      - Fără condiție de virare salarială: 4.50% % + IRCC (10.18%)

>> output/rate_validate.json
```

</details>

<details><summary>compara_rate</summary>

```
rate validate:           609
  mapate pe un produs:   499 (81%)
  excluse (promo/cashback/comision): 147
  indici de piață (nu se compară): 22
  cu sursă învechită:    7

pe produs:
   101 valori  10 bănci  credit_ipotecar
    85 valori  10 bănci  credit_nevoi_personale
    81 valori   9 bănci  depozit_termen
    52 valori   7 bănci  refinantare
    36 valori   5 bănci  card_cumparaturi
    33 valori   2 bănci  credit_auto
    26 valori   4 bănci  cont_economii
    24 valori   8 bănci  card_credit
    21 valori   8 bănci  cont_curent
    17 valori   6 bănci  descoperit_cont
    10 valori   5 bănci  noua_casa
     5 valori   2 bănci  card_debit
     3 valori   1 bănci  card_junior
     2 valori   1 bănci  leasing
     2 valori   1 bănci  credit_magazin
     1 valori   1 bănci  card_salariu

linii comparabile (>=3 bănci): 15

>> output\rate_unificate.json
>> output\comparatie_rate.md
```

</details>

<details><summary>urmareste</summary>

```
versiunea parserului:  1e009595ac24acb8
rulari anterioare:     1
documente referite:    1179

  NOU            151
  LIPSA            6
  NESCHIMBAT     314
  NEDESCARCAT    714

niciun document nu si-a schimbat octeții de la ultima rulare.

=== NU MAI E REFERIT (banca a fost recrawlata) ===
  [creditcoop] https://www.creditcoop.ro/fisiere/2023/10/Formular-pentru-Informatiile-oferite-deponentilor.pdf
  [creditcoop] https://www.creditcoop.ro/fisiere/2023/10/Depozite-excluse-de-la-garantare.pdf
  [ing] https://ing.ro/dam/jcr:d329abe5-c151-4ae6-97bb-e24c6be22434/termeni_si_conditii_specifice_depozitelor_si_tranzactiilor_de_schimb_valutar_la_vedere_spot.pdf
  [ing] https://ing.ro/dam/ingro/doc/contractuale/pers-juridice/Termeni-si-Conditii-Specifice-Contului-de-Economii-20250718.pdf
  [ing] https://ing.ro/dam/ingro/doc/contractuale/pers-juridice/en/Specific-terms-and-conditions-Deposits-and-FX-SPOT-Transactions.pdf
  [ing] https://ing.ro/dam/ingro/doc/contractuale/pers-juridice/en/Specific-Terms-and-Conditions-for-Saving-Account-20250718.pdf

=== ORIGINI FARA ROBOTS.TXT CITIT ===
robots.txt e per origine prin standard. Documentele descarcate de
pe originile de mai jos nu au o regula citita pentru ele:

  www.procreditbank-direct.com     1 doc   (legate de la: procredit)

  total: 1 documente de pe 1 origini neverificate
  de rezolvat: python scripts/verifica_robots_origini.py

comparație de valori: DA — parser neschimbat de la ultima rulare (1e009595ac24acb8)

>> 1185 documente in registru (erau 804)
   output/urme.json
```

</details>

<details><summary>raport</summary>

```
Raport scris in C:\Users\nicolae.cherascu\Desktop\incercare playwright\output\RAPORT.md
  23 banci, 1063 pagini
```

</details>

<details><summary>teste</summary>

```
73 trecute, 0 eșuate
```

</details>

<details><summary>teste_robots</summary>

```
=== ING (6 reguli) ===
  OK  permite(https://ing.ro/persoane-fizice/credite) = True (așteptat True)
  OK  permite(https://ing.ro/dam/ingro/doc/contractuale/pers-fizice/Lista-de-taxe-si-comisioane.pdf) = False (așteptat False)
  OK  permite(https://ing.ro/dam/jcr:abc/rate_dobanzi.pdf) = False (așteptat False)
  OK  permite(https://ing.ro/dam/ingro/sitemaps/sitemap.xml) = False (așteptat False)
  OK  permite(https://ing.ro/migrate/ceva) = False (așteptat False)
  OK  permite(https://ing.ro/TSPD/x) = False (așteptat False)

=== BCR (4 reguli) ===
  OK  permite(https://www.bcr.ro/ro/persoane-fizice/credite) = True (așteptat True)
  OK  permite(https://www.bcr.ro/search) = False (așteptat False)
  OK  permite(https://www.bcr.ro/ro/produs.compare) = False (așteptat False)
  OK  permite(https://cdn.erstegroup.com/x/Tarif.pdf) = True (așteptat True)

=== PATRIA (2 reguli) ===
  OK  permite(https://www.patriabank.ro/persoane-fizice/credite) = True (așteptat True)
  OK  permite(https://www.patriabank.ro/d/document.pdf) = False (așteptat False)
  OK  permite(https://www.patriabank.ro/content/x) = False (așteptat False)
  OK  crawl-delay = 5.0 (așteptat 5)

TOATE TESTELE AU TRECUT
```

</details>

<details><summary>arhiva</summary>

```
>> output\pentru_coleg_bs4_18sept.zip
   65 fișiere, 714 KB
   13 module, 26 scripturi, 14 documente, 12 rezultate
```

</details>
