"""Voice notes: record on the phone, listen in the clinic.

Owner: Aubin Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md
Safety rules: only audio is accepted (checked by the file's first bytes, not only its name); size and length are
capped; listening by anyone other than the patient is audited like every other access.
"""
from django.conf import settings
from django.http import Http404, HttpResponse
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.care import scopes
from apps.common.access import PatientScopedMixin

from .models import VoiceNote

# What browsers' MediaRecorder produces, and how each format's bytes begin.
ALLOWED = {
    "audio/webm": lambda b: b[:4] == b"\x1a\x45\xdf\xa3",
    "audio/ogg": lambda b: b[:4] == b"OggS",
    "audio/mp4": lambda b: b[4:8] == b"ftyp",
    "audio/mpeg": lambda b: b[:3] == b"ID3" or b[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"),
    "audio/wav": lambda b: b[:4] == b"RIFF" and b[8:12] == b"WAVE",
}


def _row(n):
    return {
        "id": n.id, "context": n.context, "content_type": n.content_type, "size_bytes": n.size_bytes,
        "duration_seconds": n.duration_seconds, "created_at": n.created_at,
        "recorded_by_role": n.recorded_by.role if n.recorded_by else None,
        "recorded_by_name": n.recorded_by.display_name if n.recorded_by else None,
    }  # fmt: skip


class VoiceNotesView(PatientScopedMixin, APIView):
    parser_classes = [MultiPartParser]
    scope_by_method = {"GET": scopes.VIEW_NOTES, "POST": scopes.ADD_NOTES}

    def get(self, request, patient_ref):
        notes = self.access.subject.voice_notes.defer("audio").select_related("recorded_by")[:50]
        return Response({"results": [_row(n) for n in notes]})

    def post(self, request, patient_ref):
        upload = request.FILES.get("audio")
        if upload is None:
            raise ValidationError({"audio": ["Attach a recording."]})
        if upload.size > settings.VOICE_NOTE_MAX_BYTES:
            raise ValidationError({"audio": ["This recording is too long. Keep it under three minutes."]})
        content_type = (upload.content_type or "").split(";")[0].strip().lower()
        data = upload.read()
        check = ALLOWED.get(content_type)
        if check is None or not check(data):
            raise ValidationError({"audio": ["Only voice recordings can be sent here."]})
        duration = request.data.get("duration_seconds")
        try:
            duration = int(duration) if duration not in (None, "") else None
        except ValueError:
            raise ValidationError({"duration_seconds": ["Use a whole number of seconds."]})
        if duration is not None and not 0 < duration <= settings.VOICE_NOTE_MAX_SECONDS:
            raise ValidationError({"duration_seconds": ["Keep recordings under three minutes."]})
        context = request.data.get("context") or VoiceNote.Context.GENERAL
        if context not in VoiceNote.Context.values:
            raise ValidationError({"context": [f"Use one of: {', '.join(VoiceNote.Context.values)}."]})
        note = VoiceNote.objects.create(
            patient=self.access.subject, recorded_by=request.user, context=context, audio=data,
            content_type=content_type, size_bytes=len(data), duration_seconds=duration,
        )  # fmt: skip
        return Response(_row(note), status=status.HTTP_201_CREATED)


class VoiceNoteAudioView(PatientScopedMixin, APIView):
    scope_by_method = {"GET": scopes.VIEW_NOTES, "DELETE": scopes.ADD_NOTES}

    def _get(self, note_id):
        note = VoiceNote.objects.filter(id=note_id, patient=self.access.subject).first()
        if note is None:
            raise Http404
        return note

    def get(self, request, patient_ref, note_id):
        note = self._get(note_id)
        response = HttpResponse(bytes(note.audio), content_type=note.content_type)
        response["Content-Disposition"] = "inline"
        response["X-Content-Type-Options"] = "nosniff"
        return response

    def delete(self, request, patient_ref, note_id):
        note = self._get(note_id)
        if not self.access.is_self and note.recorded_by_id != request.user.id:
            raise PermissionDenied("You can remove only recordings you made.", code="not_yours")
        note.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
