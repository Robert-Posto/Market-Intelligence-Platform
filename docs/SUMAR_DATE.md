# MIP — sumarul datelor colectate

*Stare la 24.09.2026. Reper: „Arhitectura Market Intelligence Libra" (DRAFT, 09.09.2026), secțiunea 2.*

## Pe scurt

| | |
|---|---|
| Bănci urmărite | 30 |
| Bănci cu date | 23 |
| Bănci blocate (documentate, fără alt canal) | 5 — BT, CEC, Intesa, UniCredit, Revolut |
| Surse web descoperite / active | 5.840 / 2.152 |
| Valori colectate (prețuri, comisioane, dobânzi) | 27.218 |
| Valori „curate" (verificabile și comparabile) | 14.722 (54%) |
| Citate regăsite în sursă | HTML 100% · PDF 99% (eșantion) |
| Valori datate (dată de vigoare) | 69% |
| În coada de verificare umană | 5.395 |
| Schimbări de preț detectate (istoric) | 996 |

## Ce avem, pe secțiunile din PDF

| Secțiune | Colectat | Bănci |
|---|---|---|
| **2.1 Produse & prețuri** | 23.080 de comisioane (PDF-uri de tarife + pagini); 607 produse în catalog; 100 de valori la depozite | 19–23 |
| **2.2 Rate & indicatori** | 322 dobânzi nominale · 88 DAE · 58 marje peste IRCC; curs propriu la 13 bănci | 8–17 |
| **2.3 Aplicații mobile** | 19 aplicații iOS: versiune, rating, **distribuția pe stele** (17), 130 de capturi, 120 de recenzii | 19 |
| **2.5 Rețea** | 852 de sucursale · 54 de ATM-uri proprii · 572 de ATM-uri partenere (Patria/Euronet) | 19 |
| **2.7 Sentiment** | 120 de recenzii App Store, pseudonimizate, 41 cu răspunsul băncii | 16 |

## Ce nu am colectat încă

| Secțiune din PDF | Lipsește | Motiv / următorul pas |
|---|---|---|
| 2.1 | Comisioanele ING | robots.txt interzice PDF-urile ING |
| 2.1 | Toate datele BT, CEC, Intesa, UniCredit, Revolut | ne blochează (403); doar pe o cale aprobată |
| 2.1 | IMM & corporate (factoring, leasing, cash management) — acoperire slabă | de verificat pe bancă |
| 2.2 | Dobânzi din PDF-urile de dobânzi (BCR, BRD, tbi) | trec prin parserul de tarife; de rutat la cel de dobânzi |
| 2.2 | Curs de referință BNR | feed-ul `curs.bnr.ro` e interzis de robots.txt; de găsit pagina de pe `www.bnr.ro` |
| 2.2 | ROBOR / IRCC actuale | în bază sunt doar date vechi (4–17.09, fără IRCC); extracția de pe `www.bnr.ro` merge, neîncărcată |
| 2.2 | EURIBOR | neînceput |
| 2.3 | Android (Play Store, Exodus, APK) | neînceput |
| 2.3 | Walkthrough pe device, feature matrix, internet banking public | neînceput |
| 2.3 / 2.7 | Recenzii complete (sute pe aplicație) | pagina publică arată ~8; restul doar prin furnizor licențiat |
| **2.4 Campanii & marketing** | tot: landing pages, reclame (Meta/TikTok/YouTube), newsroom, LinkedIn | neînceput |
| 2.5 | Program sucursale; locatoarele băncilor (în afară de Patria) | API-ul hărții interzis de robots.txt (BRD, CreditCoop, Libra) sau fără coordonate |
| 2.5 | Job postings | neînceput |
| **2.6 Context de piață** | tot: statistici BNR, ARB, rapoarte financiare, ANPC/CSALB | neînceput |
| 2.7 | Trustpilot, Google Business | neînceput |
| 3. Competitori | Alpha Bank, OTP, First Bank (Nivel 1); tot Nivelul 2 (Wise, N26, bunq…) și Nivelul 3 | nu sunt în lista celor 30 de bănci |

## Calitate — de îmbunătățit

- Concept comparabil între bănci: 65% (cea mai mare pârghie pentru comparații)
- Pagini fără `<main>` (ex. ING): conținutul principal ales greșit → dobânzi pierdute
- BCR: 13.661 de valori — de verificat versiunile vechi din arhivă
