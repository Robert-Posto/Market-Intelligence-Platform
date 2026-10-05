# Reclamele concurenței din bibliotecile oficiale: Google, Meta, LinkedIn, Microsoft

Nicolae Cherascu, 28.09.2026 · Market Intelligence Platform, secțiunea 2.4 („reclame active”)

## Despre ce e vorba

Market Intelligence Platform monitorizează 30 de bănci din România, doar din date publice. Secțiunea 2.4 a arhitecturii cere și **reclamele active ale concurenților**.

Regulile proiectului îngrădesc felul în care le putem lua:
- doar surse oficiale;
- fără scraping pe platformele de publicitate;
- fără servicii terțe care colectează în locul nostru;
- fără ocolirea protecțiilor anti-bot.

Sursa care respectă aceste reguli există de la **Regulamentul UE privind serviciile digitale** (DSA, art. 39). Din august 2023, platformele și motoarele de căutare foarte mari trebuie să publice o **bibliotecă a reclamelor afișate în UE**, păstrate un an după ultima afișare. Patru dintre ele oferă acces automat oficial, pe care îl putem folosi: **Google, Meta, LinkedIn și Microsoft**.

Documentul explică, pentru fiecare:
- ce date dă;
- ce costă;
- ce riscuri au termenii;
- cine ce trebuie să facă ca să pornim.

**Starea de azi:** nu s-a colectat nicio reclamă. Regula pe care o propunem e **nicio extragere reală înainte de avizul juridic**. Până atunci se pot pregăti doar conturile și structura datelor.

## Pe scurt

| | Google Ads Transparency (BigQuery) | Meta Ad Library API | LinkedIn Ad Library API | Microsoft Ad Library API |
|---|---|---|---|---|
| **Cost** | gratuit până la 1 TiB procesat pe lună; peste, 6,25 USD/TiB | gratuit | probabil gratuit (neconfirmat oficial) | gratuit, chiar fără cont |
| **Termeni pentru uzul nostru** | analiza internă pare permisă; o clauză de lămurit | nicio interdicție explicită găsită; obligație de ștergere | neclar: o clauză exclude scopul „de publicitate” | **risc**: „personal and non-commercial use” |
| **Ce trebuie ca să pornim** | un proiect Google Cloud (sandbox fără card) | un angajat numit își verifică identitatea la Meta; excepție de proxy | o cerere de acces aprobată de LinkedIn | nimic tehnic; doar avizul |
| **Textul reclamei** | **nu**, doar metadate | da | da | da |
| **Băncile noastre apar?** | da (BT, ING, Revolut, măsurat pe 25.09) | de verificat la primul apel | de verificat | da (ING, 20 de reclame în RO; BT, 0) |
| **Ordinea propusă** | 1 | 2 | 3 | 4, doar dacă avizul permite |

Niciuna nu dă **cheltuiala** unei reclame comerciale.

## Ce dă fiecare bibliotecă

### 1. Google Ads Transparency Center, prin setul public din BigQuery

**Ce e.** Google publică reclamele livrate în Spațiul Economic European ca set de date public în BigQuery:
- setul: `bigquery-public-data.google_ads_transparency_center`;
- tabelul principal: `creative_stats`.

Setul se interoghează cu SQL și nu cere nicio aprobare de la Google. Arhitectura spunea că Google n-are API și că trebuie un furnizor sau colectare manuală. **Setul acesta schimbă concluzia.**

**Ce date dă** (schema exactă se vede gratuit în consola BigQuery):
- advertiserul: nume și ID;
- formatul (text, imagine, video) și tema;
- pe fiecare țară: prima și ultima zi de afișare și un **interval** de afișări (de exemplu „între 10.000 și 50.000”);
- platforma: Search, YouTube, Shopping, Play, Maps.

Reclamele plătite de pe **YouTube** vin tot de aici.

**Ce nu dă:** textul sau imaginea reclamei, cheltuiala, cuvintele-cheie, clicurile.
- Intervalele de afișări există din martie 2023 și apar cu ~90 de zile întârziere (surse secundare).
- Google avertizează pe forumul oficial că setul *„may not have all of the data”*. Nu are SLA și nu păstrează istoricul pentru noi, deci exporturile le păstrăm la noi.

