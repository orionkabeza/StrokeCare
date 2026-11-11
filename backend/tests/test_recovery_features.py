"""Goals, recovery stages, movement log, personal phrases, progress dashboard, appointment reminders, bulk doses,
the doctor's home page and "my care team".

Owner: Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md
"""
from datetime import time, timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import Role
from apps.care import scopes as sc
from apps.care.alerts import refresh_for
from apps.care.models import Alert
from apps.family.models import CareEvent
from apps.health.models import Medication, PlanTask, RecoveryPlan
from apps.health.services import local_today
from apps.recovery.models import CarePhase
from tests.conftest import client_for, link, make_user

ME = "/api/v1/patients/me"


def theirs(world):
    return f"/api/v1/patients/{world.survivor.id}"


# --- Movement log -----------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_movement_log_records_plain_facts_and_who_entered_them(world):
    c = client_for(world.survivor)
    r = c.post(f"{ME}/mobility/", {"kind": "walking", "minutes": 15, "help": "with_aid", "note": "To the gate"}, format="json")
    assert r.status_code == 201 and r.json()["entered_by_role"] == "survivor"
    r = client_for(world.caregiver).post(f"{theirs(world)}/mobility/", {"kind": "standing", "minutes": 5}, format="json")
    assert r.status_code == 201 and r.json()["entered_by_role"] == "caregiver"
    rows = c.get(f"{ME}/mobility/").json()["results"]
    assert {x["kind"] for x in rows} == {"walking", "standing"}
    assert not {"score", "rating", "level"} & set(rows[0])


@pytest.mark.django_db
def test_movement_log_rejects_nonsense(world):
    c = client_for(world.survivor)
    assert c.post(f"{ME}/mobility/", {"kind": "flying"}, format="json").status_code == 400
    assert c.post(f"{ME}/mobility/", {"kind": "walking", "minutes": 0}, format="json").status_code == 400
    assert c.post(f"{ME}/mobility/", {"kind": "walking", "minutes": 601}, format="json").status_code == 400
    assert c.post(f"{ME}/mobility/", {"kind": "walking", "help": "carried"}, format="json").status_code == 400
    tomorrow = (local_today(world.survivor) + timedelta(days=1)).isoformat()
    assert c.post(f"{ME}/mobility/", {"kind": "walking", "date": tomorrow}, format="json").status_code == 400
    old = (local_today(world.survivor) - timedelta(days=31)).isoformat()
    assert c.post(f"{ME}/mobility/", {"kind": "walking", "date": old}, format="json").status_code == 400


@pytest.mark.django_db
def test_movement_retry_from_an_offline_phone_is_saved_once(world):
    c = client_for(world.survivor)
    body = {"kind": "walking", "minutes": 10, "client_id": "5b3c9a1e-6f2d-4a7b-8c1d-2e3f4a5b6c7d"}
    assert c.post(f"{ME}/mobility/", body, format="json").status_code == 201
    assert c.post(f"{ME}/mobility/", body, format="json").status_code == 200
    assert len(c.get(f"{ME}/mobility/").json()["results"]) == 1


@pytest.mark.django_db
def test_a_helper_can_remove_only_their_own_movement_entry(world):
    cg = client_for(world.caregiver)
    mine = cg.post(f"{theirs(world)}/mobility/", {"kind": "walking"}, format="json").json()["id"]
    own = client_for(world.survivor).post(f"{ME}/mobility/", {"kind": "standing"}, format="json").json()["id"]
    assert cg.delete(f"{theirs(world)}/mobility/{own}/").status_code == 403
    assert cg.delete(f"{theirs(world)}/mobility/{mine}/").status_code == 204
    assert client_for(world.survivor).delete(f"{ME}/mobility/{own}/").status_code == 204


