"""
Frontend views for the web application.

Serves HTML templates for login, dashboard, and event browsing.
"""

from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required


def login_view(request):
    """Render the login page."""
    return render(request, 'events/login.html')


def register_view(request):
    """Render the registration page."""
    return render(request, 'events/register.html')


def dashboard_view(request):
    """Render the main dashboard with events."""
    return render(request, 'events/dashboard.html')


@login_required
def event_detail_view(request, event_id):
    """Render the event detail page."""
    return render(request, 'events/event_detail.html', {'event_id': event_id})


@login_required
def chat_view(request):
    """Render the AI chat page."""
    return render(request, 'events/chat.html')

