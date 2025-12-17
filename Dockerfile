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

# Copy project files (including static directory with CSS/JS)
COPY . .

# Ensure staticfiles output directory exists
RUN mkdir -p staticfiles

# Verify source static files exist
RUN echo "=== Source static files ===" && \
    ls -la /app/static/ && \
    ls -la /app/static/css/ && \
    ls -la /app/static/js/

# Collect static files (must run after copying project files)
# Set environment variables for proper static file collection
ENV DJANGO_SETTINGS_MODULE=velocity_media.settings
ENV DEBUG=False
ENV SECRET_KEY=build-time-key-not-used-in-production

# Collect static files - verify it succeeds and shows output
RUN python manage.py collectstatic --noinput --verbosity 2

# Verify static files were collected
RUN echo "=== Collected staticfiles ===" && \
    ls -la /app/staticfiles/ && \
    echo "=== CSS files ===" && \
    ls -la /app/staticfiles/css/ && \
    echo "=== JS files ===" && \
    ls -la /app/staticfiles/js/

# Copy and make start script executable
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Expose port (Railway sets PORT dynamically)
EXPOSE 8000

# Use start script to handle PORT variable properly
CMD ["/app/start.sh"]

