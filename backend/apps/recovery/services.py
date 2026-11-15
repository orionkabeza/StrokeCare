"""Owner: Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md

The progress dashboard: plain counts per day. Safety rule: counts only. No percentage, score, streak, target or
colour judgement, and a day with nothing recorded is just an empty day, never a "miss".
"""
from collections import defaultdict
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate

from apps.care import scopes
from apps.health.models import Medication, MedicationDose, PlanTask, TaskLog
from apps.health.services import doses_on, local_today

from .models import CarePhase, MobilityLog

DASHBOARD_NOTE = "Counts of what was entered. They are not a score and not medical advice."


def current_phase(subject, today=None):
    today = today or local_today(subject)
    return (
        CarePhase.objects.filter(patient=subject, starts_on__lte=today)
        .exclude(ends_on__lt=today)
        .order_by("-starts_on", "-created_at")
        .first()
    )


def build_progress(subject, days: int) -> dict:
    tz = ZoneInfo(subject.timezone)
    today = local_today(subject)
    first = today - timedelta(days=days - 1)
    start = datetime.combine(first, time.min, tzinfo=tz)
    end = datetime.combine(today + timedelta(days=1), time.min, tzinfo=tz)

    task_created = [
        c.astimezone(tz).date()
        for c in PlanTask.objects.filter(plan__patient=subject, is_active=True).values_list("created_at", flat=True)
    ]  # a day only counts the tasks that existed on it, so days before there was a plan are empty, not "missed"
    ticks = defaultdict(int)
    for row in (
        TaskLog.objects.filter(task__plan__patient=subject, task__is_active=True, date__range=(first, today))
        .values("date")
        .annotate(n=Count("id"))
    ):
        ticks[row["date"]] = row["n"]
    checkins = set(subject.checkins.filter(date__range=(first, today)).values_list("date", flat=True))
    bp = defaultdict(int)
    for row in (
        subject.readings.filter(taken_at__gte=start, taken_at__lt=end)
        .annotate(d=TruncDate("taken_at", tzinfo=tz))
        .values("d")
        .annotate(n=Count("id"))
    ):
        bp[row["d"]] = row["n"]
    mobility = {
        row["date"]: row
        for row in MobilityLog.objects.filter(patient=subject, date__range=(first, today))
        .values("date")
        .annotate(sessions=Count("id"), minutes=Sum("minutes"))
    }

    rows = []
    for i in range(days):
        day = first + timedelta(days=i)
        due, taken = doses_on(subject, day)
        m = mobility.get(day)
        rows.append({
            "date": day,
            "tasks_done": ticks[day], "tasks_total": sum(1 for c in task_created if c <= day),
            "doses_taken": taken, "doses_due": due,
            "checked_in": day in checkins,
            "bp_readings": bp[day],
            "mobility_sessions": m["sessions"] if m else 0,
            "mobility_minutes": (m["minutes"] or 0) if m else 0,
        })  # fmt: skip
    totals = {
        "tasks_done": sum(r["tasks_done"] for r in rows),
        "doses_taken": sum(r["doses_taken"] for r in rows),
        "doses_due": sum(r["doses_due"] for r in rows),
        "check_ins": sum(1 for r in rows if r["checked_in"]),
        "bp_readings": sum(r["bp_readings"] for r in rows),
        "mobility_sessions": sum(r["mobility_sessions"] for r in rows),
        "mobility_minutes": sum(r["mobility_minutes"] for r in rows),
    }
    phase = current_phase(subject, today)
    return {
        "period": {"from": first, "to": today, "days": days, "timezone": subject.timezone},
        "days": rows,
        "totals": totals,
        "current_phase": phase_row(phase) if phase else None,
        "note": DASHBOARD_NOTE,
    }


def _dose_slot(t) -> int:
    """Which row of the week card a dose time sits in: 0 morning, 1 midday, 2 evening."""
    return 0 if t.hour < 11 else 1 if t.hour < 16 else 2


def build_week(subject, granted) -> dict:
    """The last seven days of each metric the viewer may see, for the week cards. Raw readings and counts only:
    no averages, statuses or targets. A metric the viewer was not given is left out entirely."""
    tz = ZoneInfo(subject.timezone)
    today = local_today(subject)
    first = today - timedelta(days=6)
    dates = [first + timedelta(days=i) for i in range(7)]
    out = {"period": {"from": first, "to": today, "timezone": subject.timezone}, "dates": dates}

    if scopes.VIEW_READINGS in granted:
        start = datetime.combine(first, time.min, tzinfo=tz)
        end = datetime.combine(today + timedelta(days=1), time.min, tzinfo=tz)
        out["readings"] = [
            {"taken_at": r.taken_at, "date": r.taken_at.astimezone(tz).date(), "systolic": r.systolic,
             "diastolic": r.diastolic, "pulse": r.pulse}
            for r in subject.readings.filter(taken_at__gte=start, taken_at__lt=end).order_by("taken_at")
        ]  # fmt: skip
    if scopes.VIEW_MEDS in granted:
        meds = list(Medication.objects.filter(patient=subject, is_active=True))
        marked = set(
            MedicationDose.objects.filter(medication__in=meds, date__range=(first, today)).values_list(
                "medication_id", "date", "time"
            )
        )
        doses = []
        for day in dates:
            slots = [{"due": 0, "taken": 0} for _ in range(3)]
            for m in meds:
                for t in m.scheduled_on(day):
                    slot = slots[_dose_slot(t)]
                    slot["due"] += 1
                    slot["taken"] += (m.id, day, t) in marked
            doses.append({"date": day, "slots": slots})
        out["doses"] = doses
    if scopes.VIEW_CHECKINS in granted:
        sent = set(subject.checkins.filter(date__range=(first, today)).values_list("date", flat=True))
        out["checkins"] = [{"date": d, "sent": d in sent} for d in dates]
    if scopes.VIEW_PLAN in granted:
        created = [
            c.astimezone(tz).date()
            for c in PlanTask.objects.filter(plan__patient=subject, is_active=True).values_list("created_at", flat=True)
        ]
        done = defaultdict(int)
        for row in (
            TaskLog.objects.filter(task__plan__patient=subject, task__is_active=True, date__range=(first, today))
            .values("date")
            .annotate(n=Count("id"))
        ):
            done[row["date"]] = row["n"]
        out["tasks"] = [{"date": d, "done": done[d], "in_plan": sum(1 for c in created if c <= d)} for d in dates]
    if scopes.VIEW_MOBILITY in granted:
        minutes = {
            row["date"]: row["minutes"]
            for row in MobilityLog.objects.filter(patient=subject, date__range=(first, today))
            .values("date")
            .annotate(minutes=Sum("minutes"))
        }
        out["mobility"] = [{"date": d, "minutes": minutes.get(d)} for d in dates]
    return out


def phase_row(p) -> dict:
    return {"id": p.id, "name": p.name, "starts_on": p.starts_on, "ends_on": p.ends_on, "care_needed": p.care_needed}
