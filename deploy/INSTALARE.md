# Serverul de test: mcc-test.libra.bank

`https://mcc-test.libra.bank` (`172.16.69.84`), Debian 13. Instalat pe 06.10.2026. Accesibil doar din rețeaua internă,
cu logare prin contul AD (vezi „Autentificare AD” mai jos).

## Acces

Intrarea e cu parola AD, nu cu cheie. În `~/.ssh/config`, blocul `Host mcc-test`
(cu `ControlMaster`, `ControlPersist 8h`) face ca după primul `ssh mcc-test` și
`deploy/deploy.sh`, și Claude Code să refolosească aceeași conexiune.

## Ce e pe server

| ce | unde |
|---|---|
| codul | `/opt/marketing/mcc` (utilizatorul `marketing`), commit-ul livrat în `VERSIUNE` |
| Python 3.13 | `/opt/marketing/venv`. Proiectul cere 3.12, dar pe Debian 13 vine 3.13, iar `requirements.txt` se instalează fără erori |
| Chromium (Playwright) | `/opt/marketing/.cache/ms-playwright` |
| PostgreSQL 17 (apt, nu Docker) | baza și rolul `mip`, doar pe `localhost`; parola e în `.env` |
| `.env` | `/opt/marketing/mcc/.env` (600): `MIP_DSN`, `MIP_SALT` generate la instalare, `MIP_PERMITE_RULARI=0`, `MCC_LDAP_*` (autentificarea), `MCC_ADMIN_INITIAL`, `MCC_AUTH_OBLIGATORIE=1`; fără `MCC_AUTH_LOCAL` |
| aplicația | `systemd`: `mcc.service` (`deploy/mcc.service`), `app/server.py` pe `127.0.0.1:8765` |
| nginx | `deploy/nginx-mcc.conf`: HTTPS pe 443 (HTTP pe 80 redirecționează), servește `web/dist`; `/api`, `/logos`, `/pdf`, `/harta.html` merg la `:8765` |
| certificatul | `/etc/nginx/ssl/`: wildcard-ul `*.libra.bank` de la Libra Enterprise Root CA (ca la rcc-test, command-center, st-test), valabil până la 10.02.2028; copie din `/srv/linux-sysprep/certs`, cheia 600 root |

nginx (`www-data`) citește `web/dist` printr-un ACL pe `/opt/marketing` (`setfacl -m u:www-data:x`), nu prin grupul
`marketing`: lista grupului e rescrisă din afară (pe 09.10.2026 `www-data` dispăruse din el, iar pagina dădea 500).

`app/server.py` refuză orice conexiune care nu vine de pe loopback (`verify_request`).
nginx stă pe același server, deci verificarea rămâne neatinsă.

## Comenzi

```bash
deploy/deploy.sh                                   # livrarea HEAD, de pe laptop
ssh mcc-test 'sudo journalctl -u mcc -n 50'        # jurnalul aplicației
ssh mcc-test 'cd /opt/marketing/mcc && DSN=$(sudo grep ^MIP_DSN= .env | cut -d= -f2-) \
  && sudo -u marketing psql "$DSN" -f db/migration_NNN_<nume>.sql \
  && sudo -u marketing psql "$DSN" -f db/sincronizeaza_vederi.sql'
```

Un script de colectare se rulează ca `marketing`, din `/opt/marketing/mcc`:

```bash
sudo -u marketing -H /opt/marketing/venv/bin/python ingest/<script>.py
```

## Autentificare AD

Logarea e cu contul de Windows, verificat la Active Directory prin LDAPS (`app/autentificare.py`). AD-ul verifică doar
parola; rolul se dă în aplicație, în pagina „Utilizatori” (ca în SCC): admin (în plus „Rulare manuală”, „Joburi și
erori” și „Utilizatori”) sau analist. Un cont nou apare acolo la prima logare, fără rol (403 până îi dă un admin unul).
`MCC_ADMIN_INITIAL` din `.env` primește admin la prima logare, ca să existe cine să dea rolurile celorlalți. Fără
sesiune nu se citește nicio dată (401). Nu e nevoie de cont de serviciu: bind-ul și căutarea se fac cu contul celui
care se loghează.

