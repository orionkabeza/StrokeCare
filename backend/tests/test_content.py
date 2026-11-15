"""Public education content, language fallback, health check.

Owner: Erica Rurangwa Sheja (Product Owner) · AI-assisted draft, see AI_USE_LOG.md
"""
import pytest
from rest_framework.test import APIClient

from apps.content.models import EducationItem, EducationTranslation, Topic


@pytest.fixture
def items(db):
    a = EducationItem.objects.create(slug="a-demo", source_name="Demo source", is_published=True, audience="prevention")
    EducationTranslation.objects.create(item=a, locale="en", title="English title", body="English body")
    EducationTranslation.objects.create(item=a, locale="fr", title="Titre français", body="Corps")
    b = EducationItem.objects.create(slug="b-demo", source_name="Demo source", is_published=True, audience="survivor")
    EducationTranslation.objects.create(item=b, locale="en", title="Only English")
    EducationItem.objects.create(slug="c-hidden", source_name="Demo", is_published=False)
    return a, b


@pytest.mark.django_db
def test_education_is_readable_without_signing_in(items):
    r = APIClient().get("/api/v1/education/")
    assert r.status_code == 200 and [i["slug"] for i in r.json()["results"]] == ["a-demo", "b-demo"]
    assert all("body" not in i for i in r.json()["results"])  # list is light; detail has the body


@pytest.mark.django_db
def test_requested_language_is_served_when_it_exists_and_english_otherwise(items):
    c = APIClient()
    fr = {i["slug"]: i for i in c.get("/api/v1/education/?lang=fr").json()["results"]}
    assert fr["a-demo"]["title"] == "Titre français" and fr["a-demo"]["fell_back"] is False
    assert fr["b-demo"]["title"] == "Only English" and fr["b-demo"]["fell_back"] is True
    assert fr["b-demo"]["locale_served"] == "en"
    rw = c.get("/api/v1/education/a-demo/?lang=rw").json()
    assert rw["fell_back"] is True and rw["body"] == "English body"


@pytest.mark.django_db
def test_accept_language_header_is_respected_and_garbage_is_ignored(items):
    c = APIClient()
    assert c.get("/api/v1/education/a-demo/", HTTP_ACCEPT_LANGUAGE="fr-FR,fr;q=0.9").json()["locale_served"] == "fr"
    assert c.get("/api/v1/education/a-demo/?lang=zz").json()["locale_served"] == "en"


@pytest.mark.django_db
def test_unpublished_items_do_not_exist_for_the_public(items):
    assert APIClient().get("/api/v1/education/c-hidden/").status_code == 404
    assert APIClient().get("/api/v1/education/nope/").status_code == 404


@pytest.mark.django_db
def test_filter_by_audience(items):
    r = APIClient().get("/api/v1/education/?audience=survivor").json()["results"]
    assert [i["slug"] for i in r] == ["b-demo"]


@pytest.fixture
def topic(db):
    return Topic.objects.create(slug="movement", order=4, name={"en": "Movement and exercises at home"})


@pytest.mark.django_db
def test_filter_by_topic(items, topic):
    a, b = items
    a.topic = topic
    a.save()
    r = APIClient().get(f"/api/v1/education/?topic={topic.slug}").json()["results"]
    assert [i["slug"] for i in r] == ["a-demo"]
    assert r[0]["topic"] == {"slug": "movement", "name": "Movement and exercises at home"}
    unfiltered = APIClient().get("/api/v1/education/").json()["results"]
    assert next(i for i in unfiltered if i["slug"] == "b-demo")["topic"] is None


@pytest.mark.django_db
def test_topics_list_counts_published_items_by_kind(items, topic):
    a, b = items
    a.topic = topic
    a.kind = EducationItem.Kind.VIDEO
    a.save()
    b.topic = topic
    b.save()
    r = APIClient().get("/api/v1/education/topics/").json()["results"]
    row = next(t for t in r if t["slug"] == "movement")
    assert row["video_count"] == 1 and row["text_count"] == 1 and row["status"] == "draft"


@pytest.mark.django_db
def test_video_item_carries_poster_captions_and_duration():
    item = EducationItem.objects.create(slug="vid-demo", source_name="Demo source", is_published=True, kind="video")
    EducationTranslation.objects.create(
        item=item, locale="en", title="Demo video", video_url="/media/demo.mp4",
        poster_url="/media/demo.jpg", captions_url="/media/demo-en.vtt", duration_seconds=180,
    )  # fmt: skip
    data = APIClient().get("/api/v1/education/vid-demo/").json()
    assert data["poster_url"] == "/media/demo.jpg" and data["captions_url"] == "/media/demo-en.vtt" and data["duration_seconds"] == 180


