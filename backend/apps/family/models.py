"""Family care calendar and handover notes: who does what, and what the next person needs to know.

Owner: Aubin Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md
Several relatives often share the care. The calendar shows appointments, medicine pick-ups, transport and visits,
each with who is doing it. Handover notes are short messages from one carer to the next.
"""
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class CareEvent(models.Model):
    class Kind(models.TextChoices):
        APPOINTMENT = "appointment", "Appointment"
        THERAPY = "therapy", "Therapy session"
        MEDICINE_PICKUP = "medicine_pickup", "Medicine pick-up"
        TRANSPORT = "transport", "Transport"
        VISIT = "visit", "Visit"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="care_events")
    title = models.CharField(max_length=120)
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.OTHER)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=120, blank=True)
    notes = models.CharField(max_length=500, blank=True)
    remind_minutes_before = models.PositiveIntegerField(
        null=True, blank=True, help_text="Remind the person and their family this many minutes before it starts."
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_care_events"
    )
    done_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["starts_at"]
        indexes = [models.Index(fields=["patient", "starts_at"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ends_at__isnull=True) | models.Q(ends_at__gte=models.F("starts_at")),
                name="care_event_ends_after_start",
            )
        ]


class HandoverNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="handover_notes")
    text = models.CharField(max_length=1000)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-created_at"]
