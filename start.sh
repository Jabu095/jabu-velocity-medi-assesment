#!/bin/bash
# Start script for Railway deployment
# This ensures PORT environment variable is properly handled

set -e

# Default to port 8000 if PORT is not set
PORT=${PORT:-8000}

# Run database migrations (important for fresh deployments)
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files (in case any are missing)
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create superuser if DJANGO_SUPERUSER_USERNAME is set and user doesn't exist
if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
    echo "Checking for superuser..."
    python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists():
    User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')
    print('Superuser created')
else:
    print('Superuser already exists')
"
fi

echo "Starting Gunicorn on port ${PORT}..."

# Start Gunicorn
exec gunicorn \
    --bind "0.0.0.0:${PORT}" \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    velocity_media.wsgi:application

