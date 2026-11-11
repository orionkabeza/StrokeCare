"""Links between a patient and the clinicians and caregivers they choose to share with.

Owner: Kenneth Master (System architect) · AI-assisted draft, see AI_USE_LOG.md
Flow: the patient creates an invitation (a short one-time code, stored only as a hash). The clinician
or caregiver enters it while signed in. Either side can end the link at any time.
"""
import hashlib
import secrets
import uuid

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I, easier to read out loud
CODE_LENGTH = 8


def normalise_code(raw: str) -> str:
    return "".join(ch for ch in raw.upper() if ch.isalnum())


def hash_code(raw: str) -> str:
    return hashlib.sha256(normalise_code(raw).encode()).hexdigest()


def new_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


class Relation(models.TextChoices):
    CLINICIAN = "clinician", "Clinician"
    CAREGIVER = "caregiver", "Caregiver"
    CHW = "chw", "Community health worker"


class LinkStatus(models.TextChoices):
    PENDING = "pending", "Waiting to be accepted"
    ACTIVE = "active", "Active"
    REVOKED = "revoked", "Ended"


class CareLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="care_links")
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="patient_links"
    )
    relation = models.CharField(max_length=16, choices=Relation.choices)
    label = models.CharField(max_length=80, blank=True, help_text="Who the invitation is for, set by the patient.")
    scopes = ArrayField(models.CharField(max_length=32), default=list)
    status = models.CharField(max_length=8, choices=LinkStatus.choices, default=LinkStatus.PENDING)
    invite_hash = models.CharField(max_length=64, unique=True, null=True, blank=True)
    invite_expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    activated_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["patient", "member", "relation"],
                condition=models.Q(status="active"),
                name="one_active_link_per_pair",
            ),
            models.CheckConstraint(
                condition=models.Q(status="pending") | models.Q(member__isnull=False),
                name="active_or_ended_link_has_member",
            ),
        ]
        indexes = [models.Index(fields=["member", "status"])]

    def member_is_eligible(self) -> bool:
        """A link only works while the other person is still the right kind of account."""
        m = self.member
        if m is None or not m.is_active or self.status != LinkStatus.ACTIVE:
            return False
        if self.relation == Relation.CLINICIAN:
            return m.is_verified_clinician
        if self.relation == Relation.CHW:
            return m.is_verified_chw
        return m.role == "caregiver"


class Alert(models.Model):
    """An in-app notice for a caregiver. Facts only ("answered Yes", "not marked as taken"), never advice.

    Safety rule: alerts are not an emergency service and are never presented as one.
    """

    class Kind(models.TextChoices):
        URGENT_ANSWER = "urgent_answer", "Answered Yes to the urgent check-in question"
        NO_CHECK_IN = "no_check_in", "No check-in for two days or more"
        DOSES_NOT_MARKED = "doses_not_marked", "Doses not marked as taken yesterday"
        APPOINTMENT_SOON = "appointment_soon", "An appointment is coming up"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="alerts")
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    dedupe_key = models.CharField(max_length=120)
    detail = models.JSONField(default=dict, blank=True, help_text="Dates, counts and the appointment title only.")
    created_at = models.DateTimeField(default=timezone.now)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["recipient", "dedupe_key"], name="one_alert_per_event")]
