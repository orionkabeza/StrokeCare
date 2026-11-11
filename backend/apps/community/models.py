"""Home visits by community health workers (CHWs).

Owner: Aubin Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md
A visit is recorded on the CHW's phone, often without signal, and sent later. `client_id` is made on the phone,
so sending the same visit twice never creates two visits.
Safety rule: the checklist records what the CHW did. It asks for no diagnosis and gives no advice.
"""
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

# Draft activity checklist: what the CHW did during the visit. Needs clinical review before real use.
CHECKLIST = [
    {"code": "bp_reading", "label": {
        "en": "Took a blood pressure reading", "fr": "Prise de la tension artérielle",
        "rw": "Napimye umuvuduko w'amaraso"}},
    {"code": "medicines_reviewed", "label": {
        "en": "Went through the medicine list together", "fr": "Revu ensemble la liste des médicaments",
        "rw": "Twarebeye hamwe urutonde rw'imiti"}},
    {"code": "plan_reviewed", "label": {
        "en": "Went through the recovery plan", "fr": "Revu le plan de rétablissement",
        "rw": "Twarebeye hamwe gahunda yo gukira"}},
    {"code": "check_in_done", "label": {
        "en": "Asked the daily check-in questions", "fr": "Posé les questions du suivi quotidien",
        "rw": "Nabajije ibibazo byo gukurikirana bya buri munsi"}},
    {"code": "caregiver_spoken", "label": {
        "en": "Spoke with the caregiver", "fr": "Parlé avec l'aidant",
        "rw": "Navuganye n'umwitaho"}},
    {"code": "health_centre_advised", "label": {
        "en": "Advised a visit to the health centre", "fr": "Conseillé une visite au centre de santé",
        "rw": "Nagiriye inama yo kujya ku kigo nderabuzima"}},
]  # fmt: skip
CHECKLIST_CODES = {item["code"] for item in CHECKLIST}


class HomeVisit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client_id = models.UUIDField(unique=True, help_text="Made on the phone; makes re-sending safe.")
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="home_visits")
    chw = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="visits_made")
    visited_at = models.DateTimeField()
    checklist = models.JSONField(default=dict, help_text='{"bp_reading": true, ...}')
    note = models.CharField(max_length=1000, blank=True)
    reading = models.ForeignKey("health.BPReading", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    received_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-visited_at"]
        indexes = [models.Index(fields=["patient", "-visited_at"])]
