# Instalarea pe server (Windows Server)

Pe server rulează **aplicația și baza**. Colectarea rămâne pe laptop: laptopul
e sursa, iar serverul primește periodic o copie a bazei și a Bronze-ului.
Serverul nu are nevoie de acces la internet, cu excepția instalării.

```
 colegi (cont de domeniu)
        │  https://<dns>/
        ▼
 IIS  ── HTTPS + Windows Authentication + grup AD
        │  proxy către 127.0.0.1:8765 (doar local)
        ▼
 serviciul MCC  (python app/server.py) ──► PostgreSQL 16 (doar local)
        │
        └─► bronze\  (PDF-urile originale, pentru vizualizator)
```

Aplicația nu are login propriu și ascultă doar pe `127.0.0.1`, pentru că
`verify_request` din `app/server.py` refuză orice altă adresă. Singura intrare
din rețea e IIS, care cere contul de domeniu. Nu se deschide în firewall nici
portul 8765, nici 5432.

## Ce cerem de la IT

| Ce | Pentru ce |
|---|---|
| Numele DNS spre IP-ul serverului | adresa aplicației |
| Certificat HTTPS pentru numele DNS (CA-ul intern) | IIS |
| Un grup AD, de exemplu `Grup-MCC`, cu colegii de la marketing | cine are acces |
| Portul 443 deschis din rețeaua internă spre server | accesul colegilor |
| Aprobare pentru NSSM (nssm.cc), URL Rewrite și ARR 3.0 | serviciul și proxy-ul |

## 1. Pe server: programele (o singură dată)

Structura propusă: `D:\mcc\mip` pentru cod, `D:\mcc\iis` pentru site-ul IIS,
`D:\mcc\nssm.exe`.

1. **PostgreSQL 16** (installerul EDB pentru Windows). După instalare, în
   `postgresql.conf` se setează `listen_addresses = 'localhost'`, iar regula
   de firewall pentru 5432 adăugată de installer se șterge. Apoi, în `psql` ca
   `postgres`:
   ```sql
   CREATE ROLE mip LOGIN PASSWORD '<parolă nouă, lungă>';
   ```
2. **Python 3.14** (python.org, „Add to PATH”) și **Git**.
3. **URL Rewrite** și **Application Request Routing 3.0** (installere offline
   de la Microsoft).

## 2. Codul și dependențele

Dacă serverul ajunge la GitHub:
```powershell
cd D:\mcc
git clone https://github.com/Robert-Posto/Market-Intelligence-Platform.git mip
```

Dacă nu ajunge, pe laptop se face `git bundle create mip.bundle main`, se
copiază fișierul și pe server se rulează `git clone mip.bundle mip`.

Pentru dependențe fără internet pe server: pe laptop se descarcă pachetele,
se copiază folderul `wheels` și se instalează de acolo.
```powershell
# pe laptop, în mip\
pip download -r requirements.txt -d wheels
# pe server, în D:\mcc\mip
pip install --no-index --find-links ..\wheels -r requirements.txt
```
Playwright și Chromium nu trebuie instalate, pentru că serverul nu colectează.

## 3. Fișierul `.env` de pe server

Se scrie de mână pe server, fără să fie copiat de pe laptop. Are doar două
rânduri:
```
MIP_DSN=host=localhost port=5432 dbname=mip user=mip password=<parola de la pasul 1>
MIP_PORT=8765
```
Cheia Anthropic și `MIP_SALT` **nu se pun pe server**, pentru că sunt folosite
doar la colectare, pe laptop.

## 4. Baza și fișierele

Pe **laptop**, în `mip\`:
```powershell
.\deploy\exporta_baza.ps1          # rezultă mip_AAAA-LL-ZZ.dump (~1-2 MB)
```

Se copiază pe server, de exemplu prin RDP (clipboard sau drive redirection)
sau printr-un share:

| De pe laptop | Pe server | Mărime |
|---|---|---|
| `mip_AAAA-LL-ZZ.dump` | `D:\mcc\` | ~1-2 MB |
| `bronze\` | `D:\mcc\mip\bronze\` | ~1,3 GB |
| `output\reclame\` | `D:\mcc\mip\output\reclame\` | câțiva MB |
| `app\.cache_pdf\` (opțional) | `D:\mcc\mip\app\.cache_pdf\` | ~60 MB |

Pentru `bronze\` e recomandat `robocopy <sursă> <destinație> /E /Z`. La a doua
copiere trec doar fișierele noi.

Pe **server**:
```powershell
cd D:\mcc\mip
.\deploy\importa_baza.ps1 -Fisier D:\mcc\mip_AAAA-LL-ZZ.dump
```

## 5. Serviciul și IIS (ca administrator)

```powershell
cd D:\mcc\mip
.\deploy\instaleaza_serviciu.ps1 -Radacina D:\mcc\mip -Nssm D:\mcc\nssm.exe
.\deploy\instaleaza_iis.ps1 -Dns <numele-dns> -Radacina D:\mcc
```

Apoi, în IIS Manager, la site-ul `MCC` → Bindings → https se alege
certificatul. În `D:\mcc\iis\web.config`, `DOMENIU\Grup-MCC` se înlocuiește cu
grupul real.

**Verificare:** `https://<numele-dns>/` se deschide de pe alt calculator din
rețea, fără cerere de parolă pentru conturile din grup, și cu 401 pentru
celelalte.

## Actualizarea datelor (după fiecare colectare)

1. Pe laptop: `.\deploy\exporta_baza.ps1`.
2. Se copiază dump-ul, iar `bronze\` se sincronizează cu `robocopy /E`.
3. Pe server: `.\deploy\importa_baza.ps1 -Fisier ...`

Importul restaurează într-o bază nouă și face schimbul abia la final. Aplicația
e oprită câteva secunde, iar copia anterioară rămâne ca `mip_vechi` până la
importul următor.

## Actualizarea codului

```powershell
cd D:\mcc\mip
git pull
Restart-Service MCC
```

Dacă `git pull` aduce o migrare nouă, ea ajunge oricum cu următorul dump de
pe laptop, pentru că baza de pe server e mereu o copie completă a celei de pe
laptop.

## Ce nu merge pe server

- **PDF-urile care nu sunt în Bronze.** Vizualizatorul le caută pe site-ul
  băncii, iar fără internet afișează eroare. Cu `bronze\` copiat complet,
  cazul e rar.
- **Butoanele de rulare a colectării.** Rămân înghețate, ca pe laptop.
