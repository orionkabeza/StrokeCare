"""Caregiver alerts and the clinician's "needs a look" facts.

Owner: Kenneth Master (System architect) · AI-assisted draft, see AI_USE_LOG.md
Both are plain facts (dates and counts). Neither ranks people by risk.
"""
from datetime import timedelta

import pytest
from django.core.management import call_command

from apps.care.models import Alert
from apps.health.models import CheckIn, Medication
from apps.health.services import local_today
from tests.conftest import client_for, link
from tests.test_safety import judgement_words, keys

ME = "/api/v1/patients/me"


def urgent_checkin(world):
    return client_for(world.survivor).post(
        f"{ME}/checkins/", {"answers": [{"question": "new-or-worse-symptoms", "value": True}]}, format="json"
    )


def med_since(patient, days):
    return Medication.objects.create(
        patient=patient, name="Demo", times=["08:00"], start_date=local_today(patient) - timedelta(days=days)
    )


# --- caregiver alerts -------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_an_urgent_answer_alerts_the_caregiver_exactly_once(world):
    urgent_checkin(world)
    c = client_for(world.caregiver)
    first = c.get("/api/v1/alerts/").json()
    second = c.get("/api/v1/alerts/").json()
    assert [a["kind"] for a in first["results"]] == ["urgent_answer"] and first["unread"] == 1
    assert len(second["results"]) == 1  # opening the app again never repeats an alert
    assert "not an emergency service" in first["note"]


@pytest.mark.django_db
def test_reading_alerts(world):
    urgent_checkin(world)
    c = client_for(world.caregiver)
    aid = c.get("/api/v1/alerts/").json()["results"][0]["id"]
    assert c.post(f"/api/v1/alerts/{aid}/read/").status_code == 204
    assert c.get("/api/v1/alerts/").json()["unread"] == 0
    assert client_for(world.caregiver_unlinked).post(f"/api/v1/alerts/{aid}/read/").status_code == 404
    assert c.post("/api/v1/alerts/read-all/").status_code == 204


@pytest.mark.django_db
def test_no_check_in_for_two_days_alerts_but_never_checked_in_does_not(world):
    c = client_for(world.caregiver)
    assert c.get("/api/v1/alerts/").json()["results"] == []  # never checked in: no nagging
    CheckIn.objects.create(user=world.survivor, date=local_today(world.survivor) - timedelta(days=3))
    rows = c.get("/api/v1/alerts/").json()["results"]
    assert [(a["kind"], a["detail"]) for a in rows] == [("no_check_in", {"days": 3})]


@pytest.mark.django_db
def test_doses_not_marked_yesterday_alert_with_a_count(world):
    med_since(world.survivor, 3)
    rows = client_for(world.caregiver).get("/api/v1/alerts/").json()["results"]
    assert rows[0]["kind"] == "doses_not_marked" and rows[0]["detail"]["count"] == 1


@pytest.mark.django_db
def test_alerts_follow_what_the_patient_chose_to_share(world):
    med_since(world.survivor, 3)
    urgent_checkin(world)
    world.caregiver_link.scopes = ["view_plan"]
    world.caregiver_link.save()
    assert client_for(world.caregiver).get("/api/v1/alerts/").json()["results"] == []


@pytest.mark.django_db
def test_withdrawn_consent_stops_alerts(world):
    urgent_checkin(world)
    client_for(world.survivor).post("/api/v1/me/consents/", {"kind": "health_data", "accept": False}, format="json")
    assert client_for(world.caregiver).get("/api/v1/alerts/").json()["results"] == []


@pytest.mark.django_db
def test_alerts_are_for_caregivers_and_the_command_matches_the_endpoint(world):
    assert client_for(world.clinician).get("/api/v1/alerts/").status_code == 403
    urgent_checkin(world)
    call_command("generate_alerts")
    call_command("generate_alerts")
    assert Alert.objects.filter(recipient=world.caregiver).count() == 1


# --- clinician facts and filters --------------------------------------------------------------------------


@pytest.mark.django_db
def test_patients_list_carries_plain_facts_and_filters_on_them(world):
    other = world.other_survivor
    link(other, world.clinician, "clinician")
    urgent_checkin(world)
    c = client_for(world.clinician)
    rows = {r["display_name"]: r for r in c.get("/api/v1/patients/").json()}
    facts = rows["survivor"]["facts"]
    assert facts["urgent_yes_last_7_days"] == 1 and facts["days_since_check_in"] == 0
    assert rows["other"]["facts"]["days_since_check_in"] is None

    assert [r["display_name"] for r in c.get("/api/v1/patients/?needs=urgent").json()] == ["survivor"]
    assert [r["display_name"] for r in c.get("/api/v1/patients/?needs=no_check_in").json()] == ["other"]
    assert c.get("/api/v1/patients/?needs=risky").status_code == 400


@pytest.mark.django_db
def test_facts_only_show_what_the_link_may_see_and_hold_no_judgement(world):
    world.clinician_link.scopes = ["view_plan"]
    world.clinician_link.save()
    rows = client_for(world.clinician).get("/api/v1/patients/").json()
    assert rows[0]["facts"] == {}
    world.clinician_link.scopes = sorted(["view_checkins", "view_meds", "view_readings"])
    world.clinician_link.save()
    body = client_for(world.clinician).get("/api/v1/patients/").json()
    assert judgement_words(set(keys(body))) == set()
