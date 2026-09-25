# MIP — evaluarea a trei servere MCP

*25.09.2026 · Chrome DevTools MCP, Firecrawl MCP, Apify MCP · evaluare pe documentația publică, fără instalare și fără teste pe site-urile băncilor.*

## Pe scurt

| MCP | Ce este | Verdict, cu regulile actuale | Verdict, dacă ocolirea blocajelor ar fi permisă |
|---|---|---|---|
| **Chrome DevTools** | Control și depanare a unui Chrome real de către un agent AI (Google, Apache-2.0) | **Doar pentru dezvoltare**, opțional | La fel — nu aduce nimic la colectare |
| **Firecrawl** | Serviciu de colectare web: randare JS, crawl, extragere structurată (cloud sau self-host, AGPL-3.0) | **Nu** | **Merită pentru cele 5 bănci blocate** (BT, CEC, Intesa, UniCredit, Revolut) |
| **Apify** | Platformă cloud cu peste 6.000 de „actori" de colectare, mai ales comunitari | **Nu** | **Merită cel mai mult**: Android, recenzii Google Maps, TikTok, Trustpilot, joburi |

## Chrome DevTools MCP

| Plusuri | Minusuri |
|---|---|
| Proiect oficial Google, licență Apache-2.0, activ | Nu verifică robots.txt și se prezintă ca un Chrome obișnuit — nepotrivit pentru colectare |
| Depanare interactivă a aplicației: consolă, cereri de rețea, stiluri, capturi, Lighthouse, trace de performanță | Cere Node.js (neinstalat acum) și Chrome |
| Înlocuiește scripturile de captură scrise la fiecare verificare | Poate fi legat de Chrome-ul personal (sesiuni, cookie-uri) — trebuie pornit mereu cu profil temporar |
| Efort de instalare mic | Proiect tânăr, se schimbă des |

**Recomandare:** opțional, doar în mediul de dezvoltare, pornit cu profil izolat. Nu intră în colectare.

## Firecrawl MCP

| Plusuri | Minusuri |
|---|---|
| Randează paginile JS și descoperă surse (map, crawl) | Moduri „stealth" cu proxy-uri rezidențiale anti-bot; modul „auto" poate trece singur pe ele |
| Extragere structurată din PDF și HTML | Robots.txt respectat implicit, dar se poate dezactiva (plan Enterprise) |
| Poate trece de blocajele celor 5 bănci (modul stealth) | Se prezintă ca „Firecrawl"; nu e clar că se poate seta UA-ul nostru |
| Varianta self-host e gratuită (dar fără stealth nu aduce mare lucru peste Playwright-ul propriu) | Datele trec prin serverele lor din SUA (jurisdicție California) |
| Cost rezonabil: Standard 99 $/lună (~100.000 de pagini; stealth ~4 credite/pagină) | Nu e clar că dă octeții originali ai PDF-urilor — fără ei nu mai funcționează Bronze, amprentele și vizualizatorul de dovezi |

**Recomandare:** nu, cu regulile actuale. Dacă ocolirea ar fi aprobată: doar pentru cele 5 bănci blocate, cu extracția păstrată pe parserele proprii (efort mediu).

## Apify MCP

| Plusuri | Minusuri |
|---|---|
| Actori gata făcuți pentru golurile din capitolul 2: Google Play, recenzii Google Maps, TikTok, Trustpilot, joburi | Aproape toți fac scraping cu proxy-uri rezidențiale și anti-bot, nu prin API oficial |
| Cost mic: 29–199 $/lună plus prețul actorului (câțiva cenți la 1.000 de recenzii) | Actori comunitari: calitate variabilă, se strică la schimbările platformelor |
| Android ar avea aceeași structură ca iOS — efort mic | Robots.txt-ul Google Play interzice adresele de recenzii; ToS-urile Google, LinkedIn, Trustpilot interzic colectarea automată |
| Recenziile Google Maps ar aduce înapoi nota și programul sucursalelor pe hartă | Răspunderea legală rămâne integral la utilizator (termenii Apify) |
| | Recenziile au autori persoane fizice — GDPR (pseudonimizare, minimizare) |

**Recomandare:** nu, cu regulile actuale. Dacă ar fi aprobat: întâi Google Play, apoi recenziile Google Maps.

## Ce a ieșit în plus din evaluare

| Subiect | Constatare |
|---|---|
| **Campanii Meta (2.4)** | API-ul oficial Meta Ad Library dă **toate reclamele din UE**, deci și din România — gratuit, fără Apify; cere cont de dezvoltator verificat (aprobare 1–4 săptămâni) |
| **TikTok** | API-ul oficial e doar pentru cercetare necomercială — nu se poate folosi |
| **Android** | API-ul oficial Google Play dă recenzii doar pentru aplicațiile proprii; de verificat dacă pagina publică a aplicației e permisă de robots.txt (varianta folosită la App Store) |
| **Băncile blocate** | Orice soluție pentru ele înseamnă ocolirea blocajului — nu există cale oficială |

## Riscul ocolirii, dacă se ia în calcul

| Risc | De ce contează |
|---|---|
| **Penal** | Accesul la un sistem informatic prin încălcarea măsurilor de securitate e infracțiune (Codul penal, art. 360); WAF-ul și captcha-ul unei bănci sunt astfel de măsuri |
| **Identificare** | UA-ul actual se identifică drept Libra Bank; ocolirea presupune ascunderea lui — sau, mai rău, o bancă vede că Libra îi ocolește protecția |
| **Contractual** | Încălcarea ToS-urilor Google, LinkedIn, Trustpilot; răspunderea e la noi |

**Recomandare finală:** niciun MCP în aplicație deocamdată; cererea de acces la API-ul oficial Meta pentru 2.4. Recenziile Google Play și Google Maps (date publice, risc mai ales contractual) se pot discuta cu juridicul; ocolirea protecției celor 5 bănci (risc penal) doar cu aprobare scrisă de la juridic și securitate.
