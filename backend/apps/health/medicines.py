"""Medicines, questions for the next visit, and clinicians' plan templates.

Owner: Aubin Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md
Safety rules:
  * Only a verified clinician writes the medicine list (scope `manage_meds`). Patients and caregivers can only
    mark a scheduled dose as taken. The app never suggests, changes or explains a dose.
  * "Not marked as taken" is reported as a fact. It is never called "missed" in a way that implies blame,
    and it never comes with advice.
"""
from datetime import date as date_cls
from datetime import timedelta

from django.db import transaction
from django.db.models import Max
from django.http import Http404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import record as audit
from apps.care import scopes
from apps.common import limits
from apps.common.access import PatientScopedMixin

from . import services
from .models import Medication, MedicationDose, PlanTask, PlanTemplate, RecoveryPlan, VisitQuestion

BACKFILL_DAYS = 7  # a dose can be marked up to a week late, not further back


# --- Medicines ------------------------------------------------------------------------------------------


class MedicationSerializer(serializers.ModelSerializer):
    start_date = serializers.DateField(required=False)

    class Meta:
        model = Medication
        fields = ["id", "name", "dose", "instructions", "times", "days_of_week", "start_date", "end_date", "is_active"]
        read_only_fields = ["id"]

    def validate_times(self, value):
        if not value or len(value) > 8:
            raise serializers.ValidationError("Give between one and eight times of day.")
        return sorted(set(value))

    def validate_days_of_week(self, value):
        if not value or any(d not in range(7) for d in value):
            raise serializers.ValidationError("Use the numbers 0 (Monday) to 6 (Sunday).")
        return sorted(set(value))

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError({"end_date": ["The end date cannot be before the start date."]})
        return attrs


def _day_param(request, subject, name="date"):
    raw = request.query_params.get(name)
    today = services.local_today(subject)
    if not raw:
        return today
    try:
        day = date_cls.fromisoformat(str(raw))
    except ValueError:
        raise ValidationError({name: ["Use the format YYYY-MM-DD."]})
    if day > today:
        raise ValidationError({name: ["This day has not happened yet."]})
    return day


class MedicationsView(PatientScopedMixin, APIView):
    scope_by_method = {"GET": scopes.VIEW_MEDS, "POST": scopes.MANAGE_MEDS}

    def get(self, request, patient_ref):
        subject = self.access.subject
        day = _day_param(request, subject)
        qs = subject.medications.all()
        if request.query_params.get("include_inactive") != "1":
            qs = qs.filter(is_active=True)
        marks = {
            (d.medication_id, d.time): d
            for d in MedicationDose.objects.filter(medication__patient=subject, date=day).select_related("entered_by")
        }
        meds, due, taken = [], 0, 0
        for m in qs:
            slots = []
            for t in m.scheduled_on(day):
                mark = marks.get((m.id, t))
                slots.append({
                    "time": t.strftime("%H:%M"), "taken": mark is not None,
                    "taken_at": mark.taken_at if mark else None,
                    "entered_by_role": mark.entered_by.role if mark and mark.entered_by else None,
                })  # fmt: skip
                due += 1
                taken += mark is not None
            meds.append({**MedicationSerializer(m).data, "doses_on_day": slots})
        return Response({"date": day, "medications": meds, "doses_due": due, "doses_marked_taken": taken})

    def post(self, request, patient_ref):
        ser = MedicationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        subject = self.access.subject
        start = ser.validated_data.pop("start_date", None) or services.local_today(subject)
        med = ser.save(patient=subject, created_by=request.user, start_date=start)
        audit(request, "meds.added", subject=subject, object_type="medication", object_id=med.id)
        return Response(MedicationSerializer(med).data, status=status.HTTP_201_CREATED)


