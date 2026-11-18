"""Add or update one emergency contact, marked as verified by a named person. Safe to run again.

Owner: Erica Rurangwa Sheja (Product Owner)
Safety rule: numbers never live in the code, so they are entered here, by a person, with the name of whoever
verified them. The app shows a number only once it has a verifier and a date (docs/SAFETY.md, rule 4).

    python manage.py add_emergency_contact --region Rwanda --label "SAMU ambulance" --kind ambulance \\
        --phone <number> --verified-by "Full Name"
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.content.models import EmergencyContact


class Command(BaseCommand):
    help = "Add or update a verified emergency contact (the number is given on the command line, never in code)."

    def add_arguments(self, parser):
        parser.add_argument("--region", required=True)
        parser.add_argument("--label", required=True)
        parser.add_argument("--kind", required=True, choices=[k for k, _ in EmergencyContact.Kind.choices])
        parser.add_argument("--phone", required=True)
        parser.add_argument("--hours", default="")
        parser.add_argument("--verified-by", required=True, help="The full name of the person who checked the number.")

    def handle(self, *args, **o):
        if not o["verified_by"].strip():
            raise CommandError("Give the name of the person who verified this number.")
        now = timezone.now()
        contact, created = EmergencyContact.objects.update_or_create(
            region=o["region"], phone=o["phone"].strip(),
            defaults={"label": o["label"], "kind": o["kind"], "hours": o["hours"], "is_active": True,
                      "verified_by_name": o["verified_by"].strip(), "verified_at": now, "last_checked_at": now},
        )  # fmt: skip
        self.stdout.write(self.style.SUCCESS(f"{'Added' if created else 'Updated'}: {contact.label} ({contact.region}), verified by {contact.verified_by_name}."))
