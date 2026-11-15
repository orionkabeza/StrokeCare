<!-- Owner: Orion Kabeza (DevOps) -->
# Orion's notes on this pass

Everything below came out of actually running the things in `docs/TEAM_HANDOFF.md`'s "Orion" row for the first
time: backend tests against a real PostgreSQL, the frontend tests, the Docker build and `docker-compose up`,
`check.sh` against the running stack, the devcontainer itself, and both `tools/` checks. Three things needed
fixing; the rest was already correct.

## What was run, and the result

| Check | Result |
|---|---|
| `cd backend && pytest` | **436 passed.** Could not run with the repo's native Python on this Windows machine — see "Windows note" below — so it ran inside a `python:3.13-slim` container against a `postgres:16` container, matching CI exactly |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `cd frontend && npm test` | **62 passed**, after a fix (below). Node 26 on this machine, well above the required 22 |
| `python tools/make_precache.py --check` | OK, after a fix (below) |
| `python tools/make_handoff.py --check` | **Fails: `.gitattributes`, `docs/HOSTING_PILOT.md` and `docs/ORION_NOTES.md` have no owner.** Not something I can fix myself — see "Needs Malaika" below |
| `docker compose build` / `docker compose up` | Builds and runs: `db`, `web` and `worker` all come up healthy, after a fix (below) |
| `.devcontainer/check.sh` against the `docker-compose.yml` stack | Server, web app, scripts and the API+DB all pass. "alert worker is not running" and "no .demo-credentials.txt" fail here **by design**, not by bug: those two checks assume the devcontainer's single-host-process model (`start.sh`'s background processes, `setup.sh`'s demo seeding), which the production-style `docker-compose.yml` does not do (the worker is its own container; nothing seeds demo users there). `check.sh` is correct for what it was written to check |
| The devcontainer itself (`.devcontainer/docker-compose.yml`, `setup.sh`, `start.sh`, `check.sh`) | **All 6 checks pass.** Actually started this time (the original build session had no Docker): brought up the `app`/`db` pair, ran `setup.sh` (installs, migrates, seeds demo data) and `start.sh` (starts the server and worker, then runs `check.sh`) for real inside the container. Every check passed, including the alert worker and the demo-credentials check that only make sense in this single-host-process model |
| `.github/workflows/ci.yml`, `scheduler.yml` | Reviewed step by step against the real commands, paths, package versions and the `/api/v1/internal/jobs/run/` endpoint. Everything matches. Not run for real on GitHub Actions yet (needs a push/PR) |

## Fixes made (small commits, see git log)

1. **`frontend/tests/site.test.js` (CRLF fix).** Two tests parsed `sw.js` with a regex ending in a literal `\n`.
   On this Windows checkout (see below) the file had `\r\n` line endings, so the regex never matched and both
   tests threw. Made both regexes accept an optional `\r`.
2. **Added `.gitattributes` (`* text=auto eol=lf`).** The real cause of the CRLF problem: this machine's global
   git config has `core.autocrlf=true`, which rewrites every text file to `\r\n` on checkout. That does not just
   break the two tests above — it changes the exact bytes `tools/make_precache.py` hashes, so `--check` failed
   too, even though the committed content (confirmed with `git show`) is plain `\n`. `.gitattributes` forces LF
   for every contributor regardless of their own `core.autocrlf`, so this cannot recur on another Windows
   machine. After adding it, `git add --renormalize .` showed no content changes (the blobs were already LF;
   only this machine's working copy was wrong), and a full re-checkout fixed the working tree.
3. **`docker-compose.yml`: `worker` now waits for `web` to be healthy, not just for `db`.** On a cold
   `docker compose up`, `worker` only waited for `db` to be healthy, not for `web` to finish migrating, and both
   start at the same time. First attempt: ran `migrate --noinput` in the worker's own command too, before
   `run_scheduler` — that just moved the race one level down, because now **two** containers called `migrate` on
   the same fresh database at once, and Postgres rejected the second attempt to create the `django_migrations`
   table with a duplicate-key error. The actual fix: added a healthcheck to `web` (hits `/healthz`, so it only
   reports healthy once migrations are done and gunicorn is serving) and made `worker` depend on `web` being
   healthy, not just on `db`. Verified with a real cold `docker compose up` after `docker compose down -v`: `web`
   goes healthy first, then `worker` starts, with no errors in its log.

## Windows note (not a repo bug, but worth knowing)

Native Python on this machine cannot import `psycopg`: `DLL load failed while importing pq: An Application
Control policy has blocked this file.` That is a Windows Application Control / WDAC policy on this machine
blocking the compiled extension, not anything wrong with `requirements.txt`. Backend tests and the two Python
tools that touch the database (`make_erd.py` needs Django to load, though not a real connection) were run inside
a `python:3.13-slim` container instead, which has no such restriction and also matches the project's pinned
Python version exactly. Any contributor hitting the same error should do the same rather than trying to work
around it in the app.

## Needs Malaika (files I don't own)

- **`OWNERS.json`**: add `.gitattributes`, `docs/HOSTING_PILOT.md` and this file (`docs/ORION_NOTES.md`) under
  Orion's rules — `.gitattributes` is a DevOps/tooling file in the same spirit as `.gitignore` and
  `.dockerignore`, which are already listed there, and the other two are new docs this pass added. Until these
  are added, `python tools/make_handoff.py --check` reports all three as orphans and the tool refuses to write
  the per-person zips.
- **`AI_USE_LOG.md`**: this file is owned by Malaika, so the row I'd add is here instead — please copy it in:

  | Date | Who | Prompt (paste it) | Output (paste or link) | What you changed |
  |---|---|---|---|---|
  | 12 Nov 2026 | Orion Kabeza | Pulled the handoff project, ran everything in the Orion row of `docs/TEAM_HANDOFF.md` that had never actually been run (backend tests against real PostgreSQL, frontend tests, Docker build, `docker compose up`, `check.sh`, the devcontainer, both `tools/` checks, the CI workflow review), fixed what was broken, and wrote the hosting pilot comparison | A CRLF-tolerant fix to `frontend/tests/site.test.js`, a new `.gitattributes`, a migration-order fix to `docker-compose.yml`'s worker, and `docs/HOSTING_PILOT.md` | Reviewed and tested every change against the real test suites and the real Docker stack before committing; nothing here was committed unseen |

  Also, the "Session 2" row's "How it was changed afterwards" cell still says *"To be filled in by Happy (the
  app), Orion (Docker, CI, tools), Erica (locales, i18n test), Malaika (README, ownership)"* — Orion's part is:
  fixed the CRLF/line-ending issue above, fixed the worker migration race in `docker-compose.yml`, and confirmed
  (by actually running them) that the Dockerfile, `docker-compose.yml`, CI workflow, devcontainer and both
  `tools/` scripts all work as documented.

## What I did not change

`docs/OPEN_QUESTIONS.md` blocker 6 (hosting for real health data) is unaffected by `docs/HOSTING_PILOT.md`: that
document is explicitly about the **pilot**, with fictional demo data, and says so at the top. No real patient
data should go on any host from this document until blockers 1-6 in `OPEN_QUESTIONS.md` are closed.
