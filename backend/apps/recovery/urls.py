"""Owner: Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md"""
from django.urls import path

from . import views

urlpatterns = [
    path("patients/<patient:patient_ref>/goals/", views.GoalsView.as_view()),
    path("patients/<patient:patient_ref>/goals/<uuid:goal_id>/", views.GoalDetailView.as_view()),
    path("patients/<patient:patient_ref>/phases/", views.PhasesView.as_view()),
    path("patients/<patient:patient_ref>/phases/<uuid:phase_id>/", views.PhaseDetailView.as_view()),
    path("patients/<patient:patient_ref>/mobility/", views.MobilityView.as_view()),
    path("patients/<patient:patient_ref>/mobility/<uuid:entry_id>/", views.MobilityDetailView.as_view()),
    path("patients/<patient:patient_ref>/phrases/", views.PhrasesView.as_view()),
    path("patients/<patient:patient_ref>/phrases/<uuid:phrase_id>/", views.PhraseDetailView.as_view()),
    path("patients/<patient:patient_ref>/progress/", views.ProgressView.as_view()),
]
