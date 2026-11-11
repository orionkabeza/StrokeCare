"""Owner: Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md

The progress dashboard: plain counts per day. Safety rule: counts only. No percentage, score, streak, target or
colour judgement, and a day with nothing recorded is just an empty day, never a "miss".
"""
from collections import defaultdict
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate

from apps.health.models import PlanTask, TaskLog
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


def phase_row(p) -> dict:
    return {"id": p.id, "name": p.name, "starts_on": p.starts_on, "ends_on": p.ends_on, "care_needed": p.care_needed}
