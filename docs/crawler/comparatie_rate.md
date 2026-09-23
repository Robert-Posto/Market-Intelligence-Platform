# Comparația ratelor și dobânzilor între bănci

Generat de `scripts/compara_rate.py`. Perechea tabelului de comisioane
([comparatie_comisioane.md](comparatie_comisioane.md)).

Fiecare linie e un produs canonic, un segment de clienți, un tip de rată,
**felul** ei (fixă / variabilă) și o monedă. Cifra e mediana, iar în
paranteză intervalul.

**Semnele din celule:**

| | |
|---|---|
| `⚠` | cel puțin o valoare vine dintr-o pagină cu **sursă învechită**, depistată la validarea încrucișată cu BNR |
| `†` | rată **derivată**: marja publicată de bancă plus indicele în vigoare. Banca nu a publicat cifra asta în forma asta. `(†)` = doar unele valori din celulă sunt derivate |
| `↓` | toate valorile băncii sunt de forma „**de la** X%” — capătul de jos al unui interval, cel mai bun caz pentru cel mai bun client, nu prețul obișnuit |

**Felul rătei nu e un detaliu.** O rată fixă de 5,49% și una variabilă de
7,71% nu sunt același produs, iar fără axa asta tabelul le punea pe același
rând — vezi secțiunea despre conversia marjelor.

## Cum se citește, și ce nu e aici

**Acoperire.** Din 1015 de valori extrase din web, 745 (73%) s-au putut mapa pe unul din cele 18
produse canonice. Restul vin din pagini care nu numesc un produs anume
(„Carduri persoane fizice”, „Compare Revolut plans”).

**Maparea e o judecată, nu o măsurătoare** — la fel ca la comisioane, dar
aici e mai greu: pe comisioane aveam secțiunile impuse prin Legea
258/2017 ca axă comună, la rate nu există nicio lege care să
standardizeze ceva. Din 185 de denumiri de pagină, doar 4 sunt folosite
de mai mult de o bancă. Ce salvează situația e că produsele sunt uniforme
ca *concept*: „Expresso” la BRD, „Libra Way” la Libra și „creditul
Econom” la Patria sunt toate credite de nevoi personale.
Verificată de mână pe 20 de valori: **18 produse corecte din 20**.

**Ce am scos deliberat:**

- **promoțiile „rate fără dobândă”** (78 de valori) — sunt „3 rate cu 0%
  dobândă” la comerciant, nu rata unui produs de creditare. Ar fi apărut
  în tabel ca dobândă 0%.
- **cashback-ul** — e un beneficiu, nu un cost.
- **valorile indicilor de piață** (IRCC, ROBOR, EURIBOR) — sunt aceeași
  cifră publicată de BNR pentru toată lumea. Diferența dintre bănci nu
  măsoară oferta, măsoară cât de veche e pagina; ea e în raportul de
  validare, nu aici. Marja *peste* indice, în schimb, e ofertă și rămâne.

## Linii de încredere (14)

Valorile variază de cel mult 8 ori între bănci.

