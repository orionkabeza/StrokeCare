"""Blood pressure, recovery plan, daily check-in, summary, reminders.

Owner: Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md
"""
from datetime import time, timedelta

import pytest
from django.utils import timezone

from apps.content.models import EmergencyContact
from apps.health.models import BPReading, PlanTask, RecoveryPlan, Reminder, TaskLog
from tests.conftest import client_for, make_user

ME = "/api/v1/patients/me"


def reading(client, base=ME, **over):
    body = {"systolic": 120, "diastolic": 80}
    body.update(over)
    return client.post(f"{base}/readings/", body, format="json")


# --- blood pressure ---------------------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "bad",
    [
        {"systolic": 1200},  # typing mistake
        {"systolic": 0},
        {"diastolic": 5},
        {"systolic": 80, "diastolic": 80},  # top must be above bottom
        {"systolic": 70, "diastolic": 90},
        {"pulse": 900},
        {"taken_at": "2999-01-01T00:00:00Z"},  # the future
        {"systolic": "abc"},
    ],
)
def test_bad_blood_pressure_input_is_rejected_with_plain_messages(world, bad):
    r = reading(client_for(world.survivor), **bad)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "validation_error" and r.json()["error"]["fields"]


@pytest.mark.django_db
def test_readings_come_back_newest_first_and_stay_numbers(world):
    c = client_for(world.survivor)
    now = timezone.now()
    for i, (s, d) in enumerate([(118, 76), (131, 84), (125, 80)]):
        reading(c, systolic=s, diastolic=d, taken_at=(now - timedelta(days=3 - i)).isoformat())
    rows = c.get(f"{ME}/readings/").json()["results"]
    assert [r["systolic"] for r in rows] == [125, 131, 118]
    assert all(isinstance(r["systolic"], int) and isinstance(r["diastolic"], int) for r in rows)


@pytest.mark.django_db
def test_reads_are_capped(world):
    c = client_for(world.survivor)
    assert c.get(f"{ME}/readings/?limit=100000").json()["count"] == 0  # accepted, then capped internally
    from apps.common.pagination import CappedLimitOffsetPagination

    assert CappedLimitOffsetPagination.max_limit == 200


@pytest.mark.django_db
def test_who_entered_a_reading_is_recorded_and_visible(world):
    reading(client_for(world.caregiver), base=f"/api/v1/patients/{world.survivor.id}", note="after a walk")
    reading(client_for(world.survivor))
    rows = {r["entered_by_role"]: r for r in client_for(world.clinician).get(f"/api/v1/patients/{world.survivor.id}/readings/").json()["results"]}
    assert rows["caregiver"]["entered_by_self"] is False and rows["survivor"]["entered_by_self"] is True


@pytest.mark.django_db
def test_a_caregiver_can_remove_only_what_they_entered(world):
    base = f"/api/v1/patients/{world.survivor.id}"
    mine = reading(client_for(world.caregiver), base=base).json()["id"]
    theirs = reading(client_for(world.survivor)).json()["id"]
    cg = client_for(world.caregiver)
    assert cg.delete(f"{base}/readings/{theirs}/").status_code == 403
    assert cg.delete(f"{base}/readings/{mine}/").status_code == 204
    assert client_for(world.survivor).delete(f"{ME}/readings/{theirs}/").status_code == 204


@pytest.mark.django_db
def test_one_patient_cannot_delete_anothers_reading(world):
    rid = reading(client_for(world.survivor)).json()["id"]
    assert client_for(world.other_survivor).delete(f"{ME}/readings/{rid}/").status_code == 404
    assert BPReading.objects.filter(id=rid).exists()


# --- recovery plan ----------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_clinician_writes_the_plan_and_survivor_ticks_it(world):
    base = f"/api/v1/patients/{world.survivor.id}"
    add = client_for(world.clinician).post(f"{base}/plan/tasks/", {"title": "Demo task", "instructions": "Fictional."}, format="json")
    assert add.status_code == 201
    tid = add.json()["id"]

    c = client_for(world.survivor)
    plan = c.get(f"{ME}/plan/").json()
    assert plan["has_plan"] and plan["tasks"][0]["done_today"] is False

    first = c.post(f"{ME}/plan/tasks/{tid}/log/", {"note": "felt fine"}, format="json")
    second = c.post(f"{ME}/plan/tasks/{tid}/log/", {}, format="json")
    assert (first.status_code, second.status_code) == (201, 200)  # ticking twice is harmless
    assert TaskLog.objects.filter(task_id=tid).count() == 1
    assert c.get(f"{ME}/plan/").json()["tasks"][0]["done_today"] is True

    assert c.delete(f"{ME}/plan/tasks/{tid}/log/").status_code == 204
    assert c.get(f"{ME}/plan/").json()["tasks"][0]["done_today"] is False


