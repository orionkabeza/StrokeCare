"""Medicines, questions for the next visit, plan templates.

Owner: Aubin Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md
"""
from datetime import timedelta

import pytest

from apps.accounts.models import Role
from apps.health.models import Medication, PlanTask, RecoveryPlan
from apps.health.services import local_today
from tests.conftest import client_for, link, make_user

ME = "/api/v1/patients/me"


def add_med(world, **over):
    body = {"name": "Demo medicine", "dose": "one tablet", "times": ["08:00", "20:00"]}
    body.update(over)
    return client_for(world.clinician).post(f"/api/v1/patients/{world.survivor.id}/medications/", body, format="json")


# --- medicines ------------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_clinician_writes_the_list_and_the_patient_ticks_doses(world):
    med = add_med(world)
    assert med.status_code == 201
    mid = med.json()["id"]
    c = client_for(world.survivor)
    today = c.get(f"{ME}/medications/").json()
    assert today["doses_due"] == 2 and today["doses_marked_taken"] == 0
    assert [s["time"] for s in today["medications"][0]["doses_on_day"]] == ["08:00", "20:00"]

    first = c.post(f"{ME}/medications/{mid}/doses/", {"time": "08:00"}, format="json")
    again = c.post(f"{ME}/medications/{mid}/doses/", {"time": "08:00"}, format="json")
    assert (first.status_code, again.status_code) == (201, 200)  # marking twice is harmless
    assert c.get(f"{ME}/medications/").json()["doses_marked_taken"] == 1

    assert c.delete(f"{ME}/medications/{mid}/doses/?time=08:00").status_code == 204
    assert c.get(f"{ME}/medications/").json()["doses_marked_taken"] == 0


@pytest.mark.django_db
def test_only_a_clinician_can_write_or_change_the_medicine_list(world):
    body = {"name": "x", "times": ["08:00"]}
    assert client_for(world.survivor).post(f"{ME}/medications/", body, format="json").status_code == 403
    base = f"/api/v1/patients/{world.survivor.id}"
    assert client_for(world.caregiver).post(f"{base}/medications/", body, format="json").status_code == 403
    mid = add_med(world).json()["id"]
    assert client_for(world.caregiver).patch(f"{base}/medications/{mid}/", {"is_active": False}, format="json").status_code == 403
    assert client_for(world.clinician).patch(f"{base}/medications/{mid}/", {"is_active": False}, format="json").status_code == 200
    assert client_for(world.survivor).get(f"{ME}/medications/").json()["medications"] == []


@pytest.mark.django_db
def test_a_caregiver_can_mark_a_dose_for_the_patient(world):
    mid = add_med(world).json()["id"]
    r = client_for(world.caregiver).post(
        f"/api/v1/patients/{world.survivor.id}/medications/{mid}/doses/", {"time": "20:00"}, format="json"
    )
    assert r.status_code == 201
    slot = client_for(world.survivor).get(f"{ME}/medications/").json()["medications"][0]["doses_on_day"][1]
    assert slot["taken"] is True and slot["entered_by_role"] == "caregiver"


@pytest.mark.django_db
def test_dose_marks_are_checked_against_the_schedule(world):
    mid = add_med(world).json()["id"]
    c = client_for(world.survivor)
    today = local_today(world.survivor)
    assert c.post(f"{ME}/medications/{mid}/doses/", {"time": "12:00"}, format="json").status_code == 400  # not scheduled
    future = (today + timedelta(days=1)).isoformat()
    assert c.post(f"{ME}/medications/{mid}/doses/", {"time": "08:00", "date": future}, format="json").status_code == 400
    Medication.objects.filter(id=mid).update(start_date=today - timedelta(days=30))
    old = (today - timedelta(days=8)).isoformat()
    assert c.post(f"{ME}/medications/{mid}/doses/", {"time": "08:00", "date": old}, format="json").status_code == 400
    week = (today - timedelta(days=7)).isoformat()
    assert c.post(f"{ME}/medications/{mid}/doses/", {"time": "08:00", "date": week}, format="json").status_code == 201


@pytest.mark.django_db
def test_days_of_week_and_end_date_limit_the_schedule(world):
    today = local_today(world.survivor)
    other_day = (today.weekday() + 1) % 7
    add_med(world, days_of_week=[other_day])
    add_med(world, name="Ended", start_date=(today - timedelta(days=5)).isoformat(), end_date=(today - timedelta(days=1)).isoformat())
    assert client_for(world.survivor).get(f"{ME}/medications/").json()["doses_due"] == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    "bad", [{"times": []}, {"days_of_week": [9]}, {"start_date": "2026-11-10", "end_date": "2026-11-01"}, {"name": ""}]
)
def test_bad_medicine_input_is_rejected(world, bad):
    assert add_med(world, **bad).status_code == 400


@pytest.mark.django_db
def test_another_patients_medicine_is_not_found(world):
    other_med = Medication.objects.create(
        patient=world.other_survivor, name="x", times=["08:00"], start_date=local_today(world.other_survivor)
    )
    r = client_for(world.survivor).post(f"{ME}/medications/{other_med.id}/doses/", {"time": "08:00"}, format="json")
    assert r.status_code == 404


