<!-- Owner: Orion Kabeza (DevOps) · AI-assisted draft, see AI_USE_LOG.md -->
# Run StrokeCare in GitHub Codespaces

Nothing to install on your computer. You need a GitHub account and a browser.

1. On the repository page, choose **Code → Codespaces → Create codespace on main**
   (or use the "Open in GitHub Codespaces" button in the main README).
2. Wait for the first build. It installs the backend packages, creates the database and loads fictional demo data
   (the web app is plain files, so there is nothing to build). This takes a few minutes the first time.
3. When it is ready, the app opens in a preview tab. If it does not, open the **Ports** tab and open port **8000**
   in the browser.
4. Sign in with one of the demo accounts. The password for all of them is in `.demo-credentials.txt` in the root
   folder (it is created for your codespace only and is never committed). It is also printed at the end of the
   creation log.

| Role | Email |
|---|---|
| Stroke survivor | `demo-survivor@example.org` |
| Prevention user | `demo-prevention@example.org` |
| Caregiver | `demo-caregiver@example.org` |
| Clinician | `demo-clinician@example.org` |
| Community health worker | `demo-chw@example.org` |
| Admin | `demo-admin@example.org` |

The data is fictional. Do not enter real health information in a codespace.

## What starts, and where

| | |
|---|---|
| App and API together | port 8000 (Django serves the web app's files from `frontend/site`) |
| API documentation | `/api/v1/docs/` on the same address |
| Alert worker | runs in the background every 15 minutes |
| Database | PostgreSQL 16 in a second container, data kept between stops and starts |
| Logs | `/tmp/strokecare-web.log` and `/tmp/strokecare-worker.log` |

Ports are **private** by default: only you, signed in to GitHub, can open the address. Keep it that way.

## Everyday commands

```bash
cd backend && .venv/bin/python -m pytest            # backend tests
cd frontend && npm test                             # frontend tests
bash .devcontainer/start.sh                         # restart the server and worker
bash .devcontainer/check.sh                         # check that everything is running
```

After changing frontend code (any file under `frontend/site/`), just reload the page: there is no build and no dev
server. Then run `python tools/make_precache.py` so the offline file list stays current.

## Check that it is running

The checks run by themselves at the end of every start. Run them again at any time:

```bash
bash .devcontainer/check.sh
```

It checks, in order: the server answers on port 8000, the web app page loads, the `*.app.github.dev` address that
GitHub's forwarding uses is accepted, the API and database answer, the alert worker runs, and the demo accounts
exist. Every failed check says what to run next. When all pass it prints the address to open.

### "HTTP ERROR 401" in the browser

If `check.sh` passes but the browser shows **HTTP ERROR 401**, the app is fine and GitHub's port forwarding is asking
you to sign in (StrokeCare itself never returns 401 for a page). Do this:

1. Open it from the **Ports** tab: hover over port 8000 and click the globe icon (**Open in Browser**). Do not paste
   the address into a new tab.
2. Be signed in to GitHub, in the same browser profile, as the account that owns the Codespace.
3. Allow cookies for `[*.]github.dev` (in Chrome: `chrome://settings/cookies`, "Sites that can always use
   cookies"). Blocked third-party cookies are the usual cause.
4. Last resort: Ports tab, right-click port 8000, **Port Visibility**, **Public**. Anyone with the address can then
   open the app, so set it back to **Private** afterwards.

### Update an existing Codespace

A Codespace made before a fix was pushed keeps the old scripts. Get the new ones and restart:

```bash
git pull
bash .devcontainer/start.sh
```

## If something goes wrong

- **The page says the host is not allowed or the sign-in fails with a network error:** the address does not end in
  `.app.github.dev`. Use the address from the Ports tab.
- **Nothing on port 8000:** run `bash .devcontainer/start.sh`, then read `/tmp/strokecare-web.log`.
- **Start again from scratch:** delete the codespace and create a new one. This removes the demo data and database.
- **Cost:** a codespace uses your GitHub plan's free monthly allowance (check GitHub's current limits). Stop it when
  you are done: it stops by itself after a period of inactivity.

## Status

The setup, start and check scripts were run end to end in a clean copy of the repository against PostgreSQL 16, with
the environment values from `devcontainer.json` and a Codespaces-style host name: first start, restart, and a dead
server (the checks fail as they should). The dev container itself (the two containers and GitHub's port forwarding) has
not been built by the person who wrote it, because no Docker was available there. If a Codespace fails to build, send
the creation log to Orion.
