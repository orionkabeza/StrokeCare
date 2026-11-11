"""Owner: Kenneth Master (System architect) · AI-assisted draft, see AI_USE_LOG.md"""
from .models import Message, ThreadRead


def unread_count(patient, user) -> int:
    marker = ThreadRead.objects.filter(patient=patient, user=user).values_list("last_read_at", flat=True).first()
    qs = Message.objects.filter(patient=patient).exclude(sender=user)
    return qs.filter(created_at__gt=marker).count() if marker else qs.count()
