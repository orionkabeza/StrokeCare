"""One error shape for the whole API, written as plain sentences.

Owner: Kenneth Master (System architect) · AI-assisted draft, see AI_USE_LOG.md

    {"error": {"code": "consent_required", "message": "...", "fields": {...}}}

`fields` appears only for validation errors.
"""
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.views import exception_handler as drf_exception_handler


class ConsentRequired(PermissionDenied):
    default_detail = "Please read and accept the consent notice before using this feature."
    default_code = "consent_required"


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    data = response.data
    if isinstance(exc, ValidationError):
        fields = data if isinstance(data, dict) else {"non_field_errors": data}
        response.data = {
            "error": {"code": "validation_error", "message": "Some details need fixing.", "fields": fields}
        }
        return response
    codes = exc.get_codes() if hasattr(exc, "get_codes") else "error"
    code = codes if isinstance(codes, str) else "error"
    message = data.get("detail") if isinstance(data, dict) else None
    response.data = {"error": {"code": code, "message": str(message or "Something went wrong.")}}
    return response
