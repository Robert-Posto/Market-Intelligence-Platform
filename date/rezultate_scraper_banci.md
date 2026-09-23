# Rezultate scraper — bănci din România (test spike, fără LLM)

Test personal, exploratoriu — NELEGAT de proiectul oficial "Market Intelligence Platform" (documentul intern DRAFT, nesemnat de Juridic + DPO). Scop: să vedem ce date publice sunt accesibile printr-un fetch simplu și respectuos (robots.txt respectat, User-Agent onest, un request pe secundă pe domeniu, fără evaziune la blocaje).

**Total bănci verificate:** 30 · OK: 21 · Blocate de robots.txt: 1 · Erori/blocaje: 8

---

## Banca Transilvania

- **URL:** https://www.bancatransilvania.ro/
- **Status:** ERROR
- **Motiv:** HTTP 403 (posibil bloc WAF/anti-bot)

## BCR

- **URL:** https://www.bcr.ro/
- **Status:** OK
- **Titlu pagină:** BCR Persoane fizice | Cont online, Carduri, Credite de nevoi si imobiliare, Economii si Investitii
- **Descriere meta:** Intra pe BCR si descopera servicii, conturi, operatiuni bancare avantajoase. Avem tot ce iti poate fi de folos: cont online, carduri de credit, credite de nevoi si imobiliare, economii si investitii. Alege BCR.
- **Linkuri relevante găsite** (produse/dobânzi/tarife etc.):
  - https://www.bcr.ro/ro/persoane-fizice#credit-george
  - https://www.bcr.ro/ro/persoane-fizice/economisire-si-investire/depozitul-la-termen
  - https://www.bcr.ro/ro/persoane-fizice/credite/credit-george
  - https://www.bcr.ro/ro/persoane-fizice/carduri-de-cumparaturi/cardul-de-credit-online
- **Fragment text homepage:** BCR Persoane fizice | Cont online, Carduri, Credite de nevoi si imobiliare, Economii si Investitii Omite Mergi la Produsele BCR Mergi la Contul George Mergi la Cum să-ți deschizi cont George Mergi la Creditul George Mergi la Curs valutar Mergi la Contact Mergi la Întrebări Frecvente Vreau cont George Planifică o vizită Feedback Caută unități , Deschide in tab nou Întreab-o pe Ada 1 / 3 Intră în prima Națională unde joacă toți românii Naționala de Edu Fin luptă pentru creșterea educației financia...
- **Pagini secundare urmărite:**
  - https://www.bcr.ro/ro/persoane-fizice#credit-george — titlu: BCR Persoane fizice | Cont online, Carduri, Credite de nevoi si imobiliare, Economii si Investitii
    - fragment: BCR Persoane fizice | Cont online, Carduri, Credite de nevoi si imobiliare, Economii si Investitii Omite Mergi la Produsele BCR Mergi la Contul George Mergi la Cum să-ți deschizi cont George Mergi la Creditul George Mergi la Curs valutar Mergi la Contact Mergi la Întrebări Frecvente Vreau cont George Planifică o vizită Feedback Caută unități , Deschide in tab nou Întreab-o pe Ada 1 / 3 Intră în prima Națională unde joacă toți românii Naționala de Edu Fin luptă pentru creșterea educației financia...
  - https://www.bcr.ro/ro/persoane-fizice/economisire-si-investire/depozitul-la-termen — titlu: Depozit la termen | Depozite bancare | BCR Persoane fizice
    - fragment: Depozit la termen | Depozite bancare | BCR Persoane fizice Omite Mergi la Ofertă promo depozit Mergi la Ce primesc? Mergi la De ce să îmi fac depozit? Mergi la Programul de beneficii Mergi la Avantajele depozitului la termen Mergi la Cât te costă? Mergi la Te-ar mai putea interesa și Vreau depozit la termen , Deschide in tab nou Vreau cont , Deschide in tab nou Planifică o vizită , Deschide in tab nou Întreab-o pe Ada Depozitul la Termen BCR Ai bonus de dobândă de până la 0.8%/an pentru depozite...

## CEC Bank

- **URL:** https://www.cec.ro/
- **Status:** ERROR
- **Motiv:** HTTP 403 (posibil bloc WAF/anti-bot)

## ING Bank (Sucursala București)

- **URL:** https://www.ing.ro/
- **Status:** OK
- **Titlu pagină:** Persoane fizice | ING Romania
- **Descriere meta:** Descopera toate produsele ING pentru persoane fizice sau juridice. Alege creditele bancare potrivite pentru nevoile tale.
- **Linkuri relevante găsite** (produse/dobânzi/tarife etc.):
  - https://ing.ro/persoane-fizice/carduri-si-conturi
  - https://ing.ro/persoane-fizice/carduri-si-conturi/pachete-conturi-curente
  - https://ing.ro/persoane-fizice/carduri-si-conturi/pachete-conturi-curente/go
  - https://ing.ro/persoane-fizice/carduri-si-conturi/pachete-conturi-curente/more
  - https://ing.ro/persoane-fizice/carduri-si-conturi/pachete-conturi-curente/extra
  - https://ing.ro/persoane-fizice/carduri-si-conturi/freeing-cont-fara-comision
  - https://ing.ro/persoane-fizice/carduri-si-conturi/young-cont-copii
  - https://ing.ro/persoane-fizice/carduri-si-conturi/ing-together
  - https://ing.ro/persoane-fizice/carduri-si-conturi/carduri-virtuale-ING
  - https://ing.ro/persoane-fizice/carduri-si-conturi/ing-elementar
- **Fragment text homepage:** Persoane fizice | ING Romania × ING Home’Bank Fă-ți un cont 100% online și primește cardul virtual pe loc. Descarcă Accesibilitate Mărește fontul Micșorează fontul Alb și negru Inversează culorile Contrast negativ Evidențiază legăturile Font normal Resetează Elimină meniu accesibilitate Dacă alegi să elimini meniul de accesibilitate, nu îl vei mai putea vizualiza, decât dacă ștergi istoricul de navigare și datele. Ești sigur că dorești să ascunzi interfața? Elimină meniul Starea serviciilor Pers...
- **Pagini secundare urmărite:**
  - https://ing.ro/persoane-fizice/carduri-si-conturi — titlu: Carduri si conturi curente ING - alege siguranta si simplitatea! ING Bank
    - fragment: Carduri si conturi curente ING - alege siguranta si simplitatea! ING Bank Accesibilitate Mărește fontul Micșorează fontul Alb și negru Inversează culorile Contrast negativ Evidențiază legăturile Font normal Resetează Elimină meniu accesibilitate Dacă alegi să elimini meniul de accesibilitate, nu îl vei mai putea vizualiza, decât dacă ștergi istoricul de navigare și datele. Ești sigur că dorești să ascunzi interfața? Elimină meniul Starea serviciilor Persoane fizice IMM Companii mari Devino clien...
  - https://ing.ro/persoane-fizice/carduri-si-conturi/pachete-conturi-curente — titlu: Pachete conturi curente ING – Beneficii care contează
    - fragment: Pachete conturi curente ING – Beneficii care contează Accesibilitate Mărește fontul Micșorează fontul Alb și negru Inversează culorile Contrast negativ Evidențiază legăturile Font normal Resetează Elimină meniu accesibilitate Dacă alegi să elimini meniul de accesibilitate, nu îl vei mai putea vizualiza, decât dacă ștergi istoricul de navigare și datele. Ești sigur că dorești să ascunzi interfața? Elimină meniul Starea serviciilor Persoane fizice IMM Companii mari Devino client ING în România Sus...

## BRD — Groupe Société Générale

- **URL:** https://www.brd.ro/
- **Status:** OK
- **Titlu pagină:** BRD România
- **Linkuri relevante găsite** (produse/dobânzi/tarife etc.):
  - https://www.brd.ro/persoane-fizice/carduri-si-conturi
  - https://www.brd.ro/persoane-fizice/carduri-si-conturi/operatiuni-curente/carduri-de-zi-cu-zi
  - https://www.brd.ro/persoane-fizice/carduri-si-conturi/operatiuni-curente/card-like
  - https://www.brd.ro/persoane-fizice/carduri-si-conturi/operatiuni-curente/card-like-kids
  - https://www.brd.ro/persoane-fizice/operatiuni-curente/cont-curent
  - https://www.brd.ro/persoane-fizice/carduri-si-conturi/operatiuni-curente/servicii-de-baza
  - https://www.brd.ro/persoane-fizice/credite/alte-credite-si-servicii/descoperit-autorizat-de-cont
  - https://www.brd.ro/card-de-credit
  - https://www.brd.ro/persoane-fizice/carduri-si-conturi/carduri/card-de-credit-gold
  - https://www.brd.ro/persoane-fizice/carduri-si-conturi/carduri/cardul-de-credit-platinum
