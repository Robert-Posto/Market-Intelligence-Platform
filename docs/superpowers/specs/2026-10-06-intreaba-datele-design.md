# „Întreabă datele”: chatbot minimal pentru căutarea de valori

> **Redenumit Vox** pe 06.10.2026, la cererea lui Nicolae: `app/vox.py`, `/api/vox`, `#/vox`, `MIP_PERMITE_VOX`, `MIP_VOX_MODEL`, `loguri/vox/`, cheile `vox.*` din `i18n`. Documentul păstrează numele de la scriere („Întreabă datele”, `intreaba`).

Design aprobat în discuție pe 06.10.2026 (Nicolae Cherascu). Ramura: `intreaba-datele`.

## Scop

O pagină în aplicație unde cineva din marketing scrie o întrebare simplă, în română sau engleză,
despre **o valoare** a unei bănci („Cât costă administrarea contului la BCR?”, „What is ING's
12-month deposit rate?”) și primește valorile din baza noastră, cu citatul și documentul fiecăreia.

Principiul: **modelul doar înțelege întrebarea, nu răspunde el.** Traduce textul în parametrii unei
căutări (bancă, concept, categorie, termen). Cifrele vin direct din `observatii_curente`, prin
aceeași funcție ca Sertar-ul din 2.1. Modelul nu vede nicio valoare și nu scrie nicio cifră.

## Ce nu intră

- Comparații și clasamente („cine are cel mai mic comision”), aplicații, recenzii, campanii,
  întrebări despre acoperirea datelor.
- Rularea pe `mcc-test.libra.bank`: serverul de test n-are autentificare, iar cheia ar fi
  folosibilă de oricine din rețea. Doar local, pe laptop.
- Istoricul conversației salvat în bază, conversația în adresă, limita zilnică de cost.
- Răspunsuri în proză scrise de model.

## Deciziile luate

| decizie | ales | de ce |
|---|---|---|
| tipul de întrebări | doar căutare de valori | minimal; comparațiile au deja paginile 2.1 / 2.2 |
| unde rulează | doar local, `MIP_PERMITE_INTREBARI=1` | `mcc-test` n-are login până la LDAP |
| abordarea | A: modelul interpretează, baza răspunde | nicio cifră scrisă de model; spre Anthropic nu pleacă valori, nici catalogul intern Libra |
| modelul implicit | `claude-haiku-4-5` | ales de Nicolae; schimbabil prin `MIP_INTREABA_MODEL` |

Variantele respinse: B (agent cu unelte, care scrie răspunsul în proză: rescrie cifrele și
primește valorile Libra din catalogul intern) și C (fără model, cu potrivire de cuvinte: fragil la
formulări).

## Arhitectura

```
pagina #/intreaba                               app/server.py  (doar ruta și verificările)
  întrebare ──POST /api/intreaba──►  app/intreaba.py
                                       1. contextul, construit din bază
                                       2. un apel Claude → interpretarea (JSON cu schemă strictă)
                                       3. validarea interpretării față de listele din bază
                                       4. valorile: celula(...) sau căutarea după text
  ◄── { interpretare, raspunsuri[], model, tokeni, cost }
  fișa de răspuns + „Vezi toate dovezile” → Sertar-ul existent (/api/celula), neschimbat
```

- `app/intreaba.py` stă lângă `app/rulari.py`. Nu știe de HTTP: primește întrebarea și
  interpretarea anterioară, întoarce un dicționar. Clientul Anthropic se poate înlocui în teste.
- `app/server.py` primește `GET /api/intreaba` (starea) și `POST /api/intreaba` (întrebarea).
- **Nicio scriere în bază.** Conversația stă în memoria paginii. Jurnalul e un fișier local (vezi
  „Cost și jurnal”).
- Serverul e `ThreadingTCPServer`, deci un apel la model de câteva secunde nu blochează celelalte
  pagini.

## Contractul cu modelul

### Ce primește

**Promptul de sistem**, fix cât timp datele nu se schimbă. Se construiește la prima întrebare și
se ține în memoria serverului; după o încărcare de date nouă se reface la repornirea serverului,
ca la orice modificare din `app/` (README o spune). Conține:

- rolul: traduce întrebarea într-o căutare; nu răspunde cu valori; nu folosește ce știe despre
  bănci; dacă întrebarea nu e despre o valoare a unei bănci, întoarce `in_afara`;
