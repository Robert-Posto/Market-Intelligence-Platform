# 04. Ce nu se poate și ce n-am putut

## Ce nu există în datele Google

- **Conținutul reclamei:** textul, imaginea, videoclipul.
- **Pagina spre care duce reclama,** numele campaniei, cuvintele-cheie, bugetul, clicurile.
- **Numărul exact de afișări.** Există doar trepte (0–1.000, 1.000–2.000, …, peste 10 milioane), publicate cu 90 de zile întârziere.

Doar din datele Google nu se poate deci spune **despre ce** e o reclamă. Filtrul „Crăciun 2025” din galerie ia reclamele pornite în sezon, iar primele patru afișate (video Revolut) n-aveau legătură cu Crăciunul.

## Ce nu merge tehnic

| ce | ce se întâmplă | cum am aflat |
|---|---|---|
| **Pagina reclamei, încadrată într-un iframe** în alt site, de exemplu în aplicația noastră | Google răspunde „403. That's an error… you do not have access to this page” | test de mână pe 29.09, cu `fisiere/test_iframe.html`: 3 reclame BCR, toate cu 403 |
| **Previzualizarea într-o fereastră mică** (`window.open`) | merge când galeria e deschisă local, din fișier, sau de pe un server intern. **Nu merge** când pagina rulează într-un cadru izolat, ca pe claude.ai: Google răspunde `ERR_BLOCKED_BY_RESPONSE` | test de mână pe 29.09, în ambele variante |
| **Descărcarea locală din consola BigQuery** | cel mult 10 MB pe fișier. Peste, rezultatul se salvează în Google Drive (până la 1 GB) și se descarcă de acolo | 30.09: 10,03 MB, prin Drive |
| **Un fișier mare, trimis unui asistent AI în chat** | conversația se blochează definitiv, cu „Prompt is too long” | 29.09: JSON de 8,5 MB atașat |

## Ce nu avem voie, după regulile proiectului

- **Să deschidem sau să citim automat paginile ATC:** nici cu Playwright, nici cu cereri HTTP, nici prin API-ul intern pe care îl folosește pagina ca să încarce reclamele. Ar fi scraping pe platforma de reclame, indiferent de ce spune `robots.txt`.
- **Să folosim servicii terțe care colectează în locul nostru,** cum sunt Apify, SerpApi sau „API-urile” neoficiale pentru ATC.
- **Să ocolim o blocare.** 403-ul de la iframe e o blocare, deci nu încercăm proxy sau alte trucuri.
- **Să punem datele în git sau în bază** înainte de aviz.

**O abatere, pe 25.09.** În cercetarea de dinaintea testului, un agent de verificare a deschis automat, cu Playwright și ecusonul MIP, pagina de termeni `adstransparency.google.com/terms`, ca să citească textul termenilor, care se încarcă doar prin JavaScript.
- N-a deschis nicio reclamă.
- `robots.txt` răspundea 404, deci nu exista nicio interdicție scrisă.
- Totuși, regula noastră exclude orice randare automată pe site-ul platformei, iar dovada `robots.txt` nu s-a salvat.
- De atunci, toate verificările pe site-ul ATC s-au făcut de mână, în browser. În testele din 29–30.09, orice cerere spre un site extern a fost blocată în Playwright.

## Limite ale datelor

| limită | măsurat |
|---|---|
| **Google păstrează doar ultimul an.** O reclamă iese din set la un an după ultima afișare | 29.09 → 30.09: au ieșit 27 de reclame cu ultima afișare pe 28.09.2025 |
| **Afișările vin cu 90 de zile întârziere** | numărate până la ultima zi din date minus 90; 3.593 de reclame n-au încă niciun număr |
| **Căutarea după nume aduce potriviri false** | GARANTI PREST, „Revolut” (RO) cu reclame Autovit, BCR Asigurări de Viață, bănci Raiffeisen germane, 151 de firme „Exim” |
| **Agențiile ascund banca** | BRD publică prin Sense8, unde „plătit de” e gol la toate cele 364 de reclame; reclamele BRD nu se pot separa automat |
| **Grupurile din alte țări** | RBI (747 de reclame, în germană) și alte 6 grupuri (513 reclame) sunt excluse. Limba reclamelor lor, în afară de RBI, n-am verificat-o |
| **Tema Google e aproximativă** | la reclama Raiffeisen `CR00542680405023653889`, setul spune „Finance”, iar pagina ATC „Mâncare și produse alimentare” |
| **„Doar în România” e o deducție** | nicio reclamă n-are sub 2 intrări de țară; presupunem că una e un total. Neconfirmat în documentația Google |
| **Setul poate fi incomplet** | Google avertizează pe forumul oficial că setul „may not have all of the data” |
| **Acoperirea e parțială** | 14 bănci din 30 găsite; vezi [03](03_REZULTATE.md) |

## Costul

- **O fotografie completă a costat 131 GB** (30.09), din bugetul gratuit de 1.024 GB pe lună. Costul nu scade cu filtrele, doar dacă scoți coloane.
- **Sandbox-ul folosit e pe un cont personal.** Pentru folosirea curentă trebuie un proiect Google Cloud al organizației, creat de IT.

## Juridic

Avizul pe termenii bibliotecilor de reclame nu e încă cerut (30.09). Întrebările pentru jurist sunt în documentul din `context/`, la „Ce cerem, pe persoane”. Pentru Google, clauza de lămurit e:

> „You may not use that content, including ads or any other information related to Google's customers' ads or ad campaigns, without the relevant customer's permission, or as otherwise allowed by law.”

Tot avizul trebuie să acopere și trimiterea capturilor sau a textelor de reclame către un furnizor extern de AI, dacă facem categorizarea descrisă în [05](05_URMEAZA.md).
