"""The one place that decides whose data a request may touch.

Owner: Kenneth Master (System architect) · AI-assisted draft, see AI_USE_LOG.md

Every patient-data route lives under /patients/<me|uuid>/... and calls `resolve_access`. Rules:
  * `me`            -> only for patient accounts, only with the health-data consent, never the clinical plan.
  * `<uuid>`        -> only through an ACTIVE care link whose scopes include the action. No link, a link
                       to someone else, or a patient who withdrew consent all answer 404, so a stranger
                       learns nothing. A link that lacks the scope answers 403.
  * Every non-owner access is written to the audit log.
"""
import uuid
from dataclasses import dataclass

from rest_framework.exceptions import NotFound, PermissionDenied

from apps.accounts.models import ConsentKind
from apps.audit.services import record as audit
from apps.care.models import CareLink, LinkStatus
from apps.care.scopes import SELF_SCOPES

from .errors import ConsentRequired


@dataclass(frozen=True)
class Access:
    subject: object  # the patient whose data this is
    link: object  # the CareLink, or None when the patient acts on their own data
    actor: object  # who is making the request

    @property
    def is_self(self) -> bool:
        return self.link is None


def resolve_access(request, patient_ref: str, scope: str) -> Access:
    actor = request.user
    if patient_ref == "me":
        if not actor.is_patient:
            raise PermissionDenied("This account does not keep personal health records.", code="not_a_patient")
        if scope not in SELF_SCOPES:
            raise PermissionDenied("Only a verified clinician can do this.", code="scope_missing")
        if not actor.has_active_consent(ConsentKind.HEALTH_DATA):
            raise ConsentRequired()
        return Access(subject=actor, link=None, actor=actor)

    try:
        patient_id = uuid.UUID(patient_ref)
    except ValueError:
        raise NotFound()
    link = (
        CareLink.objects.select_related("patient", "member")
        .filter(patient_id=patient_id, member=actor, status=LinkStatus.ACTIVE)
        .first()
    )
    if link is None or not link.member_is_eligible():
        raise NotFound()
    if not link.patient.has_active_consent(ConsentKind.HEALTH_DATA):
        raise NotFound()
    if scope not in link.scopes:
        raise PermissionDenied("You do not have this kind of access for this person.", code="scope_missing")
    audit(request, f"access.{scope}", subject=link.patient, relation=link.relation)
    return Access(subject=link.patient, link=link, actor=actor)


def require_self_patient(request):
    """For things only the person themselves may touch (their own reminders)."""
    user = request.user
    if not user.is_patient:
        raise PermissionDenied("This account does not keep personal health records.", code="not_a_patient")
    if not user.has_active_consent(ConsentKind.HEALTH_DATA):
        raise ConsentRequired()
    return user


class PatientScopedMixin:
    """Add to an APIView. Set `scope_by_method = {"GET": VIEW_X, "POST": LOG_X}`.

    Authentication and throttling run first, then access is resolved into `self.access`.
    """

    scope_by_method: dict = {}

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        method = "GET" if request.method == "HEAD" else request.method
        scope = self.scope_by_method.get(method)
        if scope is None:  # OPTIONS or a method the view does not offer
            self.access = None
            return
        self.access = resolve_access(request, kwargs["patient_ref"], scope)
