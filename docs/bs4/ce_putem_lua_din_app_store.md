# Ce putem lua din App Store (iOS), și cum

Bazat pe teste live (nu presupuneri) pe `itunes_lookup.py` + feed-ul RSS de review-uri, 2026-09-21. Două apeluri diferite, la două adrese diferite — nu e un singur API.

## 0. Mapare directă pe cerințele din PDF (secțiunea 2.3 „Aplicații mobile & digital")

Textul din PDF, punct cu punct, și ce acoperă efectiv cele două apeluri de mai jos:

| Cerință din PDF (citat) | Acoperit? | Unde, în acest document |
|---|---|---|
| „Versiuni + changelog (App Store / Play Store)" | 🟡 parțial — doar versiunea curentă | secțiunea 1 (`version`, `releaseNotes`); istoricul intră în secțiunea 4 |
| „Rating, distribuție note, volum review-uri în timp" | 🟡 parțial — ratingul agregat da, distribuția pe note nu | rating agregat: secțiunea 1; distribuție pe note: secțiunea 3 (nu există) + secțiunea 4 (aproximare) |
| „Screenshot-uri de store" | ✅ da | secțiunea 1 (`screenshotUrls`) |
| „+ walkthrough real pe device (feature matrix, onboarding, paywall)" | ❌ exclus deliberat, nu e o limită a API-ului | decis la brainstorming — fază ulterioară, nu ține de `itunes_lookup.py` |
| „Web: funcționalități de internet banking public-facing, demo-uri" | — nu se aplică aici | e alt track (scraping web, figura 2), nu API mobil — nu face parte din acest test |

Concluzie scurtă: din cele 3 puncte care țin efectiv de API-ul mobil (versiuni, rating/distribuție, screenshot-uri), **unul e complet acoperit** (screenshot-uri), **două sunt parțiale** (versiuni — doar curentă; rating — agregat da, distribuție pe note nu). Punctul de walkthrough pe device și cel de web nu sunt goluri ale acestui API, sunt pur și simplu alt scop.

## 1. Lookup API (`itunes.apple.com/lookup`) — un apel, gratuit, fără cheie

| Informație | Câmp | Notă |
|---|---|---|
| Nume aplicație | `trackName` | — |
| Dezvoltator/vânzător | `sellerName` | util ca să confirmăm că e chiar banca, nu o aplicație omonimă |
| Versiune curentă | `version` | doar curentă |
| Notă de lansare curentă | `releaseNotes` | doar versiunea curentă — des generic („bug fixes") |
| Rating agregat | `averageUserRating` | din TOATE rating-urile (cu sau fără text) |
| Volum total rating-uri | `userRatingCount` | idem |
| Preț | `price` / `currency` | — |
| Screenshot-uri oficiale de listing | `screenshotUrls` | de obicei 4-10 imagini |
| Icoană | `artworkUrl512` | — |
| OS minim necesar | `minimumOsVersion` | — |
| Link direct spre pagina din store | `trackViewUrl` | — |

## 2. Feed RSS review-uri (`itunes.apple.com/{țară}/rss/customerreviews/id=...`) — apel separat, per țară

| Informație | Câmp | Notă |
|---|---|---|
| Text review individual | `content.label` | doar dacă userul a scris text — rating-urile fără text nu apar aici deloc |
| Rating per review | `im:rating` | — |
| Versiune la momentul scrierii | `im:version` | semnal indirect de adopție, nu changelog |
| Data | `updated.label` | — |
| Autor | `author.name.label` | **nume real de afișare** — Apple NU îl anonimizează; pseudonimizarea (hash cu sare) trebuie făcută de noi la ingest, obligatoriu, nu opțional |

## 3. Ce NU putem lua deloc (nu există la niciun endpoint public al Apple)

- **Distribuție reală pe stele** (histogramă 1★-5★, din toate rating-urile) — nu există în niciun câmp JSON public. Apare doar randată vizual pe pagina web a App Store-ului, generată client-side.
- **Istoric complet de versiuni/changelog-uri trecute** — doar versiunea curentă.
- **Număr de descărcări/instalări** — nepublicat de Apple pentru aplicații ale altcuiva. Doar furnizori plătiți (Sensor Tower, data.ai) estimează asta.
- **Date demografice ale userilor**.
- **Android** — ambele apeluri de mai sus sunt exclusiv Apple; Android are nevoie de o sursă complet separată (scraping guvernat, ca-n figura 4).
- **Orice date post-login** (feature matrix, onboarding real) — exclus deliberat de la brainstorming, nu de la API.

## 4. Ce putem lua PARȚIAL, prin căutări/apeluri multiple

- **Text + rating-uri pe mai multe țări.** Un review scris pe storefront-ul „ro" nu apare pe „us" și invers — feed-ul e per țară. Testat pe trei bănci:

  | Bancă | Rating-uri totale (lookup) | Review-uri cu text pe „ro" (RSS) |
  |---|---|---|
  | Libra Internet Bank | 971 | 0 |
  | ING HomeBank | 125.844 | **0** |
  | BCR George Romania | 188.379 | 50 (maximul unei pagini) |

  Nu e o regulă simplă „bancă mică = 0". ING are de 129x mai multe rating-uri decât Libra și tot 0 review-uri cu text pe storefront-ul „ro" — deci disponibilitatea pare mai degrabă specifică fiecărei aplicații (poate ține de cum a fost publicată/legată de storefronturi), nu de popularitate. Pentru o imagine completă, trebuie interogate mai multe storefronturi (cel puțin ro + us + gb) și acceptat că, la unele bănci, tot ce obținem e 0, indiferent de câte țări încercăm.
- **Paginare limitată.** Fiecare pagină RSS are până la 50 de review-uri, până la ~10 pagini → maxim ~500 cele mai recente review-uri CU text. Nu există acces la istoric mai vechi de-atât.
- **Distribuție pe stele, dar aproximativă.** Se poate calcula o distribuție proprie din `im:rating`-urile adunate din toate review-urile cu text, de pe toate storefronturile — dar rămâne un eșantion (cei care au scris text), nu adevărul lui Apple (toate rating-urile). Eșantionul e mic și potențial nereprezentativ mai ales la bănci cu puține review-uri scrise.
- **„Volum review-uri în timp".** Nu vine dintr-un singur apel — se construiește din rulări zilnice repetate (fiecare zi = un snapshot nou, comparat cu cel de ieri), la fel ca restul platformei.

## Rezumat

| | Disponibil integral | Parțial / aproximativ | Deloc |
|---|---|---|---|
| Metadate aplicație (versiune, rating agregat, screenshot-uri) | ✅ | | |
| Text review-uri | | 🟡 doar unde există, per țară | |
| Distribuție pe stele | | 🟡 aproximată, nu reală | |
| Istoric versiuni | | | ❌ |
| Descărcări/instalări | | | ❌ |
| Android | | | ❌ (altă sursă) |
