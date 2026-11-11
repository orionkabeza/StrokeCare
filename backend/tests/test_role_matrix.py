"""Who may call what: every patient-data route against every kind of person.

Owner: Kenneth Master (System architect) · AI-assisted draft, see AI_USE_LOG.md
Mirrors the role matrix the team already uses (route, survivor, prevention, clinician, visitor) and adds the
caregiver, unlinked people and other patients. A request for someone else's record is a 404, not a 403.
"""
import pytest

from apps.health.models import PlanTask, RecoveryPlan
from tests.conftest import client_for

ACTORS = [
    "visitor", "survivor", "prevention", "other_survivor",
    "clinician", "clinician_unlinked", "caregiver", "caregiver_unlinked", "admin", "chw",
]  # fmt: skip

# route name: (method, path under /patients/<ref>/, payload, {actor: expected status})
READINGS = {"systolic": 120, "diastolic": 80}
MATRIX = {
    "GET readings": ("get", "readings/", None, dict(
        visitor=401, survivor=200, prevention=200, other_survivor=404,
        clinician=200, clinician_unlinked=404, caregiver=200, caregiver_unlinked=404, admin=403, chw=200)),
    "POST readings": ("post", "readings/", READINGS, dict(
        visitor=401, survivor=201, prevention=201, other_survivor=404,
        clinician=403, clinician_unlinked=404, caregiver=201, caregiver_unlinked=404, admin=403, chw=201)),
    "GET plan": ("get", "plan/", None, dict(
        visitor=401, survivor=200, prevention=404, other_survivor=404,
        clinician=200, clinician_unlinked=404, caregiver=200, caregiver_unlinked=404, admin=403, chw=200)),
    "POST plan task": ("post", "plan/tasks/", {"title": "Demo task"}, dict(
        visitor=401, survivor=403, prevention=403, other_survivor=404,
        clinician=201, clinician_unlinked=404, caregiver=403, caregiver_unlinked=404, admin=403, chw=403)),
    "GET checkins": ("get", "checkins/", None, dict(
        visitor=401, survivor=200, prevention=200, other_survivor=404,
        clinician=200, clinician_unlinked=404, caregiver=200, caregiver_unlinked=404, admin=403, chw=200)),
    "POST checkins": ("post", "checkins/", {"answers": [{"question": "new-joint-pain", "value": False}]}, dict(
        visitor=401, survivor=201, prevention=201, other_survivor=404,
        clinician=403, clinician_unlinked=404, caregiver=201, caregiver_unlinked=404, admin=403, chw=403)),
    "GET summary": ("get", "summary/", None, dict(
        visitor=401, survivor=200, prevention=200, other_survivor=404,
        clinician=200, clinician_unlinked=404, caregiver=200, caregiver_unlinked=404, admin=403, chw=200)),
    "POST task tick": ("post", "plan/tasks/{task}/log/", {}, dict(
        visitor=401, survivor=201, prevention=404, other_survivor=404,
        clinician=403, clinician_unlinked=404, caregiver=201, caregiver_unlinked=404, admin=403, chw=403)),
    "GET medications": ("get", "medications/", None, dict(
        visitor=401, survivor=200, prevention=200, other_survivor=404,
        clinician=200, clinician_unlinked=404, caregiver=200, caregiver_unlinked=404, admin=403, chw=200)),
    "POST medications": ("post", "medications/", {"name": "Demo", "times": ["08:00"]}, dict(
        visitor=401, survivor=403, prevention=403, other_survivor=404,
        clinician=201, clinician_unlinked=404, caregiver=403, caregiver_unlinked=404, admin=403, chw=403)),
    "POST visit question": ("post", "visit-questions/", {"text": "Demo question"}, dict(
        visitor=401, survivor=201, prevention=201, other_survivor=404,
        clinician=403, clinician_unlinked=404, caregiver=201, caregiver_unlinked=404, admin=403, chw=201)),
    "GET messages": ("get", "messages/", None, dict(
        visitor=401, survivor=200, prevention=200, other_survivor=404,
        clinician=200, clinician_unlinked=404, caregiver=200, caregiver_unlinked=404, admin=403, chw=200)),
    "POST calendar event": ("post", "calendar/", {"title": "Demo", "starts_at": "2026-11-20T09:00:00Z"}, dict(
        visitor=401, survivor=201, prevention=201, other_survivor=404,
        clinician=201, clinician_unlinked=404, caregiver=201, caregiver_unlinked=404, admin=403, chw=201)),
    "POST home visit": ("post", "home-visits/", {"client_id": "0b6f7c8e-1d2a-4c3b-9e8f-7a6b5c4d3e2f",
                                                 "visited_at": "{now}"}, dict(
        visitor=401, survivor=403, prevention=403, other_survivor=404,
        clinician=403, clinician_unlinked=404, caregiver=403, caregiver_unlinked=404, admin=403, chw=201)),
    "GET voice notes": ("get", "voice-notes/", None, dict(
        visitor=401, survivor=200, prevention=200, other_survivor=404,
        clinician=200, clinician_unlinked=404, caregiver=200, caregiver_unlinked=404, admin=403, chw=200)),
    "GET mobility": ("get", "mobility/", None, dict(
        visitor=401, survivor=200, prevention=200, other_survivor=404, clinician=200, clinician_unlinked=404, caregiver=200, caregiver_unlinked=404, admin=403, chw=200)),
    "POST mobility": ("post", "mobility/", {"kind": "walking", "minutes": 10}, dict(
        visitor=401, survivor=201, prevention=201, other_survivor=404, clinician=403, clinician_unlinked=404, caregiver=201, caregiver_unlinked=404, admin=403, chw=201)),
    "GET goals": ("get", "goals/", None, dict(
        visitor=401, survivor=200, prevention=200, other_survivor=404, clinician=200, clinician_unlinked=404, caregiver=200, caregiver_unlinked=404, admin=403, chw=200)),
    "POST goal": ("post", "goals/", {"text": "Walk to the gate"}, dict(
        visitor=401, survivor=201, prevention=201, other_survivor=404, clinician=403, clinician_unlinked=404, caregiver=201, caregiver_unlinked=404, admin=403, chw=201)),
    "GET phases": ("get", "phases/", None, dict(
        visitor=401, survivor=200, prevention=200, other_survivor=404, clinician=200, clinician_unlinked=404, caregiver=200, caregiver_unlinked=404, admin=403, chw=200)),
    "POST phase": ("post", "phases/", {"name": "First stage", "starts_on": "2026-11-01"}, dict(
        visitor=401, survivor=403, prevention=403, other_survivor=404, clinician=201, clinician_unlinked=404, caregiver=403, caregiver_unlinked=404, admin=403, chw=403)),
    "GET phrases": ("get", "phrases/", None, dict(
        visitor=401, survivor=200, prevention=200, other_survivor=404, clinician=200, clinician_unlinked=404, caregiver=200, caregiver_unlinked=404, admin=403, chw=200)),
    "POST phrase": ("post", "phrases/", {"text": "I am thirsty"}, dict(
        visitor=401, survivor=201, prevention=201, other_survivor=404, clinician=403, clinician_unlinked=404, caregiver=201, caregiver_unlinked=404, admin=403, chw=201)),
    "GET progress": ("get", "progress/", None, dict(
        visitor=401, survivor=200, prevention=200, other_survivor=404, clinician=200, clinician_unlinked=404, caregiver=200, caregiver_unlinked=404, admin=403, chw=200)),
    "POST bulk doses": ("post", "medications/doses/bulk/", {"doses": [{"medication": "0b6f7c8e-1d2a-4c3b-9e8f-7a6b5c4d3e2f", "time": "08:00"}]}, dict(
        visitor=401, survivor=400, prevention=400, other_survivor=404, clinician=403, clinician_unlinked=404, caregiver=400, caregiver_unlinked=404, admin=403, chw=403)),
}  # fmt: skip

