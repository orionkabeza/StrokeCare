"""Owner: Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md

Administrators verify clinicians here. A clinician account has no power until it is verified.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone

from .models import Consent, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("email", "display_name", "role", "professional_verified_at", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("email", "display_name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("display_name", "role", "preferred_language", "timezone")}),
        ("Professional verification", {"fields": ("professional_ref", "professional_verified_at")}),
        ("Access", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "display_name", "role", "password1", "password2")}),
    )
    actions = ["mark_verified"]

    @admin.action(description="Mark selected clinicians / community health workers as verified professionals")
    def mark_verified(self, request, queryset):
        queryset.filter(role__in=["clinician", "chw"], professional_verified_at__isnull=True).update(
            professional_verified_at=timezone.now()
        )


@admin.register(Consent)
class ConsentAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "version", "granted_at", "revoked_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