# --- Goals ------------------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_goals_are_the_persons_own_words_and_can_be_ticked_by_anyone_who_can_read_them(world):
    c = client_for(world.survivor)
    r = c.post(f"{ME}/goals/", {"text": "Hold a cup with my right hand", "target_date": "2026-12-25"}, format="json")
    assert r.status_code == 201 and r.json()["done"] is False
    gid = r.json()["id"]
    assert client_for(world.clinician).post(f"{theirs(world)}/goals/", {"text": "x"}, format="json").status_code == 403
    assert client_for(world.clinician).patch(f"{theirs(world)}/goals/{gid}/", {"done": True}, format="json").json()["done"]
    assert c.patch(f"{ME}/goals/{gid}/", {"done": False}, format="json").json()["done"] is False
    assert c.post(f"{ME}/goals/", {"text": "   "}, format="json").status_code == 400
    assert c.post(f"{ME}/goals/", {"text": "x" * 201}, format="json").status_code == 400
    assert c.post(f"{ME}/goals/", {"text": "ok", "target_date": "soon"}, format="json").status_code == 400
    assert c.patch(f"{ME}/goals/{gid}/", {"done": "yes"}, format="json").status_code == 400


# --- Recovery stages (written by the clinician) -----------------------------------------------------------


@pytest.mark.django_db
def test_only_the_clinician_writes_stages_and_the_current_one_is_marked(world):
    today = local_today(world.survivor)
    clin = client_for(world.clinician)
    past = clin.post(f"{theirs(world)}/phases/", {"name": "Early weeks", "starts_on": str(today - timedelta(days=60)),
                     "ends_on": str(today - timedelta(days=1)), "care_needed": "Help with washing and dressing"}, format="json")
    now = clin.post(f"{theirs(world)}/phases/", {"name": "Building up", "starts_on": str(today - timedelta(days=1))}, format="json")
    assert past.status_code == 201 and now.status_code == 201
    rows = client_for(world.survivor).get(f"{ME}/phases/").json()["results"]
    assert {r["name"]: r["is_current"] for r in rows} == {"Early weeks": False, "Building up": True}
    for who in (world.survivor, world.caregiver):
        url = f"{ME}/phases/" if who == world.survivor else f"{theirs(world)}/phases/"
        assert client_for(who).post(url, {"name": "Mine", "starts_on": str(today)}, format="json").status_code == 403
    bad = clin.post(f"{theirs(world)}/phases/", {"name": "Backwards", "starts_on": str(today), "ends_on": str(today - timedelta(days=2))}, format="json")
    assert bad.status_code == 400
    assert clin.post(f"{theirs(world)}/phases/", {"name": "  ", "starts_on": str(today)}, format="json").status_code == 400


@pytest.mark.django_db
def test_database_refuses_a_stage_that_ends_before_it_starts(world):
    from django.db import IntegrityError, transaction

    today = local_today(world.survivor)
    with pytest.raises(IntegrityError), transaction.atomic():
        CarePhase.objects.create(patient=world.survivor, name="x", starts_on=today, ends_on=today - timedelta(days=1))


@pytest.mark.django_db
def test_a_patient_cannot_edit_or_delete_a_stage_and_strangers_get_404(world):
    today = local_today(world.survivor)
    p = CarePhase.objects.create(patient=world.survivor, name="Stage", starts_on=today, created_by=world.clinician)
    assert client_for(world.survivor).patch(f"{ME}/phases/{p.id}/", {"name": "Changed"}, format="json").status_code == 403
    assert client_for(world.survivor).delete(f"{ME}/phases/{p.id}/").status_code == 403
    assert client_for(world.clinician_unlinked).patch(f"{theirs(world)}/phases/{p.id}/", {"name": "x"}, format="json").status_code == 404
    assert client_for(world.clinician).patch(f"{theirs(world)}/phases/{p.id}/", {"name": "Renamed"}, format="json").json()["name"] == "Renamed"
    assert client_for(world.clinician).delete(f"{theirs(world)}/phases/{p.id}/").status_code == 204


# --- Personal phrases for the talk board ------------------------------------------------------------------


