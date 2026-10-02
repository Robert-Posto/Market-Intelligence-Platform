# web — interfața pe Next.js

Next.js (App Router) doar pentru interfață. Datele vin din API-ul Python
(`app/server.py`), care rămâne singurul loc care citește baza: `next.config.mjs`
rescrie `/api/*`, `/logos/*` și `/pdf` către el. Crawler-ul și ingest-ul rămân Python.

```bash
python app/server.py            # din rădăcina repo-ului: API-ul, pe :8765
cd web && npm install
npm run dev                     # http://localhost:3001
npm run build                   # verificarea de compilare
```

`MIP_API` schimbă adresa API-ului (implicit `http://localhost:8765`);
`NEXT_PUBLIC_MIP_VECHI` e aplicația veche, unde duc paginile încă neportate.

## Ce e portat (02.10.2026)

| pagina | stare |
|---|---|
| Produse & prețuri — comparația cu Libra | portată (`app/produse`) |
| Produse & prețuri — matricea „Comisioane pe bănci” | link spre aplicația veche |
| celelalte 11 pagini | link spre aplicația veche, din meniu |

## Cum se portează o pagină

1. Logica fără HTML în `lib/<pagina>.js` (ca `lib/produse.js`), componentele în
   `components/<pagina>/`, ruta în `app/<id>/page.jsx` cu `<Antet id="<id>" />`.
2. `id`-ul intră în `PORTATE` din `lib/pagini.js`: meniul trece pe ruta Next.js.
3. Stilurile sunt deja în `app/globals.css` (copiate din `app/index.html`).
4. Starea filtrelor stă în URL (`useSearchParams`), ca o vedere să se poată trimite.
5. `npm run build` fără erori și pagina verificată în browser, pe datele reale.