@pytest.mark.django_db
def test_cannot_tick_a_future_day_or_an_inactive_task(world):
    plan = RecoveryPlan.objects.create(patient=world.survivor)
    task = PlanTask.objects.create(plan=plan, title="Demo")
    c = client_for(world.survivor)
    tomorrow = (timezone.now() + timedelta(days=2)).date().isoformat()
    assert c.post(f"{ME}/plan/tasks/{task.id}/log/", {"date": tomorrow}, format="json").status_code == 400
    task.is_active = False
    task.save()
    assert c.post(f"{ME}/plan/tasks/{task.id}/log/", {}, format="json").status_code == 404


@pytest.mark.django_db
def test_clinician_can_retire_a_task_and_it_leaves_the_plan(world):
    base = f"/api/v1/patients/{world.survivor.id}"
    tid = client_for(world.clinician).post(f"{base}/plan/tasks/", {"title": "Demo"}, format="json").json()["id"]
    r = client_for(world.clinician).patch(f"{base}/plan/tasks/{tid}/", {"is_active": False}, format="json")
    assert r.status_code == 200
    assert client_for(world.survivor).get(f"{ME}/plan/").json()["tasks"] == []


@pytest.mark.django_db
def test_a_task_id_from_another_patients_plan_is_not_found(world):
    plan = RecoveryPlan.objects.create(patient=world.other_survivor)
    task = PlanTask.objects.create(plan=plan, title="Demo")
    assert client_for(world.survivor).post(f"{ME}/plan/tasks/{task.id}/log/", {}, format="json").status_code == 404
    base = f"/api/v1/patients/{world.survivor.id}"
    assert client_for(world.clinician).patch(f"{base}/plan/tasks/{task.id}/", {"title": "x"}, format="json").status_code == 404


@pytest.mark.django_db
def test_recovery_plans_are_only_for_survivors(world):
    from tests.conftest import link

    link(world.prevention, world.clinician, "clinician")
    r = client_for(world.clinician).post(f"/api/v1/patients/{world.prevention.id}/plan/tasks/", {"title": "x"}, format="json")
    assert r.status_code == 400
    assert client_for(world.prevention).get(f"{ME}/plan/").status_code == 404


# --- daily check-in ---------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_questions_are_data_and_ship_as_draft(world):
    qs = client_for(world.survivor).get("/api/v1/checkin-questions/").json()["results"]
    assert len(qs) == 4 and all(q["status"] == "draft" for q in qs)
    urgent = [q for q in qs if q["urgent_values"]]
    assert [q["code"] for q in urgent] == ["new-or-worse-symptoms"]


@pytest.mark.django_db
def test_an_urgent_answer_returns_emergency_guidance_without_inventing_numbers(world):
    r = client_for(world.survivor).post(
        f"{ME}/checkins/", {"answers": [{"question": "new-or-worse-symptoms", "value": True}]}, format="json"
    )
    assert r.status_code == 201
    guidance = r.json()["emergency_guidance"]
    assert "emergency services" in guidance["message"] and "Do not wait" in guidance["message"]
    assert guidance["contacts"] == [] and guidance["contacts_available"] is False


@pytest.mark.django_db
def test_only_verified_contacts_are_ever_returned(world):
    EmergencyContact.objects.create(region="Demo", label="Unverified line", kind="helpline", phone="000")
    EmergencyContact.objects.create(
        region="Demo", label="Verified line", kind="helpline", phone="111",
        verified_by_name="Demo Verifier", verified_at=timezone.now(),
    )  # fmt: skip
    r = client_for(world.survivor).post(
        f"{ME}/checkins/", {"answers": [{"question": "new-or-worse-symptoms", "value": True}]}, format="json"
    )
    labels = [c["label"] for c in r.json()["emergency_guidance"]["contacts"]]
    assert labels == ["Verified line"]


@pytest.mark.django_db
def test_no_guidance_when_no_urgent_answer(world):
    r = client_for(world.survivor).post(
        f"{ME}/checkins/", {"answers": [{"question": "new-or-worse-symptoms", "value": False}]}, format="json"
    )
    assert r.json()["emergency_guidance"] is None and r.json()["urgent_question_answered_yes"] is False


@pytest.mark.django_db
def test_every_question_can_be_skipped_and_a_second_submit_replaces_the_first(world):
    c = client_for(world.survivor)
    c.post(f"{ME}/checkins/", {"answers": [{"question": "new-joint-pain", "skipped": True}]}, format="json")
    c.post(f"{ME}/checkins/", {"answers": [{"question": "new-joint-pain", "value": True}]}, format="json")
    rows = c.get(f"{ME}/checkins/").json()["results"]
    assert len(rows) == 1 and rows[0]["answers"] == [{"question": "new-joint-pain", "value": True, "skipped": False}]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "answer",
    [
        {"question": "new-joint-pain", "value": "yes"},  # yes/no must be true or false
        {"question": "feeling-vs-yesterday", "value": "fantastic"},  # not one of the choices
        {"question": "no-such-question", "value": True},
    ],
)
def test_invalid_answers_are_rejected(world, answer):
    assert client_for(world.survivor).post(f"{ME}/checkins/", {"answers": [answer]}, format="json").status_code == 400


