"""
Management command to ingest event data from Google Places API.

Usage:
    python manage.py ingest_events                    # Fetch from all cities
    python manage.py ingest_events --city Johannesburg  # Fetch from specific city
    python manage.py ingest_events --max-results 100    # Limit results per city
    python manage.py ingest_events --dry-run            # Preview without saving

This command:
1. Fetches venue data from Google Places API
2. Applies sanitation rules to clean the data
3. Stores/updates events in the database
4. Handles duplicates via source_id unique constraint
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

from events.models import Event
from events.services.google_places import GooglePlacesService
from events.sanitation import sanitize_event_data

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Ingest event/venue data from Google Places API'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--city',
            type=str,
            help='Specific city to fetch (Johannesburg or Pretoria). Defaults to all.',
        )
        parser.add_argument(
            '--max-results',
            type=int,
            default=50,
            help='Maximum results per city (default: 50)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview data without saving to database',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output for each event',
        )
    
    def handle(self, *args, **options):
        city = options.get('city')
        max_results = options.get('max_results')
        dry_run = options.get('dry_run')
        verbose = options.get('verbose')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No data will be saved'))
        
        # Initialize service
        service = GooglePlacesService()
        
        if not service.api_key:
            raise CommandError(
                'No Google Places API key configured. '
                'Set GOOGLE_PLACES_API_KEY in your .env file.'
            )
        
        # Fetch venues
        self.stdout.write(f'Fetching event venues from Google Places API...')
        
        if city:
            # Fetch from specific city
            venues = service.search_event_venues(city, max_results=max_results)
        else:
            # Fetch from all cities
            venues = service.search_all_cities(max_per_city=max_results)
        
        self.stdout.write(f'Fetched {len(venues)} venues from API')
        
        # Process and store venues
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for venue_data in venues:
            try:
                # Apply sanitation
                sanitized = sanitize_event_data(venue_data)
                
                if verbose:
                    self.stdout.write(
                        f"  Processing: {sanitized.get('title', 'Unknown')} "
                        f"({sanitized.get('city', 'Unknown')})"
                    )
                
                if dry_run:
                    created_count += 1
                    continue
                
                # Try to get existing event by source_id
                source_id = sanitized.get('source_id')
                if not source_id:
                    self.stdout.write(
                        self.style.WARNING(f"  Skipping venue without source_id")
                    )
                    skipped_count += 1
                    continue
                
                # Update or create
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
                
                if created:
                    created_count += 1
                    if verbose:
                        self.stdout.write(
                            self.style.SUCCESS(f"    Created: {event.title}")
                        )
                else:
                    updated_count += 1
                    if verbose:
                        self.stdout.write(f"    Updated: {event.title}")
                        
            except IntegrityError as e:
                error_count += 1
                logger.error(f"Database error for venue: {e}")
                if verbose:
                    self.stdout.write(
                        self.style.ERROR(f"    Error: {e}")
                    )
            except Exception as e:
                error_count += 1
                logger.error(f"Error processing venue: {e}")
                if verbose:
                    self.stdout.write(
                        self.style.ERROR(f"    Error: {e}")
                    )
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('INGESTION COMPLETE'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(f'  Created: {created_count}')
        self.stdout.write(f'  Updated: {updated_count}')
        self.stdout.write(f'  Skipped: {skipped_count}')
        if error_count:
            self.stdout.write(self.style.ERROR(f'  Errors: {error_count}'))
        self.stdout.write(f'  Total processed: {created_count + updated_count + skipped_count}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nDRY RUN - No data was actually saved'))

