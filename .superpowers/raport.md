# Raport: derulare laterală la 2.4 (branch campanii-scroll)

## Cauza (măsurată; temele luminos și intunecat identice)
`<main id="principal">` derula doar la YouTube @1280; restul derulării era în `.ant-table-body` (în chenarul fiecărui tabel).
Lățimea vine din min-content-ul coloanelor (tableLayout auto + scroll.x 100%): tabelul nu poate fi strâns sub suma lor.

Înainte (scrollWidth > clientWidth):
- Site: 1187 > 1072 @1440, 1189 > 998 @1366, 1189 > 912 @1280
- Google: 936 > 912 @1280
- Rețele: 998 > 912 @1280
- YouTube @1280: main 1056 > 1014, `.cm-banda` 1025 > 952, `.cm-chipuri` 173 > 84
- Comunicate, Bing: fără derulare

Ce lărgea:
- Site: banca și perioada cu `white-space: nowrap` (317 și 182 px); titlul „din adresă” e un nume de fișier fără spații
  („…pdf.coredownload.inline”), deci coloana Campanie nu scădea sub 248 px.
- Google: banca `nw` (210 px).
- Rețele: linkuri cu `max-width: 170px` => 4 coloane de 186 px.
- YouTube: `.cm-banda` nu rupe rândul; chipurile se strângeau la 84 px și ieșeau din bandă.
Capul lipit și rândul fantomă nu sunt cauza: coloanele cu cap lung au 84-98 px.

## Modificări (dimensiuni și rupere de text, fără overflow:hidden)
- `Site.tsx`: banca fără `cs-nowrap`; titlul din adresă are `cs-titlu`; perioada fără nowrap pe celulă, fiecare dată în `.cs-data` (nowrap), deci se rupe doar la liniuță.
- `campanii_site.css`: `.cs-titlu { overflow-wrap: anywhere }`, `.cs-data { white-space: nowrap }`.
- `Google.tsx`: banca fără `nw`.
- `campanii_youtube.css`: `max-width` linkuri rețele 170 -> 140 px (textul întreg rămâne în `title` pe celulă); `.yt-banda { flex-wrap: wrap }`, `.yt-banda .cm-chipuri { flex: 1 1 260px }`.
- `verifica_ui.py`: verificarea `lateral` (`v_scroll_lateral`).
Cod comun (Tabel.tsx, lipire.tsx, global.css) neatins.

## Rezultate
- Min-content după: Site 854, Google 855, Rețele 878 (disponibil la 1280: 912).
- Măsurători pe 6 secțiuni x 1440/1366/1280 x 2 teme: nicio derulare.
- `verifica_ui.py --doar lateral,capete`: 45 ok, 0 picate (2.4 x 6, produse, rate?categorie=credite, coada, surse, la 1440 și 1280; capete aliniate).
- `npm run typecheck && npm run build`: ok.
- Capturi 1280 înainte/după citite: Site, YouTube, Rețele, Google.

## De reținut
- Site @1280: perioada pe 2 rânduri, banca pe 2-3 rânduri; rânduri mai înalte, fără derulare.
- Sub 1280 px tabelele pot derula din nou (cerința era >= 1280).
- Vite din PowerShell cere `C:\Program Files\nodejs` în PATH.