- **Fragment text homepage:** BRD România Sari la conținutul principal Atentie la apelurile false! ANAF, banca sau alte autoritati nu solicita sa furnizezi date bancare sau coduri de access, si nici sa accesezi diverse linkuri, care pot duce la instalarea de aplicatii de control la distanta a calculatorului tau. Nu efectua „tranzactii bancare de test” si nu accepta astfel de cereri receptionate telefonic, poate fi o frauda! Contacteaza imediat consilierul bancar si raporteaza situatiile suspecte! × ro / en Persoane fizice Co...
- **Pagini secundare urmărite:**
  - https://www.brd.ro/persoane-fizice/carduri-si-conturi — titlu: BRD.ro | Carduri si Conturi Persoane Fizice
    - fragment: BRD.ro | Carduri si Conturi Persoane Fizice Sari la conținutul principal Atentie la apelurile false! ANAF, banca sau alte autoritati nu solicita sa furnizezi date bancare sau coduri de access, si nici sa accesezi diverse linkuri, care pot duce la instalarea de aplicatii de control la distanta a calculatorului tau. Nu efectua „tranzactii bancare de test” si nu accepta astfel de cereri receptionate telefonic, poate fi o frauda! Contacteaza imediat consilierul bancar si raporteaza situatiile suspec...
  - https://www.brd.ro/persoane-fizice/carduri-si-conturi/operatiuni-curente/carduri-de-zi-cu-zi — titlu: CARD DE ZI CU ZI | BRD.ro
    - fragment: CARD DE ZI CU ZI | BRD.ro Sari la conținutul principal Atentie la apelurile false! ANAF, banca sau alte autoritati nu solicita sa furnizezi date bancare sau coduri de access, si nici sa accesezi diverse linkuri, care pot duce la instalarea de aplicatii de control la distanta a calculatorului tau. Nu efectua „tranzactii bancare de test” si nu accepta astfel de cereri receptionate telefonic, poate fi o frauda! Contacteaza imediat consilierul bancar si raporteaza situatiile suspecte! × ro / en Pers...

## Raiffeisen Bank

- **URL:** https://www.raiffeisen.ro/
- **Status:** OK
- **Titlu pagină:** Raiffeisen Bank România | Conturi, carduri, credite și banking online
- **Descriere meta:** Descoperă produsele și serviciile Raiffeisen Bank pentru persoane fizice: conturi, carduri, credite, economii, aplicații digitale și soluții bancare de zi cu zi.
- **Linkuri relevante găsite** (produse/dobânzi/tarife etc.):
  - https://www.raiffeisen.ro/ro/persoane-fizice/produsele-noastre/carduri.html
  - https://www.raiffeisen.ro/ro/persoane-fizice/produsele-noastre/carduri/carduri-de-cumparaturi.html
  - https://www.raiffeisen.ro/ro/persoane-fizice/produsele-noastre/carduri/cardul-de-cumparaturi-standard.html
  - https://www.raiffeisen.ro/ro/persoane-fizice/produsele-noastre/carduri/cardul-de-cumparaturi-emag.html
  - https://www.raiffeisen.ro/ro/persoane-fizice/produsele-noastre/carduri/cardul-de-cumparaturi-platinum.html
  - https://www.raiffeisen.ro/ro/persoane-fizice/produsele-noastre/carduri/cardul-visa-credit-signature.html
  - https://www.raiffeisen.ro/ro/persoane-fizice/produsele-noastre/carduri/carduri-de-debit.html
  - https://www.raiffeisen.ro/ro/persoane-fizice/produsele-noastre/carduri/cardul-galben.html
  - https://www.raiffeisen.ro/ro/persoane-fizice/produsele-noastre/carduri/card-debit-visa-gold.html
  - https://banking.raiffeisen.ro/multishop-rate-fara-dobanda
- **Fragment text homepage:** Raiffeisen Bank România | Conturi, carduri, credite și banking online Skip to main content Personal Premium Private Business Corporații Despre noi Disponibilitatea serviciilor Campanii promoționale Cariere Rețea Contactează-ne Curs valutar Internet banking Raiffeisen Online Persoane Fizice Descarcă aplicația Smart Mobile Noul Raiffeisen Online IMM Raiffeisen Online Business Raiffeisen Online Corporate Banking 1:1 Devino client Despre bani 1:1 Nu ești client? Deschide cont online deschizi cont on...
- **Pagini secundare urmărite:**
  - https://www.raiffeisen.ro/ro/persoane-fizice/produsele-noastre/carduri.html — titlu: Carduri persoane fizice | Raiffeisen Bank
    - fragment: Carduri persoane fizice | Raiffeisen Bank Skip to main content Personal Premium Private Business Corporații Despre noi Disponibilitatea serviciilor Campanii promoționale Cariere Rețea Contactează-ne Curs valutar Internet banking Raiffeisen Online Persoane Fizice Descarcă aplicația Smart Mobile Noul Raiffeisen Online IMM Raiffeisen Online Business Raiffeisen Online Corporate Banking 1:1 Devino client Despre bani 1:1 Carduri Raiffeisen Cumpărături în siguranță online, retrageri cash de la ATM-uri ...
  - https://www.raiffeisen.ro/ro/persoane-fizice/produsele-noastre/carduri/carduri-de-cumparaturi.html — titlu: Card de credit| Carduri persoane fizice | Raiffeisen Bank
    - fragment: Card de credit| Carduri persoane fizice | Raiffeisen Bank Skip to main content Personal Premium Private Business Corporații Despre noi Disponibilitatea serviciilor Campanii promoționale Cariere Rețea Contactează-ne Curs valutar Internet banking Raiffeisen Online Persoane Fizice Descarcă aplicația Smart Mobile Noul Raiffeisen Online IMM Raiffeisen Online Business Raiffeisen Online Corporate Banking 1:1 Devino client Despre bani 1:1 Carduri de credit Raiffeisen Bank Ia-ți card din aplicația mobilă...

## UniCredit Bank

- **URL:** https://www.unicredit.ro/
- **Status:** ERROR
- **Motiv:** HTTP 403 (posibil bloc WAF/anti-bot)

## Intesa Sanpaolo Bank România

- **URL:** https://www.intesasanpaolobank.ro/
- **Status:** ERROR
- **Motiv:** HTTP 403 (posibil bloc WAF/anti-bot)

## Vista Bank (Romania)

- **URL:** https://www.vistabank.ro/
- **Status:** OK
- **Titlu pagină:** Vista Bank - Acasă
- **Descriere meta:** Împreună, suntem mai puternici
- **Linkuri relevante găsite** (produse/dobânzi/tarife etc.):
  - https://www.vistabank.ro/persoane-fizice/conturi-si-pachete-de-cont-curent
  - https://www.vistabank.ro/persoane-fizice/depozite
  - https://www.vistabank.ro/persoane-juridice
  - https://www.vistabank.ro/persoane-fizice/credite
  - https://www.vistabank.ro/persoane-fizice/credite?tab=green
  - https://www.vistabank.ro/persoane-juridice/credite
  - https://www.vistabank.ro/utile/garantare-depozite
  - https://www.vistabank.ro/public/docs/Prelucrare_date_Biroul_de_Credit.pdf
