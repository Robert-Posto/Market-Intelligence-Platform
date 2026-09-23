# Cât de recent și-a atins fiecare bancă lista de tarife

Din `Last-Modified`, strâns de sonda de schimbări — informație pe
care serverul o dă oricum la un HEAD. 53 documente de
tarife cu dată, la 12 bănci.

**Coloana care contează e „cel mai nou”.** Băncile lasă pe site toate
versiunile succesive (BRCI are „mai 2024” și „vers oct 2024”
simultan), deci cel mai *vechi* document măsoară adâncimea arhivei,
nu prospețimea prețurilor.

Coloana **dovadă** e o verificare independentă: multe bănci pun data
în numele fișierului. Unde ea și `Last-Modified` se potrivesc (±14
zile), data nu mai e o presupunere despre server — e confirmată de
bancă. Unde diferă, scrie amândouă, fără să aleg una.

| bancă | doc | cel mai nou | zile | dovadă | arhivă păstrată |
|---|---:|---|---:|---|---|
| brd | 2 | 2026-09-21 | 0 | numele nu are dată | 2026-08-03 (49 z) |
| bcr | 17 | 2026-09-18 | 2 | numele nu are dată | 2018-06-11 (3023 z) |
| creditcoop | 5 | 2026-09-10 | 10 | numele nu are dată | 2026-09-10 (10 z) |
| raiffeisen | 2 | 2026-08-31 | 20 | da, numele zice 2026-09-01 | 2026-06-26 (86 z) |
| libra | 11 | 2026-08-25 | 26 | numele nu are dată | 2024-05-16 (857 z) |
| brci | 6 | 2026-08-17 | 34 | numele nu are dată | 2024-05-29 (845 z) |
| salt | 1 | 2026-08-03 | 48 | numele nu are dată | 2026-08-03 (48 z) |
| eximbank | 1 | 2026-04-08 | 165 | numele nu are dată | 2026-04-08 (165 z) |
| techventures | 4 | 2026-02-12 | 220 | **nu**: numele zice 2026-04-14 | 2025-11-11 (313 z) |
| garanti | 1 | 2025-11-13 | 311 | da, numele zice 2025-11-10 | 2025-11-13 (311 z) |
| tbi | 2 | 2024-08-01 | 781 | **nu**: numele zice 2019-12-15 | 2024-07-31 (782 z) |
| bcrlocuinte | 1 | 2020-07-08 | 2265 | numele nu are dată | 2020-07-08 (2265 z) |

Pe tot setul: 8 documente în care cele două date se
potrivesc, 9 în care nu, 36 fără dată în nume.

### Unde cele două date nu se potrivesc

- **bcr** · server 2024-10-01, nume 2024-06-19 — `Document-de-informare-cu-privire-la-comisioane-cont-EUR_19.06.20`
- **brci** · server 2026-04-15, nume 2025-11-24 — `DOBANZI DEPOZITE LA TERMEN PJ 24.11.2025_cs.pdf`
- **brci** · server 2024-11-20, nume 2024-10-01 — `Lista Tarife si Comisioane PJ vers oct 2024.pdf`
- **raiffeisen** · server 2026-06-26, nume 2026-09-01 — `20260901-Tarife-si-comisioane-IMM-si-profesii-liberale.pdf.cored`
- **tbi** · server 2024-08-01, nume 2019-12-15 — `Lista_de_dobanzi_taxe_si_comisioane_pentru_persoane_juridice_inc`
- **techventures** · server 2025-11-11, nume 2025-06-02 — `dobanzi-depozite-pj-02062025.pdf`
- **techventures** · server 2025-11-11, nume 2025-06-02 — `dobanzi-depozite-pj-02062025.pdf`
- **techventures** · server 2026-02-12, nume 2026-04-14 — `lista-de-tarife-si-comisioane-persoane-fizice-valabile-din-14042`
- **techventures** · server 2026-02-12, nume 2026-04-14 — `lista-de-tarife-si-comisioane-aplicabile-entitatilor-economice-1`

## Atenție: date puse în masă

Mai multe fișiere ale aceleiași bănci au **exact** aceeași dată.
Aceea e aproape sigur o operație în masă — migrare de site sau
copiere de pe alt server — nu o republicare editorială. Pentru
băncile de mai jos, data nu spune când s-au schimbat tarifele.

- **bcr**: 3 fișiere, toate cu 2026-05-27
- **bcr**: 3 fișiere, toate cu 2026-07-02
- **creditcoop**: 5 fișiere, toate cu 2026-09-10
- **libra**: 5 fișiere, toate cu 2026-08-25

## Fără dată de la server

Aici nu se poate spune nimic: serverul nu trimite `Last-Modified`,
ori îl pune la ora cererii (și atunci se aruncă — vezi
`crawler/urme.py`, `SECUNDE_STAMPILA`).

- procredit: 5 documente de tarife
- raiffeisen: 3 documente de tarife
- salt: 1 documente de tarife
