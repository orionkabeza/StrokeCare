"""Owner: Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md

Everything about a person lives under /patients/<me|uuid>/. `me` is yourself; a uuid is someone who
shared with you through a care link.
"""
from django.urls import path

from . import medicines, views, voice

urlpatterns = [
    path("patients/<patient:patient_ref>/readings/", views.ReadingsView.as_view()),
    path("patients/<patient:patient_ref>/readings/<uuid:reading_id>/", views.ReadingDetailView.as_view()),
    path("patients/<patient:patient_ref>/plan/", views.PlanView.as_view()),
    path("patients/<patient:patient_ref>/plan/tasks/", views.TaskCreateView.as_view()),
    path("patients/<patient:patient_ref>/plan/tasks/<uuid:task_id>/", views.TaskDetailView.as_view()),
    path("patients/<patient:patient_ref>/plan/tasks/<uuid:task_id>/log/", views.TaskLogView.as_view()),
    path("patients/<patient:patient_ref>/checkins/", views.CheckInsView.as_view()),
    path("patients/<patient:patient_ref>/summary/", views.SummaryView.as_view()),
    path("patients/<patient:patient_ref>/medications/", medicines.MedicationsView.as_view()),
    path("patients/<patient:patient_ref>/medications/doses/bulk/", medicines.BulkDoseView.as_view()),
    path("patients/<patient:patient_ref>/medications/<uuid:med_id>/", medicines.MedicationDetailView.as_view()),
    path("patients/<patient:patient_ref>/medications/<uuid:med_id>/doses/", medicines.DoseView.as_view()),
    path("patients/<patient:patient_ref>/visit-questions/", medicines.VisitQuestionsView.as_view()),
    path("patients/<patient:patient_ref>/visit-questions/<uuid:q_id>/", medicines.VisitQuestionDetailView.as_view()),
    path("patients/<patient:patient_ref>/plan/apply-template/", medicines.ApplyTemplateView.as_view()),
    path("patients/<patient:patient_ref>/voice-notes/", voice.VoiceNotesView.as_view()),
    path("patients/<patient:patient_ref>/voice-notes/<uuid:note_id>/", voice.VoiceNoteAudioView.as_view()),
    path("plan-templates/", medicines.PlanTemplatesView.as_view()),
    path("plan-templates/<uuid:template_id>/", medicines.PlanTemplateDetailView.as_view()),
    path("checkin-questions/", views.CheckInQuestionsView.as_view()),
    path("me/reminders/", views.RemindersView.as_view()),
    path("me/reminders/upcoming/", views.UpcomingRemindersView.as_view()),
    path("me/reminders/<uuid:reminder_id>/", views.ReminderDetailView.as_view()),
]
