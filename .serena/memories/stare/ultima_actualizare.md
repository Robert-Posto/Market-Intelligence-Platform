# Ultima actualizare a memoriilor

- Commit de referință: `34720bd` (07.10.2026, `vox-chatbot`: clasamentele Vox, celulele din 2.1 / 2.2 într-un singur loc, interpretarea la temperatura 0).
- La actualizare: `git log --stat 34720bd..HEAD`; actualizează doar memoriile atinse (migrări noi, rute noi în `RUTE`, pagini noi în `web/src/pages/`, module noi în `ingest/`, schimbări de mediu), apoi scrie aici noul commit de referință.
- Se declanșează prin comanda `/actualizeaza-memoria` sau prin mementoul automat de după `git commit` (hook-ul din repo, `.claude/hooks/serena_memento.py`, legat în `.claude/settings.json`).