@pytest.mark.django_db
def test_emergency_text_exists_in_all_three_languages():
    c = APIClient()
    assert "AVC" in c.get("/api/v1/emergency/?lang=fr").json()["message"]
    rw = c.get("/api/v1/emergency/?lang=rw").json()
    assert rw["locale_served"] == "rw" and "Ntutegereze" in rw["message"]


@pytest.mark.django_db
def test_health_check_and_api_docs():
    c = APIClient()
    assert c.get("/healthz").json() == {"status": "ok"}
    assert c.get("/api/v1/schema/").status_code == 200


@pytest.mark.django_db
def test_talk_board_is_public_draft_and_falls_back_to_english():
    from django.core.management import call_command

    call_command("seed_reference")
    rows = APIClient().get("/api/v1/talk-board/?lang=rw").json()["results"]
    assert len(rows) == 17 and all(r["status"] == "draft" for r in rows)  # AI-drafted translations stay draft
    assert all(r["locale_served"] == "rw" and r["label"] for r in rows)
    assert {r["category"] for r in rows} == {"answers", "needs", "feelings", "people"}
    assert "audio_url" not in rows[0]  # no recordings: the phone's own voice reads the words


@pytest.mark.django_db
def test_seed_reference_creates_the_nine_learn_topics_as_draft():
    from django.core.management import call_command

    call_command("seed_reference")
    rows = APIClient().get("/api/v1/education/topics/").json()["results"]
    assert len(rows) == 9 and all(r["status"] == "draft" for r in rows)
    assert [r["slug"] for r in rows][0] == "recognising-a-stroke"  # starts in the required order


@pytest.mark.django_db
def test_seed_reference_fills_every_topic_with_draft_notes_and_sourced_videos():
    from django.core.management import call_command

    call_command("seed_reference")
    call_command("seed_reference")  # safe to run on every deploy
    topics = APIClient().get("/api/v1/education/topics/").json()["results"]
    assert all(t["text_count"] >= 1 and t["video_count"] >= 1 for t in topics)
    items = APIClient().get("/api/v1/education/").json()["results"]
    assert all(i["clinical_review"]["status"] == "draft" and i["source"]["name"] for i in items)
    videos = [i for i in items if i["kind"] == "video"]
    assert videos and all(i["video_url"].startswith("https://www.youtube.com/watch?v=") for i in videos)


@pytest.mark.django_db
def test_seed_reference_adds_new_languages_to_drafts_but_never_touches_reviewed_rows():
    from django.core.management import call_command
    from django.utils import timezone

    from apps.content.models import TalkPhrase

    TalkPhrase.objects.create(code="yes", category="answers", label={"en": "Yes"})
    TalkPhrase.objects.create(
        code="no", category="answers", label={"en": "No (reviewed)"}, status="reviewed",
        reviewed_by_name="Demo reviewer", reviewed_at=timezone.now(),
    )  # fmt: skip
    call_command("seed_reference")
    assert TalkPhrase.objects.get(code="yes").label["rw"] == "Yego"
    assert TalkPhrase.objects.get(code="no").label == {"en": "No (reviewed)"}


@pytest.mark.django_db
def test_app_routes_get_the_web_app_with_a_strict_csp(settings, tmp_path):
    (tmp_path / "index.html").write_text("<!doctype html><title>StrokeCare</title>")
    settings.FRONTEND_DIST = tmp_path
    c = APIClient()
    r = c.get("/p/me/checkin")
    assert r.status_code == 200 and b"StrokeCare" in b"".join(r.streaming_content)
    assert "script-src 'self'" in r["Content-Security-Policy"] and "frame-ancestors 'none'" in r["Content-Security-Policy"]
    assert c.get("/api/v1/nope/").status_code == 404  # API paths never fall through to the app
    assert c.get("/healthz").json() == {"status": "ok"}


@pytest.mark.django_db
def test_an_emergency_number_is_entered_by_a_person_with_a_verifier_never_in_code():
    from django.core.management import call_command
    from django.core.management.base import CommandError

    with pytest.raises(CommandError):
        call_command("add_emergency_contact", region="Rwanda", label="SAMU ambulance", kind="ambulance", phone="912", verified_by=" ")
    call_command("add_emergency_contact", region="Rwanda", label="SAMU ambulance", kind="ambulance", phone="912", verified_by="A Named Person")
    call_command("add_emergency_contact", region="Rwanda", label="SAMU ambulance", kind="ambulance", phone="912", verified_by="A Named Person")
    contacts = APIClient().get("/api/v1/emergency/").json()["contacts"]
    assert [(c["phone"], c["verified_by"]) for c in contacts] == [("912", "A Named Person")]  # once, however often it runs
