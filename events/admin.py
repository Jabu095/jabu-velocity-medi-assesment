"""
Django admin configuration for the Events app.

Provides a clean interface for viewing and managing event data.
"""

from django.contrib import admin
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import path
from django.db import IntegrityError
from .models import Event
from .services.google_places import GooglePlacesService
from .sanitation import sanitize_event_data


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    """Admin configuration for Event model."""
    
    list_display = [
        'title',
        'city',
        'venue_name',
        'category',
        'start_date',
        'source',
        'created_at',
    ]
    
    change_list_template = 'admin/events/event_change_list.html'
    
    list_filter = [
        'city',
        'source',
        'category',
        'created_at',
    ]
    
    search_fields = [
        'title',
        'venue_name',
        'description',
        'address',
    ]
    
    readonly_fields = [
        'source_id',
        'raw_payload',
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('Event Information', {
            'fields': ('title', 'description', 'category', 'start_date', 'image_url')
        }),
        ('Location', {
            'fields': ('venue_name', 'city', 'address', 'latitude', 'longitude')
        }),
        ('Links & Source', {
            'fields': ('event_url', 'source', 'source_id')
        }),
        ('Raw Data', {
            'fields': ('raw_payload',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    date_hierarchy = 'created_at'
    
    def get_urls(self):
        """Add custom URLs for ingestion view."""
        urls = super().get_urls()
        custom_urls = [
            path('ingest-events/', self.admin_site.admin_view(self.ingest_events_view), name='events_event_ingest'),
        ]
        return custom_urls + urls
    
    def ingest_events_view(self, request):
        """Custom admin view for ingesting events."""
        if request.method == 'POST':
            city = request.POST.get('city', '').strip()
            max_results = int(request.POST.get('max_results', 50))
            dry_run = request.POST.get('dry_run') == 'on'
            
            # Validate city
            valid_cities = ['Johannesburg', 'Pretoria', '']
            if city and city not in valid_cities:
                messages.error(request, f"Invalid city. Must be 'Johannesburg', 'Pretoria', or leave empty for all cities.")
                return redirect('admin:events_event_ingest')
            
            try:
                # Initialize service
                service = GooglePlacesService()
                
                # Check API key
                if not service.api_key:
                    messages.error(
                        request,
                        'No Google Places API key configured. '
                        'Set GOOGLE_PLACES_API_KEY in your .env file.'
                    )
                    return redirect('admin:events_event_ingest')
                
                # Perform ingestion
                created_count = 0
                updated_count = 0
                skipped_count = 0
                error_count = 0
                
                if city:
                    # Single city
                    venues = service.search_event_venues(city, max_results=max_results)
                    for venue_data in venues:
                        result = self._process_venue(venue_data, dry_run)
                        if result == 'created':
                            created_count += 1
                        elif result == 'updated':
                            updated_count += 1
                        elif result == 'skipped':
                            skipped_count += 1
                        else:
                            error_count += 1
                else:
                    # All cities
                    venues = service.search_all_cities(max_per_city=max_results)
                    for venue_data in venues:
                        result = self._process_venue(venue_data, dry_run)
                        if result == 'created':
                            created_count += 1
                        elif result == 'updated':
                            updated_count += 1
                        elif result == 'skipped':
                            skipped_count += 1
                        else:
                            error_count += 1
                
                # Show results
                if dry_run:
                    messages.success(
                        request,
                        f"Dry run completed. Would create {created_count} events. "
                        f"Errors: {error_count}"
                    )
                else:
                    messages.success(
                        request,
                        f"Ingestion completed! Created: {created_count}, "
                        f"Updated: {updated_count}, Skipped: {skipped_count}, "
                        f"Errors: {error_count}"
                    )
                
                return redirect('admin:events_event_changelist')
                
            except Exception as e:
                messages.error(request, f"Error during ingestion: {str(e)}")
                return redirect('admin:events_event_ingest')
        
        # GET request - show form
        context = {
            **self.admin_site.each_context(request),
            'title': 'Ingest Events from Google Places API',
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request),
        }
        return render(request, 'admin/events/ingest_events.html', context)
    
    def _process_venue(self, venue_data, dry_run=False):
        """Process a single venue and return status."""
        try:
            sanitized = sanitize_event_data(venue_data)
            source_id = sanitized.get('source_id')
            
            if not source_id:
                return 'skipped'
            
            if dry_run:
                return 'created'
            
            try:
                event, created = Event.objects.update_or_create(
                    source_id=source_id,
                    defaults={
                        'title': sanitized.get('title', ''),
                        'venue_name': sanitized.get('venue_name', ''),
                        'description': sanitized.get('description', ''),
                        'city': sanitized.get('city', 'Johannesburg'),
                        'address': sanitized.get('address', ''),
                        'category': sanitized.get('category', ''),
                        'event_url': sanitized.get('event_url', ''),
                        'image_url': sanitized.get('image_url', ''),
                        'latitude': sanitized.get('latitude'),
                        'longitude': sanitized.get('longitude'),
                        'source': sanitized.get('source', 'google_places'),
                        'start_date': sanitized.get('start_date'),
                        'raw_payload': sanitized.get('raw_payload', {}),
                    }
                )
                return 'created' if created else 'updated'
            except IntegrityError:
                return 'skipped'
        except Exception:
            return 'error'

