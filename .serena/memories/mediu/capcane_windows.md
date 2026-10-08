# Capcanele mediului de dezvoltare pe Windows

- Git Bash convertește căile `/tmp/...` din argumente: `docker exec … -f /tmp/x` eșuează → rulează din PowerShell sau cu `MSYS_NO_PATHCONV=1`.
- Python pe consolă = cp1252: setează `PYTHONIOENCODING=utf-8` (altfel diacriticele aruncă `UnicodeEncodeError`).
- Scripturile `.ps1` pentru PowerShell 5.1: UTF-8 **cu BOM**, altfel diacriticele se strică.
- Limita de 260 de caractere pe cale (copieri, arhive): ține căile sub ~200.
- Docker Desktop nu pornește singur după restart: pornește-l (scurtătura din Start Menu), apoi `docker start mip-db`.
- Serverele aplicației pornite din sesiunea Claude se opresc la limita de timp a proceselor de fundal → pornește-le cu `Start-Process` (proces separat).
- Node.js e în `C:\Program Files\nodejs` (poate lipsi din PATH-ul Git Bash: `export PATH="/c/Program Files/nodejs:$PATH"`); npm 11 blochează scripturile de instalare: esbuild merge fără ele, nu le aproba.
- Baza `mip` din `.env`-ul lui Nicolae n-are migrările 019–026 (`/api/banci` dă 500, `verifica_pagini.py` pică pe 11 pagini și cu codul vechi). Pentru verificări: al doilea server cu `MIP_PORT=8799` și `MIP_DSN=…dbname=mip_merge`, plus `MIP_URL=http://localhost:8799` la `verifica_pagini.py`; serverul de pe :8765 și Vite-ul de pe :5173 pot fi ale lui, nu le opri.
- Playwright din Python 3.14 n-are browserul descărcat: `p.chromium.launch(channel="msedge")` folosește Edge-ul din Windows, fără descărcare. Schimbarea doar a `#` din adresă nu reîncarcă pagina (`localStorage`, limba): `page.reload()`.
- Hook-urile de securitate ale utilizatorului (dacă există, în `~/.claude/hooks`) blochează citirea `.env`, a cheilor și comenzile distructive; nu le ocoli, spune-i utilizatorului.
- În spatele unui proxy de firmă, `curl` din Git Bash poate eșua acolo unde Python `requests` trece; unele domenii pot fi blocate de rețea.
- Serena rulează pe un Python 3.11 separat, instalat cu `uv tool` (pe 3.14, `pyyaml` nu are wheel și compilarea cere Visual C++). Configurația e în repo (`.mcp.json`, `.claude/`); instalarea, o dată pe mașină: README, „Serena”.
