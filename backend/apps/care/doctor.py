"""The doctor's home page and the person's "my care team" page.

Owner: Kenneth Master (System architect) · AI-assisted draft, see AI_USE_LOG.md
Safety rules:
  * The doctor's overview is plain facts and counts the person entered. There is no risk score and no ranking: the
    people who need a look are listed alphabetically, never by "severity".
  * It only ever includes people with an active link, a consenting patient and the matching scope.
  * "My care team" shows the person who is allowed to see their record, so they always know who that is.
"""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import ConsentKind, Role
from apps.common.access import require_self_patient
from apps.health.services import NEEDS_FILTERS, patient_facts
from apps.messaging.services import unread_count
from apps.recovery.services import current_phase, phase_row

from . import scopes as sc
from .models import CareLink, LinkStatus

NOTE = "Facts the people you care for entered. There is no risk score and no ranking, and the list is in name order."
UPCOMING_DAYS = 7


def _event_row(event, patient):
    return {
        "event_id": event.id, "patient_id": patient.id, "patient_name": patient.display_name, "title": event.title,
        "kind": event.kind, "starts_at": event.starts_at, "location": event.location,
    }  # fmt: skip


class DoctorOverviewView(APIView):
    """Today at a glance for a verified clinician: who may need a look, today's appointments, unread messages."""

    def get(self, request):
        user = request.user
        if user.role != Role.CLINICIAN:
            raise PermissionDenied("This page is for clinicians.", code="clinician_only")
        tz = ZoneInfo(user.timezone)
        today = timezone.now().astimezone(tz).date()
        day_start = datetime.combine(today, time.min, tzinfo=tz)
        day_end = day_start + timedelta(days=1)
        week_end = day_start + timedelta(days=UPCOMING_DAYS + 1)

        links = (
            CareLink.objects.filter(member=user, status=LinkStatus.ACTIVE)
            .select_related("patient", "member")
            .order_by("patient__display_name")
        )
        counts = {"urgent": 0, "no_check_in": 0, "doses_not_marked": 0, "unread_messages": 0}
        needs, appointments_today, appointments_next = [], [], []
        total = 0
        for link in links:
            patient = link.patient
            if not (link.member_is_eligible() and patient.has_active_consent(ConsentKind.HEALTH_DATA)):
                continue
            total += 1
            facts = patient_facts(patient, set(link.scopes))
            reasons = [name for name, test in NEEDS_FILTERS.items() if test(facts)]
            unread = unread_count(patient, user) if sc.MESSAGE in link.scopes else 0
            if unread:
                reasons.append("unread_messages")
            for reason in reasons:
                counts[reason] += 1
            if reasons:
                needs.append({"patient_id": patient.id, "display_name": patient.display_name, "reasons": reasons})
            if sc.VIEW_CALENDAR in link.scopes:
                events = patient.care_events.filter(
                    starts_at__gte=day_start, starts_at__lt=week_end, done_at__isnull=True
                ).order_by("starts_at")
                for event in events:
                    (appointments_today if event.starts_at < day_end else appointments_next).append(_event_row(event, patient))
        appointments_today.sort(key=lambda e: e["starts_at"])
        appointments_next.sort(key=lambda e: e["starts_at"])
        return Response({
            "display_name": user.display_name,
            "date": today,
            "patients_total": total,
            "counts": counts,
            "needs_a_look": needs,
            "appointments_today": appointments_today,
            "appointments_next_days": appointments_next,
            "note": NOTE,
        })  # fmt: skip


class CareTeamView(APIView):
    """For the person themselves: who is on my care team, my current stage and my next appointment."""

    def get(self, request):
        user = require_self_patient(request)
        team = []
        for link in CareLink.objects.filter(patient=user, status=LinkStatus.ACTIVE).select_related("member"):
            if link.member_is_eligible():
                team.append({
                    "link_id": link.id, "member_id": link.member_id, "display_name": link.member.display_name,
                    "relation": link.relation, "since": link.activated_at,
                })  # fmt: skip
        team.sort(key=lambda m: (m["relation"], m["display_name"]))
        phase = current_phase(user)
        nxt = user.care_events.filter(starts_at__gte=timezone.now(), done_at__isnull=True).order_by("starts_at").first()
        return Response({
            "team": team,
            "current_phase": phase_row(phase) if phase else None,
            "next_appointment": (
                {"event_id": nxt.id, "title": nxt.title, "kind": nxt.kind, "starts_at": nxt.starts_at, "location": nxt.location}
                if nxt else None
            ),
        })  # fmt: skip
