# Pipeline-ul de colectare

Un singur drum pentru date, indiferent de sursă.

```
                    ┌─ citire pachet   (JSON gata extras de coleg)  ─┐
surse (tabelă) ──►  ├─ extractor HTML  (BS4 + parser_rate)          ─┼─► înregistrare
     ▲              ├─ extractor PDF   (parser_pdf / parser_tarife) ─┤     brută
     │              └─ extractor store (iTunes Lookup)               ─┘      │
     └── discovery LLM (claudeCrawl.py) propune URL-uri                      ▼
                                                                    normalizeaza.py
                                                                             │
                                                                             ▼
                                                                      observations
```

`router.py` decide ce extractor primește fiecare sursă. `normalizeaza.py` e
singurul loc care traduce o înregistrare brută în rânduri de bază.

> **Corectură.** O versiune anterioară a diagramei scria „extractor PDF
> (Playwright)" pe prima ramură. Era fals: ramura aceea **citește un JSON pe
> care pachetul colegului l-a produs deja**, nu extrage dintr-un PDF. Până la
> `din_pdf`, pipeline-ul nu putea procesa niciun document nou — de aceea 16
> bănci, printre care ING, Banca Transilvania, UniCredit și CEC, aveau zero
> comisioane în bază.

## Comenzi

```bash
python ingest/router.py --pas playwright     # citește pachetul colegului (JSON)
python ingest/router.py --pas bs4            # depozite, scraperul propriu
python ingest/router.py --pas descoperite    # BS4 peste URL-urile găsite de LLM (rețea)
python ingest/router.py --pas pdf            # comisioane din PDF-urile de tarife (rețea)
python ingest/router.py --pas tot            # toate, în ordine
```

Pașii auxiliari, care pregătesc sursele pentru `--pas pdf`:

```bash
python ingest/recolteaza_pdf_banci.py   # găsește și înregistrează PDF-urile de tarife
python ingest/cauta_app_id.py           # id-urile de App Store, pentru 2.3 și 2.7
```

## Extracția din PDF

Comisioanele unei bănci stau într-un PDF de tarife, iar un PDF nu se citește cu
BS4 — oricât de bine ai adus pagina. Corelația măsurată înainte de acest pas era
perfectă: comisioane în bază **exact** la băncile care aveau un PDF adus de
pachetul colegului, zero la restul.

`din_pdf` alege între cele două parsere ale colegului după **titlul din
conținutul documentului**, nu după numele fișierului:

| document | parser | de ce |
|---|---|---|
| formular standardizat prin Legea 258/2017 | `parser_pdf.extrage` | terminologie impusă prin lege, identică la toate băncile |
| listă de tarife nestandardizată | `parser_tarife.extrage_tarife` | geometrie liberă, mai zgomotos, dar singurul care o citește |

Diferența nu e cosmetică: pe același document BCR, parserul de formular dă 25 de
valori cu secțiuni completate, iar cel de tarife 29, dintre care prima e un rând
de glosar luat drept serviciu.

După parsare, fiecare valoare trece prin `vocabular.canonic()` — maparea la
conceptul canonic (`administrare_cont`, `retragere_numerar`, …). **Fără ea,
valorile ajung în găleata generică `comision` și nu apar în nicio comparație**:
prima rulare la ING a extras 1.603 valori corecte, toate invizibile pe 2.1 exact
din motivul ăsta. Ce nu se mapează rămâne `comision`, nu se ghicește, iar
denumirea băncii se păstrează în `serviciu`.

Rata de mapare, măsurată pe valorile în lei/eur/usd: **74,9%** pentru `pdf`,
față de 71,9% pentru pachetul colegului.

Fiecare pas e idempotent: șterge doar observațiile scrise de aceeași
proveniență, apoi rescrie. O rulare repetată nu dublează și nu pierde nimic.

## De ce arată așa

Înainte existau trei loadere separate, fiecare cu propria listă de intrare și
propria mapare la vocabularul canonic. Trei consecințe măsurate:

1. **196 de pagini de produs descoperite de LLM nu erau extrase de nimeni** —
   niciun script nu le avea în listă. `banca-transilvania` avea 13 surse
   descoperite și 0 observații.
2. Maparea tip-de-rată → produs, pragurile de plauzibilitate și construcția
   `cod_scenariu` existau în trei copii. O schimbare trebuia făcută în trei
   locuri.
3. Orice sursă nouă cerea un script nou.

## Proveniențe

| valoare | ce înseamnă | acoperire |
|---|---|---|
| `playwright` | PDF-uri oficiale de tarife + rate din HTML, pachetul colegului | 6.518 valori, 20 bănci |
| `bs4` | scraperul propriu, pe lista proprie de bănci — singurul care acoperă depozitele | 511 valori, 16 bănci |
| `bs4_llm` | același extractor BS4, dar pe URL-urile găsite de discovery | 184 valori, 19 bănci |

