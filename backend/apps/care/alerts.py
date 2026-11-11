"""Caregiver alerts, worked out from plain facts when the caregiver opens the app.

Owner: Kenneth Master (System architect) · AI-assisted draft, see AI_USE_LOG.md
No background worker is needed: alerts are computed on read and de-duplicated, so opening the app twice never
repeats one. `python manage.py generate_alerts` does the same for every caregiver, ready for a scheduler later.
"""
from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import ConsentKind
from apps.care import scopes as sc
from apps.health.services import local_today, patient_facts

from .models import Alert, CareLink, LinkStatus, Relation

URGENT_LOOKBACK_DAYS = 3
APPOINTMENT_LOOKAHEAD_DAYS = 3  # the longest reminder lead time offered is two days


def refresh_for(member) -> int:
    """Create any new alerts for one caregiver. Returns how many were created."""
    created = 0
    links = CareLink.objects.filter(member=member, relation=Relation.CAREGIVER, status=LinkStatus.ACTIVE).select_related(
        "patient", "member"
    )
    for link in links:
        patient = link.patient
        if not link.member_is_eligible() or not patient.has_active_consent(ConsentKind.HEALTH_DATA):
            continue
        facts = patient_facts(patient, set(link.scopes))
        today = local_today(patient)
        events = []
        if sc.VIEW_CHECKINS in link.scopes:
            since = today - timedelta(days=URGENT_LOOKBACK_DAYS - 1)
            for day in patient.checkins.filter(date__gte=since, urgent_answered=True).values_list("date", flat=True):
                events.append((Alert.Kind.URGENT_ANSWER, f"urgent:{patient.id}:{day}", {"date": str(day)}))
            gap = facts.get("days_since_check_in")
            if gap is not None and gap >= 2:  # people who never checked in are not nagged about it
                events.append((Alert.Kind.NO_CHECK_IN, f"no_check_in:{patient.id}:{today}", {"days": gap}))
        if facts.get("doses_not_marked_yesterday", 0) > 0:
            yday = today - timedelta(days=1)
            events.append((
                Alert.Kind.DOSES_NOT_MARKED, f"doses:{patient.id}:{yday}",
                {"date": str(yday), "count": facts["doses_not_marked_yesterday"]},
            ))  # fmt: skip
        if sc.VIEW_CALENDAR in link.scopes:
            now = timezone.now()
            soon = patient.care_events.filter(
                remind_minutes_before__isnull=False, done_at__isnull=True, starts_at__gt=now,
                starts_at__lte=now + timedelta(days=APPOINTMENT_LOOKAHEAD_DAYS),
            )  # fmt: skip
            for e in soon:
                if now >= e.starts_at - timedelta(minutes=e.remind_minutes_before):
                    events.append((
                        Alert.Kind.APPOINTMENT_SOON, f"appt:{e.id}:{e.remind_minutes_before}",
                        {"title": e.title, "starts_at": e.starts_at.isoformat(), "location": e.location},
                    ))  # fmt: skip
        for kind, key, detail in events:
            _, was_new = Alert.objects.get_or_create(
                recipient=member, dedupe_key=key, defaults={"patient": patient, "kind": kind, "detail": detail}
            )
            created += was_new
    return created
