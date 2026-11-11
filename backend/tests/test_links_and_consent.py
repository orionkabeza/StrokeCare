"""Consent gate and the invitation flow between patients, clinicians and caregivers.

Owner: Kenneth Master (System architect) · AI-assisted draft, see AI_USE_LOG.md
"""
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import Role
from apps.care.models import CareLink, LinkStatus
from tests.conftest import client_for, link, make_user


def invite(patient, **body):
    body.setdefault("relation", "clinician")
    return client_for(patient).post("/api/v1/links/invite/", body, format="json")


# --- consent --------------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_health_data_is_locked_until_consent_is_given():
    user = make_user("a@test.org", Role.SURVIVOR, consent=False)
    r = client_for(user).get("/api/v1/patients/me/readings/")
    assert r.status_code == 403 and r.json()["error"]["code"] == "consent_required"
    assert client_for(user).post("/api/v1/me/consents/", {"kind": "health_data", "accept": True}, format="json").status_code == 200
    assert client_for(user).get("/api/v1/patients/me/readings/").status_code == 200


@pytest.mark.django_db
def test_consent_for_a_different_version_does_not_count(settings):
    user = make_user("a@test.org", Role.SURVIVOR)
    settings.CONSENT_VERSIONS = {**settings.CONSENT_VERSIONS, "health_data": "2.0"}
    assert client_for(user).get("/api/v1/patients/me/readings/").status_code == 403  # must agree again


@pytest.mark.django_db
def test_withdrawing_consent_cuts_off_linked_clinicians_and_caregivers(world):
    url = f"/api/v1/patients/{world.survivor.id}/readings/"
    assert client_for(world.clinician).get(url).status_code == 200
    r = client_for(world.survivor).post("/api/v1/me/consents/", {"kind": "health_data", "accept": False}, format="json")
    assert r.status_code == 200 and r.json()["health_data"]["granted"] is False
    assert client_for(world.clinician).get(url).status_code == 404
    assert client_for(world.caregiver).get(url).status_code == 404
    assert client_for(world.clinician).get("/api/v1/patients/").json() == []


@pytest.mark.django_db
def test_caregiver_cannot_give_a_health_data_consent():
    user = make_user("c@test.org", Role.CAREGIVER)
    r = client_for(user).post("/api/v1/me/consents/", {"kind": "health_data", "accept": True}, format="json")
    assert r.status_code == 400


# --- invitations ------------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_invite_and_redeem_gives_access_and_the_code_is_single_use(world):
    r = invite(world.other_survivor, relation="clinician")
    assert r.status_code == 201
    code = r.json()["code"]
    assert len(code.replace("-", "")) == 8
    assert not CareLink.objects.filter(invite_hash=code).exists()  # only a hash is stored

    ok = client_for(world.clinician_unlinked).post("/api/v1/links/redeem/", {"code": code.lower()}, format="json")
    assert ok.status_code == 200 and ok.json()["status"] == "active"
    again = client_for(world.clinician).post("/api/v1/links/redeem/", {"code": code}, format="json")
    assert again.status_code == 400
    assert client_for(world.clinician_unlinked).get(f"/api/v1/patients/{world.other_survivor.id}/summary/").status_code == 200


@pytest.mark.django_db
def test_redeem_failures_all_look_the_same(world):
    """Expired, wrong role, unverified, own code and nonsense all answer with the same message."""
    unverified = make_user("u@test.org", Role.CLINICIAN, verified=False)
    code = invite(world.other_survivor, relation="clinician").json()["code"]
    expired = invite(world.other_survivor, relation="clinician").json()
    CareLink.objects.filter(id=expired["id"]).update(invite_expires_at=timezone.now() - timedelta(minutes=1))

    attempts = [
        (unverified, code),
        (world.caregiver_unlinked, code),  # a caregiver cannot use a clinician's code
        (world.other_survivor, code),  # a patient cannot redeem their own code
        (world.clinician_unlinked, expired["code"]),
        (world.clinician_unlinked, "ZZZZ-ZZZZ"),
    ]
    messages = set()
    for user, c in attempts:
        r = client_for(user).post("/api/v1/links/redeem/", {"code": c}, format="json")
        assert r.status_code == 400
        messages.add(r.json()["error"]["fields"]["code"][0])
    assert len(messages) == 1