Pe mcc-test (09.10.2026): DC-ul e cel din SCC, `buc-orange-dc2.libra.bank`, dar pe LDAPS (636), cu Libra Enterprise
Root CA în `/etc/ssl/mcc/ca-ad.pem` („Verify return code: 0 (ok)” de pe server); `MCC_LDAP_DOMENIU=libra.bank`,
`MCC_LDAP_BAZA=DC=libra,DC=bank`, `MCC_ADMIN_INITIAL=doru.popescu`.

### Ce cerem de la IT

1. **Un DC pentru LDAPS**: numele complet (ex. `dc01.<domeniu>`), port 636, deschis din `172.16.69.84`. Certificatul
   DC-ului trebuie să conțină exact acest nume (SAN); se verifică, deci o adresă IP în loc de nume nu merge.
2. **CA-ul** care a emis certificatul DC-ului, ca fișier PEM. Dacă e Libra Enterprise Root CA, e probabil deja în
   `/srv/linux-sysprep/certs`; se copiază în `/etc/ssl/mcc/ca-ad.pem` (citibil de `marketing`) și se pune în `MCC_LDAP_CA`.
3. ~~Grupurile AD~~: nu mai trebuie. Rolurile se dau în aplicație (pagina „Utilizatori”, migrarea 040).
4. **Sufixul UPN** (`MCC_LDAP_DOMENIU`: utilizatorul scrie numele scurt, bind-ul e `nume@sufix`) și **baza de căutare**
   (`MCC_LDAP_BAZA`, DN-ul domeniului).
5. **Politica de blocare a conturilor** din AD: pragul (*Account lockout threshold*) și fereastra de observație
   (*Reset account lockout counter after*). Aplicația oprește încercările după `MCC_AUTH_MAX_INCERCARI` (implicit 3)
   parole greșite pe utilizator și `MCC_AUTH_MAX_PE_IP` (implicit 20) pe adresă, în `MCC_AUTH_FEREASTRA_MIN`
   (implicit 30) minute. Limita pe utilizator trebuie să rămână sub pragul AD, altfel oricine poate bloca un cont
   prin aplicație. Regula:

   **prag AD > `MCC_AUTH_MAX_INCERCARI` × alias-uri × ⌈fereastra AD / `MCC_AUTH_FEREASTRA_MIN`⌉**

   *Alias-uri* = câte nume diferite duc la același cont. `ana`, `ANA`, `LIBRA\ana` și `ana@<domeniu>` se numără
   împreună (1), dar un cont cu UPN explicit diferit de sAMAccountName (`dan` și `daniel.pop`) are 2. Exemplu: AD cu
   prag 5 și fereastră 30 de minute, valorile implicite: 3 × 1 × 1 = 3 < 5; dacă există conturi cu 2 alias-uri,
   3 × 2 × 1 = 6 nu mai trece, deci `MCC_AUTH_MAX_INCERCARI=2` (2 × 2 × 1 = 4). Outlook, VPN-ul etc. adună la același
   contor AD: lăsați loc.

   Regula oprește rafalele. AD-ul își golește contorul abia după o fereastră întreagă *fără* nicio parolă greșită, deci
   cineva care trimite rar câte una, sub limita aplicației, tot poate duce contorul la prag, doar mai încet (cu
   valorile implicite și AD 5 / 30 de minute: în circa 40 de minute). Garanția completă cere în plus
   `MCC_AUTH_FEREASTRA_MIN` ≥ `MCC_AUTH_MAX_INCERCARI` × alias-uri × fereastra AD (aici 90), cu prețul că cine greșește
   parola de 3 ori așteaptă tot atât. Valorile se aleg cu IT-ul, după politica AD.

