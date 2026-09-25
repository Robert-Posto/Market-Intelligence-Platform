# Handoff: revamp-ul interfeței (25.09.2026)

Pentru cine lucrează mai departe pe aplicație (`app/`) după acest push.
Nu s-a schimbat nimic în baza de date și în colectare: **nicio migrare nouă**.

## Ce ai de făcut după `git pull`

Doar repornește serverul, fiindcă s-a schimbat și `app/server.py`:

```bash
python app/server.py        # apoi http://127.0.0.1:8765
```

Dacă vrei varianta veche a interfeței, ca să compari:
`git checkout ui-inainte-de-revamp -- app/` (și repornești serverul).
Revii cu `git checkout main -- app/`.

## De ce

Datele erau greu de găsit. Exemplul care a pornit totul: la 2.1, clic pe
„BCR · Administrare cont" deschidea 316 valori desfășurate, ~35 de ecrane de
derulat. Fiecare pagină a fost analizată separat (sarcini concrete, câte
clicuri și câte ecrane până la răspuns), apoi rearanjată după aceeași rețetă:

1. rezumat sus (cifra care răspunde la întrebare);
2. un tabel compact, sortabil la clic pe antet, cu **Libra fixată prima**;
3. filtrele fixe sus la derulare (`.bara-fixa`);
4. detaliile și explicațiile lungi pliate („ⓘ Despre date");
5. paginare reală unde sunt mii de rânduri.

Doar desktop; adaptarea pentru telefon nu e cerută.

## Ce s-a schimbat, pe pagini

| Pagină | Acum |
|---|---|
| Overview | 7 carduri pe categoriile 2.1–2.6 (cifră, câte bănci din 30, prospețime, link); „Ce avem pe fiecare bancă", detaliile tehnice și rulările sunt pliate. Butoanele „Rulează" rămân dezactivate. |
| Sertarul cu dovezi | rezumat (interval, variante, gratuite), căutare, grupe pliate ordonate de la cel mai ieftin, o valoare pe rând, citatul la clic pe rând, variantele ieșite din ofertă ascunse. Esc închide. |
| 2.1 Produse | tabel bancă × serviciu în locul celor 5 clasamente; celula = câte prețuri, interval, câte gratuite; clic = sertarul. |
| 2.2 Rate | tabel bancă × tip de dobândă; filtru pe **termen** la depozite și pe **produs** la credite (vezi mai jos). |
| 2.3 Aplicații & recenzii | **2.7 Sentiment s-a mutat aici.** Comutator iOS / Android (Android: „în lucru"). Tabelul aplicațiilor are și coloanele de recenzii; clic pe bancă = recenziile ei, cu răspunsul băncii. `#/sentiment` redirecționează aici. |
| 2.4 Campanii | tabel cu sursele posibile și ce cere fiecare. |
| 2.5 Rețea | sortat pe rețeaua proprie (sucursale + ATM proprii), nu pe total; link „vezi pe hartă" pe fiecare bancă. |
| Hartă | `harta.html?banca=libra` preselectează și centrează banca; puncte grupate în bule la zoom mic; ATM-urile partenere estompate; legenda reparată; numărul din zona vizibilă. |
| 2.6 Context | IRCC în vigoare și ROBOR 3M/6M/12M sus; tabel zi × scadență (O/N → 12M); IRCC pe trimestre. |
| Versus | bilanțul Libra (cea mai bună / la mijloc / cea mai slabă), filtru „unde Libra pierde / câștigă", capul secțiunilor fix la derulare, selector cu căutare și limita de 3 bănci vizibilă. |
| Fișă bancă (nouă) | `#/banca?b=<slug>`: tot ce avem despre o bancă; clic pe numele băncii în tabele duce aici. |
| Istoric | filtre de perioadă, tip și ordine („cele mai mari schimbări"); rezumatul se recalculează din filtru; grupat pe bancă. |
| Surse | tabel pe bancă (cu date / încercate / neîncercate / acoperire); căutare după fișier; coloana „Fișier"; paginare de 50. |
| Coada de verificare | tabel bancă × motiv (clic = filtru); explicația motivului o singură dată; filtru „doar citate cu context"; paginare de 100 (înainte se vedeau doar primele 150 din 5.263). |

## Ce s-a schimbat în API (`app/server.py`)

Toate rutele vechi răspund la fel; s-au adăugat doar parametri și câmpuri.

- `/api/rate`: `termen` (`scurt`, `6`, `12`, `lung`, `necunoscut`) și `produs`
  (`ipotecar`, `nevoi_personale`, `card`, `rate_magazin`, `altele`); întoarce
  `termene` și `produse` cu numărul de valori, plus `luni` pe celulă.
  Termenul e citit din `frecventa` sau din al doilea segment al `cod_scenariu`
  (`TERMEN_LUNI`); produsul e dedus din `serviciu` + `conditie` (`PRODUS_CREDIT`).
- `/api/celula`: aceleași `termen` și `produs`, ca sertarul să arate exact
  valorile din spatele celulei.
- `/api/istoric`: exclude schimbările cu valori peste pragurile din
  `normalizeaza.PRAGURI` (ex. capitalul social BCR citit ca comision) și
  întoarce `excluse_implauzibile`.
- `/api/surse`: `q` (căutare în adresă), `motiv`, câmpul `fisier`, `pe_banca`
  (toate cele 30 de bănci); sortarea nu mai face o subinterogare pe rând
  (2,5 s → 0,6 s).
- `/api/coada`: `offset`, `context=1`, `matrice` (bancă × motiv); `in_coada_cu_link`
  numără și sursele care sunt ele însele adrese web (înainte arăta 0).
- `/api/sentiment`: `raspuns_banca` pe recenzie; pe o singură bancă, negativele întâi.
- `/api/mobil`: `distributie_stele`. `/api/indici`: `valabil_pana`, `sursa`.
- `/api/acoperire` (nouă): cifrele pe categorii și pe fiecare bancă, pentru
  Overview și fișa de bancă.
- **`/pdf` servește întâi copia din Bronze** (`_din_bronze`). Înainte descărca
  din nou documentul de la bancă la prima deschidere, iar la unele bănci
  cădea, deci PDF-ul nu se deschidea în vizualizator. Acum se vede exact
  versiunea din care s-au extras cifrele și nu mai pleacă nicio cerere spre
  bancă. Verificat: toate cele 536 de documente cu valori se servesc.
  Descărcarea din rețea (cu robots.txt) rămâne doar pentru ce nu e în Bronze.

## În `index.html`, pe scurt

- `tabel(randuri, coloane, opt)`: `s` pe coloană = valoarea de sortare,
  `td` = clasă/atribute pe celulă, `opt.libra` fixează Libra, `opt.rand` dă
  clasă/clic pe rând, `opt.implicit` sortarea inițială.
- helperi noi: `despre()`, `bareStele()`, `paginare()`, `varsta()`,
  `cautaInTabel()`, `deschideSertarHtml()`.
- routerul păstrează derularea când se schimbă doar un filtru pe aceeași
  pagină și înțelege `la=<id>` (sare la secțiunea respectivă).
- au dispărut `clasament()`, `randObs()`, `grafBare()`, `grupuriCoada()`.

## Ce a ieșit la iveală (de date, nu de interfață)

- **Termenul depozitelor lipsește la ~70% din valori** (31 din 107 îl au);
  la „7–12 luni" apar doar 2 bănci. De îmbunătățit în extracție.
- **La BRD s-au extras valori din două formulare fiscale americane** (IRS
  W-8BEN, W-9). Trebuie adăugate la filtrul de documente fără tarife
  (`extractoare.RE_NU_TARIF` / `RE_TITLU_NU_TARIF`) la următoarea refacere
  din Bronze.
- **Libra are doar 5 locații** în Overture; orașul/județul lipsesc la ~75%
  din puncte, deci nu se face încă defalcare pe județe.
- **Cursul valutar al băncilor nu se colectează** (2 valori în total); în
  `docs/SUMAR_DATE.md` a fost mutat la „Urmează".
- Istoricul BCR e dominat de versiunile vechi ale documentelor; se reduce la
  refacerea din Bronze cu marcarea versiunilor (`ingest/versiuni.py`), care
  încă n-a rulat după ultimele parsere.

## Ce n-a intrat

- un filtru global „băncile mele", păstrat între pagini;
- data ultimei actualizări a aplicațiilor (nu e colectată);
- Android (Google Play) — doar marcat „în lucru".
