"""Owner: Axel Mfura (Backend and database) · AI-assisted draft, see AI_USE_LOG.md

Everything health-related we hold about one person, for the "download my data" right.
"""
from .models import MedicationDose, Reminder
from .serializers import ReadingSerializer, ReminderSerializer, TaskSerializer, serialise_checkin


def patient_export(user) -> dict:
    plan = getattr(user, "plan", None)
    return {
        "blood_pressure_readings": ReadingSerializer(user.readings.select_related("entered_by"), many=True).data,
        "recovery_plan": None
        if plan is None
        else {
            "title": plan.title,
            "notes_for_patient": plan.notes_for_patient,
            "tasks": [
                {**TaskSerializer(t).data, "ticks": [{"date": l.date, "note": l.note} for l in t.logs.all()]}
                for t in plan.tasks.prefetch_related("logs")
            ],
        },
        "daily_check_ins": [serialise_checkin(c) for c in user.checkins.select_related("entered_by")],
        "reminders": ReminderSerializer(Reminder.objects.filter(user=user), many=True).data,
        "medicines": [
            {"name": m.name, "dose": m.dose, "instructions": m.instructions, "times": m.times,
             "days_of_week": m.days_of_week, "start_date": m.start_date, "end_date": m.end_date, "is_active": m.is_active,
             "marked_taken": [{"date": d.date, "time": d.time} for d in MedicationDose.objects.filter(medication=m)]}
            for m in user.medications.all()
        ],  # fmt: skip
        "voice_notes": [
            {"context": n.context, "duration_seconds": n.duration_seconds, "created_at": n.created_at,
             "download": f"/api/v1/patients/me/voice-notes/{n.id}/"}
            for n in user.voice_notes.defer("audio")
        ],
        "care_calendar": [
            {"title": e.title, "kind": e.kind, "starts_at": e.starts_at, "location": e.location, "notes": e.notes}
            for e in user.care_events.all()
        ],
        "handover_notes": [{"text": n.text, "created_at": n.created_at} for n in user.handover_notes.all()],
        "messages": [
            {"body": m.body, "created_at": m.created_at, "from_role": m.sender.role if m.sender else None}
            for m in user.thread_messages.select_related("sender")
        ],
        "home_visits": [
            {"visited_at": v.visited_at, "checklist": v.checklist, "note": v.note} for v in user.home_visits.all()
        ],  # fmt: skip
        "visit_questions": [
            {"text": q.text, "created_at": q.created_at, "discussed_at": q.discussed_at} for q in user.visit_questions.all()
        ],
    }
