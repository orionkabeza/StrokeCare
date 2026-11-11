# Owner: Orion Kabeza (DevOps) · AI-assisted draft, see AI_USE_LOG.md
# One image, one link: the API under /api/ and the web app at /. The same image runs the scheduler worker.
# The web app is plain HTML, CSS and JavaScript (frontend/site), so there is no Node build stage: the files are
# copied in as they are and Django serves them.
# NOTE: written but not yet built in the session that created it (no Docker daemon there). Build it once.

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 FRONTEND_DIST=/app/frontend_dist
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY frontend/site/ /app/frontend_dist/
RUN useradd --create-home app && chown -R app /app
USER app
# collectstatic needs settings to load, so it gets throwaway values that exist only for this build step
RUN DJANGO_SECRET_KEY=build-only DATABASE_URL=postgres://x:x@localhost/x python manage.py collectstatic --noinput
EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py seed_reference && gunicorn strokecare.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --access-logfile -"]
