"""Fictional demo data for the course demo and for developers. NEVER for real people.

Owner: Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md
Safety rules: refuses to run unless ALLOW_DEMO_DATA is on; all names and emails are fictional
(@example.org); blood pressure numbers are random; there are NO emergency contacts and NO medical advice.
"""
import random
import secrets
from datetime import time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.models import Consent, ConsentKind, Role, User
from apps.care.models import CareLink, LinkStatus, Relation
from apps.care.scopes import DEFAULT_SCOPES
from apps.content.models import EducationItem, EducationTranslation
from apps.health.models import (
    BPReading, CheckIn, CheckInAnswer, CheckInQuestion, Medication, MedicationDose, PlanTask, PlanTemplate,
    RecoveryPlan, TaskLog, VisitQuestion,
)  # fmt: skip

DEMO = {
    "survivor": ("demo-survivor@example.org", "Demo Survivor", Role.SURVIVOR),
    "prevention": ("demo-prevention@example.org", "Demo Prevention User", Role.PREVENTION),
    "caregiver": ("demo-caregiver@example.org", "Demo Caregiver", Role.CAREGIVER),
    "clinician": ("demo-clinician@example.org", "Demo Clinician", Role.CLINICIAN),
    "chw": ("demo-chw@example.org", "Demo Health Worker", Role.CHW),
    "admin": ("demo-admin@example.org", "Demo Administrator", Role.ADMIN),
}


