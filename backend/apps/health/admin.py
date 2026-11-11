"""Owner: Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md

Only the check-in QUESTIONS are managed here, so reviewers can sign them off. Patients' health records are
deliberately NOT registered in the admin: staff do not browse people's blood pressure.
"""
from django.contrib import admin

from .models import CheckInQuestion


@admin.register(CheckInQuestion)
class CheckInQuestionAdmin(admin.ModelAdmin):
    list_display = ("code", "answer_type", "status", "reviewed_by_name", "is_active", "order")
    list_filter = ("status", "answer_type", "is_active")
