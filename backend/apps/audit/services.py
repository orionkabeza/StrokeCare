"""Owner: Kenneth Master (System architect) · AI-assisted draft, see AI_USE_LOG.md"""
from .models import AuditLog


def record(request, action, *, subject=None, actor=None, object_type="", object_id="", **metadata):
    """Write one audit entry. `metadata` must never contain health values or passwords."""
    if actor is None:
        user = getattr(request, "user", None)
        actor = user if user is not None and user.is_authenticated else None
    return AuditLog.objects.create(
        actor=actor,
        subject=subject,
        action=action,
        object_type=object_type,
        object_id=str(object_id) if object_id else "",
        metadata=metadata,
    )
