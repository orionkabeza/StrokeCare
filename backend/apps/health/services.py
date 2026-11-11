"""Owner: Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md

Safety rule for everything below: counts, averages and the person's own words. Never a label, a colour,
a band, a score, or a verdict.
"""
from collections import Counter
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.db import transaction
from django.db.models import Avg, Count
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.care import scopes as sc

from .models import CheckIn, CheckInAnswer, CheckInQuestion, Medication, MedicationDose, PlanTask, Reminder, TaskLog

SUMMARY_DISCLAIMER = (
    "A description of what the person entered. It is not a diagnosis and not medical advice. "
    "Interpretation belongs to the clinician."
)
NOTES_IN_SUMMARY = 20


def local_today(user):
    return timezone.now().astimezone(ZoneInfo(user.timezone)).date()


def _round(value):
    return None if value is None else round(float(value), 1)


@transaction.atomic
def save_checkin(subject, actor, date, cleaned):
    """Create or replace the check-in for one day. `cleaned` is [(question, value, skipped)]."""
    urgent = any((not skipped) and value in q.urgent_values for q, value, skipped in cleaned)
    checkin, _ = CheckIn.objects.update_or_create(
        user=subject,
        date=date,
        defaults={"submitted_at": timezone.now(), "urgent_answered": urgent, "entered_by": actor},
    )
    checkin.answers.all().delete()
    CheckInAnswer.objects.bulk_create(
        CheckInAnswer(checkin=checkin, question=q, value=None if skipped else value, skipped=skipped)
        for q, value, skipped in cleaned
    )
    return checkin


def build_summary(subject, days: int) -> dict:
    tz = ZoneInfo(subject.timezone)
    today = local_today(subject)
    first = today - timedelta(days=days - 1)
    start = datetime.combine(first, time.min, tzinfo=tz)
    end = datetime.combine(today + timedelta(days=1), time.min, tzinfo=tz)

    readings = subject.readings.filter(taken_at__gte=start, taken_at__lt=end)
    agg = readings.aggregate(n=Count("id"), sys=Avg("systolic"), dia=Avg("diastolic"))
    days_with_reading = readings.annotate(d=TruncDate("taken_at", tzinfo=tz)).values("d").distinct().count()

    logs = TaskLog.objects.filter(task__plan__patient=subject, date__range=(first, today))
    checkins = subject.checkins.filter(date__range=(first, today))
    answers = CheckInAnswer.objects.filter(checkin__in=checkins).select_related("question")

    per_question: dict[str, dict] = {}
    skipped = 0
    for a in answers:
        row = per_question.setdefault(
            a.question.code,
            {"question": a.question.code, "prompt": a.question.prompt.get("en", ""), "answered": 0, "skipped": 0,
             "value_counts": Counter()},
        )  # fmt: skip
        if a.skipped:
            row["skipped"] += 1
            skipped += 1
            continue
        row["answered"] += 1
        if a.question.answer_type != CheckInQuestion.AnswerType.TEXT:
            key = ("yes" if a.value else "no") if isinstance(a.value, bool) else str(a.value)
            row["value_counts"][key] += 1
    for row in per_question.values():
        row["value_counts"] = dict(row["value_counts"])

    notes = [
        {"at": r.taken_at, "source": "blood_pressure", "text": r.note}
        for r in readings.exclude(note="").order_by("-taken_at")[:NOTES_IN_SUMMARY]
    ]
    notes += [
        {"at": l.created_at, "source": "recovery_task", "text": l.note}
        for l in logs.exclude(note="").order_by("-created_at")[:NOTES_IN_SUMMARY]
    ]
    notes += [
        {"at": a.checkin.submitted_at, "source": "daily_check_in", "text": a.value}
        for a in answers.filter(question__answer_type="text", skipped=False)
        if a.value
    ]
    notes.sort(key=lambda n: n["at"], reverse=True)

    return {
        "period": {"from": first, "to": today, "days": days, "timezone": subject.timezone},
        "blood_pressure": {
            "readings": agg["n"],
            "days_with_a_reading": days_with_reading,
            "average_systolic": _round(agg["sys"]),
            "average_diastolic": _round(agg["dia"]),
            "unit": "mmHg",
        },
        "recovery_tasks": {
            "active_tasks": PlanTask.objects.filter(plan__patient=subject, is_active=True).count(),
            "ticks": logs.count(),
            "days_with_a_tick": logs.values("date").distinct().count(),
        },
        "daily_check_ins": {
            "submitted": checkins.count(),
            "questions_skipped": skipped,
            "days_urgent_question_answered_yes": checkins.filter(urgent_answered=True).count(),
            "by_question": sorted(per_question.values(), key=lambda r: r["question"]),
        },
        "medicines": _dose_counts(subject, first, today),
        "visit_questions_open": subject.visit_questions.filter(discussed_at__isnull=True).count(),
        "voice_notes": subject.voice_notes.filter(created_at__gte=start, created_at__lt=end).count(),
        "home_visits": subject.home_visits.filter(visited_at__gte=start, visited_at__lt=end).count(),
        "notes_in_their_own_words": notes[:NOTES_IN_SUMMARY],
        "disclaimer": SUMMARY_DISCLAIMER,
    }


