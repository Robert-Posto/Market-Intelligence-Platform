# Ultima actualizare a memoriilor

- Commit de referință: `38717c5` (07.10.2026, main unit în `vox-chatbot`: autentificarea AD și tema întunecată, peste istoricul conversațiilor Vox).
- La actualizare: `git log --stat 38717c5..HEAD`; actualizează doar memoriile atinse (migrări noi, rute noi în `RUTE`, pagini noi în `web/src/pages/`, module noi în `ingest/`, schimbări de mediu), apoi scrie aici noul commit de referință.
- Se declanșează prin comanda `/actualizeaza-memoria` sau prin mementoul automat de după `git commit` (hook-ul din repo, `.claude/hooks/serena_memento.py`, legat în `.claude/settings.json`).
