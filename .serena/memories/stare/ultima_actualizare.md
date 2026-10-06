# Ultima actualizare a memoriilor

- Commit de referință: `91555ba` (06.10.2026, chatbotul Vox, ramura `intreaba-datele`).
- La actualizare: `git log --stat 91555ba..HEAD`; actualizează doar memoriile atinse (migrări noi, rute noi în `RUTE`, pagini noi în `web/src/pages/`, module noi în `ingest/`, schimbări de mediu), apoi scrie aici noul commit de referință.
- Se declanșează prin comanda `/actualizeaza-memoria` sau prin mementoul automat de după `git commit` (hook-ul din repo, `.claude/hooks/serena_memento.py`, legat în `.claude/settings.json`).