**Cum se lucrează:**
1. IT creează un proiect Google Cloud al organizației. Varianta *sandbox* merge fără card: 1 TiB de interogări pe lună, 10 GiB de stocare, iar tabelele expiră după 60 de zile.
2. Vedem schema și costul unei interogări cu un *dry-run*, care e gratuit și nu citește date.
3. După aviz: o interogare filtrată pe advertiserii băncilor și pe `region_code = 'RO'`.
4. Exportăm rezultatul local, din consola BigQuery. Pentru export nu e nevoie de cod.

**Cost:** Google plătește stocarea, iar noi plătim doar interogările. Exportul complet al setului are ~680 GB în JSON, dar BigQuery taxează doar coloanele citite. O interogare restrânsă pe băncile noastre ar trebui să intre în pragul gratuit, iar dry-run-ul confirmă asta înainte. Prețul de 6,25 USD/TiB e cel din regiunile US; locația setului n-am confirmat-o.

**Termenii** (Ads Transparency Center Additional Terms of Service):
- *„You may access and use the Ads Transparency Center for your or your organization's information or research purposes only.”* Analiza internă pare permisă.
- *„…you will not sell or monetize any part of the Ads Transparency Center…”* Nu e cazul nostru.
- *„You may not use that content, including ads or any other information related to Google's customers' ads or ad campaigns, without the relevant customer's permission, or as otherwise allowed by law.”* **Clauza de lămurit cu juristul.**

**Ce am verificat pe 25.09.2026:** am analizat un singur fragment din exportul oficial public, cu 66.916 reclame, dintre care 4.308 livrate în România. În el apar:
- **Banca Transilvania**, cu 4 reclame, deși site-ul BT ne blochează;
- **ING Bank N.V. Amsterdam Sucursala București**, cu 2 reclame, sub două grafii ale numelui;
- **Revolut Ltd**.

### 2. Meta Ad Library API (Facebook și Instagram)

**Ce e.** API-ul oficial al bibliotecii de reclame Meta. Pagina oficială spune că întoarce *„ads of any type that were delivered to the UK or EU during the past year”*, deci și reclame comerciale, nu doar politice. O sursă terță susține contrariul, așa că **primul apel real** ne arată dacă găsim reclamele băncilor din România.

**Ce date dă:**
- textul reclamei, titlul, descrierea;
- data de start și de stop, platformele (Facebook, Instagram, Messenger…);
- pentru reclamele din UE: **reach-ul total estimat**, defalcarea pe vârstă, gen și țară, targetarea, plătitorul și beneficiarul;
- imaginea și videoclipul vin doar ca **link** spre biblioteca Meta (`ad_snapshot_url`), nu ca fișiere.

**Ce nu dă:** cheltuiala și impresiile. Acestea există doar pentru reclamele politice, iar din octombrie 2025 Meta nu mai acceptă reclame politice în UE (surse secundare).

**Cum se lucrează:**
1. **Un angajat numit** își confirmă identitatea la `facebook.com/ID`, cu act de identitate emis de stat și dovada țării. Meta spune că durează câteva zile. Contul e **personal**, al angajatului, deci datele lui ajung la Meta.
2. Angajatul își face un cont Meta for Developers și acceptă Platform Terms, apoi o aplicație și un token de acces, valabil ~60 de zile (surse secundare).
3. Cererile se fac pe țara RO și pe paginile de Facebook ale băncilor, cu tipul de reclamă „ALL”. Limita e de ~200 de apeluri pe oră, cu 25 de reclame pe pagină (surse secundare).

Din rețeaua băncii, `facebook.com` a întors eroare de conexiune pe 25.09, deci **IT trebuie să facă o excepție de proxy**.

**Cost:** gratuit.

