<!-- Owner: Kenneth Master (System architect) · AI-assisted draft, see AI_USE_LOG.md -->
# Data model

The diagram is generated from the real Django models, so it cannot drift from the database. To refresh it:

```bash
cd backend && python ../tools/make_erd.py > ../docs/erd.mmd
```

Paste `docs/erd.mmd` into <https://mermaid.live> or any Mermaid viewer to see it, or into the course report's ERD section.

## Tables, in plain words

| Table | Holds | Notable rules |
|---|---|---|
| `accounts_user` | everyone who signs in | email stored lower-case (DB check); role; own time zone; clinicians carry `professional_verified_at` |
| `accounts_consent` | each consent grant, with version and revoke time | history is kept; a new notice version means asking again |
| `accounts_accessibilitypreference` | per-person display and input settings | every option defaults to off |
| `care_carelink` | patient ↔ clinician/caregiver sharing | invitation code stored only as a hash; unique active link per pair; scopes are an array |
| `health_bpreading` | blood pressure | DB checks: plausible range, top above bottom; index on (user, time); remembers who typed it |
| `health_recoveryplan`, `health_plantask`, `health_tasklog` | one plan per survivor; tasks; one tick per task per day | unique constraints |
| `health_checkinquestion` | the questions (data, per-language prompts, urgent answers) | cannot be "reviewed" without reviewer and date |
| `health_checkin`, `checkinanswer` | one check-in per person per day; one row per answer | answers are queryable, skippable |
| `health_reminder` | reminders (plan tasks, blood pressure, check-in, medicines, movement) | in-app only for now |
| `content_educationitem`, `educationtranslation` | education with source, clinical review, per-language review | reviewed ⇒ reviewer + date |
| `content_emergencycontact` | verified emergency contacts | hidden until verified |
| `health_medication`, `health_medicationdose` | the clinician's medicine list; a row per dose marked taken | one mark per dose; "not marked" is computed, never stored as blame |
| `health_visitquestion`, `health_voicenote` | questions for the next visit; voice notes (audio bytes in PostgreSQL) | audio checked by file signature, 5 MB and 3 minutes max |
| `health_plantemplate` | a clinician's reusable task lists | private to the clinician |
| `care_alert` | caregiver alerts: urgent answer, no check-in, doses not marked, appointment coming up | one per recipient per event (`dedupe_key`) |
| `messaging_message`, `messaging_threadread` | one care-team thread per patient; read markers | |
| `family_careevent`, `family_handovernote` | care calendar, handover notes | assignee must be in the care team; `remind_minutes_before` is one of 15, 30, 60, 120, 1440, 2880 |
| `recovery_goal` | goals in the person's own words, optional date | no score or percentage field exists |
| `recovery_carephase` | recovery stages named by the clinician, with dates and the care needed | DB check: end not before start; written only with `manage_plan` |
| `recovery_mobilitylog` | the movement log: kind, minutes, how much help, note | `client_id` makes a retry from an offline phone safe (unique per person); DB check on plausible minutes |
| `recovery_customphrase` | a person's own talk-board phrases | at most 30 per person |
| `community_homevisit` | CHW home visits | `client_id` from the phone is unique: safe re-sending |
| `content_talkphrase` | talk-board tiles | reviewed ⇒ reviewer + date |
| `audit_auditlog` | who accessed whose data | append-only; no health values stored |
| `token_blacklist_*` | revoked refresh tokens | from the JWT library |

Health records are keyed by UUID and always filtered by owner in the query.
