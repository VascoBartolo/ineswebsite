#!/bin/sh
set -e

# In cloud (Azure Container Apps) the service-account key is injected as a secret env var
# instead of a mounted file. Materialize it to disk before the app imports calendar_service.
# Local docker-compose mounts credentials.json directly, so this is a no-op there.
# Prefer base64 (GOOGLE_CREDENTIALS_B64) — a single safe line, easy to pass as an ACA secret;
# fall back to raw JSON (GOOGLE_CREDENTIALS_JSON) if that's what's provided.
CRED_FILE="${GOOGLE_CREDENTIALS_FILE:-/app/credentials.json}"
if [ ! -f "$CRED_FILE" ]; then
  if [ -n "$GOOGLE_CREDENTIALS_B64" ]; then
    echo "[entrypoint] Writing service-account credentials from GOOGLE_CREDENTIALS_B64..."
    echo "$GOOGLE_CREDENTIALS_B64" | base64 -d > "$CRED_FILE"
  elif [ -n "$GOOGLE_CREDENTIALS_JSON" ]; then
    echo "[entrypoint] Writing service-account credentials from GOOGLE_CREDENTIALS_JSON..."
    printf '%s' "$GOOGLE_CREDENTIALS_JSON" > "$CRED_FILE"
  fi
fi

echo "[entrypoint] Waiting for database..."
until python -c "
import os, psycopg2
psycopg2.connect(os.environ.get('DATABASE_URL', 'postgresql://ibnutricao:ibnutricao@postgres:5432/ibnutricao'))
" 2>/dev/null; do
  sleep 1
done

echo "[entrypoint] Initializing database schema..."
python -c "
from app import app, db
with app.app_context():
    db.create_all()
print('[entrypoint] Schema ready.')
"

exec gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 60 app:app