Cele trei acoperă bănci diferite, de-aia rulează toate. La depozite, `bs4` e
singurul care ajunge la `garanti`, `procredit`, `salt` și `vista`. `bs4_llm` e
singurul care aduce `bid`, `citibank` și `bankofchina`.

## Ce nu se poate lua, și de ce

**Bănci blocate de WAF (HTTP 403):** `banca-transilvania`, `cec`, `unicredit`,
`intesa`, `revolut`. Nu se forțează — proiectul nu ocolește WAF sau captcha.
Datele lor se pot lua doar cu browser real (extractorul Playwright), nu cu HTTP
simplu. Motivul e scris pe fiecare sursă în `surse.nota_extractie` și se vede
în pagina „Surse" la filtrul *încercate, blocate*.

**Bănci fără surse descoperite:** `bnpparibas`, `pko`, `banorient`. Aici
lipsește pasul de discovery, nu extracția.

## Dovada din spatele fiecărei cifre

Trei nivele, arătate diferit în interfață fiindcă nu sunt același lucru:

| nivel | ce înseamnă | cum apare |
|---|---|---|
| direct | documentul exact sau pagina web de unde s-a citit cifra | `↗ document.pdf p.4` |
| pagina băncii | pagina de pe care banca publică lista de tarife — **nu** documentul | `⌂ pagina băncii`, estompat |
| fără link | numele fișierului și pagina din PDF, verificabile manual | doar eticheta |

**De ce nu toate au link direct:** pachetul sursă reține doar calea locală a
documentului (`bcr/2c03037c_Tarif....pdf`) și pagina, nu URL-ul de la care a
fost descărcat, iar PDF-urile nu sunt incluse. Discovery-ul a găsit 40 de
URL-uri de PDF în total; 9 s-au potrivit exact. Măsurat: nu există mai mult de
potrivit, și zero URL-uri PDF clasificate greșit ca HTML. La prag mai permisiv
apăreau legături greșite (`Ghid_tarife_comisioane.pdf` se lega la
`Ghid_dobanzi_si_comisioane_credite.pdf`), iar un link care trimite la alt
document decât cifra e mai rău decât niciun link. Soluția completă cere o
rulare nouă de colectare, cu URL-ul înregistrat la descărcare.

Pentru restul se caută pagina de publicare, în doi pași:

```bash
python ingest/leaga_url_documente.py     # potrivire exactă document <-> URL descoperit
python ingest/leaga_pagina_tarife.py     # alege pagina de tarife din sursele deja știute
python ingest/gaseste_pagina_tarife.py   # caută pagina pe site-ul băncii, unde lipsește
```

Al treilea nu ghicește adrese: citește linkurile din paginile pe care le avem
deja pentru bancă, păstrează cele care arată ca pagini de tarife (după textul
ancorei sau după adresă) și acceptă un candidat doar dacă răspunde 200 **și**
conținutul menționează tarife sau comisioane. Orice pagină adăugată e o
afirmație verificată, nu o presupunere despre structura site-ului.

Al doilea are un prag minim de punctaj (`PRAG_MIN = 35`) tocmai ca să nu
accepte orice: fără el, Cetelem primea o pagină de tombolă promoțională și
Vista una despre agricultură, doar fiindcă discovery-ul le găsise.

## Istoric

`data_vigoare` și `stare_data` se **păstrează** la încărcare; filtrul e al
afișării (vederea `observatii_curente`). Prima versiune le arunca, și cu ele
se pierdeau 18 schimbări reale de preț — de exemplu BCR, transfer intrabancar
la ghișeu: **15 lei la 2024-06-14 → 30 lei la 2024-06-19**.

Vederea `schimbari_pret` le recalculează din observații, deci nu poate rămâne
desincronizată. Se vede în pagina „Istoric & schimbări".

## Praguri de plauzibilitate

Stau într-un singur loc, `normalizeaza.PRAGURI`, și sunt importate de API.
Fiecare are un motiv măsurat, nu presupus:

| prag | valoare | de ce |
|---|---|---|
| sumă | 10.000 lei | limitele de retragere (Libra, 20.000) și capitalul social al BCR (1,6 mld) ieșeau ca preț |
| depozite | 12% | TBI apărea cu „dobândă tipică 20%" din `LCP cu Taxa_depozit-scule` |
| credite | 30% | peste asta sunt penalități sau procente de alt fel |
| carduri | 40% | dobânda reală la cardul de credit ajunge la ~28% |

Ce depășește pragul nu se aruncă: se marchează `ambiguu`, se exclude din
comparații și apare în „Coadă de verificare" cu citatul din document.
