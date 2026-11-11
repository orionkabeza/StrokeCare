"""What a linked person may do. The patient chooses, and can change or end it at any time.

Owner: Kenneth Master (System architect) · AI-assisted draft, see AI_USE_LOG.md
Safety rule: least privilege. A clinician can write the recovery plan but cannot log readings for the
patient; a caregiver can log on the patient's behalf but can never change the clinician's plan.
"""
VIEW_READINGS = "view_readings"
LOG_READINGS = "log_readings"
VIEW_PLAN = "view_plan"
MANAGE_PLAN = "manage_plan"
LOG_TASKS = "log_tasks"
VIEW_CHECKINS = "view_checkins"
LOG_CHECKINS = "log_checkins"
VIEW_SUMMARY = "view_summary"
VIEW_MEDS = "view_meds"
LOG_MEDS = "log_meds"  # tick a dose as taken
MANAGE_MEDS = "manage_meds"  # write the medicine list (clinician only)
VIEW_NOTES = "view_notes"  # questions for the next visit
ADD_NOTES = "add_notes"
MESSAGE = "message"  # read and write the care-team conversation
VIEW_CALENDAR = "view_calendar"  # family care calendar and handover notes
EDIT_CALENDAR = "edit_calendar"
LOG_VISITS = "log_visits"  # community health worker home visits
VIEW_MOBILITY = "view_mobility"  # movement log: what the person did and how much help they used
LOG_MOBILITY = "log_mobility"

ALL_SCOPES = frozenset(
    {VIEW_READINGS, LOG_READINGS, VIEW_PLAN, MANAGE_PLAN, LOG_TASKS, VIEW_CHECKINS, LOG_CHECKINS, VIEW_SUMMARY,
     VIEW_MEDS, LOG_MEDS, MANAGE_MEDS, VIEW_NOTES, ADD_NOTES, MESSAGE, VIEW_CALENDAR, EDIT_CALENDAR, LOG_VISITS,
     VIEW_MOBILITY, LOG_MOBILITY}
)  # fmt: skip

CLINICIAN_ALLOWED = frozenset(
    {VIEW_READINGS, VIEW_PLAN, MANAGE_PLAN, VIEW_CHECKINS, VIEW_SUMMARY, VIEW_MEDS, MANAGE_MEDS, VIEW_NOTES,
     MESSAGE, VIEW_CALENDAR, EDIT_CALENDAR, VIEW_MOBILITY}
)  # fmt: skip
CAREGIVER_ALLOWED = frozenset(
    {VIEW_READINGS, LOG_READINGS, VIEW_PLAN, LOG_TASKS, VIEW_CHECKINS, LOG_CHECKINS, VIEW_SUMMARY,
     VIEW_MEDS, LOG_MEDS, VIEW_NOTES, ADD_NOTES, MESSAGE, VIEW_CALENDAR, EDIT_CALENDAR, VIEW_MOBILITY, LOG_MOBILITY}
)  # fmt: skip
# Community health workers visit people at home: they may take a reading and record the visit, never change the
# clinician's plan or medicine list.
CHW_ALLOWED = frozenset(
    {VIEW_READINGS, LOG_READINGS, VIEW_PLAN, VIEW_CHECKINS, VIEW_SUMMARY, VIEW_MEDS, VIEW_NOTES, ADD_NOTES,
     MESSAGE, VIEW_CALENDAR, EDIT_CALENDAR, LOG_VISITS, VIEW_MOBILITY, LOG_MOBILITY}
)  # fmt: skip

DEFAULT_SCOPES = {
    "clinician": sorted(CLINICIAN_ALLOWED),
    "caregiver": sorted(CAREGIVER_ALLOWED),
    "chw": sorted(CHW_ALLOWED),
}
ALLOWED_SCOPES = {"clinician": CLINICIAN_ALLOWED, "caregiver": CAREGIVER_ALLOWED, "chw": CHW_ALLOWED}

# A person acting on their own record can do everything except write their own clinical plan or medicine list.
SELF_SCOPES = ALL_SCOPES - {MANAGE_PLAN, MANAGE_MEDS, LOG_VISITS}
