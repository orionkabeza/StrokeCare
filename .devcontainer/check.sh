#!/usr/bin/env bash
# Owner: Orion Kabeza (DevOps) · AI-assisted draft, see AI_USE_LOG.md
# Checks that StrokeCare is really running and prints the address to open. Exit code 0 means every check passed.
# Run it any time:  bash .devcontainer/check.sh
set -uo pipefail

PORT=8000
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FAILED=0

pass() { printf '  OK    %s\n' "$*"; }
fail() { printf '  FAIL  %s\n' "$*"; FAILED=1; }
# Prints only the HTTP status code (000 when nothing answers).
code() { curl -s -o /dev/null -m 10 -w '%{http_code}' "$@" 2>/dev/null || true; }

echo "StrokeCare checks"

# 1. The server answers. Give it up to 30 seconds, because it may have only just started.
for _ in $(seq 1 30); do
  [ "$(code "http://127.0.0.1:$PORT/healthz")" = 200 ] && break
  sleep 1
done
c="$(code "http://127.0.0.1:$PORT/healthz")"
if [ "$c" = 200 ]; then
  pass "the server answers on port $PORT"
else
  fail "the server does not answer on port $PORT (got ${c:-000}). Run: bash .devcontainer/start.sh   then read /tmp/strokecare-web.log"
fi

# 2. The web app is served (it is plain files in frontend/site; there is nothing to build).
c="$(code "http://127.0.0.1:$PORT/")"
if [ "$c" = 200 ]; then
  pass "the web app page loads"
else
  fail "the web app page returned ${c:-000}. Check that frontend/site/index.html exists, then run: bash .devcontainer/start.sh"
fi
c="$(code "http://127.0.0.1:$PORT/js/main.js")"
if [ "$c" = 200 ]; then
  pass "the app's scripts load"
else
  fail "the app's script /js/main.js returned ${c:-000}. Check that frontend/site/js/main.js exists"
fi

# 3. The address that GitHub's port forwarding uses is accepted (otherwise sign-in fails with a host error).
if [ -n "${CODESPACE_NAME:-}" ]; then
  DOMAIN="${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
  HOST="${CODESPACE_NAME}-${PORT}.${DOMAIN}"
  c="$(code -H "Host: $HOST" -H 'X-Forwarded-Proto: https' "http://127.0.0.1:$PORT/healthz")"
  if [ "$c" = 200 ]; then
    pass "the Codespaces address is accepted ($HOST)"
  else
    fail "the Codespaces address $HOST was refused (got ${c:-000}). Check DJANGO_ALLOWED_HOSTS includes .app.github.dev"
  fi
  ADDRESS="https://$HOST"
else
  ADDRESS="http://localhost:$PORT"
fi

# 4. The API and the database work. A wrong password must be refused cleanly (400 or 401), never an error (5xx).
c="$(curl -s -o /dev/null -m 10 -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
  -d '{"email":"check@example.org","password":"not-a-real-password"}' \
  "http://127.0.0.1:$PORT/api/v1/auth/login/" 2>/dev/null || true)"
case "$c" in
  400|401) pass "the API and the database answer (a wrong password is refused with $c, as it should be)" ;;
  *) fail "the sign-in API returned ${c:-000}. Read /tmp/strokecare-web.log" ;;
esac

# 5. The alert worker is running.
if pgrep -f "manage.py run_scheduler" >/dev/null 2>&1; then
  pass "the alert worker is running"
else
  fail "the alert worker is not running. Run: bash .devcontainer/start.sh"
fi

# 6. Demo accounts exist for this Codespace.
if [ -f "$ROOT/.demo-credentials.txt" ]; then
  pass "demo accounts are ready (password and emails: cat .demo-credentials.txt)"
else
  fail "no .demo-credentials.txt. Run: bash .devcontainer/setup.sh"
fi

echo
if [ "$FAILED" = 0 ]; then
  echo "All checks passed. StrokeCare is running."
  echo "Address: $ADDRESS"
  echo
  echo "How to open it: Ports tab -> port $PORT -> click the globe icon (Open in Browser)."
  echo "If the browser shows \"HTTP ERROR 401\", the app is fine. GitHub is asking you to sign in. Open it from the"
  echo "Ports tab while signed in to GitHub as this Codespace's owner, with cookies for github.dev allowed."
  exit 0
fi
echo "Some checks failed (see FAIL above). Fix the first one and run this script again."
exit 1