class Command(BaseCommand):
    help = "Create fictional demo accounts and records (development and demo only)."

    def add_arguments(self, parser):
        parser.add_argument("--password", help="Password for every demo account. Random if omitted.")

    def handle(self, *args, **opts):
        if not settings.ALLOW_DEMO_DATA:
            raise CommandError("Demo data is switched off here. Set ALLOW_DEMO_DATA=1 (never in production).")
        if User.objects.filter(email__in=[v[0] for v in DEMO.values()]).exists():
            raise CommandError("Demo accounts already exist. Nothing changed.")
        call_command("seed_reference")
        password = opts["password"] or secrets.token_urlsafe(12)
        now = timezone.now()
        users = {}
        for key, (email, name, role) in DEMO.items():
            u = User.objects.create_user(
                email, password, display_name=name, role=role,
                professional_verified_at=now if role in (Role.CLINICIAN, Role.CHW) else None,
                is_staff=role == Role.ADMIN,
            )  # fmt: skip
            for kind in u.required_consents():
                Consent.objects.create(user=u, kind=kind, version=settings.CONSENT_VERSIONS[kind])
            users[key] = u
        survivor = users["survivor"]
        for rel, key in ((Relation.CLINICIAN, "clinician"), (Relation.CAREGIVER, "caregiver"), (Relation.CHW, "chw")):
            CareLink.objects.create(
                patient=survivor, member=users[key], relation=rel, scopes=DEFAULT_SCOPES[rel],
                status=LinkStatus.ACTIVE, activated_at=now, label=f"Demo {key}",
            )  # fmt: skip

        plan = RecoveryPlan.objects.create(patient=survivor, title="Demo plan (fictional)", created_by=users["clinician"])
        tasks = [
            PlanTask.objects.create(plan=plan, order=i, title=title, instructions="Fictional demo task.", created_by=users["clinician"])
            for i, title in enumerate(["Demo task A: practice item", "Demo task B: practice item", "Demo task C: practice item"])
        ]
        rng = random.Random(42)  # same fake numbers every time
        tz = ZoneInfo(survivor.timezone)
        today = now.astimezone(tz).date()
        questions = list(CheckInQuestion.objects.filter(is_active=True))
        meds = [
            Medication.objects.create(
                patient=survivor, name=f"Demo medicine {letter}", dose="[as prescribed]", times=times,
                start_date=today - timedelta(days=14), created_by=users["clinician"],
            )  # fmt: skip
            for letter, times in (("A", [time(8), time(20)]), ("B", [time(13)]))
        ]
        for days_ago in range(14):
            day = today - timedelta(days=days_ago)
            for owner in (survivor, users["prevention"]):
                for hour in (8, 19):
                    taken_at = now.astimezone(tz).replace(hour=hour, minute=0) - timedelta(days=days_ago)
                    if taken_at > now:
                        continue  # never a reading from the future
                    sys_ = rng.randint(110, 150)
                    BPReading.objects.create(
                        user=owner, systolic=sys_, diastolic=rng.randint(65, min(95, sys_ - 10)), taken_at=taken_at,
                        entered_by=owner, context="morning" if hour == 8 else "evening",
                    )  # fmt: skip
            for t in tasks:
                if rng.random() < 0.7:
                    TaskLog.objects.create(task=t, date=day, entered_by=survivor)
            if days_ago > 0:  # today's doses are left for the demo to tick live
                for m in meds:
                    for t in m.scheduled_on(day):
                        if rng.random() < 0.85:
                            MedicationDose.objects.create(medication=m, date=day, time=t, entered_by=survivor)
            ci = CheckIn.objects.create(user=survivor, date=day, entered_by=survivor)
            for q in questions:
                if q.answer_type == "yes_no":
                    value = False
                elif q.choices:
                    value = rng.choice(q.choices)["value"]
                else:
                    value = None
                CheckInAnswer.objects.create(checkin=ci, question=q, value=value, skipped=value is None)

        VisitQuestion.objects.create(patient=survivor, text="Demo question: can I walk outside on my own?", entered_by=survivor)
        self._seed_recovery(survivor, users, today, rng, now)
        PlanTemplate.objects.create(
            owner=users["clinician"], name="Demo template", tasks=[{"title": "Demo task D", "instructions": "Fictional."}]
        )
        item = EducationItem.objects.create(
            slug="demo-placeholder", source_name="StrokeCare demo (fictional)", is_published=True
        )
        EducationTranslation.objects.create(
            item=item, locale="en", title="Demo placeholder: education article",
            summary="Fictional demo content.", body="This is placeholder text for the demo. It is not medical information.",
        )  # fmt: skip
        self.stdout.write(self.style.SUCCESS("Demo data created."))
        self.stdout.write(f"Password for all demo accounts: {password}")
        for email, *_ in DEMO.values():
            self.stdout.write(f"  {email}")

    def _seed_recovery(self, survivor, users, today, rng, now):
        """Fictional goals, a recovery stage, movement entries, personal phrases and a reminder for the demo."""
        from datetime import timedelta as td

        from apps.family.models import CareEvent
        from apps.recovery.models import CarePhase, CustomPhrase, Goal, MobilityLog

        Goal.objects.create(patient=survivor, text="Demo goal: walk to the gate on my own", entered_by=survivor)
        Goal.objects.create(patient=survivor, text="Demo goal: hold a cup with both hands", entered_by=survivor, done_at=now)
        CarePhase.objects.create(
            patient=survivor, name="Demo stage: early weeks at home", starts_on=today - td(days=30), ends_on=today - td(days=1),
            care_needed="Fictional example text written by the demo clinician.", created_by=users["clinician"],
        )  # fmt: skip
        CarePhase.objects.create(
            patient=survivor, name="Demo stage: building up", starts_on=today,
            care_needed="Fictional example: help is needed in the mornings and evenings.", created_by=users["clinician"],
        )  # fmt: skip
        for days_ago in range(10):
            if rng.random() < 0.7:
                MobilityLog.objects.create(
                    patient=survivor, date=today - td(days=days_ago), kind=rng.choice(["walking", "stretching", "standing"]),
                    minutes=rng.choice([5, 10, 15, 20]), help=rng.choice(["alone", "with_aid", "with_person"]), entered_by=survivor,
                )  # fmt: skip
        CustomPhrase.objects.create(patient=survivor, text="Demo phrase: please call my daughter", icon="phone-call", entered_by=survivor)
        CareEvent.objects.create(
            patient=survivor, title="Demo appointment: clinic visit", kind="appointment",
            starts_at=now + td(days=1, hours=2), location="Demo clinic (fictional)", remind_minutes_before=1440,
            created_by=users["clinician"],
        )  # fmt: skip
