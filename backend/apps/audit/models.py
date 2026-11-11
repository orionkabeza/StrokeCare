"""Append-only audit log.

Owner: Kenneth Master (System architect) · AI-assisted draft, see AI_USE_LOG.md
Safety rule: every time someone other than the patient touches a patient's data, it is recorded.
We store the minimum: who, whose data, what kind of action, when. No health values, no IP address.
Note: the application cannot edit or delete rows. For production, also revoke UPDATE/DELETE on this
table from the application's database role (see docs/DEPLOYMENT.md).
"""
from django.conf import settings
from django.db import models


class AppendOnlyQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise RuntimeError("Audit log entries are append-only.")

    def delete(self):
        raise RuntimeError("Audit log entries are append-only.")


class AuditLog(models.Model):
    at = models.DateTimeField(auto_now_add=True, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    subject = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_entries"
    )
    action = models.CharField(max_length=64, db_index=True)
    object_type = models.CharField(max_length=64, blank=True)
    object_id = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        ordering = ["-at"]
        indexes = [models.Index(fields=["subject", "-at"])]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise RuntimeError("Audit log entries are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Audit log entries are append-only.")

    def __str__(self):
        return f"{self.at:%Y-%m-%d %H:%M} {self.action}"
