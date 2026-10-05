# 06. Ce poți refolosi pentru Meta, LinkedIn și Microsoft

Partea Google e făcută: știm cine face reclame, când, cât, unde și cum țintește, dar nu **ce spun** reclamele. Celelalte trei biblioteci dau tocmai textul reclamei. Împreună, cele patru surse ar acoperi mai multe bănci și ar da un conținut pe care Google nu-l are.

Termenii, accesul și pașii pentru fiecare platformă sunt în `context/RECLAME_BIBLIOTECI_OFICIALE_2026-09-28.md`. Aici e doar ce se leagă de munca pe Google.

## 1. Lista băncilor și capcanele căutării după nume

- **Punctul de plecare:** `ingest/banks.py`, în repo, cu cele 30 de bănci, numele oficiale și site-urile. Pe Google s-au adăugat `fisiere/google_advertiseri.csv`, cu numele sub care apar băncile, și agențiile lor.
- **La Meta, LinkedIn și Microsoft vei da probabil de aceleași capcane.** Pe Google le-am măsurat pe toate:

| capcană | pe Google | ce să verifici la tine |
|---|---|---|
| **aceeași bancă, mai multe conturi** | BT are 2 ID-uri, ING 2, Revolut 3 | toate paginile sau conturile unei bănci |
| **grupul din altă țară** | RBI are 747 de reclame livrate și în RO, dar în germană; Société Générale, Intesa (Italia), ProCredit, BNP și Cetelem (Spania), PKO și Citi au împreună 513 | dacă reclamele sunt făcute pentru piața din România: limba, țările de livrare |
| **nume asemănător, altă firmă** | GARANTI PREST, cu 1.796 de reclame; „Revolut” (RO), cu reclame Autovit; BCR Asigurări de Viață, care aparține VIG | verificare de mână a fiecărui cont găsit după nume |
| **publicare prin agenție** | Intesa prin WPP Media Romania, găsită după „plătit de”; BRD prin Sense8, găsită doar căutând `brd.ro` | câmpurile de plătitor sau beneficiar și căutarea după site, unde există |
| **entitatea globală** | Revolut face reclame în RO doar din contul Revolut Ltd (GB), cu ~20% dintre reclame în română; doar 26% rulează numai în România | la fel la Meta: pagina globală sau una locală |

**La Microsoft, pe 25.09, Raiffeisen a apărut ca „Raiffeisen Bank International”.** Pe Google, RBI are reclame în germană și l-am exclus. La Microsoft trebuie verificat separat dacă reclamele RBI sunt pentru România.

## 2. Regulile de atribuire folosite pe Google

1. **O reclamă se leagă de bancă prin ID-ul contului, dintr-o listă fixă,** niciodată doar prin nume. Căutarea după nume servește doar la descoperirea conturilor.
2. **Fiecare cont găsit primește un rol:** `banca`, `filiala`, `agentie`, `exclus` sau `de_verificat`, cu o notă despre motiv și data verificării. Modelul e în [01](01_PASI_GOOGLE.md), pasul 6.
3. **Grupurile din alte țări se exclud** dacă reclamele lor nu sunt pentru România. Excepție: entitatea e singura prin care banca își face reclamele aici, cum e Revolut Ltd.
4. **O agenție contează la bancă doar pe reclamele unde plătitorul sau beneficiarul numește banca.**
5. **Filialele se țin separat** și nu intră în comparația dintre bănci.

**Propunere:** câte o listă pe platformă, cu aceleași coloane ca `google_advertiseri.csv` (`banca, id, nume, tara, rol, nota`): `meta_pagini.csv`, `linkedin_advertiseri.csv`, `microsoft_advertiseri.csv`.

## 3. Un model comun de date, ca să le putem pune împreună

Coloanele Google sunt cele reale, din [02](02_CAMPURI.md). Pentru celelalte platforme sunt conceptele din documentul din 28.09; numele exacte ale câmpurilor le confirmi din documentația oficială.

