<!-- Owner: Kenneth Master (System architect) · AI-assisted draft, see AI_USE_LOG.md -->
# Roles and permissions

## Account types

| Role | How it is created | Has its own health record? |
|---|---|---|
| Prevention user | self sign-up | yes (blood pressure, check-in, medicines, reminders; no recovery plan) |
| Stroke survivor | self sign-up | yes (everything above, plus a recovery plan written by a clinician) |
| Caregiver | self sign-up | no. Acts only for a patient who invited them |
| Clinician | created by an administrator, then **verified** | no. Sees only patients who invited them |
| Community health worker (CHW) | created by an administrator, then **verified** (`create_clinician --role chw`) | no. Sees only people who invited them; records home visits |
| Administrator | created by an administrator | no. Edits content and verifies professionals. Cannot see patients' records |

## What a patient can share (the "scopes")

The patient picks these when inviting (sensible defaults are pre-selected), can change them at any time, and can end
the link at any time. The other person can also end it.

| Scope | Clinician | Caregiver | CHW | Patient on own record |
|---|---|---|---|---|
| `view_readings` / `log_readings` | view | view + log | view + log | both |
| `view_plan` / `manage_plan` (write the plan) | view + **write** | view | view | view only |
| `log_tasks` (tick tasks) | no | yes | no | yes |
| `view_checkins` / `log_checkins` | view | both | view | both |
| `view_summary` | yes | yes | yes | yes |
| `view_meds` / `manage_meds` (write the list) / `log_meds` (mark taken) | view + **write** | view + mark | view | view + mark |
| `view_notes` / `add_notes` (visit questions, voice notes) | view (and tick "discussed") | both | both | both |
| `message` (care-team thread) | yes | yes | yes | yes |
| `view_calendar` / `edit_calendar` | both | both | both | both |
| `log_visits` (home visits) | no | no | **yes** | no |
| `view_mobility` / `log_mobility` (movement log) | view | view + log | view + log | both |

Other new features reuse existing scopes: **goals and personal talk-board phrases** use `view_notes` / `add_notes`
(the person's own words), **recovery stages** use `view_plan` / `manage_plan` (only a verified clinician writes them), and
the **progress dashboard** uses `view_summary`.

A link made before the movement log existed keeps the scopes the patient chose then. Nothing new is shared silently:
the patient adds `view_mobility` / `log_mobility` to an existing link in Sharing, and new links get them by default.

Only a verified clinician writes the plan and the medicine list. Only a verified CHW records home visits.

## Expected responses (exactly what `test_role_matrix.py` checks: 25 routes × 10 callers)

`me` = the caller's own record. Everyone else addresses the survivor by id.

| Route | Visitor | Survivor | Prevention | Other patient | Clinician | Unlinked clinician | Caregiver | Unlinked caregiver | Admin | CHW |
|---|---|---|---|---|---|---|---|---|---|---|
| GET readings | 401 | 200 | 200 | 404 | 200 | 404 | 200 | 404 | 403 | 200 |
| POST readings | 401 | 201 | 201 | 404 | 403 | 404 | 201 | 404 | 403 | 201 |
| GET plan | 401 | 200 | 404 | 404 | 200 | 404 | 200 | 404 | 403 | 200 |
| POST plan task | 401 | 403 | 403 | 404 | 201 | 404 | 403 | 404 | 403 | 403 |
| GET check-ins | 401 | 200 | 200 | 404 | 200 | 404 | 200 | 404 | 403 | 200 |
| POST check-ins | 401 | 201 | 201 | 404 | 403 | 404 | 201 | 404 | 403 | 403 |
| GET summary | 401 | 200 | 200 | 404 | 200 | 404 | 200 | 404 | 403 | 200 |
| Tick a task | 401 | 201 | 404 | 404 | 403 | 404 | 201 | 404 | 403 | 403 |
| GET medicines | 401 | 200 | 200 | 404 | 200 | 404 | 200 | 404 | 403 | 200 |
| POST medicine | 401 | 403 | 403 | 404 | 201 | 404 | 403 | 404 | 403 | 403 |
| POST visit question | 401 | 201 | 201 | 404 | 403 | 404 | 201 | 404 | 403 | 201 |
| GET messages | 401 | 200 | 200 | 404 | 200 | 404 | 200 | 404 | 403 | 200 |
| POST calendar event | 401 | 201 | 201 | 404 | 201 | 404 | 201 | 404 | 403 | 201 |
| POST home visit | 401 | 403 | 403 | 404 | 403 | 404 | 403 | 404 | 403 | 201 |
| GET voice notes | 401 | 200 | 200 | 404 | 200 | 404 | 200 | 404 | 403 | 200 |
| GET movement log | 401 | 200 | 200 | 404 | 200 | 404 | 200 | 404 | 403 | 200 |
| POST movement entry | 401 | 201 | 201 | 404 | 403 | 404 | 201 | 404 | 403 | 201 |
| GET goals | 401 | 200 | 200 | 404 | 200 | 404 | 200 | 404 | 403 | 200 |
| POST goal | 401 | 201 | 201 | 404 | 403 | 404 | 201 | 404 | 403 | 201 |
| GET recovery stages | 401 | 200 | 200 | 404 | 200 | 404 | 200 | 404 | 403 | 200 |
| POST recovery stage | 401 | 403 | 403 | 404 | 201 | 404 | 403 | 404 | 403 | 403 |
| GET personal phrases | 401 | 200 | 200 | 404 | 200 | 404 | 200 | 404 | 403 | 200 |
| POST personal phrase | 401 | 201 | 201 | 404 | 403 | 404 | 201 | 404 | 403 | 201 |
| GET progress | 401 | 200 | 200 | 404 | 200 | 404 | 200 | 404 | 403 | 200 |
| POST several doses at once | 401 | 400* | 400* | 404 | 403 | 404 | 400* | 404 | 403 | 403 |

\* The matrix sends a medicine that does not exist, so the callers who are allowed get a 400 ("not on this person's
list"). It shows who is let in, not what they may mark.

Two more pages are not under `/patients/<ref>/`: `GET /doctor/overview/` is for clinicians only (403 for everyone else)
and `GET /me/care-team/` is for the person themselves (403 for a clinician).

404 means "no link, so we do not even confirm the person exists". 403 means "you are linked, but not for this".
Withdrawing the `health_data` consent turns every linked caller's 200 into 404 at once.
