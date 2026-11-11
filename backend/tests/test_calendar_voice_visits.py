"""Family care calendar, handover notes, voice notes and home visits.

Owner: Aubin Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md
"""
import uuid
from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.community.models import HomeVisit
from apps.health.models import BPReading
from tests.conftest import client_for

ME = "/api/v1/patients/me"
WEBM = b"\x1a\x45\xdf\xa3" + b"\x00" * 2000


def base(world):
    return f"/api/v1/patients/{world.survivor.id}"


def soon(hours=24):
    return (timezone.now() + timedelta(hours=hours)).isoformat()


# --- calendar ---------------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_family_calendar_with_assignments_to_the_care_team(world):
    cg = client_for(world.caregiver)
    r = cg.post(f"{base(world)}/calendar/", {"title": "Physio", "kind": "therapy", "starts_at": soon(),
                                             "assigned_to": str(world.caregiver.id)}, format="json")
    assert r.status_code == 201 and r.json()["assigned_to_name"] == "caregiver"
    listing = client_for(world.survivor).get(f"{ME}/calendar/").json()
    assert [e["title"] for e in listing["results"]] == ["Physio"]
    assert {m["relation"] for m in listing["team"]} == {"patient", "clinician", "caregiver", "chw"}

    eid = r.json()["id"]
    done = cg.patch(f"{base(world)}/calendar/{eid}/", {"done": True}, format="json")
    assert done.status_code == 200 and done.json()["is_done"] is True
    assert cg.delete(f"{base(world)}/calendar/{eid}/").status_code == 204


@pytest.mark.django_db
def test_calendar_input_is_checked(world):
    c = client_for(world.survivor)
    stranger = cg_id = str(world.caregiver_unlinked.id)
    assert c.post(f"{ME}/calendar/", {"title": "x", "starts_at": soon(), "assigned_to": stranger}, format="json").status_code == 400
    assert c.post(f"{ME}/calendar/", {"title": "x", "starts_at": soon(5), "ends_at": soon(1)}, format="json").status_code == 400
    assert c.get(f"{ME}/calendar/?from=2026-01-01&to=2026-12-31").status_code == 400  # more than 92 days
    assert c.get(f"{ME}/calendar/?from=not-a-date").status_code == 400
    assert cg_id


@pytest.mark.django_db
def test_view_only_calendar_access_cannot_add(world):
    world.caregiver_link.scopes = ["view_calendar"]
    world.caregiver_link.save()
    cg = client_for(world.caregiver)
    assert cg.get(f"{base(world)}/calendar/").status_code == 200
    assert cg.post(f"{base(world)}/calendar/", {"title": "x", "starts_at": soon()}, format="json").status_code == 403


@pytest.mark.django_db
def test_handover_notes(world):
    cg = client_for(world.caregiver)
    assert cg.post(f"{base(world)}/handover/", {"text": "Took the evening dose at 20:10."}, format="json").status_code == 201
    rows = client_for(world.survivor).get(f"{ME}/handover/").json()["results"]
    assert rows[0]["author_role"] == "caregiver" and rows[0]["text"].startswith("Took")
    assert cg.post(f"{base(world)}/handover/", {"text": ""}, format="json").status_code == 400


# --- voice notes ------------------------------------------------------------------------------------------


def upload(client, url, data=WEBM, content_type="audio/webm", **extra):
    return client.post(url, {"audio": SimpleUploadedFile("note.webm", data, content_type=content_type), **extra}, format="multipart")


@pytest.mark.django_db
def test_record_and_listen_with_auditing(world):
    r = upload(client_for(world.survivor), f"{ME}/voice-notes/", duration_seconds="12", context="visit")
    assert r.status_code == 201 and r.json()["duration_seconds"] == 12
    nid = r.json()["id"]
    listen = client_for(world.clinician).get(f"{base(world)}/voice-notes/{nid}/")
    assert listen.status_code == 200 and listen.content == WEBM and listen["Content-Type"] == "audio/webm"
    assert AuditLog.objects.filter(action="access.view_notes", actor=world.clinician).exists()
    rows = client_for(world.caregiver).get(f"{base(world)}/voice-notes/").json()["results"]
    assert rows[0]["context"] == "visit" and "audio" not in rows[0]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "data,ctype",
    [(b"hello, not audio" * 10, "audio/webm"), (b"\x89PNG\r\n\x1a\n" + b"0" * 50, "image/png"), (b"RIFF0000WAVE", "text/plain")],
)
def test_only_real_audio_is_accepted(world, data, ctype):
    assert upload(client_for(world.survivor), f"{ME}/voice-notes/", data=data, content_type=ctype).status_code == 400