def upcoming_reminders(user, horizon_days: int = 7):
    """Next time each active reminder is due, in the person's own time zone."""
    tz = ZoneInfo(user.timezone)
    now = timezone.now().astimezone(tz)
    out = []
    for r in Reminder.objects.filter(user=user, is_active=True):
        for offset in range(horizon_days + 1):
            day = now.date() + timedelta(days=offset)
            due = datetime.combine(day, r.time_of_day, tzinfo=tz)
            if day.weekday() in r.days_of_week and due > now:
                out.append({"id": r.id, "kind": r.kind, "next_at": due, "channel": r.channel})
                break
    out.extend(_upcoming_appointments(user, now, horizon_days))
    return sorted(out, key=lambda x: x["next_at"])


def _upcoming_appointments(user, now, horizon_days):
    """The person's own care-calendar events that start soon, so the app can show them as reminders."""
    from apps.family.models import CareEvent  # local import: the family app imports this module

    end = now + timedelta(days=horizon_days)
    events = CareEvent.objects.filter(patient=user, done_at__isnull=True, starts_at__gt=now, starts_at__lte=end)
    return [
        {
            "id": e.id, "kind": "appointment", "next_at": e.starts_at, "channel": "in_app", "title": e.title,
            "event_kind": e.kind, "location": e.location, "remind_minutes_before": e.remind_minutes_before,
        }
        for e in events.order_by("starts_at")[:20]
    ]  # fmt: skip


# --- Medicines and plain facts ------------------------------------------------------------------------------


def doses_on(subject, day) -> tuple[int, int]:
    """(doses scheduled on `day`, doses marked as taken on `day`)."""
    meds = list(Medication.objects.filter(patient=subject, is_active=True))
    due = {(m.id, t) for m in meds for t in m.scheduled_on(day)}
    if not due:
        return 0, 0
    marked = MedicationDose.objects.filter(medication__in=meds, date=day).values_list("medication_id", "time")
    return len(due), len(due & set(marked))


def _dose_counts(subject, first, last) -> dict:
    due = taken = 0
    day = first
    while day <= last:
        d, t = doses_on(subject, day)
        due, taken = due + d, taken + t
        day += timedelta(days=1)
    return {
        "active": Medication.objects.filter(patient=subject, is_active=True).count(),
        "doses_due": due,
        "doses_marked_taken": taken,
    }


def patient_facts(subject, granted) -> dict:
    """Plain facts for the people a patient shares with: dates and counts, never a judgement or a score.

    Only facts the viewer's scopes already allow them to see are included.
    """
    today = local_today(subject)
    facts = {}
    if sc.VIEW_CHECKINS in granted:
        last = subject.checkins.order_by("-date").values_list("date", flat=True).first()
        facts["last_check_in"] = last
        facts["days_since_check_in"] = (today - last).days if last else None
        facts["urgent_yes_last_7_days"] = subject.checkins.filter(
            date__gte=today - timedelta(days=6), urgent_answered=True
        ).count()
    if sc.VIEW_MEDS in granted:
        due, taken = doses_on(subject, today - timedelta(days=1))
        facts["doses_not_marked_yesterday"] = due - taken
    if sc.VIEW_READINGS in granted:
        facts["last_reading_at"] = subject.readings.values_list("taken_at", flat=True).first()
    return facts


# "Needs a look" filters for clinicians: each is a plain yes/no question about the facts above.
NEEDS_FILTERS = {
    "urgent": lambda f: f.get("urgent_yes_last_7_days", 0) > 0,
    "no_check_in": lambda f: "days_since_check_in" in f and (f["days_since_check_in"] is None or f["days_since_check_in"] >= 2),
    "doses_not_marked": lambda f: f.get("doses_not_marked_yesterday", 0) > 0,
}