CASES = [(route, actor) for route in MATRIX for actor in ACTORS]


@pytest.mark.parametrize("route,actor", CASES, ids=[f"{r} / {a}" for r, a in CASES])
def test_role_matrix(world, route, actor):
    method, path, payload, expected = MATRIX[route]
    plan = RecoveryPlan.objects.create(patient=world.survivor, created_by=world.clinician)
    task = PlanTask.objects.create(plan=plan, title="Demo task")

    # People who keep their own record call /patients/me/...; everyone else names the survivor.
    own_record = actor in {"survivor", "prevention", "admin"}
    ref = "me" if own_record else str(world.survivor.id)
    client = client_for(None if actor == "visitor" else getattr(world, actor))
    url = f"/api/v1/patients/{ref}/" + path.format(task=task.id)

    if payload is not None and payload.get("visited_at") == "{now}":
        from django.utils import timezone

        payload = {**payload, "visited_at": timezone.now().isoformat()}
    response = getattr(client, method)(url, payload, format="json") if payload is not None else getattr(client, method)(url)
    assert response.status_code == expected[actor], response.content


def test_matrix_covers_every_actor():
    for route, (_, _, _, expected) in MATRIX.items():
        assert set(expected) == set(ACTORS), route


def test_a_patient_cannot_name_another_patients_id(world):
    """Even a patient's own UUID in the URL gives no way into someone else's record."""
    client = client_for(world.other_survivor)
    assert client.get(f"/api/v1/patients/{world.survivor.id}/readings/").status_code == 404


def test_unknown_reference_is_not_found(world):
    client = client_for(world.survivor)
    assert client.get("/api/v1/patients/not-a-uuid/readings/").status_code == 404


def test_unverified_clinician_link_gives_no_access(world):
    from apps.accounts.models import Role
    from tests.conftest import link, make_user

    fake = make_user("fake@test.org", Role.CLINICIAN, verified=False)
    link(world.survivor, fake, "clinician")
    assert client_for(fake).get(f"/api/v1/patients/{world.survivor.id}/readings/").status_code == 404
