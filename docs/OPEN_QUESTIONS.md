<!-- Owner: Erica Rurangwa Sheja (Product Owner) · AI-assisted draft, see AI_USE_LOG.md -->
# Open questions and launch blockers

The code is built to be safe by default, but a product for real patients also needs things code cannot supply.
Nothing below is solved by this repository. Items marked **BLOCKER** must be closed before real users.

## Blockers (not code)

| # | What | Why it blocks | Who can close it |
|---|---|---|---|
| 1 | **No named clinical reviewer** (the team report: DEL-002 not started, DEC-003 open) | No education text, check-in question, threshold or emergency instruction can be marked reviewed. The database refuses "reviewed" without a name and date. | Supervisor / clinical partner |
| 2 | **Emergency contacts are unverified** (DEC-004, R-004) | The app shows NO number until a verifier signs one off. The seed data contains none. | Clinical or local health partner |
| 3 | **Ethics approval and supervisor direction** for real users and real data (team report) | Required before interviews or any identifiable health data. | Supervisor |
| 4 | **Consent and privacy text is not written.** Versions are the placeholder `0.1-draft`. | Users cannot give informed consent to text that does not exist. | Product owner + legal advice |
| 5 | **Rwandan data-protection and health-software rules have not been checked** by anyone on this build, including whether the app counts as regulated medical software. | Unknown legal exposure with real health data. | Supervisor / legal advice |
| 6 | **Hosting for real health data.** The team's own report lists compliant hosting, encryption at rest and backups as planned. Free tiers may sleep, expire or lack backups: check each provider's current terms before relying on one. | Losing or leaking patient data. | DevOps |
| 7 | **All Kinyarwanda and French text is an AI draft**, including the emergency guidance, check-in questions, talk-board phrases and every screen. | A wrong word in an emergency or medical sentence can mislead. | Native-speaker clinical translator: review `frontend/src/locales/*.json`, `backend/apps/*/fixtures/*.json`, `apps/content/guidance.py`, `apps/community/models.py` |
| 8 | **Only 4 of the 10 draft check-in questions** are in the repo: the other six were not visible to the builder. Answer options for two of the four were proposed by the developer. | Incomplete and unreviewed questions. | Erica: edit `apps/health/fixtures/checkin_questions.json` |
| 9 | **Not tested with real users**: screen readers, slow networks, aphasia-friendly mode, one-handed use. | Accessibility claims are unproven. | Team + stroke survivors/caregivers |
| 10 | **Medicine flow, talk-board phrases and alert wording need clinical review.** The medicine screen records what a clinician wrote; nobody has checked the wording with a clinician yet. | Wrong or frightening wording around medicines. | Clinical reviewer |

11. **Movement log categories need clinical review.** "Walking, standing up, stretching, wheelchair, other" and "on my own, with an aid, with another person's help" were chosen by the builder as everyday words. They are not a clinical scale. A clinician or therapist should confirm them. | The log still works; it shows counts only.
12. **Recovery stages are free text by design.** The app ships no definition of a stage, so there is nothing to review, but the team should decide whether clinicians want ready-made stage templates, and who writes and reviews them.
13. **The optional offline copy keeps personal data on a phone** (off by default, own plan data only, wiped at sign-out). Confirm the wording of the warning, and whether ethics approval needs to cover it, because phones are often shared.
14. **All new French and Kinyarwanda texts** (about 160 strings for these features) are AI drafts, like the rest. The app says so, and a native speaker with clinical knowledge must review them.

## Decisions the team still needs to make

1. **Login identifier.** Email now. Many users may not have email: should it be a phone number instead (or as well)? This changes the user table.
2. **SMS, USSD or push for alerts and reminders.** Alerts and reminders appear in the app; nothing reaches a closed phone yet. Needs a provider, cost, and a rule for who pays.
3. **Blood pressure typing limits** (`apps/common/limits.py`): the current numbers only catch typos. A clinician should confirm them.
4. **Who approves clinician accounts** in production, and how their licence is checked (`create_clinician --verified`, or the admin site).
5. **Retention.** How long is data kept after the last login or after consent is withdrawn? Today it is kept until the person deletes the account.
6. **Platform (DEC-002)** is still "To Confirm" with the sponsor.
7. **Caregiver role.** The prototype deferred it. It is built here; confirm the team wants it in scope.

## Known technical follow-ups

- The generated API docs at `/api/v1/docs/` are incomplete for some endpoints (no request/response schemas yet). Frontend work needs them: add `@extend_schema` to the views.
- `Dockerfile` and `docker-compose.yml` were written but not built in the session that created them.
- Login throttling uses per-process memory. With more than one server instance, use a shared cache.
- The audit log is append-only in application code. In production also remove UPDATE/DELETE on `audit_auditlog` from the app's database role.
- Reminders and appointment reminders show inside the app (Today, Reminders, caregiver alerts). Nothing reaches a closed phone yet: SMS or push needs a provider.
- A link made before the movement log existed does not share it until the patient adds it in Sharing (by design: nothing new is shared silently).
- The browser run (`e2e`) used in the build session now also covers the new features, but it is still not in CI.
- The scheduler (worker or GitHub cron) creates alerts on time, but they are only seen when the app is opened. Push or SMS delivery is the next step.
- Voice notes are stored in PostgreSQL. Fine for a pilot; move them to object storage if the database grows large.
- Reading aloud uses the phone's own voice; many phones have no Kinyarwanda voice. Recorded audio was removed on request.
- Tokens are in the browser's localStorage so people stay signed in; the strict Content Security Policy is the main defence against script injection reading them.
- The browser end-to-end run used in the build session is not in CI yet. Add it with `@playwright/test`.
