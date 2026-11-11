#!/usr/bin/env bash
# Owner: Orion Kabeza (DevOps) · AI-assisted draft, see AI_USE_LOG.md
# Runs every time the Codespace starts: the server on port 8000 (app and API together) and the alert worker,
# then checks that everything really answers.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"

pkill -f "manage.py runserver" 2>/dev/null || true
pkill -f "manage.py run_scheduler" 2>/dev/null || true

# setsid + closed stdin: the processes must outlive this script and the terminal that ran it.
setsid nohup .venv/bin/python manage.py runserver 0.0.0.0:8000 --noreload > /tmp/strokecare-web.log 2>&1 < /dev/null &
setsid nohup .venv/bin/python manage.py run_scheduler > /tmp/strokecare-worker.log 2>&1 < /dev/null &

echo "Starting StrokeCare on port 8000. Logs: /tmp/strokecare-web.log and /tmp/strokecare-worker.log"
bash "$ROOT/.devcontainer/check.sh" || true
