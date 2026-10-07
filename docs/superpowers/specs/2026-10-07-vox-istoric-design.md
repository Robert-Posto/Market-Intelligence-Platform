# Vox: istoricul conversațiilor

Data: 07.10.2026. Ramura `vox-chatbot`. Macheta aprobată: planșa „Propunere · istoricul
conversațiilor” din https://claude.ai/artifact/3vpGF9ShcqQ4uxGTydygf7.

## Ce vrea utilizatorul

Conversațiile cu Vox rămân după ce închide pagina și se pot redeschide și continua („și la ING?”
merge și a doua zi). Azi conversația trăiește doar în memoria paginii: un refresh o pierde.

Criterii de reușită:
- o conversație redeschisă arată exact ce a arătat atunci (valorile, citatele, documentele), cu
  data și ora fiecărei întrebări, fără niciun apel la model;
- o întrebare nouă într-o conversație redeschisă o continuă (ultima interpretare se reface) și se
  adaugă la ea;
- lista se vede pe pagina Vox, fără să caute nimeni unde e; conversațiile se pot șterge.

## Unde se păstrează: fișiere pe laptop, scrise de server

`loguri/vox/conversatii/<id>.jsonl`, un rând pe întrebare:
`{"data": "<ISO cu fus>", "intrebare": "...", "raspuns": {interpretare, ignorate, raspunsuri, model, tokeni, cost_usd}}`.
O redenumire e tot un rând adăugat, `{"data": "...", "titlu": "..."}` (ultimul câștigă; `null` =
înapoi la prima întrebare): fișierul doar crește, nu se rescrie niciodată.

- `id`: 16 caractere hex (`secrets.token_hex(8)`), generat de server la prima întrebare a unei
  conversații. Orice `id` venit din afară se verifică cu `^[0-9a-f]{16}$` înainte să atingă discul,
  deci nu poate ieși din folder.
- Se scrie doar o întrebare cu răspuns. O eroare (model, rețea, bază) nu intră în conversație; rămâne
  doar în jurnalul de costuri, ca azi.
- Scrierea e un `append` sub lacăt, ca la jurnal. `loguri/vox/` e deja în `.gitignore`.
- Nu se scrie în bază: regula „serverul e read-only” rămâne adevărată. Rândul despre Vox din
  `CLAUDE.md` spune în plus că Vox își păstrează conversațiile în `loguri/vox/conversatii/`.

Respinse:
- **browserul** (localStorage): se pierde la ștergerea datelor site-ului sau în alt browser, iar
  ~5 MB țin 10–20 de conversații cu tabelele lor (un răspuns are până la ~60 KB);
- **baza**: ar încălca regula read-only, iar baza se înlocuiește la reîncărcări (`mip` → `mip_merge`).

Istoricul începe gol: jurnalul de până acum are interpretarea și numărul de valori, nu răspunsurile
întregi.

## Server

`app/vox.py` primește o clasă `Istoric(dir)` (fără HTTP și fără SQL, ca restul modulului):
`lista()`, `citeste(id)`, `adauga(id, tura)`, `redenumeste(id, titlu)`, `sterge(id)`, `id_nou()`.
`Vox` o ține ca `self.istoric` (dosarul se dă în constructor, ca testele să lucreze într-un director
temporar). `lista()` ține minte rezumatul fiecărui fișier după `mtime` și mărime: un răspuns are până
la ~60 KB, iar lista se cere după fiecare întrebare.

`Vox.intreaba(intrebare, anterior=None, conversatie=None)`:
- `conversatie` dată: format valid și fișier existent, altfel `Respins("Conversația nu mai
  există.")` **înainte** de apelul la model (nimic plătit);
- `conversatie` lipsă: id nou;
- după răspuns: tura se adaugă la conversație, iar răspunsul conține `conversatie: <id>`.

Rute (în `Handler`, ca `/api/vox`, nu în `RUTE`):

| rută | protecție | răspuns |
|---|---|---|
| `GET /api/vox/conversatii` | Host/Origin, ca `GET /api/vox` | `[{id, titlu, redenumita, intrebari, texte, inceputa, ultima, cost_usd}]`, cea mai recentă prima |
| `GET /api/vox/conversatii/<id>` | Host/Origin | `{id, titlu, redenumita, ture: [{data, intrebare, raspuns}]}`; 404 dacă nu există sau `id` invalid |
| `POST /api/vox` | ca acum (token, Origin, JSON) | corpul primește `conversatie` opțional; răspunsul, `conversatie` |
| `POST /api/vox/conversatii/<id>/redenumeste` | ca `POST /api/vox` | corp `{titlu}` (text, cel mult 120 de caractere; gol = prima întrebare) → `{titlu, redenumita}`; 400 / 404 |
| `POST /api/vox/conversatii/<id>/sterge` | ca `POST /api/vox` | `{sters: true}`; 404 dacă nu există |

