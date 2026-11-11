<!-- Owner: Malaika Elohim Isingizwe Mukama (Scrum Master). Every person adds their own rows. -->
# AI use log

The Foundations Project rules (as summarised in the team report) require: an annex with **every prompt, every output
and how the output was changed**, plus an acknowledgement statement naming the tool. This file is the running log
the annex is built from. It does not replace the full chat export, which must be attached as well.

**Acknowledgement draft (confirm the wording with the teaching team):** Parts of this repository were drafted with
Claude (Anthropic) in a Claude Code session. All output was reviewed by the team member named for each file, who is
responsible for understanding it.

## Session 1: rebuild (8 Nov 2026), requested by Emmanuel Happy Rangira

| What was asked | What the AI produced | How it was changed afterwards |
|---|---|---|
| Rebuild StrokeCare as a market-ready product on the "alternatives" stack with a real database, split by team role | The whole `backend/` (Django + DRF + PostgreSQL), 166 tests, CI/Docker files, ownership map, hand-off tool, and the documents in `docs/` | *To be filled in by each owner as they review and edit their files* |

## Session 1, part 2: redesign and new features (8 Nov 2026), requested by Emmanuel Happy Rangira

| What was asked | What the AI produced | How it was changed afterwards |
|---|---|---|
| Redesign the UI (direction C, Phosphor icons, themes, motion) and add the agreed features | Backend: medicines and dose marks, visit questions, plan templates, talk board, caregiver alerts, clinician facts and filters, 56 more tests. Design: 12-board Claude Design canvas and `frontend/design-tokens.css` | *To be filled in by each owner* |

## Session 1, part 3: the app and the remaining features (8 Nov 2026), requested by Emmanuel Happy Rangira

| What was asked | What the AI produced | How it was changed afterwards |
|---|---|---|
| Build the Vue app, remove recordings, translate to French and Kinyarwanda, add the alert scheduler, voice notes, family calendar, messaging and the community-health-worker role, then email the team | The whole `frontend/` (Vue 3 + TypeScript, every screen, 3 languages, PWA, tests); backend apps `messaging`, `family`, `community`, voice notes, scheduler, CHW role; AI-drafted French and Kinyarwanda texts; root Dockerfile, worker, GitHub scheduler | *To be filled in by each owner* |
| Open the project in GitHub Codespaces, with no local install | `.devcontainer/` (dev container config, compose file with PostgreSQL 16, setup and start scripts) and a README section | *To be filled in by Orion* |
| Add personalised recovery, movement tracker, progress dashboard, caregiver access, appointment and medicine reminders, time-of-day medicines, clinician-set recovery stages, personal talk-board phrases, offline access, fewer forms and taps, and a doctor page | `backend/apps/recovery/`, `backend/apps/care/doctor.py`, bulk dose marking, appointment reminders and alerts, new scopes and migrations, 25 + 7 new tests, about 25 new or changed frontend screens, offline copy, 156 new English, French and Kinyarwanda strings; fixed two bugs found in the browser run (offline start signed people out; duplicate offline sends could return an error) | *To be filled in by each owner* |

## Session 2: the frontend in plain HTML, CSS and JavaScript (11 Nov 2026), requested by Emmanuel Happy Rangira

| What was asked | What the AI produced | How it was changed afterwards |
|---|---|---|
| Rewrite the frontend in HTML, CSS and JavaScript (it was Vue 3 + TypeScript + Vite) | `frontend/site/`: the whole app as plain ES modules, no framework, no packages, no build step (31 screens, 3 languages, router, offline outbox, optional saved copy, service worker, plain-SVG charts, inline Phosphor icons); `tools/make_precache.py` (service worker file list) and `tools/make_icons.py` (icon file); Node tests in `frontend/tests/` (62); Dockerfile, CI, Codespaces scripts and docs updated; the Vue sources and Vite/Vitest setup removed (still in git history) | *To be filled in by Happy (the app), Orion (Docker, CI, tools), Erica (locales, i18n test), Malaika (README, ownership)* |

Every file's first lines name its owner and say "AI-assisted draft". Remove that line only after you have rewritten
or fully reviewed the file, and say what you changed in the row above.

## Add a row each time you use AI

| Date | Who | Prompt (paste it) | Output (paste or link) | What you changed |
|---|---|---|---|---|
| | | | | |
