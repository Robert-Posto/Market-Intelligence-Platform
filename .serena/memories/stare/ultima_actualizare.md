# Ultima actualizare a memoriilor

- Commit de referință: `8cf7956` (08.10.2026, `vox-chatbot`: unirea cu main-ul lui Robert — lista albă de fișiere statice, garda de rețea internă la `/pdf`, modul local doar pe loopback —, `PillSegment` și evaluarea Vox cu 44 de întrebări).
- La actualizare: `git log --stat 34720bd..HEAD`; actualizează doar memoriile atinse (migrări noi, rute noi în `RUTE`, pagini noi în `web/src/pages/`, module noi în `ingest/`, schimbări de mediu), apoi scrie aici noul commit de referință.
- Se declanșează prin comanda `/actualizeaza-memoria` sau prin mementoul automat de după `git commit` (hook-ul din repo, `.claude/hooks/serena_memento.py`, legat în `.claude/settings.json`).
