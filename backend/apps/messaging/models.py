"""The care-team conversation: one thread per patient, shared with the people they chose.

Owner: Kenneth Master (System architect) · AI-assisted draft, see AI_USE_LOG.md
Safety rule: messaging is not for emergencies and is not watched around the clock. Every thread response
carries that notice, and the app shows it above the message box.
"""
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="thread_messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["patient", "-created_at"])]


class ThreadRead(models.Model):
    """When each person last read a patient's thread, for unread counts."""

    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="thread_reads")
    last_read_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["patient", "user"], name="one_read_marker_per_thread")]