- **Fragment text homepage:** Vista Bank - Acasă Meniu Despre noi Persoane juridice AGRI Persoane fizice Trezorerie Utile VÂNZĂRI IMOBILE Clienți Eurobank Sucursale +4021.222.33.10 E-BANKING ADEVĂRUL ESTE CĂ IUBEȘTI GRECIA. CU VISTA TRAVEL ÎN EURO O VEI IUBI ȘI MAI MULT! Ai zero comisioane la pachetul de cont curent, și retrageri gratuite de numerar de la orice bancomat din statele Uniunii Europene! Perioada campaniei:                                                  15 iunie – 31 iulie 2026 #faster RoPay - Plăti instant cu ...
- **Pagini secundare urmărite:**
  - https://www.vistabank.ro/persoane-fizice/conturi-si-pachete-de-cont-curent — titlu: Vista Bank - Conturi şi pachete de cont curent
    - fragment: Vista Bank - Conturi şi pachete de cont curent Meniu Despre noi Persoane juridice AGRI Persoane fizice Trezorerie Utile VÂNZĂRI IMOBILE Clienți Eurobank Sucursale +4021.222.33.10 E-BANKING Persoane fizice Conturi şi pachete de cont curent Condiții generale de afaceri Tarife termeni și conditii Informare – Tarife termeni și conditii Simulator credite Protecția datelor cu caracter personal Colaborare Vista Bank – Evidența Populației Rețea sucursale Rețea bancomate Indici de referință Contact Vista...
  - https://www.vistabank.ro/persoane-fizice/depozite — titlu: Vista Bank - Depozite
    - fragment: Vista Bank - Depozite Meniu Despre noi Persoane juridice AGRI Persoane fizice Trezorerie Utile VÂNZĂRI IMOBILE Clienți Eurobank Sucursale +4021.222.33.10 E-BANKING Persoane fizice Depozite Depozite Credite MAI MULTE Carduri MAI MULTE Conturi şi pachete de cont curent MAI MULTE Depozite la Termen Depozitul la Termen Vista 12+1 Depozitul VISTA KIDS Contul de Economii Vista Smart Avantaje Beneficii Avantaje Beneficii Avantaje Beneficii Avantaje Beneficii Avantaje Beneficii Avantaje Beneficii Cu Dep...

## Patria Bank

- **URL:** https://www.patriabank.ro/
- **Status:** OK
- **Titlu pagină:** Card și cont bancar, credite și depozite persoane fizice
- **Descriere meta:** Patria Bank - carduri și conturi bancare pentru persoane fizice, credite și depozite la termen cu dobânzi avantajoase, banking online.
- **Linkuri relevante găsite** (produse/dobânzi/tarife etc.):
  - https://www.patriabank.ro/imm_corporate
  - https://www.patriabank.ro/depozitonline
  - https://www.patriabank.ro/creditonline
  - https://www.patriabank.ro/card-credit-online
  - https://www.patriabank.ro/persoane-fizice/credite
  - https://www.patriabank.ro/persoane-fizice/credite/credit-de-nevoi-personale-patria-plus
  - https://www.patriabank.ro/persoane-fizice/credite/creditul-de-nevoi-personale-cu-ipoteca
  - https://www.patriabank.ro/persoane-fizice/credite/creditul-ipotecar-patria-acasa
  - https://www.patriabank.ro/persoane-fizice/credite/credit-refinantare
  - https://www.patriabank.ro/persoane-fizice/credite/credit-de-consum-econom
- **Fragment text homepage:** Card și cont bancar, credite și depozite persoane fizice Persoane fizice Afaceri mici Agro IMM & CORPORATE Investitori Info Utile Despre Patria Blog ro en Persoane fizice Internet Banking Depozit online Credit online Card credit online Internet Banking Contact Agenții Patria Curs valutar Credite Credit de nevoi personale Credit de nevoi personale cu ipotecă Credit ipotecar Credit refinanțare Credit Econom Credit Overdraft - Descoperire de Cont Asigurări - Bancassurance Carduri și conturi Card de...
- **Pagini secundare urmărite:**
  - https://www.patriabank.ro/imm_corporate — titlu: Finanțare IMM, credite avantajoase. Patria Bank
    - fragment: Finanțare IMM, credite avantajoase. Patria Bank ││                                                                                                                     │ Persoane fizice Afaceri mici Agro IMM & CORPORATE Investitori Info Utile Despre Patria Blog ro en IMM & CORPORATE Internet Banking Depozit online Credit online Card credit online Internet Banking Contact Agenții Patria Curs valutar Operațiuni curente Cont curent Card Business 3D Secure Metode de autorizare a plăților online Servi...
  - https://www.patriabank.ro/depozitonline — titlu: Depozite 100% online, Patria de Oriunde
    - fragment: Depozite 100% online, Patria de Oriunde ││                                                                                                                     │ Persoane fizice Afaceri mici Agro IMM & CORPORATE Investitori Info Utile Despre Patria Blog ro en Deschide un depozit 100% online Internet Banking Depozit online Credit online Card credit online Internet Banking Contact Agenții Patria Curs valutar Info Utile Despre Patria Blog Produse bancare online pentru persoane fizice care nu dețin c...

## Exim Banca Românească

- **URL:** https://www.eximbank.ro/
- **Status:** OK
- **Titlu pagină:** Exim Banca Românească - Exim - Banca Romaneasca
- **Linkuri relevante găsite** (produse/dobânzi/tarife etc.):
  - https://www.eximbank.ro/#
  - https://www.eximbank.ro/2022/12/05/credit-capital-de-lucru/
  - https://www.eximbank.ro/2022/12/05/credit-pentru-investitii/
  - https://www.eximbank.ro/2022/12/05/credite-pentru-afaceri-din-domeniul-medical/
  - https://eximbank.ro/2025/09/22/credite-cu-garantii-fei/?pfa-microintreprinderi
  - https://www.eximbank.ro/2022/12/04/depozite/
  - https://www.eximbank.ro/2022/12/05/business-card/?pfa-microintreprinderi
  - https://www.eximbank.ro/2024/11/01/card-business-premium/
  - https://www.eximbank.ro/2022/12/05/credite/
  - https://www.eximbank.ro/2025/09/22/credite-cu-garantii-fei/
- **Fragment text homepage:** Exim Banca Românească - Exim - Banca Romaneasca Prima Pagina Despre noi Retea Documente utile Cariere Noutati Contact Formular de contact Persoane Juridice Despre Noi Prima Pagina Despre noi Retea Noutati Documente utile Cariere Contact Persoane Juridice Persoane fizice Fonduri de stat PFA  si Microintreprinderi PACHET START-UP Pachete servicii Credite Overdraft Credit capital de lucru la termen Credit pentru investitii Credite pentru afaceri din domeniul medical Scrisori de garantie bancara Cre...
- **Pagini secundare urmărite:**
  - https://www.eximbank.ro/# — titlu: Exim Banca Românească - Exim - Banca Romaneasca
    - fragment: Exim Banca Românească - Exim - Banca Romaneasca Prima Pagina Despre noi Retea Documente utile Cariere Noutati Contact Formular de contact Persoane Juridice Despre Noi Prima Pagina Despre noi Retea Noutati Documente utile Cariere Contact Persoane Juridice Persoane fizice Fonduri de stat PFA  si Microintreprinderi PACHET START-UP Pachete servicii Credite Overdraft Credit capital de lucru la termen Credit pentru investitii Credite pentru afaceri din domeniul medical Scrisori de garantie bancara Cre...
  - https://www.eximbank.ro/2022/12/05/credit-capital-de-lucru/ — titlu: Credit capital de lucru la termen - Exim - Banca Romaneasca
    - fragment: Credit capital de lucru la termen - Exim - Banca Romaneasca Convertor IBAN Internet Banking Prima Pagina Despre noi Retea Documente utile Cariere Noutati Contact Internet Banking Convertor IBAN Formular de contact Persoane Juridice Despre Noi Prima Pagina Despre noi Retea Noutati Documente utile Cariere Contact Persoane Juridice Persoane fizice Fonduri de stat PFA  si Microintreprinderi PACHET START-UP Pachete servicii Credite Overdraft Credit capital de lucru la termen Credit pentru investitii ...

## Libra Internet Bank

- **URL:** https://www.librabank.ro/
- **Status:** OK
- **Notă inițială:** angajator, nu competitor
- **Titlu pagină:** Libra Internet Bank | Cont online, card online, credite, mobile banking
- **Descriere meta:** Produse Libra Internet Bank: ⭐Cont online personal ⭐Cont online business ⭐Depozite la termen ⭐Credit ipotecar ⭐Card de debit online ⭐Card de credit online ⭐Credite imm/profesii/corporate ⭐Credite agricultura ⭐Mobile banking
- **Linkuri relevante găsite** (produse/dobânzi/tarife etc.):
  - https://www.librabank.ro/cont-curent-persoane-fizice
  - https://www.librabank.ro/cont-curent-notarial
  - https://www.librabank.ro/cont-curent-imm
  - https://www.librabank.ro/card-bancar
  - https://www.librabank.ro/card-persoane-fizice
  - https://www.librabank.ro/card-de-debit
  - https://www.librabank.ro/card-de-credit-cumparaturi
  - https://www.librabank.ro/card-junior-copii
  - https://www.librabank.ro/card-persoane-juridice
  - https://www.librabank.ro/card-credit-profesii
