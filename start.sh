#!/bin/bash
# Start script for Railway deployment
# This ensures PORT environment variable is properly handled

set -e

# Default to port 8000 if PORT is not set
PORT=${PORT:-8000}

# Start Gunicorn
exec gunicorn \
    --bind "0.0.0.0:${PORT}" \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    velocity_media.wsgi:application

