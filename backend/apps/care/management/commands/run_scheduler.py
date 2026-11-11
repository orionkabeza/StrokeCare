"""Owner: Kenneth Master (System architect) · AI-assisted draft, see AI_USE_LOG.md

A small worker: runs the jobs every --interval seconds until stopped. Use it where the host allows a background
worker (docker-compose `worker`). A failed run is logged and retried at the next tick; it never stops the loop.
"""
import signal
import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from apps.care.jobs import run_all


class Command(BaseCommand):
    help = "Run background jobs (caregiver alerts) on a fixed interval."

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=int, default=900, help="Seconds between runs (default 900 = 15 min).")
        parser.add_argument("--once", action="store_true", help="Run once and exit.")

    def handle(self, *args, **opts):
        stopping = {"now": False}

        def stop(*_):
            stopping["now"] = True

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        interval = max(60, opts["interval"])
        while not stopping["now"]:
            try:
                r = run_all()
                self.stdout.write(f"jobs: {r['alerts_created']} new alerts, {r['caregivers_checked']} caregivers checked")
            except Exception as exc:  # keep the worker alive; the next tick tries again
                self.stderr.write(f"jobs failed: {exc!r}")
            if opts["once"]:
                break
            for _ in range(interval):
                if stopping["now"]:
                    break
                time.sleep(1)
            close_old_connections()  # drop a stale database connection before the next run
