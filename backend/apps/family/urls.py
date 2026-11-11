"""Owner: Aubin Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md"""
from django.urls import path

from . import views

urlpatterns = [
    path("patients/<patient:patient_ref>/calendar/", views.CalendarView.as_view()),
    path("patients/<patient:patient_ref>/calendar/<uuid:event_id>/", views.CalendarEventView.as_view()),
    path("patients/<patient:patient_ref>/handover/", views.HandoverView.as_view()),
]
