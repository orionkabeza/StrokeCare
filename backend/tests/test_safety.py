"""The safety boundary, as tests. If one of these fails, a safety rule was broken.

Owner: Erica Rurangwa Sheja (Product Owner) · AI-assisted draft, see AI_USE_LOG.md
Rules: no diagnosis, no prescribing, no risk score, no colours or labels on blood pressure, no unverified
emergency number, nothing marked "reviewed" without a named reviewer.
"""
import re
from pathlib import Path

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.content.models import EducationItem, EducationTranslation, EmergencyContact, TalkPhrase
from apps.health.models import BPReading, CheckIn, CheckInQuestion, PlanTask, RecoveryPlan
from tests.conftest import client_for

ME = "/api/v1/patients/me"
BACKEND = Path(__file__).resolve().parents[1]

# Words that would turn a description into a judgement. Matched against whole words in field names.
FORBIDDEN = {
    "risk", "diagnosis", "diagnoses", "diagnostic", "score", "severity", "normal", "abnormal", "high", "low",
    "elevated", "hypertension", "hypertensive", "colour", "color", "band", "threshold", "category", "stage",
    "grade", "verdict", "prediction", "predicted",
}  # fmt: skip


def keys(node):
    if isinstance(node, dict):
        for k, v in node.items():
            yield k
            yield from keys(v)
    elif isinstance(node, list):
        for item in node:
            yield from keys(item)


def judgement_words(names):
    return {n for n in names if FORBIDDEN & set(re.split(r"[_\W]+", n.lower()))}


@pytest.mark.django_db
def test_no_judgement_field_in_any_patient_response(world):
    """S11: no risk or diagnosis field anywhere, for every kind of response a clinician or patient sees."""
    c = client_for(world.survivor)
    c.post(f"{ME}/readings/", {"systolic": 180, "diastolic": 110}, format="json")  # a high-looking number
    RecoveryPlan.objects.create(patient=world.survivor)
    c.post(f"{ME}/checkins/", {"answers": [{"question": "new-or-worse-symptoms", "value": True}]}, format="json")
    c.post(f"{ME}/mobility/", {"kind": "walking", "minutes": 10}, format="json")
    c.post(f"{ME}/goals/", {"text": "Walk to the gate"}, format="json")
    c.post(f"{ME}/phrases/", {"text": "I am thirsty"}, format="json")
    clin = client_for(world.clinician)
    base = f"/api/v1/patients/{world.survivor.id}"
    clin.post(f"{base}/phases/", {"name": "Building up", "starts_on": "2026-11-01"}, format="json")
    responses = [
        c.get(f"{ME}/mobility/"), c.get(f"{ME}/goals/"), c.get(f"{ME}/phases/"), c.get(f"{ME}/phrases/"),
        c.get(f"{ME}/progress/"), c.get("/api/v1/me/care-team/"), clin.get("/api/v1/doctor/overview/"),
        c.get(f"{ME}/readings/"), c.get(f"{ME}/plan/"), c.get(f"{ME}/checkins/"), c.get(f"{ME}/summary/"),
        c.get("/api/v1/checkin-questions/"), c.get("/api/v1/emergency/"),
        clin.get(f"{base}/summary/"), clin.get(f"{base}/readings/"),
    ]  # fmt: skip
    for r in responses:
        assert r.status_code == 200
        assert judgement_words(set(keys(r.json()))) == set(), r.request["PATH_INFO"]


def test_no_judgement_field_in_the_database_models():
    from apps.care.models import Alert
    from apps.health.models import Medication, MedicationDose
    from apps.recovery.models import CarePhase, CustomPhrase, Goal, MobilityLog

    for model in (BPReading, CheckIn, PlanTask, RecoveryPlan, Medication, MedicationDose, Alert,
                  Goal, CarePhase, MobilityLog, CustomPhrase):
        assert judgement_words({f.name for f in model._meta.get_fields()}) == set(), model.__name__


@pytest.mark.django_db
def test_a_very_high_reading_gets_no_special_treatment(world):
    c = client_for(world.survivor)
    low = c.post(f"{ME}/readings/", {"systolic": 100, "diastolic": 60}, format="json").json()
    high = c.post(f"{ME}/readings/", {"systolic": 250, "diastolic": 150}, format="json").json()
    assert set(low) == set(high)  # same shape: no flag, colour or label appears for extreme values


