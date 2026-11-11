<!-- Owner: Orion Kabeza (DevOps) · AI-assisted draft, see AI_USE_LOG.md -->
# Deployment

## What is verified and what is not

| Item | State |
|---|---|
| Backend on PostgreSQL 16: migrations apply, 436 tests pass | **Verified** in the build session |
| Frontend (plain HTML, CSS and JavaScript, no build): 62 Node tests, and the service worker's file list is current | **Verified** |
| Django serving the built app at `/` with the API under `/api/` | **Verified**, in a real browser: every role's main flows passed with no console errors (sign-in, check-in with urgent guidance, reading, dose, voice note recorded with the browser's recorder, message, Kinyarwanda + dark theme, caregiver alert and calendar, clinician caseload and summary, CHW home visit) |
| `manage.py check --deploy` with production settings | **Verified** earlier; only a short-test-secret warning and an optional HSTS-preload note |
| Root `Dockerfile`, `docker-compose.yml` | **Written, never built** (no Docker daemon in the build session). Build once and fix what it finds |
| GitHub Actions `ci.yml` and `scheduler.yml` | **Written, never run.** The first pull request and the first scheduled run will tell |
| Any hosting provider | **Not chosen, not tested** |

## One image, three jobs

The root `Dockerfile` builds the Python service and copies the web app's plain files (`frontend/site`) next to it, so
Django serves both. There is no Node stage and no front-end build. The same image runs as:

| Process | Command | Notes |
|---|---|---|
| web | default `CMD`: migrate, load reference data, gunicorn | one public URL for the app and the API |
| worker | `python manage.py run_scheduler --interval 900` | caregiver alerts every 15 minutes; use it where the host allows a background worker |
| (no worker) | `.github/workflows/scheduler.yml` | free alternative: GitHub calls `POST /api/v1/internal/jobs/run/` every 15 minutes with the `CRON_SECRET` header |

Use the worker **or** the GitHub schedule. Running both is harmless (alerts are never duplicated), just wasteful.

## Environment variables (production)

| Variable | Needed | Notes |
|---|---|---|
| `DJANGO_SECRET_KEY` | yes | long random value; the app refuses to start without it |
| `DATABASE_URL` | yes | must be PostgreSQL; the app refuses anything else |
| `DJANGO_ALLOWED_HOSTS` | yes | your domain(s), comma separated |
| `CSRF_TRUSTED_ORIGINS` | for the admin site | e.g. `https://strokecare.example.org` |
| `DATABASE_SSL_REQUIRE` | recommended | `1` when the database is on another host |
| `NUM_PROXIES` | behind a proxy | so login throttling sees real IPs |
| `CRON_SECRET` | only for the GitHub scheduler | long random value; also saved as a GitHub secret. Empty = endpoint off |
| `CORS_ALLOWED_ORIGINS` | only if the app is hosted on a different domain from the API | not needed for the one-image setup |
| `ALLOW_DEMO_DATA` | **never in production** | |

`DJANGO_DEBUG` must be unset or `0`. With debug off the app forces HTTPS, secure cookies and HSTS. The app's page is
served with a strict Content Security Policy (scripts from the site only).

## First deploy checklist

1. Create the PostgreSQL database and a **separate, limited database user** for the app.
2. After the first `migrate`, revoke `UPDATE` and `DELETE` on `audit_auditlog` from that user.
3. Set the variables above. The container migrates, loads the draft reference data, and starts gunicorn.
4. `python manage.py createsuperuser`, then add professionals only after checking their credentials:
   `python manage.py create_clinician <email> "<name>" --ref <licence> --verified` (add `--role chw` for a community health worker).
5. Start the worker, or set `STROKECARE_URL` and `CRON_SECRET` as GitHub repository secrets.
6. Check `/healthz` returns `{"status": "ok"}` and that `/` shows the app.
7. Turn on database backups and test one restore **before** any real person signs up. Voice notes live in the
   database, so the backup covers them.

## Free tiers

Free tiers are fine for the course demo with fictional data. Before relying on one, read its current terms for:
database expiry or sleep, backups, where data is stored, and background workers (if there is none, use the GitHub
scheduler). They are **not** a decision to host real patients on. See launch blocker 6 in `OPEN_QUESTIONS.md`.