- băncile din `banci`: slug-ul și numele (30 la 06.10.2026);
- conceptele cu cel puțin o valoare numerică în `observatii_curente`, fără `comision` (127 la
  06.10.2026, baza `mip`). Fiecare are unitățile, categoriile (primul segment din `cod_scenariu`),
  numărul de valori și 2–3 denumiri reale ale băncilor (cele mai frecvente valori din `serviciu`).
  Exemplele vin din date, deci nu se dublează etichetele din `web/src/i18n/` și nici vocabularul
  din `crawler/vocabular.py`;
- valorile permise pentru `categorie` (cheile din `GRUPURI_RATE`), `termen` (cheile din `TERMENE`
  plus `necunoscut`) și `produs_credit` (cheile din `PRODUSE_CREDIT`), importate din constantele din
  `app/server.py` (un singur loc).

**Mesajul utilizatorului** conține întrebarea și, dacă există, interpretarea anterioară (JSON),
pentru continuări de tipul „și la BRD?”. Restul conversației nu se trimite.

### Ce întoarce

Răspuns prin `output_config.format` (JSON cu schemă strictă; Haiku 4.5 îl suportă):

```json
{
  "tip": "cautare | neclar | in_afara",
  "banci": ["bcr"],
  "concept": "administrare_cont",
  "categorie": null,
  "termen": null,
  "produs_credit": null,
  "text_cautat": null,
  "clarificare": null
}
```

- `banci` e o listă de `enum` generat din `banci.slug`. `concept` e `enum` generat din lista de
  concepte, sau `null`. API-ul nu acceptă astfel un slug inexistent.
- Modul strict nu acceptă constrângeri pe liste (`maxItems`), deci limita de **3 bănci** se aplică
  pe server: se iau primele 3, iar fișa spune că restul s-au ignorat.
- Schema se compilează o dată pe API și se ține în cache 24 de ore. Se schimbă doar când apare o
  bancă sau un concept nou.
- Haiku 4.5: fără `effort` (dă eroare pe acest model) și fără gândire extinsă. `max_tokens` mic
  (interpretarea are sub 200 de tokeni).

### Validarea pe server

Chiar dacă schema e strictă, serverul verifică din nou fiecare slug și fiecare `enum` față de
listele din bază. O interpretare care nu trece se tratează ca `neclar`, cu un mesaj fix.

## Ce face serverul, pe cazuri

| caz | ce se întâmplă |
|---|---|
| `cautare` cu `concept` | `celula(banca, concept, unitate='', scenariu=categorie, termen, produs)` pentru fiecare bancă (maximum 3) |
| `cautare` fără `concept`, cu `text_cautat` | căutare cu parametri (`ILIKE %s`) pe `serviciu` și `citat` în `observatii_curente`, pe banca respectivă, maximum 50 de rânduri; fișa spune „căutare după text în denumirile băncii, nu după un concept comparabil” |
| `cautare` fără bancă | se tratează ca `neclar` („La ce bancă te referi?”) |
| `neclar` | se afișează `clarificare`, textul scris de model |
| `in_afara` | mesaj fix din `i18n`: „Răspund doar la valori: o bancă și un comision sau o dobândă”, cu trei exemple pe care se poate da clic |
| zero valori | „Nu avem valori pentru X la banca Y.” Dacă toate sursele băncii sunt `blocat`, fișa adaugă că banca e documentată ca blocată (WAF sau `robots.txt`) |

- **Căutarea după text** acoperă cele 3.859 de valori rămase în `comision` (06.10.2026, baza
  `mip`), fără să le atribuie un concept (regula „un serviciu care nu se mapează rămâne
  `comision`”). Dacă se poate extinde o funcție existentă (de pildă `observatii`) fără să schimbe
  ce văd paginile actuale, se extinde; altfel se scrie o funcție nouă în `app/intreaba.py`, tot
  peste `observatii_curente` și tot cu parametri.
- **Valorile ambigue** apar în fișă separat, marcate, și nu intră în interval, ca în Sertar.
- **Singurul text scris de model care ajunge pe ecran e `clarificare`.** Rezumatul, cifrele și
  citatele vin din bază; formulările fixe vin din `i18n`.

## Ruta și securitatea

