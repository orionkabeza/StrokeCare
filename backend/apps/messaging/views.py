"""Owner: Kenneth Master (System architect) · AI-assisted draft, see AI_USE_LOG.md"""
from datetime import datetime
from datetime import timezone as dt_timezone

from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import ConsentKind
from apps.care import scopes
from apps.care.models import CareLink, LinkStatus
from apps.common.access import PatientScopedMixin

from .models import Message, ThreadRead
from .services import unread_count

NOTICE = (
    "Messages are not for emergencies and are not watched all the time. "
    "In an emergency, contact local emergency services."
)
PAGE = 50


def _row(m, me):
    sender = m.sender
    return {
        "id": m.id,
        "body": m.body,
        "created_at": m.created_at,
        "mine": sender is not None and sender.id == me.id,
        "sender_name": sender.display_name if sender else None,
        "sender_role": sender.role if sender else None,
    }


class MessagesView(PatientScopedMixin, APIView):
    """GET newest-last page (`?before=<ISO time>` for older); POST {"body": "..."}."""

    scope_by_method = {"GET": scopes.MESSAGE, "POST": scopes.MESSAGE}

    def get(self, request, patient_ref):
        qs = Message.objects.filter(patient=self.access.subject).select_related("sender")
        before = request.query_params.get("before")
        if before:
            try:
                qs = qs.filter(created_at__lt=datetime.fromisoformat(before.replace("Z", "+00:00")))
            except ValueError:
                raise ValidationError({"before": ["Use an ISO date and time."]})
        page = list(qs[: PAGE + 1])
        rows = [_row(m, request.user) for m in reversed(page[:PAGE])]
        return Response({"results": rows, "has_older": len(page) > PAGE, "notice": NOTICE})

    def post(self, request, patient_ref):
        body = str(request.data.get("body", "")).strip()
        if not body:
            raise ValidationError({"body": ["Write a message first."]})
        if len(body) > 2000:
            raise ValidationError({"body": ["Keep it under 2000 characters."]})
        m = Message.objects.create(patient=self.access.subject, sender=request.user, body=body)
        ThreadRead.objects.update_or_create(
            patient=self.access.subject, user=request.user, defaults={"last_read_at": m.created_at}
        )
        return Response(_row(m, request.user), status=status.HTTP_201_CREATED)


class MarkReadView(PatientScopedMixin, APIView):
    scope_by_method = {"POST": scopes.MESSAGE}

    def post(self, request, patient_ref):
        ThreadRead.objects.update_or_create(
            patient=self.access.subject, user=request.user, defaults={"last_read_at": timezone.now()}
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class InboxView(APIView):
    """Every thread I can see: my own (if I keep a record) and those of people who let me message."""

    def get(self, request):
        me = request.user
        patients = []
        if me.is_patient and me.has_active_consent(ConsentKind.HEALTH_DATA):
            patients.append((me, "me"))
        for link in CareLink.objects.filter(member=me, status=LinkStatus.ACTIVE).select_related("patient", "member"):
            if (
                scopes.MESSAGE in link.scopes
                and link.member_is_eligible()
                and link.patient.has_active_consent(ConsentKind.HEALTH_DATA)
            ):
                patients.append((link.patient, str(link.patient_id)))
        rows = []
        for patient, ref in patients:
            last = Message.objects.filter(patient=patient).select_related("sender").first()
            rows.append({
                "patient_ref": ref, "patient_name": patient.display_name,
                "last_message": _row(last, me) if last else None, "unread": unread_count(patient, me),
            })  # fmt: skip
        never = datetime.min.replace(tzinfo=dt_timezone.utc)
        rows.sort(key=lambda r: r["last_message"]["created_at"] if r["last_message"] else never, reverse=True)
        return Response({"results": rows, "notice": NOTICE})