- **Fragment text homepage:** Libra Internet Bank | Cont online, card online, credite, mobile banking EN Conturi Conturi persoane fizice Cont online personal Cont online 2 în 1 Pachete de Beneficii Libra Conturi persoane juridice Cont online business Cont online 2 în 1 Cont profesii liberale Cont Special Notarial Companii până la 5M lei Companii peste 5M lei Convenții salariale Carduri Persoane fizice Card de debit Card de credit Card junior Persoane juridice Card de credit profesii Card de credit companii Card de debit busi...
- **Pagini secundare urmărite:**
  - https://www.librabank.ro/cont-curent-persoane-fizice — titlu: Deschide-ti cont curent persoane fizice online | Libra Bank
    - fragment: Deschide-ti cont curent persoane fizice online | Libra Bank EN Conturi Conturi persoane fizice Cont online personal Cont online 2 în 1 Pachete de Beneficii Libra Conturi persoane juridice Cont online business Cont online 2 în 1 Cont profesii liberale Cont Special Notarial Companii până la 5M lei Companii peste 5M lei Convenții salariale Carduri Persoane fizice Card de debit Card de credit Card junior Persoane juridice Card de credit profesii Card de credit companii Card de debit business Economi...
  - https://www.librabank.ro/cont-curent-notarial — titlu: Cont Curent Special Notarial ✔️ Administrare de cont gratuita
    - fragment: Cont Curent Special Notarial ✔️ Administrare de cont gratuita EN Conturi Conturi persoane fizice Cont online personal Cont online 2 în 1 Pachete de Beneficii Libra Conturi persoane juridice Cont online business Cont online 2 în 1 Cont profesii liberale Cont Special Notarial Companii până la 5M lei Companii peste 5M lei Convenții salariale Carduri Persoane fizice Card de debit Card de credit Card junior Persoane juridice Card de credit profesii Card de credit companii Card de debit business Econo...

## ProCredit Bank

- **URL:** https://www.procreditbank.ro/
- **Status:** OK
- **Titlu pagină:** ProCredit Bank - Persoane fizice: Credite, Carduri, Conturi
- **Descriere meta:** Vezi toate serviciile si produsele ProCredit Bank pentru persoane fizice: credite ✓ pachete de cont curent ✓ carduri ✓ depozite la termen ✓.
- **Linkuri relevante găsite** (produse/dobânzi/tarife etc.):
  - https://www.procreditbank.ro/
  - https://www.procreditbank.ro/companii/
  - https://www.procreditbank.ro/agricultura/
  - https://www.procreditbank.ro/dezvoltare-durabila/
  - https://www.procreditbank.ro/despre-noi/
  - https://www.procreditbank.ro/cariere/
  - https://www.procreditbank.ro/companii/calculator-emisii-co2-pentru-companii/
  - https://www.procreditbank.ro/stiri/
  - https://www.procreditbank.ro/lista-cursurilor-de-schimb/
  - https://www.procreditbank.ro/locatii/
- **Fragment text homepage:** ProCredit Bank - Persoane fizice: Credite, Carduri, Conturi Sari la conținut Persoane fizice Companii Agricultură Dezvoltare durabilă Despre noi Cariere Calculator CO₂ Știri Curs Valutar Locații Contact Internet Banking Persoane fizice Conturi Pachete de cont curent Pachetul Cont de plăți cu servicii de bază Carduri Visa FlexFund Overdraft Economisire FlexSave – cont de economii Depozite la termen Credite FlexFund Overdraft Credit de nevoi personale Credit imobiliar-ipotecar Credit pentru invest...
- **Pagini secundare urmărite:**
  - https://www.procreditbank.ro/ — titlu: ProCredit Bank - Persoane fizice: Credite, Carduri, Conturi
    - fragment: ProCredit Bank - Persoane fizice: Credite, Carduri, Conturi Sari la conținut Persoane fizice Companii Agricultură Dezvoltare durabilă Despre noi Cariere Calculator CO₂ Știri Curs Valutar Locații Contact Internet Banking Persoane fizice Conturi Pachete de cont curent Pachetul Cont de plăți cu servicii de bază Carduri Visa FlexFund Overdraft Economisire FlexSave – cont de economii Depozite la termen Credite FlexFund Overdraft Credit de nevoi personale Credit imobiliar-ipotecar Credit pentru invest...
  - https://www.procreditbank.ro/companii/ — titlu: Servicii și produse bancare pentru Companii - ProCredit Bank
    - fragment: Servicii și produse bancare pentru Companii - ProCredit Bank Sari la conținut Persoane fizice Companii Agricultură Dezvoltare durabilă Despre noi Cariere Calculator CO₂ Știri Curs Valutar Locații Contact Business Portal Internet Banking Persoane fizice Conturi Pachete de cont curent Pachetul Cont de plăți cu servicii de bază Carduri Visa FlexFund Overdraft Economisire FlexSave – cont de economii Depozite la termen Credite FlexFund Overdraft Credit de nevoi personale Credit imobiliar-ipotecar Cre...

## Revolut Bank UAB — Sucursala București

- **URL:** https://www.revolut.com/en-RO/
- **Status:** ERROR
- **Motiv:** HTTP 403 (posibil bloc WAF/anti-bot)

## tbi bank EAD Sofia — Sucursala București

- **URL:** https://tbibank.ro/
- **Status:** OK
- **Titlu pagină:** tbi bank | Servicii Bancare Persoane Fizice & Companii - tbi bank
- **Descriere meta:** tbi bank vine in intampinarea clientilor cu o alternativa diferita la abordarea traditionala a serviciilor bancare.
- **Linkuri relevante găsite** (produse/dobânzi/tarife etc.):
  - https://tbibank.ro/#economii
  - https://tbibank.ro/product/depozitul-online/
  - https://tbibank.ro/product/depozitul-simplu/
  - https://tbibank.ro/product/contul-de-economii
  - https://tbibank.ro/#credite-nevoi-personale
  - https://tbibank.ro/product/creditul-tau-personal/
  - https://tbibank.ro/product/creditul-cash-zero/
  - https://tbibank.ro/product/credit-pentru-planuri-mari/
  - https://tbibank.ro/product/refinanteaza-cu-creditul-personal/
  - https://tbibank.ro/product/creditul-tbi-duo/
- **Fragment text homepage:** tbi bank | Servicii Bancare Persoane Fizice & Companii - tbi bank Skip to content Personal​ Business Despre tbi bank​ Aplicatia tbi Economii Depozitul Online Depozitul Simplu Contul de Economii Credite nevoi personale Creditul personal Creditul Cash Zero Credit pentru planuri mari Credit refinantare externa Creditul tbi duo Cumpara acum, plateste mai tarziu Cumpara online si castiga 4 rate, 0% dobanda Cumparaturi bunuri online Cumparaturi bunuri din magazine Servicii medicale in rate Finantare a...
- **Pagini secundare urmărite:**
  - https://tbibank.ro/#economii — titlu: tbi bank | Servicii Bancare Persoane Fizice & Companii - tbi bank
    - fragment: tbi bank | Servicii Bancare Persoane Fizice & Companii - tbi bank Skip to content Personal​ Business Despre tbi bank​ Aplicatia tbi Economii Depozitul Online Depozitul Simplu Contul de Economii Credite nevoi personale Creditul personal Creditul Cash Zero Credit pentru planuri mari Credit refinantare externa Creditul tbi duo Cumpara acum, plateste mai tarziu Cumpara online si castiga 4 rate, 0% dobanda Cumparaturi bunuri online Cumparaturi bunuri din magazine Servicii medicale in rate Finantare a...
  - https://tbibank.ro/product/depozitul-online/ — titlu: Depozite Online | Aplica acum | tbi bank
    - fragment: Depozite Online | Aplica acum | tbi bank Skip to content Personal​ Business Despre tbi bank​ Aplicatia tbi Economii Depozitul Online Depozitul Simplu Contul de Economii Credite nevoi personale Creditul personal Creditul Cash Zero Credit pentru planuri mari Credit refinantare externa Creditul tbi duo Cumpara acum, plateste mai tarziu Cumpara online si castiga 4 rate, 0% dobanda Cumparaturi bunuri online Cumparaturi bunuri din magazine Servicii medicale in rate Finantare auto Verde la energie Mai ...

