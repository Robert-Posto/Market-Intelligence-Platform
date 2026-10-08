"""PostToolUse hook (proiectul MIP): după un `git commit` care schimbă structura codului, îi cere
agentului să actualizeze memoriile Serena (`.serena/memories/`).

Nu blochează nimic: doar adaugă context. La orice eroare proprie tace (fail-open).
Rulat din `.claude/settings.json` al proiectului, cu `python`.
"""
import json
import os
import re
import subprocess
import sys

STRUCTURAL = [
    (r"^db/migration_\d+.*\.sql$", "migrare nouă sau modificată"),
    (r"^db/(schema|sincronizeaza_vederi)\.sql$", "schema / vederile"),
    (r"^app/(server|rulari)\.py$", "API-ul (rute)"),
    (r"^web/src/(App\.tsx|pagini\.ts)$", "rutele / meniul interfeței"),
    (r"^web/src/pages/", "pagini din web/"),
    (r"^web/src/components/", "componente comune"),
    (r"^shared/src/", "schemele API (shared)"),
    (r"^crawler/vocabular\.py$", "vocabularul canonic"),
    (r"^(CLAUDE|PIPELINE)\.md$", "regulile / pipeline-ul"),
]
# `git commit` ca program, nu ca text: șirurile din ghilimele se scot înainte de căutare
RE_COMMIT = re.compile(r"(^|[;&|\n(]\s*)git((?:\s+-[Cc]\s+\S+)*)\s+commit\b")


def git(repo, *args):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=5)
    return r.stdout if r.returncode == 0 else ""


def main():
    ev = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace") or "{}")
    cmd = (ev.get("tool_input") or {}).get("command") or ""
    fara_ghilimele = re.sub(r"'[^']*'|\"(?:\\.|[^\"\\])*\"", "''", cmd)
    m = RE_COMMIT.search(fara_ghilimele)
    if not m:
        return
    repo = ev.get("cwd") or os.getcwd()
    dirs = [d for d in re.findall(r"-C\s+(\S+)", m.group(2)) if d != "''"]
    if dirs:  # `git -C <cale> commit`; /c/... din Git Bash devine C:/...
        repo = os.path.join(repo, re.sub(r"^/([a-zA-Z])/", r"\1:/", dirs[-1]))
    root = git(repo, "rev-parse", "--show-toplevel").strip()
    if not root or not os.path.isdir(os.path.join(root, ".serena", "memories")):
        return
    motive, fisiere = set(), []
    for line in git(root, "show", "--name-status", "--format=", "HEAD").splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status, path = parts[0], parts[-1].replace("\\", "/")
        hit = [why for rx, why in STRUCTURAL if re.search(rx, path)]
        if status.startswith("A") and re.match(r"^ingest/[^/]+\.py$", path) and "test_" not in path:
            hit.append("modul nou în ingest/")
        if hit:
            motive.update(hit)
            fisiere.append(path)
    if not motive:
        return
    head = git(root, "rev-parse", "--short", "HEAD").strip()
    msg = (f"serena-memento: commit-ul {head} a schimbat structura codului ({', '.join(sorted(motive))}; "
           f"ex. {', '.join(fisiere[:5])}). Înainte să închei, actualizează memoriile Serena afectate "
           f"(pornește de la `mem:core`), urmând `mem:memory_maintenance`, și scrie commit-ul {head} în "
           f"`mem:stare/ultima_actualizare` (sau rulează /actualizeaza-memoria). Dacă nu s-a schimbat nimic "
           f"durabil, spune asta și nu modifica memoriile.")
    sys.stdout.write(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                                        "additionalContext": msg}}, ensure_ascii=True))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