@pytest.mark.django_db
def test_personal_phrases(world):
    c = client_for(world.survivor)
    assert c.post(f"{ME}/phrases/", {"text": "Ndashaka icyayi", "icon": "drop"}, format="json").status_code == 201
    mine = client_for(world.caregiver).post(f"{theirs(world)}/phrases/", {"text": "My glasses, please"}, format="json")
    assert mine.status_code == 201 and mine.json()["icon"] == "chat-circle"
    assert c.post(f"{ME}/phrases/", {"text": "x", "icon": "rocket"}, format="json").status_code == 400
    assert c.post(f"{ME}/phrases/", {"text": ""}, format="json").status_code == 400
    assert c.post(f"{ME}/phrases/", {"text": "y" * 81}, format="json").status_code == 400
    assert len(c.get(f"{ME}/phrases/").json()["results"]) == 2
    first = c.get(f"{ME}/phrases/").json()["results"][0]["id"]
    assert client_for(world.caregiver).delete(f"{theirs(world)}/phrases/{first}/").status_code == 403
    assert c.delete(f"{ME}/phrases/{first}/").status_code == 204


@pytest.mark.django_db
def test_personal_phrases_have_a_limit(world):
    c = client_for(world.survivor)
    for i in range(30):
        assert c.post(f"{ME}/phrases/", {"text": f"Phrase {i}"}, format="json").status_code == 201
    assert c.post(f"{ME}/phrases/", {"text": "One too many"}, format="json").status_code == 400


# --- Progress dashboard -----------------------------------------------------------------------------------


@pytest.mark.django_db
def test_progress_counts_what_was_entered_and_nothing_else(world):
    today = local_today(world.survivor)
    plan = RecoveryPlan.objects.create(patient=world.survivor, created_by=world.clinician)
    t1 = PlanTask.objects.create(plan=plan, title="One")
    PlanTask.objects.create(plan=plan, title="Two")
    med = Medication.objects.create(patient=world.survivor, name="Demo", times=[time(8), time(20)], start_date=today)
    c = client_for(world.survivor)
    c.post(f"{ME}/plan/tasks/{t1.id}/log/", {}, format="json")
    c.post(f"{ME}/medications/{med.id}/doses/", {"time": "08:00"}, format="json")
    c.post(f"{ME}/readings/", {"systolic": 120, "diastolic": 80}, format="json")
    c.post(f"{ME}/checkins/", {"answers": [{"question": "new-joint-pain", "value": False}]}, format="json")
    c.post(f"{ME}/mobility/", {"kind": "walking", "minutes": 20}, format="json")
    c.post(f"{ME}/mobility/", {"kind": "stretching", "minutes": 10}, format="json")
    data = c.get(f"{ME}/progress/?days=7").json()
    assert len(data["days"]) == 7 and data["period"]["to"] == str(today)
    last = data["days"][-1]
    assert last["date"] == str(today)
    assert (last["tasks_done"], last["tasks_total"]) == (1, 2)
    assert (last["doses_taken"], last["doses_due"]) == (1, 2)
    assert last["checked_in"] is True and last["bp_readings"] == 1
    assert (last["mobility_sessions"], last["mobility_minutes"]) == (2, 30)
    assert data["days"][0]["mobility_sessions"] == 0  # an empty day is just empty, never a "miss"
    assert data["days"][0]["tasks_total"] == 0  # the tasks did not exist yet, so that day cannot count them as undone
    assert data["totals"]["mobility_minutes"] == 30 and data["totals"]["check_ins"] == 1
    assert "not a score" in data["note"]


@pytest.mark.django_db
def test_progress_has_no_percentages_streaks_or_targets(world):
    from tests.test_safety import judgement_words, keys

    data = client_for(world.survivor).get(f"{ME}/progress/?days=30").json()
    names = set(keys(data))
    assert judgement_words(names) == set()
    assert not {n for n in names if any(w in n for w in ("percent", "streak", "target", "goal_met", "rate", "average"))}


@pytest.mark.django_db
def test_progress_days_must_be_sensible(world):
    c = client_for(world.survivor)
    for bad in ("0", "31", "abc"):
        assert c.get(f"{ME}/progress/?days={bad}").status_code == 400


@pytest.mark.django_db
def test_progress_shows_the_current_stage(world):
    today = local_today(world.survivor)
    CarePhase.objects.create(patient=world.survivor, name="Building up", starts_on=today, created_by=world.clinician)
    data = client_for(world.caregiver).get(f"{theirs(world)}/progress/").json()
    assert data["current_phase"]["name"] == "Building up"


