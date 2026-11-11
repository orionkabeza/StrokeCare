"""Owner: Kenneth Master (System architect) · AI-assisted draft, see AI_USE_LOG.md"""
from django.urls import path

from . import views

urlpatterns = [
    path("inbox/", views.InboxView.as_view()),
    path("patients/<patient:patient_ref>/messages/", views.MessagesView.as_view()),
    path("patients/<patient:patient_ref>/messages/read/", views.MarkReadView.as_view()),
]
