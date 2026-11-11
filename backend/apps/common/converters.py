"""Owner: Kenneth Master (System architect) · AI-assisted draft, see AI_USE_LOG.md

URL piece for "whose record is this": the word `me` or a UUID. Anything else is a 404.
"""
from django.urls import register_converter


class PatientRefConverter:
    regex = r"me|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"

    def to_python(self, value):
        return value.lower()

    def to_url(self, value):
        return str(value)


register_converter(PatientRefConverter, "patient")