class MedicationDetailView(PatientScopedMixin, APIView):
    scope_by_method = {"PATCH": scopes.MANAGE_MEDS}

    def patch(self, request, patient_ref, med_id):
        med = Medication.objects.filter(id=med_id, patient=self.access.subject).first()
        if med is None:
            raise Http404
        ser = MedicationSerializer(med, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        audit(request, "meds.changed", subject=self.access.subject, object_type="medication", object_id=med.id)
        return Response(ser.data)


def check_dose_slot(subject, med, day, time):
    """A dose can be marked only for a day that has happened, not too long ago, and at a scheduled time."""
    today = services.local_today(subject)
    if day > today:
        raise ValidationError({"date": ["This day has not happened yet."]})
    if day < today - timedelta(days=BACKFILL_DAYS):
        raise ValidationError({"date": [f"Doses can be marked up to {BACKFILL_DAYS} days late."]})
    if time not in med.scheduled_on(day):
        raise ValidationError({"time": ["This medicine is not scheduled at that time on that day."]})


class DoseInSerializer(serializers.Serializer):
    date = serializers.DateField(required=False)
    time = serializers.TimeField()


class DoseView(PatientScopedMixin, APIView):
    """Mark a scheduled dose as taken (POST) or undo that mark (DELETE ?date=&time=)."""

    scope_by_method = {"POST": scopes.LOG_MEDS, "DELETE": scopes.LOG_MEDS}

    def _resolve(self, med_id, day, time):
        subject = self.access.subject
        med = Medication.objects.filter(id=med_id, patient=subject).first()
        if med is None:
            raise Http404
        check_dose_slot(subject, med, day, time)
        return med

    def post(self, request, patient_ref, med_id):
        ser = DoseInSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        day = ser.validated_data.get("date") or services.local_today(self.access.subject)
        time = ser.validated_data["time"]
        med = self._resolve(med_id, day, time)
        dose, created = MedicationDose.objects.get_or_create(
            medication=med, date=day, time=time, defaults={"entered_by": request.user}
        )
        body = {"medication": med.id, "date": day, "time": time.strftime("%H:%M"), "taken_at": dose.taken_at}
        return Response(body, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def delete(self, request, patient_ref, med_id):
        ser = DoseInSerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        day = ser.validated_data.get("date") or services.local_today(self.access.subject)
        med = self._resolve(med_id, day, ser.validated_data["time"])
        MedicationDose.objects.filter(medication=med, date=day, time=ser.validated_data["time"]).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Questions for the next visit ---------------------------------------------------------------------------


class VisitQuestionSerializer(serializers.ModelSerializer):
    entered_by_role = serializers.SerializerMethodField()
    discussed = serializers.SerializerMethodField()

    class Meta:
        model = VisitQuestion
        fields = ["id", "text", "created_at", "discussed", "discussed_at", "entered_by_role"]
        read_only_fields = ["id", "created_at", "discussed_at"]

    def get_entered_by_role(self, obj):
        return obj.entered_by.role if obj.entered_by else None

    def get_discussed(self, obj) -> bool:
        return obj.discussed_at is not None


class VisitQuestionsView(PatientScopedMixin, APIView):
    scope_by_method = {"GET": scopes.VIEW_NOTES, "POST": scopes.ADD_NOTES}

    def get(self, request, patient_ref):
        qs = self.access.subject.visit_questions.select_related("entered_by")
        if request.query_params.get("open") == "1":
            qs = qs.filter(discussed_at__isnull=True)
        return Response({"results": VisitQuestionSerializer(qs[:100], many=True).data})

    def post(self, request, patient_ref):
        text = str(request.data.get("text", "")).strip()
        if not text:
            raise ValidationError({"text": ["Write the question first."]})
        if len(text) > limits.NOTE_MAX_LENGTH:
            raise ValidationError({"text": [f"Keep it under {limits.NOTE_MAX_LENGTH} characters."]})
        q = VisitQuestion.objects.create(patient=self.access.subject, text=text, entered_by=request.user)
        return Response(VisitQuestionSerializer(q).data, status=status.HTTP_201_CREATED)


class VisitQuestionDetailView(PatientScopedMixin, APIView):
    # Anyone who may read the questions may tick one off as discussed (the clinician usually does, in the visit).
    scope_by_method = {"PATCH": scopes.VIEW_NOTES, "DELETE": scopes.ADD_NOTES}

    def _get(self, q_id):
        q = VisitQuestion.objects.filter(id=q_id, patient=self.access.subject).first()
        if q is None:
            raise Http404
        return q

    def patch(self, request, patient_ref, q_id):
        q = self._get(q_id)
        discussed = request.data.get("discussed")
        if not isinstance(discussed, bool):
            raise ValidationError({"discussed": ["Send true or false."]})
        q.discussed_at = timezone.now() if discussed else None
        q.save(update_fields=["discussed_at"])
        return Response(VisitQuestionSerializer(q).data)

    def delete(self, request, patient_ref, q_id):
        q = self._get(q_id)
        if not self.access.is_self and q.entered_by_id != request.user.id:
            raise PermissionDenied("You can remove only questions you wrote.", code="not_yours")
        q.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Plan templates -------------------------------------------------------------------------------------------


class TemplateTaskSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    instructions = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="")


class PlanTemplateSerializer(serializers.ModelSerializer):
    tasks = TemplateTaskSerializer(many=True)

    class Meta:
        model = PlanTemplate
        fields = ["id", "name", "tasks", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_tasks(self, value):
        if not 1 <= len(value) <= 30:
            raise serializers.ValidationError("A template holds between 1 and 30 tasks.")
        return value


def _require_verified_clinician(request):
    if not request.user.is_verified_clinician:
        raise PermissionDenied("Only verified clinicians have plan templates.", code="not_a_clinician")


class PlanTemplatesView(APIView):
    def get(self, request):
        _require_verified_clinician(request)
        return Response({"results": PlanTemplateSerializer(request.user.plan_templates.all(), many=True).data})

    def post(self, request):
        _require_verified_clinician(request)
        ser = PlanTemplateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return Response(PlanTemplateSerializer(ser.save(owner=request.user)).data, status=status.HTTP_201_CREATED)


class PlanTemplateDetailView(APIView):
    def _get(self, request, template_id):
        _require_verified_clinician(request)
        tpl = request.user.plan_templates.filter(id=template_id).first()
        if tpl is None:
            raise Http404
        return tpl

    def patch(self, request, template_id):
        ser = PlanTemplateSerializer(self._get(request, template_id), data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        return Response(PlanTemplateSerializer(ser.save()).data)

    def delete(self, request, template_id):
        self._get(request, template_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ApplyTemplateView(PatientScopedMixin, APIView):
    """Copy a template's tasks into this person's plan. The copies are independent of the template."""

    scope_by_method = {"POST": scopes.MANAGE_PLAN}

    def post(self, request, patient_ref):
        subject = self.access.subject
        if subject.role != "survivor":
            raise ValidationError({"detail": ["Recovery plans are only for stroke survivors."]})
        tpl = PlanTemplate.objects.filter(id=request.data.get("template"), owner=request.user).first()
        if tpl is None:
            raise ValidationError({"template": ["Choose one of your own templates."]})
        with transaction.atomic():
            plan, _ = RecoveryPlan.objects.get_or_create(patient=subject, defaults={"created_by": request.user})
            start = (plan.tasks.aggregate(m=Max("order"))["m"] or 0) + 1
            created = [
                PlanTask.objects.create(
                    plan=plan, order=start + i, title=t["title"], instructions=t.get("instructions", ""),
                    created_by=request.user,
                )  # fmt: skip
                for i, t in enumerate(tpl.tasks)
            ]
        audit(request, "plan.template_applied", subject=subject, template=str(tpl.id), tasks=len(created))
        return Response({"added": len(created)}, status=status.HTTP_201_CREATED)


class BulkDoseItemSerializer(serializers.Serializer):
    medication = serializers.UUIDField()
    time = serializers.TimeField()


class BulkDoseInSerializer(serializers.Serializer):
    date = serializers.DateField(required=False)
    doses = BulkDoseItemSerializer(many=True, allow_empty=False, max_length=50)


class BulkDoseView(PatientScopedMixin, APIView):
    """Mark several scheduled doses as taken in one go ("all of this morning's medicines"). All or nothing."""

    scope_by_method = {"POST": scopes.LOG_MEDS}

    @transaction.atomic
    def post(self, request, patient_ref):
        subject = self.access.subject
        ser = BulkDoseInSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        day = ser.validated_data.get("date") or services.local_today(subject)
        meds = {m.id: m for m in Medication.objects.filter(patient=subject)}
        marked = 0
        for item in ser.validated_data["doses"]:
            med = meds.get(item["medication"])
            if med is None:
                raise ValidationError({"doses": ["One of these medicines is not on this person's list."]})
            check_dose_slot(subject, med, day, item["time"])
            _, created = MedicationDose.objects.get_or_create(
                medication=med, date=day, time=item["time"], defaults={"entered_by": request.user}
            )
            marked += created
        return Response({"date": day, "newly_marked": marked, "requested": len(ser.validated_data["doses"])})
