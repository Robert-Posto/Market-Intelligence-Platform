# Comparația comisioanelor între bănci

Generat de `scripts/unifica_comisioane.py`. Fiecare linie e un serviciu
canonic, un canal, o destinație, o monedă și un tip de valoare — altfel
s-ar compara lucruri diferite. Cifra e mediana, iar în paranteză
intervalul, când banca are mai multe valori pentru același serviciu.

Doar serviciile prezente la cel puțin 3 bănci: sub atât nu e o
comparație, e o observație despre o bancă.

## Cum se citește, și ce nu e aici

**Acoperire.** Din 5427 de comisioane extrase, 3550 (65%) s-au putut
mapa pe unul din cele 26 de concepte canonice. Restul sunt servicii
specifice unei singure bănci, sau valori a căror etichetă s-a pierdut la
extragere. Ele rămân în `comisioane_unificate.json`, nemapate — nu
ghicite.

**Maparea denumirilor e singurul pas din tot lanțul care nu se poate
verifica geometric** — e o judecată. Legea 258/2017 standardizează
structura formularului, nu formularea: doar 4 denumiri din 116 sunt
folosite de 3 bănci din 5. Verificată de mână pe 22 de valori luate la
întâmplare: **20 concepte corecte din 22**.

**Segmentul** (pf/pj/imm/pfa) se citește din numele documentului, deci e
determinist. Fără el s-ar compara prețuri pentru persoane fizice cu
prețuri pentru firme: la poprire, Libra are 20 lei la PF și 50 la PJ.
Unde scrie `-`, documentul nu spune.

**Semnul `?` de după o cifră** înseamnă că cel puțin una din valorile din
spatele ei nu poate fi atribuită. În același document, sub același serviciu,
banca are mai multe prețuri diferite și nimic nu spune care când se aplică —
pragul de sumă sau antetul coloanei s-a pierdut la extragere. Eximbank cere 0
lei pentru schimbarea PIN-ului la unele carduri și 2,5 la altele; tipul
cardului nu s-a citit. **Cifra e reală, dar nu e un răspuns complet.**

Valorile astea **rămân** în comparație. A le scoate ar însemna să aruncăm
prețuri adevărate fiindcă nu le știm eticheta.

**Cele două măsuri de eterogenitate.** O linie e o comparație doar dacă trec
amândouă, fiecare cu limita de 5×:

- **între** — de câte ori diferă cifrele afișate (medianele) între bănci. Peste
  limită, băncile nu vând același lucru la prețuri comparabile.
- **intern** — cea mai mare împrăștiere din interiorul unei singure bănci. Peste
  limită, celula aceea adună servicii diferite, iar mediana ei nu descrie nimic.

`max/min` pe toate valorile la comun nu răspunde la niciuna din întrebări: la
`livrare_card` dădea 3× și trecea linia, deși Salt cere 30–50 lei față de 0–15
la ceilalți.

## Linii de încredere (58)

Amândouă măsurile sub limită, deci mediana reprezintă ceva.

