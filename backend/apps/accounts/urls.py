"""Owner: Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    path("auth/register/", views.RegisterView.as_view()),
    path("auth/login/", views.LoginView.as_view()),
    path("auth/refresh/", TokenRefreshView.as_view()),
    path("auth/logout/", views.LogoutView.as_view()),
    path("me/", views.MeView.as_view()),
    path("me/consents/", views.ConsentView.as_view()),
    path("me/accessibility/", views.AccessibilityView.as_view()),
    path("me/export/", views.ExportView.as_view()),
]
