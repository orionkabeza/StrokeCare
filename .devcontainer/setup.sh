#!/usr/bin/env bash
# Owner: Orion Kabeza (DevOps) · AI-assisted draft, see AI_USE_LOG.md
# Runs once when the Codespace is created: installs the backend packages, prepares the database and loads
# fictional demo data. Safe to run again.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CRED="$ROOT/.demo-credentials.txt"

echo "==> Backend packages"
cd "$ROOT/backend"
[ -d .venv ] || python -m venv .venv
.venv/bin/pip install --quiet -r requirements-dev.txt

# The web app (frontend/site) is plain HTML, CSS and JavaScript: nothing to install or build.

echo "==> Database"
cd "$ROOT/backend"
for i in $(seq 1 30); do
  if .venv/bin/python -c "import os, psycopg; psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=3).close()" 2>/dev/null; then
    break
  fi
  if [ "$i" = 30 ]; then echo "The database did not come up in time."; exit 1; fi
  sleep 2
done
.venv/bin/python manage.py migrate --no-input

echo "==> Demo data"
if [ ! -f "$CRED" ]; then
  PW="$(python3 -c 'import secrets; print(secrets.token_urlsafe(12))')"
  if .venv/bin/python manage.py seed_demo --password "$PW" > /tmp/strokecare-seed.log 2>&1; then
    {
      echo "StrokeCare demo accounts (fictional data, never for real people)"
      echo "Password for every account: $PW"
      echo
      grep -E 'demo-.*@example\.org' /tmp/strokecare-seed.log | sed 's/^ *//'
    } > "$CRED"
  else
    echo "Demo data was not created (probably it already exists). Details:"
    cat /tmp/strokecare-seed.log
  fi
fi

echo
echo "==> Ready. Open the forwarded port 8000 (Ports tab) to use the app."
[ -f "$CRED" ] && cat "$CRED" || true
