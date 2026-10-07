# Autentificare AD (LDAP) cu roluri — plan de implementare

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** logare cu contul AD (LDAPS), roluri admin/analist din grupuri AD, sesiuni cu cookie, verificare pe server pentru toate datele și pentru rutele de admin, pagină de logare în interfață.

**Architecture:** modul nou `app/autentificare.py` (configurare, validare, LDAP prin `ldap3`, limitare, sesiuni în memorie, jurnal în fișier), folosit de o poartă în `Handler` din `app/server.py`; interfața întreabă `GET /api/sesiune` la pornire și arată pagina de logare la 401.

**Tech Stack:** Python 3 (`http.server`, `ldap3`, `unittest`), React 18 + AntD 5, nginx.

**Spec:** `docs/superpowers/specs/2026-10-06-autentificare-ldap.md` (citește-o întâi)

## Global Constraints

- Serverul rămâne fără scrieri în baza de date: sesiunile în memorie, jurnalul în `loguri/autentificare.log` (o linie JSON pe eveniment).
- Variabile de mediu, exact: `MCC_LDAP_URL`, `MCC_LDAP_DOMENIU`, `MCC_LDAP_BAZA`, `MCC_LDAP_GRUP_ADMIN`, `MCC_LDAP_GRUP_ANALIST`, `MCC_LDAP_CA` (opțional), `MCC_SESIUNE_ORE` (implicit 8), `MCC_AUTH_LOCAL` (`admin` | `analist`, doar dezvoltare), `MCC_AUTH_OBLIGATORIE` (`1` pe server).
- Rute, exact: `POST /api/autentificare` `{utilizator, parola}` → 200 `{utilizator, nume, rol}`; `GET /api/sesiune` → 200 `{utilizator, nume, rol, local}` sau 401; `POST /api/delogare` → 200 `{}`. Rolurile: `"admin"` | `"analist"`. Erorile: `{eroare: "<cod>"}` cu codurile `neautentificat` (401), `date_invalide` (401), `fara_rol` (403), `interzis` (403, rol insuficient), `prea_multe_incercari` (429), `ad_indisponibil` (503).
- Cookie: numele `mcc_sesiune` pe HTTP și `__Host-mcc_sesiune` pe HTTPS (după audit, 07.10); `HttpOnly; SameSite=Strict; Path=/; Max-Age=<sec>`; `Secure` când `X-Forwarded-Proto: https`.
- Rute admin (403 pentru analist): `/api/jobs`, `/api/rulare_manuala`, `/api/rulare_manuala/estimare`, `/api/rulari` (GET), `/api/rulari/porneste`, `/api/rulari/opreste` (POST).
- Fără sesiune → 401 pe: orice `/api/*` (în afară de `/api/autentificare`, `/api/sesiune`, `/api/delogare`), `/pdf`, `/logos/*`, `/pdf.html`, `/harta.html`, `/` și `/index.html` (interfața veche).
- Cod: Python în stilul din `app/server.py` și `app/rulari.py` (comentarii în română care spun DE CE); TypeScript fără punct și virgulă, ghilimele simple; texte noi în dicționar RO + EN.
- Dependență nouă: doar `ldap3` (în `requirements.txt`, cu comentariu). Nimic altceva.
- Shell Git Bash; Node: `export PATH="/c/Program Files/nodejs:$PATH"`; Python: `/c/Users/robert.postolache/AppData/Local/Programs/Python/Python314/python.exe`, `PYTHONIOENCODING=utf-8`. Nu opri serverele utilizatorului (:8765, :5173).

## Cerințe de securitate (din threat model, obligatorii)

