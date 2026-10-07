# Autentificare cu Active Directory (LDAP), roluri admin și analist: design

06.10.2026 · aprobat de Robert în conversație (variantele recomandate la toate cele 4 întrebări)

## 1. Ce se cere

Aplicația de pe `mcc-test.libra.bank` nu are azi nicio autentificare: nginx servește interfața și trimite `/api`
la `app/server.py`, deci oricine din rețea vede tot. Se cere logare cu contul AD și două roluri.

Criterii de reușită:
1. Pe server, nicio dată (`/api/*`, `/pdf`, `/logos`) nu se poate citi fără sesiune validă (401).
2. Logarea folosește contul de Windows (utilizator + parolă), verificat la Active Directory prin **LDAPS** (TLS,
   certificat verificat). Parola nu se salvează și nu se scrie nicăieri.
3. Rolul vine din grupurile AD, inclusiv din grupuri imbricate: `MCC-Admin` → admin, `MCC-Analist` → analist (numele
   exacte ale grupurilor se configurează). Cine e în ambele e admin. Cine nu e în niciunul nu intră (403, mesaj clar).
4. Adminul poate în plus: **Rulare manuală** (inclusiv rulările din Overview, `/api/rulari*`, `/api/rulare_manuala*`) și
   **Joburi și erori** (`/api/jobs`). Verificarea e pe server (403 pentru analist), iar interfața ascunde paginile.
5. Sesiune prin cookie `HttpOnly`, `SameSite=Strict`, `Secure` pe HTTPS; expiră după 8 ore fără activitate (configurabil);
   buton „Ieșire”.
6. Încercările greșite repetate sunt limitate (ca aplicația să nu poată fi folosită la blocarea conturilor din AD).
7. Fiecare logare, reușită sau nu, se scrie într-un jurnal (fără parolă).
8. Pe laptop (dezvoltare), cu `MCC_AUTH_LOCAL=admin` în `.env`, aplicația te consideră admin fără logare; pe server
   setarea nu poate avea efect (vezi 4.4).
9. Setările AD stau în `.env` (exemplu în `.env.example`); fără ele, pe server, logarea răspunde 503 cu mesaj clar,
   nu cade.

## 2. În afara scopului

- Logare automată cu contul de Windows (Kerberos/SPNEGO): se poate adăuga peste același model de sesiune.
- Gestionarea utilizatorilor în aplicație: accesul se dă din AD (grupuri).
- Interfața veche (`app/index.html`): pe server nu e publicată de nginx; local merge cu `MCC_AUTH_LOCAL`.
- Scrierea în baza de date: serverul rămâne doar de citire (sesiunile în memorie, jurnalul în fișier).

## 3. Starea de azi

- `app/server.py`: `http.server`, `Handler.do_GET` (rutele din `RUTE`, `/pdf`, fișiere statice) și `do_POST`
  (doar `/api/rulari/porneste|opreste`, cu verificările din `app/rulari.py`: Host, Origin, `Sec-Fetch-Site`, token).
  Ascultă doar pe loopback (`verify_request`).
- `deploy/nginx-mcc.conf`: HTTPS cu certificatul `*.libra.bank`; `location ~ ^/(api|logos|pdf)` și `(pdf|harta).html`
  merg la `127.0.0.1:8765` **fără** antete despre clientul real; `deploy/mcc.service` (systemd).
- Interfața: `web/src/api/client.ts` (`api()`, `apiPost()`), meniul din `web/src/pagini.ts`, rutele în `App.tsx`,
  paginile admin: `logging` (Joburi și erori), `rulare` (Rulare manuală), plus secțiunea de rulări din Overview.

## 4. Design

### 4.1 Modulul `app/autentificare.py` (fără dependențe de server, testabil separat)
- **Configurare** din mediu: `MCC_LDAP_URL` (ex. `ldaps://dc01.libra.bank:636`), `MCC_LDAP_DOMENIU` (sufixul UPN,
  ex. `libra.bank`), `MCC_LDAP_BAZA` (ex. `DC=libra,DC=bank`), `MCC_LDAP_GRUP_ADMIN`, `MCC_LDAP_GRUP_ANALIST` (DN-uri),
  opțional `MCC_LDAP_CA` (fișierul CA; altfel depozitul sistemului), `MCC_SESIUNE_ORE` (implicit 8).
- **Validare** înainte de AD: utilizatorul doar `[A-Za-z0-9._-]{1,64}` (numele scurt, fără domeniu; un `DOMENIU\x` sau
  `x@domeniu` se reduce la `x`); **parola goală se refuză** (AD acceptă „unauthenticated bind” cu parolă goală).
- **Verificarea**: bind ca `utilizator@MCC_LDAP_DOMENIU` cu parola, pe LDAPS cu certificat verificat (`CERT_REQUIRED`),
  timeout de conectare 5 s; apoi, cu aceeași conexiune, o căutare a utilizatorului (`sAMAccountName`, valoare escapată)
  care aduce `displayName` și, pentru fiecare grup, apartenența prin regula AD pentru grupuri imbricate
  (`memberOf:1.2.840.113556.1.4.1941:=<DN grup>`). Biblioteca: `ldap3` (Python pur), adăugată în `requirements.txt`.