`titlu` = numele dat la redenumire, altfel prima întrebare (fără model, fără cost). `texte` = toate
întrebările conversației, pentru căutare. `ultima` = ora ultimei întrebări (redenumirea nu mută
conversația în listă). Lista și citirea nu depind de `MIP_PERMITE_VOX`: doar citesc fișiere locale.
Redenumirea și ștergerea trec prin aceleași verificări ca întrebarea (token, Origin,
`application/json`); fără Vox activ nu există token, deci istoricul rămâne doar de citit.

## Pagina

- **Coloana „Conversații”** în stânga chatului (~268 px), în pagina Vox, nu în bara laterală
  vișinie (care la 800 px înălțime depășește deja ecranul): „+ Conversație nouă” sus; grupe
  „Azi”, „Ieri”, „Mai vechi” după `ultima`; fiecare rând = titlul (cel mult 2 rânduri), dedesubt
  „N întrebări · ora”; cea deschisă marcată. Coloana rămâne pe ecran la derulare (sticky). Jos:
  „Salvate pe acest laptop. Redeschiderea nu cheamă modelul, deci nu costă nimic.”
- **Acțiunile unui rând** (vizibile la hover, la focus și pe rândul deschis): creion = redenumire pe
  loc (câmp în rând; Enter salvează, Esc renunță, gol = înapoi la prima întrebare); coș = ștergere cu
  confirmare (`Popconfirm`). Cât timp o întrebare așteaptă răspunsul, coloana nu schimbă conversația.
- **Căutarea**: câmpul „Caută în conversații” sub „+ Conversație nouă”. Caută în titlu și în toate
  întrebările, fără diacritice și fără majuscule; fiecare cuvânt trebuie să apară. Când potrivirea nu
  e în titlu, rândul arată dedesubt prima întrebare care se potrivește („↳ și la BRD?”). Fără
  rezultate: „Nicio conversație cu „…”.” Termenul stă în adresă (`cauta`), ca filtrele celorlalte
  pagini. Se caută în browser, în lista primită: nicio cerere în plus.
- **Sub ~1100 px lățime** coloana dispare și apare butonul „Istoric (N)” lângă chat, care o
  deschide într-un `Drawer`.
- **Deasupra chatului**, când e deschisă o conversație: titlul, „N întrebări · $cost · începută
  azi la 12:37”. Fiecare tură are ora ei („AZI, 12:37”).
- **Adresa**: `#/vox?c=<id>` (filtrele stau în adresă). Un link deschis citește fișierul, nu cheamă
  modelul, deci abaterea din 06.10 („conversația nu intră în adresă”) nu mai e necesară.
- **Conversație nouă**: golește chatul și scoate `c` din adresă. Prima întrebare primește id-ul de la
  server și îl pune în adresă fără să reîncarce conversația.
- **Continuarea**: `anterior` = ultima interpretare `cautare` din conversația deschisă (salvată sau
  nouă), ca azi.
- **Câmpul de jos** arată costul conversației (toate turele ei), nu al sesiunii.
- **Erori**: listă indisponibilă → o notă în coloană, chatul merge; conversație ștearsă sau `id`
  greșit în adresă → mesajul „Conversația nu mai există.” și chat gol; ștergerea conversației
  deschise → conversație nouă.

Fișiere: `shared/src/vox.ts` (scheme noi: `ConversatieRezumat`, `Tura`, `Conversatie`; răspunsul
la POST capătă `conversatie`), `web/src/api/vox.ts` (`useConversatii`, `citesteConversatia`,
`redenumesteConversatia`, `stergeConversatia`), `web/src/pages/vox/Conversatii.tsx` (coloana și
sertarul; „Istoric” e deja numele paginii „Istoric & schimbări”), `web/src/pages/Vox.tsx`,
`web/src/styles/vox.css`, `web/src/i18n/dict/vox.ts` (RO și EN; mesajele românești ale serverului,
identice în `server.vox.*`).

## Teste

Fără rețea, în `app/test_vox.py`:
- `Istoric`: adaugă și citește, lista ordonată după `ultima` cu titlu, număr, texte și cost;
  redenumire (ultima câștigă, gol = prima întrebare, peste 120 de caractere respins, nu mută
  conversația în listă); ștergere; `id` invalid (`../x`, majuscule, lungime greșită) respins fără să
  atingă discul; un rând stricat (scriere întreruptă) sărit, nu tot fișierul;
- `Vox.intreaba`: id nou întors și salvat; continuarea adaugă la același fișier; id inexistent →
  `Respins` fără niciun apel la clientul fals; o eroare a modelului nu intră în conversație;
- HTTP: lista, o conversație, 404, redenumirea și ștergerea cu și fără token, Origin străin refuzat,
  `id` cu `..` în adresă.

Interfața: typecheck, apoi capturi pe :5173 cu răspunsuri servite prin `page.route` (fără apeluri
plătite): coloana cu grupe, căutare cu și fără rezultate, redenumire, o conversație redeschisă și
continuată, conversație nouă, ștergere, ecran îngust cu sertarul, RO, EN și modul întunecat.

## În afara acestei lucrări

Reîmprospătarea valorilor cu datele de azi, istoricul pe mai mulți utilizatori (când Vox va merge pe
`mcc-test` cu autentificare). Redenumirea și căutarea au intrat la cererea utilizatorului (07.10.2026).
