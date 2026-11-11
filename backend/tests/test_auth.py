"""Sign up, sign in, tokens, throttling.

Owner: Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md
"""
import pytest
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from apps.accounts.models import User
from apps.audit.models import AuditLog
from tests.conftest import PASSWORD, client_for, make_user

REGISTER = "/api/v1/auth/register/"
LOGIN = "/api/v1/auth/login/"


def signup(client, **over):
    body = {"email": "New@Test.org", "password": PASSWORD, "display_name": "New Person", "role": "survivor"}
    body.update(over)
    return client.post(REGISTER, body, format="json")


@pytest.mark.django_db
def test_register_returns_tokens_and_lists_required_consents():
    r = signup(APIClient())
    assert r.status_code == 201
    assert {"access", "refresh", "user", "consents"} <= set(r.json())
    assert r.json()["user"]["email"] == "new@test.org"  # stored lower-case
    assert set(r.json()["consents"]) == {"privacy_notice", "health_data"}
    assert not any(c["granted"] for c in r.json()["consents"].values())


@pytest.mark.django_db
def test_caregiver_needs_only_the_privacy_notice():
    r = signup(APIClient(), role="caregiver")
    assert set(r.json()["consents"]) == {"privacy_notice"}


@pytest.mark.django_db
@pytest.mark.parametrize("role", ["clinician", "admin", "superuser", ""])
def test_nobody_can_register_as_clinician_or_admin(role):
    r = signup(APIClient(), role=role)
    assert r.status_code == 400
    assert not User.objects.filter(email="new@test.org").exists()


@pytest.mark.django_db
def test_duplicate_email_and_weak_password_are_rejected():
    make_user("new@test.org", "survivor")
    assert signup(APIClient()).status_code == 400
    r = signup(APIClient(), email="other@test.org", password="12345678")
    assert r.status_code == 400 and "password" in r.json()["error"]["fields"]


@pytest.mark.django_db
def test_passwords_are_hashed_with_bcrypt(real_hashers):
    signup(APIClient())
    assert User.objects.get(email="new@test.org").password.startswith("bcrypt_sha256$")


@pytest.mark.django_db
def test_login_and_wrong_password():
    make_user("a@test.org", "survivor")
    ok = APIClient().post(LOGIN, {"email": "A@test.org", "password": PASSWORD}, format="json")
    assert ok.status_code == 200 and ok.json()["user"]["role"] == "survivor"
    bad = APIClient().post(LOGIN, {"email": "a@test.org", "password": "nope"}, format="json")
    assert bad.status_code == 401
    assert bad.json()["error"]["code"] == "no_active_account"


@pytest.mark.django_db
def test_failed_login_is_logged_without_the_email():
    make_user("a@test.org", "survivor")
    APIClient().post(LOGIN, {"email": "a@test.org", "password": "nope"}, format="json")
    entry = AuditLog.objects.get(action="login.failed")
    assert entry.actor is None and "a@test.org" not in str(entry.metadata)


@pytest.mark.django_db
def test_login_is_rate_limited(monkeypatch):
    monkeypatch.setitem(ScopedRateThrottle.THROTTLE_RATES, "login", "3/min")
    make_user("a@test.org", "survivor")
    codes = [
        APIClient().post(LOGIN, {"email": "a@test.org", "password": "nope"}, format="json").status_code
        for _ in range(5)
    ]
    assert codes == [401, 401, 401, 429, 429]


@pytest.mark.django_db
def test_refresh_rotates_and_the_old_token_stops_working():
    make_user("a@test.org", "survivor")
    tokens = APIClient().post(LOGIN, {"email": "a@test.org", "password": PASSWORD}, format="json").json()
    c = APIClient()
    first = c.post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]}, format="json")
    assert first.status_code == 200 and first.json()["refresh"] != tokens["refresh"]
    replay = c.post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]}, format="json")
    assert replay.status_code == 401


@pytest.mark.django_db
def test_logout_revokes_the_refresh_token_on_the_server():
    make_user("a@test.org", "survivor")
    tokens = APIClient().post(LOGIN, {"email": "a@test.org", "password": PASSWORD}, format="json").json()
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert c.post("/api/v1/auth/logout/", {"refresh": tokens["refresh"]}, format="json").status_code == 204
    assert c.post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]}, format="json").status_code == 401


@pytest.mark.django_db
def test_protected_routes_need_a_token_and_never_return_the_hash():
    assert APIClient().get("/api/v1/me/").status_code == 401
    user = make_user("a@test.org", "survivor")
    body = client_for(user).get("/api/v1/me/").content.decode()
    assert "password" not in body and "md5" not in body


@pytest.mark.django_db
def test_profile_update_cannot_change_role_or_email():
    user = make_user("a@test.org", "survivor")
    r = client_for(user).patch("/api/v1/me/", {"role": "clinician", "email": "x@test.org", "display_name": "Neo"}, format="json")
    user.refresh_from_db()
    assert r.status_code == 200 and user.role == "survivor" and user.email == "a@test.org" and user.display_name == "Neo"


@pytest.mark.django_db
def test_accessibility_preferences_default_to_off_and_persist():
    user = make_user("a@test.org", "survivor")
    c = client_for(user)
    first = c.get("/api/v1/me/accessibility/").json()
    assert first["text_scale"] == 100 and not first["audio_first"] and not first["one_question_at_a_time"]
    c.patch("/api/v1/me/accessibility/", {"audio_first": True, "text_scale": 150}, format="json")
    again = c.get("/api/v1/me/accessibility/").json()
    assert again["audio_first"] is True and again["text_scale"] == 150
    assert c.patch("/api/v1/me/accessibility/", {"text_scale": 999}, format="json").status_code == 400
