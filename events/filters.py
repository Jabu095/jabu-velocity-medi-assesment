"""
Django Filter configuration for Event model.

Why django-filter is loved:
- Declarative filtering (no manual queryset filtering code)
- Works seamlessly with DRF
- Supports complex lookups (gte, lte, contains, etc.)
- Auto-generates filter forms in DRF browsable API
- Type-safe filtering
"""

import django_filters
from .models import Event


class EventFilter(django_filters.FilterSet):
    """
    Advanced filtering for Event model using django-filter.
    
    Examples:
        GET /api/events/?city=Johannesburg
        GET /api/events/?category=Music&city=Pretoria
        GET /api/events/?start_date__gte=2024-12-20
        GET /api/events/?created_at__year=2024
    """
    
    # Exact match filters
    city = django_filters.CharFilter(field_name='city', lookup_expr='iexact')
    category = django_filters.CharFilter(field_name='category', lookup_expr='iexact')
    source = django_filters.CharFilter(field_name='source', lookup_expr='iexact')
    
    # Date range filters
    start_date__gte = django_filters.DateTimeFilter(
        field_name='start_date',
        lookup_expr='gte',
        help_text='Events starting on or after this date'
    )
    start_date__lte = django_filters.DateTimeFilter(
        field_name='start_date',
        lookup_expr='lte',
        help_text='Events starting on or before this date'
    )
    
    # Created date filters
    created_at__year = django_filters.NumberFilter(
        field_name='created_at',
        lookup_expr='year'
    )
    created_at__month = django_filters.NumberFilter(
        field_name='created_at',
        lookup_expr='month'
    )
    
    # Text search filters
    title__icontains = django_filters.CharFilter(
        field_name='title',
        lookup_expr='icontains',
        help_text='Search in event title (case-insensitive)'
    )
    venue_name__icontains = django_filters.CharFilter(
        field_name='venue_name',
        lookup_expr='icontains',
        help_text='Search in venue name (case-insensitive)'
    )
    
    # Ordering
    ordering = django_filters.OrderingFilter(
        fields=(
            ('start_date', 'start_date'),
            ('created_at', 'created_at'),
            ('title', 'title'),
            ('city', 'city'),
        ),
        help_text='Order results by: start_date, created_at, title, city'
    )
    
    class Meta:
        model = Event
        fields = ['city', 'category', 'source', 'start_date__gte', 'start_date__lte']

