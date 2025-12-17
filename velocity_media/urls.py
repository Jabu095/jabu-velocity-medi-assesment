"""
URL configuration for velocity_media project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from events.frontend_views import login_view, register_view, dashboard_view, event_detail_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('events.urls')),
    # Health check endpoints (django-health-check)
    path('health/', include('health_check.urls')),
    # Frontend routes
    path('', dashboard_view, name='home'),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('events/<int:event_id>/', event_detail_view, name='event-detail'),
]

# Debug toolbar URLs (only in development)
if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass

