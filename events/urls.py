"""
URL configuration for the Events API.

Routes:
    GET /api/events/          - List all events (with optional filters)
    GET /api/events/{id}/     - Get event details
    GET /api/events/stats/    - Get event statistics
    POST /api/auth/register/  - Register new user
    POST /api/auth/login/     - Login user
    POST /api/auth/refresh/   - Refresh access token
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import EventListView, EventDetailView, EventStatsView
from .auth_views import register, login, refresh_token

app_name = 'events'

urlpatterns = [
    # Event endpoints (protected)
    path('events/', EventListView.as_view(), name='event-list'),
    path('events/stats/', EventStatsView.as_view(), name='event-stats'),
    path('events/<int:pk>/', EventDetailView.as_view(), name='event-detail'),
    # Authentication endpoints (public)
    path('auth/register/', register, name='register'),
    path('auth/login/', login, name='login'),
    path('auth/refresh/', refresh_token, name='refresh-token'),
    # JWT token endpoints (for compatibility)
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

