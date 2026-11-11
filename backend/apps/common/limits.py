"""Owner: Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md

Plausibility limits for typed blood pressure numbers. They exist only to reject typing mistakes
such as 1200 or 0. They are NOT clinical thresholds and must never be shown as a "normal range".
Safety rule: a qualified clinician should confirm these limits before real use (open item).
"""
BP_SYSTOLIC_MIN, BP_SYSTOLIC_MAX = 40, 300
BP_DIASTOLIC_MIN, BP_DIASTOLIC_MAX = 20, 200
PULSE_MIN, PULSE_MAX = 20, 250
FUTURE_CLOCK_SKEW_MINUTES = 5
NOTE_MAX_LENGTH = 500

# Recovery, mobility and personal phrases. Typing limits only; none of these is a clinical threshold.
GOAL_MAX_LENGTH = 200
PHRASE_MAX_LENGTH = 80
PHRASES_PER_PATIENT = 30
PHASE_NAME_MAX_LENGTH = 80
PHASE_CARE_MAX_LENGTH = 1000
MOBILITY_MINUTES_MAX = 600
MOBILITY_BACKFILL_DAYS = 30
