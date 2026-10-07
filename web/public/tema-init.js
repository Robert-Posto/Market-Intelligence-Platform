/* Tema aleasă (localStorage „mcc-tema”), pusă pe <html> înainte de primul cadru, ca pagina
   să nu clipească în tema greșită. Aceeași validare ca în src/tema/context.ts: orice altă
   valoare înseamnă „ca sistemul”. Fișier separat, nu script inline: merge și sub un CSP
   cu script-src 'self'. `color-scheme` face și fundalul implicit închis până vine CSS-ul. */
(function () {
  var t = null
  try { t = localStorage.getItem('mcc-tema') } catch (e) { /* fără stocare: ca sistemul */ }
  var intunecat = t === 'intunecat' ||
    (t !== 'luminos' && window.matchMedia('(prefers-color-scheme: dark)').matches)
  var html = document.documentElement
  html.setAttribute('data-theme', intunecat ? 'dark' : 'light')
  html.style.colorScheme = intunecat ? 'dark' : 'light'
})()
