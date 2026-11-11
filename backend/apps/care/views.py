"""Owner: Kenneth Master (System architect) · AI-assisted draft, see AI_USE_LOG.md"""
import hmac
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import Http404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import ConsentKind
from apps.audit.services import record as audit
from apps.common.errors import ConsentRequired

from apps.health.services import NEEDS_FILTERS, patient_facts
from apps.messaging.services import unread_count

from . import jobs
from . import scopes as sc
from .alerts import refresh_for
from .models import CareLink, LinkStatus, Relation, hash_code, new_code
from .scopes import ALLOWED_SCOPES
from .serializers import InviteSerializer, LinkSerializer, RedeemSerializer, ScopesSerializer

BAD_CODE = "This code is not valid, or it has expired. Ask the person for a new one."


def _my_links(user):
    return CareLink.objects.filter(Q(patient=user) | Q(member=user)).select_related("patient", "member")


class LinkListView(APIView):
    def get(self, request):
        links = _my_links(request.user).exclude(status=LinkStatus.REVOKED)
        return Response(LinkSerializer(links, many=True, context={"request": request}).data)


class InviteView(APIView):
    """A patient creates a one-time code to give to their clinician or caregiver."""

    def post(self, request):
        if not request.user.is_patient:
            raise PermissionDenied("Only people who keep a health record can invite others.", code="not_a_patient")
        if not request.user.has_active_consent(ConsentKind.HEALTH_DATA):
            raise ConsentRequired()
        ser = InviteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        for _ in range(5):  # a clash on a random 8-character code is astronomically unlikely; retry anyway
            code = new_code()
            try:
                with transaction.atomic():
                    link = CareLink.objects.create(
                        patient=request.user,
                        relation=d["relation"],
                        label=d["label"],
                        scopes=d["scopes"],
                        invite_hash=hash_code(code),
                        invite_expires_at=timezone.now() + timedelta(hours=settings.INVITE_TTL_HOURS),
                    )
                break
            except IntegrityError:
                continue
        else:  # pragma: no cover
            raise ValidationError({"detail": ["Could not create a code. Please try again."]})
        audit(request, "link.invited", subject=request.user, relation=d["relation"], link=str(link.id))
        data = LinkSerializer(link, context={"request": request}).data
        data["code"] = f"{code[:4]}-{code[4:]}"  # shown once; only a hash is stored
        return Response(data, status=status.HTTP_201_CREATED)


class RedeemView(APIView):
    """A clinician or caregiver enters the code they were given."""

    throttle_scope = "redeem"

    def post(self, request):
        ser = RedeemSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        with transaction.atomic():
            link = (
                CareLink.objects.select_for_update()
                .select_related("patient")
                .filter(
                    invite_hash=hash_code(ser.validated_data["code"]),
                    status=LinkStatus.PENDING,
                    invite_expires_at__gt=timezone.now(),
                )
                .first()
            )
            me = request.user
            eligible = link is not None and (
                (link.relation == Relation.CLINICIAN and me.is_verified_clinician)
                or (link.relation == Relation.CHW and me.is_verified_chw)
                or (link.relation == Relation.CAREGIVER and me.role == "caregiver")
            )
            if not eligible or link.patient_id == me.id:
                raise ValidationError({"code": [BAD_CODE]})  # same answer for every failure: no probing
            link.member = me
            link.status = LinkStatus.ACTIVE
            link.activated_at = timezone.now()
            link.invite_hash = None
            link.invite_expires_at = None
            link.save()
        audit(request, "link.accepted", subject=link.patient, relation=link.relation, link=str(link.id))
        return Response(LinkSerializer(link, context={"request": request}).data)


