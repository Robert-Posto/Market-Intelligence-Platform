# O secțiune nouă cap-coadă (modelul folosit la Android, 05.10.2026)

1. `db/migration_NNN_<nume>.sql` (următorul număr; tabele cu `provenienta`), rând în tabelul „Migrări” din README.
2. Loader în `ingest/` (tranzacție unică, numărători de control, test în `ingest/test_*.py`).
3. Funcție + intrare în `RUTE` în `app/server.py`; listele mari la cerere (`?param=`), nu în răspunsul principal. Repornește serverul după modificare.
4. Schemă Zod în `shared/src/<zonă>.ts` + export în `shared/src/index.ts`.
5. Cererea în `web/src/api/<zonă>.ts`; pagina sau secțiunea în `web/src/pages/…`; textele în `web/src/i18n/dict/<zonă>.ts` + înregistrare în `dict/index.ts`; CSS în `web/src/styles/<zonă>.css`.
6. Verificare: `npm run typecheck && npm run build`, pagina în RO și EN, consola curată.
- `Sertar` e legat de `/api/celula` (prețuri); pentru alt detaliu, Drawer AntD cu același aspect (ca în `web/src/pages/rate_mobil/android/Detaliu.tsx`).
- Orice `href` din date colectate se verifică la `http(s)` (React 18 nu blochează `javascript:`); model: `web/src/pages/Document.tsx`, `web/src/i18n/index.tsx`.
