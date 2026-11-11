"""Owner: Erica Rurangwa Sheja (Product Owner) · AI-assisted draft, see AI_USE_LOG.md

Language choice with English fallback (decision DEC-009): a missing translation never hides content.
"""
from django.conf import settings


def request_locale(request) -> str:
    """?lang= wins, then the signed-in user's choice, then Accept-Language, then English."""
    wanted = request.query_params.get("lang") if hasattr(request, "query_params") else None
    user = getattr(request, "user", None)
    if not wanted and user is not None and user.is_authenticated:
        wanted = user.preferred_language
    if not wanted:
        header = request.META.get("HTTP_ACCEPT_LANGUAGE", "")
        for part in header.split(","):
            code = part.split(";")[0].strip().lower()[:2]
            if code in settings.SUPPORTED_LOCALES:
                wanted = code
                break
    wanted = (wanted or settings.DEFAULT_LOCALE).lower()[:2]
    return wanted if wanted in settings.SUPPORTED_LOCALES else settings.DEFAULT_LOCALE


def pick(translations: dict, locale: str):
    """Return (text, locale_served). `translations` maps locale -> text; falls back to English."""
    if translations.get(locale):
        return translations[locale], locale
    return translations.get(settings.DEFAULT_LOCALE, ""), settings.DEFAULT_LOCALE
