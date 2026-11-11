"""Emergency guidance shown with the verified contact list.

Owner: Erica Rurangwa Sheja (Product Owner) · AI-assisted draft, see AI_USE_LOG.md
Safety rules: it says "contact local emergency services" and "do not wait for this app". It contains NO phone
number. Numbers come only from verified EmergencyContact rows.
LAUNCH BLOCKER: the French and Kinyarwanda texts are AI drafts. A native speaker with clinical review must
check them before real use (see docs/OPEN_QUESTIONS.md).
"""
from apps.common.locale import pick

from .models import EmergencyContact

GUIDANCE = {
    "en": (
        "If you think you or someone near you may be having a stroke or another emergency, contact your local "
        "emergency services now. Do not wait for this app."
    ),
    "fr": (
        "Si vous pensez que vous, ou une personne près de vous, faites peut-être un AVC ou une autre urgence, "
        "contactez immédiatement les services d'urgence locaux. N'attendez pas cette application."
    ),
    "rw": (
        "Niba utekereza ko wowe cyangwa undi muntu uri hafi yawe ashobora kuba afite stroke cyangwa ikindi kibazo "
        "cyihutirwa, hamagara serivisi z'ubutabazi zo mu gace kawe ubu nonaha. Ntutegereze iyi porogaramu."
    ),
}


def verified_contacts():
    return EmergencyContact.objects.filter(is_active=True, verified_at__isnull=False)


def guidance_payload(locale: str) -> dict:
    text, served = pick(GUIDANCE, locale)
    contacts = [
        {
            "id": c.id, "region": c.region, "label": c.label, "kind": c.kind, "phone": c.phone,
            "hours": c.hours, "verified_by": c.verified_by_name, "last_checked_at": c.last_checked_at,
        }
        for c in verified_contacts()
    ]  # fmt: skip
    return {
        "message": text,
        "locale_served": served,
        "contacts": contacts,
        "contacts_available": bool(contacts),
    }
