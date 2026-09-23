# Migrare de plan Claude: ce trebuie refăcut

Notă scrisă la **23 septembrie 2026**, înainte de trecerea Enterprise → Team.

---

## Ce NU se pierde

Contextul Claude Code e local, pe mașină, nu în cont:

| ce | unde |
|---|---|
| conversațiile proiectului | `~/.claude/projects/c--Users-robert-postolache-Desktop-Scraping/*.jsonl` |
| memoria proiectului | `.../memory/MEMORY.md` + fișierele de memorie |
| instrucțiuni globale | `~/.claude/CLAUDE.md` |
| setări, skill-uri, MCP | `~/.claude/` |

Schimbarea planului nu le atinge. **Nu există și nu e nevoie de nicio comandă
de migrare.**

Copie de siguranță făcută la:
`~/Desktop/backup-claude-mip-2026-09-23/` (31 MB — 3 conversații, memoria,
CLAUDE.md, settings.json)

---

## Ce se poate pierde

**Artefactul cu arhitectura.** Era stocat pe claude.ai, marcat *shared with
your organization*. Dacă trecerea înseamnă o organizație nouă, artefactele
rămân la cea veche.

**Salvat local, în repo:** [`docs/arhitectura-flow.html`](docs/arhitectura-flow.html)
— 6 diagrame SVG, se deschide în orice browser, fără dependențe. E aceeași
versiune care era publicată.

---

## Ce trebuie refăcut DUPĂ migrare

### 1. Cheia Anthropic

`ANTHROPIC_API_KEY` din `.env` nu va mai funcționa dacă se schimbă
organizația. Generează una nouă pe contul Team și pune-o în `.env`.

Trebuia rotită oricum: a fost trimisă în text clar într-o conversație, deci e
compromisă independent de migrare.

Se folosește doar de:
- `claudeCrawl.py` (discovery de surse noi)
- treapta 3 a cascadei din `flux.py` (`web_fetch`)

Restul pipeline-ului nu are nevoie de ea. Colectarea cu `--fara-llm` merge
fără cheie.

### 2. Nimic altceva

Baza de date e locală (Docker). Codul e în repo. Parserele colegilor sunt în
`~/Downloads/pentru_coleg_bs4_21sept` și `~/Downloads/flux-colectare` — pe
disc, nu în cont.

---

## Ce NU trebuie atins

**`MIP_SALT`.** Nu se regenerează la migrare. Sarea determină hash-urile de
autor din `app_review`; dacă se schimbă, aceleași recenzii capătă hash-uri
diferite și nu se mai pot lega între rulări. Păstrează exact valoarea actuală
și distribuie-o echipei pe alt canal decât repo-ul.

---

## Înainte de migrare, în ordine

1. ✅ artefactul salvat în `docs/arhitectura-flow.html`
2. ✅ copie de siguranță a conversațiilor și memoriei pe Desktop
3. ⬜ **împinge repo-ul pe GitHub** — odată acolo, codul nu mai depinde nici
   de mașină, nici de cont:
   ```bash
   cd ~/Downloads/mip
   git remote add origin https://github.com/Robert-Posto/Market-Intelligence-Platform.git
   git push -u origin main
   ```
4. ⬜ notează valoarea actuală a `MIP_SALT` într-un loc sigur (nu în repo)
5. ⬜ întreabă suportul Anthropic dacă trecerea Enterprise → Team păstrează
   aceeași organizație. Dacă da, artefactele rămân accesibile și punctul 1 e
   doar o precauție.
