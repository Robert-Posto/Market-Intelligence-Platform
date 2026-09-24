# MIP — ce date colectăm

*Stare la 24.09.2026 · 30 de bănci urmărite, 23 cu date · categorii conform „Arhitectura Market Intelligence Libra" (secțiunea 2).*

## 1. Ce colectăm în prezent

| Categorie | Ce conține | Bănci | Volum |
|---|---|---|---|
| **Comisioane** (2.1) | Liste de tarife și comisioane (PDF + pagini web): cont curent, carduri, transferuri, retrageri, pachete | 19 | 23.080 de valori |
| **Catalog de produse** (2.1) | Numele produselor de pe paginile băncilor | 23 | 607 produse |
| **Depozite** (2.1) | Dobânzi la depozite, pe termene | 20 | 100 de valori |
| **Dobânzi la credite** (2.2) | Dobândă nominală, DAE, marjă peste IRCC | 17 | 468 de valori |
| **Curs valutar propriu** (2.2) | Cursul afișat de bancă | 13 | 30 de valori |
| **Indici de referință BNR** (2.2) | ROBOR și ROBID zilnic (7 scadențe), IRCC trimestrial — IRCC în vigoare: 5,56% | BNR | 150 de valori |
| **Aplicații mobile iOS** (2.3) | Versiune, rating, distribuția notelor pe stele, capturi din store | 19 | 19 aplicații |
| **Recenzii App Store** (2.7) | Recenzii afișate public, autor pseudonimizat, cu răspunsul băncii | 16 | 120 de recenzii |
| **Rețea** (2.5) | Sucursale și ATM-uri pe hartă | 19 | 852 sucursale · 54 ATM proprii · 572 ATM partenere |
| **Istoric de prețuri** | Schimbări de preț între versiunile documentelor | — | 996 de schimbări |

**Calitate:** 54% dintre valori sunt direct verificabile și comparabile între bănci; citatele se regăsesc în sursă (HTML 100%, PDF 99%); 69% au dată de vigoare. Valorile nesigure (20%) stau în coada de verificare umană.

## 2. Propuse / în așteptare

| Ce | Stare | Ce e nevoie |
|---|---|---|
| Curs de referință BNR | în așteptare | feed-ul oficial XML (curs.bnr.ro) interzice roboții prin robots.txt; de confirmat cu BNR / echipa dacă se poate folosi |
| Dobânzi din PDF-urile de dobânzi | **în lucru azi** | — |
| Mai multe dobânzi și prețuri de pe paginile ING și ale altor bănci | **în lucru azi** | — |
| Curățarea versiunilor vechi de documente (ex. BCR) | **în lucru azi** | — |
| Bănci blocate: BT, CEC, Intesa, UniCredit, Revolut | în așteptare | cale aprobată: cerere de acces / comparator public / aviz juridic |
| Comisioanele ING | în așteptare | ING interzice roboților PDF-urile; cerere de acces sau colectare manuală |
| Recenzii complete (sute pe aplicație) | propus | furnizor licențiat (ex. Sensor Tower, AppFollow) |
| Aplicații Android | propus | — |
| EURIBOR | propus | verificarea licenței EMMI |
| Campanii & marketing (2.4) | propus | Meta Ad Library / TikTok (verificare de identitate a firmei) |
| Context de piață (2.6): BNR, ARB, rapoarte financiare, ANPC | propus | — |
| Job postings (2.5) | propus | — |
| Trustpilot, Google Business (2.7) | propus | verificarea condițiilor de utilizare |
| Competitori Nivel 2–3 (Wise, N26, bunq, ING NL…) | propus | extinderea listei de bănci |
| Bază de date comună pentru echipă | în așteptare | server intern sau Postgres în cloud |