**Termenii:** n-am găsit o interdicție explicită a uzului comercial sau a analizei concurenței. Platform Terms cer însă ștergerea datelor când păstrarea lor *„is no longer necessary for a legitimate business purpose”*. Asta se bate cu regula proiectului „datele nu se aruncă”, deci trebuie o politică de retenție, prinsă în aviz. Pagina „Ad Library API Terms” n-am putut-o citi.

### 3. LinkedIn Ad Library API

**Ce e.** API-ul oficial al bibliotecii de reclame LinkedIn, confirmat de Help Center și de blogul de inginerie LinkedIn. Biblioteca are reclamele difuzate după 1 iunie 2023, păstrate un an după ultima afișare.

**Ce date dă:**
- creația (textul și previzualizarea), advertiserul și plătitorul, formatul;
- prima și ultima afișare, un interval de impresii;
- pentru UE: targetarea pe 12 categorii (limbă, funcție, industrie, companie, locație, vârstă, gen etc.).

**Nu dă cheltuieli.**

**Cum se lucrează:**
1. Facem o aplicație în LinkedIn Developer Portal.
2. În tab-ul Products cerem produsul „Ad Library API” și așteptăm aprobarea LinkedIn.
3. Autentificare OAuth 2.0 și cereri de căutare după cuvânt-cheie și advertiser.

Criteriile de eligibilitate, durata aprobării și limitele **nu sunt confirmate oficial**. Pagina de documentație LinkedIn ne-a răspuns pe 25.09 cu o blocare Cloudflare, pe care n-am ocolit-o. Developerii raportează și erori 404 chiar cu clientul oficial.

**Cost:** probabil gratuit, după sursele secundare; neconfirmat oficial.

**Termenii** (LinkedIn API Terms of Use, 13.12.2022):
- La eligibilitate se cere ca aplicația să **nu** folosească datele *„for the purposes of advertising”*. Nu e clar dacă monitorizarea reclamelor concurenței intră aici. **De lămurit în aviz înainte de cerere.** Dacă formularul cere să negăm un scop pe care îl avem, LinkedIn se exclude.
- §4.1: stocarea e permisă doar dacă datele se pot șterge selectiv și doar cât e necesar.
- §4.5: datele se șterg la încetarea accesului.
- §3.1: fără vânzare sau partajare către terți.

### 4. Microsoft Ad Library API (Bing)

**Ce e.** API-ul public al bibliotecii de reclame Microsoft Advertising, pentru reclamele afișate pe Bing în SEE din iunie 2023. **Nu cere cont.** Cu un *developer token*, tot gratuit, limitele sunt mai mari.

**Ce date dă:**
- titlul și **textul complet**;
- URL-ul afișat și cel de destinație;
- perioada, plătitorul;
- intervalul de impresii și ponderea pe țări;
- targetarea: vârstă, gen, locație, audiențe.

**Nu dă** cheltuieli, clicuri sau cuvinte-cheie. Datele apar cu 1–3 zile întârziere.

**Cum se lucrează:** se caută advertiserul, apoi reclamele lui filtrate pe țara RO (maximum 24 pe cerere, măsurat), apoi detaliile, câte o cerere pe fiecare reclamă.

**Ce am verificat pe 25.09.2026:** ~20 de cereri de test, cu ecusonul proiectului. Nimic nu a fost încărcat în bază.
- API-ul răspunde fără cont.
- **ING** are 20 de reclame livrate în România, **BT** 0.
- Raiffeisen apare ca „Raiffeisen Bank International”.

**Termenii: riscul cel mai mare dintre cele patru.**
- Documentația trimite la Microsoft Terms of Use (07.02.2022): *„Unless otherwise specified, the Services are for your personal and non-commercial use.”*
- Microsoft APIs Terms of Use (octombrie 2025) interzic, la 3.b.4, construirea de baze de date din datele API-ului, *„except as necessary to enable an intended usage scenario”*.
- Microsoft descrie biblioteca drept *„primarily intended for regulatory visibility rather than performance analysis”*.

**Îl folosim doar dacă avizul juridic permite uzul comercial.**

## Ce nu folosim și de ce

