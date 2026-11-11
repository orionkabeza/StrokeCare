"""Owner: Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md

Every view here reads only `self.access.subject`'s rows (ownership lives in the query), and the access
check has already run. A record id that belongs to someone else is simply "not found".
"""
from datetime import date as date_cls

from django.db import transaction
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import record as audit
from apps.care import scopes
from apps.common.access import PatientScopedMixin, require_self_patient
from apps.common.locale import request_locale
from apps.common.pagination import CappedLimitOffsetPagination
from apps.content.guidance import guidance_payload

from . import services
from .models import CheckInQuestion, PlanTask, RecoveryPlan, Reminder, TaskLog
from .serializers import (
    CheckInSubmitSerializer,
    PlanPatchSerializer,
    ReadingSerializer,
    ReminderSerializer,
    TaskLogInSerializer,
    TaskLogSerializer,
    TaskSerializer,
    serialise_checkin,
    serialise_question,
)


class CheckInPagination(LimitOffsetPagination):
    default_limit = 14
    max_limit = 60


# --- Blood pressure -----------------------------------------------------------------------------------


class ReadingsView(PatientScopedMixin, APIView):
    scope_by_method = {"GET": scopes.VIEW_READINGS, "POST": scopes.LOG_READINGS}
    pagination_class = CappedLimitOffsetPagination

    def get(self, request, patient_ref):
        qs = self.access.subject.readings.select_related("entered_by")  # newest first
        if request.query_params.get("from"):
            qs = qs.filter(taken_at__date__gte=request.query_params["from"])
        if request.query_params.get("to"):
            qs = qs.filter(taken_at__date__lte=request.query_params["to"])
        paginator = ReadingsView.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(ReadingSerializer(page, many=True).data)

    def post(self, request, patient_ref):
        ser = ReadingSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        reading = ser.save(user=self.access.subject, entered_by=request.user)
        return Response(ReadingSerializer(reading).data, status=status.HTTP_201_CREATED)


class ReadingDetailView(PatientScopedMixin, APIView):
    scope_by_method = {"DELETE": scopes.LOG_READINGS}

    def delete(self, request, patient_ref, reading_id):
        reading = self.access.subject.readings.filter(id=reading_id).first()
        if reading is None:
            raise Http404
        if not self.access.is_self and reading.entered_by_id != request.user.id:
            raise PermissionDenied("You can remove only readings you entered yourself.", code="not_yours")
        reading.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Recovery plan --------------------------------------------------------------------------------------


def _survivor_plan_or_404(subject):
    if subject.role != "survivor":
        raise Http404
    return RecoveryPlan.objects.filter(patient=subject).first()


class PlanView(PatientScopedMixin, APIView):
    scope_by_method = {"GET": scopes.VIEW_PLAN, "PATCH": scopes.MANAGE_PLAN}

    def get(self, request, patient_ref):
        subject = self.access.subject
        plan = _survivor_plan_or_404(subject)
        today = services.local_today(subject)
        if plan is None:
            return Response({"has_plan": False, "date": today, "tasks": []})
        ticked = {l.task_id: l for l in TaskLog.objects.filter(task__plan=plan, date=today)}
        tasks = []
        for t in plan.tasks.filter(is_active=True):
            tick = ticked.get(t.id)
            tasks.append({**TaskSerializer(t).data, "done_today": tick is not None, "note_today": tick.note if tick else ""})
        return Response(
            {"has_plan": True, "title": plan.title, "notes_for_patient": plan.notes_for_patient, "date": today,
             "updated_at": plan.updated_at, "tasks": tasks}
        )  # fmt: skip

    def patch(self, request, patient_ref):
        subject = self.access.subject
        if subject.role != "survivor":
            raise ValidationError({"detail": ["Recovery plans are only for stroke survivors."]})
        ser = PlanPatchSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        plan, _ = RecoveryPlan.objects.get_or_create(patient=subject, defaults={"created_by": request.user})
        for field, value in ser.validated_data.items():
            setattr(plan, field, value)
        plan.save()
        audit(request, "plan.updated", subject=subject, object_type="plan", object_id=plan.id)
        return Response({"title": plan.title, "notes_for_patient": plan.notes_for_patient})


class TaskCreateView(PatientScopedMixin, APIView):
    scope_by_method = {"POST": scopes.MANAGE_PLAN}

    def post(self, request, patient_ref):
        subject = self.access.subject
        if subject.role != "survivor":
            raise ValidationError({"detail": ["Recovery plans are only for stroke survivors."]})
        ser = TaskSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        with transaction.atomic():
            plan, _ = RecoveryPlan.objects.get_or_create(patient=subject, defaults={"created_by": request.user})
            task = ser.save(plan=plan, created_by=request.user)
        audit(request, "plan.task_added", subject=subject, object_type="task", object_id=task.id)
        return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)


