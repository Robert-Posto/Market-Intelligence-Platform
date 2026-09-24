# Îmbunătățirile populării de la zero (23–24.09.2026)

Popularea s-a refăcut de la zero, numai cu scripturile din repo: nu s-a
încărcat nimic din `date/pachet/`, din `date/rezultate_*.json` sau din Bronze-ul
vechi. Pachetul colegului apare mai jos doar ca reper numeric.

Cifrele „după" vin din `python scripts/raport_calitate.py`, rulat pe 24.09.2026
după refacerea finală din Bronze.

## Actualizare 24.09, după completare și parserele colegului

Descoperirea intră acum și pe paginile „tarife / documente" (BCR: 97 → 326 de
surse active), iar extracția folosește parserele PDF ale colegului (subpuncte
cu serviciu, USD/GBP/CHF, valori false scoase). Refăcut din Bronze.

| | 24.09 dimineață | 24.09 după completare + parserele colegului |
|---|---|---|
| valori | 7.017 | **27.218** |
| curate | 3.223 (46%) | **14.722 (54%)** |
| concept comparabil | 59% | **65%** |
| datate | 57% | **69%** |
| ambigue | 24% | 20% |
| citate HTML regăsite | 520/520 | 626/626 |
| citate PDF (eșantion) | 222/223 | 245/247 |

De verificat: BCR are 13.661 de valori (jumătate din total) — posibil și
versiuni vechi din arhivă, marcate totuși în vigoare.

## Rezultatul, pe scurt (24.09 dimineață)

| | |
|---|---|
| surse descoperite | 5.023 de adrese, 30 de bănci (sitemap ∪ navigare) |
| valori (prețuri, dobânzi) | 7.017, la 23 de bănci; plus 604 nume de produse |
| valori curente | 6.589 (restul: istoric, dublură sau preț anunțat pentru viitor) |
| **valori „curate"** | **3.223 (46%)**: curente, neambigue, cu link, cu citat regăsit în sursă, cu concept comparabil |
| citate HTML regăsite în conținutul paginii | 520 / 520 (100%) |
| citate PDF regăsite pe pagina indicată (eșantion) | 222 / 223 (100%) |
| concept comparabil | 59% |
| datate | 57% |
| ambigue (în coada de verificare) | 24% |
| bănci blocate, documentate | BT, CEC, Intesa, UniCredit, Revolut |
| harta | 1.478 de puncte: Patria din locatorul băncii (45 de agenții + 572 de ATM-uri Euronet partenere, marcate separat), restul din Overture |

„Curat" e plafonat în primul rând de conceptul comparabil (59%) și de
ambiguitate (24%), nu de corectitudinea citirii: citatele se regăsesc aproape
integral în surse.

## Ce s-a schimbat și de ce

| # | schimbare | înainte | după |
|---|---|---|---|
| 1 | **Stop la blocaj.** 401/403/429 sau pagină de blocaj → sursa `blocat`, cu dovada; fără alt canal | cascada trecea la Playwright cu UA de Chrome și la LLM după 403 (așa „răspundeau" BT, Intesa, UniCredit, CEC) | 5 bănci documentate ca blocate |
| 2 | **UA-ul echipei peste tot**, inclusiv Playwright și proxy-ul `/pdf` | Playwright imita Chrome; proxy-ul avea alt UA | un singur UA, din `crawler/__init__.py` |
| 3 | **robots.txt:** grupul care ne numește, Crawl-delay per origine, verificare și după redirect și pe proxy-ul `/pdf` | doar grupul `*`; pauză fixă 1,5 s (Patria cere 5 s) | ING `*.pdf` refuzat și în aplicație (403) |
| 4 | **Descoperire:** sitemap ∪ navigare pe 2 niveluri, toate adresele clasificate salvate | crawler-ul colegului salva ≤80 de pagini vizitate; 612 surse în total | 5.023 de adrese; activ plafonat la 6 pagini/produs |
| 5 | **Amprentă pe textul sanitizat** (figura 3); Bronze scris doar la schimbare | amprentă pe octeți | un token de sesiune nu mai arată ca o schimbare |
| 6 | **Dobânzi doar din conținutul principal**, fără pagini de presă | 201 din 643 de citate (31%) veneau din meniu/subsol (ex. bannerul ING „4,79%/an") | 520 / 520 regăsite în conținut |
| 7 | **Documentele fără tarife nu mai dau prețuri** (rapoarte Reg. 575, situații financiare, buletine economice, PSD2/API, asigurări, prospecte, clasamente MiFID) | ~9.000 de „valori" din astfel de documente (CreditCoop ~1.000, Libra ~700, Vista 4.911 dintr-un singur document API) | 132+ documente excluse după nume/titlu |
| 8 | **Coloana și segmentul** (Visa/Mastercard, PF/PJ) ajung în bază și în cheia de deduplicare | variantele de produs se uneau într-un singur rând | migrarea 015 |
| 9 | **Validatorul colegului** pe dobânzi; suspectele merg în coadă | neconectat | 37/38 verdicte corecte pe etalon |
| 10 | **Plafoanele de încredere** aplicate și valorilor numerice | plafonul `SURSA_VECHE` era cod mort | aplicat |
| 11 | **Vocabular:** recuperare card, contestare, pachet de servicii | nemapate | 3 concepte noi |
| 12 | **ATM-uri partenere** separate de rețeaua proprie (migrarea 016) | 617 „ATM-uri Patria" care erau Euronet | 45 agenții + 572 partenere |
| 13 | **PDF-urile noi au link** în aplicație | linkul se construia doar din `url_public`, gol | se deschid, cu pagina și citatul evidențiat |
| 14 | **`--banca` înlocuiește doar banca ei** | parametrul era suprascris în `scrie()`: fiecare bancă ștergea datele celorlalte | reparat, refăcut din Bronze |

## Comparație cu pachetul colegului (doar reper numeric)

Mai multe valori acum: Vista (951 vs 4), Nexent (771 vs 18), BRCI, Libra,
Garanti, Raiffeisen, Salt, Patria. Mai puține: BCR (458 vs 1.526), CreditCoop
(7 vs 230), Exim (109 vs 333), ProCredit (194 vs 367), TechVentures (49 vs
261), Credex, BCR Locuințe, Revolut (acum ne blochează). Cauze probabile, de
verificat: documente de tarife neajunse în plafonul de 6 pagini/produs sau
nedescoperite; la CreditCoop, pachetul includea probabil și rapoartele pe
care acum le excludem.

## Ce rămâne

- **Bănci blocate** (BT, CEC, Intesa, UniCredit, Revolut): o cale permisă —
  comparatorul public de costuri, cerere de acces către bancă, aviz juridic
  pentru `web_search`/`web_fetch`, sau documente salvate manual de un om.
- **LLM:** discovery pentru goluri și rezerva de extracție (plan, pașii 7 și
  11) — cu cost măsurat întâi pe o bancă.
- **Concept comparabil 59%:** cea mai mare pârghie pentru „curat".
- **Locatoare cu căutare** (BCR, BRD…): API-ul hărții e interzis de robots.txt
  la BRD, CreditCoop, Libra; la BCR, BRCI, ProCredit răspunsurile JSON nu au
  coordonate. Scriptul există: `ingest/locatoare_js.py`.
- **Măsurat, amânat:** dobânzi pe coloane multiple (plan, pasul 6) —
  `crawler/parser_rate.py` are deja `_coloane_suplimentare`; re-scorarea pe
  etalon înainte de orice schimbare.
- **Înlocuirea `robots_matcher.py`** în scripturile BS4 vechi (nu fac parte
  din populare).