| produs | segm. | tip rată | fel | mon. | între | intern | libra | bcr | bcrlocuinte | brci | brd | cetelem | credex | eximbank | garanti | ing | nexent | patria | procredit | raiffeisen | revolut | salt | tbi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| credit_ipotecar | pf | nominala | variabila | LEI | 2× | 2× | 7.71 (7.71–8.31) (†) | 7.86 (7.66–7.86) † |  |  | 8.03 (7.66–8.21) † |  |  | 4.99 |  | 8.05 † |  | 6.304 (4.768–8.46) | 7.66 (4.89–8.06) (†) | 7.56 (4.9–7.66) (†) ↓ |  |  |  |
| credit_nevoi_personale | pf | nominala | fixa | LEI | 2× | 3× | 7.81 | 9.49 (6.29–14.99) |  |  | 6.095 (5.7–6.49) ↓ |  |  |  |  | 10.99 (5.99–15.99) |  | 9.33 | 9.9 (7.4–12.4) | 5.95 (5.95–18.35) |  | 5.49 ↓ |  |
| credit_ipotecar | pf | marja_ircc | variabila | LEI | 1× | 1× | 2.15 (2.15–2.75) | 2.3 (2.1–2.3) |  |  | 2.47 (2.1–2.65) |  |  |  |  | 2.49 |  |  | 2.15 (1.99–2.5) | 2.1 (1.9–2.1) ↓ |  |  |  |
| refinantare | pf | nominala | fixa | LEI | 2× | 3× |  | 7.995 (5.79–14.99) |  |  | 5.7 ↓ |  |  |  |  | 4.5 |  |  | 5.89 | 5.95 (5.95–18.35) |  | 5.49 ↓ |  |
| credit_nevoi_personale | pf | nominala | - | - | 3× | 7× |  | 9.49 |  |  |  |  | 18 |  |  |  |  | 8.73 (3.5–22.8) |  | 5.95 ↓ |  |  |  |
| depozit_termen | pj | nominala | - | EUR/RON/USD | 3× | 4× | 5.75 (5.25–6.22) | 5 |  |  |  |  |  |  |  | 5.1 |  | 2 (1–4) |  |  |  |  |  |
| card_credit | pf | nominala | - | LEI/RON | 1× | 2× |  |  |  |  | 21.45 (16.9–26) | 0 |  |  |  |  |  |  |  | 0 |  |  |  |
| cont_curent | pj | nominala | - | EUR | 2× | 1× | 1 |  |  |  |  |  |  |  |  |  |  |  | 2 |  | 1.935 (1.86–2.01) |  |  |
| cont_economii | pj | nominala | - | EURO/LEI/RON | 2× | 3× |  |  |  |  |  |  |  |  |  |  |  |  | 5 (1.6–5.4) |  | 4 | 2.5 (0–4) |  |
| credit_ipotecar | pf | dae | - | LEI | 1× | 2× |  |  | 5.98 |  |  |  |  |  |  |  | 8.97 (8.81–9.13) | 7.5 (5.49–8.91) |  |  |  |  |  |
| descoperit_cont | pf | marja_ircc | variabila | - | 2× | 1× | 4.5 |  |  |  |  |  |  |  | 7.98 |  |  |  |  | 4.99 |  |  |  |
| descoperit_cont | pf | nominala | variabila | - | 1× | 1× | 10.06 † |  |  |  |  |  |  |  | 13.54 † |  |  |  |  | 10.55 † |  |  |  |
| noua_casa | pf | nominala | variabila | - | 4× | 1× | 7.84 |  |  |  | 7.56 † |  |  |  |  | 2 |  |  |  |  |  |  |  |
| refinantare | pf | nominala | variabila | - | 2× | 2× |  |  |  |  | 7.66 (4.65–7.66) (†) |  |  |  |  |  |  | 17.515 (12.23–22.8) |  | 7.46 † ↓ |  |  |  |

## Linii prea eterogene (5)

Aici s-au amestecat oferte prea diferite sub același produs — de obicei pentru că pagina dă un interval larg, sau un exemplu reprezentativ alături de rata reală. Intervalul e informativ, mediana **nu**.

| produs | segm. | tip rată | fel | mon. | între | intern | libra | bcr | bcrlocuinte | brci | brd | cetelem | credex | eximbank | garanti | ing | nexent | patria | procredit | raiffeisen | revolut | salt | tbi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| depozit_termen | pf | nominala | - | EUR/EURO/LEI/RON/USD | 28× | 27× | 5.125 (1.95–6.22) | 0.8 (0–6) |  |  | 5.6 |  |  | 6.75 (2.5–7.2) |  | 5.5 (0.7–10) | 6.25 (0.25–6.75) |  |  | 5.2 (2.5–6.4) | 5.5 |  | 22.5 (0–35) |
| credit_ipotecar | pf | nominala | fixa | LEI | 10× | 1× |  | 4.99 (4.79–4.99) | 5 |  | 7.75 ↓ |  |  |  |  | 0.8 | 8.31 |  |  | 4.7 ↓ |  |  |  |
| cont_curent | pf | nominala | - | LEI | 200× | 1× |  |  |  | 0 (0–2) |  |  |  |  |  | 10 (8–10) | 1.2 | 0.05 | 5.3 |  |  |  |  |
| cont_economii | pf | nominala | - | LEI/RON | 40× | 15× |  | 0.2 |  |  |  |  |  |  |  | 8 (1–10) |  | 0.5 (0–0.75) | 3 (0.2–3) |  | 5.5 |  |  |
| credit_ipotecar | pf | nominala | - | LEI | 13× | 292× |  |  |  |  | 8.79 (0.033–9.65) |  |  |  |  | 7.34 (4.79–9.89) |  | 1.25 (1–1.5) | 0.7 | 4.7 ↓ |  |  |  |