- **Rezultat**: `Rezultat(ok, utilizator, nume, rol, motiv)`; motivele: `invalid` (parolă/utilizator greșit, mesaj
  generic), `fara_rol`, `indisponibil` (AD nu răspunde / neconfigurat), `limitat`.
- **Limitarea**: în memorie, cu lacăt; maximum 3 eșecuri pe utilizator și 20 pe adresă IP în 30 de minute (după audit,
  07.10: configurabile prin `MCC_AUTH_MAX_INCERCARI`, `MCC_AUTH_MAX_PE_IP`, `MCC_AUTH_FEREASTRA_MIN`; „fără rol” se
  numără pe adresă) → `limitat`
  (429) fără să mai întrebe AD-ul.
- **Sesiuni**: în memorie, cu lacăt; identificatorul `secrets.token_urlsafe(32)`, ținut doar ca SHA-256; expirare după
  `MCC_SESIUNE_ORE` de inactivitate și maximum 12 ore de la logare; la delogare se șterge.
- **Jurnal**: o linie JSON pe eveniment în `loguri/autentificare.log` (moment, utilizator, IP, rezultat, motiv);
  niciodată parola.

### 4.2 Serverul
- Rute noi: `POST /api/autentificare` (`{utilizator, parola}` → 200 `{utilizator, nume, rol}` + cookie `mcc_sesiune`,
  sau 401/403/429/503), `GET /api/sesiune` (200 `{utilizator, nume, rol, local}` sau 401), `POST /api/delogare`.
- **Poarta**: orice cerere spre `/api/*`, `/pdf`, `/logos/*`, `/pdf.html`, `/harta.html` fără sesiune validă → 401
  (`{eroare: "neautentificat"}`), în afară de `/api/autentificare` și `/api/sesiune`. Rutele admin → 403 pentru analist.
- POST-urile noi cer `Content-Type: application/json`, corp ≤ 2 KB și resping `Sec-Fetch-Site` străin (ca la rulări).
- Cookie: `mcc_sesiune=<id>; HttpOnly; SameSite=Strict; Path=/; Max-Age=…`, plus `Secure` când cererea vine prin
  HTTPS (`X-Forwarded-Proto: https`, pus de nginx).
  - *Notă (07.10, după audit):* pe HTTPS numele e `__Host-mcc_sesiune` (`Secure`, `Path=/`, fără `Domain`), ca un alt
    site `*.libra.bank` să nu poată pune un cookie de sesiune; serverul citește și golește doar numele schemei curente
    (`mcc_sesiune` rămâne pe HTTP, pe laptop).
- Adresa clientului: `X-Real-IP` pus de nginx (`proxy_set_header X-Real-IP $remote_addr; X-Forwarded-Proto $scheme`);
  fără el, adresa socketului.

### 4.3 Interfața
- La pornire `GET /api/sesiune`; la 401 se arată pagina de logare (pe tot ecranul, fără meniu, RO/EN, cu tema aleasă);
  după logare, aplicația. Orice 401 ulterior (sesiune expirată) duce înapoi la logare, păstrând adresa paginii.
- În subsolul meniului: numele, rolul și „Ieșire”. Paginile admin dispar din meniu pentru analist, iar ruta lor arată
  „acces interzis”; secțiunea de rulări din Overview, la fel.
- Textele noi în dicționar, RO și EN.

### 4.4 Scurtătura de pe laptop
- `MCC_AUTH_LOCAL=admin` (sau `analist`) în `.env`: cererea e tratată ca a unui utilizator local cu acel rol **doar
  dacă**: serverul nu are `MCC_AUTH_OBLIGATORIE=1` și cererea nu poartă `X-Real-IP` (nginx îl pune mereu).
- `deploy/mcc.service` setează `MCC_AUTH_OBLIGATORIE=1`; cu ea, serverul refuză să pornească dacă `MCC_AUTH_LOCAL` e
  setată (mesaj clar), deci o greșeală de configurare nu deschide serverul.

## 5. Securitate

Analiza de amenințări (skill-ul threat-model) se face înainte de plan; constatările ei intră în plan ca cerințe.

## 6. Verificare
- Teste Python pentru `autentificare.py` cu un AD simulat (validare, parolă goală, roluri, grupuri, limitare,
  sesiuni, expirare, jurnal fără parolă).
- Teste de integrare pe server (pornit pe alt port, cu AD simulat): 401 fără sesiune pe fiecare tip de rută, 403
  pentru analist pe rutele admin, cookie cu atributele cerute, delogare, scurtătura locală refuzată cu `X-Real-IP`
  și la `MCC_AUTH_OBLIGATORIE=1`.
- Interfața: `npm run typecheck && npm run build`; în browser, logare, rol, ieșire, expirare, meniul analistului.
