"""Owner: Aubin Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md"""
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.care import scopes
from apps.common import limits
from apps.common.access import PatientScopedMixin
from apps.common.locale import pick, request_locale
from apps.health.serializers import ReadingSerializer

from .models import CHECKLIST, CHECKLIST_CODES, HomeVisit

BACKFILL_DAYS = 14  # a visit recorded offline can arrive up to two weeks late


class VisitInSerializer(serializers.Serializer):
    client_id = serializers.UUIDField()
    visited_at = serializers.DateTimeField()
    checklist = serializers.DictField(child=serializers.BooleanField(), required=False, default=dict)
    note = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")
    systolic = serializers.IntegerField(required=False)
    diastolic = serializers.IntegerField(required=False)
    pulse = serializers.IntegerField(required=False)

    def validate_visited_at(self, value):
        now = timezone.now()
        if value > now + timedelta(minutes=limits.FUTURE_CLOCK_SKEW_MINUTES):
            raise serializers.ValidationError("A visit cannot be in the future.")
        if value < now - timedelta(days=BACKFILL_DAYS):
            raise serializers.ValidationError(f"Visits can be sent up to {BACKFILL_DAYS} days late.")
        return value

    def validate_checklist(self, value):
        unknown = set(value) - CHECKLIST_CODES
        if unknown:
            raise serializers.ValidationError(f"Unknown checklist items: {sorted(unknown)}")
        return value

    def validate(self, attrs):
        if ("systolic" in attrs) != ("diastolic" in attrs):
            raise serializers.ValidationError({"diastolic": ["Give both numbers, or neither."]})
        return attrs


def _row(v):
    return {
        "id": v.id, "client_id": v.client_id, "visited_at": v.visited_at, "checklist": v.checklist, "note": v.note,
        "chw_name": v.chw.display_name if v.chw else None,
        "reading": {"systolic": v.reading.systolic, "diastolic": v.reading.diastolic} if v.reading else None,
    }  # fmt: skip


class ChecklistView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        locale = request_locale(request)
        return Response({
            "results": [{"code": i["code"], "label": pick(i["label"], locale)[0]} for i in CHECKLIST],
            "status": "draft",
        })  # fmt: skip


class HomeVisitsView(PatientScopedMixin, APIView):
    scope_by_method = {"GET": scopes.VIEW_SUMMARY, "POST": scopes.LOG_VISITS}

    def get(self, request, patient_ref):
        visits = self.access.subject.home_visits.select_related("chw", "reading")[:30]
        return Response({"results": [_row(v) for v in visits]})

    def post(self, request, patient_ref):
        ser = VisitInSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        existing = HomeVisit.objects.filter(client_id=d["client_id"]).select_related("chw", "reading").first()
        if existing:
            if existing.patient_id != self.access.subject.id or existing.chw_id != request.user.id:
                raise serializers.ValidationError({"client_id": ["This visit id is already used."]})
            return Response(_row(existing), status=status.HTTP_200_OK)  # sent twice from the phone: harmless
        try:
            with transaction.atomic():
                reading = None
                if "systolic" in d:
                    rs = ReadingSerializer(data={
                        "systolic": d["systolic"], "diastolic": d["diastolic"], "pulse": d.get("pulse"),
                        "taken_at": d["visited_at"], "context": "other", "note": "Home visit",
                    })  # fmt: skip
                    rs.is_valid(raise_exception=True)
                    reading = rs.save(user=self.access.subject, entered_by=request.user)
                visit = HomeVisit.objects.create(
                    client_id=d["client_id"], patient=self.access.subject, chw=request.user, visited_at=d["visited_at"],
                    checklist=d["checklist"], note=d["note"], reading=reading,
                )  # fmt: skip
        except IntegrityError:
            # The same visit was sent twice at the same moment and the other request won. The whole attempt (including
            # its blood pressure reading) was rolled back, so there is still exactly one visit and one reading.
            existing = HomeVisit.objects.filter(client_id=d["client_id"]).select_related("chw", "reading").first()
            if existing is None or existing.patient_id != self.access.subject.id or existing.chw_id != request.user.id:
                raise
            return Response(_row(existing), status=status.HTTP_200_OK)
        return Response(_row(visit), status=status.HTTP_201_CREATED)
