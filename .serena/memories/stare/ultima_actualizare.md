# Ultima actualizare a memoriilor

- Commit de referință: `c92546b` (09.10.2026, `vox-chatbot`: Vox se deschide din bula din dreapta jos, `layout/BulaVox.tsx`, în locul butonului din bara laterală).
- La actualizare: `git log --stat <commit de referință>..HEAD`; actualizează doar memoriile atinse (migrări noi, rute noi în `RUTE`, pagini noi în `web/src/pages/`, module noi în `ingest/`, schimbări de mediu), apoi scrie aici noul commit de referință.
- Se declanșează prin comanda `/actualizeaza-memoria` sau prin mementoul automat de după `git commit` (hook-ul din repo, `.claude/hooks/serena_memento.py`, legat în `.claude/settings.json`).
