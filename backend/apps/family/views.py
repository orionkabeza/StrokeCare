"""Owner: Aubin Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md"""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.http import Http404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.care import scopes
from apps.care.models import CareLink, LinkStatus
from apps.common.access import PatientScopedMixin
from apps.health.services import local_today

from .models import CareEvent, HandoverNote

MAX_RANGE_DAYS = 92


def care_team(patient) -> list[dict]:
    """The patient plus everyone actively linked to them: the people an event can be assigned to."""
    team = [{"id": patient.id, "display_name": patient.display_name, "relation": "patient"}]
    for link in CareLink.objects.filter(patient=patient, status=LinkStatus.ACTIVE).select_related("member"):
        if link.member_is_eligible():
            team.append({"id": link.member_id, "display_name": link.member.display_name, "relation": link.relation})
    return team


REMIND_CHOICES = [15, 30, 60, 120, 1440, 2880]  # minutes before: 15 min, 30 min, 1 h, 2 h, 1 day, 2 days


class CareEventSerializer(serializers.ModelSerializer):
    assigned_to = serializers.UUIDField(source="assigned_to_id", required=False, allow_null=True)
    assigned_to_name = serializers.SerializerMethodField()
    done = serializers.BooleanField(required=False, write_only=True)
    remind_minutes_before = serializers.ChoiceField(choices=REMIND_CHOICES, required=False, allow_null=True)
    is_done = serializers.SerializerMethodField()

    class Meta:
        model = CareEvent
        fields = ["id", "title", "kind", "starts_at", "ends_at", "location", "notes", "remind_minutes_before", "assigned_to",
                  "assigned_to_name",
                  "done", "is_done", "done_at", "created_at"]  # fmt: skip
        read_only_fields = ["id", "done_at", "created_at"]

    def get_assigned_to_name(self, obj):
        return obj.assigned_to.display_name if obj.assigned_to_id else None

    def get_is_done(self, obj) -> bool:
        return obj.done_at is not None

    def validate(self, attrs):
        start = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        end = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        if start and end and end < start:
            raise serializers.ValidationError({"ends_at": ["The end cannot be before the start."]})
        assignee = attrs.get("assigned_to_id")
        if assignee and assignee not in {m["id"] for m in self.context["team"]}:
            raise serializers.ValidationError({"assigned_to": ["Choose someone from this person's care team."]})
        return attrs

    def save(self, **kwargs):
        done = self.validated_data.pop("done", None)
        if done is not None:
            kwargs["done_at"] = timezone.now() if done else None
        return super().save(**kwargs)


def _range(request, subject):
    tz = ZoneInfo(subject.timezone)
    today = local_today(subject)
    try:
        start = date.fromisoformat(request.query_params.get("from") or (today - timedelta(days=1)).isoformat())
        end = date.fromisoformat(request.query_params.get("to") or (today + timedelta(days=30)).isoformat())
    except ValueError:
        raise ValidationError({"from": ["Use the format YYYY-MM-DD."]})
    if end < start or (end - start).days > MAX_RANGE_DAYS:
        raise ValidationError({"to": [f"Choose a range of up to {MAX_RANGE_DAYS} days."]})
    return datetime.combine(start, time.min, tzinfo=tz), datetime.combine(end + timedelta(days=1), time.min, tzinfo=tz)


class CalendarView(PatientScopedMixin, APIView):
    scope_by_method = {"GET": scopes.VIEW_CALENDAR, "POST": scopes.EDIT_CALENDAR}

    def get(self, request, patient_ref):
        subject = self.access.subject
        start, end = _range(request, subject)
        qs = subject.care_events.filter(starts_at__gte=start, starts_at__lt=end).select_related("assigned_to")
        return Response({"results": CareEventSerializer(qs, many=True).data, "team": care_team(subject)})

    def post(self, request, patient_ref):
        subject = self.access.subject
        ser = CareEventSerializer(data=request.data, context={"team": care_team(subject)})
        ser.is_valid(raise_exception=True)
        event = ser.save(patient=subject, created_by=request.user)
        return Response(CareEventSerializer(event).data, status=status.HTTP_201_CREATED)


class CalendarEventView(PatientScopedMixin, APIView):
    scope_by_method = {"PATCH": scopes.EDIT_CALENDAR, "DELETE": scopes.EDIT_CALENDAR}

    def _get(self, event_id):
        event = CareEvent.objects.filter(id=event_id, patient=self.access.subject).first()
        if event is None:
            raise Http404
        return event

    def patch(self, request, patient_ref, event_id):
        ser = CareEventSerializer(
            self._get(event_id), data=request.data, partial=True, context={"team": care_team(self.access.subject)}
        )
        ser.is_valid(raise_exception=True)
        return Response(CareEventSerializer(ser.save()).data)

    def delete(self, request, patient_ref, event_id):
        self._get(event_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class HandoverView(PatientScopedMixin, APIView):
    scope_by_method = {"GET": scopes.VIEW_CALENDAR, "POST": scopes.EDIT_CALENDAR}

    def get(self, request, patient_ref):
        notes = self.access.subject.handover_notes.select_related("created_by")[:30]
        return Response({"results": [
            {"id": n.id, "text": n.text, "created_at": n.created_at,
             "author_name": n.created_by.display_name if n.created_by else None,
             "author_role": n.created_by.role if n.created_by else None}
            for n in notes
        ]})  # fmt: skip

    def post(self, request, patient_ref):
        text = str(request.data.get("text", "")).strip()
        if not text or len(text) > 1000:
            raise ValidationError({"text": ["Write a note of up to 1000 characters."]})
        n = HandoverNote.objects.create(patient=self.access.subject, text=text, created_by=request.user)
        return Response({"id": n.id, "text": n.text, "created_at": n.created_at}, status=status.HTTP_201_CREATED)
