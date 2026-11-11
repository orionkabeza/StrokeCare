<!-- Owner: Malaika Elohim Isingizwe Mukama (Scrum Master) · AI-assisted draft, see AI_USE_LOG.md -->
# StrokeCare

Stroke prevention and recovery at home, for Rwanda, in English, Kinyarwanda and French.
For stroke survivors, prevention users, caregivers, clinicians and community health workers.
**It records and summarises what people enter. It never diagnoses, prescribes, scores risk, or delays emergency care.**

Team 3 · Foundations Project · ALU. Version 2: the first prototype lived in `EricaSheja/stroke_care_development`.

## What it does

| For | Features |
|---|---|
| Survivors and prevention users | Today screen, daily check-in (urgent answers show emergency guidance at once), blood pressure with a chart, medicine ticks, talk board for aphasia, questions and voice notes for the next visit, care-team messages, care calendar, accessibility settings, data download and deletion |
| Caregivers | Alerts (urgent answer, doses not marked, no check-in), act on the person's behalf, family care calendar with handover notes, messages |
| Clinicians | Caseload with "needs a look" filters (facts only), seven-day summary, write the recovery plan and medicine list, plan templates, listen to voice notes, messages |
| Community health workers | People who invited them, home visits recorded offline and sent later, readings during visits |
| New in this version | Personal recovery (stage named by the clinician, own goals), movement tracker, progress dashboard (counts, no scores), appointment reminders, medicines grouped by time of day with one-tap "mark all", personal talk-board phrases, a one-screen check-in, an optional offline copy of the plan, a doctor home page and a "my care team" page |
| Everyone, signed in or not | Emergency help, talk board, education |

## Stack

| Layer | Choice |
|---|---|
| Backend | Django 5.2 + Django REST Framework, Python 3.13 |
| Database | PostgreSQL 16 (no SQLite anywhere; voice notes are stored in PostgreSQL too) |
| Auth | bcrypt password hashes, 15-minute JWT access tokens, rotating refresh tokens revoked on the server |
| Frontend | Plain HTML, CSS and JavaScript: no framework, no packages, no build step. Phosphor icons drawn inline, plain-SVG charts; installable PWA that works offline |
| Jobs | `run_scheduler` worker, or a guarded HTTP endpoint called by GitHub Actions every 15 minutes |
| Tests | pytest (backend), Node's built-in test runner (frontend), plus a browser run of every role's main flows in the build session |
| Delivery | GitHub Actions (backend + frontend checks), one Docker image serving the API and the app |

## Run it locally

```bash
docker compose up --build        # PostgreSQL + app + scheduler worker on http://localhost:8000 (not yet run: see docs/DEPLOYMENT.md)
```

Without installing anything on your computer, use GitHub Codespaces: [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/erangira-005/StrokeCare-app). It builds a cloud workspace with PostgreSQL, loads fictional demo data and starts the app on port 8000. See [`.devcontainer/README.md`](.devcontainer/README.md).

Quickest way without Docker (one server, app and API together). You need Python 3.13 and a PostgreSQL 16 you can reach. Nothing to build for the web app: it is plain files in `frontend/site`, and Django serves them. Create the database once:

```bash
psql -U postgres -c "CREATE USER strokecare PASSWORD 'strokecare' CREATEDB" -c "CREATE DATABASE strokecare OWNER strokecare"
```

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export DJANGO_DEBUG=1 ALLOW_DEMO_DATA=1 DATABASE_URL=postgres://strokecare:strokecare@localhost:5432/strokecare
python manage.py migrate
python manage.py seed_demo --password 'choose-a-demo-password'
python manage.py runserver                      # open http://localhost:8000
```

`seed_demo` lists the fictional accounts (demo-survivor, demo-caregiver, demo-clinician, demo-chw, demo-prevention, demo-admin, all at example.org). Use the password you chose. The data is fictional and must never be used with real people.

To change the web app, edit a file under `frontend/site/` and reload the page: there is no build and no dev server to run. After adding, removing or changing a file there, refresh the offline file list with `python tools/make_precache.py` (a test and CI fail if it is out of date). API docs are at `/api/v1/docs/`.

```bash
cd backend && pytest              # backend tests; needs DATABASE_URL
cd frontend && npm test           # frontend tests; needs Node 22 or newer, installs nothing
python tools/make_precache.py --check
```

## Where things are

| | |
|---|---|
| `backend/apps/accounts` | users, consent, accessibility preferences, sign-in |
| `backend/apps/care` | sharing links, caregiver alerts, the scheduler |
| `backend/apps/health` | blood pressure, plan, check-in, medicines, visit questions, voice notes, summary, reminders |
| `backend/apps/messaging`, `family`, `community` | care-team messages; care calendar and handover notes; CHW home visits |
| `backend/apps/content` | education, emergency guidance and verified contacts, talk board |
| `backend/apps/common`, `audit` | the single access-control module, error format, audit log |
| `frontend/site` | the web app, plain HTML, CSS and JavaScript (`js/views/` has the 31 screens, `locales/` the three languages); `frontend/tests` its tests; see `frontend/README.md` |
| `docs/` | architecture, roles matrix, safety rules, data model, deployment, **open questions and launch blockers** |
| `OWNERS.json` | who owns which file (`python tools/make_handoff.py --check`) |

**Before this goes near real people, read `docs/OPEN_QUESTIONS.md`.** Several launch blockers are not code.
