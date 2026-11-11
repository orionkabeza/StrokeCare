# Owner: Orion Kabeza (DevOps) · AI-assisted draft, see AI_USE_LOG.md
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "strokecare.settings")
application = get_wsgi_application()
