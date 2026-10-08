#!/usr/bin/env bash
# Livrare pe serverul de test: build-ul interfeței local → tarball → scp → rsync în /opt/marketing/mcc.
#
#   deploy/deploy.sh [mcc-test]
#
# Conexiunea: `ssh mcc-test` cu parola o dată (~/.ssh/config, ControlMaster), apoi
# scriptul o refolosește. Prima instalare a serverului (06.10.2026) e descrisă în
# deploy/INSTALARE.md.
#
# Ce produce serverul nu se șterge (regulile `P` de mai jos): .env, loguri/,
# bronze/, output/, cache-ul PDF, JSON-urile din date/, copiile robots.txt.
# Nu se folosește .gitignore ca filtru: rsync citește `!output/reclame/` ca
# „golește lista de reguli”, iar cu --delete asta ar fi șters bronze/.
# Migrările noi NU se rulează automat: se rulează de mână, apoi sincronizeaza_vederi.sql.
#
# Înainte de repornire, livrarea se oprește dacă serviciul nu are MCC_AUTH_OBLIGATORIE=1 sau
# nginx nu trimite X-Real-IP: fără ele „niciodată utilizator local pe server” ar depinde doar de
# pașii făcuți de mână (deploy/INSTALARE.md). Codul nou e deja copiat; rulează tot cel vechi.
set -euo pipefail
TARGET="${1:-mcc-test}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -n "$(git status --porcelain)" ]; then
  echo "!! Ai modificări necommise; se livrează doar HEAD ($(git rev-parse --short HEAD))."
fi

echo "== Typecheck și build"
npm run typecheck
npm run build

echo "== Pachet"
TAR="$(mktemp -d)/mcc.tar"
git archive --format=tar HEAD -o "$TAR"
tar -rf "$TAR" web/dist
gzip "$TAR"
ls -lh "$TAR.gz"

echo "== Copiere pe $TARGET"
scp -q "$TAR.gz" "$TARGET:/tmp/mcc-release.tar.gz"
ssh "$TARGET" "set -e
  rm -rf /tmp/mcc-release && mkdir -p /tmp/mcc-release && tar -xzf /tmp/mcc-release.tar.gz -C /tmp/mcc-release
  echo 'commit: $(git rev-parse --short HEAD) ($(date +%F))' > /tmp/mcc-release/VERSIUNE
  sudo rsync -a --delete \\
    -f 'P /.env' -f 'P /loguri/' -f 'P /bronze/' -f 'P /bronze_arhiva_*/' -f 'P /output/' \\
    -f 'P /app/.cache_pdf/' -f 'P /.cache_pdf/' -f 'P /date/*.json' -f 'P /date/robots/' \\
    -f 'P __pycache__/' -f 'P /VERSIUNE' \\
    /tmp/mcc-release/ /opt/marketing/mcc/
  sudo cp /tmp/mcc-release/VERSIUNE /opt/marketing/mcc/VERSIUNE
  sudo chown -R marketing:marketing /opt/marketing/mcc
  sudo -u marketing /opt/marketing/venv/bin/pip install -q -r /opt/marketing/mcc/requirements.txt
  if ! systemctl show -p Environment mcc | grep -qw 'MCC_AUTH_OBLIGATORIE=1'; then
    echo '!! Oprit înainte de repornire: serviciul mcc nu are MCC_AUTH_OBLIGATORIE=1 (logarea AD n-ar fi garantată).' >&2
    echo '   Pe server: sudo cp /opt/marketing/mcc/deploy/mcc.service /etc/systemd/system/ && sudo systemctl daemon-reload' >&2
    echo '   apoi din nou deploy/deploy.sh (vezi deploy/INSTALARE.md).' >&2
    exit 1
  fi
  if ! sudo nginx -T 2>/dev/null | grep -v '^[[:space:]]*#' | grep -Eq 'proxy_set_header[[:space:]]+X-Real-IP'; then
    echo '!! Oprit înainte de repornire: nginx nu trimite X-Real-IP spre aplicație (proxy_set_header X-Real-IP).' >&2
    echo '   Fără el limitarea logărilor vede o singură adresă. Instalează deploy/nginx-mcc.conf' >&2
    echo '   (sudo nginx -t && sudo systemctl reload nginx), apoi din nou deploy/deploy.sh (vezi deploy/INSTALARE.md).' >&2
    exit 1
  fi
  sudo systemctl restart mcc
  sleep 2
  curl -s -o /dev/null -w 'pagina: %{http_code}\n' http://localhost/
  curl -s -o /dev/null -w 'api: %{http_code}\n' http://localhost/api/logos"
