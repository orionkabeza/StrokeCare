"""Owner: Erica Rurangwa Sheja (Product Owner)

Education and emergency guidance are public on purpose: they hold no personal data, and someone who is
not signed in, or cannot sign in, must still be able to read them.
"""
from django.conf import settings
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.locale import pick, request_locale

from .guidance import guidance_payload
from .models import EducationItem, TalkPhrase, Topic


def _serialise(item, locale, with_body):
    by_locale = {t.locale: t for t in item.translations.all()}
    t = by_locale.get(locale) or by_locale.get(settings.DEFAULT_LOCALE)
    if t is None:
        return None
    topic_name = None
    if item.topic is not None:
        topic_name, _ = pick(item.topic.name, locale)
    data = {
        "slug": item.slug,
        "kind": item.kind,
        "topic": {"slug": item.topic.slug, "name": topic_name} if item.topic is not None else None,
        "audience": item.audience,
        "title": t.title,
        "summary": t.summary,
        "video_url": t.video_url,
        "poster_url": t.poster_url,
        "captions_url": t.captions_url,
        "duration_seconds": t.duration_seconds,
        "locale_served": t.locale,
        "fell_back": t.locale != locale,
        "available_locales": sorted(by_locale),
        "source": {"name": item.source_name, "url": item.source_url},
        "clinical_review": {
            "status": item.status, "reviewed_by": item.reviewed_by_name, "reviewed_at": item.reviewed_at,
            "review_due_at": item.review_due_at,
        },  # fmt: skip
        "translation_review": {"status": t.status, "reviewed_by": t.reviewed_by_name, "reviewed_at": t.reviewed_at},
        "updated_at": item.updated_at,
    }
    if with_body:
        data["body"] = t.body
    return data


class EducationListView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        locale = request_locale(request)
        qs = EducationItem.objects.filter(is_published=True).select_related("topic").prefetch_related("translations")
        for param in ("audience", "kind"):
            if request.query_params.get(param):
                qs = qs.filter(**{param: request.query_params[param]})
        if request.query_params.get("topic"):
            qs = qs.filter(topic__slug=request.query_params["topic"])
        items = [d for d in (_serialise(i, locale, False) for i in qs) if d]
        return Response({"results": items})


class TopicListView(APIView):
    """The nine stroke topics the Learn page groups education by, each with its item counts for the current
    language. Draft topics are included (never hidden for being unreviewed), same as draft education items."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        locale = request_locale(request)
        rows = []
        for topic in Topic.objects.prefetch_related("items"):
            name, served = pick(topic.name, locale)
            published = topic.items.filter(is_published=True)
            rows.append({
                "slug": topic.slug, "name": name, "locale_served": served, "status": topic.status,
                "video_count": published.filter(kind=EducationItem.Kind.VIDEO).count(),
                "text_count": published.exclude(kind=EducationItem.Kind.VIDEO).count(),
            })  # fmt: skip
        return Response({"results": rows})


class EducationDetailView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, slug):
        item = EducationItem.objects.filter(slug=slug, is_published=True).prefetch_related("translations").first()
        data = _serialise(item, request_locale(request), True) if item else None
        if data is None:
            raise NotFound()
        return Response(data)


class EmergencyView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response(guidance_payload(request_locale(request)))


class TalkBoardView(APIView):
    """Public, so it works on a shared family phone before anyone signs in."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        locale = request_locale(request)
        rows = []
        for p in TalkPhrase.objects.filter(is_active=True):
            label, served = pick(p.label, locale)
            rows.append({
                "code": p.code, "category": p.category, "label": label, "locale_served": served,
                "icon": p.icon, "status": p.status,
            })  # fmt: skip
        return Response({"results": rows})
