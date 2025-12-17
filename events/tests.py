"""
Tests for the Events application.

Run with: python manage.py test events
"""

from datetime import datetime, date
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from .models import Event
from .sanitation import (
    standardize_city_name,
    parse_date,
    clean_text,
    validate_and_clean_url,
    sanitize_event_data,
)


class SanitationTests(TestCase):
    """Tests for data sanitation utilities."""
    
    # City name standardization tests
    def test_standardize_johannesburg_variations(self):
        """Test various Johannesburg name variations."""
        variations = ['jhb', 'Joburg', 'jo\'burg', 'jozi', 'JOHANNESBURG', 'sandton']
        for variation in variations:
            result = standardize_city_name(variation)
            self.assertEqual(result, 'Johannesburg', f"Failed for: {variation}")
    
    def test_standardize_pretoria_variations(self):
        """Test various Pretoria name variations."""
        variations = ['pta', 'Tshwane', 'PRETORIA', 'centurion', 'hatfield']
        for variation in variations:
            result = standardize_city_name(variation)
            self.assertEqual(result, 'Pretoria', f"Failed for: {variation}")
    
    def test_standardize_unknown_city(self):
        """Unknown cities should be returned in title case."""
        result = standardize_city_name('cape town')
        self.assertEqual(result, 'Cape Town')
    
    def test_standardize_empty_city(self):
        """Empty/None input should return None."""
        self.assertIsNone(standardize_city_name(None))
        self.assertIsNone(standardize_city_name(''))
    
    # Date parsing tests
    def test_parse_iso_date(self):
        """Test ISO format date parsing."""
        result = parse_date('2024-12-17T10:30:00')
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.month, 12)
        self.assertEqual(result.day, 17)
    
    def test_parse_date_only(self):
        """Test date-only string parsing."""
        result = parse_date('2024-12-17')
        self.assertIsNotNone(result)
        self.assertEqual(result.date(), date(2024, 12, 17))
    
    def test_parse_human_date(self):
        """Test human-readable date parsing."""
        result = parse_date('December 17, 2024')
        self.assertIsNotNone(result)
        self.assertEqual(result.month, 12)
        self.assertEqual(result.day, 17)
    
    def test_parse_datetime_object(self):
        """Test that datetime objects pass through."""
        dt = datetime(2024, 12, 17, 10, 30)
        result = parse_date(dt)
        self.assertEqual(result, dt)
    
    def test_parse_invalid_date(self):
        """Invalid dates should return default."""
        result = parse_date('not a date', default=None)
        self.assertIsNone(result)
    
    # Text cleaning tests
    def test_clean_html_tags(self):
        """Test HTML tag removal."""
        result = clean_text('<p>Hello <b>World</b>!</p>')
        self.assertEqual(result, 'Hello World !')
    
    def test_clean_html_entities(self):
        """Test HTML entity unescaping."""
        result = clean_text('Tom &amp; Jerry')
        self.assertEqual(result, 'Tom & Jerry')
    
    def test_clean_whitespace(self):
        """Test whitespace normalization."""
        result = clean_text('Hello    World\n\t!')
        self.assertEqual(result, 'Hello World !')
    
    def test_clean_max_length(self):
        """Test text truncation."""
        result = clean_text('A' * 100, max_length=50)
        self.assertEqual(len(result), 50)
        self.assertTrue(result.endswith('...'))
    
    # URL validation tests
    def test_validate_valid_url(self):
        """Test valid URL passes."""
        result = validate_and_clean_url('https://example.com/event')
        self.assertEqual(result, 'https://example.com/event')
    
    def test_validate_add_scheme(self):
        """Test scheme is added if missing."""
        result = validate_and_clean_url('example.com/event')
        self.assertEqual(result, 'https://example.com/event')
    
    def test_validate_invalid_url(self):
        """Test invalid URL returns empty string."""
        result = validate_and_clean_url('not a url')
        self.assertEqual(result, '')
    
    def test_validate_empty_url(self):
        """Test empty input returns empty string."""
        self.assertEqual(validate_and_clean_url(None), '')
        self.assertEqual(validate_and_clean_url(''), '')
    
    # Composite sanitation tests
    def test_sanitize_event_data(self):
        """Test full event data sanitation."""
        raw_data = {
            'title': '<b>Cool Event</b>',
            'city': 'jhb',
            'event_url': 'example.com/event',
            'description': 'Event &amp; Party',
        }
        result = sanitize_event_data(raw_data)
        
        self.assertEqual(result['title'], 'Cool Event')
        self.assertEqual(result['city'], 'Johannesburg')
        self.assertEqual(result['event_url'], 'https://example.com/event')
        self.assertEqual(result['description'], 'Event & Party')


