"""Owner: Erica Rurangwa Sheja (Product Owner)"""
from django.urls import path

from . import views

urlpatterns = [
    path("education/", views.EducationListView.as_view()),
    path("education/<slug:slug>/", views.EducationDetailView.as_view()),
    path("emergency/", views.EmergencyView.as_view()),
    path("talk-board/", views.TalkBoardView.as_view()),
]
