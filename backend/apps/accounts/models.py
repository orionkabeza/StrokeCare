"""Accounts, consent and accessibility preferences.

Owner: Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md
Safety rules:
  * Anyone can sign up as a prevention user, survivor or caregiver. Clinician, community health worker and admin
    accounts are created by an administrator, and a professional can act only after `professional_verified_at` is set.
  * Health data is processed only while a current-version `health_data` consent is active.
"""
import uuid

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils.timezone import now


class Role(models.TextChoices):
    PREVENTION = "prevention", "Prevention user"
    SURVIVOR = "survivor", "Stroke survivor"
    CAREGIVER = "caregiver", "Caregiver"
    CLINICIAN = "clinician", "Clinician"
    CHW = "chw", "Community health worker"
    ADMIN = "admin", "Administrator / content reviewer"


SELF_REGISTER_ROLES = (Role.PREVENTION, Role.SURVIVOR, Role.CAREGIVER)
PATIENT_ROLES = (Role.PREVENTION, Role.SURVIVOR)


class Language(models.TextChoices):
    EN = "en", "English"
    RW = "rw", "Kinyarwanda"
    FR = "fr", "Français"


class ConsentKind(models.TextChoices):
    PRIVACY_NOTICE = "privacy_notice", "Privacy notice"
    HEALTH_DATA = "health_data", "Processing of my health data"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _make(self, email, password, **extra):
        if not email:
            raise ValueError("An email address is required.")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._make(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.update(is_staff=True, is_superuser=True, role=Role.ADMIN)
        return self._make(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=120)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.PREVENTION)
    preferred_language = models.CharField(max_length=2, choices=Language.choices, default=Language.EN)
    timezone = models.CharField(max_length=64, default="Africa/Kigali")
    professional_verified_at = models.DateTimeField(null=True, blank=True)
    professional_ref = models.CharField(
        max_length=120, blank=True, help_text="Licence or registration reference checked by an administrator."
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now, editable=False)

    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["display_name"]

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(email=models.functions.Lower("email")), name="user_email_is_lowercase"
            )
        ]

    def __str__(self):
        return f"{self.display_name} <{self.email}>"

    @property
    def is_patient(self) -> bool:
        return self.role in PATIENT_ROLES

    @property
    def is_verified_clinician(self) -> bool:
        return self.role == Role.CLINICIAN and self.professional_verified_at is not None

    @property
    def is_verified_chw(self) -> bool:
        return self.role == Role.CHW and self.professional_verified_at is not None

    @property
    def is_verified_professional(self) -> bool:
        return self.is_verified_clinician or self.is_verified_chw

    def has_active_consent(self, kind: str) -> bool:
        return self.consents.filter(
            kind=kind, version=settings.CONSENT_VERSIONS[kind], revoked_at__isnull=True
        ).exists()

    def required_consents(self) -> list[str]:
        kinds = [ConsentKind.PRIVACY_NOTICE]
        if self.is_patient:
            kinds.append(ConsentKind.HEALTH_DATA)
        return kinds


class Consent(models.Model):
    """One row per grant. Revoking stamps `revoked_at`; the history stays."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="consents")
    kind = models.CharField(max_length=24, choices=ConsentKind.choices)
    version = models.CharField(max_length=32)
    granted_at = models.DateTimeField(default=now)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-granted_at"]
        indexes = [models.Index(fields=["user", "kind"])]


class AccessibilityPreference(models.Model):
    """Follows the person across devices. Every flag defaults to off, so nothing changes until chosen."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="accessibility")
    text_scale = models.PositiveSmallIntegerField(
        default=100, choices=[(100, "Normal"), (125, "Large"), (150, "Larger"), (200, "Largest")]
    )
    theme = models.CharField(
        max_length=8, default="system", choices=[("system", "Follow the phone"), ("light", "Light"), ("dark", "Dark")]
    )
    high_contrast = models.BooleanField(default=False)
    easy_read_font = models.BooleanField(default=False, help_text="Atkinson Hyperlegible: letters harder to mix up.")
    reduce_motion = models.BooleanField(default=False)
    audio_first = models.BooleanField(default=False, help_text="Offer to read every screen aloud.")
    one_question_at_a_time = models.BooleanField(default=False, help_text="Aphasia-friendly check-in.")
    one_handed_layout = models.BooleanField(default=False, help_text="Controls sit within thumb reach.")
    low_data_mode = models.BooleanField(default=False, help_text="Text only; no video or large images.")
    updated_at = models.DateTimeField(auto_now=True)