@pytest.mark.django_db
def test_invite_scopes_are_checked_against_the_relation(world):
    assert invite(world.survivor, relation="caregiver", scopes=["manage_plan"]).status_code == 400
    assert invite(world.survivor, relation="clinician", scopes=["log_readings"]).status_code == 400
    assert invite(world.survivor, relation="clinician", scopes=[]).status_code == 400  # sharing nothing is not a link
    from apps.care.scopes import CLINICIAN_ALLOWED

    assert invite(world.survivor, relation="clinician").json()["scopes"] == sorted(CLINICIAN_ALLOWED)
    ok = invite(world.survivor, relation="caregiver", scopes=["view_plan", "log_tasks"])
    assert ok.status_code == 201 and ok.json()["scopes"] == ["log_tasks", "view_plan"]


@pytest.mark.django_db
def test_only_people_with_a_health_record_can_invite(world):
    assert invite(world.clinician).status_code == 403
    assert invite(world.caregiver, relation="caregiver").status_code == 403


@pytest.mark.django_db
def test_patient_can_narrow_what_is_shared_and_it_applies_at_once(world):
    url = f"/api/v1/patients/{world.survivor.id}/summary/"
    assert client_for(world.caregiver).get(url).status_code == 200
    r = client_for(world.survivor).patch(f"/api/v1/links/{world.caregiver_link.id}/", {"scopes": ["view_plan"]}, format="json")
    assert r.status_code == 200
    assert client_for(world.caregiver).get(url).status_code == 403
    assert client_for(world.caregiver).get(f"/api/v1/patients/{world.survivor.id}/plan/").status_code == 200
    # a caregiver cannot widen their own access, and a clinician link cannot hold caregiver-only scopes
    assert client_for(world.caregiver).patch(f"/api/v1/links/{world.caregiver_link.id}/", {"scopes": ["view_summary"]}, format="json").status_code == 403
    bad = client_for(world.survivor).patch(f"/api/v1/links/{world.clinician_link.id}/", {"scopes": ["log_readings"]}, format="json")
    assert bad.status_code == 400


@pytest.mark.django_db
@pytest.mark.parametrize("who", ["survivor", "clinician"])
def test_either_side_can_end_a_link(world, who):
    url = f"/api/v1/patients/{world.survivor.id}/readings/"
    assert client_for(world.clinician).get(url).status_code == 200
    r = client_for(getattr(world, who)).delete(f"/api/v1/links/{world.clinician_link.id}/")
    assert r.status_code == 204
    assert client_for(world.clinician).get(url).status_code == 404
    world.clinician_link.refresh_from_db()
    assert world.clinician_link.status == LinkStatus.REVOKED


@pytest.mark.django_db
def test_strangers_cannot_see_or_end_other_peoples_links(world):
    r = client_for(world.other_survivor).delete(f"/api/v1/links/{world.clinician_link.id}/")
    assert r.status_code == 404
    assert client_for(world.other_survivor).get("/api/v1/links/").json() == []


@pytest.mark.django_db
def test_my_patients_lists_only_active_eligible_links(world):
    link(world.other_survivor, world.clinician, "clinician")
    rows = client_for(world.clinician).get("/api/v1/patients/").json()
    assert {r["patient_id"] for r in rows} == {str(world.survivor.id), str(world.other_survivor.id)}
    assert all("email" not in r for r in rows)
    assert client_for(world.clinician_unlinked).get("/api/v1/patients/").json() == []
