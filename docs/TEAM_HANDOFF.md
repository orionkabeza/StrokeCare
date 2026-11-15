<!-- Owner: Malaika Elohim Isingizwe Mukama (Scrum Master) · AI-assisted draft, see AI_USE_LOG.md -->
# How the team moves the new app into our repository

The new app goes into **https://github.com/EricaSheja/stroke_care_development**, the repository we started from. It
replaces the prototype on `master`. The prototype stays in the history, because we remove its files in a normal
commit: nothing is force-pushed and nothing is rewritten.

Every file belongs to exactly one of us (`OWNERS.json`). Each person gets a zip of **their own files**, made by
`python tools/make_handoff.py`. The folders inside the zip are the real folders. The app only runs once all six zips
are in, so we build it up on one shared branch, `new-app`, and merge that into `master` once, after a full check.

| Order | Who | Files | What they are |
|---|---|---|---|
| 1 | Orion | 32 | settings, Docker, compose, CI, Codespaces, tools, requirements, test setup, deployment docs |
| 2 | Kenneth | 50 | access control, sharing links, audit log, alerts and scheduler, doctor overview, messaging, role-matrix tests |
| 3 | Axel | 65 | accounts, health records, medicines, calendar, home visits, recovery, the week endpoint, emergency contacts, migrations |
| 4 | Erica | 29 | content (Learn, emergency guidance, talk board), fixtures, safety tests and docs, the three translation files |
| 5 | Malaika | 5 | README, `OWNERS.json`, `AI_USE_LOG.md`, this guide, PR template |
| 6 | Happy | 64 | the web app in `frontend/site/` and its tests |

## Before anyone starts (Erica, once)

On GitHub: **Settings → Collaborators → Add people**, and add Orion, Kenneth, Axel, Malaika and Happy with **Write**
access. Everyone accepts the invitation from their email.

## Before you start (everyone, once)

Install Git, and make sure your commits carry **your** name and the email of **your** GitHub account, or they will
not count as yours:

```bash
git config --global user.name  "Your Full Name"
git config --global user.email "the-email-on-your-github-account"
```

## Step 1: Orion starts the branch

```bash
git clone https://github.com/EricaSheja/stroke_care_development.git
cd stroke_care_development
git checkout -b new-app
git rm -r -q .                       # removes the prototype's files from this branch (they stay in the history)
# unzip Orion_Kabeza.zip here, at the root of the repository, keeping its folders
git add -A
git commit -m "Replace the prototype with the new app: settings, Docker, CI, tools"
git push -u origin new-app
```

Then tell the group chat "step 1 done".

## Steps 2 to 6: everyone else, in the order above

Wait for the person before you to say they are done, then:

```bash
git clone https://github.com/EricaSheja/stroke_care_development.git   # first time only
cd stroke_care_development
git fetch origin
git checkout new-app                 # first time; afterwards: git switch new-app
git pull
# unzip <Your_Name>.zip here, at the root of the repository, keeping its folders
git status                           # only your files should appear as new
git add -A
git commit -m "Add <your area>"      # for example "Add access control, sharing links and audit log"
git push
```

If `git push` is refused because someone pushed first, run `git pull --rebase` and then `git push` again. Our files
never overlap, so this cannot conflict.

On Windows, unzip with **Extract All** (or 7-Zip) and choose the repository folder itself, not a new subfolder:
`backend/`, `frontend/` and `docs/` must land at the top of the repository.

## Step 7: Orion checks the whole app, then opens the pull request

From a fresh clone of `new-app`:

```bash
docker compose up --build -d
docker compose exec web python manage.py seed_demo --password 'admin@2025!'
docker compose exec web python manage.py add_emergency_contact --region Rwanda --label "SAMU ambulance" \
    --kind ambulance --phone 912 --verified-by "Emmanuel Happy Rangira"
docker compose exec web sh -c "pip install --user -q -r requirements-dev.txt && python -m pytest -p no:warnings -q"
cd frontend && npm test && cd .. && python tools/make_precache.py --check && python tools/make_handoff.py --check
```

Open http://localhost:8000 and sign in as `demo-survivor@example.org` with `admin@2025!`. Then open a pull request
from `new-app` into `master`, fill in the template, and link the Trello card. CI runs the backend and frontend
checks; both must be green.

## Step 8: review and merge

Reviewers (from the team report): Kenneth ↔ Axel review each other, Axel reviews Happy, Malaika ↔ Erica review each
other, Kenneth reviews Orion. Each reviewer reads the files of the person they review and leaves at least one real
comment or question. Then Erica merges with **"Create a merge commit"**. Do **not** use "Squash and merge": it would
fold everyone's commits into one and erase who did what.

## After the merge: everyday work

Every change from now on goes through a branch and a pull request, never straight to `master`:

```bash
git switch master && git pull
git switch -c feature/<what-you-are-doing>
# change, test, commit in small steps
git push -u origin feature/<what-you-are-doing>
# open a pull request, link the Trello card, get one approval, merge with a merge commit
```

## Your files are yours

Read every file in your zip until you can explain it. Your starting points and the questions you should be able to
answer:

| Person | Start here | Questions you should be able to answer |
|---|---|---|
| Orion | `settings.py`, `Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml`, `tools/make_precache.py` | Why does the app refuse to start without a secret and a PostgreSQL URL? Why is there no front-end build, and what does `make_precache.py` do and when must it run? |
| Kenneth | `apps/common/access.py`, `apps/care/`, `test_role_matrix.py` | Why 404 for strangers but 403 for a missing scope? How does withdrawing consent cut access? |
| Axel | `apps/accounts/`, `apps/health/`, `apps/recovery/` (including `build_week`) | How is "one tick per task per day" guaranteed? How does the week endpoint leave out a metric that was not shared? |
| Erica | `apps/content/`, `docs/SAFETY.md`, `test_safety.py`, `fixtures/`, `locales/` | Where is each safety rule enforced? Why can no phone number be in the code, and how is 912 added? |
| Happy | `frontend/site/js/router.js`, `dom.js`, `api.js`, `components/metric-card.js`, `views/patient/check-in.js` | How does a screen draw and keep what you typed? Why can a name never become markup? How does the offline outbox work? |
| Malaika | `README.md`, `OWNERS.json`, `AI_USE_LOG.md`, this guide | Which open questions are decisions, and who owns each? |

## Course rules

The course says individual marks follow **your own coding contributions**, and that AI use outside its guidelines is
penalised. These files were drafted with AI help, and every file says "AI-assisted draft" at the top. So:

- Record the AI use in `AI_USE_LOG.md`: what was asked, what it produced, and what you changed. Malaika keeps it
  complete.
- Your real contribution is what you do after this: review, test, fix and improve your files, in your own commits.
  When you have truly reviewed or rewritten a file, remove its "AI-assisted draft" line.
- Write the reports yourselves: the Canvas instructions say not to use AI to generate them.
- Check with the teaching team how they want the AI use presented before the final submission.
