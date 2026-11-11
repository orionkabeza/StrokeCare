"""Education content and emergency contacts.

Owner: Erica Rurangwa Sheja (Product Owner) · AI-assisted draft, see AI_USE_LOG.md
Safety rules enforced by the database:
  * Nothing can be marked "reviewed" without a reviewer's name and a date.
  * An emergency contact is shown only after someone has verified it and recorded when.
There is NO medical content and NO phone number in the source code or the migrations.
"""
import uuid

from django.db import models
from django.utils import timezone


class ReviewStatus(models.TextChoices):
    DRAFT = "draft", "Draft: not reviewed"
    REVIEWED = "reviewed", "Reviewed"


def _reviewed_needs_signoff(name):
    return models.CheckConstraint(
        condition=models.Q(status="draft") | (~models.Q(reviewed_by_name="") & models.Q(reviewed_at__isnull=False)),
        name=name,
    )


class EducationItem(models.Model):
    class Kind(models.TextChoices):
        ARTICLE = "article", "Article"
        VIDEO = "video", "Video"
        AUDIO = "audio", "Audio"
        ILLUSTRATED = "illustrated", "Picture guide"

    class Audience(models.TextChoices):
        ALL = "all", "Everyone"
        PREVENTION = "prevention", "Prevention users"
        SURVIVOR = "survivor", "Stroke survivors and caregivers"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=80, unique=True)
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.ARTICLE)
    audience = models.CharField(max_length=12, choices=Audience.choices, default=Audience.ALL)
    source_name = models.CharField(max_length=200, help_text="Who the information comes from. Always shown.")
    source_url = models.URLField(blank=True)
    status = models.CharField(max_length=10, choices=ReviewStatus.choices, default=ReviewStatus.DRAFT)
    reviewed_by_name = models.CharField(max_length=120, blank=True, help_text="Clinical reviewer.")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_due_at = models.DateField(null=True, blank=True)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["slug"]
        constraints = [_reviewed_needs_signoff("education_reviewed_has_reviewer")]

    def __str__(self):
        return self.slug


class EducationTranslation(models.Model):
    item = models.ForeignKey(EducationItem, on_delete=models.CASCADE, related_name="translations")
    locale = models.CharField(max_length=2, choices=[("en", "English"), ("rw", "Kinyarwanda"), ("fr", "Français")])
    title = models.CharField(max_length=200)
    summary = models.CharField(max_length=400, blank=True)
    body = models.TextField(blank=True)
    video_url = models.URLField(blank=True)
    status = models.CharField(max_length=10, choices=ReviewStatus.choices, default=ReviewStatus.DRAFT)
    reviewed_by_name = models.CharField(max_length=120, blank=True, help_text="Language reviewer.")
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["item", "locale"], name="one_translation_per_locale"),
            _reviewed_needs_signoff("translation_reviewed_has_reviewer"),
        ]


class EmergencyContact(models.Model):
    class Kind(models.TextChoices):
        AMBULANCE = "ambulance", "Ambulance"
        HOSPITAL = "hospital", "Hospital"
        HELPLINE = "helpline", "Health helpline"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    region = models.CharField(max_length=80, help_text="Country, district or facility area.")
    label = models.CharField(max_length=120)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    phone = models.CharField(max_length=32)
    hours = models.CharField(max_length=80, blank=True, help_text='e.g. "24 hours"')
    verified_by_name = models.CharField(max_length=120, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True, help_text="Empty means NOT shown to anyone.")
    last_checked_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["region", "kind", "label"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(verified_at__isnull=True) | ~models.Q(verified_by_name=""),
                name="verified_contact_names_verifier",
            )
        ]

    def __str__(self):
        return f"{self.label} ({self.region})"


class TalkPhrase(models.Model):
    """A tile on the talk board: tap it and the phone shows the words large and plays them aloud.

    For people who find speaking hard after a stroke (aphasia). Everyday needs only: never medical advice.
    The phone speaks the words with its own text-to-speech voice when it has one for the language.
    """

    class Category(models.TextChoices):
        ANSWERS = "answers", "Quick answers"
        NEEDS = "needs", "I need"
        FEELINGS = "feelings", "I feel"
        PEOPLE = "people", "People"

    code = models.SlugField(max_length=40, unique=True)
    category = models.CharField(max_length=10, choices=Category.choices)
    label = models.JSONField(help_text='{"en": "...", "fr": "...", "rw": "..."}; English is required.')
    icon = models.CharField(max_length=40, blank=True, help_text="A Phosphor icon name, e.g. drop.")
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=10, choices=ReviewStatus.choices, default=ReviewStatus.DRAFT)
    reviewed_by_name = models.CharField(max_length=120, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["category", "order"]
        constraints = [_reviewed_needs_signoff("talk_phrase_reviewed_has_reviewer")]

    def __str__(self):
        return self.code
