<!-- Owner: Orion Kabeza (DevOps) -->
# Hosting for the pilot

**No real patient data goes on any host until every item in `docs/OPEN_QUESTIONS.md` marked BLOCKER is closed**:
a named clinical reviewer, verified emergency contacts, ethics approval and supervisor direction, written
consent and privacy text, a check on Rwandan data-protection and health-software rules, and a hosting decision
for *real* health data specifically (this document is about the pilot, with fictional demo data only — see
blocker 6). Until then, every option below runs with `ALLOW_DEMO_DATA=1` and fictional accounts.

Prices and regions for every provider below change often; re-check each provider's own pricing and region pages
before paying for anything. This review was done in November 2026.

## What the pilot needs

- One Docker image serving the app and the API (already built: `Dockerfile`), plus a worker **or** the GitHub
  Actions scheduler (already built: `.github/workflows/scheduler.yml`) for caregiver alerts.
- A managed PostgreSQL 16 database: automated backups, and a restore that has actually been tested.
- Automatic HTTPS on a custom domain.
- Low enough latency from Rwanda to be usable; nothing here is latency-sensitive in the way a game would be, but a
  page that takes several seconds to respond will be read as broken.
- A reasonable answer, even for a pilot, to "where does the data live and who can get at it" — because the
  habits and secrets set up now (where the database lives, who holds the password) are the ones that carry into
  the real-data phase if the team is not deliberate about it.

## Options compared