@pytest.mark.django_db
def test_duplicate_questions_and_future_dates_are_rejected(world):
    c = client_for(world.survivor)
    twice = {"answers": [{"question": "new-joint-pain", "value": True}, {"question": "new-joint-pain", "value": False}]}
    assert c.post(f"{ME}/checkins/", twice, format="json").status_code == 400
    future = {"date": (timezone.now() + timedelta(days=3)).date().isoformat(), "answers": [{"question": "new-joint-pain", "value": True}]}
    assert c.post(f"{ME}/checkins/", future, format="json").status_code == 400


@pytest.mark.django_db
def test_questions_are_served_in_kinyarwanda_and_fall_back_to_english_when_missing(world):
    from apps.health.models import CheckInQuestion

    r = client_for(world.survivor).get("/api/v1/checkin-questions/?lang=rw").json()["results"][0]
    assert r["locale_served"] == "rw" and r["choices"][0]["label"] == "Neza kurusha ejo"
    CheckInQuestion.objects.filter(code="feeling-vs-yesterday").update(prompt={"en": "English only"})
    r = client_for(world.survivor).get("/api/v1/checkin-questions/?lang=rw").json()["results"][0]
    assert r["locale_served"] == "en" and r["prompt"] == "English only"


# --- summary ----------------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_summary_counts_and_averages_are_correct(world):
    c = client_for(world.survivor)
    now = timezone.now()
    reading(c, systolic=120, diastolic=80, taken_at=(now - timedelta(hours=2)).isoformat(), note="felt calm")
    reading(c, systolic=140, diastolic=90, taken_at=(now - timedelta(hours=1)).isoformat())
    reading(c, systolic=200, diastolic=100, taken_at=(now - timedelta(days=20)).isoformat())  # outside 7 days
    plan = RecoveryPlan.objects.create(patient=world.survivor)
    task = PlanTask.objects.create(plan=plan, title="Demo")
    c.post(f"{ME}/plan/tasks/{task.id}/log/", {"note": "done slowly"}, format="json")
    c.post(
        f"{ME}/checkins/",
        {"answers": [{"question": "new-or-worse-symptoms", "value": True}, {"question": "new-joint-pain", "skipped": True}]},
        format="json",
    )

    body = client_for(world.clinician).get(f"/api/v1/patients/{world.survivor.id}/summary/").json()
    assert body["period"]["days"] == 7
    assert body["blood_pressure"] == {
        "readings": 2, "days_with_a_reading": body["blood_pressure"]["days_with_a_reading"],
        "average_systolic": 130.0, "average_diastolic": 85.0, "unit": "mmHg",
    }  # fmt: skip
    assert body["recovery_tasks"]["ticks"] == 1 and body["recovery_tasks"]["active_tasks"] == 1
    ci = body["daily_check_ins"]
    assert ci["submitted"] == 1 and ci["questions_skipped"] == 1 and ci["days_urgent_question_answered_yes"] == 1
    assert {n["text"] for n in body["notes_in_their_own_words"]} == {"felt calm", "done slowly"}


@pytest.mark.django_db
def test_summary_with_no_data_is_empty_not_an_error(world):
    body = client_for(world.survivor).get(f"{ME}/summary/").json()
    assert body["blood_pressure"]["readings"] == 0 and body["blood_pressure"]["average_systolic"] is None


@pytest.mark.django_db
@pytest.mark.parametrize("days", ["0", "31", "x", "-1"])
def test_summary_period_is_limited(world, days):
    assert client_for(world.survivor).get(f"{ME}/summary/?days={days}").status_code == 400


# --- reminders --------------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_reminders_are_private_and_upcoming_is_computed_in_the_users_time_zone(world):
    c = client_for(world.survivor)
    r = c.post("/api/v1/me/reminders/", {"kind": "blood_pressure", "time_of_day": "08:00", "days_of_week": [0, 2, 4]}, format="json")
    assert r.status_code == 201 and r.json()["channel"] == "in_app"
    up = c.get("/api/v1/me/reminders/upcoming/").json()["results"]
    assert len(up) == 1 and up[0]["next_at"].endswith("+02:00")  # Africa/Kigali
    assert client_for(world.other_survivor).get("/api/v1/me/reminders/").json()["results"] == []
    assert client_for(world.other_survivor).delete(f"/api/v1/me/reminders/{r.json()['id']}/").status_code == 404
    assert c.post("/api/v1/me/reminders/", {"kind": "tasks", "time_of_day": "09:00", "days_of_week": [9]}, format="json").status_code == 400
    assert client_for(world.clinician).get("/api/v1/me/reminders/").status_code == 403
    assert Reminder.objects.count() == 1