## Garanti BBVA România

- **URL:** https://www.garantibbva.ro/
- **Status:** OK
- **Titlu pagină:** Produse si servicii bancare pentru persoane fizice | Garanti BBVA
- **Descriere meta:** DescoperÄ ofertele avantajoase de credite de nevoi personale, auto Èi ipotecare de la Garanti BBVA, precum Èi conturile de depozit la termen. Aplica rapid Èi uÈor!
- **Linkuri relevante găsite** (produse/dobânzi/tarife etc.):
  - https://www.garantibbva.ro/corporate/
  - https://www.garantibbva.ro/persoane-fizice/bonus-card/info-bonus-card/
  - https://www.garantibbva.ro/persoane-fizice/bonus-card/info-bonus-card
  - https://www.garantibbva.ro/persoane-fizice/bonus-card-2
  - https://www.garantibbva.ro/persoane-fizice/bonus-card/
  - https://www.garantibbva.ro/persoane-fizice/bonus-card/bonus-card-classic/
  - https://www.garantibbva.ro/persoane-fizice/bonus-card/bonus-card-gold/
  - https://www.garantibbva.ro/persoane-fizice/bonus-card/bonus-card-platinum/
  - https://www.garantibbva.ro/persoane-fizice/bonus-card/wwf-bonus-card/
  - https://www.garantibbva.ro/persoane-fizice/bonus-card/wwf-bonus-card
- **Fragment text homepage:** Produse si servicii bancare pentru persoane fizice | Garanti BBVA Â  Â  Â  Â Sari la conÈinut EN AgenÈii Èi ATM-uri EN AgenÈii Èi ATM-uri EN Persoane fizice IMM ÈI PFA CORPORATE Persoane fizice IMM ÈI PFA CORPORATE CautÄ Devino client Garanti BBVA Online Bonus Card Vezi toate Lumea Bonus Card IntrÄ Ã®n Lumea Bonus Card Èi descoperÄ toate avantaje Bonus Card Classic BucurÄ-te de o lume pe plus Åi fii pregÄtit pentru shopping! Bonus Card Gold ÃndeplineÅte-Å£i dorinÅ£Ä dupÄ dorinÅ...
- **Pagini secundare urmărite:**
  - https://www.garantibbva.ro/corporate/ — titlu: Corporate banking | Garanti BBVA
    - fragment: Corporate banking | Garanti BBVA Â  Â  Â  Â Sari la conÈinut AgenÈii Èi ATM-uri EN EN AgenÈii Èi ATM-uri EN CORPORATE PERSOANE FIZICE IMM ÈI PFA CORPORATE PERSOANE FIZICE IMM ÈI PFA CautÄ Devino client Garanti BBVA Online Propunerea de valoare SoluÈii de finanÈare FinanÈarea activitÄÈii curente Solutii de finanÅ£are Åi garantare FinanÈarea investiÈiilor AsigurÄ finanÅ£area pentru investiÅ£ii ScontÄri de creanÈe comerciale O soluÈie de finanÅ£are structuratÄ Scrisori de garan...
  - https://www.garantibbva.ro/persoane-fizice/bonus-card/info-bonus-card/ — titlu: IntrÄ Ã®n lumea Bonus Card | Garanti BBVA
    - fragment: IntrÄ Ã®n lumea Bonus Card | Garanti BBVA Â  Â  Â  Â Sari la conÈinut EN AgenÈii Èi ATM-uri EN AgenÈii Èi ATM-uri EN Persoane fizice IMM ÈI PFA CORPORATE Persoane fizice IMM ÈI PFA CORPORATE CautÄ Devino client Garanti BBVA Online Bonus Card Vezi toate Lumea Bonus Card IntrÄ Ã®n Lumea Bonus Card Èi descoperÄ toate avantaje Bonus Card Classic BucurÄ-te de o lume pe plus Åi fii pregÄtit pentru shopping! Bonus Card Gold ÃndeplineÅte-Å£i dorinÅ£Ä dupÄ dorinÅ£Ä cu Bonus Card Gold ...

## Salt Bank

- **URL:** https://www.saltbank.ro/
- **Status:** ERROR
- **Motiv:** ConnectionError: HTTPSConnectionPool(host='www.saltbank.ro', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='www.saltbank.ro', port=443): Failed to resolve 'www.saltbank.ro' ([Errno 11001] getaddrinfo failed)"))

## Citibank Europe plc — Sucursala România

- **URL:** https://www.citibank.com/icg/sa/emea/romania/english/about-us.html
- **Status:** OK
- **Titlu pagină:** Citi | Romania
- **Descriere meta:** With the most diverse array of products and the broadest global reach of any financial firm in the world, there is no bank better equipped to meet your corporation's evolving global needs.
- **Linkuri relevante găsite:** niciunul (pe baza cuvintelor-cheie folosite)
- **Fragment text homepage:** Citi | Romania Romana | English About Us Citi in Romania Citi is one of the worldâs leading largest financial institutions, with a heritage of over 200 years, serving more than 200 million clients in 160 countries. Our history can be traced back as far as 1812, when the financial institution was first established as the bank for New Yorkers, when we took the name âCity Bank of New Yorkâ. We were later renamed the First National City Bank of New York as we expanded and allowed more people t...

## BNP Paribas S.A. Paris — Sucursala București

- **URL:** https://romania.bnpparibas.com/
- **Status:** OK
- **Titlu pagină:** BNP Paribas in Romania: a European bank of reference in Romania
- **Descriere meta:** With nearly 1,000 employees, BNP Paribas in Romania is a leading European bank in Romania for corporates and institutions.
- **Linkuri relevante găsite** (produse/dobânzi/tarife etc.):
  - https://www.romania.bnpparibas.com/en/corporates-institutions/
- **Fragment text homepage:** BNP Paribas in Romania: a European bank of reference in Romania Direct access to content Direct access to Search Direct access to Main Menu Direct access to Online Banking Menu Twitter Linkedin Youtube Instagram BNP Paribas Group BNP Paribas in the world Online Banking Global Markets The single point of entry to BNP Paribas Fixed Income's global web services New window Connexis Trade Finance & Cash Management Access your world accounts in real time for cash operations and file transfers New wind...
- **Pagini secundare urmărite:**
  - https://www.romania.bnpparibas.com/en/corporates-institutions/ — titlu: Corporates and institutions : BNP Paribas in Romania supports you
    - fragment: Corporates and institutions : BNP Paribas in Romania supports you Direct access to content Direct access to Search Direct access to Main Menu Direct access to Online Banking Menu Twitter Linkedin Youtube Instagram BNP Paribas Group BNP Paribas in the world Online Banking Global Markets The single point of entry to BNP Paribas Fixed Income's global web services New window Connexis Trade Finance & Cash Management Access your world accounts in real time for cash operations and file transfers New wi...

## Banca Centrală Cooperatistă CREDITCOOP

- **URL:** https://www.creditcoop.ro/
- **Status:** OK
- **Titlu pagină:** CREDITCOOP – Banca Centrala Cooperatistă
- **Descriere meta:** Rețeaua cooperatistă CREDITCOOP, una dintre cele mai vechi și respectate instituții financiare cooperatiste din România, ce își are rădăcinile înca din anul 1851 și este alături de oameni de peste 170 de ani.
- **Linkuri relevante găsite** (produse/dobânzi/tarife etc.):
  - https://www.creditcoop.ro
  - https://www.creditcoop.ro/harta-agentiilor-creditcoop/
  - https://www.creditcoop.ro/lista-agentiilor-creditcoop/
  - https://www.creditcoop.ro/harta-bancilor-cooperatiste-afiliate/
  - https://www.creditcoop.ro/lista-bancilor-cooperatiste-afiliate/
  - https://www.fgdb.ro/
  - https://www.fngcimm.ro/
  - http://www.fgcr.ro/
  - http://www.birouldecredit.ro/
  - http://www.bnro.ro/Centrala-Riscului-de-Credit-(CRC)--2107.aspx