class LinkDetailView(APIView):
    def _get(self, request, link_id):
        link = _my_links(request.user).filter(id=link_id).first()
        if link is None:
            raise Http404
        return link

    def patch(self, request, link_id):
        """The patient changes what a person may see or do."""
        link = self._get(request, link_id)
        if link.patient_id != request.user.id:
            raise PermissionDenied("Only the patient can change what is shared.", code="patient_only")
        if link.status == LinkStatus.REVOKED:
            raise Http404
        ser = ScopesSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        scopes = set(ser.validated_data["scopes"])
        if scopes - ALLOWED_SCOPES[link.relation]:
            raise ValidationError({"scopes": [f"Some of these are not allowed for a {link.relation}."]})
        link.scopes = sorted(scopes)
        link.save(update_fields=["scopes"])
        audit(request, "link.scopes_changed", subject=link.patient, link=str(link.id))
        return Response(LinkSerializer(link, context={"request": request}).data)

    def delete(self, request, link_id):
        """Either side can end a link at any time."""
        link = self._get(request, link_id)
        if link.status != LinkStatus.REVOKED:
            link.status = LinkStatus.REVOKED
            link.revoked_at = timezone.now()
            link.invite_hash = None
            link.save(update_fields=["status", "revoked_at", "invite_hash"])
            audit(request, "link.ended", subject=link.patient, link=str(link.id), by=request.user.role)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyPatientsView(APIView):
    """For clinicians and caregivers: the people who shared with me, what I may do, and plain facts.

    `?needs=urgent|no_check_in|doses_not_marked` keeps only people for whom that fact is true. The facts are
    dates and counts. There is no score and no ranking by "risk".
    """

    def get(self, request):
        needs = request.query_params.get("needs")
        if needs and needs not in NEEDS_FILTERS:
            raise ValidationError({"needs": [f"Use one of: {', '.join(sorted(NEEDS_FILTERS))}."]})
        links = (
            CareLink.objects.filter(member=request.user, status=LinkStatus.ACTIVE)
            .select_related("patient", "member")
            .order_by("patient__display_name")
        )
        out = []
        for l in links:
            if not (l.member_is_eligible() and l.patient.has_active_consent(ConsentKind.HEALTH_DATA)):
                continue
            facts = patient_facts(l.patient, set(l.scopes))
            if sc.MESSAGE in l.scopes:
                facts["unread_messages"] = unread_count(l.patient, request.user)
            if needs and not NEEDS_FILTERS[needs](facts):
                continue
            out.append({
                "patient_id": l.patient_id, "display_name": l.patient.display_name, "patient_role": l.patient.role,
                "relation": l.relation, "scopes": l.scopes, "link_id": l.id, "facts": facts,
            })  # fmt: skip
        return Response(out)


def _alert_row(a):
    return {
        "id": a.id, "kind": a.kind, "patient_id": a.patient_id, "patient_name": a.patient.display_name,
        "detail": a.detail, "created_at": a.created_at, "read": a.read_at is not None,
    }  # fmt: skip


class AlertsView(APIView):
    """A caregiver's alerts, newest first. Opening the list works out any new ones first."""

    def get(self, request):
        if request.user.role != "caregiver":
            raise PermissionDenied("Alerts are for caregivers.", code="not_a_caregiver")
        refresh_for(request.user)
        qs = request.user.alerts.select_related("patient")[:50]
        return Response({
            "results": [_alert_row(a) for a in qs],
            "unread": request.user.alerts.filter(read_at__isnull=True).count(),
            "note": "Alerts are not an emergency service. In an emergency, contact local emergency services.",
        })  # fmt: skip


class AlertReadView(APIView):
    def post(self, request, alert_id=None):
        qs = request.user.alerts.filter(read_at__isnull=True)
        if alert_id is not None:
            qs = qs.filter(id=alert_id)
            if not request.user.alerts.filter(id=alert_id).exists():
                raise Http404
        qs.update(read_at=timezone.now())
        return Response(status=status.HTTP_204_NO_CONTENT)


class RunJobsView(APIView):
    """For a free external cron. Off unless CRON_SECRET is set; the caller must send it in X-Cron-Secret."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        secret = settings.CRON_SECRET
        given = request.headers.get("X-Cron-Secret", "")
        if not secret:
            raise Http404
        if not hmac.compare_digest(secret.encode(), given.encode()):
            raise PermissionDenied("Wrong scheduler secret.", code="bad_secret")
        return Response(jobs.run_all())
