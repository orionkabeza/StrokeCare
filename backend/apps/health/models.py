"""Health records: blood pressure, recovery plan, daily check-in, reminders.

Owner: Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md
Safety rules enforced here:
  * Blood pressure is stored and returned as numbers. There is no label, colour, band or risk field.
  * A recovery plan is written only by a verified clinician. One plan per patient, one tick per task per day.
  * Check-in questions are data and ship as DRAFT until a named reviewer signs them off.
"""
import uuid

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone

from apps.common import limits


def every_day():
    return [0, 1, 2, 3, 4, 5, 6]  # Monday = 0


class BPReading(models.Model):
    class Context(models.TextChoices):
        RESTING = "resting", "Resting"
        MORNING = "morning", "Morning"
        EVENING = "evening", "Evening"
        AFTER_ACTIVITY = "after_activity", "After activity"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="readings")
    systolic = models.PositiveSmallIntegerField()
    diastolic = models.PositiveSmallIntegerField()
    pulse = models.PositiveSmallIntegerField(null=True, blank=True)
    taken_at = models.DateTimeField()
    context = models.CharField(max_length=16, choices=Context.choices, default=Context.OTHER)
    note = models.CharField(max_length=limits.NOTE_MAX_LENGTH, blank=True)
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-taken_at"]
        indexes = [models.Index(fields=["user", "-taken_at"], name="bp_user_taken_idx")]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(systolic__gte=limits.BP_SYSTOLIC_MIN, systolic__lte=limits.BP_SYSTOLIC_MAX),
                name="bp_systolic_plausible",
            ),
            models.CheckConstraint(
                condition=models.Q(diastolic__gte=limits.BP_DIASTOLIC_MIN, diastolic__lte=limits.BP_DIASTOLIC_MAX),
                name="bp_diastolic_plausible",
            ),
            models.CheckConstraint(condition=models.Q(systolic__gt=models.F("diastolic")), name="bp_top_above_bottom"),
        ]


class RecoveryPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="plan")
    title = models.CharField(max_length=120, blank=True)
    notes_for_patient = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)


class PlanTask(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(RecoveryPlan, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=200)
    instructions = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["order", "created_at"]


class TaskLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(PlanTask, on_delete=models.CASCADE, related_name="logs")
    date = models.DateField()
    note = models.CharField(max_length=limits.NOTE_MAX_LENGTH, blank=True)
    entered_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["task", "date"], name="one_tick_per_task_per_day")]
        indexes = [models.Index(fields=["task", "-date"])]


class CheckInQuestion(models.Model):
    class AnswerType(models.TextChoices):
        YES_NO = "yes_no", "Yes / No"
        SCALE_5 = "scale_5", "Scale 1 to 5"
        CHOICE = "choice", "One of several choices"
        TEXT = "text", "Free text"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft: not clinically reviewed"
        REVIEWED = "reviewed", "Reviewed by a named clinician"

    code = models.SlugField(max_length=40, unique=True)
    prompt = models.JSONField(help_text='{"en": "...", "fr": "...", "rw": "..."}; English is required.')
    answer_type = models.CharField(max_length=10, choices=AnswerType.choices)
    choices = models.JSONField(default=list, blank=True, help_text='For "choice": [{"value": "better", "label": {"en": ".."}}]')
    urgent_values = models.JSONField(
        default=list, blank=True, help_text="Answers that must show urgent guidance straight away, e.g. [true]."
    )
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    source = models.CharField(max_length=300, blank=True)
    reviewed_by_name = models.CharField(max_length=120, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["order", "code"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status="draft")
                | (~models.Q(reviewed_by_name="") & models.Q(reviewed_at__isnull=False)),
                name="reviewed_question_has_reviewer",
            )
        ]

    def __str__(self):
        return self.code


class CheckIn(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="checkins")
    date = models.DateField(help_text="The person's own calendar day.")
    submitted_at = models.DateTimeField(default=timezone.now)
    urgent_answered = models.BooleanField(default=False)
    entered_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["-date"]
        constraints = [models.UniqueConstraint(fields=["user", "date"], name="one_checkin_per_user_per_day")]


