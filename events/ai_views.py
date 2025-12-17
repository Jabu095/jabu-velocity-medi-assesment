"""
AI-powered API views for enhanced event discovery.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from .models import Event
from .serializers import EventListSerializer
from .ai_services import (
    NaturalLanguageSearch,
    EventRecommendationEngine,
    EventSummarizer,
    SmartCategorizer
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def natural_language_search(request):
    """
    Natural language event search endpoint.
    
    Example queries:
    - "Find jazz concerts this weekend in Johannesburg"
    - "Show me family-friendly events in Pretoria"
    - "What music events are happening tonight?"
    
    GET /api/ai/search/?q=<natural language query>
    """
    query = request.GET.get('q', '').strip()
    
    if not query:
        return Response(
            {'error': 'Query parameter "q" is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Parse natural language query
    nlp = NaturalLanguageSearch()
    params = nlp.parse_query(query)
    
    # Build queryset based on parsed parameters
    queryset = Event.objects.all()
    
    if params.get('city'):
        queryset = queryset.filter(city__iexact=params['city'])
    
    if params.get('category'):
        queryset = queryset.filter(category__iexact=params['category'])
    
    if params.get('keywords'):
        # Search in title, description, venue
        keyword_q = Q()
        for keyword in params['keywords']:
            keyword_q |= (
                Q(title__icontains=keyword) |
                Q(description__icontains=keyword) |
                Q(venue_name__icontains=keyword)
            )
        queryset = queryset.filter(keyword_q)
    
    if params.get('date_range'):
        start_date, end_date = params['date_range']
        if start_date and end_date:
            queryset = queryset.filter(
                start_date__date__gte=start_date,
                start_date__date__lte=end_date
            )
    
    if params.get('time_preference'):
        # Filter by time of day
        now = timezone.now()
        if params['time_preference'] == 'morning':
            queryset = queryset.filter(start_date__hour__gte=6, start_date__hour__lt=12)
        elif params['time_preference'] == 'afternoon':
            queryset = queryset.filter(start_date__hour__gte=12, start_date__hour__lt=17)
        elif params['time_preference'] == 'evening':
            queryset = queryset.filter(start_date__hour__gte=17, start_date__hour__lt=22)
    
    # Limit to upcoming events
    queryset = queryset.filter(start_date__gte=timezone.now())
    
    # Serialize and return
    serializer = EventListSerializer(queryset[:50], many=True)  # Limit to 50 results
    
    return Response({
        'query': query,
        'parsed_params': params,
        'count': len(serializer.data),
        'results': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recommendations(request):
    """
    Get personalized event recommendations.
    
    GET /api/ai/recommendations/
    GET /api/ai/recommendations/?viewed=1,2,3  # Events user has viewed
    """
    viewed_ids = request.GET.get('viewed', '').strip()
    viewed_event_ids = None
    
    if viewed_ids:
        try:
            viewed_event_ids = [int(id) for id in viewed_ids.split(',')]
        except ValueError:
            pass
    
    limit = int(request.GET.get('limit', 10))
    
    engine = EventRecommendationEngine()
    recommendations = engine.get_recommendations(
        user_id=request.user.id if request.user.is_authenticated else None,
        viewed_event_ids=viewed_event_ids,
        limit=limit
    )
    
    serializer = EventListSerializer(recommendations, many=True)
    
    return Response({
        'count': len(serializer.data),
        'results': serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def summarize_event(request, event_id):
    """
    Generate AI summary for an event.
    
    POST /api/ai/events/<id>/summarize/
    """
    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        return Response(
            {'error': 'Event not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    max_length = int(request.data.get('max_length', 150))
    
    summarizer = EventSummarizer()
    summary = summarizer.summarize(
        title=event.title,
        description=event.description or '',
        max_length=max_length
    )
    
    return Response({
        'event_id': event_id,
        'summary': summary,
        'original_length': len(event.description or ''),
        'summary_length': len(summary)
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def categorize_event(request, event_id):
    """
    Auto-categorize an event using AI.
    
    POST /api/ai/events/<id>/categorize/
    """
    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        return Response(
            {'error': 'Event not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    categorizer = SmartCategorizer()
    category = categorizer.categorize(
        title=event.title,
        description=event.description or '',
        venue_name=event.venue_name or ''
    )
    
    # Optionally update the event
    if request.data.get('update', False):
        event.category = category
        event.save()
    
    return Response({
        'event_id': event_id,
        'suggested_category': category,
        'current_category': event.category
    })