- `GET /api/intreaba` → `{activ, model, token}`. Exemplele de întrebări sunt texte de interfață și
  stau în `i18n`, nu vin de la server. `activ` e adevărat doar cu `MIP_PERMITE_INTREBARI=1`
  **și** cu o cheie `ANTHROPIC_API_KEY` care arată ca o cheie reală: începe cu `sk-ant-` și are
  lungimea unei chei, nu a unui placeholder (cel din `.env`-ul de acum are 10 caractere).
- `POST /api/intreaba` cu `{intrebare, anterior?}`. Refuzat dacă:
  - variabila lipsește (403);
  - `Content-Type` nu e `application/json`;
  - lipsește `X-MIP-Token` sau e greșit (același token aleator, generat la pornirea serverului,
    ca la rulări);
  - `Origin` (dacă e trimis) nu e `http://localhost:5173`, `http://localhost:8765` sau
    echivalentele lor `127.0.0.1` / `[::1]`;
  - întrebarea e goală sau are peste 500 de caractere.
- Spre deosebire de rulări, `localhost:5173` e permis, ca funcția să meargă și din `npm run dev`.
  Verificările de la `/api/rulari/*` **nu se ating**.
- Cheia se citește din `.env`-ul din rădăcină (prin `config.incarca()`). Acolo e acum un
  placeholder (jobul 172); pentru folosire trebuie pusă cheia reală. `fara_mediu` din
  `app/rulari.py` rămâne cum e.

## Interfața

Pagina `#/intreaba`, „Întreabă datele” / „Ask the data”, în grupul Analiză. Se construiește după
rețeta din CLAUDE.md: ruta în `App.tsx`, intrarea în `pagini.ts`, `i18n/dict/intreaba.ts`,
`shared/src/intreaba.ts` (+ export în `index.ts`), `api/intreaba.ts`, `pages/Intreaba.tsx`,
`styles/intreaba.css`.

- **Sus:** câmpul de întrebare și trei exemple pe care se poate da clic.
- **Dedesubt:** întrebările și răspunsurile, cele noi jos. Conversația stă doar în memoria paginii.
- **Fișa de răspuns:**
  - „Am înțeles: BCR · Administrare cont” (numele băncii din `useMeta`, eticheta conceptului din
    `camp.<slug>.eticheta`), ca o interpretare greșită să se vadă imediat;
  - rezumatul pe fiecare unitate: câte valori, intervalul fără cele ambigue, câte sunt gratuite;
  - primele 5 valori: serviciul, valoarea, frecvența, condiția, cu `LinkSursa` spre document;
  - „Vezi toate dovezile” deschide `Sertar` cu `{banca, camp, unitate, scenariu, termen, produs}`;
    câte un buton pe unitate, dacă sunt mai multe;
  - `Pill` „căutare după text” la răspunsurile fără concept;
  - jos, mărunt: modelul, tokenii, costul.
- **Antetul paginii:** costul total al sesiunii.
- **Abatere asumată de la „filtrele stau în adresă”:** conversația nu intră în adresă, fiindcă un
  link deschis ar porni un apel plătit. Dacă se cere mai târziu, intră în adresă doar
  interpretarea, care nu cere model.
- Datele băncilor (servicii, citate) nu se traduc. Textele românești de la server trec prin
  `deLaServer`.

## Erori

| situație | ce vede utilizatorul |
|---|---|
| funcția oprită (fără variabilă sau fără cheie reală) | avertisment ca în „Rulare manuală”, câmpul dezactivat |
| serverul de date oprit | mesajul existent `SERVER_OPRIT` |
| cheie greșită (401), limită de cereri (429), rețea, timeout de 30 s | mesaj clar; întrebarea rămâne în câmp, ca să poată fi retrimisă |
| `stop_reason` = `refusal` sau `max_tokens` | tratat ca `neclar`, nu ca o cădere |

SDK-ul reîncearcă singur de două ori la 429/5xx. Erorile se prind de la cea mai specifică
(`AuthenticationError`, `RateLimitError`, `APIStatusError`, `APIConnectionError`), nu cu o singură
clasă generală.

## Cost și jurnal

- Costul fiecărui răspuns se calculează din `usage` cu `extragere_produse_bancare/preturi.py`, care
  există deja și are `claude-haiku-4-5`. Nu se face o a doua listă de prețuri.