class CheckInAnswer(models.Model):
    checkin = models.ForeignKey(CheckIn, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(CheckInQuestion, on_delete=models.PROTECT, related_name="answers")
    value = models.JSONField(null=True, blank=True)
    skipped = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["checkin", "question"], name="one_answer_per_question")]
        indexes = [models.Index(fields=["question", "checkin"])]


class Reminder(models.Model):
    class Kind(models.TextChoices):
        TASKS = "tasks", "Recovery plan tasks"
        BLOOD_PRESSURE = "blood_pressure", "Blood pressure reading"
        CHECKIN = "checkin", "Daily check-in"
        MEDICINES = "medicines", "Medicine doses"
        MOBILITY = "mobility", "Movement"

    class Channel(models.TextChoices):
        IN_APP = "in_app", "In the app"
        # "sms" and "push" arrive later, once a provider is chosen (see docs/OPEN_QUESTIONS.md)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reminders")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    time_of_day = models.TimeField()
    days_of_week = ArrayField(models.PositiveSmallIntegerField(), default=every_day)
    channel = models.CharField(max_length=8, choices=Channel.choices, default=Channel.IN_APP)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["time_of_day"]


# --- Medicines ------------------------------------------------------------------------------------------
# Safety rule: the app never suggests, doses or changes a medicine. A verified clinician writes the list
# exactly as prescribed; the app only reminds and records "taken". A missed dose is shown as a fact, never
# with advice about what to do (that is the clinician's call).


class Medication(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="medications")
    name = models.CharField(max_length=120)
    dose = models.CharField(max_length=120, blank=True, help_text="As written by the clinician, e.g. one tablet.")
    instructions = models.TextField(blank=True)
    times = ArrayField(models.TimeField(), help_text="Times of day the person takes it.")
    days_of_week = ArrayField(models.PositiveSmallIntegerField(), default=every_day)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__isnull=True) | models.Q(end_date__gte=models.F("start_date")),
                name="medication_end_after_start",
            )
        ]

    def scheduled_on(self, day) -> list:
        """The dose times due on `day`, or [] when none are."""
        if not self.is_active or day < self.start_date or (self.end_date and day > self.end_date):
            return []
        return sorted(self.times) if day.weekday() in self.days_of_week else []


class MedicationDose(models.Model):
    """One scheduled dose marked as taken. No row means not marked (yet)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name="doses")
    date = models.DateField()
    time = models.TimeField(help_text="Which scheduled time this was.")
    taken_at = models.DateTimeField(default=timezone.now)
    entered_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["medication", "date", "time"], name="one_mark_per_dose")]
        indexes = [models.Index(fields=["medication", "-date"])]


# --- Questions for the next visit ---------------------------------------------------------------------------


class VisitQuestion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="visit_questions")
    text = models.CharField(max_length=limits.NOTE_MAX_LENGTH)
    entered_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    discussed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["discussed_at", "-created_at"]  # open questions first


# --- Plan templates (a clinician's own reusable task lists) ------------------------------------------------


class PlanTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="plan_templates")
    name = models.CharField(max_length=120)
    tasks = models.JSONField(help_text='[{"title": "...", "instructions": "..."}]')
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["name"]


# --- Voice notes ----------------------------------------------------------------------------------------------
# For people who find typing or reading hard (aphasia, one hand, low literacy). Stored in PostgreSQL itself, so they
# survive on hosts whose disk is wiped on every deploy. Size and length are capped.


class VoiceNote(models.Model):
    class Context(models.TextChoices):
        VISIT = "visit", "For the next visit"
        CHECK_IN = "check_in", "With the daily check-in"
        GENERAL = "general", "General"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="voice_notes")
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    context = models.CharField(max_length=10, choices=Context.choices, default=Context.GENERAL)
    audio = models.BinaryField()
    content_type = models.CharField(max_length=40)
    size_bytes = models.PositiveIntegerField()
    duration_seconds = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["patient", "-created_at"])]
