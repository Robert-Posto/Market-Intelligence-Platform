---
name: actualizeaza-memoria
description: Actualizează memoriile Serena ale proiectului curent (`.serena/memories/`) după schimbările din cod de la ultima actualizare. Folosește-l când utilizatorul cere „/actualizeaza-memoria”, „actualizează memoria Serena” sau când hook-ul serena-memento semnalează că un commit a schimbat structura codului.
argument-hint: "[tot]"
---

# Actualizează memoriile Serena

1. **Punctul de plecare:** citește memoria `stare/ultima_actualizare` (cu unealta Serena `read_memory`,
   sau `serena memories read stare/ultima_actualizare .` din rădăcina proiectului) și ia commit-ul de
   referință. Fără memorie sau cu `$ARGUMENTS` = `tot` → treci prin toate memoriile.
2. **Ce s-a schimbat:** `git log --stat <commit>..HEAD` (și `git status` pentru ce e necomis). Reține
   doar schimbările durabile de structură: migrări noi, rute noi în `app/server.py`, pagini/componente noi
   în `web/`, module noi în `ingest/`, scheme noi în `shared/`, schimbări de mediu sau de comenzi.
3. **Ce memorii ating:** pornește de la `core` și urmează trimiterile `mem:`. Pentru fiecare memorie
   afectată, verifică în cod (uneltele simbolice Serena: `find_symbol`, `get_symbols_overview`) că ce
   scrii e adevărat, apoi actualizează cu `write_memory` / `edit_memory` (sau CLI: `serena memories
   write|edit`). O memorie nouă doar pentru un domeniu nou, cu trimitere din memoria-părinte.
4. **Reguli:** urmează `memory_maintenance` (note dense, fapte stabile, fără detalii de linie, fără
   note de o zi). **Nu copia reguli din `CLAUDE.md`**, trimite la el. Fără secrete, chei sau date
   interne: repo-ul poate fi public.
5. **Închidere:** `serena memories check .` (fără trimiteri rupte); scrie commit-ul curent
   (`git rev-parse --short HEAD`) în `stare/ultima_actualizare`; spune-i utilizatorului, pe scurt, ce
   memorii s-au schimbat și de ce (sau că nu era nimic de actualizat).
