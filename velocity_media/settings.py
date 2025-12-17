"""
Django settings for velocity_media project.

This project aggregates event data from Google APIs for the
Johannesburg and Pretoria metropolitan areas.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')

# Allow Railway and other common hosting platforms
# ALLOWED_HOSTS configuration
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Add Railway domain automatically if RAILWAY_PUBLIC_DOMAIN is set
if os.getenv('RAILWAY_PUBLIC_DOMAIN'):
    ALLOWED_HOSTS.append(os.getenv('RAILWAY_PUBLIC_DOMAIN'))

# Add Railway service URL if available
if os.getenv('RAILWAY_SERVICE_URL'):
    from urllib.parse import urlparse
    parsed = urlparse(os.getenv('RAILWAY_SERVICE_URL'))
    if parsed.hostname:
        ALLOWED_HOSTS.append(parsed.hostname)

if not DEBUG:
    pass

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'django_filters',  # Advanced filtering for DRF
    'corsheaders',  # CORS support for frontend
    'health_check',  # Health monitoring
    'health_check.db',  # Database health check
    'django_extensions',  # Development tools
    # Local apps
    'events',
]

# Add debug toolbar only in development
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']

MIDDLEWARE = [
    'velocity_media.middleware.RailwayHostMiddleware',  # Railway domain validation (MUST be before SecurityMiddleware)
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Static files serving - must be after SecurityMiddleware
    'corsheaders.middleware.CorsMiddleware',  # CORS - must be before CommonMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Add debug toolbar middleware only in development
if DEBUG:
    # Place debug toolbar middleware early but after security middleware
    MIDDLEWARE.insert(1, 'debug_toolbar.middleware.DebugToolbarMiddleware')

ROOT_URLCONF = 'velocity_media.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'velocity_media.wsgi.application'

# Database - SQLite3 as per project requirements
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Johannesburg'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
# Only add to STATICFILES_DIRS if directory exists (prevents warnings in production)
static_dir = BASE_DIR / 'static'
STATICFILES_DIRS = [static_dir] if static_dir.exists() else []
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise for efficient static file serving in production
# Why loved: Serves static files efficiently from Django, handles compression and caching
# Using CompressedStaticFilesStorage (without manifest) for simpler deployment
# Manifest storage requires proper manifest.json generation which can be tricky in Docker
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# WhiteNoise configuration
WHITENOISE_USE_FINDERS = True  # Allow WhiteNoise to find static files during development
WHITENOISE_AUTOREFRESH = DEBUG  # Auto-refresh in development
# WhiteNoise will automatically use STATIC_ROOT, no need to set WHITENOISE_ROOT

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework configuration
REST_FRAMEWORK = {
    # Note: Individual views can override with custom pagination classes
    # Enhanced pagination is used in EventListView
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    # django-filter integration - powerful declarative filtering
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
}

# Google API Configuration
GOOGLE_PLACES_API_KEY = os.getenv('GOOGLE_PLACES_API_KEY', '')
SEARCH_RADIUS_METERS = int(os.getenv('SEARCH_RADIUS_METERS', 50000))

# Target cities for event search
TARGET_CITIES = {
    'johannesburg': {
        'latitude': -26.2041,
        'longitude': 28.0473,
        'canonical_name': 'Johannesburg',
    },
    'pretoria': {
        'latitude': -25.7461,
        'longitude': 28.1881,
        'canonical_name': 'Pretoria',
    },
}

# JWT Configuration
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
}

# ============================================================================
# Popular Django Packages Configuration
# ============================================================================

# CORS Headers - Allow frontend to access API
# Why loved: Solves CORS issues with minimal configuration
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React/Next.js default
    "http://localhost:8000",  # Django dev server
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
]

# Allow credentials (cookies, authorization headers)
CORS_ALLOW_CREDENTIALS = True

# In development, allow all origins (remove in production!)
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True

# Debug Toolbar Configuration
# Why loved: Shows SQL queries, templates, signals, performance metrics
if DEBUG:
    INTERNAL_IPS = [
        '127.0.0.1',
        'localhost',
    ]
    
    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG and not request.path.startswith('/api/'),
        'DISABLE_PANELS': {
            'debug_toolbar.panels.profiling.ProfilingPanel',  # Disable profiling to prevent recursion errors
        },
        'SHOW_TEMPLATE_CONTEXT': True,
        'RENDER_PANELS': True,
    }

# Health Check Configuration
# Why loved: Standard endpoints for monitoring, database checks, etc.
HEALTH_CHECK = {
    'DISK_USAGE_MAX': 90,  # percent
    'MEMORY_MIN': 100,  # in MB
}