1. Utilizator validat cu `^[A-Za-z0-9._-]{1,64}$` după ce se scot `DOMENIU\` sau `@domeniu`; altfel `date_invalide` fără a întreba AD-ul.
2. Parola goală (sau doar spații) → `date_invalide` fără a întreba AD-ul. Parolă > 256 caractere → `date_invalide`.
3. Valoarea din filtrul LDAP escapată (`ldap3.utils.conv.escape_filter_chars`).
4. Doar `ldaps://` (TLS, `ssl.CERT_REQUIRED`, `MCC_LDAP_CA` dacă e dat, altfel depozitul sistemului); `MCC_LDAP_URL` cu alt protocol → configurație invalidă (logarea răspunde `ad_indisponibil`, iar serverul scrie motivul la pornire).
5. Timeout: conectare 5 s, răspuns 10 s; maximum 4 verificări LDAP simultane (semafor); peste → `ad_indisponibil`.
6. Limitare (după audit, configurabilă: `MCC_AUTH_MAX_INCERCARI`, `MCC_AUTH_MAX_PE_IP`, `MCC_AUTH_FEREASTRA_MIN`): implicit 3 eșecuri / utilizator și 20 / IP în 30 de minute → `prea_multe_incercari` fără a întreba AD-ul; o logare reușită șterge contorul utilizatorului.
7. Mesaje către client doar codurile de mai sus; excepțiile LDAP detaliate merg doar în jurnalul serverului.
8. Sesiune: `secrets.token_urlsafe(32)`, ținută ca SHA-256; identificator nou la fiecare logare; expirare la `MCC_SESIUNE_ORE` de inactivitate și maximum 12 h absolut; maximum 10 sesiuni pe utilizator (cea mai veche iese); curățare periodică a celor expirate.
9. POST-urile de autentificare: doar `application/json`, corp ≤ 2048 B, `Sec-Fetch-Site` (dacă e trimis) doar `same-origin`/`none`.
10. Jurnal: logare reușită/eșuată (cu motivul), delogare, refuz 403 pe rută admin, pornire/oprire rulare (cu utilizatorul); niciodată parola sau corpul cererii.
11. Scurtătura locală: activă doar cu `MCC_AUTH_LOCAL` setată, fără `MCC_AUTH_OBLIGATORIE=1` și fără antetul `X-Real-IP` în cerere; cu `MCC_AUTH_OBLIGATORIE=1` și `MCC_AUTH_LOCAL` setată, serverul refuză să pornească (mesaj, ieșire cu cod ≠ 0).
12. `/pdf`: `Cache-Control: private, max-age=86400`; răspunsurile JSON: `Cache-Control: no-store`.
13. nginx: `proxy_set_header X-Real-IP $remote_addr; proxy_set_header X-Forwarded-Proto $scheme;` în ambele `location` spre :8765; în blocul 443: `add_header X-Frame-Options "DENY" always; add_header Content-Security-Policy "frame-ancestors 'none'" always; add_header X-Content-Type-Options "nosniff" always;`. `deploy/mcc.service`: `Environment=MCC_AUTH_OBLIGATORIE=1`.
14. Interfața: după logare, întoarcerea doar la o rută internă care începe cu `#/`; parola nu se păstrează în stare după trimitere; câmpul are `autocomplete="current-password"`.

---

### Task A (backend): `app/autentificare.py` + poarta din server + deploy

**Files:** Create `app/autentificare.py`, `app/test_autentificare.py`, `app/test_server_autentificare.py`. Modify `app/server.py` (Handler: poartă, rute noi, jurnal la rulări, Cache-Control), `requirements.txt`, `.env.example`, `deploy/nginx-mcc.conf`, `deploy/mcc.service`, `deploy/INSTALARE.md` (secțiune „Autentificare AD”: ce cere de la IT — adresa DC pentru LDAPS, CA-ul, cele două grupuri), `README.md` (o secțiune scurtă).

**Interfaces (Produces, folosite de interfață — exact cum sunt în Global Constraints):** rutele, codurile de eroare, cookie-ul.

`app/autentificare.py` expune (pentru teste și server):
- `class Config` cu `din_mediu(env=os.environ) -> Config` și `problema() -> str | None` (motivul pentru care nu se poate loga: lipsă URL, protocol greșit etc.).
- `class Rezultat(NamedTuple)`: `ok: bool, utilizator: str, nume: str, rol: str | None, motiv: str | None`.
- `class Autentificator` cu `__init__(config, verificator=None, ceas=time.monotonic)` unde `verificator(utilizator, parola) -> tuple[nume, rol] | None` poate fi înlocuit în teste (implicit: LDAP real cu `ldap3`), și `autentifica(utilizator, parola, ip) -> Rezultat`.
- `class Sesiuni` cu `creeaza(utilizator, nume, rol) -> str` (identificatorul în clar, o singură dată), `citeste(id) -> dict | None` (reînnoiește activitatea), `sterge(id)`, `curata()`.
- `def jurnal(eveniment: dict)`.
- `def mod_local(env, antete) -> str | None` (rolul local sau None) și `def verifica_pornire(env) -> str | None` (motivul refuzului de pornire).

