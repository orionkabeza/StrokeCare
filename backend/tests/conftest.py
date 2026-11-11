"""Shared test helpers.

Owner: Orion Kabeza (DevOps) · AI-assisted draft, see AI_USE_LOG.md
"""
from types import SimpleNamespace

import pytest
from django.conf import settings as django_settings
from django.core.cache import cache
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Consent, Role, User
from apps.care.models import CareLink, LinkStatus
from apps.care.scopes import ALLOWED_SCOPES, DEFAULT_SCOPES

PASSWORD = "correct-horse-battery-staple"
REAL_HASHERS = list(django_settings.PASSWORD_HASHERS)


@pytest.fixture(autouse=True)
def _fast_and_clean(settings):
    """A fast hasher keeps the suite quick; tests that check bcrypt switch back with `real_hashers`."""
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def real_hashers(settings):
    settings.PASSWORD_HASHERS = REAL_HASHERS


def make_user(email, role, consent=True, verified=True, name=None):
    user = User.objects.create_user(
        email,
        PASSWORD,
        display_name=name or email.split("@")[0],
        role=role,
        professional_verified_at=timezone.now() if (role in (Role.CLINICIAN, Role.CHW) and verified) else None,
        is_staff=role == Role.ADMIN,
    )
    if consent:
        for kind in user.required_consents():
            Consent.objects.create(user=user, kind=kind, version=django_settings.CONSENT_VERSIONS[kind])
    return user


def link(patient, member, relation, scopes=None):
    return CareLink.objects.create(
        patient=patient,
        member=member,
        relation=relation,
        scopes=sorted(scopes) if scopes is not None else DEFAULT_SCOPES[relation],
        status=LinkStatus.ACTIVE,
        activated_at=timezone.now(),
    )


def client_for(user=None):
    c = APIClient()
    if user is not None:
        c.force_authenticate(user)
    return c


@pytest.fixture
def questions(db):
    call_command("seed_reference")


@pytest.fixture
def world(db, questions):
    """One survivor with a linked clinician and caregiver, plus unrelated people."""
    w = SimpleNamespace()
    w.survivor = make_user("survivor@test.org", Role.SURVIVOR)
    w.prevention = make_user("prevention@test.org", Role.PREVENTION)
    w.other_survivor = make_user("other@test.org", Role.SURVIVOR)
    w.clinician = make_user("clinician@test.org", Role.CLINICIAN)
    w.clinician_unlinked = make_user("clinician2@test.org", Role.CLINICIAN)
    w.caregiver = make_user("caregiver@test.org", Role.CAREGIVER)
    w.caregiver_unlinked = make_user("caregiver2@test.org", Role.CAREGIVER)
    w.admin = make_user("admin@test.org", Role.ADMIN)
    w.chw = make_user("chw@test.org", Role.CHW)
    w.clinician_link = link(w.survivor, w.clinician, "clinician")
    w.chw_link = link(w.survivor, w.chw, "chw")
    w.caregiver_link = link(w.survivor, w.caregiver, "caregiver")
    return w


def scopes_for(relation):
    return ALLOWED_SCOPES[relation]