- **TikTok Commercial Content API.** Termenii limitează datele la cercetarea riscurilor (*„CCL Purposes”*), iar monitorizarea concurenței nu intră aici. A declara alt scop ar însemna să ocolim termenii. Rămâne consultarea manuală a `library.tiktok.com`, documentată.
- **YouTube Data API.** Dă doar videoclipurile de pe canalele băncilor, nu reclamele. Politicile cer ștergerea sau reîmprospătarea datelor la 30 de zile, ceea ce se bate cu „datele nu se aruncă”. Reclamele plătite de pe YouTube vin oricum prin Google (punctul 1).
- **Scraping pe site-urile bibliotecilor și „API-urile” neoficiale** (Apify, SerpApi și servicii similare). Imită browsere, ocolesc protecțiile și colectează în locul nostru. Toate trei sunt interzise de regulile proiectului.

## Cum arată rezultatul în aplicație

Pagina Campanii primește o secțiune „Reclame”. Schița de mai jos e **ilustrativă (mock)**, cu valori inventate:

```
Reclame active în RO · fotografie din <data>                         [MOCK]
bancă    platformă  format   prima → ultima afișare  text (unde există)         sursa
<banca>  Google     video    02.09 → 24.09           — (Google nu dă textul)    link ATC
<banca>  Meta       imagine  10.09 → activă          „Card nou, 0 lei…”         link Meta
<banca>  Bing       text     01.08 → 20.09           „Credit rapid…”            link Bing
```

Reclamele sunt o dimensiune separată de campaniile de pe site-urile băncilor și nu se adună cu ele.

## Cum procedăm

### Pașii

| pas | cine | ce | depinde de | efort [estimare] |
|---:|---|---|---|---|
| 1 | Juridic și conformitate | un **aviz unic** pe clauzele din secțiunea următoare | – | – |
| 2 | IT | proiectul Google Cloud al organizației (sandbox), cu acces pentru Nicolae | – | – |
| 3 | Nicolae | schema setului Google și dry-run-ul, **fără extragere de date** | 2 | parte din cele ~3 zile pentru Google |
| 4 | Nicolae | prima extragere Google, pe băncile din RO, salvată local | 1, 3 | ~3 zile în total, pentru Google |
| 5 | Nicolae; angajatul desemnat; IT | Meta: desemnarea angajatului, verificarea identității, excepția de proxy pentru `facebook.com`, aplicația și **un apel de test** | 1 | 2–3 zile, plus așteptarea verificării |
| 6 | Nicolae | LinkedIn: cererea produsului, cu scopul real declarat | 1 (clauza „advertising”) | ~1 zi după aprobare |
| 7 | Nicolae | Microsoft: extragerea | 1, doar dacă avizul permite | 0,5–1 zi |
| 8 | Robert | tabela pentru reclame în baza de date: o migrare nouă, după aviz; până atunci, fișiere locale în afara git | 1 | – |

Pașii 2 și 3 se pot face imediat, fiindcă nu ating date. Tot restul așteaptă avizul.

### Regulile de lucru, pentru cine implementează

1. **Reclama se leagă de bancă după țara de livrare (RO), nu după țara advertiserului.** ING apare ca ING Bank N.V. Amsterdam, iar Raiffeisen ca Raiffeisen Bank International. Pe fiecare bancă ținem lista tuturor grafiilor numelui.
2. **Păstrăm linkul spre biblioteca oficială**, dar nu descărcăm și nu randăm imaginile sau videoclipurile.
3. **Datele nu intră în git.** Până la migrare stau în `output/reclame/<platforma>_<data>.json`, cale ignorată de git; dintr-un istoric git nu se mai pot șterge selectiv. Dacă folosim `date/reclame/`, calea se adaugă în `.gitignore` în același commit.
4. **Ștergerea cerută de Meta și LinkedIn contrazice regula „datele nu se aruncă”.** Nicolae decide, cu avizul, o excepție scrisă și o politică de retenție pentru datele de reclame.
5. **Fotografie datată, nu monitorizare continuă.** Rulările periodice sunt înghețate în proiect, deci a doua fotografie se face manual. Bibliotecile păstrează reclamele un an după ultima afișare, așa că prima extragere prinde ultimul an.
6. **Orice cerere HTTP trece prin fluxul proiectului, cu ecusonul lui:** nume și contact, fără imitarea unui browser.
7. **Orice pachet nou** (de exemplu `google-cloud-bigquery`, dacă scriem cod pentru Google) intră în `requirements.txt` în același commit.

