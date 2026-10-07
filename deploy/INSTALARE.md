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
| `.env` | `/opt/marketing/mcc/.env` (600): `MIP_DSN`, `MIP_SALT` generate la instalare, `MIP_PERMITE_RULARI=0`, `MCC_LDAP_*` (autentificarea); fără `MCC_AUTH_LOCAL` |
| aplicația | `systemd`: `mcc.service` (`deploy/mcc.service`), `app/server.py` pe `127.0.0.1:8765` |
| nginx | `deploy/nginx-mcc.conf`: HTTPS pe 443 (HTTP pe 80 redirecționează), servește `web/dist`; `/api`, `/logos`, `/pdf`, `/harta.html` merg la `:8765` |
| certificatul | `/etc/nginx/ssl/`: wildcard-ul `*.libra.bank` de la Libra Enterprise Root CA (ca la rcc-test, command-center, st-test), valabil până la 10.02.2028; copie din `/srv/linux-sysprep/certs`, cheia 600 root |

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

Logarea e cu contul de Windows, verificat la Active Directory prin LDAPS (`app/autentificare.py`). Rolul vine din
grupurile AD, inclusiv imbricate: admin (în plus „Rulare manuală” și „Joburi și erori”) sau analist; cine nu e în
niciunul primește 403. Fără sesiune nu se citește nicio dată (401). Nu e nevoie de cont de serviciu: bind-ul și
căutările se fac cu contul celui care se loghează.

### Ce cerem de la IT

1. **Un DC pentru LDAPS**: numele complet (ex. `dc01.<domeniu>`), port 636, deschis din `172.16.69.84`. Certificatul
   DC-ului trebuie să conțină exact acest nume (SAN); se verifică, deci o adresă IP în loc de nume nu merge.
2. **CA-ul** care a emis certificatul DC-ului, ca fișier PEM. Dacă e Libra Enterprise Root CA, e probabil deja în
   `/srv/linux-sysprep/certs`; se copiază în `/etc/ssl/mcc/ca-ad.pem` (citibil de `marketing`) și se pune în `MCC_LDAP_CA`.
3. **Cele două grupuri**, cu DN-ul complet (ex. `CN=MCC-Admin,OU=…,DC=…`) și cu membrii lor: unul pentru admin, unul
   pentru analist.
4. **Sufixul UPN** (`MCC_LDAP_DOMENIU`: utilizatorul scrie numele scurt, bind-ul e `nume@sufix`) și **baza de căutare**
   (`MCC_LDAP_BAZA`, DN-ul domeniului).
5. **Pragul de blocare a conturilor** din AD: aplicația oprește încercările după 5 parole greșite pe utilizator (și 20
   pe adresă) în 15 minute; pragul AD trebuie să fie peste 5, ca aplicația să nu poată bloca un cont.

### Instalare (o singură dată, la prima livrare cu autentificare)

`deploy/deploy.sh` instalează `ldap3` (din `requirements.txt`), dar **nu** copiază serviciul și configurația nginx.
Fără ele: fără `X-Real-IP` toți utilizatorii par aceeași adresă (20 de parole greșite ale oricui blochează logarea
tuturor 15 minute), iar cookie-ul nu primește `Secure`. Se copiază imediat după livrare; în cele câteva minute
dintre pași aplicația cere deja logare (`.env` nu are `MCC_AUTH_LOCAL`).

```bash
# 1. pe server: .env cu variabilele MCC_LDAP_* (model în .env.example), fără MCC_AUTH_LOCAL
sudo nano /opt/marketing/mcc/.env
# 2. pe server: TLS-ul DC-ului, „Verify return code: 0 (ok)”
openssl s_client -connect dc01.<domeniu>:636 -CAfile /etc/ssl/mcc/ca-ad.pem -verify_hostname dc01.<domeniu> </dev/null \
  | grep 'Verify return code'
# 3. de pe laptop: livrarea (codul, ldap3, repornirea)
deploy/deploy.sh
# 4. pe server: serviciul (MCC_AUTH_OBLIGATORIE=1) și nginx (X-Real-IP, X-Forwarded-Proto, antetele anti-încadrare)
cd /opt/marketing/mcc
sudo cp deploy/mcc.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl restart mcc
sudo nginx -T | grep -m1 '# configuration file'      # unde e instalată configurația; se înlocuiește cu deploy/nginx-mcc.conf
sudo nginx -t && sudo systemctl reload nginx
```

### Verificare

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://mcc-test.libra.bank/api/sumar    # 401 fără sesiune
ssh mcc-test 'sudo journalctl -u mcc -n 20'       # fără „Autentificarea AD nu e configurată: …”
ssh mcc-test 'sudo tail -n 20 /opt/marketing/mcc/loguri/autentificare.log'
```

`loguri/autentificare.log` (păstrat la livrare): o linie JSON pe eveniment (logare reușită sau nu, cu motivul;
delogare; refuz 403 pe o rută de admin; pornire/oprire de rulare), fără parole. Erorile AD detaliate (certificat,
timeout, configurație) apar doar aici, în câmpul `detaliu`; clientul vede doar codul (`ad_indisponibil`).

Sesiunile stau în memorie: `systemctl restart mcc` îi deloghează pe toți. Dacă `.env` are `MCC_AUTH_LOCAL`, serverul
refuză să pornească (motivul în `journalctl -u mcc`).