- Estimarea, nemăsurată încă: aproximativ 5.000 de tokeni de intrare pe întrebare, deci ~$0,005 cu
  Haiku 4.5. Promptul intră în cache abia de la 4.096 tokeni; dacă e sub, nu se pune în cache și
  nu forțăm. Cifra reală se măsoară la implementare și se scrie în README.
- Jurnal: `loguri/intreaba/AAAA-LL.jsonl`, câte un rând pe întrebare: data, întrebarea,
  interpretarea, numărul de rânduri găsite, modelul, tokenii, costul, eroarea. `loguri/intreaba/`
  intră în `.gitignore`, ca `loguri/rulari/`. Servește la evaluare (unde greșește interpretarea).
- Fără limită zilnică: rulează doar local, cu un singur utilizator.

## Teste și verificări

- `app/test_intreaba.py` (unittest, fără rețea, fără cheie, cu un client fals):
  - schema generată din liste (băncile și conceptele ca `enum`);
  - validarea: slug inexistent respins, mai mult de 3 bănci tăiate;
  - fiecare caz din tabelul de mai sus;
  - ruta: fără variabilă → 403, cheie placeholder → `activ` fals, alt `Origin` → refuz, alt
    `Content-Type` → refuz, fără token → refuz, întrebare prea lungă → refuz.
- Setul de evaluare `app/intreaba_exemple.json`: aproximativ 25 de întrebări reale cu
  interpretarea așteptată (RO și EN; „BT”, „ING”; continuări; comisioane fără concept; întrebări în
  afara scopului). `python app/eval_intreaba.py` le trimite modelului real și raportează câte sunt
  corecte și costul. **Costă bani** (estimat ~$0,15): se rulează o dată, cu acordul lui Nicolae, iar
  rezultatul măsurat și datat intră în README.
- `npm run typecheck && npm run build`; pagina deschisă în RO și EN, cu consola curată.
- `python app/verifica_pagini.py` (cu serverul pornit) și `python app/test_rulari.py`, fiindcă se
  atinge `app/server.py`.

## Documentație

- README: secțiunea „Întreabă datele” (variabila, cheia, modelul, costul măsurat, rezultatul
  evaluării).
- `.env.example`: `MIP_PERMITE_INTREBARI=0` și `MIP_INTREABA_MODEL=claude-haiku-4-5`.
- CLAUDE.md, la „Serverul e read-only”: `/api/intreaba` cheamă modelul doar cu
  `MIP_PERMITE_INTREBARI=1`, nu scrie în bază, iar cifrele nu vin niciodată de la model.
- Memoriile Serena (`cod/harta`, `web/sectiune_noua` dacă e cazul), după commit, cu
  `/actualizeaza-memoria`.

## Fișiere

| fișier | ce |
|---|---|
| `app/intreaba.py` | nou: contextul, apelul, validarea, căutarea |
| `app/server.py` | rutele `GET` / `POST /api/intreaba` |
| `app/test_intreaba.py`, `app/intreaba_exemple.json`, `app/eval_intreaba.py` | noi |
| `shared/src/intreaba.ts`, `shared/src/index.ts` | schema Zod |
| `web/src/api/intreaba.ts`, `web/src/api/client.ts` | cererea; `apiPost` se refolosește |
| `web/src/pages/Intreaba.tsx`, `web/src/styles/intreaba.css` | pagina |
| `web/src/App.tsx`, `web/src/pagini.ts`, `web/src/i18n/dict/intreaba.ts`, `web/src/i18n/dict/index.ts` | ruta, meniul, textele |
| `README.md`, `CLAUDE.md`, `.env.example`, `.gitignore` | documentația |

Nicio migrare, nicio dependență nouă: `anthropic` e deja în `requirements.txt`.

## De verificat la implementare

- Ce `Origin` și ce `Host` vede serverul când cererea vine prin proxy-ul Vite (`vite.config.ts`).
- Dimensiunea reală a promptului de sistem (tokeni) și dacă trece de pragul de cache al Haiku 4.5.
- Dacă o schemă cu ~130 de valori `enum` e acceptată de modul strict fără probleme de compilare.
- Ce concepte non-preț (de pildă `nume_produs`, `conditie`) rămân în listă: intră doar cele cu
  valori numerice.
