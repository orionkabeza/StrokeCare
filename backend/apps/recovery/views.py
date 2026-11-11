"""Goals, recovery stages, movement log, personal phrases and the progress dashboard.

Owner: Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md
All of it lives under /patients/<me|uuid>/ and goes through the one access function. Scopes:
  * goals and personal phrases: `view_notes` to read, `add_notes` to write (the person's own words)
  * recovery stages: `view_plan` to read, `manage_plan` to write (a verified clinician only)
  * movement log: `view_mobility` / `log_mobility`
  * progress dashboard: `view_summary`
Safety rule: counts and plain words only. Nothing here scores, grades, ranks or sets a target.
"""
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.http import Http404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.care import scopes
from apps.common import limits
from apps.common.access import PatientScopedMixin
from apps.health.services import local_today

from . import services
from .models import CarePhase, CustomPhrase, Goal, MobilityLog


def _only_own_or_self(view, request, obj):
    """The person can change anything on their record. A helper can remove only what they wrote themselves."""
    if not view.access.is_self and obj.entered_by_id != request.user.id:
        raise PermissionDenied("You can change only what you wrote.", code="not_yours")


def _text(data, key, max_len, label):
    value = str(data.get(key, "")).strip()
    if not value:
        raise ValidationError({key: [f"Write {label} first."]})
    if len(value) > max_len:
        raise ValidationError({key: [f"Keep it under {max_len} characters."]})
    return value


# --- Goals ----------------------------------------------------------------------------------------------


class GoalSerializer(serializers.ModelSerializer):
    done = serializers.SerializerMethodField()
    entered_by_role = serializers.SerializerMethodField()

    class Meta:
        model = Goal
        fields = ["id", "text", "target_date", "done", "done_at", "created_at", "entered_by_role"]

    def get_done(self, obj) -> bool:
        return obj.done_at is not None

    def get_entered_by_role(self, obj):
        return obj.entered_by.role if obj.entered_by else None


class GoalsView(PatientScopedMixin, APIView):
    scope_by_method = {"GET": scopes.VIEW_NOTES, "POST": scopes.ADD_NOTES}

    def get(self, request, patient_ref):
        qs = self.access.subject.goals.select_related("entered_by")[:100]
        return Response({"results": GoalSerializer(qs, many=True).data})

    def post(self, request, patient_ref):
        text = _text(request.data, "text", limits.GOAL_MAX_LENGTH, "the goal")
        target = request.data.get("target_date") or None
        if target is not None:
            ser = serializers.DateField()
            try:
                target = ser.to_internal_value(target)
            except serializers.ValidationError:
                raise ValidationError({"target_date": ["Use the format YYYY-MM-DD."]})
        goal = Goal.objects.create(patient=self.access.subject, text=text, target_date=target, entered_by=request.user)
        return Response(GoalSerializer(goal).data, status=status.HTTP_201_CREATED)


class GoalDetailView(PatientScopedMixin, APIView):
    # Anyone who may read a goal may tick it as done (the person, a family member or the clinician in a visit).
    scope_by_method = {"PATCH": scopes.VIEW_NOTES, "DELETE": scopes.ADD_NOTES}

    def _get(self, goal_id):
        goal = Goal.objects.filter(id=goal_id, patient=self.access.subject).first()
        if goal is None:
            raise Http404
        return goal

    def patch(self, request, patient_ref, goal_id):
        goal = self._get(goal_id)
        done = request.data.get("done")
        if not isinstance(done, bool):
            raise ValidationError({"done": ["Send true or false."]})
        goal.done_at = timezone.now() if done else None
        goal.save(update_fields=["done_at"])
        return Response(GoalSerializer(goal).data)

    def delete(self, request, patient_ref, goal_id):
        goal = self._get(goal_id)
        _only_own_or_self(self, request, goal)
        goal.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Recovery stages (written by a verified clinician) --------------------------------------------------