@pytest.mark.django_db
def test_caregiver_without_the_summary_scope_cannot_see_progress(world):
    link_scopes = set(sc.CAREGIVER_ALLOWED) - {sc.VIEW_SUMMARY}
    world.caregiver_link.scopes = sorted(link_scopes)
    world.caregiver_link.save()
    assert client_for(world.caregiver).get(f"{theirs(world)}/progress/").status_code == 403


# --- Appointments and reminders ---------------------------------------------------------------------------


def event_body(hours_from_now, remind=None, title="Physiotherapy"):
    body = {"title": title, "kind": "therapy", "starts_at": (timezone.now() + timedelta(hours=hours_from_now)).isoformat()}
    if remind is not None:
        body["remind_minutes_before"] = remind
    return body


@pytest.mark.django_db
def test_an_appointment_can_carry_a_reminder_lead_time(world):
    c = client_for(world.survivor)
    r = c.post(f"{ME}/calendar/", event_body(30, remind=60), format="json")
    assert r.status_code == 201 and r.json()["remind_minutes_before"] == 60
    assert c.post(f"{ME}/calendar/", event_body(30, remind=7), format="json").status_code == 400
    assert c.post(f"{ME}/calendar/", event_body(30), format="json").json()["remind_minutes_before"] is None


@pytest.mark.django_db
def test_upcoming_reminders_include_appointments(world):
    c = client_for(world.survivor)
    c.post(f"{ME}/calendar/", event_body(5, remind=30, title="Clinic visit"), format="json")
    rows = c.get("/api/v1/me/reminders/upcoming/").json()["results"]
    appt = [r for r in rows if r["kind"] == "appointment"]
    assert len(appt) == 1 and appt[0]["title"] == "Clinic visit" and appt[0]["remind_minutes_before"] == 30


@pytest.mark.django_db
def test_medicine_and_movement_reminders_can_be_created(world):
    c = client_for(world.survivor)
    for kind in ("medicines", "mobility"):
        r = c.post("/api/v1/me/reminders/", {"kind": kind, "time_of_day": "08:00"}, format="json")
        assert r.status_code == 201, r.content


@pytest.mark.django_db
def test_caregiver_gets_one_alert_when_an_appointment_is_inside_its_reminder_window(world):
    c = client_for(world.survivor)
    c.post(f"{ME}/calendar/", event_body(1, remind=120, title="Eye clinic"), format="json")  # inside the window
    c.post(f"{ME}/calendar/", event_body(30, remind=60, title="Far away"), format="json")  # not yet
    c.post(f"{ME}/calendar/", event_body(1, title="No reminder asked"), format="json")
    assert refresh_for(world.caregiver) == 1
    assert refresh_for(world.caregiver) == 0  # opening the app twice never repeats an alert
    alert = Alert.objects.get(recipient=world.caregiver, kind="appointment_soon")
    assert alert.detail["title"] == "Eye clinic"


@pytest.mark.django_db
def test_a_caregiver_without_the_calendar_scope_gets_no_appointment_alert(world):
    world.caregiver_link.scopes = sorted(set(sc.CAREGIVER_ALLOWED) - {sc.VIEW_CALENDAR})
    world.caregiver_link.save()
    client_for(world.survivor).post(f"{ME}/calendar/", event_body(1, remind=120), format="json")
    refresh_for(world.caregiver)
    assert not Alert.objects.filter(kind="appointment_soon").exists()


# --- Bulk dose marking ------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_mark_several_doses_at_once_is_idempotent_and_all_or_nothing(world):
    today = local_today(world.survivor)
    a = Medication.objects.create(patient=world.survivor, name="A", times=[time(8)], start_date=today)
    b = Medication.objects.create(patient=world.survivor, name="B", times=[time(8), time(20)], start_date=today)
    c = client_for(world.survivor)
    good = {"doses": [{"medication": str(a.id), "time": "08:00"}, {"medication": str(b.id), "time": "08:00"}]}
    r = c.post(f"{ME}/medications/doses/bulk/", good, format="json")
    assert r.status_code == 200 and r.json()["newly_marked"] == 2
    assert c.post(f"{ME}/medications/doses/bulk/", good, format="json").json()["newly_marked"] == 0
    bad = {"doses": [{"medication": str(b.id), "time": "20:00"}, {"medication": str(a.id), "time": "09:30"}]}
    assert c.post(f"{ME}/medications/doses/bulk/", bad, format="json").status_code == 400
    assert not b.doses.filter(time=time(20)).exists()  # the first, valid dose was not kept either
    assert c.post(f"{ME}/medications/doses/bulk/", {"doses": []}, format="json").status_code == 400