### Instalare (o singură dată, la prima livrare cu autentificare)

`deploy/deploy.sh` instalează `ldap3` (din `requirements.txt`), dar **nu** copiază serviciul și configurația nginx.
Le verifică însă înainte de repornire și se oprește, cu mesaj, dacă serviciul nu are `MCC_AUTH_OBLIGATORIE=1`
(`systemctl show -p Environment mcc`) sau nginx nu trimite `X-Real-IP` (`nginx -T`). Fără `X-Real-IP` toți utilizatorii
par aceeași adresă (20 de parole greșite ale oricui blochează logarea tuturor), iar fără `X-Forwarded-Proto` cookie-ul
nu primește `Secure` (nici prefixul `__Host-`). La prima livrare cu autentificare scriptul se oprește deci la pasul 3:
codul nou e copiat, dar rulează tot cel vechi până la pasul 5.

`MCC_AUTH_OBLIGATORIE=1` se pune și în `.env`, nu doar în serviciu: `.env` e păstrat la livrare, deci rămâne valabil și
dacă serviciul ar fi reinstalat dintr-o copie veche.

```bash
# 1. pe server: .env cu variabilele MCC_LDAP_* (model în .env.example) și MCC_AUTH_OBLIGATORIE=1, fără MCC_AUTH_LOCAL;
#    eventual MCC_AUTH_MAX_INCERCARI / MCC_AUTH_FEREASTRA_MIN după politica AD (punctul 5 de mai sus)
sudo nano /opt/marketing/mcc/.env
# 2. pe server: TLS-ul DC-ului, „Verify return code: 0 (ok)”
openssl s_client -connect dc01.<domeniu>:636 -CAfile /etc/ssl/mcc/ca-ad.pem -verify_hostname dc01.<domeniu> </dev/null \
  | grep 'Verify return code'
# 3. de pe laptop: livrarea (codul, ldap3); prima dată se oprește la verificări, înainte de repornire
deploy/deploy.sh
# 4. pe server: serviciul (MCC_AUTH_OBLIGATORIE=1) și nginx (X-Real-IP, X-Forwarded-Proto, antetele anti-încadrare)
cd /opt/marketing/mcc
sudo cp deploy/mcc.service /etc/systemd/system/ && sudo systemctl daemon-reload
sudo nginx -T | grep -m1 '# configuration file'      # unde e instalată configurația; se înlocuiește cu deploy/nginx-mcc.conf
sudo nginx -t && sudo systemctl reload nginx
# 5. de pe laptop: din nou livrarea; verificările trec și serviciul repornește
deploy/deploy.sh
```

### Verificare

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://mcc-test.libra.bank/api/sumar    # 401 fără sesiune
ssh mcc-test 'sudo journalctl -u mcc -n 20'       # fără „Autentificarea AD nu e configurată: …”
ssh mcc-test 'sudo tail -n 20 /opt/marketing/mcc/loguri/autentificare.log'
```

`loguri/autentificare.log` (păstrat la livrare): o linie JSON pe eveniment (logare reușită sau nu, cu motivul;
delogare; refuz 403 pe o rută de admin; pornire/oprire de rulare), fără parole. La o logare eșuată numele scris nu
apare (poate fi o parolă scrisă în câmpul greșit), ci doar `utilizator_hash`: o amprentă cu o cheie nouă la fiecare
pornire, bună la corelarea încercărilor până la următoarea repornire. Erorile AD detaliate (certificat, timeout,
configurație) apar doar aici, în câmpul `detaliu`; clientul vede doar codul (`ad_indisponibil`).

Sesiunile stau în memorie: `systemctl restart mcc` îi deloghează pe toți. Dacă `.env` are `MCC_AUTH_LOCAL`, serverul
refuză să pornească (motivul în `journalctl -u mcc`).
