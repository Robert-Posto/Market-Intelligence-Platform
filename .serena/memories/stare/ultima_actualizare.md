# Ultima actualizare a memoriilor

- Commit de referință: `709fcae` (08.10.2026, `vox-chatbot`: fișa Vox citește corect, butoane fără model, cache de o oră).
- La actualizare: `git log --stat 34720bd..HEAD`; actualizează doar memoriile atinse (migrări noi, rute noi în `RUTE`, pagini noi în `web/src/pages/`, module noi în `ingest/`, schimbări de mediu), apoi scrie aici noul commit de referință.
- Se declanșează prin comanda `/actualizeaza-memoria` sau prin mementoul automat de după `git commit` (hook-ul din repo, `.claude/hooks/serena_memento.py`, legat în `.claude/settings.json`).