- [ ] **Step 1:** scrie `app/test_autentificare.py` (unittest, fără rețea) acoperind: cerințele 1, 2, 3 (un utilizator cu `*)(` e respins înainte de verificator), 4 (`ldap://` → `config.problema()`), 5 (verificatorul care aruncă timeout → `ad_indisponibil`), 6 (al 6-lea eșec → `prea_multe_incercari`, verificatorul nu mai e apelat; succes → contor resetat), 7, 8 (expirare la inactivitate cu ceas simulat; maximum 12 h; maximum 10 sesiuni), 10 (jurnalul nu conține parola — caută textul parolei în fișierul scris într-un director temporar), 11 (`mod_local`, `verifica_pornire`), rolurile (admin + analist → admin; niciunul → `fara_rol`). Rulează: pică (modulul lipsește).
- [ ] **Step 2:** implementează `app/autentificare.py`; verificatorul LDAP real: bind UPN `utilizator@MCC_LDAP_DOMENIU` pe `ldaps://` cu `Tls(validate=ssl.CERT_REQUIRED, ca_certs_file=MCC_LDAP_CA or None)`, `auto_bind`, `receive_timeout=10`, `connect_timeout=5`; căutare `(&(objectClass=user)(sAMAccountName=<esc>))` în `MCC_LDAP_BAZA` pentru `displayName`; apartenența la fiecare grup cu `(&(sAMAccountName=<esc>)(memberOf:1.2.840.113556.1.4.1941:=<DN grup escapat>))`. Rulează testele: trec.
- [ ] **Step 3:** scrie `app/test_server_autentificare.py`: pornește `Handler` pe un port liber, cu `Autentificator` cu verificator simulat (utilizatori `ana`/`analist`, `adi`/`admin`), într-un fir; verifică: 401 pe `/api/sumar`, `/pdf?u=x`, `/logos/x.svg`, `/harta.html`, `/`; logare → cookie cu atributele cerute (și `Secure` doar cu `X-Forwarded-Proto: https`); cu cookie, `/api/sesiune` 200; analist → 403 pe fiecare rută admin, admin → nu 403; delogare → 401 după; POST fără JSON → 415; `Sec-Fetch-Site: cross-site` → 403; `mod_local` cu `X-Real-IP` → 401. Rutele de date pot cere baza: dacă baza nu răspunde, testul acceptă orice cod diferit de 401/403 pentru „trecut de poartă”. Rulează: pică.
- [ ] **Step 4:** integrează în `app/server.py`: poarta la începutul `do_GET`/`do_POST`, rutele noi, jurnal la `porneste`/`opreste`, `Cache-Control`, `verifica_pornire` în `__main__`, citirea configurației o dată la pornire. Rulează ambele fișiere de test + `python app/test_rulari.py` (existent): trec.
- [ ] **Step 5:** `requirements.txt` (`ldap3>=2.9  # autentificarea AD, app/autentificare.py`), `pip install ldap3`, `.env.example` (variabilele cu exemple fictive, fără date reale), deploy (cerința 13), `INSTALARE.md`, `README.md`.
- [ ] **Step 6:** commit: `server: autentificare AD (LDAPS) cu roluri admin/analist, sesiuni și poarta pe toate datele`.

### Task B (interfața): logare, sesiune, roluri

**Files:** Create `web/src/auth/` (context + hook `useSesiune()`, `PaginaLogare.tsx`, `AccesInterzis.tsx`), `web/src/i18n/dict/auth.ts` (+ înregistrare în `dict/index.ts`), CSS în `web/src/styles/auth.css`. Modify `web/src/api/client.ts` (401 → eveniment „sesiune expirată”; `apiPost` primește și cookie implicit — `fetch` same-origin trimite cookie-urile), `web/src/main.tsx` sau `App.tsx` (învelirea cu providerul; fără sesiune → pagina de logare), `web/src/layout/AppShell.tsx` (numele, rolul, „Ieșire” în `.picior`; meniul filtrat), `web/src/pagini.ts` (marcaj `admin: true` pe `logging`, `rulare`), `web/src/App.tsx` (rutele admin → `AccesInterzis` pentru analist), `web/src/pages/Overview.tsx` (secțiunea de rulări doar pentru admin).

**Interfaces (Consumes):** exact rutele, codurile și forma răspunsurilor din Global Constraints. `GET /api/sesiune` cu `local: true` = scurtătura de pe laptop (fără buton „Ieșire”, cu mențiunea „local”).

- [ ] **Step 1:** providerul: la pornire `GET /api/sesiune`; stări: `se_incarca` | `neautentificat` | `{utilizator, nume, rol, local}`; `logare(utilizator, parola)` (POST JSON), `delogare()`; la evenimentul 401 din `client.ts` → `neautentificat` și se golește cache-ul React Query.
- [ ] **Step 2:** `PaginaLogare`: pe tot ecranul, cu marca aplicației, câmpurile (AntD `Form`, `Input`, `Input.Password` cu `autocomplete="username"` / `"current-password"`), butonul, mesajele pe cod (`date_invalide`, `fara_rol`, `prea_multe_incercari`, `ad_indisponibil`), RO/EN și tema aleasă (comutatoarele vizibile și aici); după logare, întoarcere la `#/…` memorat (cerința 14).
- [ ] **Step 3:** meniul, rutele admin, Overview, subsolul cu utilizatorul.
- [ ] **Step 4:** verificare: `npm run typecheck && npm run build`; testare manuală în browser cu un server de test (vezi Task C) sau, până atunci, cu răspunsuri simulate prin `page.route` în Playwright (logare reușită admin/analist, eșec pe fiecare cod, expirare → logare → întoarcere la pagina din care a venit, meniul analistului fără paginile admin, `#/rulare` → acces interzis). Capturi luminos/întunecat ale paginii de logare.
- [ ] **Step 5:** commit: `web: pagina de logare, sesiunea și meniul după rol`.

### Task C (controller, după A și B): integrare cap-coadă

- [ ] Unirea ramurilor; serverul de test pe alt port cu verificator simulat și `web/dist` servit pe `/app/` (vezi `translate_path`); Playwright: logare admin și analist, meniul, 403 pe rutele admin din interfață, ieșire, sesiune expirată.
- [ ] Rulează `verifica_ui.py` pe 5173 cu `MCC_AUTH_LOCAL=admin` (laptopul lui Robert): nimic nu se schimbă pentru el.
- [ ] Audit de securitate (security-auditor) pe tot diff-ul; corecturile într-o singură rundă.
