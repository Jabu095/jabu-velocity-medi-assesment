"""
Google Places API Integration Service.

This module handles fetching event-related venue data from Google Places API.
Since Google doesn't have a dedicated Events API, we use Places API to fetch
venues that host events (theaters, stadiums, clubs, galleries, etc.).

Design Decisions:
- Uses Google Places API (New) with Text Search for broader results
- Stores raw API responses for data lineage
- Implements retry logic for API resilience
- Maps Google Place types to event categories

Comparison with Apify:
- Apify: Scraped event listings directly, had title/date/venue in one response
- Google Places: Provides venue data; we infer event potential from place types
  and treat each venue as a potential event location

Note: For actual events with dates, consider augmenting with:
- Google Calendar API for public calendars
- Google Custom Search API for event announcements
"""

import logging
import time
from typing import Optional
from datetime import datetime
import requests

from django.conf import settings

logger = logging.getLogger(__name__)


# Google Places types that are likely to host events
EVENT_VENUE_TYPES = [
    'night_club',
    'bar',
    'restaurant',
    'museum',
    'art_gallery',
    'movie_theater',
    'performing_arts_theater',
    'stadium',
    'tourist_attraction',
    'amusement_park',
    'bowling_alley',
    'casino',
    'convention_center',
    'cultural_center',
    'event_venue',
    'live_music_venue',
    'concert_hall',
]

# Map Google Place types to our category system
CATEGORY_MAPPING = {
    'night_club': 'Nightlife',
    'bar': 'Nightlife',
    'restaurant': 'Food & Dining',
    'museum': 'Arts & Culture',
    'art_gallery': 'Arts & Culture',
    'movie_theater': 'Entertainment',
    'performing_arts_theater': 'Performing Arts',
    'stadium': 'Sports',
    'tourist_attraction': 'Attractions',
    'amusement_park': 'Entertainment',
    'bowling_alley': 'Entertainment',
    'casino': 'Entertainment',
    'convention_center': 'Business & Conferences',
    'cultural_center': 'Arts & Culture',
    'event_venue': 'Events',
    'live_music_venue': 'Music',
    'concert_hall': 'Music',
}