@pytest.mark.django_db
def test_summary_counts_doses(world):
    mid = add_med(world).json()["id"]
    client_for(world.survivor).post(f"{ME}/medications/{mid}/doses/", {"time": "08:00"}, format="json")
    meds = client_for(world.clinician).get(f"/api/v1/patients/{world.survivor.id}/summary/").json()["medicines"]
    assert meds == {"active": 1, "doses_due": 2, "doses_marked_taken": 1}


# --- questions for the next visit -------------------------------------------------------------------------


@pytest.mark.django_db
def test_visit_questions_flow(world):
    base = f"/api/v1/patients/{world.survivor.id}/visit-questions/"
    mine = client_for(world.survivor).post(f"{ME}/visit-questions/", {"text": "Can I start walking outside?"}, format="json")
    theirs = client_for(world.caregiver).post(base, {"text": "Is the new tiredness expected?"}, format="json")
    assert mine.status_code == theirs.status_code == 201
    assert client_for(world.clinician).post(base, {"text": "x"}, format="json").status_code == 403  # clinicians answer, not ask

    rows = client_for(world.clinician).get(base).json()["results"]
    assert len(rows) == 2 and not any(r["discussed"] for r in rows)
    done = client_for(world.clinician).patch(f"{base}{mine.json()['id']}/", {"discussed": True}, format="json")
    assert done.status_code == 200 and done.json()["discussed"] is True
    open_rows = client_for(world.survivor).get(f"{ME}/visit-questions/?open=1").json()["results"]
    assert [r["text"] for r in open_rows] == ["Is the new tiredness expected?"]

    assert client_for(world.caregiver).delete(f"{base}{mine.json()['id']}/").status_code == 403  # not theirs
    assert client_for(world.survivor).delete(f"{ME}/visit-questions/{theirs.json()['id']}/").status_code == 204


@pytest.mark.django_db
@pytest.mark.parametrize("text", ["", "   ", "x" * 501])
def test_visit_question_text_is_checked(world, text):
    assert client_for(world.survivor).post(f"{ME}/visit-questions/", {"text": text}, format="json").status_code == 400


@pytest.mark.django_db
def test_summary_and_export_include_the_new_records(world):
    client_for(world.survivor).post(f"{ME}/visit-questions/", {"text": "Demo question"}, format="json")
    add_med(world)
    assert client_for(world.clinician).get(f"/api/v1/patients/{world.survivor.id}/summary/").json()["visit_questions_open"] == 1
    export = client_for(world.survivor).get("/api/v1/me/export/").json()["health"]
    assert export["visit_questions"][0]["text"] == "Demo question" and export["medicines"][0]["name"] == "Demo medicine"


# --- plan templates ---------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_clinician_templates_are_private_and_copy_into_a_plan(world):
    c = client_for(world.clinician)
    tpl = c.post("/api/v1/plan-templates/", {"name": "Week one", "tasks": [{"title": "Demo A"}, {"title": "Demo B"}]}, format="json")
    assert tpl.status_code == 201
    assert client_for(world.clinician_unlinked).get("/api/v1/plan-templates/").json()["results"] == []

    plan = RecoveryPlan.objects.create(patient=world.survivor)
    PlanTask.objects.create(plan=plan, title="Existing", order=5)
    base = f"/api/v1/patients/{world.survivor.id}/plan/apply-template/"
    r = c.post(base, {"template": tpl.json()["id"]}, format="json")
    assert r.status_code == 201 and r.json() == {"added": 2}
    titles = [t["title"] for t in client_for(world.survivor).get(f"{ME}/plan/").json()["tasks"]]
    assert titles == ["Existing", "Demo A", "Demo B"]


@pytest.mark.django_db
def test_templates_need_a_verified_clinician_and_their_own_template(world):
    unverified = make_user("u@test.org", Role.CLINICIAN, verified=False)
    assert client_for(unverified).get("/api/v1/plan-templates/").status_code == 403
    assert client_for(world.survivor).get("/api/v1/plan-templates/").status_code == 403
    tpl = client_for(world.clinician_unlinked).post("/api/v1/plan-templates/", {"name": "x", "tasks": [{"title": "y"}]}, format="json")
    r = client_for(world.clinician).post(
        f"/api/v1/patients/{world.survivor.id}/plan/apply-template/", {"template": tpl.json()["id"]}, format="json"
    )
    assert r.status_code == 400  # someone else's template
    assert client_for(world.clinician).post("/api/v1/plan-templates/", {"name": "x", "tasks": []}, format="json").status_code == 400


@pytest.mark.django_db
def test_templates_only_apply_to_survivors_and_only_by_the_plan_writer(world):
    tpl = client_for(world.clinician).post("/api/v1/plan-templates/", {"name": "x", "tasks": [{"title": "y"}]}, format="json").json()
    link(world.prevention, world.clinician, "clinician")
    r = client_for(world.clinician).post(f"/api/v1/patients/{world.prevention.id}/plan/apply-template/", {"template": tpl["id"]}, format="json")
    assert r.status_code == 400
    r = client_for(world.caregiver).post(f"/api/v1/patients/{world.survivor.id}/plan/apply-template/", {"template": tpl["id"]}, format="json")
    assert r.status_code == 403
