"""Owner: Axel Mfura (Backend and database)"""
import json
import re

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import AuthenticationFailed, NotFound, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.audit.models import AuditLog
from apps.audit.services import record as audit
from apps.common import limits

from .models import AccessibilityPreference, Consent, ConsentKind, PersonalEmergencyContact
from .serializers import (
    AccessibilityPreferenceSerializer,
    ConsentActionSerializer,
    DeleteAccountSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
    consent_status,
)


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "register"

    def post(self, request):
        ser = RegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.save()
        audit(request, "account.registered", subject=user, actor=user, role=user.role)
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "consents": consent_status(user),
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
        except (AuthenticationFailed, ValidationError):
            audit(request, "login.failed")  # no email stored: minimal data
            raise
        user_id = response.data["user"]["id"]
        AuditLog.objects.create(actor_id=user_id, subject_id=user_id, action="login.ok")
        return response


class LogoutView(APIView):
    """Revokes the refresh token on the server, so a stolen copy stops working."""

    def post(self, request):
        token = request.data.get("refresh")
        if not token:
            raise ValidationError({"refresh": ["This field is required."]})
        try:
            RefreshToken(token).blacklist()
        except TokenError:
            pass  # already invalid: nothing left to revoke
        audit(request, "logout", subject=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    def get(self, request):
        return Response({"user": UserSerializer(request.user).data, "consents": consent_status(request.user)})

    def patch(self, request):
        ser = UserSerializer(request.user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

    def delete(self, request):
        """Erase the account and everything attached to it. Needs the password again."""
        ser = DeleteAccountSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        if not request.user.check_password(ser.validated_data["password"]):
            raise ValidationError({"password": ["That password is not correct."]})
        user = request.user
        with transaction.atomic():
            audit(request, "account.deleted", actor=None, role=user.role)  # nobody is named: the person is gone
            user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConsentView(APIView):
    def get(self, request):
        return Response(consent_status(request.user))

    def post(self, request):
        ser = ConsentActionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        kind, accept = ser.validated_data["kind"], ser.validated_data["accept"]
        if kind not in request.user.required_consents():
            raise ValidationError({"kind": ["This consent does not apply to your account."]})
        now = timezone.now()
        with transaction.atomic():
            if accept:
                if not request.user.has_active_consent(kind):
                    Consent.objects.create(user=request.user, kind=kind, version=settings.CONSENT_VERSIONS[kind])
                audit(request, "consent.granted", subject=request.user, kind=kind)
            else:
                request.user.consents.filter(kind=kind, revoked_at__isnull=True).update(revoked_at=now)
                audit(request, "consent.revoked", subject=request.user, kind=kind)
        return Response(consent_status(request.user))


class AccessibilityView(APIView):
    def _prefs(self, request):
        prefs, _ = AccessibilityPreference.objects.get_or_create(user=request.user)
        return prefs

    def get(self, request):
        return Response(AccessibilityPreferenceSerializer(self._prefs(request)).data)

    def patch(self, request):
        ser = AccessibilityPreferenceSerializer(self._prefs(request), data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class ExportView(APIView):
    """Everything we hold about the signed-in person, as one JSON file they can keep."""

    def get(self, request):
        user = request.user
        data = {
            "exported_at": timezone.now().isoformat(),
            "profile": UserSerializer(user).data,
            "consents": [
                {"kind": c.kind, "version": c.version, "granted_at": c.granted_at, "revoked_at": c.revoked_at}
                for c in user.consents.all()
            ],
            "accessibility": AccessibilityPreferenceSerializer(
                AccessibilityPreference.objects.get_or_create(user=user)[0]
            ).data,
            "care_links": [
                {"relation": l.relation, "status": l.status, "scopes": l.scopes, "created_at": l.created_at}
                for l in user.care_links.all()
            ],
            "emergency_contacts": [
                {"name": c.name, "relation": c.relation, "phone": c.phone} for c in user.emergency_contacts.all()
            ],
            "access_log": [
                {"at": e.at, "action": e.action, "by_role": getattr(e.actor, "role", None)}
                for e in user.audit_entries.select_related("actor")
            ],
        }
        if user.is_patient:
            from apps.health.exports import patient_export

            data["health"] = patient_export(user)
        body = json.dumps(data, default=str, indent=2, ensure_ascii=False)
        audit(request, "account.exported", subject=user)
        response = HttpResponse(body, content_type="application/json; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="strokecare-my-data.json"'
        return response


class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonalEmergencyContact
        fields = ["id", "name", "relation", "phone"]

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Write a name.")
        return value.strip()

    def validate_phone(self, value):
        value = value.strip()
        if not re.fullmatch(r"\+?[0-9][0-9 ()-]{1,22}", value):
            raise serializers.ValidationError("Use digits, spaces and an optional + at the start.")
        return value


class EmergencyContactsView(APIView):
    """The signed-in person's own people to call in an emergency."""

    def get(self, request):
        return Response({"results": EmergencyContactSerializer(request.user.emergency_contacts.all(), many=True).data})

    def post(self, request):
        if request.user.emergency_contacts.count() >= limits.PERSONAL_EMERGENCY_CONTACTS_MAX:
            raise ValidationError({"detail": [f"You can keep up to {limits.PERSONAL_EMERGENCY_CONTACTS_MAX} people."]})
        ser = EmergencyContactSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save(user=request.user)
        return Response(ser.data, status=status.HTTP_201_CREATED)


class EmergencyContactDetailView(APIView):
    def delete(self, request, contact_id):
        deleted, _ = request.user.emergency_contacts.filter(id=contact_id).delete()
        if not deleted:
            raise NotFound()
        return Response(status=status.HTTP_204_NO_CONTENT)
