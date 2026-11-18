"""Owner: Aubin Axel Mfura (Backend and database)"""
from django.urls import path

from . import views

urlpatterns = [
    path("patients/<patient:patient_ref>/calendar/", views.CalendarView.as_view()),
    path("patients/<patient:patient_ref>/calendar/<uuid:event_id>/", views.CalendarEventView.as_view()),
    path("patients/<patient:patient_ref>/handover/", views.HandoverView.as_view()),
]