class TaskDetailView(PatientScopedMixin, APIView):
    scope_by_method = {"PATCH": scopes.MANAGE_PLAN}

    def patch(self, request, patient_ref, task_id):
        task = PlanTask.objects.filter(id=task_id, plan__patient=self.access.subject).first()
        if task is None:
            raise Http404
        ser = TaskSerializer(task, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        audit(request, "plan.task_changed", subject=self.access.subject, object_type="task", object_id=task.id)
        return Response(ser.data)


class TaskLogView(PatientScopedMixin, APIView):
    """Tick a task for a day. Ticking twice is harmless: one tick per task per day."""

    scope_by_method = {"POST": scopes.LOG_TASKS, "DELETE": scopes.LOG_TASKS}

    def _task(self, task_id):
        task = PlanTask.objects.filter(id=task_id, plan__patient=self.access.subject, is_active=True).first()
        if task is None:
            raise Http404
        return task

    def post(self, request, patient_ref, task_id):
        task = self._task(task_id)
        ser = TaskLogInSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        today = services.local_today(self.access.subject)
        date = ser.validated_data.get("date", today)
        if date > today:
            raise ValidationError({"date": ["A task cannot be ticked for a future day."]})
        log, created = TaskLog.objects.get_or_create(
            task=task, date=date, defaults={"note": ser.validated_data["note"], "entered_by": request.user}
        )
        return Response(TaskLogSerializer(log).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def delete(self, request, patient_ref, task_id):
        task = self._task(task_id)
        raw = request.query_params.get("date")
        try:
            date = date_cls.fromisoformat(raw) if raw else services.local_today(self.access.subject)
        except ValueError:
            raise ValidationError({"date": ["Use the format YYYY-MM-DD."]})
        TaskLog.objects.filter(task=task, date=date).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)



# --- Daily check-in -------------------------------------------------------------------------------------


class CheckInQuestionsView(APIView):
    def get(self, request):
        locale = request_locale(request)
        qs = CheckInQuestion.objects.filter(is_active=True)
        return Response({"results": [serialise_question(q, locale) for q in qs]})


class CheckInsView(PatientScopedMixin, APIView):
    scope_by_method = {"GET": scopes.VIEW_CHECKINS, "POST": scopes.LOG_CHECKINS}

    def get(self, request, patient_ref):
        qs = self.access.subject.checkins.select_related("entered_by")
        paginator = CheckInPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response([serialise_checkin(c) for c in page])

    def post(self, request, patient_ref):
        subject = self.access.subject
        ser = CheckInSubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        today = services.local_today(subject)
        date = ser.validated_data.get("date", today)
        if date > today:
            raise ValidationError({"date": ["A check-in cannot be dated in the future."]})
        checkin = services.save_checkin(subject, request.user, date, ser.validated_data["cleaned"])
        body = serialise_checkin(checkin)
        body["emergency_guidance"] = guidance_payload(request_locale(request)) if checkin.urgent_answered else None
        return Response(body, status=status.HTTP_201_CREATED)


# --- Summary --------------------------------------------------------------------------------------------


class SummaryView(PatientScopedMixin, APIView):
    scope_by_method = {"GET": scopes.VIEW_SUMMARY}

    def get(self, request, patient_ref):
        try:
            days = int(request.query_params.get("days", 7))
        except ValueError:
            raise ValidationError({"days": ["Use a whole number from 1 to 30."]})
        if not 1 <= days <= 30:
            raise ValidationError({"days": ["Use a whole number from 1 to 30."]})
        return Response(services.build_summary(self.access.subject, days))


# --- Reminders (the person's own) -------------------------------------------------------------------------


class RemindersView(APIView):
    def get(self, request):
        user = require_self_patient(request)
        return Response({"results": ReminderSerializer(Reminder.objects.filter(user=user), many=True).data})

    def post(self, request):
        user = require_self_patient(request)
        ser = ReminderSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return Response(ReminderSerializer(ser.save(user=user)).data, status=status.HTTP_201_CREATED)


class ReminderDetailView(APIView):
    def _get(self, request, reminder_id):
        user = require_self_patient(request)
        reminder = Reminder.objects.filter(id=reminder_id, user=user).first()
        if reminder is None:
            raise Http404
        return reminder

    def patch(self, request, reminder_id):
        ser = ReminderSerializer(self._get(request, reminder_id), data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        return Response(ReminderSerializer(ser.save()).data)

    def delete(self, request, reminder_id):
        self._get(request, reminder_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UpcomingRemindersView(APIView):
    def get(self, request):
        user = require_self_patient(request)
        return Response({"results": services.upcoming_reminders(user)})