class GooglePlacesService:
    """
    Service for fetching venue/event data from Google Places API.
    
    Uses the Places API (New) with Text Search endpoint for comprehensive
    results in target cities.
    
    Usage:
        service = GooglePlacesService()
        results = service.search_event_venues('Johannesburg')
        for venue in results:
            print(venue['title'], venue['category'])
    """
    
    # Google Places API (New) endpoints
    BASE_URL = 'https://places.googleapis.com/v1/places:searchText'
    PLACE_DETAILS_URL = 'https://places.googleapis.com/v1/places'
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the service.
        
        Args:
            api_key: Google API key. Defaults to settings.GOOGLE_PLACES_API_KEY
        """
        self.api_key = api_key or settings.GOOGLE_PLACES_API_KEY
        if not self.api_key:
            logger.warning("No Google Places API key configured")
    
    def _make_request(
        self,
        method: str,
        url: str,
        headers: dict,
        json_data: Optional[dict] = None,
        max_retries: int = 3
    ) -> Optional[dict]:
        """
        Makes an HTTP request with retry logic.
        
        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            json_data: JSON body for POST requests
            max_retries: Number of retries on failure
            
        Returns:
            Response JSON or None on failure
        """
        for attempt in range(max_retries):
            try:
                if method == 'POST':
                    response = requests.post(url, headers=headers, json=json_data, timeout=30)
                else:
                    response = requests.get(url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # Rate limited
                    wait_time = 2 ** attempt
                    logger.warning(f"Rate limited, waiting {wait_time}s before retry")
                    time.sleep(wait_time)
                else:
                    logger.error(f"API error: {response.status_code} - {response.text}")
                    return None
                    
            except requests.RequestException as e:
                logger.error(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
        
        return None
    
    def search_event_venues(
        self,
        city: str,
        venue_types: Optional[list] = None,
        max_results: int = 60
    ) -> list[dict]:
        """
        Searches for event venues in a city.
        
        Args:
            city: City name (e.g., 'Johannesburg', 'Pretoria')
            venue_types: List of venue types to search. Defaults to EVENT_VENUE_TYPES
            max_results: Maximum number of results to return
            
        Returns:
            List of transformed venue dictionaries ready for Event model
        """
        if not self.api_key:
            logger.error("Cannot search: No API key configured")
            return []
        
        # Get city coordinates from settings
        city_config = settings.TARGET_CITIES.get(city.lower())
        if not city_config:
            logger.warning(f"Unknown city: {city}. Using text search without coordinates.")
            location_bias = None
        else:
            location_bias = {
                'circle': {
                    'center': {
                        'latitude': city_config['latitude'],
                        'longitude': city_config['longitude']
                    },
                    'radius': settings.SEARCH_RADIUS_METERS
                }
            }
        
        venue_types = venue_types or EVENT_VENUE_TYPES
        all_venues = []
        
        # Search for each venue type
        for venue_type in venue_types:
            if len(all_venues) >= max_results:
                break
            
            query = f"{venue_type.replace('_', ' ')} in {city}, South Africa"
            venues = self._text_search(query, location_bias, venue_type)
            all_venues.extend(venues)
            
            # Small delay to avoid rate limiting
            time.sleep(0.1)
        
        # Deduplicate by place_id
        seen_ids = set()
        unique_venues = []
        for venue in all_venues:
            if venue['source_id'] not in seen_ids:
                seen_ids.add(venue['source_id'])
                unique_venues.append(venue)
        
        return unique_venues[:max_results]
    
    def _text_search(
        self,
        query: str,
        location_bias: Optional[dict],
        venue_type: str
    ) -> list[dict]:
        """
        Performs a text search using Google Places API (New).
        
        Args:
            query: Search query
            location_bias: Location bias configuration
            venue_type: The venue type being searched
            
        Returns:
            List of transformed venue dictionaries
        """
        headers = {
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': self.api_key,
            'X-Goog-FieldMask': (
                'places.id,'
                'places.displayName,'
                'places.formattedAddress,'
                'places.location,'
                'places.types,'
                'places.websiteUri,'
                'places.googleMapsUri,'
                'places.primaryType,'
                'places.editorialSummary,'
                'places.photos'
            )
        }
        
        request_body = {
            'textQuery': query,
            'languageCode': 'en',
            'maxResultCount': 20,
        }
        
        if location_bias:
            request_body['locationBias'] = location_bias
        
        response_data = self._make_request(
            'POST',
            self.BASE_URL,
            headers,
            request_body
        )
        
        if not response_data or 'places' not in response_data:
            return []
        
        return [
            self._transform_place(place, venue_type, response_data)
            for place in response_data.get('places', [])
        ]
    
    def _transform_place(
        self,
        place: dict,
        venue_type: str,
        raw_response: dict
    ) -> dict:
        """
        Transforms a Google Place response to our Event model format.
        
        Args:
            place: Raw place data from API
            venue_type: The venue type that matched
            raw_response: Complete API response for storage
            
        Returns:
            Dictionary matching Event model fields
        """
        # Extract display name
        display_name = place.get('displayName', {})
        title = display_name.get('text', 'Unknown Venue') if isinstance(display_name, dict) else str(display_name)
        
        # Get primary category
        primary_type = place.get('primaryType', venue_type)
        category = CATEGORY_MAPPING.get(
            primary_type,
            CATEGORY_MAPPING.get(venue_type, 'General')
        )
        
        # Extract description
        editorial = place.get('editorialSummary', {})
        description = editorial.get('text', '') if isinstance(editorial, dict) else ''
        
        # Get URL (prefer website, fallback to Google Maps)
        event_url = place.get('websiteUri', '') or place.get('googleMapsUri', '')
        
        # Get image URL from photos (first photo, max width 800)
        image_url = ''
        photos = place.get('photos', [])
        if photos and len(photos) > 0:
            photo = photos[0]
            if isinstance(photo, dict):
                photo_name = photo.get('name', '')
                if photo_name:
                    # Google Places API (New) photo URL
                    image_url = f"https://places.googleapis.com/v1/{photo_name}/media?key={self.api_key}&maxWidthPx=800"
                else:
                    # Try photo reference
                    photo_ref = photo.get('photoReference') or photo.get('photo_reference')
                    if photo_ref:
                        image_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photoreference={photo_ref}&key={self.api_key}"
            elif isinstance(photo, str):
                # If it's a photo reference string
                image_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photoreference={photo}&key={self.api_key}"
        
        # Get coordinates
        location = place.get('location', {})
        
        # Extract city from address
        address = place.get('formattedAddress', '')
        city_name = self._extract_city_from_address(address)
        
        # Fallback to placeholder image if no photo available
        if not image_url:
            # Use Unsplash placeholder based on category
            category_slug = primary_type.replace('_', '-') if primary_type else 'event'
            city_slug = city_name.lower() if city_name else 'venue'
            image_url = f"https://source.unsplash.com/800x600/?{category_slug},venue,{city_slug}"
        
        return {
            'source_id': f"google_places:{place.get('id', '')}",
            'title': title,
            'venue_name': title,  # For venues, title is venue name
            'description': description,
            'city': city_name,
            'address': address,
            'category': category,
            'event_url': event_url,
            'image_url': image_url,
            'latitude': location.get('latitude'),
            'longitude': location.get('longitude'),
            'source': 'google_places',
            'start_date': None,  # Venues don't have specific event dates
            'raw_payload': {
                'place': place,
                'search_query': venue_type,
                'fetched_at': datetime.now().isoformat()
            }
        }
    
    def _extract_city_from_address(self, address: str) -> str:
        """
        Extracts city from formatted address.
        
        Args:
            address: Formatted address string
            
        Returns:
            City name (defaults to 'Johannesburg')
        """
        address_lower = address.lower()
        
        if 'pretoria' in address_lower or 'tshwane' in address_lower:
            return 'Pretoria'
        elif 'johannesburg' in address_lower or any(
            suburb in address_lower
            for suburb in ['sandton', 'rosebank', 'soweto', 'randburg', 'midrand']
        ):
            return 'Johannesburg'
        
        # Default to Johannesburg for Gauteng addresses
        if 'gauteng' in address_lower:
            return 'Johannesburg'
        
        return 'Johannesburg'  # Default
    
    def search_all_cities(self, max_per_city: int = 50) -> list[dict]:
        """
        Searches for event venues in all target cities.
        
        Args:
            max_per_city: Maximum results per city
            
        Returns:
            Combined list of venues from all cities
        """
        all_venues = []
        
        for city_key, city_config in settings.TARGET_CITIES.items():
            logger.info(f"Searching venues in {city_config['canonical_name']}...")
            venues = self.search_event_venues(
                city_config['canonical_name'],
                max_results=max_per_city
            )
            all_venues.extend(venues)
            logger.info(f"Found {len(venues)} venues in {city_config['canonical_name']}")
        
        return all_venues

