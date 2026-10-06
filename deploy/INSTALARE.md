# Serverul de test: mcc-test.libra.bank

`https://mcc-test.libra.bank` (`172.16.69.84`), Debian 13. Instalat pe 06.10.2026. Accesibil doar din rețeaua internă
și fără autentificare deocamdată: LDAP urmează, când se știu rolurile.

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
| `.env` | `/opt/marketing/mcc/.env` (600): `MIP_DSN`, `MIP_SALT` generate la instalare, `MIP_PERMITE_RULARI=0` |
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
