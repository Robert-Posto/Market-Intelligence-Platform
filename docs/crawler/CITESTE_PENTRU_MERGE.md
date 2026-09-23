# Citește asta înainte de merge

*O pagină. Restul documentelor sunt context și pot aștepta.*

Pachetul conține comisioane și dobânzi extrase de pe site-urile a 23 de bănci
românești, cu Playwright. Datele sunt în `comisioane_unificate.json` și
`rate_validate.json`.

---

## Regula care contează cel mai mult

**Nu lua toate valorile din `comisioane_unificate.json`.** Fișierul conține și
valori despre care știm că nu trebuie folosite. Sunt lăsate înăuntru
intenționat — ca să se poată verifica de ce au fost excluse — dar au un steag.

```python
bune = [x for x in comisioane
        if x["stare_data"] not in ("ISTORIC", "DUBLURA")]
```

Fără filtrul ăsta bagi înapoi în date tarifele BCR din martie și iulie, peste
cele din august, plus documente numărate de două ori.

---

## Câmpurile adăugate

### `stare_data` — din ce versiune de document vine prețul

| valoare | ce înseamnă | de folosit? |
|---|---|---|
| `IN_VIGOARE` | dată citită din document, în trecut | **da** |
| `DATA_NECUNOSCUTA` | banca nu și-a datat documentul | **da**, dar marchează-l |
| `VIITOR` | preț anunțat, nu practicat încă | nu pentru „azi" |
| `ISTORIC` | există o versiune mai nouă a aceluiași act | **nu** |
| `DUBLURA` | același fișier, numărat de două ori | **nu** |
| `NECITIT` | pasul de datare n-a rulat | verifică lanțul |

`DATA_NECUNOSCUTA` **nu** înseamnă „vechi". Înseamnă că banca n-a scris nicio
dată în document și nici în numele fișierului. Sunt 18 documente așa, din care
12 sunt ale Librei. Dacă le scoți, ștergi Eximbank, Salt și BCR Locuințe cu
totul, și lași Libra cu 65 de valori din 876.

### `ambiguu` — prețul e real, dar nu știm pentru ce

`true` când, în același document și sub același serviciu, apar mai multe
prețuri diferite și nimic nu spune care când se aplică.

```
Eximbank, "Schimbare PIN la ATM":  0 lei   la unele carduri
                                   2,5 lei la altele
```

Tipul cardului era antet de coloană și nu s-a citit. Ambele prețuri sunt reale.
`motiv_ambiguu` spune ce s-a pierdut: `antet de coloana pierdut` sau
`prag de suma pierdut`.

**Nu le arunca.** Dacă agregi, marchează rezultatul. Dacă răspunzi la „cât
costă exact X", exclude-le.

### Restul câmpurilor relevante

| câmp | ce e |
|---|---|
| `concept`, `canal`, `destinatie` | maparea pe vocabularul canonic (29 concepte) |
| `segment` | `pf` / `pj` / `imm` / `pfa`, citit din numele documentului |
| `rol` | `conditie` = cifra e o cerință sau o limită, **nu un preț** |
| `conditie` | pragul de sumă, unde s-a putut citi |
| `sursa_pdf`, `pagina`, `text_sursa` | de unde vine, ca să se poată verifica |
| `data_vigoare`, `sursa_data` | data și dacă vine din text sau din numele fișierului |

`rol == "conditie"` merită atenție separată: sunt cifre ca „limită zilnică
1.000.000 lei" sau „rulaj minim 10.000 lei/lună". Arată ca prețuri și nu sunt.

---

## Ce nu e în pachet

**Patru bănci lipsesc.** Banca Transilvania, UniCredit și Intesa blochează
automatizarea; ING interzice prin `robots.txt` descărcarea PDF-urilor
(`Disallow: *.pdf`). Nu s-a ocolit nimic. Dacă în celelalte două abordări
apar date de la ele, verificați pe ce cale au fost obținute înainte de merge.

Banorient e exclusă complet (`Disallow: /`).

**Ratele nu au `stare_data`.** Toate cele ~1.000 vin din pagini web, nu din
PDF-uri, deci nu există „versiunea din iulie lăsată lângă cea din august". Data
lor e data crawlului.

**`necesita_llm.json`** — ~80 de valori pe care extragerea deterministă nu le
poate rezolva. Astea sunt exact ce așteptăm de la abordarea cu Claude API.

---

## Două lucruri de verificat la merge

**1. Aceeași bancă, același serviciu, trei surse — care câștigă?**
Dacă cele trei abordări dau valori diferite, nu media lor. Verifică `sursa_pdf`
și `pagina`: al nostru spune întotdeauna din ce document și de la ce pagină
vine cifra. O valoare cu sursă verificabilă bate una fără.

**2. Denominatorul.** Acoperirea noastră e 39% din 23 bănci × 20 cerințe = 460.
Cifra e pesimistă: TBI n-are credite ipotecare, Bank of China n-are produse
retail în România. Nu sunt cerințe ratate, sunt produse care nu există. Dacă
aveți o listă de produse pe bancă, numitorul se poate corecta — și e probabil
cea mai utilă contribuție a abordării cu API la partea asta.

---

## Unde se verifică o cifră

```
output/date_documente.json     data fiecărui document + DOVADA (fragmentul exact)
output/SCHIMBARI_PRETURI.md    ce preț s-a schimbat între două versiuni
output/comparatie_comisioane.md  tabelul comparativ; "?" = valoare ambiguă
output/urme.json               amprenta sha256 a fiecărui document
output/robots_origini.json     ce a permis fiecare origine, cu data verificării
output/robots/                 fișierele robots.txt brute, 30 de origini
```

**Despre dovada de conformitate.** `robots_origini.json` are un câmp
`verificat` pe fiecare origine: zece sunt verificate la 18 septembrie, una la
21. Fișierele `robots.txt` brute sunt în `output/robots/`, 30 la număr — alea
sunt dovada primară și nu depind de niciun script de-al nostru.

Documentul mai lung despre datare e `DATAREA_DOCUMENTELOR.md`. Restul
fișierelor `.md` din pachet sunt jurnale și note de lucru, fiecare cu data lui
în antet.