| câmp comun | Google (BigQuery) | Meta | LinkedIn | Microsoft |
|---|---|---|---|---|
| `platforma` | google | meta | linkedin | microsoft |
| `banca` | din `google_advertiseri.csv` | din lista paginilor | din lista advertiserilor | din lista advertiserilor |
| `cont_id`, `cont_nume` | `advertiser_id`, `advertiser_disclosed_name` | pagina de Facebook | advertiserul | advertiserul |
| `platitor` | `ad_funded_by` (agenția) | plătitorul și beneficiarul (UE) | plătitorul | plătitorul |
| `reclama_id`, `link` | `creative_id`; link spre ATC | ID-ul reclamei; `ad_snapshot_url` | ID-ul reclamei; previzualizarea | ID-ul reclamei |
| `text` | **nu există** | textul, titlul, descrierea | textul creației | titlul și textul complet |
| `format` | `ad_format_type` | – | formatul | – |
| `prima_afisare`, `ultima_afisare` | `first_shown`, `last_shown` (RO) | start, stop | prima și ultima afișare | perioada |
| `afisari` | treaptă, până la ultima zi minus 90 | reach estimat în UE; impresiile doar la reclamele politice | interval de impresii | interval de impresii |
| `suprafata` | Search, YouTube, Maps, Play, Shopping | Facebook, Instagram, Messenger… | – | Bing |
| `doar_ro`, `tari` | `nr_tari` = 2 | defalcarea pe țări (UE) | – | ponderea pe țări |
| `tintire` | 5 criterii | vârstă, gen, locație (UE) | 12 categorii (UE) | vârstă, gen, locație, audiențe |
| `data_fotografiei` | ziua descărcării | la fel | la fel | la fel |

Cu `text` completat de Meta, LinkedIn și Microsoft, cardurile din galerie ar arăta conținutul real. `fisiere/galerie.py` și `galerie_sablon.html` s-ar adapta la modelul comun.

## 4. Categorizarea automată, pe text

Schema propusă pentru Google, cu sezonul, produsul, mesajul și limba, e în [05](05_URMEAZA.md), la pasul 4. Pe textul de la Meta, LinkedIn și Microsoft se poate aplica automat, cu un model AI, fără capturi. Asta rezolvă problema de la Google, unde filtrul de Crăciun după dată a arătat reclame Revolut fără legătură cu Crăciunul.

Trimiterea textelor către un AI extern intră în avizul juridic (vezi [04](04_LIMITE.md)).

## 5. Ce știm deja despre fiecare platformă, măsurat pe 25.09

| platformă | ce știm |
|---|---|
| **Microsoft** | API public, fără cont. Pe 25.09 s-au făcut ~20 de cereri de test, cu ecusonul proiectului: ING are 20 de reclame în RO, BT 0. `robots.txt` al `adlibrary.api.bingads.microsoft.com` a răspuns 403, iar dovada nu s-a salvat. **Termenii** („personal and non-commercial use”) sunt riscul cel mai mare: doar după aviz |
| **Meta** | cere verificarea identității unui angajat numit, iar datele lui personale ajung la Meta. Din rețeaua băncii, `facebook.com` a întors eroare de conexiune pe 25.09, deci e nevoie de o excepție de proxy de la IT. Dacă apar reclamele comerciale ale băncilor din RO, arată primul apel real |
| **LinkedIn** | acces pe bază de cerere, aprobată de LinkedIn. Clauza de eligibilitate „for the purposes of advertising” trebuie lămurită cu juristul înainte de cerere. Documentația a răspuns cu o blocare Cloudflare pe 25.09, pe care n-am ocolit-o |

## 6. Ce ar fi cel mai util de aflat

1. **Ce bănci apar pe fiecare platformă.** Pe Google sunt 14 din 30. Pentru BT, CEC și UniCredit, care ne blochează site-ul, reclamele sunt singura sursă automată, deci contează dacă apar și la Meta.
2. **ID-urile conturilor fiecărei bănci pe fiecare platformă,** într-o listă ca `google_advertiseri.csv`.
3. **Câteva texte de reclame pe bancă,** ca să vedem dacă merge categorizarea automată.
4. **Dacă Meta întoarce reclamele comerciale ale băncilor din România,** nu doar pe cele politice.

## 7. Cum am lucrat pe Google, pe scurt

- **Fotografie datată,** descărcată o dată și salvată local, într-un folder ignorat de git.
- **Scripturi care numără doar din fișier,** fără nicio conexiune la platformă.
- **Nimic în bază până la aviz.**
- **La orice cerere HTTP automată,** de exemplu spre API-ul Microsoft: fluxul proiectului, ecusonul din `crawler/__init__.py` și `robots.txt` respectat, cu dovada salvată pe disc.
- **Fără scraping pe site-urile bibliotecilor,** fără servicii terțe, fără ocolirea blocărilor.
- **Fișierele mari nu se atașează în conversațiile cu un asistent AI;** se lasă pe disc.
