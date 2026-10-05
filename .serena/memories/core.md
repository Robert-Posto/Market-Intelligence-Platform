# Marketing Command Center (MIP) — rădăcina memoriilor

- Ce e: monitorizarea a 30 de bănci din România din date publice, pentru marketingul Libra Bank. Colectare Python → PostgreSQL → API Python (`app/server.py`, :8765) → interfață React (`web/`, :5173). Interfața veche `app/index.html` rămâne până la livrare.
- **Regulile proiectului NU stau aici:** sunt în `CLAUDE.md` din rădăcina repo-ului (conformitate, „datele nu se aruncă”, migrări, interfață, verificări). Citește-l pe el; memoriile de aici doar completează.
- Harta codului (ce modul face ce, punctele de intrare, unde adaugi ceva nou): `mem:cod/harta`.
- Drumul datelor și vederile care filtrează (de ce o valoare nu apare pe ecran): `mem:date/fluxul_si_vederile`.
- Cum se construiește o pagină sau o secțiune nouă în `web/`, cap-coadă (migrare → loader → rută → schemă → pagină): `mem:web/sectiune_noua`.
- Capcanele mediului Windows al lui Robert (Git Bash, PowerShell 5.1, Docker, căi lungi, hook-urile de securitate): `mem:mediu/capcane_windows`.
- Ultima actualizare a memoriilor (commit-ul de referință) și cum se actualizează: `mem:stare/ultima_actualizare`.
- Întreținerea memoriilor (stilul, ce intră și ce nu): `mem:memory_maintenance`.
