# Ultima actualizare a memoriilor

- Commit de referință: `7bad344` (07.10.2026, butonul Vox jos în bara laterală, ramura `intreaba-datele`).
- La actualizare: `git log --stat 7bad344..HEAD`; actualizează doar memoriile atinse (migrări noi, rute noi în `RUTE`, pagini noi în `web/src/pages/`, module noi în `ingest/`, schimbări de mediu), apoi scrie aici noul commit de referință.
- Se declanșează prin comanda `/actualizeaza-memoria` sau prin mementoul automat de după `git commit` (hook-ul din repo, `.claude/hooks/serena_memento.py`, legat în `.claude/settings.json`).
