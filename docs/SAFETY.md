<!-- Owner: Erica Rurangwa Sheja (Product Owner) · AI-assisted draft, see AI_USE_LOG.md -->
# Safety rules, and where each one is enforced

These carry over from the team's safety boundary (`docs/safety.md` in the prototype). A rule that only lives in a
document gets broken; each one below is also a test or a database constraint.

| # | Rule | Enforced by |
|---|---|---|
| 1 | The app does not diagnose, prescribe, predict or score risk | No such field exists in any model or response. `test_safety.py` scans every patient-facing response and model for judgement words (risk, score, normal, high, low, threshold, …) |
| 2 | Blood pressure is numbers only: no colour, label, band or threshold | Same tests. Extreme values return the same shape as ordinary ones. The only limits in code reject typing mistakes (`apps/common/limits.py`) |
| 3 | Emergency guidance says to contact local emergency services and **not to wait for the app** | `apps/content/guidance.py`; tested |
| 4 | No emergency phone number is shown until verified by a named person with a date | `EmergencyContact` is hidden unless `verified_at` is set; the database refuses a verified contact with no verifier; a test fails on ANY digit in guidance text or fixtures, so a number cannot be hard-coded |
| 5 | Nothing is "reviewed" without a named reviewer and a date | Database check constraints on education, translations and check-in questions. All content ships as `draft` and the API always returns source + review status so the app can show them |
| 6 | Education and check-in content is never silently missing: show English if a translation is missing | `apps/common/locale.py`; response says `fell_back: true` |
| 7 | An urgent check-in answer shows urgent guidance at once | Question data carries `urgent_values`; the API returns them so the app can react before the form is sent, and the submit response repeats the guidance |
| 8 | Health data is processed only with a current consent, and sharing is opt-in | Consent gate on every patient route; links are created by the patient |
| 9 | The summary describes, never judges | Counts, averages, and the person's own words, plus a disclaimer. Interpretation is the clinician's |
| 10 | Data is shown only to people the patient chose, and each access is recorded | `resolve_access` + append-only audit log |
| 11 | Real data only with supervisor direction and ethics approval; demos use fictional records | `seed_demo` refuses to run unless `ALLOW_DEMO_DATA` is on; demo emails are `@example.org` |
| 12 | The app never suggests, doses or changes a medicine | Only a verified clinician has `manage_meds`; patients and caregivers can only mark a scheduled dose as taken; tested in the role matrix and `test_medicines_and_visits.py` |
| 13 | "Not marked as taken" is a fact, not blame and not advice | Wording in the API and UI; no advice text anywhere |
| 14 | Alerts and "needs a look" filters are facts (dates, counts), never a risk score or ranking | `patient_facts`; tested for judgement words; alerts carry a "not an emergency service" note |
| 15 | Talk-board phrases are everyday needs only | Fixture is reviewed like any content (DB constraint) and ships as draft. There are no recordings: the phone's own voice reads the words when it has one for the language |
| 16 | Messages and alerts are not an emergency service | Every thread and alert response carries that notice, and the app shows it |
| 17 | A community health worker never writes the plan or the medicine list | `CHW_ALLOWED` scopes; tested |
| 18 | Only real audio is stored as a voice note, with size and length caps; listening by others is audited | File signature check; tests send fake audio, images and text |
| 19 | French and Kinyarwanda texts are AI drafts until a native speaker reviews them | Content keeps `draft` status; Settings says so; `seed_reference` never overwrites a reviewed row |
| 20 | Personal health data is not cached by the service worker | Only public endpoints are in the PWA's runtime cache (`PUBLIC_API` in `frontend/site/sw.js`; `frontend/tests/site.test.js` fails if a personal path matches it). The one exception is the person's own opt-in copy, rule 24 |
| 21 | Movement, goals and the progress dashboard are counts and plain words only: no score, grade, percentage, streak, target or "improvement" | No such field exists on `Goal`, `MobilityLog`, `CarePhase` or `CustomPhrase`; `test_no_judgement_field_*` covers every new response; `test_progress_has_no_percentages_streaks_or_targets`; an empty day is empty, never a "miss" |
| 22 | A recovery stage is the clinician's own wording. The app ships no medical definition of a stage | Written only with `manage_plan` (verified clinician); no stage fixture or default exists; patients, caregivers and health workers get 403 |
| 23 | The doctor's overview lists facts in NAME order, never ranked by importance or risk | `test_doctor_overview_lists_facts_in_name_order...`; only linked, consenting patients and granted scopes appear |
| 24 | The optional offline copy is OFF by default, holds only the person's own plan-type data, never blood pressure, check-ins or messages, belongs to one person, and is wiped at sign-out | `frontend/tests/offline-copy.test.js` and `auth-offline.test.js`; Settings explains it keeps data on the phone until sign-out |
| 25 | Nothing in a check-in is ever pre-answered. An unanswered question is sent as skipped, and an urgent answer shows emergency guidance at once even with all questions on one screen | `frontend/site/js/views/patient/check-in.js`; browser run `Check-in ... Nothing is pre-answered`, `Emergency guidance shows at once, before sending` |
| 26 | Being offline never signs a person out | `auth.load` ends the session only on a 401 or 403 from the server; `frontend/tests/auth-offline.test.js` |

## Frontend rules (for Happy)

- Never colour, badge, arrow or animate a blood pressure value to suggest good or bad.
- Show the emergency banner/button on every screen. When a question has `urgent_values` and the user picks one, show guidance immediately, before submitting.
- Show each education item's source and review status. Mark `draft` content visibly.
- Do not write medical copy in the UI. Medical text comes from the API (reviewed content) or waits for review.
- Use the tokens in `frontend/site/css/tokens.css`. Red (`--danger`) is for emergency help only.
- Put text from people or the server into the page only through an `html` template (it escapes), never with `innerHTML` and never by gluing strings into markup. Use `raw()` only for markup the code built itself (`frontend/tests/dom.test.js`). Add no inline scripts or `onclick="..."`: the Content Security Policy blocks them and `frontend/tests/site.test.js` fails.
- Never add streaks, scores or confetti. Recovery is not a game, and a broken streak shames people.
- No targets, no percentages, no colour that means good or bad on the movement log or the progress screens. Show counts and a table with the same numbers.
- A day before a plan, a medicine or a reading existed is an empty day ("–"), never "0 of 3".
