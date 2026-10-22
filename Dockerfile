FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY requirements.txt requirements-deploy.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt -r requirements-deploy.txt

COPY app.py ./
COPY templates ./templates
COPY static ./static

# Cloud Run provides PORT; Gunicorn listens on all container interfaces.
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 8 --timeout 120 app:app"]
