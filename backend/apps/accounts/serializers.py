"""Owner: Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md"""
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import SELF_REGISTER_ROLES, AccessibilityPreference, ConsentKind, Language, Role, User


def validate_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        raise serializers.ValidationError("This time zone is not recognised.")
    return value


def consent_status(user: User) -> dict:
    """Which notices this person must accept, at which version, and whether they have."""
    return {
        kind: {"version": settings.CONSENT_VERSIONS[kind], "granted": user.has_active_consent(kind)}
        for kind in user.required_consents()
    }


class UserSerializer(serializers.ModelSerializer):
    is_verified_professional = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "display_name", "role", "preferred_language", "timezone",
            "is_verified_professional", "created_at",
        ]  # fmt: skip
        read_only_fields = ["id", "email", "role", "created_at"]

    def get_is_verified_professional(self, obj) -> bool:
        return obj.is_verified_professional

    def validate_timezone(self, value):
        return validate_timezone(value)


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    display_name = serializers.CharField(max_length=120)
    role = serializers.ChoiceField(choices=[r.value for r in SELF_REGISTER_ROLES])
    preferred_language = serializers.ChoiceField(choices=Language.values, default=Language.EN)
    timezone = serializers.CharField(default="Africa/Kigali", validators=[validate_timezone])

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate(self, attrs):
        probe = User(email=attrs["email"], display_name=attrs["display_name"])
        try:
            validate_password(attrs["password"], user=probe)
        except Exception as exc:  # django ValidationError -> DRF
            raise serializers.ValidationError({"password": list(getattr(exc, "messages", [str(exc)]))})
        return attrs

    def create(self, validated):
        return User.objects.create_user(**validated)


class LoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        attrs["email"] = (attrs.get("email") or "").strip().lower()
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        data["consents"] = consent_status(self.user)
        return data


class ConsentActionSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=ConsentKind.values)
    accept = serializers.BooleanField()


class AccessibilityPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessibilityPreference
        exclude = ["id", "user"]
        read_only_fields = ["updated_at"]


class DeleteAccountSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)
