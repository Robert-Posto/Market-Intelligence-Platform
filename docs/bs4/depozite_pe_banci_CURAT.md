# Tipuri de depozite pe bănci din România — versiune curată (v2, robustă)

## Metodologie (versiunea 2)

Versiunea anterioară folosea regex/headinguri pentru a "ghici" nume de produse
direct din text brut — genera multe fals-pozitive (întrebări FAQ, linkuri de
navigare "Mergi la...", fragmente de meniu prinse ca "produse").

Versiunea asta e diferită:
1. **Fetch politicos** — robots.txt respectat, User-Agent onest, delay între cereri (nemodificat față de v1).
2. **Curățare la nivel de HTML, nu de text** — elimin `<nav>`, `<header>`, `<footer>`, `<script>`, `<style>`, `<form>`, `<button>`, `<svg>`, `<iframe>` din DOM *înainte* de a extrage textul, nu prin pattern-matching după.
3. **Fără regex de "ghicit" nume de produs.** Am salvat textul curat, complet, per pagină, și l-am citit eu (Claude) direct, ca să identific produsele reale și să scriu descrierile — asta e pasul "cu Claude in spate" cerut inițial, făcut prin înțelegere, nu prin pattern matching.

Limitări rămase, onest raportate:
- Câteva site-uri (ex. **Nexent Bank**) sunt randate prin JavaScript — fetch-ul static nu vede conținutul real al paginii, doar elemente statice (în cazul Nexent, doar un banner de cookie-uri neobișnuit de lung). Pentru acestea am păstrat informația din numele produselor vizibile în linkurile de meniu (care sunt reale, doar că nu am descrierea completă).
- Câteva bănci rămân neaccesibile din motive tehnice (WAF/403, DNS, robots.txt real) — vezi tabelul rezumat.
- Unele dobânzi/promoții au date explicite în text (ex. Vista Bank are pagini cu campanii din 2021-2022 încă publicate) — le-am marcat clar ca **expirate**, nu curente.

---

