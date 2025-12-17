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

# Collect static files (must run after copying project files)
# Set DJANGO_SETTINGS_MODULE if not set
ENV DJANGO_SETTINGS_MODULE=velocity_media.settings
# Set DEBUG=False for production static file collection
ENV DEBUG=False
# Collect static files - this must succeed
RUN python manage.py collectstatic --noinput

# Copy and make start script executable
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Expose port (Railway sets PORT dynamically)
EXPOSE 8000

# Use start script to handle PORT variable properly
CMD ["/app/start.sh"]

