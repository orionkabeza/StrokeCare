"""Background jobs, run by the scheduler.

Owner: Kenneth Master (System architect) · AI-assisted draft, see AI_USE_LOG.md
Three ways to run them, all calling `run_all()`:
  * `python manage.py run_scheduler`        a worker process that loops (docker-compose `worker` service)
  * `python manage.py generate_alerts`      one run, for any cron
  * POST /api/v1/internal/jobs/run/          one run over HTTP, guarded by the CRON_SECRET header, for free hosts
                                             without workers (.github/workflows/scheduler.yml calls it)
Every job is safe to run twice: alerts are de-duplicated.
"""
import logging

from .alerts import refresh_for
from .models import CareLink, LinkStatus, Relation

log = logging.getLogger("strokecare.jobs")


def run_all() -> dict:
    members = {
        link.member
        for link in CareLink.objects.filter(relation=Relation.CAREGIVER, status=LinkStatus.ACTIVE).select_related("member")
    }
    created = sum(refresh_for(m) for m in members)
    result = {"caregivers_checked": len(members), "alerts_created": created}
    log.info("jobs run: %s", result)
    return result