- **Fragment text homepage:** CREDITCOOP – Banca Centrala Cooperatistă Sari la conținut Agenții Close Agenții Open Agenții Harta agențiilor CREDITCOOP Lista Agențiilor CREDITCOOP Bănci afiliate Close Bănci afiliate Open Bănci afiliate Harta Băncilor Cooperatiste afiliate Lista Băncilor Cooperatiste afiliate Parteneri Close Parteneri Open Parteneri Membru în Asociaţia Română a Băncilor European Association of Co-operative Banks Colaboratori Fondul de garantare a depozitelor bancare Agenţia de Plăţi şi Intervenţie pentru Agric...
- **Pagini secundare urmărite:**
  - https://www.creditcoop.ro — titlu: CREDITCOOP – Banca Centrala Cooperatistă
    - fragment: CREDITCOOP – Banca Centrala Cooperatistă Sari la conținut Agenții Close Agenții Open Agenții Harta agențiilor CREDITCOOP Lista Agențiilor CREDITCOOP Bănci afiliate Close Bănci afiliate Open Bănci afiliate Harta Băncilor Cooperatiste afiliate Lista Băncilor Cooperatiste afiliate Parteneri Close Parteneri Open Parteneri Membru în Asociaţia Română a Băncilor European Association of Co-operative Banks Colaboratori Fondul de garantare a depozitelor bancare Agenţia de Plăţi şi Intervenţie pentru Agric...
  - https://www.creditcoop.ro/harta-agentiilor-creditcoop/ — titlu: Harta agențiilor CREDITCOOP – CREDITCOOP
    - fragment: Harta agențiilor CREDITCOOP – CREDITCOOP Sari la conținut Agenții Close Agenții Open Agenții Harta agențiilor CREDITCOOP Lista Agențiilor CREDITCOOP Bănci afiliate Close Bănci afiliate Open Bănci afiliate Harta Băncilor Cooperatiste afiliate Lista Băncilor Cooperatiste afiliate Parteneri Close Parteneri Open Parteneri Membru în Asociaţia Română a Băncilor European Association of Co-operative Banks Colaboratori Fondul de garantare a depozitelor bancare Agenţia de Plăţi şi Intervenţie pentru Agric...

## Banca de Investiții și Dezvoltare (BID)

- **URL:** https://www.bidromania.eu/
- **Status:** OK
- **Titlu pagină:** Acasă | Banca de Investiții și Dezvoltare
- **Linkuri relevante găsite** (produse/dobânzi/tarife etc.):
  - https://www.bidromania.eu/#
  - https://www.bidromania.eu/produse/credite/creditare-directa
  - https://www.bidromania.eu/produse/credite/fondul-de-participare-regional
  - https://www.bidromania.eu/produse/credite/fondul-de-participare-tranzitie-justa
  - https://www.bidromania.eu/beneficiari/sprijin-pentru-mediul-public/creditare-directa
  - https://www.bidromania.eu/sites/default/files/2026-01/_Strategia%20de%20investitii%20si%20creditare_22.01.2026.pdf
- **Fragment text homepage:** Acasă | Banca de Investiții și Dezvoltare Sorry, you need to enable JavaScript to visit this website. Sari la conținutul principal Cariere Contact RO / EN Acasă Cine suntem Despre noi Legislație Guvernanță Conducere Produse Garanții Diaspora Investește Acasă Garanții de portofoliu pentru IMM Garanții individuale pentru mediul public Credite Creditare directă Fondul de Participare Regional Fondul de Participare Tranziție Justă Intermediari financiari Garanții de portofoliu pentru IMM Garanții ind...
- **Pagini secundare urmărite:**
  - https://www.bidromania.eu/# — titlu: Acasă | Banca de Investiții și Dezvoltare
    - fragment: Acasă | Banca de Investiții și Dezvoltare Sorry, you need to enable JavaScript to visit this website. Sari la conținutul principal Cariere Contact RO / EN Acasă Cine suntem Despre noi Legislație Guvernanță Conducere Produse Garanții Diaspora Investește Acasă Garanții de portofoliu pentru IMM Garanții individuale pentru mediul public Credite Creditare directă Fondul de Participare Regional Fondul de Participare Tranziție Justă Intermediari financiari Garanții de portofoliu pentru IMM Garanții ind...
  - https://www.bidromania.eu/produse/credite/creditare-directa — titlu: Creditare directă | Banca de Investiții și Dezvoltare
    - fragment: Creditare directă | Banca de Investiții și Dezvoltare Sorry, you need to enable JavaScript to visit this website. Sari la conținutul principal Cariere Contact RO / EN Acasă Cine suntem Despre noi Legislație Guvernanță Conducere Produse Garanții Diaspora Investește Acasă Garanții de portofoliu pentru IMM Garanții individuale pentru mediul public Credite Creditare directă Fondul de Participare Regional Fondul de Participare Tranziție Justă Intermediari financiari Garanții de portofoliu pentru IMM ...

## Bank of China (CEE) Ltd — Sucursala București

- **URL:** https://www.bankofchina.com/ro/en/
- **Status:** OK
- **Titlu pagină:** Bank of China (Central and Eastern Europe) Limited Bucharest Branch
- **Linkuri relevante găsite** (produse/dobânzi/tarife etc.):
  - https://www.bankofchina.com/ro/en/cbservice/
  - https://www.bankofchina.com/ro/en/cbservice/cb2/
  - https://www.bankofchina.com/ro/en/custserv/cs2/
  - https://www.bankofchina.com/ro/en/aboutus/ab2/
  - https://www.bankofchina.com/ro/en/cbservice/RMBSrv/202104/t20210430_19360664.html
  - https://www.bankofchina.com/ro/en/custserv/cs2/202104/t20210430_19360662.html
  - https://www.bankofchina.com/ro/en/bocinfo/bi4/
  - https://www.bankofchina.com/ro/en/bocinfo/bi2/202109/t20210908_20014518.html
- **Fragment text homepage:** Bank of China (Central and Eastern Europe) Limited Bucharest Branch ç½é©¬å°¼äº Romania ç®ä½ä¸­æ English | Global Site Hotline : +40318029888 Home CorporateÂ Banking e-Banking AboutÂ Us RMB Service Deposits CorporateÂ Loans Trade Services Treasury & Foreign Exchange Other Services Corporate OnlineÂ Banking BOC News Outline Financial Report Regulations Corporate Social Responsibility Join Us Notices BOC News SecurityÂ TipsÂ onÂ PreventingÂ theÂ RiskÂ ofÂ OnlineÂ Fraud Beware of fake online i...
- **Pagini secundare urmărite:**
  - https://www.bankofchina.com/ro/en/cbservice/ — titlu: Bank of China@Romania_BOC Romania_CorporateÂ Banking
    - fragment: Bank of China@Romania_BOC Romania_CorporateÂ Banking ç½é©¬å°¼äº Romania ç®ä½ä¸­æ English | Global Site Hotline : +40318029888 Home CorporateÂ Banking e-Banking AboutÂ Us RMB Service Deposits CorporateÂ Loans Trade Services Treasury & Foreign Exchange Other Services Corporate OnlineÂ Banking BOC News Outline Financial Report Regulations Corporate Social Responsibility Join Us Current Position : Home > BOC Romania > CorporateÂ Banking RMB Service Corporate RMB Settlement Products Trade Finan...
  - https://www.bankofchina.com/ro/en/cbservice/cb2/ — titlu: Bank of China@Romania_BOC Romania_CorporateÂ Banking_CorporateÂ Loans
    - fragment: < Bank of China@Romania_BOC Romania_CorporateÂ Banking_CorporateÂ Loans ç½é©¬å°¼äº Romania ç®ä½ä¸­æ English | Global Site Hotline : +40318029888 Home CorporateÂ Banking e-Banking AboutÂ Us RMB Service Deposits CorporateÂ Loans Trade Services Treasury & Foreign Exchange Other Services Corporate OnlineÂ Banking BOC News Outline Financial Report Regulations Corporate Social Responsibility Join Us Current Position : Home > BOC Romania > CorporateÂ Banking > CorporateÂ Loans CorporateÂ Loans On...

## Credex Bank

