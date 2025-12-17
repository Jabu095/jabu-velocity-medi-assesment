"""
Event models for storing event data from Google APIs.

This module defines the Event model which stores normalized event data
fetched from Google Places API. It includes:
- Duplicate prevention via unique constraints
- Automatic timestamp tracking
- Efficient indexing for common query patterns
"""

from django.db import models
from django.utils import timezone


class Event(models.Model):
    """
    Stores event data aggregated from Google APIs.
    
    Design Decisions:
    - source_id: Unique identifier from the source API (e.g., Google Place ID)
                 Used for duplicate prevention
    - raw_payload: Stores the complete API response as JSON for data lineage
                   and debugging purposes
    - city: Standardized to canonical names (Johannesburg, Pretoria) for
            consistent filtering
    """
    
    # Required fields as per assessment
    title = models.CharField(
        max_length=500,
        help_text="Event or venue title (sanitized)"
    )
    start_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Event start date/time. Null if not available from source."
    )
    venue_name = models.CharField(
        max_length=500,
        blank=True,
        help_text="Name of the venue hosting the event"
    )
    city = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Standardized city name (Johannesburg or Pretoria)"
    )
    category = models.CharField(
        max_length=200,
        blank=True,
        help_text="Event category derived from Google Places types"
    )
    event_url = models.URLField(
        max_length=2048,
        blank=True,
        help_text="URL to the event or venue page"
    )
    source = models.CharField(
        max_length=100,
        default='google_places',
        help_text="Data source identifier (e.g., google_places, apify)"
    )
    raw_payload = models.JSONField(
        default=dict,
        help_text="Complete raw API response for data lineage"
    )
    
    # Additional metadata for data management
    source_id = models.CharField(
        max_length=255,
        unique=True,
        help_text="Unique identifier from the source (e.g., Google Place ID)"
    )
    description = models.TextField(
        blank=True,
        help_text="Event or venue description (sanitized)"
    )
    address = models.CharField(
        max_length=500,
        blank=True,
        help_text="Full address of the venue"
    )
    latitude = models.FloatField(
        null=True,
        blank=True,
        help_text="Venue latitude coordinate"
    )
    longitude = models.FloatField(
        null=True,
        blank=True,
        help_text="Venue longitude coordinate"
    )
    image_url = models.URLField(
        max_length=2048,
        blank=True,
        help_text="URL to event/venue image (from Google Places or placeholder)"
    )
    
    # Timestamps for tracking
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this record was first created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this record was last updated"
    )
    
    class Meta:
        ordering = ['-start_date', '-created_at']
        indexes = [
            models.Index(fields=['city', 'start_date']),
            models.Index(fields=['category']),
            models.Index(fields=['source']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = 'Event'
        verbose_name_plural = 'Events'
    
    def __str__(self):
        date_str = self.start_date.strftime('%Y-%m-%d') if self.start_date else 'TBD'
        return f"{self.title} ({self.city}) - {date_str}"
    
    def save(self, *args, **kwargs):
        """
        Override save to ensure data consistency.
        - Strips whitespace from text fields
        - Ensures city name is properly capitalized
        """
        if self.title:
            self.title = self.title.strip()
        if self.venue_name:
            self.venue_name = self.venue_name.strip()
        if self.city:
            self.city = self.city.strip().title()
        if self.description:
            self.description = self.description.strip()
        
        super().save(*args, **kwargs)

