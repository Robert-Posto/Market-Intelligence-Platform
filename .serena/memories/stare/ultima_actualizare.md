# Ultima actualizare a memoriilor

- Commit de referință: `f18f3f4` (07.10.2026, istoricul conversațiilor Vox: `Istoric`, `/api/vox/conversatii`, `pages/vox/`, ramura `vox-chatbot`). Main, unit în ramură tot pe 07.10, a adus tema întunecată (memoriile ei sunt la zi, în `web/sectiune_noua`) și autentificarea AD (`app/autentificare.py`, `Handler._poarta`, `web/src/auth/`), care nu e încă în memorii.
- La actualizare: `git log --stat f18f3f4..HEAD`; actualizează doar memoriile atinse (migrări noi, rute noi în `RUTE`, pagini noi în `web/src/pages/`, module noi în `ingest/`, schimbări de mediu), apoi scrie aici noul commit de referință.
- Se declanșează prin comanda `/actualizeaza-memoria` sau prin mementoul automat de după `git commit` (hook-ul din repo, `.claude/hooks/serena_memento.py`, legat în `.claude/settings.json`).
