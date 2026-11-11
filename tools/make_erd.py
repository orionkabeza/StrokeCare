#!/usr/bin/env python3
"""Draw the database design (ERD) straight from the Django models, as a Mermaid diagram.

Owner: Orion Kabeza (DevOps) · AI-assisted draft, see AI_USE_LOG.md
Run from the backend folder:  python ../tools/make_erd.py > ../docs/erd.mmd
Because it reads the real models, the diagram can never drift from the database.
"""
import os
import sys

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "strokecare.settings")
os.environ.setdefault("DJANGO_SECRET_KEY", "erd-only")
os.environ.setdefault("DATABASE_URL", "postgres://x:x@localhost/x")

import django  # noqa: E402

django.setup()
from django.apps import apps  # noqa: E402

OURS = {"accounts", "care", "health", "content", "audit", "messaging", "family", "community", "recovery"}
print("erDiagram")
for model in apps.get_models():
    if model._meta.app_label not in OURS:
        continue
    name = model.__name__
    print(f"  {name} {{")
    for f in model._meta.concrete_fields:
        kind = f.get_internal_type()
        flag = " PK" if f.primary_key else (" FK" if f.is_relation else "")
        print(f"    {kind} {f.name}{flag}")
    print("  }")
for model in apps.get_models():
    if model._meta.app_label not in OURS:
        continue
    for f in model._meta.concrete_fields:
        if f.is_relation and f.related_model._meta.app_label in OURS and not f.primary_key:
            one = "o|" if f.one_to_one else "}o"
            print(f"  {f.related_model.__name__} ||--{one} {model.__name__} : \"{f.name}\"")
