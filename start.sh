#!/bin/bash
set -e

echo "Waiting for database..."
python -c "
import os, sys, time
import psycopg

host     = os.environ.get('DB_HOST', 'localhost')
port     = os.environ.get('DB_PORT', '5432')
user     = os.environ.get('DB_USER', '')
password = os.environ.get('DB_PASSWORD', '')
dbname   = os.environ.get('DB_NAME', '')

for attempt in range(1, 31):
    try:
        conn = psycopg.connect(
            host=host, port=port, user=user,
            password=password, dbname=dbname, connect_timeout=3,
        )
        conn.close()
        print('Database ready.')
        sys.exit(0)
    except Exception as exc:
        print(f'Attempt {attempt}/30: DB not ready — {exc}')
        time.sleep(2)

print('ERROR: Database did not become ready after 60 s.')
sys.exit(1)
"

echo "Ensuring sites migrations consistency..."
python manage.py ensure_sites_migrations

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting gunicorn..."
exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 2 \
    --timeout 120 \
    --access-logfile -
