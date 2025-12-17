# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create static directory if it doesn't exist (prevents STATICFILES_DIRS warning)
RUN mkdir -p static staticfiles

# Collect static files
RUN python manage.py collectstatic --noinput || true

# Expose port (Railway sets PORT dynamically)
EXPOSE 8000

# Run gunicorn (use shell form to access PORT env var)
# Railway will set PORT environment variable
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8000} --workers 3 --timeout 120 --access-logfile - --error-logfile - velocity_media.wsgi:application"]

