<!-- Owner: Kenneth Master (System architect) · AI-assisted draft, see AI_USE_LOG.md -->
# Architecture

```
Browser (installable app in plain HTML, CSS and JavaScript at "/", 3 languages, works offline)
   │  HTTPS, JSON, Authorization: Bearer <short-lived access token>
   ▼
Django + DRF (one service: the app at "/", the API under /api/v1/, the admin under /admin/)
   │  every request:  authenticate → throttle → consent → role/link/scope → validate → ownership in the query
   ▼
PostgreSQL 16
```

## The rule that protects everyone's data

All personal-data routes live under `/api/v1/patients/<me|uuid>/…` and go through ONE function,
`apps/common/access.py: resolve_access`.

| Caller says | Allowed when | Otherwise |
|---|---|---|
| `me` | the account keeps a health record (survivor, prevention user) and has a current `health_data` consent | 403 `not_a_patient` / `consent_required` |
| `<uuid>` | an **active** care link to that patient, the other person is still eligible (verified clinician / caregiver), the patient's consent is active, **and** the link's scopes include the action | 404 if there is no link (a stranger learns nothing), 403 `scope_missing` if linked but not allowed |

Every access by someone other than the patient is written to the append-only audit log, and the patient can see
that list in their data export. Roles and scopes are laid out in `ROLES_MATRIX.md`, and proven by
`backend/tests/test_role_matrix.py` (every personal-data route against every kind of caller).

## Sign-in

- Passwords: bcrypt (SHA-256 pre-hash). Strength rules: Django's validators.
- Access token 15 minutes. Refresh token 7 days, **rotated on every use; the old one is revoked on the server.** Logout revokes it too.
- Login, sign-up and invitation-code entry are rate limited. Failed logins are logged without the email address.
- Clinician, community-health-worker and admin accounts cannot be self-registered. A professional has no power until an administrator sets `professional_verified_at`.

## API overview (all under `/api/v1/`)

| Area | Routes |
|---|---|
| Auth | `auth/register`, `auth/login`, `auth/refresh`, `auth/logout` |
| Me | `me/` (GET, PATCH, DELETE with password), `me/consents/`, `me/accessibility/`, `me/export/`, `me/reminders/…` |
| Sharing | `links/`, `links/invite/`, `links/redeem/`, `links/<id>/` (PATCH scopes, DELETE to end), `patients/` (who shared with me, with plain facts; `?needs=urgent|no_check_in|doses_not_marked`) |
| Caregiver alerts | `alerts/` (worked out on read, never repeated), `alerts/<id>/read/`, `alerts/read-all/`; `manage.py generate_alerts` for a scheduler |
| Patient data | `patients/<ref>/readings/`, `…/plan/`, `…/plan/tasks/`, `…/plan/tasks/<id>/log/`, `…/plan/apply-template/`, `…/checkins/`, `…/summary/?days=7`, `…/medications/`, `…/medications/<id>/doses/`, `…/visit-questions/` |
| Clinician tools | `plan-templates/` (a verified clinician's own reusable task lists) |
| Care team | `inbox/`, `patients/<ref>/messages/` (+ `read/`), `…/calendar/`, `…/calendar/<id>/`, `…/handover/`, `…/voice-notes/` (+ `<id>/` to listen or delete), `…/home-visits/` |
| Scheduler | `internal/jobs/run/` (POST, `X-Cron-Secret` header; off unless `CRON_SECRET` is set) |
| Content (public) | `education/`, `education/<slug>/`, `emergency/`, `talk-board/`, `home-visit-checklist/` (add `?lang=en|fr|rw`) |
| Config | `checkin-questions/` |
| Ops | `/healthz`, `schema/`, `docs/` |

Errors always look like `{"error": {"code": "…", "message": "plain sentence", "fields": {…}}}`.

## Why these choices

- **One access module** instead of per-view checks: one place to audit, one test matrix.
- **UUID ids, ownership inside every query**: a guessed id returns 404 even if someone forgot a check.
- **Check-in answers in their own table** (not JSON blobs): the prototype could not query them. Questions are data, so reviewers can change them without a deploy.
- **Public education and emergency routes**: they hold no personal data, and must work when someone cannot sign in.
- **Django admin is for content reviewers and account verification only.** Patients' health records are deliberately not registered there.

## Background jobs

Caregiver alerts are worked out by `apps/care/jobs.run_all()`. It runs when a caregiver opens their alerts, and on
a schedule: the `run_scheduler` worker, or GitHub Actions calling the guarded endpoint every 15 minutes. Every run
is safe to repeat because alerts are de-duplicated in the database.

## Offline

The app installs as a PWA. Public content is cached for offline reading. Check-ins, readings, dose marks and home
visits entered without signal wait in an outbox on the phone and are sent in order when the phone reconnects.
Home visits carry an id made on the phone, so re-sending one never creates a duplicate. Personal health data is
never cached by the service worker.

## Scaling path

One web container, one worker and one PostgreSQL are enough to start. Next, in this order: a shared cache for
throttling (needed once there is more than one web instance), push or SMS delivery for alerts and reminders,
moving voice notes to object storage if the database grows large, read replicas only if measurements show a need.
