#!/bin/sh

# Exit immediately if any command returns a non-zero status code
set -e

# Await database readiness using a quick python check
if [ -n "$DATABASE_URL" ]; then
    echo "Awaiting database connectivity..."
    python -c "
import urllib.parse, sys, socket, time
url = urllib.parse.urlparse('$DATABASE_URL')
if url.hostname:
    port = url.port or 5432
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect((url.hostname, port))
            s.close()
            break
        except Exception:
            time.sleep(1)
"
    echo "Database is active."
fi

# Execute migrations and collect static assets when launching django web server
if [ "$1" = "gunicorn" ] || [ "$1" = "python" -a "$2" = "manage.py" -a "$3" = "runserver" ]; then
    echo "Running database migrations..."
    python manage.py migrate --noinput
    echo "Collecting static files..."
    python manage.py collectstatic --noinput
fi

echo "Running command: $@"
exec "$@"
