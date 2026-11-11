"""Owner: Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md"""
from django.conf import settings
from django.contrib import admin
from django.db import connection
from django.http import FileResponse, JsonResponse
from django.urls import include, path, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def healthz(request):
    """Used by the host to check the app is up and the database answers."""
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
        return JsonResponse({"status": "ok"})
    except Exception:
        return JsonResponse({"status": "database_unreachable"}, status=503)


def spa(request):
    """Every app route (/today, /p/me/checkin, ...) gets the app's index.html; the app's router takes over."""
    index = settings.FRONTEND_DIST / "index.html"
    if not index.exists():
        return JsonResponse({"error": {"code": "no_frontend", "message": "The web app files were not found. Check that frontend/site/index.html exists (or that FRONTEND_DIST points at it)."}}, status=404)
    response = FileResponse(open(index, "rb"), content_type="text/html; charset=utf-8")
    response["Cache-Control"] = "no-cache"
    response["Content-Security-Policy"] = settings.CONTENT_SECURITY_POLICY
    response["Permissions-Policy"] = "microphone=(self), camera=(), geolocation=()"
    return response


api = [
    path("", include("apps.accounts.urls")),
    path("", include("apps.care.urls")),
    path("", include("apps.health.urls")),
    path("", include("apps.content.urls")),
    path("", include("apps.messaging.urls")),
    path("", include("apps.family.urls")),
    path("", include("apps.community.urls")),
    path("", include("apps.recovery.urls")),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema")),
]

urlpatterns = [
    path("healthz", healthz),
    path("api/v1/", include(api)),
    path("admin/", admin.site.urls),
    re_path(r"^(?!api/|admin/|static/|healthz).*$", spa),
]
