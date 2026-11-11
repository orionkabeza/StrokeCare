"""Owner: Kenneth Master (System architect) · AI-assisted draft, see AI_USE_LOG.md

Compute alerts for every caregiver once. Safe to run on a schedule; it never duplicates an alert.
"""
from django.core.management.base import BaseCommand

from apps.care.jobs import run_all


class Command(BaseCommand):
    help = "Create new caregiver alerts from today's facts (one run)."

    def handle(self, *args, **options):
        r = run_all()
        self.stdout.write(self.style.SUCCESS(f"{r['alerts_created']} new alerts for {r['caregivers_checked']} caregivers."))