@pytest.mark.django_db
def test_summary_says_it_is_not_a_diagnosis(world):
    body = client_for(world.clinician).get(f"/api/v1/patients/{world.survivor.id}/summary/").json()
    assert "not a diagnosis" in body["disclaimer"]


# --- emergency information ------------------------------------------------------------------------------


@pytest.mark.django_db
def test_emergency_endpoint_is_public_and_contains_no_number_until_one_is_verified():
    from rest_framework.test import APIClient

    r = APIClient().get("/api/v1/emergency/")
    assert r.status_code == 200
    body = r.json()
    assert "Do not wait for this app" in body["message"]
    assert body["contacts"] == [] and body["contacts_available"] is False
    assert not re.search(r"\d", body["message"])


@pytest.mark.django_db
def test_inactive_or_unverified_contacts_never_appear():
    from rest_framework.test import APIClient

    EmergencyContact.objects.create(region="R", label="Not verified", kind="helpline", phone="1")
    EmergencyContact.objects.create(
        region="R", label="Retired", kind="helpline", phone="2", is_active=False,
        verified_by_name="V", verified_at=timezone.now(),
    )  # fmt: skip
    assert APIClient().get("/api/v1/emergency/").json()["contacts"] == []


@pytest.mark.django_db
def test_database_refuses_a_verified_contact_with_no_verifier():
    with pytest.raises(IntegrityError), transaction.atomic():
        EmergencyContact.objects.create(region="R", label="x", kind="helpline", phone="1", verified_at=timezone.now())


def _strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from _strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _strings(v)


def test_no_digit_appears_in_any_emergency_text_or_fixture():
    """Emergency codes can be as short as three digits, so ANY digit in guidance text or shipped fixtures fails.
    Numbers may only come from verified EmergencyContact rows, never from code."""
    import json

    from apps.content.guidance import GUIDANCE

    texts = list(GUIDANCE.values())
    fixtures = list((BACKEND / "apps" / "health" / "fixtures").glob("*.json"))
    fixtures += list((BACKEND / "apps" / "content" / "fixtures").glob("*.json"))
    assert len(fixtures) >= 2
    for fixture in fixtures:
        texts += list(_strings(json.loads(fixture.read_text(encoding="utf-8"))))
    offenders = [t for t in texts if re.search(r"\d", t)]
    assert offenders == []


# --- review rules ---------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_nothing_can_be_reviewed_without_a_named_reviewer_and_a_date():
    item = EducationItem.objects.create(slug="demo", source_name="Demo source")
    assert item.status == "draft"  # the default is always draft
    for model, kwargs in [
        (EducationItem, {"slug": "x", "source_name": "s", "status": "reviewed"}),
        (CheckInQuestion, {"code": "x", "prompt": {"en": "?"}, "answer_type": "yes_no", "status": "reviewed"}),
        (TalkPhrase, {"code": "x", "category": "needs", "label": {"en": "x"}, "status": "reviewed"}),
    ]:
        with pytest.raises(IntegrityError), transaction.atomic():
            model.objects.create(**kwargs)
    with pytest.raises(IntegrityError), transaction.atomic():
        EducationTranslation.objects.create(item=item, locale="fr", title="t", status="reviewed")
    ok = EducationItem.objects.create(
        slug="signed", source_name="s", status="reviewed", reviewed_by_name="Dr Demo", reviewed_at=timezone.now()
    )
    assert ok.status == "reviewed"


@pytest.mark.django_db
def test_education_always_shows_its_source_and_review_state():
    from rest_framework.test import APIClient

    item = EducationItem.objects.create(slug="demo", source_name="Demo source", is_published=True)
    EducationTranslation.objects.create(item=item, locale="en", title="Demo", body="Fictional.")
    data = APIClient().get("/api/v1/education/demo/").json()
    assert data["source"]["name"] == "Demo source"
    assert data["clinical_review"]["status"] == "draft" and data["translation_review"]["status"] == "draft"
