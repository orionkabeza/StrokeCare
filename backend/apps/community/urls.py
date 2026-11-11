"""Owner: Aubin Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md"""
from django.urls import path

from . import views

urlpatterns = [
    path("home-visit-checklist/", views.ChecklistView.as_view()),
    path("patients/<patient:patient_ref>/home-visits/", views.HomeVisitsView.as_view()),
]