## BCR
*Persoane fizice*
- **Depozitul la Termen BCR** — LEI: 3/6/12/24 luni · EUR/USD: 3/6/12 luni. Dobândă fixă, zero comision. Campanie activă 15.09.2026–31.12.2026: până la 6%/an lei, 2,25%/an euro pentru sume noi (doar clienți George nivel Max/Max Invest sau cu venit recurent în cont). Bonus dobândă până la 0,8%/an suplimentar pentru nivel Max/Max Invest. [sursă](https://www.bcr.ro/ro/persoane-fizice/economisire-si-investire/depozitul-la-termen)
- **Contul de economii** — menționat ca produs conex, fără pagină dedicată accesată în acest test.

## CEC Bank
**Fără date** — HTTP 403 pe pagina reală (WAF/anti-bot). Robots.txt propriu-zis permite accesul (`Allow: /`) — blocajul e la nivel de firewall, nu de robots.txt.

## Banca Transilvania
**Fără date** — HTTP 403 pe pagina reală (WAF/anti-bot), aceeași situație ca la CEC Bank.

## ING Bank (Sucursala București)
*Persoane fizice*
- **ING Economii** — cont de economii flexibil, zero comisioane, transfer instant din Home'Bank.
- **Depozit Bonus** — dobândă până la 6%/an pe 4 luni, pentru sume noi economisite în ING Economii; acces la bani fără să pierzi dobânda acumulată.
- **Depozite la termen** — RON: 3/6/12 luni · EUR: 1/3/6/12 luni. Zero comisioane.
- **ING Depo Invest** — 50% depozit + 50% fond mutual, dintr-o singură sumă (min. 2.000 RON sau 2.000 EUR). Dobândă preferențială pe partea de depozit: 7%/an RON (6 luni) sau 2,5%/an EUR (3 luni), vs. 4,5%/1,5% dobânda standard fără pachet.
- **ING Economii pentru Copii** — cont de economii pentru minori, alimentare de la orice bancomat ING.
- **Round Up** — economisire automată prin rotunjirea plăților cu cardul/telefonul, transferată în ING Economii.

*IMM/Companii*
- **Depozitul Business Bonus** — 3 luni, dobândă 5,1%/an, min. 1.000 RON, exclusiv pentru sume noi ale companiei; acces oricând la bani fără pierderea dobânzii.
- **Depozite la termen (IMM)** — min. 1.000 unități RON/EUR (standard) sau 100.000 unități (premium).
- **Cont de economii (IMM)** — dobândă pe praguri de la 25.000 lei, plătită lunar, max. 3 conturi/companie.

[surse](https://ing.ro/persoane-fizice/economii-si-investitii) · [depo-invest](https://ing.ro/persoane-fizice/economii-si-investitii/depo-invest) · [imm](https://ing.ro/imm/Economii/depozitul-business-bonus)

## BRD — Groupe Société Générale
*Persoane fizice*
- **Depozitul la Termen** — LEI/EUR/USD, 1 lună – 4 ani. Dobânzi tabelate (ex. 1 an: LEI 4,00%/ghișeu–5,20%/YOU BRD; EUR 1,15–1,65%; USD 2,25–2,75%). Min. 500 unități. Bonus dobândă la constituire prin YOU BRD.
- **Depozitul Progresso** — dobândă progresivă pe intervale de 180 zile, disponibil pe 1 an sau 3 ani, LEI/EUR/USD, min. 500 unități. Poți retrage integral fără să pierzi dobânda pe intervalele deja încheiate.
- **Contul de economii YOU Save** — 2,50%/an, fără sumă minimă, dobândă lunară.
- **YOU Save Junior** — cont economii pentru minori, 3,00%/an, plafon 500.000 RON, doar în agenții.
- **Economii la plata cu cardul** — mecanism de rotunjire/procent fix/transfer automat la fiecare plată cu cardul, către un cont de economii ales (nu e depozit propriu-zis).

*(Menționate ca produse conexe de economisire, nu depozite clasice: Eduplan, Asigurarea Invest Benefit+, Asigurarea LongVita — asigurări de viață cu componentă investițională)*

[sursă principală](https://www.brd.ro/depozitul-la-termen) · [Progresso](https://www.brd.ro/persoane-fizice/economisire-si-investitii/depozite/progresso)

## Raiffeisen Bank
*Persoane fizice*
- **Cont de economii (Super Acces Plus)** — LEI/EUR/USD, fără sumă minimă, termen nelimitat. Dobândă variabilă pe tranșe: LEI ≤50.000 = 2,00%/an, 50.001–300.000 = 2,50%/an, >300.000 = 3,00%/an; EUR flat 0,50%/an; USD flat 0,30%/an.
- **Cont "Plătești și Economisești"** — cont de economii alimentat automat prin rotunjire la plata cu cardul de debit; dobândă LEI pe tranșe: ≤5.000 = 10,00%/an, 5.001–50.000 = 5,00%/an, >50.000 = 2,50%/an.
- **Depozitul Fresh Money** — doar pentru bani noi, LEI/EUR, min. 500 lei/100 EUR, 4 luni, dobândă fixă 6,20%/an LEI / 2,50%/an EUR, închidere la maturitate.
- **Flexidepozit** (depozit cu depuneri ulterioare) — LEI, min. 500 lei, 6 luni, dobândă fixă 5,00%/an, o retragere parțială permisă (max. 20% din sold).
- **Depozite la termen (standard)** — LEI: 3/12/24 luni (4,70–6,40%/an) · EUR: 1/3/6/12 luni (0,50–2,00%/an) · USD: 3/6/12 luni (2,20–2,80%/an). Variante cu bonus de dobândă pentru clienți cu pachet Gold/Premium/Zero și încasări lunare minime.

[sursă economii](https://www.raiffeisen.ro/ro/persoane-fizice/produsele-noastre/economii.html) · [depozite la termen](https://www.raiffeisen.ro/ro/persoane-fizice/produsele-noastre/economii/depozite-la-termen.html)

## UniCredit Bank
**Fără date** — HTTP 403 (WAF/anti-bot).

## Intesa Sanpaolo Bank România
**Fără date** — HTTP 403 (WAF/anti-bot).

## Vista Bank (Romania)
*Persoane fizice — produse curente (fără dată de expirare în text)*
- **Depozitul la Termen "VISTA 12+1"** — persoane fizice/juridice, min. 4.500 LEI / 1.000 EUR/USD, fără limită maximă. Acces la dobânda acumulată la fiecare aniversare lunară, plus bonus la scadența finală (12 luni). Bonus +0,2pp la constituire online.
- **Depozitul VISTA KIDS** — pentru minori până la 18 ani, min. 2.000 LEI/500 EUR/USD, +0,5pp bonus față de depozitele standard pe 12 luni (12 luni: 6,00% RON / 2,50% EUR / 3,50% USD).
- **Contul de Economii Vista Smart** — LEI/EUR/USD, dobândă crescătoare pe tranșe (ex. RON: 0% ≤2.000, 3,00% 2.001–50.000, 3,30% 50.001–100.000, 3,50% peste).
- **Depozite la Termen (generale)** — 1/3/6/9/12 luni, RON 4,25–5,50%, EUR 0,50–2,00%, USD 1,00–3,00%.
- VISTA FLEXI (Depozitul pe 12 Luni) și "VISTA DEPOZIT LA TERMEN PE 6 LUNI" — menționate cu dobânzi mai vechi (fără dată clară de expirare), posibil produse istorice — verifică direct cu banca.

⚠️ **Promoții expirate încă publicate pe pagină, NU curente**: "Depozitul de bun venit 2,2%" (iunie 2021), "Depozitul Vista 2,9%" (ianuarie 2022), "Depozitul Generos 3,1%" (iulie 2021), "Depozitul Vista 3,45%" (februarie 2021).

[sursă](https://www.vistabank.ro/persoane-fizice/depozite)

## Patria Bank
*Persoane fizice*
- **Depozit online** ("Patria de Oriunde") — 100% online, doar pentru clienți fără cont curent existent la Patria. LEI 4 luni 6,60%/an, EUR 7 luni 2,60%/an, USD până la 3,50%/an.
- **Depozitul Patria Clasic** — LEI/EUR/USD, 1–24 luni.
- **Depozitul Patria Senior Plus** — exclusiv pentru pensionari peste 60 ani.
- **Depozite la termen (general)** — 1–25 luni (în funcție de monedă/campanie), posibilitate de negociere peste 100.000 lei depuși.
- **Contul de economii Patria** — fără cost, fără sumă minimă. Dobândă LEI degresivă: <5.000 lei = 0,50%/an, 5.000–10.000 = 0,75%/an, >10.000 = 0,00%/an.
- **Fonduri de investiții** (Patria Global, Patria Obligațiuni) — alternativă de economisire, nu depozit clasic.

*Companii*
- **Depozitul Business Flexi** — promoție 27.07–31.10.2026, RON 4,00%/an, EUR 1,00%/an, USD 2,00%/an, fără sumă minimă/maximă, fără prelungire automată.
- **Depozit Overnight** — plasament pe termen foarte scurt pentru companii.

[sursă](https://www.patriabank.ro/persoane-fizice/economii/depozite-bancare) · [business flexi](https://www.patriabank.ro/afaceri-mici/depozite/depozitul-business-flexi)

## Exim Banca Românească
*Persoane fizice*
- **DEPOZITUL PLUS LEI / PLUS START** — promoție activă până la 30.10.2026, 7 luni, 6,5%/an, min. 500 lei din fonduri noi, doar clienți noi.
- **DEPOZITUL PLUS LEI / PLUS ACTIV** — aceeași promoție, 6,3%/an, pentru clienți existenți.
- **DEPOZITUL PLUS EURO** (START/ACTIV) — aceeași structură, 7 luni, 2,9%/2,70%/an, min. 150 EUR.
- **Depozit cu plata dobânzii la scadență** — RON/EUR/USD/GBP/CHF, min. 500 RON/150 valută, termene 30–730 zile (ex. 365 zile: 5,40% RON / 2,00% EUR / 3,00% USD).
- **Depozit cu plata lunară a dobânzii** — RON/EUR, 3/6/12 luni, min. 1.500 RON/500 EUR.
- **Depozitul Pensia Activa** — pentru pensionari, RON/EUR/USD, min. 500 RON/150 valută, rate similare (365 zile: 5,50/2,05/3,05%).
- Bonus automat de dobândă pentru depozite peste 100.000 RON (+0,15pp) sau peste 20.000 EUR/USD (+0,10pp).

*Companii/IMM*
- **Depozite standard** — min. 100.000 RON/50.000 EUR/USD (negociabile peste acest prag), 1/3/6/12 luni.
- **Automatic Overnight** — depozit peste noapte automat, min. 100.000 RON/50.000 valută.
- **Titluri de stat** — certificate de trezorerie (termen scurt) și obligațiuni (termen lung).

[sursă](https://www.eximbank.ro/2026/09/15/depozitul-plus-lei/) · [depozite generale](https://www.eximbank.ro/2022/11/09/si-mai-multe-depozite/)

## Libra Internet Bank *(angajator, nu competitor)*
*Persoane fizice / profesii liberale / persoane juridice — categorii separate, dobânzi valabile de la 18.08.2026*
- **Depozite standard** (7 zile/1/3/6/9/12 luni) — LEI 2,50–5,50%/an, EUR 1,10–2,15%/an, USD 1,50–3,00%/an (variază ușor pe categorie).
- **Depozite pe termen lung** (18/24/36 luni) — LEI ~5,00%, EUR ~1,75%, USD ~3,00%.
- **Depozit "Blitz"** (best-offer) — 7 luni 5,25%/an LEI sau 1 an+1 lună 5,75%/an LEI (6,22% total); variante EUR mai mici (2,20–2,25%).
- **Cont de economii** — 3,00%/an (scadență 6–12 luni), 2,50%/an (3–6 luni), 2,00%/an (nelimitat, dobândă lunară).

[sursă](https://www.librabank.ro/dobanzi-depozite-bancare-pentru-pensionari-persoane-fizice) · [firme](https://www.librabank.ro/dobanzi-depozite-persoane-juridice)

## ProCredit Bank
*Persoane fizice*
- **Depozit la termen** — LEI: 1/3/6/9/12/14/18/24 luni (5,00–7,15%/an, cel mai recent anunț din 6 iulie 2026) · EUR: aceleași termene (1,60–2,70%/an). Min. 500 unități.
- **FlexSave** — cont de economii, fără sumă minimă, 3%/an LEI, 0,20%/an EUR, fără retrageri directe (necesită transfer în cont curent).

*Companii*
- **Biz FlexSave** — cont de economii pentru afaceri, flexibil, 100% online.
- **Depozite la termen companii** — LEI/EUR, 3/6/12 luni, min. 50.000 LEI/10.000 EUR.

[sursă](https://www.procreditbank.ro/persoane-fizice/depozit-la-termen/) · [anunț extindere](https://www.procreditbank.ro/procredit-bank-extinde-oferta-de-depozite-la-termen/)

## Revolut Bank UAB — Sucursala București
**Fără date** — HTTP 403 (WAF/anti-bot) la prima rulare; la a doua rulare accesibil dar fără pagini de depozite identificate (posibil terminologie diferită în EN sau conținut integral JS).

## tbi bank EAD Sofia — Sucursala București
*Persoane fizice*
- **Depozitul Online** — 100% online, cetățeni români rezidenți, 18+. LEI: 1 lună 6,50% → 36 luni 7,50%/an. Fără costuri de deschidere/administrare/retragere.
- **Depozitul Simplu** — constituit în agenție, LEI/EUR/USD (LEI similar Online; EUR 0,35–3,00%; USD 0,75–3,00%, pe aceleași termene 1–36 luni).
- **Contul de Economii** — dobândă 5%/an, calculată zilnic, acces oricând.

*Companii*
- **Depozit pentru companii** — RON/EUR/USD, 1/3/6/12 luni, disponibil pentru PFA/liber profesioniști/companii, fără comisioane.

[sursă](https://tbibank.ro/product/depozitul-online/) · [companii](https://tbibank.ro/companii/depozite/depozit-persoane-juridice/)

## Garanti BBVA România
*Persoane fizice*
- **Depozit la termen** — RON/EUR/USD/GBP/CHF/CAD/TRY/NOK/SEK/PLN (+JPY/HUF cu min. mai mare), 1/3/6/12/15 luni. RON: 4,00–4,25%/an (agenție) sau 4,55–5,10%/an (online, variază pe tranșă valorică); EUR: 1,20–1,60%/an; USD: 1,50–2,45%/an. Min. 200 unități.
- **Economus** (cont economii) — plan automat lunar, dobândă capitalizată zilnic; RON 3,00%/an (50–10.000 RON), EUR 1,00%/an (10–2.500 EUR).
- **Depozite Cash Colateral** — folosite ca garanție, dobândă simbolică (0,01%).

*IMM/PFA/Corporate*
- **Depozit la termen (IMM)** — RON 4,25–5,25%/an, EUR 1,20–1,75%/an, USD 1,50–2,50%/an.
- **Economus (companii)** — RON 0,65%/an, EUR 0,25%/an.

[sursă](https://www.garantibbva.ro/persoane-fizice/dobanzi-si-comisioane-depozite-persoane-fizice/)

## Salt Bank
**Fără date** — domeniul `www.saltbank.ro` nu se rezolvă DNS. Domeniul real e posibil altul — nu confirmat.

## Citibank Europe plc — Sucursala România
**Fără produse de depozit identificate** — orientare exclusiv corporate/institutional banking, fără produse retail publice.

## BNP Paribas S.A. Paris — Sucursala București
**Accesibilă, fără produse de depozit retail** — corporate/institutional banking, fără produse retail publice.

## Banca Centrală Cooperatistă CREDITCOOP
*Persoane fizice*
- **Standard** — min. 30 lei, 1–24 luni, dobândă fixă sau variabilă, fără comision.
- **Star Plus** — min. 500 lei, 3 sau 6 luni, dobândă fixă.
- **Depozitul CREDITCOOP** — min. 500 lei, termen 14 luni, dobândă fixă.
- **Acces cont economii** — min. 100 lei, flexibil (depuneri/retrageri oricând), dobândă variabilă.
- Menționate în meniu, fără detalii extrase: FlexiPlus 7 luni, Standard 6 Luni Plus, CREDITCOOP Plus (variante promoționale pentru fonduri noi).

*Persoane juridice*
- **Standard Business** — min. 200 lei, 1–24 luni.
- **Star Plus Business** — min. 1.000 lei, 3 sau 6 luni.
- **Acces cont economii Business** — min. 500 lei, flexibil.

[sursă](https://www.creditcoop.ro/c/persoane-fizice/depozite/)

## Banca de Investiții și Dezvoltare (BID)
**Fără produse de depozit** — instituție de dezvoltare (nu bancă retail); clienții direcți sunt instituții de credit și UAT-uri, nu persoane fizice.

## Bank of China (CEE) Ltd — Sucursala București
**Fără produse de depozit retail identificate** — meniu corporate menționează generic "Deposits", fără detalii publice. Orientare trade finance China-România.

## Credex Bank
**Fără produse de depozit identificate** — site axat exclusiv pe credite de consum/carduri; nu oferă depozite pentru persoane fizice.

## TechVentures Bank
*Companii (singura pagină accesată cu succes)*
- **Depozit cu depuneri ulterioare** — LEI, min. 10.000 RON, 6 luni, dobândă fixă, opțiune de prelungire automată (cu/fără capitalizare), majorabil cu min. 100 lei/operațiune la ghișeu.
- Menționate în meniu, fără pagină accesată: Depozite overnight, Depozite la termen, Depozite escrow, Conturi de economii.

## Banca Română de Credite și Investiții (BRCI)
- **Depozite la termen** — RON/EUR/USD, 1/3/6/9/12 luni, min. 500 RON/100 EUR/100 USD. Dobândă fixă, posibilitate de prelungire automată, accesibil și minorilor prin reprezentant legal. Constituire în max. 30 secunde prin iBanking/app mobilă.

[sursă](https://www.brci.ro/ro/produse/depozitul-la-termen.html)

## BCR Banca pentru Locuințe
**Fără produse de tip depozit clasic** — casă de economii pentru domeniul locativ (Bauspar); produsul central e Creditul Locativ (economisire+creditare condiționată), nu un depozit independent.

## Nexent Bank N.V. Amsterdam – Sucursala București
⚠️ **Limitare tehnică**: paginile de produs sunt randate prin JavaScript — fetch-ul static nu vede conținutul real, doar un banner de cookie-uri neobișnuit de lung. Informația de mai jos vine din numele produselor vizibile în linkurile de meniu (reale, dar fără descrierile complete):
- **Depozite la termen** — RON/EUR/USD, variante standard și pentru pensionari.
- **Campania "Bani Noi"** — dobândă preferențială până la 6,75%/an pentru sume noi.
- **Contul de economii** — flexibil, protejat de schema de garantare olandeză.
- **Depozite IMM / Depozite Corporate** — pentru companii.

Recomandare: verifică direct pe site cu un browser normal, nu prin fetch automatizat.

## BNP Paribas Personal Finance S.A. – Sucursala București / Cetelem
**Fără produse de depozit** — specializat exclusiv pe credit de consum și carduri de cumpărături.

## Banque Banorient France S.A. – Sucursala România
**Fără date** — blocat de `robots.txt` (singurul caz confirmat de interdicție reală în conținutul fișierului, nu fals-pozitiv).

## PKO Bank Polski S.A. – Sucursala București
**Fără date** — conexiune resetată de server. Sucursală corporate orientată spre companii poloneze din România — puțin probabil să aibă depozite retail publice.

---

## Rezumat

| Status | Bănci |
|---|---|
| **Produse de depozit identificate, cu detalii solide** (14) | BCR, ING, BRD, Raiffeisen, Vista Bank, Patria Bank, Exim Banca Românească, Libra Internet Bank, ProCredit Bank, tbi bank, Garanti BBVA, CREDITCOOP, BRCI, TechVentures Bank (parțial) |
| **Nume de produs cunoscute, dar fără descriere completă** (1) | Nexent Bank (conținut randat prin JS) |
| **Accesibile, fără produse de depozit retail** (7) | Citibank, BNP Paribas Sucursala București, BID, Bank of China, Credex Bank, BCR Banca pentru Locuințe, Cetelem |
| **Blocate real de robots.txt** (1) | Banque Banorient France |
| **Erori tehnice (WAF/DNS/timeout)** (7) | Banca Transilvania, CEC Bank, UniCredit, Intesa Sanpaolo, Revolut, Salt Bank, PKO Bank Polski |