No option below has a data centre in Rwanda or East Africa. The only one with an Africa-based region at all is
AWS, in Cape Town (`af-south-1`) — roughly 3,000 km from Kigali, still closer than any European or US region.
Everything else means routing to Europe (Fly.io and Render's closest region is Frankfurt) or further.

| | A. Render (Docker + managed Postgres) | B. Fly.io (Docker + managed Postgres) | C. Railway (Docker + Postgres) | D. Small VPS with `docker compose` (e.g. Hetzner, DigitalOcean, or AWS EC2 in `af-south-1`) |
|---|---|---|---|---|
| **Fit with this repo** | Direct: builds `Dockerfile` as-is, one web service, a separate "Background Worker" service for `run_scheduler`, or skip the worker and use the GitHub scheduler | Direct: same one-image model, `fly.toml` on top of the existing Dockerfile | Direct: same model, Railway builds the Dockerfile | Direct, but **you** run `docker compose up -d` and keep it running (systemd unit, restart policy) |
| **Nearest region to Rwanda** | Frankfurt (EU) | Frankfurt (EU) for Managed Postgres; a compute-only region in Johannesburg exists but its managed Postgres does not run there, so splitting app and database across continents would add cross-region latency instead of removing it | US / EU / Asia-Pacific only, no Africa or Middle East region | Your choice — `af-south-1` (Cape Town) is the only real African option among major clouds; Hetzner/DigitalOcean are Europe/US only |
| **Managed Postgres, with backups** | Yes, on a paid plan: automated daily backups, point-in-time recovery on higher tiers | Yes: Fly Managed Postgres, from about $38/month on its base plan (verify at deploy time) | Added HA Postgres in 2026 (Patroni-based); third-party reviews call it still new, so treat backup maturity as unproven | Only if you add RDS (extra cost and setup) or run Postgres yourself on the VPS and are personally responsible for backups and tested restores |
| **Automatic HTTPS** | Yes, out of the box | Yes, out of the box | Yes, out of the box | No — you configure TLS yourself (e.g. Caddy or nginx + Let's Encrypt in front of `docker compose`) |
| **Cost for a small pilot** | Low: a small web service plus a small Postgres plan, roughly in the $10-25/month range depending on the tier chosen | Similar range; Managed Postgres alone starts around $38/month, which is more than this pilot needs unless storage/compute requirements grow | Lowest sticker price (Hobby tier from $5/month) but Postgres is metered on top | Cheapest compute (a few dollars a month for a small VPS) but the real cost is your team's time: patching, backups, TLS, monitoring |
| **Operational effort for a student team** | Low | Low | Low | High — nothing is managed; every item in the "First deploy checklist" in `docs/DEPLOYMENT.md` is on you |
| **Encryption at rest** | Provider-managed (check their current docs to confirm) | Provider-managed | Provider-managed, newer feature set | Only if you set it up (e.g. encrypted volumes) |
| **Who can access the data** | Render's own staff, under their security policy — check their current SOC 2 / compliance status before trusting it with real health data | Fly's own staff, under their policy | Railway's own staff | Only your team, if you manage the VPS yourself and lock it down — more containment, but only as good as your own practices |

## Oracle Cloud Always Free (also set up)

A second route, for a no-cost demo host: one Always Free VM running `docker-compose.prod.yml` (app, worker, PostgreSQL, Caddy for HTTPS). Closest region is Johannesburg. It has no managed database and no backups of its own, so it is for fictional demo data only. Steps: `docs/DEPLOY_ORACLE.md`.

## Recommendation

**Render**, EU (Frankfurt) region, for the pilot, with fictional demo data:

1. It matches this repository's architecture with no changes: one `Dockerfile`, no separate build step for the
   frontend (`frontend/site` is already plain files copied into the image).
2. Managed Postgres with automated backups and point-in-time recovery on a paid tier means the team is not
   building and testing its own backup script before the first demo.
3. Automatic HTTPS and a custom domain are included, which `docs/DEPLOYMENT.md`'s production hardening
   (`SESSION_COOKIE_SECURE`, HSTS, etc.) already assumes.
4. It needs the least ongoing attention from a team that is not staffing 24/7 operations — unlike option D, where
   every security patch and every backup is the team's own job.
5. For the pilot, skip Render's paid "Background Worker" service and use the GitHub Actions scheduler already
   built in `.github/workflows/scheduler.yml` (set `STROKECARE_URL` and `CRON_SECRET` as repository secrets) —
   it is free and already reviewed, and `docs/DEPLOYMENT.md` already says running both the worker and the
   schedule is harmless but wasteful.

This is a recommendation for the **pilot with fictional data only**. Revisit it once blocker 5 (Rwandan
data-protection and health-software rules) and blocker 6 (hosting for real health data) in
`docs/OPEN_QUESTIONS.md` are resolved — at that point data residency (for example AWS `af-south-1`, the one
option here with an actual African region) may matter in a way it does not for a pilot.

### Deploy steps (Render)

1. Create a Render account linked to the team's GitHub org; connect the `StrokeCare` repository.
2. **New Web Service** → build from the root `Dockerfile` → region **Frankfurt**. Render detects the `EXPOSE 8000`
   and the image's `CMD`; no changes needed.
3. **New PostgreSQL** → version 16 → same region. Copy its internal connection string.
4. On the web service, set the environment variables from the "Environment variables (production)" table in
   `docs/DEPLOYMENT.md`: `DJANGO_SECRET_KEY` (generate a long random value), `DATABASE_URL` (the string from
   step 3), `DJANGO_ALLOWED_HOSTS` (the Render domain, then the custom domain once added),
   `CSRF_TRUSTED_ORIGINS`, `DATABASE_SSL_REQUIRE=1`. Leave `ALLOW_DEMO_DATA=1` for the pilot only — never for
   real users.
5. Enable auto-deploy on push to `main` (or restrict it to tagged releases, team's choice).
6. Add the custom domain in Render's dashboard; it issues and renews the TLS certificate automatically.
7. Set `STROKECARE_URL` (the Render URL) and `CRON_SECRET` (a long random value, matching `CRON_SECRET` on the
   web service) as GitHub repository secrets so `.github/workflows/scheduler.yml` can call the app every 15
   minutes.
8. After the first deploy: `python manage.py createsuperuser` via Render's shell, confirm `/healthz` returns
   `{"status": "ok"}`, and test one database restore from Render's backup panel before telling anyone the pilot
   is ready.
9. Confirm Render's current backup retention and point-in-time recovery window on the plan chosen, and write the
   result down here or in `docs/DEPLOYMENT.md` so it does not need re-checking every time.
