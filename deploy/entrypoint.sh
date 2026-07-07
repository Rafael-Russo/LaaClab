#!/bin/sh
# Container entrypoint: wait for the DB, apply migrations, collect static,
# seed demo data, then run whatever command was passed (gunicorn or runserver).
set -e

# Wait for the database (parsed from DATABASE_URL) to accept connections.
python - <<'PY'
import os, re, socket, sys, time

url = os.environ.get("DATABASE_URL", "")
if url.startswith("mysql"):
    m = re.search(r"@([^:/]+):?(\d+)?", url)
    host = m.group(1) if m else "db"
    port = int(m.group(2) or 3306)
    for _ in range(60):
        try:
            socket.create_connection((host, port), timeout=2).close()
            print(f"database {host}:{port} is up")
            break
        except OSError:
            print(f"waiting for database {host}:{port} ...")
            time.sleep(2)
    else:
        print("database never became reachable", file=sys.stderr)
        sys.exit(1)
PY

if [ "${MIGRATE:-1}" = "1" ]; then
    echo "Applying migrations..."
    python manage.py migrate --noinput
fi

# Skip in dev (COLLECTSTATIC=0): runserver+DEBUG serves static directly, and
# WhiteNoise's utime step fails on bind-mounted source. Runs by default (prod).
if [ "${COLLECTSTATIC:-1}" = "1" ]; then
    echo "Collecting static files..."
    python manage.py collectstatic --noinput
fi

if [ "${SEED_ON_START:-1}" = "1" ]; then
    echo "Seeding demo data..."
    python manage.py seed || echo "seed skipped (continuing)"
fi

exec "$@"