| serviciu | segm. | canal | dest. | mon. | tip | frecv. | rol | între | intern | libra | bcr | brci | brd | creditcoop | eximbank | garanti | procredit | raiffeisen | salt | tbi | techventures |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| administrare_cont | pf | - | - | - | gratuit | - | - | 1× | 1× | 0 |  | 0 |  | 0 |  | 0 |  |  | 0 |  | 0 |
| administrare_cont | pf | - | - | LEI | suma | anual | - | 4× | 1× | 0 | 240 | 60 |  | 60 |  |  | 0 |  | 0 |  |  |
| extras_de_cont | pf | - | - | LEI | suma | - | - | 4× | 2× |  | 2 (0.8–2) | 5 |  |  |  | 8 | 0 |  |  | 5 | 5 |
| incasare | pf | - | interbancar | LEI | suma | - | - | 1× | 1× | 0 | 0 | 0 |  |  |  | 6 | 0 | 0 |  |  |  |
| administrare_banking_distanta | pf | internet_banking | - | LEI | suma | anual | - | 1× | 1× | 0 |  | 0 |  | 60 |  |  | 0 |  | 0 |  |  |
| interogare_sold | pf | atm | - | LEI | suma | - | - | 2× | 1× |  | 0 (0–4.5) | 0 |  |  |  | 1 |  | 1 |  |  | 2 |
| poprire | pf | - | - | LEI | suma | - | - | 2× | 1× | 20 | 25 |  |  |  |  |  |  | 25 | 30 |  | 50 |
| administrare_banking_distanta | pf | internet_banking | - | LEI | suma | lunar | - | 1× | 1× |  |  | 0 |  | 5 |  |  | 0 |  |  |  | 5 |
| deschidere_cont | pf | - | - | - | gratuit | - | - | 1× | 1× | 0 |  | 0 |  |  |  | 0 |  |  | 0 |  |  |
| documentar | pj | - | - | - | procent | - | - | 2× | 4× | 0.15 (0.05–0.2)? | 0.125 (0.1–0.2) | 0.15 (0.1–0.2)? |  |  |  |  |  |  |  | 0.3 |  |
| documentar | pj | - | - | EUR | suma | - | min | 5× | 4× | 30 (25–75)? | 50 (25–100) | 75 (50–100)? |  |  |  |  |  |  |  | 150 |  |
| modificare_anulare | pj | - | - | EUR | suma | - | - | 1× | 3× | 20 (15–40) | 25 (20–30)? | 25 |  |  |  |  |  |  |  | 20 (20–50) |  |
| reemitere_card | pf | - | - | - | gratuit | - | - | 1× | 1× |  |  | 0 |  |  |  | 0 |  |  | 0 |  | 0 |
| retragere_numerar | pf | atm | - | LEI | suma | - | - | 2× | 1× | 2.5 | 0 | 1 |  |  |  |  | 0 |  |  |  |  |
| schimbare_pin | - | - | - | LEI | suma | - | - | 2× | 2× | 5 (0–5) |  |  | 10 (10–12)? |  | 0 (0–10)? |  |  |  |  |  | 10 |
| transfer_credit | pf | - | intrabancar | LEI | suma | - | - | 3× | 1× |  | 30 (0–30)? |  |  |  |  | 12.5 |  |  |  | 10 | 10 |
| transfer_credit | pj | - | - | EUR | suma | - | - | 2× | 5× | 25 (25–50) | 27.5 (20–35) | 32.5 (10–50) |  |  |  |  |  |  |  | 20 (15–20) |  |
| transfer_credit | pj | - | - | EUR | suma | - | min | 2× | 3× | 25 | 50 (50–75) | 50 (25–75) |  |  |  |  |  |  |  | 25 (15–50) |  |
| administrare_card | pf | - | - | - | gratuit | - | - | 1× | 1× |  |  | 0 |  |  |  | 0 |  |  | 0 |  |  |
| administrare_cont | pf | - | - | EUR | suma | anual | - | 1× | 1× | 0 |  | 36 |  |  |  |  | 0 |  |  |  |  |
| administrare_cont | pf | - | - | EUR | suma | lunar | - | 1× | 1× | 0 |  | 3 |  |  |  |  | 0 |  |  |  |  |
| administrare_cont | pj | - | - | LEI | suma | lunar | - | 4× | 3× | 10 (5–13) | 42.5 (25–60) |  |  |  |  |  |  |  |  | 10 |  |
| conversie_valutara | - | - | - | - | procent | - | - | 2× | 2× | 1 (0–2) | 2 |  |  |  | 2 |  |  |  |  |  |  |
| conversie_valutara | pf | - | - | - | procent | - | - | 1× | 1× |  | 2.5 | 2 |  |  |  |  |  |  | 1.8 |  |  |
| depunere_numerar | pf | - | - | - | gratuit | - | - | 1× | 1× | 0 |  | 0 |  |  |  | 0 |  |  |  |  |  |
| depunere_numerar | pf | - | - | LEI | suma | - | - | 1× | 1× | 0 |  | 0 |  |  |  |  | 0 |  |  |  |  |
| deschidere_cont | pj | - | - | - | gratuit | - | - | 1× | 1× | 0 | 0 | 0 |  |  |  |  |  |  |  |  |  |
| documentar | - | - | - | - | procent | - | - | 1× | 2× |  |  |  | 0.1 |  |  |  |  | 0.1 (0.1–0.2)? |  |  | 0.15 (0.1–0.25) |
| documentar | pf | - | - | - | procent | - | - | 1× | 4× | 0.15 (0.05–0.2)? | 0.1 |  |  |  |  | 0.15 (0.1–0.15) |  |  |  |  |  |
| documentar | pf | - | - | EUR | suma | - | max | 2× | 2× | 300? | 750 |  |  |  |  | 500 (500–1000) |  |  |  |  |  |
| documentar | pf | - | - | EUR | suma | - | min | 2× | 3× | 30 (25–75)? | 40 |  |  |  |  | 50 (45–50) |  |  |  |  |  |
| documentar | pj | - | - | - | procent | trimestrial | - | 2× | 1× |  | 0.15 | 0.25 |  |  |  |  |  |  |  | 0.25 |  |
| documentar | pj | - | - | EUR | suma | - | - | 2× | 4× | 40 (20–70) | 30 (25–80)? | 50 (25–50) |  |  |  |  |  |  |  |  |  |
| extras_de_cont | pj | swift | - | LEI | suma | lunar | - | 1× | 1× | 100 | 100 | 125 |  |  |  |  |  |  |  |  |  |
| incasare | pf | - | - | - | gratuit | - | - | 1× | 1× | 0 |  | 0 |  |  |  |  |  | 0 |  |  |  |
| incasare | pf | - | interbancar | - | gratuit | - | - | 1× | 1× |  |  |  |  |  |  | 0 |  |  | 0 |  | 0 |
| incasare | pf | - | interbancar | EUR | suma | - | - | 1× | 1× | 0 | 0 | 0 |  |  |  |  |  |  |  |  |  |
| incasare | pf | - | intrabancar | LEI | suma | - | - | 1× | 1× |  | 0 |  |  |  |  | 1 |  | 0 |  |  |  |
| incasare | pj | - | - | - | gratuit | - | - | 1× | 1× | 0 | 0 | 0 |  |  |  |  |  |  |  |  |  |
| incasare | pj | - | - | EUR | suma | - | - | 4× | 1× |  | 30 | 100 |  |  |  |  |  |  |  | 25 |  |
| interogare_sold | - | atm | - | LEI | suma | - | - | 5× | 1× | 0 (0–1) |  |  |  |  | 1 |  |  |  |  |  | 5 |
| interogare_sold | pf | atm | - | - | gratuit | - | - | 1× | 1× |  |  | 0 |  |  |  | 0 |  |  | 0 |  |  |
| modificare_anulare | pj | - | - | - | gratuit | - | - | 1× | 1× | 0 | 0 | 0 |  |  |  |  |  |  |  |  |  |
| plata_programata | pf | - | - | LEI | suma | - | - | 1× | 1× | 0 | 0 |  |  |  |  |  |  | 1.5 |  |  |  |
| poprire | pj | - | - | LEI | suma | - | - | 3× | 2× | 40 (30–50) | 50 | 18 |  |  |  |  |  |  |  |  |  |
| reemitere_card | - | - | - | EUR | suma | - | - | 5× | 1× | 2.5 (0–5) |  |  | 12 |  | 0 |  |  |  |  |  |  |
| refuz_plata | - | - | - | EUR | suma | - | - | 3× | 1× | 8 |  |  |  |  | 12 |  |  |  |  |  | 25 |
| retragere_numerar | pf | atm | extern | - | procent | - | - | 2× | 2× |  |  |  |  |  |  |  | 1 | 1.5 (1–2)? | 2 |  |  |
| retragere_numerar | pf | ghiseu | intrabancar | - | procent | - | - | 5× | 1× | 1 | 2.5 | 0.5 |  |  |  |  |  |  |  |  |  |
| retragere_numerar | pf | ghiseu | intrabancar | EUR | suma | - | min | 5× | 1× | 10 | 5.5 (5–6) | 2 |  |  |  |  |  |  |  |  |  |
| schimbare_pin | - | - | - | EUR | suma | - | - | 2× | 1× | 1 |  |  | 2.5 |  | 1 (0–2) |  |  |  |  |  |  |
| schimbare_pin | - | atm | - | LEI | suma | - | - | 2× | 1× |  |  |  | 2 |  | 0 (0–2.5)? |  |  |  |  |  | 5 |
| speze_swift | pf | swift | - | EUR | suma | - | - | 2× | 1× | 10 |  |  |  |  |  | 10 |  |  |  | 15 |  |
| transfer_credit | - | - | - | EUR | suma | - | - | 5× | 3× |  |  |  | 10 (10–30) |  |  |  |  | 25 |  |  | 50 (15–50) |
| transfer_credit | - | - | - | EUR | suma | - | max | 2× | 4× |  |  |  | 1250 (1000–1500) |  |  |  |  | 1500 (500–2000) |  |  | 750 (500–1000)? |
| transfer_credit | - | - | - | EUR | suma | - | min | 2× | 5× |  |  |  | 15 (10–50)? |  |  |  |  | 30 (30–50) |  |  | 35 (10–50)? |
| transfer_credit | pf | - | - | - | gratuit | - | - | 1× | 1× | 0 |  | 0 |  | 0 |  |  |  |  |  |  |  |
| transfer_credit | pj | - | - | EUR | suma | - | max | 5× | 1× | 300 | 1500 | 550 |  |  |  |  |  |  |  |  |  |

