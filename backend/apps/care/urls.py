"""Owner: Kenneth Master (System architect) · AI-assisted draft, see AI_USE_LOG.md"""
from django.urls import path

from . import doctor, views

urlpatterns = [
    path("links/", views.LinkListView.as_view()),
    path("links/invite/", views.InviteView.as_view()),
    path("links/redeem/", views.RedeemView.as_view()),
    path("links/<uuid:link_id>/", views.LinkDetailView.as_view()),
    path("patients/", views.MyPatientsView.as_view()),
    path("doctor/overview/", doctor.DoctorOverviewView.as_view()),
    path("me/care-team/", doctor.CareTeamView.as_view()),
    path("alerts/", views.AlertsView.as_view()),
    path("alerts/read-all/", views.AlertReadView.as_view()),
    path("alerts/<uuid:alert_id>/read/", views.AlertReadView.as_view()),
    path("internal/jobs/run/", views.RunJobsView.as_view()),
]
