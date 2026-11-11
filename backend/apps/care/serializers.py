"""Owner: Kenneth Master (System architect) · AI-assisted draft, see AI_USE_LOG.md"""
from rest_framework import serializers

from .models import Relation
from .scopes import ALLOWED_SCOPES, DEFAULT_SCOPES


class LinkSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    relation = serializers.CharField()
    status = serializers.CharField()
    label = serializers.CharField()
    scopes = serializers.ListField(child=serializers.CharField())
    created_at = serializers.DateTimeField()
    activated_at = serializers.DateTimeField()
    invite_expires_at = serializers.DateTimeField()
    other_party = serializers.SerializerMethodField()
    my_side = serializers.SerializerMethodField()

    def get_my_side(self, obj) -> str:
        return "patient" if obj.patient_id == self.context["request"].user.id else "member"

    def get_other_party(self, obj):
        me = self.context["request"].user
        other = obj.member if obj.patient_id == me.id else obj.patient
        return None if other is None else {"id": other.id, "display_name": other.display_name}


class InviteSerializer(serializers.Serializer):
    relation = serializers.ChoiceField(choices=Relation.values)
    label = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
    scopes = serializers.ListField(child=serializers.CharField(), required=False)

    def validate(self, attrs):
        relation = attrs["relation"]
        scopes = attrs["scopes"] if "scopes" in attrs else DEFAULT_SCOPES[relation]
        unknown = set(scopes) - ALLOWED_SCOPES[relation]
        if unknown:
            raise serializers.ValidationError({"scopes": [f"Not allowed for a {relation}: {sorted(unknown)}"]})
        if not scopes:
            raise serializers.ValidationError({"scopes": ["Choose at least one thing to share."]})
        attrs["scopes"] = sorted(set(scopes))
        return attrs


class RedeemSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=32)


class ScopesSerializer(serializers.Serializer):
    scopes = serializers.ListField(child=serializers.CharField(), allow_empty=False)
