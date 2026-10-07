# Ultima actualizare a memoriilor

- Commit de referință: `b9dad3a` (07.10.2026, `vox-chatbot`: segmentul în `/api/celula` și în Vox, căderea filtrelor pe „nespecificat în sursă”, motivul lipsei unei bănci).
- La actualizare: `git log --stat b9dad3a..HEAD`; actualizează doar memoriile atinse (migrări noi, rute noi în `RUTE`, pagini noi în `web/src/pages/`, module noi în `ingest/`, schimbări de mediu), apoi scrie aici noul commit de referință.
- Se declanșează prin comanda `/actualizeaza-memoria` sau prin mementoul automat de după `git commit` (hook-ul din repo, `.claude/hooks/serena_memento.py`, legat în `.claude/settings.json`).
