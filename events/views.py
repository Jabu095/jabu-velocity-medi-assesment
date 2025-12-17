"""
API Views for the Events endpoint.

Implements the minimal REST API as specified:
- GET /api/events - List all events
- GET /api/events?city=Johannesburg - Filter by city
- Pagination is included via Django REST Framework settings
"""

from rest_framework import generics, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from .models import Event
from .serializers import EventSerializer, EventDetailSerializer, EventListSerializer
from .filters import EventFilter
from .pagination import EnhancedPageNumberPagination


class EventListView(generics.ListAPIView):
    """
    List all events with optional filtering.
    
    Endpoints:
        GET /api/events/
        GET /api/events/?city=Johannesburg
        GET /api/events/?city=Pretoria
        GET /api/events/?category=Music
        GET /api/events/?search=concert
    
    Pagination:
        Results are paginated (20 per page by default).
        Use ?page=N to navigate pages.
    
    Response Format:
        {
            "count": 100,
            "next": "http://localhost:8000/api/events/?page=2",
            "previous": null,
            "results": [
                {
                    "id": 1,
                    "title": "Event Title",
                    "start_date": "2024-12-20T19:00:00Z",
                    "venue_name": "Venue Name",
                    "city": "Johannesburg",
                    "category": "Music",
                    "event_url": "https://..."
                },
                ...
            ]
        }
    """
    
    queryset = Event.objects.all()
    serializer_class = EventListSerializer
    pagination_class = EnhancedPageNumberPagination  
   
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = EventFilter 
    search_fields = ['title', 'venue_name', 'description', 'category']
    ordering_fields = ['start_date', 'created_at', 'title', 'city']
    ordering = ['-created_at']


class EventDetailView(generics.RetrieveAPIView):
    """
    Retrieve a single event by ID.
    
    Endpoint:
        GET /api/events/{id}/
    
    Returns full event details including raw_payload.
    """
    
    queryset = Event.objects.all()
    serializer_class = EventDetailSerializer


class EventStatsView(APIView):
    """
    Get statistics about stored events.
    
    Endpoint:
        GET /api/events/stats/
    
    Returns:
        {
            "total_events": 150,
            "by_city": {
                "Johannesburg": 100,
                "Pretoria": 50
            },
            "by_category": {
                "Music": 30,
                "Nightlife": 45,
                ...
            },
            "by_source": {
                "google_places": 150
            }
        }
    """
    
    def get(self, request):
        from django.db.models import Count
        
        # Total count
        total = Event.objects.count()
        
        # Count by city
        city_counts = dict(
            Event.objects.values('city')
            .annotate(count=Count('id'))
            .values_list('city', 'count')
        )
        
        # Count by category
        category_counts = dict(
            Event.objects.values('category')
            .annotate(count=Count('id'))
            .values_list('category', 'count')
        )
        
        # Count by source
        source_counts = dict(
            Event.objects.values('source')
            .annotate(count=Count('id'))
            .values_list('source', 'count')
        )
        
        return Response({
            'total_events': total,
            'by_city': city_counts,
            'by_category': category_counts,
            'by_source': source_counts,
        })