@pytest.mark.django_db
def test_size_and_length_limits(world, settings):
    c = client_for(world.survivor)
    assert upload(c, f"{ME}/voice-notes/", duration_seconds="500").status_code == 400
    settings.VOICE_NOTE_MAX_BYTES = 100
    assert upload(c, f"{ME}/voice-notes/").status_code == 400


@pytest.mark.django_db
def test_only_the_patient_or_the_recorder_can_delete(world):
    nid = upload(client_for(world.survivor), f"{ME}/voice-notes/").json()["id"]
    assert client_for(world.caregiver).delete(f"{base(world)}/voice-notes/{nid}/").status_code == 403
    assert client_for(world.clinician).delete(f"{base(world)}/voice-notes/{nid}/").status_code == 403  # no add_notes
    assert client_for(world.survivor).delete(f"{ME}/voice-notes/{nid}/").status_code == 204


# --- home visits ------------------------------------------------------------------------------------------


def visit(world, **over):
    body = {"client_id": str(uuid.uuid4()), "visited_at": timezone.now().isoformat(),
            "checklist": {"bp_reading": True, "medicines_reviewed": True}, "note": "Fictional demo visit."}
    body.update(over)
    return client_for(world.chw).post(f"{base(world)}/home-visits/", body, format="json")


@pytest.mark.django_db
def test_a_visit_with_a_reading_and_safe_resending(world):
    cid = str(uuid.uuid4())
    first = visit(world, client_id=cid, systolic=132, diastolic=84)
    again = visit(world, client_id=cid, systolic=132, diastolic=84)
    assert (first.status_code, again.status_code) == (201, 200)
    assert HomeVisit.objects.count() == 1
    reading = BPReading.objects.get(user=world.survivor)
    assert reading.entered_by == world.chw and reading.systolic == 132
    rows = client_for(world.survivor).get(f"{ME}/home-visits/").json()["results"]
    assert rows[0]["chw_name"] == "chw" and rows[0]["reading"] == {"systolic": 132, "diastolic": 84}


@pytest.mark.django_db
@pytest.mark.parametrize(
    "over",
    [
        {"visited_at": "2999-01-01T00:00:00Z"},
        {"checklist": {"diagnosed": True}},
        {"systolic": 130},
        {"systolic": 1300, "diastolic": 80},
    ],
)
def test_visit_input_is_checked(world, over):
    assert visit(world, **over).status_code == 400


@pytest.mark.django_db
def test_visits_older_than_two_weeks_are_refused_and_ids_cannot_be_reused(world):
    assert visit(world, visited_at=(timezone.now() - timedelta(days=15)).isoformat()).status_code == 400
    cid = str(uuid.uuid4())
    assert visit(world, client_id=cid).status_code == 201
    from tests.conftest import link, make_user

    other = make_user("chw2@test.org", "chw")
    link(world.survivor, other, "chw")
    r = client_for(other).post(f"{base(world)}/home-visits/", {"client_id": cid, "visited_at": timezone.now().isoformat()}, format="json")
    assert r.status_code == 400


@pytest.mark.django_db
def test_checklist_is_public_translated_and_draft():
    from rest_framework.test import APIClient

    body = APIClient().get("/api/v1/home-visit-checklist/?lang=rw").json()
    assert len(body["results"]) == 6 and body["status"] == "draft"
    assert body["results"][0]["label"] == "Napimye umuvuduko w'amaraso"


@pytest.mark.django_db
def test_summary_and_export_include_the_new_records(world):
    visit(world)
    upload(client_for(world.survivor), f"{ME}/voice-notes/")
    s = client_for(world.clinician).get(f"{base(world)}/summary/").json()
    assert s["home_visits"] == 1 and s["voice_notes"] == 1
    client_for(world.survivor).post(f"{ME}/calendar/", {"title": "Demo", "starts_at": soon()}, format="json")
    client_for(world.survivor).post(f"{ME}/messages/", {"body": "Hello"}, format="json")
    export = client_for(world.survivor).get("/api/v1/me/export/").json()["health"]
    assert {"voice_notes", "care_calendar", "handover_notes", "messages", "home_visits"} <= set(export)
    assert "audio" not in str(export["voice_notes"][0].keys())