@pytest.mark.django_db
def test_bulk_doses_cannot_touch_another_persons_medicine(world):
    today = local_today(world.survivor)
    theirs_med = Medication.objects.create(patient=world.other_survivor, name="Not mine", times=[time(8)], start_date=today)
    r = client_for(world.survivor).post(
        f"{ME}/medications/doses/bulk/", {"doses": [{"medication": str(theirs_med.id), "time": "08:00"}]}, format="json"
    )
    assert r.status_code == 400 and not theirs_med.doses.exists()


# --- The doctor's home page -------------------------------------------------------------------------------


@pytest.mark.django_db
def test_doctor_overview_is_for_clinicians_only(world):
    for who in (world.caregiver, world.chw, world.survivor, world.admin):
        assert client_for(who).get("/api/v1/doctor/overview/").status_code == 403
    assert client_for(None).get("/api/v1/doctor/overview/").status_code == 401
    assert client_for(world.clinician).get("/api/v1/doctor/overview/").status_code == 200


@pytest.mark.django_db
def test_doctor_overview_lists_facts_in_name_order_and_todays_appointments(world):
    ann = make_user("ann@test.org", Role.SURVIVOR, name="Ann")
    link(ann, world.clinician, "clinician")
    c = client_for(world.survivor)
    c.post(f"{ME}/checkins/", {"answers": [{"question": "new-or-worse-symptoms", "value": True}]}, format="json")
    c.post(f"{ME}/calendar/", event_body(1, title="Clinic visit"), format="json")
    ann_c = client_for(ann)
    ann_c.post("/api/v1/patients/me/checkins/", {"answers": [{"question": "new-or-worse-symptoms", "value": True}]}, format="json")
    data = client_for(world.clinician).get("/api/v1/doctor/overview/").json()
    assert data["patients_total"] == 2
    assert data["counts"]["urgent"] == 2
    names = [p["display_name"] for p in data["needs_a_look"]]
    assert names == sorted(names)  # alphabetical, never ranked by risk
    assert all(p["reasons"] for p in data["needs_a_look"])
    soon = data["appointments_today"] + data["appointments_next_days"]
    assert [e["title"] for e in soon] == ["Clinic visit"]
    from tests.test_safety import judgement_words, keys

    assert judgement_words(set(keys(data))) == set()
    assert "no risk score" in data["note"]


@pytest.mark.django_db
def test_doctor_overview_leaves_out_people_who_withdrew_consent_or_whose_link_ended(world):
    gone = make_user("gone@test.org", Role.SURVIVOR, consent=False)
    link(gone, world.clinician, "clinician")
    ended = make_user("ended@test.org", Role.SURVIVOR)
    lk = link(ended, world.clinician, "clinician")
    lk.status = "revoked"
    lk.save()
    data = client_for(world.clinician).get("/api/v1/doctor/overview/").json()
    assert data["patients_total"] == 1


@pytest.mark.django_db
def test_doctor_overview_respects_the_scopes_the_patient_allowed(world):
    world.clinician_link.scopes = sorted(set(sc.CLINICIAN_ALLOWED) - {sc.VIEW_CALENDAR, sc.MESSAGE})
    world.clinician_link.save()
    client_for(world.survivor).post(f"{ME}/calendar/", event_body(1), format="json")
    data = client_for(world.clinician).get("/api/v1/doctor/overview/").json()
    assert data["appointments_today"] == [] and data["appointments_next_days"] == []


# --- My care team -----------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_my_care_team_shows_who_may_see_my_record_my_stage_and_my_next_appointment(world):
    today = local_today(world.survivor)
    CarePhase.objects.create(patient=world.survivor, name="Building up", starts_on=today, created_by=world.clinician)
    c = client_for(world.survivor)
    c.post(f"{ME}/calendar/", event_body(48, title="Later"), format="json")
    c.post(f"{ME}/calendar/", event_body(2, title="Sooner"), format="json")
    data = c.get("/api/v1/me/care-team/").json()
    assert {m["relation"] for m in data["team"]} == {"clinician", "caregiver", "chw"}
    assert data["current_phase"]["name"] == "Building up"
    assert data["next_appointment"]["title"] == "Sooner"


