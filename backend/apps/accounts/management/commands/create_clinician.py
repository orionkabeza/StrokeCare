"""Create a clinician account after an administrator has checked their credentials.

Owner: Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md
Safety rule: only run this after you have checked the person's licence. `--verified` records that you did.
"""
import secrets

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Create a clinician account. Prints a one-time password if you do not give one."

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("display_name")
        parser.add_argument("--ref", default="", help="Licence or registration reference you checked.")
        parser.add_argument("--verified", action="store_true", help="I have checked this person's credentials.")
        parser.add_argument("--password")
        parser.add_argument("--role", choices=["clinician", "chw"], default="clinician",
                            help="clinician, or chw for a community health worker")

    def handle(self, *args, **o):
        if User.objects.filter(email=o["email"].lower()).exists():
            raise CommandError("That email already has an account.")
        password = o["password"] or secrets.token_urlsafe(12)
        User.objects.create_user(
            o["email"], password, display_name=o["display_name"], role=o["role"],
            professional_ref=o["ref"], professional_verified_at=timezone.now() if o["verified"] else None,
        )  # fmt: skip
        self.stdout.write(self.style.SUCCESS(f"{o['role'].upper()} account created ({'verified' if o['verified'] else 'NOT verified yet'})."))
        if not o["password"]:
            self.stdout.write(f"One-time password: {password}  (ask them to change it)")