class EventModelTests(TestCase):
    """Tests for the Event model."""
    
    def test_create_event(self):
        """Test basic event creation."""
        event = Event.objects.create(
            source_id='test:123',
            title='Test Event',
            city='Johannesburg',
            venue_name='Test Venue',
        )
        self.assertEqual(event.title, 'Test Event')
        self.assertEqual(event.city, 'Johannesburg')
    
    def test_duplicate_source_id_rejected(self):
        """Test that duplicate source_id is rejected."""
        Event.objects.create(
            source_id='test:duplicate',
            title='First Event',
            city='Johannesburg',
        )
        
        with self.assertRaises(Exception):
            Event.objects.create(
                source_id='test:duplicate',
                title='Second Event',
                city='Pretoria',
            )
    
    def test_city_name_normalized_on_save(self):
        """Test that city name is title-cased on save."""
        event = Event.objects.create(
            source_id='test:city',
            title='Test Event',
            city='JOHANNESBURG',
        )
        self.assertEqual(event.city, 'Johannesburg')


class EventAPITests(APITestCase):
    """Tests for the Events REST API."""
    
    def setUp(self):
        """Create test events."""
        Event.objects.create(
            source_id='test:jhb1',
            title='Johannesburg Event 1',
            city='Johannesburg',
            category='Music',
        )
        Event.objects.create(
            source_id='test:jhb2',
            title='Johannesburg Event 2',
            city='Johannesburg',
            category='Nightlife',
        )
        Event.objects.create(
            source_id='test:pta1',
            title='Pretoria Event 1',
            city='Pretoria',
            category='Arts & Culture',
        )
    
    def test_list_all_events(self):
        """Test GET /api/events/ returns all events."""
        url = reverse('events:event-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
    
    def test_filter_by_city(self):
        """Test GET /api/events/?city=Johannesburg filters correctly."""
        url = reverse('events:event-list')
        response = self.client.get(url, {'city': 'Johannesburg'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        for event in response.data['results']:
            self.assertEqual(event['city'], 'Johannesburg')
    
    def test_filter_by_city_case_insensitive(self):
        """Test city filter is case-insensitive."""
        url = reverse('events:event-list')
        response = self.client.get(url, {'city': 'johannesburg'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
    
    def test_filter_by_category(self):
        """Test filtering by category."""
        url = reverse('events:event-list')
        response = self.client.get(url, {'category': 'Music'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
    
    def test_event_detail(self):
        """Test GET /api/events/{id}/ returns event details."""
        event = Event.objects.first()
        url = reverse('events:event-detail', args=[event.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], event.title)
    
    def test_event_stats(self):
        """Test GET /api/events/stats/ returns statistics."""
        url = reverse('events:event-stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_events'], 3)
        self.assertIn('by_city', response.data)
        self.assertIn('by_category', response.data)
    
    def test_pagination(self):
        """Test that results are paginated."""
        # Create more events
        for i in range(25):
            Event.objects.create(
                source_id=f'test:page{i}',
                title=f'Event {i}',
                city='Johannesburg',
            )
        
        url = reverse('events:event-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('next', response.data)
        self.assertEqual(len(response.data['results']), 20)  # Default page size