@pytest.mark.django_db
def test_my_care_team_leaves_out_unverified_clinicians_and_ended_links(world):
    fake = make_user("fake@test.org", Role.CLINICIAN, verified=False)
    link(world.survivor, fake, "clinician")
    world.chw_link.status = "revoked"
    world.chw_link.save()
    data = client_for(world.survivor).get("/api/v1/me/care-team/").json()
    assert {m["relation"] for m in data["team"]} == {"clinician", "caregiver"}
    assert "fake@test.org" not in str(data)


@pytest.mark.django_db
def test_my_care_team_is_only_for_the_person_themselves(world):
    assert client_for(world.clinician).get("/api/v1/me/care-team/").status_code == 403
    assert client_for(None).get("/api/v1/me/care-team/").status_code == 401


# --- Scope defaults ---------------------------------------------------------------------------------------


def test_default_scopes_for_the_new_movement_log():
    assert {sc.VIEW_MOBILITY, sc.LOG_MOBILITY} <= sc.CAREGIVER_ALLOWED
    assert {sc.VIEW_MOBILITY, sc.LOG_MOBILITY} <= sc.CHW_ALLOWED
    assert sc.VIEW_MOBILITY in sc.CLINICIAN_ALLOWED and sc.LOG_MOBILITY not in sc.CLINICIAN_ALLOWED
    assert sc.MANAGE_PLAN not in sc.SELF_SCOPES  # stages stay clinician-only


# --- Two syncs at the same moment ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_a_duplicate_that_races_past_the_check_is_saved_once_not_an_error(world, monkeypatch):
    """The phone reconnects and two syncs send the same entry together. The loser must get the saved entry back."""
    from apps.recovery.models import MobilityLog

    cid = "5b3c9a1e-6f2d-4a7b-8c1d-2e3f4a5b6c7d"
    MobilityLog.objects.create(patient=world.survivor, date=local_today(world.survivor), kind="walking", client_id=cid, entered_by=world.survivor)
    real_filter = MobilityLog.objects.filter
    calls = {"n": 0}

    def blind_first_check(*args, **kwargs):  # the first lookup sees nothing, as if the other request had not finished
        calls["n"] += 1
        return MobilityLog.objects.none() if calls["n"] == 1 else real_filter(*args, **kwargs)

    monkeypatch.setattr(MobilityLog.objects, "filter", blind_first_check)
    r = client_for(world.survivor).post(f"{ME}/mobility/", {"kind": "walking", "client_id": cid}, format="json")
    assert r.status_code == 200
    monkeypatch.undo()
    assert MobilityLog.objects.filter(patient=world.survivor, client_id=cid).count() == 1


@pytest.mark.django_db
def test_a_home_visit_sent_twice_at_once_keeps_one_visit_and_one_reading(world, monkeypatch):
    from django.utils import timezone as tz

    from apps.community.models import HomeVisit

    body = {"client_id": "0b6f7c8e-1d2a-4c3b-9e8f-7a6b5c4d3e2f", "visited_at": tz.now().isoformat(), "systolic": 120, "diastolic": 80}
    chw = client_for(world.chw)
    url = f"/api/v1/patients/{world.survivor.id}/home-visits/"
    assert chw.post(url, body, format="json").status_code == 201
    real_filter = HomeVisit.objects.filter
    calls = {"n": 0}

    def blind_first_check(*args, **kwargs):
        calls["n"] += 1
        return HomeVisit.objects.none() if calls["n"] == 1 else real_filter(*args, **kwargs)

    monkeypatch.setattr(HomeVisit.objects, "filter", blind_first_check)
    assert chw.post(url, body, format="json").status_code == 200
    monkeypatch.undo()
    assert HomeVisit.objects.filter(patient=world.survivor).count() == 1
    assert world.survivor.readings.count() == 1  # the second attempt's reading was rolled back with it
