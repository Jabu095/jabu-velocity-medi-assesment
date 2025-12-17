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
from .ai_views import (
    natural_language_search,
    recommendations,
    summarize_event,
    categorize_event
)
from .chat_views import (
    chat_send_message,
    chat_conversations,
    chat_messages,
    chat_delete_conversation,
    chat_token_usage
)

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
    
    # AI-powered endpoints (authenticated)
    path('ai/search/', natural_language_search, name='ai-natural-search'),
    path('ai/recommendations/', recommendations, name='ai-recommendations'),
    path('ai/events/<int:event_id>/summarize/', summarize_event, name='ai-summarize'),
    path('ai/events/<int:event_id>/categorize/', categorize_event, name='ai-categorize'),
    
    # AI Chat endpoints (authenticated)
    path('ai/chat/', chat_send_message, name='ai-chat-send'),
    path('ai/chat/conversations/', chat_conversations, name='ai-chat-conversations'),
    path('ai/chat/conversations/<int:conversation_id>/messages/', chat_messages, name='ai-chat-messages'),
    path('ai/chat/conversations/<int:conversation_id>/', chat_delete_conversation, name='ai-chat-delete'),
    path('ai/chat/token-usage/', chat_token_usage, name='ai-chat-token-usage'),
]

