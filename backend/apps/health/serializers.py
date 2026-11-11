"""Owner: Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md"""
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from apps.common import limits
from apps.common.locale import pick

from .models import BPReading, CheckIn, CheckInQuestion, PlanTask, Reminder, TaskLog


def _not_in_future(value, message):
    if value > timezone.now() + timedelta(minutes=limits.FUTURE_CLOCK_SKEW_MINUTES):
        raise serializers.ValidationError(message)
    return value


class ReadingSerializer(serializers.ModelSerializer):
    taken_at = serializers.DateTimeField(required=False)
    entered_by_role = serializers.SerializerMethodField()
    entered_by_self = serializers.SerializerMethodField()

    class Meta:
        model = BPReading
        fields = ["id", "systolic", "diastolic", "pulse", "taken_at", "context", "note", "entered_by_role",
                  "entered_by_self", "created_at"]  # fmt: skip
        read_only_fields = ["id", "created_at"]

    def get_entered_by_role(self, obj):
        return obj.entered_by.role if obj.entered_by else None

    def get_entered_by_self(self, obj) -> bool:
        return obj.entered_by_id == obj.user_id

    def validate_taken_at(self, value):
        return _not_in_future(value, "A reading cannot be dated in the future.")

    def validate(self, attrs):
        s, d, p = attrs.get("systolic"), attrs.get("diastolic"), attrs.get("pulse")
        errors = {}
        if s is not None and not limits.BP_SYSTOLIC_MIN <= s <= limits.BP_SYSTOLIC_MAX:
            errors["systolic"] = ["Please check this number: it looks like a typing mistake."]
        if d is not None and not limits.BP_DIASTOLIC_MIN <= d <= limits.BP_DIASTOLIC_MAX:
            errors["diastolic"] = ["Please check this number: it looks like a typing mistake."]
        if p is not None and not limits.PULSE_MIN <= p <= limits.PULSE_MAX:
            errors["pulse"] = ["Please check this number: it looks like a typing mistake."]
        if not errors and s is not None and d is not None and s <= d:
            errors["diastolic"] = ["The top number should be larger than the bottom number."]
        if errors:
            raise serializers.ValidationError(errors)
        attrs.setdefault("taken_at", timezone.now())
        return attrs


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanTask
        fields = ["id", "title", "instructions", "order", "is_active"]
        read_only_fields = ["id"]


class PlanPatchSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120, required=False, allow_blank=True)
    notes_for_patient = serializers.CharField(required=False, allow_blank=True)


class TaskLogInSerializer(serializers.Serializer):
    date = serializers.DateField(required=False)
    note = serializers.CharField(max_length=limits.NOTE_MAX_LENGTH, required=False, allow_blank=True, default="")


class TaskLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskLog
        fields = ["id", "date", "note", "created_at"]


# --- Daily check-in ---------------------------------------------------------------------------------


def serialise_question(q: CheckInQuestion, locale: str) -> dict:
    prompt, served = pick(q.prompt, locale)
    return {
        "code": q.code,
        "prompt": prompt,
        "locale_served": served,
        "answer_type": q.answer_type,
        "choices": [
            {"value": c["value"], "label": pick(c.get("label", {}), locale)[0]} for c in (q.choices or [])
        ],
        "urgent_values": q.urgent_values,  # lets the app show urgent guidance the moment it is chosen
        "status": q.status,
        "reviewed_by": q.reviewed_by_name,
        "reviewed_at": q.reviewed_at,
        "source": q.source,
    }


class AnswerInSerializer(serializers.Serializer):
    question = serializers.SlugField()
    value = serializers.JSONField(required=False, allow_null=True)
    skipped = serializers.BooleanField(default=False)


def validate_answer_value(q: CheckInQuestion, value):
    t = q.answer_type
    if t == CheckInQuestion.AnswerType.YES_NO and isinstance(value, bool):
        return value
    if t == CheckInQuestion.AnswerType.SCALE_5 and isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 5:
        return value
    if t == CheckInQuestion.AnswerType.CHOICE and value in [c["value"] for c in (q.choices or [])]:
        return value
    if t == CheckInQuestion.AnswerType.TEXT and isinstance(value, str):
        return value.strip()[: limits.NOTE_MAX_LENGTH]
    raise serializers.ValidationError({"answers": [f"That answer is not valid for question '{q.code}'."]})


class CheckInSubmitSerializer(serializers.Serializer):
    date = serializers.DateField(required=False)
    answers = AnswerInSerializer(many=True, allow_empty=False)

    def validate(self, attrs):
        questions = {q.code: q for q in CheckInQuestion.objects.filter(is_active=True)}
        seen, cleaned = set(), []
        for a in attrs["answers"]:
            q = questions.get(a["question"])
            if q is None:
                raise serializers.ValidationError({"answers": [f"Unknown question: {a['question']}"]})
            if q.code in seen:
                raise serializers.ValidationError({"answers": [f"Question '{q.code}' appears twice."]})
            seen.add(q.code)
            if a["skipped"] or a.get("value") is None:
                cleaned.append((q, None, True))
            else:
                cleaned.append((q, validate_answer_value(q, a["value"]), False))
        attrs["cleaned"] = cleaned
        return attrs


def serialise_checkin(ci: CheckIn) -> dict:
    return {
        "id": ci.id,
        "date": ci.date,
        "submitted_at": ci.submitted_at,
        "urgent_question_answered_yes": ci.urgent_answered,
        "entered_by_role": ci.entered_by.role if ci.entered_by else None,
        "answers": [
            {"question": a.question.code, "value": a.value, "skipped": a.skipped}
            for a in ci.answers.select_related("question")
        ],
    }


# --- Reminders --------------------------------------------------------------------------------------


class ReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reminder
        fields = ["id", "kind", "time_of_day", "days_of_week", "channel", "is_active"]
        read_only_fields = ["id"]

    def validate_days_of_week(self, value):
        if not value or any(d not in range(7) for d in value):
            raise serializers.ValidationError("Use the numbers 0 (Monday) to 6 (Sunday).")
        return sorted(set(value))
