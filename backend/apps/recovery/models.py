"""Personal recovery: goals in the person's own words, recovery stages set by a clinician, a movement log and
personal talk-board phrases.

Owner: Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md
Safety rules enforced here:
  * No score, grade, percentage, streak, target or "improvement" field exists on any of these models. The app
    records what people entered and counts it; it never judges it.
  * A recovery stage (CarePhase) is written by a verified clinician in their own words. The app ships no medical
    definition of a stage, because that would be clinical content that no clinician has reviewed.
  * Goals and personal phrases are the person's own words, not medical advice.
"""
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common import limits


class Goal(models.Model):
    """Something the person (or their family, for them) wants to be able to do. Plain words, optional date."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="goals")
    text = models.CharField(max_length=limits.GOAL_MAX_LENGTH)
    target_date = models.DateField(null=True, blank=True, help_text="Optional. A wish, not a deadline.")
    done_at = models.DateTimeField(null=True, blank=True)
    entered_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["done_at", "created_at"]


class CarePhase(models.Model):
    """A stage of this person's recovery, named by their clinician, with the dates it covers."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="care_phases")
    name = models.CharField(max_length=limits.PHASE_NAME_MAX_LENGTH)
    starts_on = models.DateField()
    ends_on = models.DateField(null=True, blank=True)
    care_needed = models.TextField(blank=True, max_length=limits.PHASE_CARE_MAX_LENGTH, help_text="What care and help this stage needs, in the clinician's words.")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["starts_on", "created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ends_on__isnull=True) | models.Q(ends_on__gte=models.F("starts_on")),
                name="care_phase_end_after_start",
            )
        ]


class MobilityLog(models.Model):
    """One entry in the movement log. Counts and plain words only: there is no rating and no target."""

    class Kind(models.TextChoices):
        WALKING = "walking", "Walking"
        STANDING = "standing", "Standing up"
        STRETCHING = "stretching", "Stretching or exercises"
        WHEELCHAIR = "wheelchair", "Wheelchair"
        OTHER = "other", "Other"

    class Help(models.TextChoices):
        ALONE = "alone", "On my own"
        WITH_AID = "with_aid", "With a stick, frame or other aid"
        WITH_PERSON = "with_person", "With another person's help"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mobility_logs")
    date = models.DateField()
    kind = models.CharField(max_length=12, choices=Kind.choices)
    minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    help = models.CharField(max_length=12, choices=Help.choices, blank=True)
    note = models.CharField(max_length=limits.NOTE_MAX_LENGTH, blank=True)
    entered_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    client_id = models.UUIDField(null=True, blank=True, help_text="Set by the phone so a retry never saves it twice.")
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-date", "-created_at"]
        indexes = [models.Index(fields=["patient", "-date"])]
        constraints = [
            models.UniqueConstraint(
                fields=["patient", "client_id"], condition=models.Q(client_id__isnull=False), name="one_mobility_per_client_id"
            ),
            models.CheckConstraint(
                condition=models.Q(minutes__isnull=True) | models.Q(minutes__lte=limits.MOBILITY_MINUTES_MAX),
                name="mobility_minutes_plausible",
            ),
        ]


class CustomPhrase(models.Model):
    """A phrase the person, or their family, added to the talk board for them, in any language."""

    ICONS = (
        "chat-circle", "check", "x", "hourglass", "question", "hand-heart", "drop", "fork-knife", "toilet", "bed",
        "hand-waving", "hand-palm", "moon", "thermometer-cold", "thermometer-hot", "smiley-sad", "users-three",
        "phone-call",
    )  # fmt: skip

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="custom_phrases")
    text = models.CharField(max_length=limits.PHRASE_MAX_LENGTH)
    icon = models.CharField(max_length=24, default="chat-circle")
    entered_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["created_at"]
