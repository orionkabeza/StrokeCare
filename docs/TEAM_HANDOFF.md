<!-- Owner: Malaika Elohim Isingizwe Mukama (Scrum Master) · AI-assisted draft, see AI_USE_LOG.md -->
# How the team takes over the code

The whole project is already on `main` of **https://github.com/erangira-005/StrokeCare-app**. It went in as a few
commits made by the AI assistant that drafted it, so no teammate has a commit in it yet. Each person gets a zip of
**their own files** (`handoff/<Name>.zip`, made by `python tools/make_handoff.py`) so we all know exactly what is ours.
The folder layout inside is the real layout.

Your contribution is what you do next: read your files until you can explain them, test them, change what you
disagree with, and commit that under your own name.

## Steps for everyone

1. Clone the repository and create a branch: `git checkout -b feature/<your-area>`.
2. Unzip your file into the repository root. It overwrites your files with identical copies, so `git status` should show
   nothing changed. That confirms your zip matches `main`.
3. Read every file in your zip. **You must be able to explain your files** in the technical presentation: they are yours.
4. Run the tests before you change anything, and again after:
   - backend: `cd backend && pytest` (needs a PostgreSQL, see the README); 436 tests should pass
   - frontend: `cd frontend && npm test` (Node 22 or newer; nothing to install, no build); 62 tests should pass.
     Then `python tools/make_precache.py --check` should say OK
5. Make it yours: fix what you disagree with, change what is wrong, add what is missing. Commit in small commits **under
   your own name**. When you have fully reviewed or rewritten a file, remove its "AI-assisted draft" line.
6. Open a pull request using the template; link your Trello card; one teammate approves.
7. Add or update your row in `AI_USE_LOG.md`: what you asked the AI, what it produced, and how you changed it.

## Suggested reading and review order

The files depend on each other, so read in this order. Reviewers pair up as below.

| Order | Who | Why first |
|---|---|---|
| 1 | Orion | project settings, Docker, CI, Codespaces, test setup: nothing runs without these |
| 2 | Kenneth | access control, links, audit log, the doctor page: other apps import them |
| 3 | Axel | users, health records, recovery features, API wiring (`strokecare/urls.py`) |
| 4 | Erica | content app, fixtures, safety tests, translations |
| 5 | Malaika | README, process files |
| 6 | Happy | `frontend/` (the app: plain HTML, CSS and JavaScript in `frontend/site/`). Erica's zip holds the three translation files it needs (`frontend/site/locales/`) and the translation test |

Migrations belong to the app that owns them, so they are in each person's zip.

## Reviewers (from the team report)

Kenneth ↔ Axel review each other. Axel reviews Happy. Malaika ↔ Erica. Kenneth reviews Orion.

## Per-person starting points

| Person | Start here | Questions you should be able to answer |
|---|---|---|
| Orion | `settings.py`, `Dockerfile`, `.github/workflows/ci.yml`, `.devcontainer/`, `tools/make_precache.py`, `tools/make_icons.py`, `frontend/tests/site.test.js` | Why does the app refuse to start without a secret and a PostgreSQL URL? How does the Codespace set itself up and check itself? Why is there no front-end build, and what does `make_precache.py` do and when must it run? What is untested? |
| Kenneth | `apps/common/access.py`, `apps/care/` (including `doctor.py` and `scopes.py`), `test_role_matrix.py` | Why 404 for strangers but 403 for a missing scope? How does withdrawing consent cut access? Why does the doctor's overview list people by name and not by risk? |
| Axel | `apps/accounts/`, `apps/health/`, `apps/recovery/`, `test_recovery_features.py` | Why are check-in answers a table, not JSON? How is "one tick per task per day" guaranteed? How does a phone's retry never save a movement entry twice? |
| Erica | `apps/content/`, `docs/SAFETY.md` (rules 21 to 26), `test_safety.py`, `fixtures/`, `locales/` | Where is each safety rule enforced? Why does the app ship no definition of a recovery stage? What are the launch blockers? |
| Happy | `frontend/site/js/api.js`, `copy.js`, `offline.js`, `store.js`, `router.js`, `dom.js`, `views/patient/check-in.js`, `progress.js`, `mobility.js` | How does a screen draw and keep what you typed when it redraws? Why can a name never become markup? How does the offline outbox work? What may the optional offline copy hold, and what never? Why is a person never signed out for being offline? |
| Malaika | `README.md`, `OWNERS.json`, this file | Which open questions are decisions, and who owns each? |

## A note on course rules

The course requires any AI use to be disclosed with every prompt, every output and how it was changed, and says
individual marks follow your own coding contributions. These files were drafted with AI assistance. Do not present
them as solely your own work: record them in `AI_USE_LOG.md`, change and understand them, and check with the
teaching team how they want this handled.