- **URL:** https://credex.ro/
- **Status:** OK
- **Titlu pagină:** Credit online | Credex
- **Descriere meta:** Credit online | Aplica pentru un credit rapid online si obtine aprobarea in doar cateva minute! Fara garantii, fara acte suplimentare, bani direct in cont! | Credex
- **Linkuri relevante găsite** (produse/dobânzi/tarife etc.):
  - https://credex.ro/credit-de-nevoi-personale/
  - https://credex.ro/totul-despre-credite/card-de-credit-credex/
  - https://credex.ro/credit-1000-lei/
  - https://credex.ro/credit-2000-lei/
  - https://credex.ro/credit-3000-lei/
  - https://credex.ro/credit-4000-lei/
  - https://credex.ro/credit-5000-lei/
  - https://credex.ro/credit-doar-cu-buletinul/
  - https://credex.ro/credit-ifn/
  - https://credex.ro/credit-pe-termen-scurt/
- **Fragment text homepage:** Credit online | Credex Sari la conținut Meniu Meniu Credit de nevoi personale Card de credit Oferte Despre Noi Contact Plateste rata Credit online Imprumuturi rapide, fara drumuri la banca Credite online super avantajoase. Aplica pentru un credit online. Simplu, sigur si rapid. Suma * This field is hidden when viewing the form Perioada * Suma de care ai nevoie * Pentru ce perioada * Rata lunara Aplica online Suma solicitata Dobanda 18% Rata lunara DAE Valoarea totala Completezi formularul cu dat...
- **Pagini secundare urmărite:**
  - https://credex.ro/credit-de-nevoi-personale/ — titlu: Credit de nevoi personale - Credex
    - fragment: Credit de nevoi personale - Credex Sari la conținut Meniu Meniu Credit de nevoi personale Card de credit Oferte Despre Noi Contact Plateste rata Credit nevoi personale Ia-ti noul credit de nevoi personale, simplu si rapid. Orice plan ai avea, noi te ajutam sa devina realitate. Ai credit de nevoi personale cu dobanda incepand de la 18%! Creditul de nevoi personale de oriunde, oricand si pentru orice cu rate fixe pe toata durata creditului. Poti obtine un credit rapid si simplu, 100% online, fara ...
  - https://credex.ro/totul-despre-credite/card-de-credit-credex/ — titlu: Card de credit - Credex
    - fragment: Card de credit - Credex Sari la conținut Meniu Meniu Credit de nevoi personale Card de credit Oferte Despre Noi Contact Plateste rata Alege cardul de credit Credex si poti avea tot ce iti doresti! Bani pentru proiectele tale Plateste in 12 rate fara dobanda cu Cardul Credex la Altex, Media Galaxy si Brico Depot, atat online, cat si in magazinele fizice, pentru tranzactii de minimum 1.000 lei. Tranzactiile eligibile se posteaza automat in 12 rate fara dobanda. Vezi regulamentul campaniei AICI Apl...

## TechVentures Bank

- **URL:** https://techventures.bank/
- **Status:** ERROR
- **Notă inițială:** user a semnalat inițial: fără pagină ToS identificată
- **Motiv:** ReadTimeout: HTTPSConnectionPool(host='techventures.bank', port=443): Read timed out. (read timeout=10)

## Banca Română de Credite și Investiții (BRCI)

- **URL:** https://www.brci.ro/
- **Status:** OK
- **Notă inițială:** user a semnalat inițial: fără pagină ToS identificată
- **Titlu pagină:** BRCI
- **Linkuri relevante găsite** (produse/dobânzi/tarife etc.):
  - https://www.facebook.com/pages/BRCI-Banca-Rom%C3%A2n%C4%83-de-Credite-%C5%9Fi-Investi%C5%A3ii/1414785792161177
  - https://www.brci.ro/ro/produse/cont-curent-pj.html
  - https://www.brci.ro/ro/produse/card-mastercard-business.html
  - https://www.brci.ro/ro/produse/card-mastercard-netopia-business.html
  - https://www.brci.ro/ro/produse/card-mastercard-paypoint-business.html
  - https://www.brci.ro/ro/produse/plafon-de-creditare.html
  - https://www.brci.ro/ro/produse/linia-de-credit.html
  - https://www.brci.ro/ro/produse/creditul-de-investitie.html
  - https://www.brci.ro/ro/produse/acreditivul-documentar.html
  - https://www.brci.ro/ro/produse/depozite.html
- **Fragment text homepage:** BRCI AGENȚII PROGRAM Facebook +40 021 2006 111 Curs valutar Agenții Contact Persoane juridice Persoane fizice Asistență Clienţi: +4 021.20.06.111 BRCI iBanking Operațiuni curente Operațiuni curente Cont curent Card Mastercard Business Card Mastercard NETOPIA Business Card Mastercard PayPoint Business ÎNTREBAŢI SPECIALISTUL Credite Credite Plafon de creditare Linie de credit Overdraft Plafon de trezorerie Credit de investiții ÎNTREBAŢI SPECIALISTUL Factoring Operațiuni documentare Operațiuni docu...
- **Pagini secundare urmărite:**
  - https://www.facebook.com/pages/BRCI-Banca-Rom%C3%A2n%C4%83-de-Credite-%C5%9Fi-Investi%C5%A3ii/1414785792161177 — ERROR: ReadTimeout: HTTPSConnectionPool(host='www.facebook.com', port=443): Read timed out. (read timeout=10)
  - https://www.brci.ro/ro/produse/cont-curent-pj.html — titlu: BRCI
    - fragment: BRCI AGENȚII PROGRAM Facebook +40 021 2006 111 Curs valutar Agenții Contact Persoane juridice Persoane fizice Asistență Clienţi: +4 021.20.06.111 BRCI iBanking Operațiuni curente Operațiuni curente Cont curent Card Mastercard Business Card Mastercard NETOPIA Business Card Mastercard PayPoint Business ÎNTREBAŢI SPECIALISTUL Credite Credite Plafon de creditare Linie de credit Overdraft Plafon de trezorerie Credit de investiții ÎNTREBAŢI SPECIALISTUL Factoring Operațiuni documentare Operațiuni docu...

## BCR Banca pentru Locuințe

- **URL:** https://www.bcrlocuinte.ro/
- **Status:** OK
- **Notă inițială:** user a semnalat inițial: fără pagină ToS identificată
- **Titlu pagină:** Banca pentru Locuințe | Banca Comercială Română
- **Descriere meta:** Banca pentru locuințe îți pune la dispoziție creditul potrivit pentru casa ta! Află avantajele Creditului fix, Creditului Locativ, Creditului Anticipat și alte credite.
- **Linkuri relevante găsite** (produse/dobânzi/tarife etc.):
  - https://www.bcrlocuinte.ro/ro/creditare/creditul-locativ
- **Fragment text homepage:** Banca pentru Locuințe | Banca Comercială Română Omite Bine ai venit la BCR Banca pentru Locuințe! Împreună cu noi, casa la care visezi devine acasă! Ministerul Dezvoltarii, Lucrarilor Publice si Administratiei a virat Primele de Stat pentru perioada 2014 – 2022. Pentru mai multe informatii va rugam sa accesati Detalii Prima de Stat. Detalii Prima de Stat Susținem realizarea planurilor mari. Al tău care este? Creditul locativ Ideile bune merită să fie puse în practică. De aceea creditul pentru do...
- **Pagini secundare urmărite:**
  - https://www.bcrlocuinte.ro/ro/creditare/creditul-locativ — titlu: Creditul Locativ
    - fragment: Creditul Locativ Omite Mergi la Avantaje Mergi la Caracteristici Mergi la Exemplu de calcul Mergi la Garanții Mergi la Asigurări Mergi la Riscuri  și consecințe Mergi la Condiții Mergi la Documente utile Creditul pentru domeniul locativ Bauspar E păcat să se irosească ideile bune! De aceea,  creditul pentru domeniul locativ îţi sare în ajutor atunci când îţi planifici reamenajarea casei tale. În plus, te vei bucura şi de costuri reduse. Dobânda redusă și fixă de 5%/an sau 6%/an pe toata perioada...

## Nexent Bank N.V. Amsterdam – Sucursala București

