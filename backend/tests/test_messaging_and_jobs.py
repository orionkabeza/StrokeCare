"""Care-team messaging, the scheduler, and the community-health-worker role.

Owner: Kenneth Master (System architect) · AI-assisted draft, see AI_USE_LOG.md
"""
import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.accounts.models import Role
from apps.care.models import Alert
from tests.conftest import PASSWORD, client_for, make_user

ME = "/api/v1/patients/me"


def thread(world):
    return f"/api/v1/patients/{world.survivor.id}/messages/"


# --- messaging --------------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_the_care_team_shares_one_thread_with_unread_counts(world):
    client_for(world.survivor).post(f"{ME}/messages/", {"body": "Feeling steadier today."}, format="json")
    client_for(world.caregiver).post(thread(world), {"body": "We walked to the gate."}, format="json")

    clin = client_for(world.clinician)
    body = clin.get(thread(world)).json()
    assert [m["body"] for m in body["results"]] == ["Feeling steadier today.", "We walked to the gate."]  # oldest first
    assert body["results"][1]["sender_role"] == "caregiver" and not body["results"][1]["mine"]
    assert "not for emergencies" in body["notice"]

    inbox = clin.get("/api/v1/inbox/").json()["results"]
    assert inbox[0]["patient_name"] == "survivor" and inbox[0]["unread"] == 2
    assert clin.post(f"{thread(world)}read/").status_code == 204
    assert clin.get("/api/v1/inbox/").json()["results"][0]["unread"] == 0
    # the sender's own message never counts as unread for them
    assert client_for(world.survivor).get("/api/v1/inbox/").json()["results"][0]["unread"] == 1


@pytest.mark.django_db
@pytest.mark.parametrize("text", ["", "   ", "x" * 2001])
def test_message_text_is_checked(world, text):
    assert client_for(world.survivor).post(f"{ME}/messages/", {"body": text}, format="json").status_code == 400


@pytest.mark.django_db
def test_messaging_follows_the_patients_choices(world):
    world.clinician_link.scopes = ["view_summary"]
    world.clinician_link.save()
    assert client_for(world.clinician).get(thread(world)).status_code == 403
    assert client_for(world.clinician).get("/api/v1/inbox/").json()["results"] == []
    assert client_for(world.caregiver_unlinked).get(thread(world)).status_code == 404


@pytest.mark.django_db
def test_patients_list_shows_unread_messages(world):
    client_for(world.survivor).post(f"{ME}/messages/", {"body": "Hello"}, format="json")
    rows = client_for(world.clinician).get("/api/v1/patients/").json()
    assert rows[0]["facts"]["unread_messages"] == 1


# --- scheduler --------------------------------------------------------------------------------------------


def urgent(world):
    client_for(world.survivor).post(
        f"{ME}/checkins/", {"answers": [{"question": "new-or-worse-symptoms", "value": True}]}, format="json"
    )


@pytest.mark.django_db
def test_cron_endpoint_is_off_without_a_secret_and_guarded_with_one(world, settings):
    url = "/api/v1/internal/jobs/run/"
    settings.CRON_SECRET = ""
    assert APIClient().post(url).status_code == 404
    settings.CRON_SECRET = "s3cret-value"
    assert APIClient().post(url, HTTP_X_CRON_SECRET="wrong").status_code == 403
    urgent(world)
    r = APIClient().post(url, HTTP_X_CRON_SECRET="s3cret-value")
    assert r.status_code == 200 and r.json() == {"caregivers_checked": 1, "alerts_created": 1}
    assert APIClient().post(url, HTTP_X_CRON_SECRET="s3cret-value").json()["alerts_created"] == 0  # never twice


@pytest.mark.django_db
def test_worker_and_one_shot_commands_create_alerts_once(world):
    urgent(world)
    call_command("run_scheduler", "--once")
    call_command("generate_alerts")
    assert Alert.objects.filter(recipient=world.caregiver, kind="urgent_answer").count() == 1


# --- community health workers -----------------------------------------------------------------------------


@pytest.mark.django_db
def test_nobody_can_self_register_as_a_chw():
    body = {"email": "c@test.org", "password": PASSWORD, "display_name": "x", "role": "chw"}
    assert APIClient().post("/api/v1/auth/register/", body, format="json").status_code == 400


@pytest.mark.django_db
def test_only_a_verified_chw_can_redeem_a_chw_code(world):
    code = client_for(world.other_survivor).post("/api/v1/links/invite/", {"relation": "chw"}, format="json").json()["code"]
    unverified = make_user("u@test.org", Role.CHW, verified=False)
    for user in (unverified, world.caregiver_unlinked, world.clinician_unlinked):
        assert client_for(user).post("/api/v1/links/redeem/", {"code": code}, format="json").status_code == 400
    fresh_chw = make_user("chw2@test.org", Role.CHW)
    assert client_for(fresh_chw).post("/api/v1/links/redeem/", {"code": code}, format="json").status_code == 200
    assert client_for(fresh_chw).get(f"/api/v1/patients/{world.other_survivor.id}/summary/").status_code == 200


@pytest.mark.django_db
def test_a_chw_can_never_write_the_plan_or_the_medicine_list(world):
    r = client_for(world.survivor).post("/api/v1/links/invite/", {"relation": "chw", "scopes": ["manage_meds"]}, format="json")
    assert r.status_code == 400
    r = client_for(world.survivor).post("/api/v1/links/invite/", {"relation": "chw", "scopes": ["manage_plan"]}, format="json")
    assert r.status_code == 400
