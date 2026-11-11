"""The right to download and erase your data, the audit trail, and no caching.

Owner: Kenneth Master (System architect) · AI-assisted draft, see AI_USE_LOG.md
"""
import json

import pytest

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.health.models import BPReading
from tests.conftest import PASSWORD, client_for

ME = "/api/v1/patients/me"


@pytest.mark.django_db
def test_export_contains_my_data_and_nobody_elses(world):
    client_for(world.survivor).post(f"{ME}/readings/", {"systolic": 121, "diastolic": 79, "note": "mine"}, format="json")
    client_for(world.other_survivor).post(f"{ME}/readings/", {"systolic": 133, "diastolic": 88, "note": "theirs"}, format="json")
    r = client_for(world.survivor).get("/api/v1/me/export/")
    assert r.status_code == 200 and "attachment" in r["Content-Disposition"]
    text = r.content.decode()
    data = json.loads(text)
    assert [x["note"] for x in data["health"]["blood_pressure_readings"]] == ["mine"]
    assert "theirs" not in text and "other@test.org" not in text
    assert "password" not in text


@pytest.mark.django_db
def test_export_for_a_caregiver_has_no_health_section(world):
    assert "health" not in client_for(world.caregiver).get("/api/v1/me/export/").json()


@pytest.mark.django_db
def test_deleting_an_account_needs_the_password_and_erases_everything(world):
    c = client_for(world.survivor)
    c.post(f"{ME}/readings/", {"systolic": 121, "diastolic": 79}, format="json")
    assert c.delete("/api/v1/me/", {"password": "wrong"}, format="json").status_code == 400
    assert User.objects.filter(id=world.survivor.id).exists()

    assert c.delete("/api/v1/me/", {"password": PASSWORD}, format="json").status_code == 204
    assert not User.objects.filter(id=world.survivor.id).exists()
    assert BPReading.objects.count() == 0
    # the clinician's link went with it, and the deletion itself is logged without naming anyone
    assert client_for(world.clinician).get("/api/v1/patients/").json() == []
    gone = AuditLog.objects.get(action="account.deleted")
    assert gone.actor is None and gone.subject is None


@pytest.mark.django_db
def test_every_access_by_someone_else_is_audited_but_own_access_is_not(world):
    client_for(world.survivor).get(f"{ME}/readings/")
    assert not AuditLog.objects.filter(action="access.view_readings").exists()
    client_for(world.clinician).get(f"/api/v1/patients/{world.survivor.id}/readings/")
    entry = AuditLog.objects.get(action="access.view_readings")
    assert entry.actor == world.clinician and entry.subject == world.survivor
    assert entry.metadata == {"relation": "clinician"}  # who and what kind: never a health value


@pytest.mark.django_db
def test_patient_sees_who_looked_at_their_data_in_their_export(world):
    client_for(world.clinician).get(f"/api/v1/patients/{world.survivor.id}/summary/")
    log = client_for(world.survivor).get("/api/v1/me/export/").json()["access_log"]
    assert any(e["action"] == "access.view_summary" and e["by_role"] == "clinician" for e in log)


@pytest.mark.django_db
def test_plan_changes_by_a_clinician_are_audited(world):
    client_for(world.clinician).post(f"/api/v1/patients/{world.survivor.id}/plan/tasks/", {"title": "Demo"}, format="json")
    assert AuditLog.objects.filter(action="plan.task_added", actor=world.clinician, subject=world.survivor).exists()


@pytest.mark.django_db
def test_the_audit_log_is_append_only(world):
    entry = AuditLog.objects.create(action="test.entry", subject=world.survivor)
    entry.action = "tampered"
    with pytest.raises(RuntimeError):
        entry.save()
    with pytest.raises(RuntimeError):
        entry.delete()
    with pytest.raises(RuntimeError):
        AuditLog.objects.filter(id=entry.id).update(action="tampered")
    with pytest.raises(RuntimeError):
        AuditLog.objects.all().delete()


@pytest.mark.django_db
def test_api_responses_are_never_cached(world):
    r = client_for(world.survivor).get(f"{ME}/readings/")
    assert r["Cache-Control"] == "no-store"


@pytest.mark.django_db
def test_errors_use_one_plain_shape(world):
    r = client_for(world.survivor).get(f"/api/v1/patients/{world.other_survivor.id}/readings/")
    assert r.status_code == 404 and set(r.json()) == {"error"} and {"code", "message"} <= set(r.json()["error"])
