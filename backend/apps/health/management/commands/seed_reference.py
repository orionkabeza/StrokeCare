"""Load the check-in questions that ship with the app. Safe to run on every deploy.

Owner: Erica Rurangwa Sheja (Product Owner) · AI-assisted draft, see AI_USE_LOG.md
It creates missing questions and phrases. For rows still in DRAFT it also adds languages that are missing
(new translations), never replacing text someone already wrote. Reviewed rows are never touched.
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.content.models import EducationItem, EducationTranslation, TalkPhrase, Topic
from apps.health.models import CheckInQuestion

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "checkin_questions.json"
TALK_FIXTURE = Path(__file__).resolve().parents[3] / "content" / "fixtures" / "talk_phrases.json"
TOPICS_FIXTURE = Path(__file__).resolve().parents[3] / "content" / "fixtures" / "topics.json"
EDUCATION_FIXTURE = Path(__file__).resolve().parents[3] / "content" / "fixtures" / "education.json"


class Command(BaseCommand):
    help = "Create the draft check-in questions and talk-board phrases if they do not exist yet."

    def handle(self, *args, **options):
        created = 0
        for row in json.loads(FIXTURE.read_text(encoding="utf-8")):
            q, was_created = CheckInQuestion.objects.get_or_create(
                code=row["code"],
                defaults={**{k: v for k, v in row.items() if k != "code"}, "status": CheckInQuestion.Status.DRAFT},
            )
            created += was_created
            if not was_created and q.status == CheckInQuestion.Status.DRAFT:
                q.prompt = {**row["prompt"], **{k: v for k, v in q.prompt.items() if v}}
                by_value = {c["value"]: c for c in row.get("choices", [])}
                q.choices = [
                    {**c, "label": {**by_value.get(c["value"], {}).get("label", {}), **{k: v for k, v in c.get("label", {}).items() if v}}}
                    for c in q.choices
                ]
                if row.get("follow_up") and not q.follow_up:
                    q.follow_up, q.follow_up_when = row["follow_up"], row.get("follow_up_when", [])
                q.save(update_fields=["prompt", "choices", "follow_up", "follow_up_when"])
        self.stdout.write(self.style.SUCCESS(f"Check-in questions: {created} created, rest already present."))
        phrases = 0
        for row in json.loads(TALK_FIXTURE.read_text(encoding="utf-8")):
            p, was_created = TalkPhrase.objects.get_or_create(
                code=row["code"], defaults={**{k: v for k, v in row.items() if k != "code"}, "status": "draft"}
            )
            phrases += was_created
            if not was_created and p.status == "draft":
                p.label = {**row["label"], **{k: v for k, v in p.label.items() if v}}
                p.save(update_fields=["label"])
        self.stdout.write(self.style.SUCCESS(f"Talk-board phrases: {phrases} created, rest already present."))
        topics = 0
        for row in json.loads(TOPICS_FIXTURE.read_text(encoding="utf-8")):
            top, was_created = Topic.objects.get_or_create(
                slug=row["slug"], defaults={"order": row["order"], "name": row["name"], "status": "draft"}
            )
            topics += was_created
            if not was_created and top.status == "draft":
                top.name = {**row["name"], **{k: v for k, v in top.name.items() if v}}
                top.save(update_fields=["name"])
        self.stdout.write(self.style.SUCCESS(f"Learn topics: {topics} created, rest already present."))
        items = 0
        topic_by_slug = {t.slug: t for t in Topic.objects.all()}
        for row in json.loads(EDUCATION_FIXTURE.read_text(encoding="utf-8")):
            item, was_created = EducationItem.objects.get_or_create(
                slug=row["slug"],
                defaults={
                    "kind": row["kind"], "topic": topic_by_slug.get(row["topic"]), "audience": row["audience"],
                    "source_name": row["source_name"], "source_url": row["source_url"], "status": "draft",
                    "is_published": True,
                },
            )  # fmt: skip
            items += was_created
            if item.status != "draft":
                continue
            for loc in ("en", "fr", "rw"):
                if loc in row:
                    EducationTranslation.objects.get_or_create(item=item, locale=loc, defaults={**row[loc], "status": "draft"})
        self.stdout.write(self.style.SUCCESS(f"Learn items: {items} created, rest already present."))
