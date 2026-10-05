# 03. Ce arată datele

Toate cifrele vin din fotografia din 30.09 (`fisiere/date/atc_ro_2026-09-30.csv`, ultima zi din date 29.09.2026) și se refac cu:

```
python fisiere/analiza_atc.py fisiere/date/atc_ro_2026-09-30.csv
```

## Acoperirea: 14 bănci din 30

| situație | bănci |
|---|---|
| **Găsite și numărate (14)** | Banca Transilvania, ING, BCR, Raiffeisen, Revolut, Nexent, CEC, TBI, Salt, Libra, UniCredit, Garanti, Patria, Intesa Sanpaolo (prin agenție) |
| **Găsită, dar nenumărată (1)** | BRD: publică prin agenția Sense8, unde „plătit de” e gol. Căutarea de mână după `brd.ro` pe site-ul ATC arată 4 reclame în RO |
| **Negăsite (15)** | Vista, Exim, ProCredit, Citi, BNP Paribas, Creditcoop, BID, Bank of China, Credex, TechVentures, BRCI, BCR Banca pentru Locuințe, Cetelem, Banorient, PKO |

Motivele pentru care cele 15 lipsesc nu sunt măsurate, doar probabile:
- **Citi, BNP Paribas, Bank of China, BID și PKO** lucrează mai ales cu firme. Analiza din 28.09 le scosese din scop și pentru colectarea de pe site.
- **Celelalte** sunt bănci mici sau de nișă, care probabil nu fac reclame Google, sau le fac prin agenții fără „plătit de”, ca BRD.
- **Grupurile lor din alte țări apar,** dar sunt excluse, fiindcă reclamele lor nu par făcute pentru piața din România. RBI, de exemplu, are reclame în germană.
- **Setul Google poate fi incomplet.** Google avertizează singur despre asta.

## Pe bănci

| bancă | reclame în ultimul an | active în ultimele 7 zile | noi în ultimele 30 de zile | text / imagine / video | prima afișare | afișări până la 01.07.2026, mil. |
|---|---:|---:|---:|---|---|---:|
| bt | 10.246 | 1.236 | 1.286 | 2.219 / 5.417 / 2.610 | 31.03.2025 | 180–216 |
| ing | 2.039 | 451 | 270 | 359 / 1.352 / 328 | 01.03.2023 | ≥ 400 |
| bcr | 1.383 | 248 | 124 | 536 / 336 / 511 | 06.03.2025 | 264–307 |
| raiffeisen | 933 | 87 | 50 | 314 / 289 / 330 | 11.03.2024 | ≥ 385 |
| revolut | 868 | 341 | 38 | 315 / 12 / 541 | 01.03.2023 | ≥ 538 |
| nexent | 297 | 46 | 11 | 176 / 74 / 47 | 01.03.2023 | ≥ 54 |
| cec | 202 | 17 | 0 | 59 / 62 / 81 | 22.10.2025 | 9–11 |
| tbi | 193 | 15 | 4 | 70 / 67 / 56 | 12.05.2025 | 54–62 |
| salt | 191 | 71 | 2 | 52 / 61 / 78 | 04.04.2024 | ≥ 196 |
| libra | 153 | 16 | 1 | 66 / 60 / 27 | 18.12.2024 | 4–5 |
| unicredit | 118 | 33 | 8 | 40 / 47 / 31 | 10.05.2023 | 24–27 |
| garanti | 95 | 9 | 9 | 42 / 38 / 15 | 03.06.2025 | 21–24 |
| intesa | 42 | 0 | 0 | 25 / 9 / 8 | 11.09.2025 | 6–7 |
| patria | 5 | 0 | 0 | 5 / 0 / 0 | 07.02.2024 | 0–0 |
| *filiale BCR* | 77 | 10 | 1 | 44 / 25 / 8 | 10.03.2025 | 10–12 |
| *filiala BRD* | 4 | 2 | 0 | 3 / 1 / 0 | 14.02.2025 | 0–0 |

**Cum se citesc:**
- **O „reclamă” e o variantă de creație, nu o campanie.** Reclamele de pe Search au multe variante de text.
- **Numărul de reclame nu arată presiunea publicitară.**
  - BT are 61% dintre reclamele băncilor, dar la afișări e sub Revolut, ING, Raiffeisen și BCR.
  - Mediana de la prima la ultima afișare e de 12 zile la BT și de 227 de zile la Revolut (29.09).
- **Afișările sunt intervale, adunate pe toată durata fiecărei reclame, până la 01.07.**
  - Duratele diferă între bănci, deci cifrele sunt un ordin de mărime.
  - „≥” apare când măcar o reclamă e în treapta deschisă „peste 10 milioane”.
- **Intesa n-a mai avut reclame Google** după 21.12.2025.

## Platformă, liste de clienți, țări și agenții