## Ce cerem, pe persoane

**Juridic și conformitate: un singur aviz, pe:**
1. **Google (Ads Transparency Center Additional Terms):** e permisă analiza internă a reclamelor altor bănci, având în vedere clauza *„You may not use that content… without the relevant customer's permission, or as otherwise allowed by law”*?
2. **Meta (Platform Terms):** ce politică de retenție satisface clauza de ștergere, *„no longer necessary for a legitimate business purpose”*? Mai sunt de citit „Ad Library API Terms” și implicațiile verificării identității unui angajat.
3. **LinkedIn (API Terms of Use):** monitorizarea reclamelor concurenței e un scop exclus de clauza *„for the purposes of advertising”*? Cum respectăm §4.1 (ștergerea selectivă) și §4.5 (ștergerea la încetare)?
4. **Microsoft (Terms of Use și APIs Terms of Use):** permit uzul comercial, dat fiind *„personal and non-commercial use”* și interdicția de a construi baze de date?

**IT:**
- proiectul Google Cloud al organizației: cine îl deține și cine are acces;
- excepția de proxy pentru `facebook.com`;
- cine deține conturile de developer (Meta, LinkedIn), ca să nu depindă de o singură persoană.

**Nicolae, decizii:**
- cine e angajatul care își verifică identitatea la Meta;
- politica de retenție pentru datele de reclame.

**Robert:**
- tabela de reclame, într-o migrare nouă, după aviz.

**De corectat în arhitectură (secțiunea 2.4):**
- Google **are** un set oficial, în BigQuery;
- TikTok iese, din cauza termenilor.

## Ce nu știm încă

- dacă Meta întoarce reclamele comerciale ale băncilor din România; o spune primul apel real;
- schema exactă a setului Google și costul real al interogării, pe care le arată dry-run-ul;
- cât de repede se actualizează setul Google și cât păstrează;
- condițiile exacte de acces și limitele LinkedIn;
- ce acoperă fiecare platformă la cele 30 de bănci. Pe 25.09 am verificat doar BT și ING la Google, și ING, BT și Raiffeisen la Microsoft.

## Surse

- Meta: [Ad Library API](https://www.facebook.com/ads/library/api) · [Ad Library tools, Transparency Center](https://transparency.meta.com/researchtools/ad-library-tools)
- Google: [Ads Transparency Center](https://adstransparency.google.com) și termenii lui suplimentari (text citit pe 25.09.2026) · [BigQuery sandbox](https://cloud.google.com/bigquery/docs/sandbox) · forumul Google Developer: [setul BigQuery](https://discuss.google.dev/t/bq-dataset-google-ads-transparency-center/185395), [date lipsă din set](https://discuss.google.dev/t/querying-public-google-ads-transparency-center-table-doesnt-show-all-the-needed-data/177804)
- LinkedIn: [Ad Library](https://www.linkedin.com/ad-library) · [problema cu `/rest/adLibrary` în clientul oficial](https://github.com/linkedin-developers/linkedin-api-python-client/issues/64) · LinkedIn API Terms of Use, 13.12.2022
- Microsoft: [Ad Library](https://adlibrary.ads.microsoft.com) · API: `https://adlibrary.api.bingads.microsoft.com/api/v1/` · [Microsoft Terms of Use](https://www.microsoft.com/en-us/legal/terms-of-use) · Microsoft APIs Terms of Use, octombrie 2025
- DSA: Regulamentul (UE) 2022/2065, art. 39 (registrele de reclame)
- Analiza completă, cu testul pe 4 bănci și restul secțiunii 2.4: `docs/NICOLAE_CHERASCU_MARKETING.md`, capitolul 4.2
