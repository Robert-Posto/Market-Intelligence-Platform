# Baza MIP: copia lui Robert, de pus pe laptopul tău

Fotografia bazei e din **30.09.2026, ora 15:39**. Pașii de mai jos
îți aduc exact aceeași bază în containerul tău `mip-db`. Baza ta de acum nu se
șterge: rămâne alături, sub alt nume, și poți reveni oricând la ea.

## Ce e în pachet

| fișier | mărime | ce e |
|---|---|---|
| `mip_2026-09-30.dump` | 1,5 MB | baza întreagă (`pg_dump -Fc`), schema până la migrarea 026 inclusiv |
| `output\reclame\` | 21 MB, 22 fișiere | reclamele Bing (`microsoft_2026-09-29.json`) și Google (`google_2026-09-30\`), citite de aplicație din fișiere, nu din bază |
| `app\.cache_pdf\` | 58 MB, 114 PDF-uri | opțional: PDF-uri publice ale băncilor, aduse deja de vizualizator (fallback când documentul nu e în Bronze) |
| `importa_baza_docker.ps1` | | aceeași copie ca `deploy\importa_baza_docker.ps1` din repo, în caz că nu a ajuns încă în `main` |

**Nu** sunt în pachet: `.env`, cheile API, `MIP_SALT`, `loguri\` și `bronze\`.

### Numerele din fotografie

| tabelă | rânduri |
|---|---|
| `observatii_curente` (vedere) | 24.169 |
| `observations` | 27.677 |
| `surse` | 7.313 |
| `campanii` | 742 (+ 1.540 în `campanii_surse`) |
| `comunicate` | 989 |
| `catalog_libra` | 57 |
| `app_release` | 26 (+ 133 capturi, 120 recenzii) |
| `banci` | 30 |
| `locatii` | 1.478 |

> **Campaniile sunt complete** pentru rularea din 30.09 (colectorul s-a terminat
> înainte de export): brd 156, bcr 135, ing 111, salt 109, raiffeisen 66,
> procredit 42, garanti 40, tbi 37, exim 20, libra 12, patria 6, bcr-locuinte 4,
> vista 2, credex și nexent câte 1. Comunicatele (newsroom): doar titlu și dată.

## Pași

Toate comenzile sunt pentru PowerShell, rulate din rădăcina repo-ului `mip`.

**0. Oprește aplicația**, dacă rulează (Ctrl+C în fereastra cu `python app/server.py`).

**1. Codul la zi** (migrările 019–026 și pagina de reclame trebuie să fie în cod):
```powershell
git checkout main
git pull
pip install -r requirements.txt
```

**2. Baza pornită:**
```powershell
docker compose up -d
```

**3. Importul.** Pune în `$P` folderul unde ai dezarhivat pachetul:
```powershell
$P = "$env:USERPROFILE\Downloads\pentru_coleg_baza_2026-09-30"
powershell -ExecutionPolicy Bypass -File .\deploy\importa_baza_docker.ps1 -Fisier "$P\mip_2026-09-30.dump"
```
Scriptul restaurează în `mip_nou`, apoi închide conexiunile și schimbă numele:
`mip` devine `mip_vechi_<AAAAMMZZ_HHmmss>` și `mip_nou` devine `mip`. La final
afișează numărătorile, care trebuie să fie cele din tabelul de mai sus
(24169 / 7313 / 742 / 57 / 26). Dacă `pg_restore` eșuează, baza ta rămâne
neatinsă. După import **nu rula** `db/schema.sql` sau migrările, pentru că
dump-ul le conține deja.

**4. Fișierele de date:**
```powershell
robocopy "$P\output\reclame" ".\output\reclame" /E
robocopy "$P\app\.cache_pdf" ".\app\.cache_pdf" /E     # opțional
```
(robocopy întoarce cod 1 când a copiat fișiere, ceea ce e normal.)

**5. `.env`:** îl păstrezi pe al tău. `MIP_DSN` trebuie să fie
`host=localhost port=5432 dbname=mip user=mip password=mip`. **`MIP_SALT` trebuie
să fie identic cu al lui Robert.** `app_review.autor_hash` e hash-ul cu sare al
autorului și face parte din cheia unică a recenziilor. Cu altă sare, aceleași
recenzii colectate din nou apar dublate, iar pseudonimele nu se mai potrivesc.
Robert ți-l dă separat, pe un canal sigur (de exemplu în persoană sau
într-un mesaj criptat). Sarea **nu** e în pachet și nu se trimite în chat sau
pe e-mail necriptat.

**6. Pornirea:**
```powershell
python app/server.py
```
Deschide `http://localhost:8765`.

## Bronze (opțional, 1,35 GB)

`bronze\` conține documentele originale descărcate de la bănci (2.550 de
fișiere, 1.444.819.010 octeți în 30.09). Îl folosesc vizualizatorul de PDF (care
servește exact versiunea citată, fără nicio cerere la bancă) și refacerile.
Fără el aplicația merge, iar vizualizatorul ia PDF-ul din `app\.cache_pdf\` sau,
în ultimă instanță, de pe site-ul băncii. Dacă îl vrei, Robert îl pune pe un
share după ce se termină colectarea campaniilor (care scrie în
`bronze\campanii\`). De acolo îl copiezi cu:
```powershell
robocopy "\\<share>\mip_bronze" ".\bronze" /E /Z
```
La o copiere ulterioară trec doar fișierele noi.

## Ce date sunt cu regim special

- **Reclamele Bing și Google** (`output\reclame\`): **test, până la avizul
  juridic.** Stau doar în fișiere, nu în bază (tabela vine după aviz), deci nu
  se prezintă ca rezultat final și nu se distribuie mai departe.
- **Catalogul Libra** (`catalog_libra` și valorile cu `metoda_extractie = 'catalog'`):
  **uz intern.** Provine din exportul intern Sales Command Center, nu de pe web.

## Dacă ceva nu merge: revenirea la baza ta

Scriptul afișează la final exact numele copiei vechi. Cu aplicația oprită:
```powershell
docker exec mip-db psql -U mip -d postgres -c "ALTER DATABASE mip RENAME TO mip_importat"
docker exec mip-db psql -U mip -d postgres -c "ALTER DATABASE mip_vechi_<AAAAMMZZ_HHmmss> RENAME TO mip"
```
Copiile existente se văd cu:
```powershell
docker exec mip-db psql -U mip -d postgres -tAc "SELECT datname FROM pg_database ORDER BY 1"
```
Copia veche se șterge doar când ești sigur că baza nouă e bună:
```powershell
docker exec mip-db psql -U mip -d postgres -c "DROP DATABASE mip_vechi_<AAAAMMZZ_HHmmss>"
```