## Linii prea eterogene (45)

Coloanele **între** și **intern** spun care măsură a depășit limita, deci ce e de reparat: `între` mare cere o cheie mai fină (de obicei destinația, nescrisă în document), `intern` mare cere etichete mai bune. Intervalul e informativ, mediana **nu**.

| serviciu | segm. | canal | dest. | mon. | tip | frecv. | rol | între | intern | libra | bcr | brci | brd | creditcoop | eximbank | garanti | procredit | raiffeisen | salt | tbi | techventures |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| administrare_cont | pf | - | - | LEI | suma | lunar | - | 4× | 7× | 0 | 11.99 (0–20) | 5 |  | 5 (5–8) |  | 7.5 | 10 (0–50)? |  | 0 | 3 | 6.5 (0–36) |
| transfer_credit | pf | - | - | - | procent | - | - | 3× | 140× | 0.1 | 0.175 (0.1–13.99)? | 0.1 |  |  |  | 0.25 |  | 0 |  | 0.165 (0.1–0.18) | 0.3 (0.15–1.8)? |
| transfer_credit | pf | - | - | EUR | suma | - | - | 3× | 2083× | 50 | 17.5 (0–35) | 50 (25–50) |  |  |  | 25 (2–35) |  | 25 |  | 30 (12–25000)? | 50 (15–50) |
| transfer_credit | pf | - | - | LEI | suma | - | - | 10× | 111111× | 3 (0.45–50000)? | 4 (0–30)? | 5 (1–250)? |  |  |  | 30 (15–45) | 0 |  |  | 6 (0.51–50)? | 10 (0.45–200)? |
| modificare_anulare | pf | - | - | EUR | suma | - | - | 2× | 6× | 20 (15–40) | 12.5 (10–15) | 27.5 (5–30) |  |  |  | 25 |  |  |  | 25 (20–50) | 30 |
| modificare_anulare | pf | - | - | LEI | suma | - | - | 18× | 30× | 50 (20–66.3) | 18.15 (0–36.3) | 77.5 (5–150) |  |  |  |  | 89 |  |  | 5 | 20 |
| retragere_numerar | pf | - | - | - | procent | - | - | 44× | 5× | 2 | 2.5 | 0.5 |  |  |  | 0.5 (0.5–2) |  | 22 (5–26)? |  |  | 1 (1–2.5) |
| transfer_credit | pf | - | - | EUR | suma | - | min | 6× | 5× | 25 | 30 (10–50)? | 5 |  |  |  | 20 |  |  |  | 25 (25–50) | 20 (10–20)? |
| administrare_cont | pf | - | - | LEI | suma | - | - | 5× | 7× | 3 | 15 (0–100) | 5 |  |  |  | 7.5 |  | 0 |  |  |  |
| emitere_card | - | - | - | LEI | suma | - | - | 10× | 15× | 20 (0–150) | 100 |  |  |  | 0 |  |  | 10 |  |  | 25 |
| emitere_card | pf | - | - | LEI | suma | - | - | 4× | 60× | 20 (0–20) | 20 (0–600)? | 10 (0–10) |  |  |  |  | 0 |  |  |  | 37.5 (25–50) |
| incasare | pf | - | - | LEI | suma | - | - | 57× | 200× | 50.25 (0.5–100) | 0.88 |  |  |  |  | 10 | 0 |  |  | 20 |  |
| transfer_credit | pf | - | - | EUR | suma | - | max | 7× | 2× | 300 | 750 (500–1000)? |  |  |  |  | 2000 |  |  |  | 2000 | 750 (500–1000)? |
| transfer_credit | pf | - | interbancar | LEI | suma | - | - | 29× | 67× | 3 (1–20) | 3.255 (0.51–6) | 5.5 (0.45–30) |  |  |  | 15 (15–30) |  | 0.51? |  |  |  |
| deschidere_cont | pf | - | - | LEI | suma | - | - | 9× | 33× | 150 | 22.5 (0–500) |  |  |  |  |  |  | 0 |  |  | 200 |
| extras_de_cont | - | - | - | LEI | suma | - | - | 2× | 8× |  |  |  | 10 (3–25) |  | 0 |  |  | 20 |  |  | 10 |
| incasare | pf | - | - | EUR | suma | - | - | 6× | 1× | 25 |  | 5 |  |  |  |  | 0 |  |  | 30 |  |
| livrare_card | pf | - | - | LEI | suma | - | - | 5× | 2× |  | 15 (0–15)? |  |  |  |  |  |  | 7.5 (0–15) | 40 (30–50) |  | 20 |
| reemitere_card | - | - | - | LEI | suma | - | - | 15× | 45× | 2.5 (0–25) |  |  | 17.5 (10–450)? |  | 0 (0–15)? |  |  |  |  |  | 37.5 (25–50) |
| retragere_numerar | pf | - | - | LEI | suma | - | min | 5× | 10× |  | 30 |  |  |  |  | 10 |  | 10? |  |  | 50 (5–50) |
| transfer_credit | - | - | - | - | procent | - | - | 8× | 3× |  |  |  | 0.175 (0.15–0.2)? |  | 1 |  |  | 0.125 (0.1–0.15) |  |  | 0.15 (0.1–0.3)? |
| transfer_credit | - | - | - | LEI | suma | - | - | 8× | 98039× |  |  |  | 30 (6–30)? |  | 5 |  |  | 37.5 (0.51–50000)? |  |  | 11 (0.45–200)? |
| transfer_credit | pj | - | - | - | procent | - | - | 28× | 167× | 0.1 | 2.75 (0.15–25) | 0.175 (0.1–0.2)? |  |  |  |  |  |  |  | 0.1 (0.1–0.15) |  |
| transfer_credit | pj | - | - | LEI | suma | - | - | 4× | 250× | 4 (0.45–75)? | 16 (10–79) | 18 (5.5–50)? |  |  |  |  |  |  |  | 7 (0–999.99) |  |
| administrare_card | - | - | - | LEI | suma | - | - | 2× | 6× | 0 | 200 |  |  |  |  |  |  | 100 (50–300) |  |  |  |
| administrare_card | pf | - | - | LEI | suma | - | - | 36× | 800× |  | 14 (0–1200) | 40 |  |  |  |  |  | 500 (25–2000)? |  |  |  |
| administrare_card | pf | - | - | LEI | suma | lunar | - | 6× | 3× | 4 (0–8) | 22.5 (0–45) |  |  |  |  |  |  |  |  |  | 10 (5–15) |
| administrare_cont | - | - | - | LEI | suma | - | - | 60× | 10× |  |  |  | 450 |  | 7.5 (0–20)? |  |  | 10 |  |  |  |
| depunere_numerar | pf | - | - | - | procent | - | - | 20× | 1× | 10 | 1 | 0.5 |  |  |  |  |  |  |  |  |  |
| depunere_numerar | pf | - | - | EUR | suma | - | - | 1× | 17× | 0 |  | 10 (3–50) |  |  |  |  | 0 |  |  |  |  |
| deschidere_cont | pj | - | - | LEI | suma | - | - | 15× | 13× | 150 | 84.5 (15–199)? |  |  |  |  |  |  |  |  | 10 |  |
| documentar | - | - | - | EUR | suma | - | max | 3× | 8× |  |  |  | 1000 |  |  |  |  | 500 (500–750) |  |  | 1500 (200–1500) |
| documentar | - | - | - | EUR | suma | - | min | 2× | 7× |  |  |  | 50 |  |  |  |  | 75 (30–200)? |  |  | 50 (25–50) |
| extras_de_cont | pj | - | - | LEI | suma | - | - | 10× | 1× | 50 | 5 |  |  |  |  |  |  |  |  | 10 |  |
| file_cec | pf | - | - | LEI | suma | - | - | 3× | 18× | 6 (1.5–6) | 5.275 (0.55–10) |  |  |  |  | 2.21 (2–2.42)? |  |  |  |  |  |
| file_cec | pj | - | - | LEI | suma | - | - | 7× | 33333× | 6 (1.5–50000)? | 7.5 (6–10) | 1.1 |  |  |  |  |  |  |  |  |  |
| incasare | - | - | - | LEI | suma | - | - | 230× | 80× |  |  |  | 202.5 (5–400) |  |  |  |  | 4 (0–16)? |  |  | 0.88 (0.51–6) |
| incasare | pf | - | - | - | procent | - | - | 7× | 1× | 0.2 | 1 | 0.15 |  |  |  |  |  |  |  |  |  |
| interogare_baze_date | pj | - | - | LEI | suma | - | - | 2× | 8× | 11 (5–40)? | 9 (8–10) | 17.5 (5–30) |  |  |  |  |  |  |  |  |  |
| modificare_anulare | - | - | - | EUR | suma | - | - | 40× | 2× |  |  |  |  |  | 1 (0–2) |  |  | 40 (30–50) |  |  | 25 (25–30) |
| modificare_anulare | - | - | - | LEI | suma | - | - | 11× | 10× |  |  |  |  |  | 5 (0–20) |  |  | 55 (10–100) |  |  | 20 |
| modificare_anulare | pj | - | - | LEI | suma | - | - | 20× | 5× | 100 (20–100) |  | 5 |  |  |  |  |  |  |  | 5 |  |
| reemitere_card | pf | - | - | LEI | suma | - | - | 3× | 6× |  |  | 25 (5–30) |  |  |  |  |  | 70 (0–100) |  |  | 50 (25–50) |
| retragere_numerar | - | atm | - | LEI | suma | - | min | 5× | 25× |  | 10 |  |  |  | 2 |  |  | 3 (3–75) |  |  |  |
| retragere_numerar | pf | atm | - | - | procent | - | - | 1× | 6× | 0.5 (0.2–0.75) |  |  |  |  |  | 0.725 (0.2–1.25) |  | 0 |  |  |  |