class PhaseSerializer(serializers.ModelSerializer):
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = CarePhase
        fields = ["id", "name", "starts_on", "ends_on", "care_needed", "is_current", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_is_current(self, obj) -> bool:
        today = self.context["today"]
        return obj.starts_on <= today and (obj.ends_on is None or obj.ends_on >= today)

    def validate(self, attrs):
        start = attrs.get("starts_on", getattr(self.instance, "starts_on", None))
        end = attrs.get("ends_on", getattr(self.instance, "ends_on", None))
        if start and end and end < start:
            raise serializers.ValidationError({"ends_on": ["The end cannot be before the start."]})
        return attrs

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Give the stage a name.")
        return value


class PhasesView(PatientScopedMixin, APIView):
    scope_by_method = {"GET": scopes.VIEW_PLAN, "POST": scopes.MANAGE_PLAN}

    def get(self, request, patient_ref):
        subject = self.access.subject
        ctx = {"today": local_today(subject)}
        return Response({"results": PhaseSerializer(subject.care_phases.all(), many=True, context=ctx).data})

    def post(self, request, patient_ref):
        subject = self.access.subject
        ctx = {"today": local_today(subject)}
        ser = PhaseSerializer(data=request.data, context=ctx)
        ser.is_valid(raise_exception=True)
        phase = ser.save(patient=subject, created_by=request.user)
        return Response(PhaseSerializer(phase, context=ctx).data, status=status.HTTP_201_CREATED)


class PhaseDetailView(PatientScopedMixin, APIView):
    scope_by_method = {"PATCH": scopes.MANAGE_PLAN, "DELETE": scopes.MANAGE_PLAN}

    def _get(self, phase_id):
        phase = CarePhase.objects.filter(id=phase_id, patient=self.access.subject).first()
        if phase is None:
            raise Http404
        return phase

    def patch(self, request, patient_ref, phase_id):
        ctx = {"today": local_today(self.access.subject)}
        ser = PhaseSerializer(self._get(phase_id), data=request.data, partial=True, context=ctx)
        ser.is_valid(raise_exception=True)
        return Response(PhaseSerializer(ser.save(), context=ctx).data)

    def delete(self, request, patient_ref, phase_id):
        self._get(phase_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Movement log ----------------------------------------------------------------------------------------


class MobilitySerializer(serializers.ModelSerializer):
    entered_by_role = serializers.SerializerMethodField()
    date = serializers.DateField(required=False)
    minutes = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=limits.MOBILITY_MINUTES_MAX)
    help = serializers.ChoiceField(choices=MobilityLog.Help.choices, required=False, allow_blank=True)
    client_id = serializers.UUIDField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = MobilityLog
        fields = ["id", "date", "kind", "minutes", "help", "note", "client_id", "created_at", "entered_by_role"]
        read_only_fields = ["id", "created_at"]

    def get_entered_by_role(self, obj):
        return obj.entered_by.role if obj.entered_by else None


class MobilityView(PatientScopedMixin, APIView):
    scope_by_method = {"GET": scopes.VIEW_MOBILITY, "POST": scopes.LOG_MOBILITY}

    def get(self, request, patient_ref):
        subject = self.access.subject
        try:
            days = int(request.query_params.get("days", 30))
        except ValueError:
            raise ValidationError({"days": ["Use a whole number from 1 to 90."]})
        if not 1 <= days <= 90:
            raise ValidationError({"days": ["Use a whole number from 1 to 90."]})
        first = local_today(subject) - timedelta(days=days - 1)
        qs = subject.mobility_logs.filter(date__gte=first).select_related("entered_by")[:300]
        return Response({"results": MobilitySerializer(qs, many=True).data})

    def post(self, request, patient_ref):
        subject = self.access.subject
        ser = MobilitySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        today = local_today(subject)
        day = data.get("date") or today
        if day > today:
            raise ValidationError({"date": ["This day has not happened yet."]})
        if day < today - timedelta(days=limits.MOBILITY_BACKFILL_DAYS):
            raise ValidationError({"date": [f"Movement can be added up to {limits.MOBILITY_BACKFILL_DAYS} days late."]})
        client_id = data.get("client_id")
        if client_id:  # a retry from a phone that was offline must not save it twice
            existing = MobilityLog.objects.filter(patient=subject, client_id=client_id).first()
            if existing:
                return Response(MobilitySerializer(existing).data, status=status.HTTP_200_OK)
        try:
            with transaction.atomic():
                entry = ser.save(patient=subject, entered_by=request.user, date=day)
        except IntegrityError:
            # Two syncs from the same phone arrived at the same moment and the other one won. Not an error.
            existing = MobilityLog.objects.filter(patient=subject, client_id=client_id).first() if client_id else None
            if existing is None:
                raise
            return Response(MobilitySerializer(existing).data, status=status.HTTP_200_OK)
        return Response(MobilitySerializer(entry).data, status=status.HTTP_201_CREATED)


class MobilityDetailView(PatientScopedMixin, APIView):
    scope_by_method = {"DELETE": scopes.LOG_MOBILITY}

    def delete(self, request, patient_ref, entry_id):
        entry = MobilityLog.objects.filter(id=entry_id, patient=self.access.subject).first()
        if entry is None:
            raise Http404
        _only_own_or_self(self, request, entry)
        entry.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Personal talk-board phrases -------------------------------------------------------------------------


class PhraseSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomPhrase
        fields = ["id", "text", "icon", "created_at"]
        read_only_fields = ["id", "created_at"]


class PhrasesView(PatientScopedMixin, APIView):
    scope_by_method = {"GET": scopes.VIEW_NOTES, "POST": scopes.ADD_NOTES}

    def get(self, request, patient_ref):
        return Response({"results": PhraseSerializer(self.access.subject.custom_phrases.all(), many=True).data})

    def post(self, request, patient_ref):
        subject = self.access.subject
        text = _text(request.data, "text", limits.PHRASE_MAX_LENGTH, "the phrase")
        icon = str(request.data.get("icon") or "chat-circle")
        if icon not in CustomPhrase.ICONS:
            raise ValidationError({"icon": ["Choose one of the pictures offered."]})
        if subject.custom_phrases.count() >= limits.PHRASES_PER_PATIENT:
            raise ValidationError({"text": [f"There is room for {limits.PHRASES_PER_PATIENT} personal phrases. Remove one first."]})
        phrase = CustomPhrase.objects.create(patient=subject, text=text, icon=icon, entered_by=request.user)
        return Response(PhraseSerializer(phrase).data, status=status.HTTP_201_CREATED)


class PhraseDetailView(PatientScopedMixin, APIView):
    scope_by_method = {"DELETE": scopes.ADD_NOTES}

    def delete(self, request, patient_ref, phrase_id):
        phrase = CustomPhrase.objects.filter(id=phrase_id, patient=self.access.subject).first()
        if phrase is None:
            raise Http404
        _only_own_or_self(self, request, phrase)
        phrase.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Progress dashboard ----------------------------------------------------------------------------------


class ProgressView(PatientScopedMixin, APIView):
    scope_by_method = {"GET": scopes.VIEW_SUMMARY}

    def get(self, request, patient_ref):
        try:
            days = int(request.query_params.get("days", 7))
        except ValueError:
            raise ValidationError({"days": ["Use a whole number from 1 to 30."]})
        if not 1 <= days <= 30:
            raise ValidationError({"days": ["Use a whole number from 1 to 30."]})
        return Response(services.build_progress(self.access.subject, days))
