"""Owner: Erica Rurangwa Sheja (Product Owner) · AI-assisted draft, see AI_USE_LOG.md

The content reviewers' workspace: write, translate, and sign off here.
"""
from django.contrib import admin

from .models import EducationItem, EducationTranslation, EmergencyContact, TalkPhrase


class TranslationInline(admin.StackedInline):
    model = EducationTranslation
    extra = 0


@admin.register(EducationItem)
class EducationItemAdmin(admin.ModelAdmin):
    list_display = ("slug", "kind", "audience", "status", "reviewed_by_name", "is_published")
    list_filter = ("status", "kind", "audience", "is_published")
    search_fields = ("slug", "translations__title")
    inlines = [TranslationInline]


@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    list_display = ("label", "region", "kind", "phone", "verified_by_name", "verified_at", "is_active")
    list_filter = ("region", "kind", "is_active")


@admin.register(TalkPhrase)
class TalkPhraseAdmin(admin.ModelAdmin):
    list_display = ("code", "category", "icon", "status", "reviewed_by_name", "is_active", "order")
    list_filter = ("category", "status", "is_active")