| bancă | YouTube principal | Search principal | fără platformă clară | exclude o listă de clienți | țintește o listă | doar în România | agenție |
|---|---:|---:|---:|---:|---:|---:|---|
| bt | 1.595 | 1.303 | 7.322 | 42% | 9% | 94% | – |
| ing | 145 | 284 | 1.585 | 2% | 19% | 76% | DQ&A Technology NL BV, la 1.291 |
| bcr | 475 | 372 | 469 | 1% | 36% | 87% | – |
| raiffeisen | 327 | 288 | 289 | 19% | 30% | 77% | – |
| revolut | 80 | 90 | 676 | 15% | 5% | 26% | – |
| nexent | 35 | 112 | 130 | 53% | 5% | 95% | Dentsu București, la 297 |
| cec | 60 | 62 | 80 | 0% | 37% | 90% | – |
| tbi | 46 | 62 | 84 | 0% | 48% | 64% | – |
| salt | 60 | 54 | 61 | 18% | 38% | 76% | – |
| libra | 21 | 48 | 84 | 0% | 30% | 86% | – |
| unicredit | 25 | 36 | 52 | 0% | 44% | 84% | – |
| garanti | 26 | 26 | 43 | 0% | 29% | 96% | – |
| intesa | 6 | 24 | 11 | 0% | 26% | 90% | WPP Media Romania, publică toate cele 42 |
| patria | 0 | 5 | 0 | 0% | 0% | 80% | – |

**Ce reiese:**
- **Agențiile:** ING își cumpără reclamele prin DQ&A Technology, din Olanda, Nexent prin Dentsu București, iar Intesa le publică prin WPP Media Romania. BRD lucrează cu Sense8.
- **Listele de clienți:**
  - BT și Nexent își exclud des clienții proprii (42% și 53%), deci caută clienți noi.
  - TBI, UniCredit, CEC și BCR își țintesc des clienții (48%, 44%, 37%, 36%).
  - Semnificația „clienți proprii” e cea mai probabilă, dar nu e confirmată de Google.
- **Revolut:** doar 26% dintre reclamele lui rulează numai în România, aproape de cele ~20% în română găsite la o verificare de mână. Filtrul „doar în România” e cel mai bun indiciu automat pentru reclamele Revolut făcute pentru piața locală.

## Reclame noi pe lună, 2026

Valurile de lansare se văd în numărul de reclame noi pe lună. De exemplu, CEC are 80 în martie, 49 în august și aproape nimic în rest.

| bancă | ian | feb | mar | apr | mai | iun | iul | aug | sep |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bt | 695 | 869 | 191 | 844 | 733 | 368 | 576 | 410 | 1.270 |
| ing | 50 | 63 | 104 | 218 | 158 | 318 | 343 | 45 | 258 |
| bcr | 49 | 83 | 59 | 68 | 166 | 30 | 53 | 51 | 124 |
| raiffeisen | 58 | 66 | 56 | 96 | 37 | 44 | 97 | 17 | 49 |
| revolut | 32 | 36 | 17 | 25 | 36 | 31 | 15 | 84 | 38 |
| nexent | 14 | 23 | 9 | 10 | 14 | 38 | 14 | 14 | 11 |
| cec | 0 | 0 | 80 | 18 | 1 | 13 | 0 | 49 | 0 |
| tbi | 12 | 16 | 16 | 18 | 22 | 16 | 16 | 16 | 2 |
| salt | 1 | 7 | 13 | 0 | 4 | 44 | 5 | 11 | 2 |
| libra | 1 | 9 | 20 | 2 | 35 | 21 | 3 | 7 | 1 |
| unicredit | 0 | 15 | 2 | 7 | 10 | 10 | 0 | 15 | 8 |
| garanti | 0 | 0 | 0 | 0 | 0 | 22 | 11 | 4 | 9 |

## Sezonul de Crăciun 2025: ce se poate și ce nu

- **După dată:** 1.392 de reclame au pornit între 15.11 și 31.12.2025. Filtrul e însă aproximativ. Primele patru după afișări, toate video Revolut pornite pe 23.12, n-au nicio legătură cu Crăciunul (verificat de mână pe 30.09).
- **Cu tema Google „Ocazii și cadouri”** rămân 40 de reclame. E un semnal mai curat, dar prinde puține și depinde de etichetarea Google.
- **Valurile de lansare:** cele 1.392 de reclame vin din 51 de valuri. Un val înseamnă reclamele unei bănci pornite în aceeași săptămână.

  | valuri | ce parte din reclamele din sezon |
  |---:|---:|
  | primele 10 | 77% |
  | primele 20 | 90% |
  | primele 30 | 96% |

  Cel mai mare val e al BT: 232 de reclame în săptămâna din 1.12.2025. Asta face posibilă o etichetare cu puține capturi (vezi [05](05_URMEAZA.md)).

## Prima comparație între două fotografii: 29.09 → 30.09

| | reclame ale băncilor |
|---|---:|
| noi | 118 |
| dispărute | 28 |
| în ambele | 16.605 |

- 27 dintre cele dispărute aveau ultima afișare pe 28.09.2025. Au ieșit din set exact la un an după ultima afișare, cum păstrează Google.
- Una a dispărut din alt motiv, necercetat.
- Comparația arată că fotografiile succesive se leagă într-un istoric. Istoricul de peste un an există doar dacă îl păstrăm noi.
