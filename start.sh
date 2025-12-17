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
# Default admin user for demo purposes
echo "Checking for superuser..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'test1234')
    print('Superuser created: admin')
else:
    print('Superuser already exists')
"

echo "Starting Gunicorn on port ${PORT}..."

# Start Gunicorn
exec gunicorn \
    --bind "0.0.0.0:${PORT}" \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    velocity_media.wsgi:application