- **URL:** https://www.nexentbank.ro/
- **Status:** OK
- **Notă inițială:** user a semnalat inițial: doar politică de cookies găsită
- **Titlu pagină:** Nexent Bank
- **Descriere meta:** Nexent Bank ofera solutii bancare digitale moderne, sigure si rapide, adaptate nevoilor tale financiare, oriunde te-ai afla.
- **Linkuri relevante găsite** (produse/dobânzi/tarife etc.):
  - https://actualizare-date-personale.crediteurope.ro/Main?culture=ro-RO#/userjourney/FTOS_BARET_AccountApplication/insert/form/CEB_DataUpdate
  - https://www.cardavantaj.ro/aplica?core_campaign=1435&product=contcurent
  - https://www.nexentbank.ro/persoane-fizice/Carduri-de-credit
  - https://www.nexentbank.ro/persoane-fizice/Carduri-de-credit/CardAvantaj
  - https://www.nexentbank.ro/persoane-fizice/Carduri-de-credit/WIZZ-Card-Avantaj
  - https://www.nexentbank.ro/persoane-fizice/Carduri-de-credit/Optimo-Card
  - https://www.nexentbank.ro/persoane-fizice/Carduri-de-credit/Nexent-Diamond
  - https://www.nexentbank.ro/persoane-fizice/Carduri-de-Debit
  - https://www.nexentbank.ro/persoane-fizice/Carduri-de-Debit/Mastercard-Standard-Debit
  - https://www.nexentbank.ro/persoane-fizice/Carduri-de-Debit/Visa-Clasic-Debit
- **Fragment text homepage:** Nexent Bank Folosim tehnologii de tip cookies pentru a-ți asigura o experiență cât mai plăcută de utilizare a site-ului. Această tehnologie ne permite să analizăm performanța site-ului, să îi îmbunătățim permanent funcționalitățile și să afișăm un conținut și reclame personalizate, în funcție de preferințele tale. De asemenea, utilizăm fișierele de tip cookies pentru activitățile specifice publicității în mediul online, pentru promovarea produselor și serviciilor financiare oferite de Nexent Ban...
- **Pagini secundare urmărite:**
  - https://actualizare-date-personale.crediteurope.ro/Main?culture=ro-RO#/userjourney/FTOS_BARET_AccountApplication/insert/form/CEB_DataUpdate — ERROR: ConnectionError: HTTPSConnectionPool(host='actualizare-date-personale.crediteurope.ro', port=443): Max retries exceeded with url: /Main?culture=ro-RO (Caused by NameResolutionError("HTTPSConnection(host='actualizare-date-personale.crediteurope.ro', port=443): Failed to resolve 'actualizare-date-personale.crediteurope.ro' ([Errno 11001] getaddrinfo failed)"))
  - https://www.cardavantaj.ro/aplica?core_campaign=1435&product=contcurent — titlu: Deschide cont curent Nexent Bank
    - fragment: Deschide cont curent Nexent Bank Deschide cont acum Depozite la termen în lei cu dobândă promoțională de până la 6,75% Deschide un cont curent, transferă fonduri și constituie un depozit pe 3, 6 sau 12 luni cu dobândă de până la 6,75%. Deschide cont acum *Zero comisioane la transferurile efectuate prin aplicația monet indiferent de moneda tranzacției, până la 31.12.2026 Mai multe beneficii pentru economiile tale Dobândă până la 6,75% promoțională pentru depozite constituite în lei din sume noi**...

## BNP Paribas Personal Finance S.A. – Sucursala București / Cetelem

- **URL:** https://www.cetelem.ro/
- **Status:** OK
- **Notă inițială:** user a semnalat inițial: fără clauză găsită
- **Titlu pagină:** Cetelem
- **Descriere meta:** Aplica pentru un credit de nevoi personale rapid Cetelem sau pentru refinantare cu dobanda avantajoasa, fara comisioane, fara garantii pana la 225.000 lei.  Cetelem este sucursala Bucuresti a BNP PARIBAS Personal Finance Paris SA. Credit rapid online, card de credit, credit auto, asigurari.
- **Linkuri relevante găsite** (produse/dobânzi/tarife etc.):
  - https://www.cetelem.ro/card-de-credit?cid=000002b490c4daaf64342a497cde5685
  - https://www.cetelem.ro/carduri-de-cumparaturi?cid=000002b490c4daaf64342a497cde5685
  - https://www.cetelem.ro/card-de-credit/cardul-cardulescu?cid=000002b490c4daaf64342a497cde5685
  - https://www.cetelem.ro/card-de-credit/carduri-de-cumparaturi/card-auchan?cid=000002b490c4daaf64342a497cde5685
  - https://www.cetelem.ro/card-de-credit/carduri-de-cumparaturi/card-flanco?cid=000002b490c4daaf64342a497cde5685
  - https://www.cetelem.ro/card-de-credit/carduri-de-cumparaturi/card-leroy?cid=000002b490c4daaf64342a497cde5685
  - https://www.cetelem.ro/card-de-credit/carduri-de-cumparaturi/card-dedeman?cid=000002b490c4daaf64342a497cde5685
  - https://www.cetelem.ro/card-de-credit/carduri-de-cumparaturi/card-rombiz?cid=000002b490c4daaf64342a497cde5685
  - https://www.cetelem.ro/card-de-credit/carduri-de-cumparaturi/card-opel?cid=000002b490c4daaf64342a497cde5685
  - https://www.cetelem.ro/card-de-credit/reguli-siguranta-card-cetelem?cid=000002b490c4daaf64342a497cde5685
- **Fragment text homepage:** Cetelem Login Detalii Meniu Carduri Cardurile Cetelem Card Cardulescu Card Auchan Card Flanco Card Leroy Merlin Card Dedeman Card Rombiz Card Opel Reguli siguranta card Cetelem Cum platesti online cu cardul Cetelem (tutorial) Plateste online cu aplicatia gratuita Cetelem 3D Secure (tutorial) Relații clienți Contactează-ne Cardurile Cetelem Reguli siguranta card Cetelem Cum platesti online cu cardul Cetelem (tutorial) Plateste online cu aplicatia gratuita Cetelem 3D Secure (tutorial) Asigurari Ba...
- **Pagini secundare urmărite:**
  - https://www.cetelem.ro/card-de-credit?cid=000002b490c4daaf64342a497cde5685 — titlu: Cardul de cumparaturi Cetelem
    - fragment: Cardul de cumparaturi Cetelem Login Detalii Meniu Carduri Cardurile Cetelem Card Cardulescu Card Auchan Card Flanco Card Leroy Merlin Card Dedeman Card Rombiz Card Opel Reguli siguranta card Cetelem Cum platesti online cu cardul Cetelem (tutorial) Plateste online cu aplicatia gratuita Cetelem 3D Secure (tutorial) Relații clienți Contactează-ne Cardurile Cetelem Reguli siguranta card Cetelem Cum platesti online cu cardul Cetelem (tutorial) Plateste online cu aplicatia gratuita Cetelem 3D Secure (...
  - https://www.cetelem.ro/carduri-de-cumparaturi?cid=000002b490c4daaf64342a497cde5685 — titlu: Card de cumparaturi co-branded| Cetelem
    - fragment: Card de cumparaturi co-branded| Cetelem Login Detalii Meniu Carduri Cardurile Cetelem Card Cardulescu Card Auchan Card Flanco Card Leroy Merlin Card Dedeman Card Rombiz Card Opel Reguli siguranta card Cetelem Cum platesti online cu cardul Cetelem (tutorial) Plateste online cu aplicatia gratuita Cetelem 3D Secure (tutorial) Relații clienți Contactează-ne Cardurile Cetelem Reguli siguranta card Cetelem Cum platesti online cu cardul Cetelem (tutorial) Plateste online cu aplicatia gratuita Cetelem 3...

## Banque Banorient France S.A. – Sucursala România

- **URL:** https://www.banorientfrance.com/romanian/romania
- **Status:** BLOCKED_ROBOTS
- **Notă inițială:** user a semnalat inițial: doar note legale GDPR găsite
- **Motiv:** interzis explicit de robots.txt

## PKO Bank Polski S.A. – Sucursala București

- **URL:** https://www.pkobp.pl/ro/filiala-romania
- **Status:** ERROR
- **Notă inițială:** user a semnalat inițial: fără pagină ToS identificată
- **Motiv:** ConnectionError: ('Connection aborted.', ConnectionResetError(10054, 'An existing connection was forcibly closed by the remote host', None, 10054, None))
