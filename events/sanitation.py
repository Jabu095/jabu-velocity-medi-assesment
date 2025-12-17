"""
Data Sanitation Utilities for Event Data.

This module implements data cleaning and normalization rules for event data
ingested from Google APIs. It ensures data quality and consistency.

Sanitation Rules Implemented:
1. City Name Standardization - Normalizes variations to canonical names
2. Date Parsing - Handles multiple date formats and edge cases
3. Title/Description Cleaning - Removes HTML, normalizes whitespace
4. URL Validation - Validates and cleans event URLs

Design Decisions:
- Functions are pure and stateless for easy testing
- Logging is used for debugging without interrupting flow
- Graceful handling of malformed data (return None/empty instead of raising)
"""

import re
import html
import logging
from datetime import datetime, date
from typing import Optional, Union
from urllib.parse import urlparse, urlunparse

from dateutil import parser as date_parser
from dateutil.parser import ParserError

try:
    import validators
    HAS_VALIDATORS = True
except ImportError:
    HAS_VALIDATORS = False

logger = logging.getLogger(__name__)


# ==============================================================================
# RULE 1: City Name Standardization
# ==============================================================================

# Mapping of common variations to canonical city names
CITY_NAME_MAPPINGS = {
    # Johannesburg variations
    'johannesburg': 'Johannesburg',
    'jhb': 'Johannesburg',
    'joburg': 'Johannesburg',
    'jo\'burg': 'Johannesburg',
    'jozi': 'Johannesburg',
    'egoli': 'Johannesburg',
    'johannesberg': 'Johannesburg',  # Common misspelling
    'johannesburgo': 'Johannesburg',  # Spanish variation
    'gauteng': 'Johannesburg',  # Province - default to Johannesburg
    'sandton': 'Johannesburg',  # Suburb
    'rosebank': 'Johannesburg',  # Suburb
    'soweto': 'Johannesburg',  # Part of Johannesburg
    'midrand': 'Johannesburg',  # Between JHB and PTA, closer to JHB
    'fourways': 'Johannesburg',  # Suburb
    'randburg': 'Johannesburg',  # Suburb
    'roodepoort': 'Johannesburg',  # Suburb
    'kempton park': 'Johannesburg',  # East Rand
    'boksburg': 'Johannesburg',  # East Rand
    'benoni': 'Johannesburg',  # East Rand
    'alberton': 'Johannesburg',  # South of Johannesburg
    
    # Pretoria variations
    'pretoria': 'Pretoria',
    'pta': 'Pretoria',
    'tshwane': 'Pretoria',
    'city of tshwane': 'Pretoria',
    'hatfield': 'Pretoria',  # Suburb
    'menlyn': 'Pretoria',  # Suburb
    'centurion': 'Pretoria',  # Part of Tshwane
    'brooklyn': 'Pretoria',  # Suburb (Pretoria's Brooklyn)
    'arcadia': 'Pretoria',  # Suburb
    'sunnyside': 'Pretoria',  # Suburb
}


def standardize_city_name(city: Optional[str]) -> Optional[str]:
    """
    Standardizes city name to canonical form.
    
    Args:
        city: Raw city name from API response
        
    Returns:
        Canonical city name ('Johannesburg' or 'Pretoria') or original
        if no mapping found
        
    Examples:
        >>> standardize_city_name('jhb')
        'Johannesburg'
        >>> standardize_city_name('Tshwane')
        'Pretoria'
        >>> standardize_city_name('Cape Town')
        'Cape Town'  # Not in target cities, returned as-is
    """
    if not city:
        return None
    
    # Normalize for lookup: lowercase, strip whitespace
    normalized = city.lower().strip()
    
    # Direct lookup
    if normalized in CITY_NAME_MAPPINGS:
        return CITY_NAME_MAPPINGS[normalized]
    
    # Partial match - check if any key is contained in the city string
    for key, canonical in CITY_NAME_MAPPINGS.items():
        if key in normalized:
            return canonical
    
    # No mapping found, return title case
    return city.strip().title()


def extract_city_from_address(address: Optional[str]) -> Optional[str]:
    """
    Attempts to extract and standardize city from a full address string.
    
    Args:
        address: Full address string
        
    Returns:
        Standardized city name if found, None otherwise
    """
    if not address:
        return None
    
    address_lower = address.lower()
    
    # Check for known city names in address
    for key, canonical in CITY_NAME_MAPPINGS.items():
        if key in address_lower:
            return canonical
    
    return None


# ==============================================================================
# RULE 2: Date Parsing
# ==============================================================================

def parse_date(
    date_input: Optional[Union[str, datetime, date, int, float]],
    default: Optional[datetime] = None
) -> Optional[datetime]:
    """
    Parses various date formats into a datetime object.
    
    Handles:
    - ISO 8601 strings (2024-12-17T10:00:00Z)
    - Common date formats (17/12/2024, Dec 17, 2024, etc.)
    - Unix timestamps (integer/float)
    - Already parsed datetime objects
    
    Args:
        date_input: Date in various formats
        default: Default value if parsing fails
        
    Returns:
        Parsed datetime or default value
        
    Examples:
        >>> parse_date('2024-12-17')
        datetime(2024, 12, 17, 0, 0)
        >>> parse_date(1702800000)  # Unix timestamp
        datetime(2023, 12, 17, 8, 0, 0)
    """
    if date_input is None:
        return default
    
    # Already a datetime
    if isinstance(date_input, datetime):
        return date_input
    
    # Date object - convert to datetime
    if isinstance(date_input, date):
        return datetime.combine(date_input, datetime.min.time())
    
    # Unix timestamp (int or float)
    if isinstance(date_input, (int, float)):
        try:
            # Handle milliseconds vs seconds
            if date_input > 1e12:  # Likely milliseconds
                date_input = date_input / 1000
            return datetime.fromtimestamp(date_input)
        except (ValueError, OSError) as e:
            logger.warning(f"Failed to parse timestamp {date_input}: {e}")
            return default
    
    # String parsing
    if isinstance(date_input, str):
        date_str = date_input.strip()
        
        if not date_str:
            return default
        
        try:
            # Use dateutil parser with dayfirst=True for SA date formats
            parsed = date_parser.parse(date_str, dayfirst=True, fuzzy=True)
            return parsed
        except (ParserError, ValueError) as e:
            logger.warning(f"Failed to parse date string '{date_str}': {e}")
            return default
    
    logger.warning(f"Unsupported date type: {type(date_input)}")
    return default


def format_date_for_display(dt: Optional[datetime], format_str: str = '%Y-%m-%d %H:%M') -> str:
    """
    Formats a datetime for display.
    
    Args:
        dt: Datetime to format
        format_str: strftime format string
        
    Returns:
        Formatted date string or 'TBD' if None
    """
    if dt is None:
        return 'TBD'
    return dt.strftime(format_str)


# ==============================================================================
# RULE 3: Title/Description Cleaning
# ==============================================================================

# Regex patterns for cleaning
HTML_TAG_PATTERN = re.compile(r'<[^>]+>')
MULTIPLE_SPACES_PATTERN = re.compile(r'\s+')
SPECIAL_CHARS_PATTERN = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')  # Control characters


def clean_text(
    text: Optional[str],
    strip_html: bool = True,
    normalize_whitespace: bool = True,
    unescape_html: bool = True,
    max_length: Optional[int] = None
) -> str:
    """
    Cleans and normalizes text content.
    
    Operations:
    - Strips HTML tags
    - Unescapes HTML entities (&amp; -> &)
    - Normalizes whitespace (multiple spaces -> single space)
    - Removes control characters
    - Trims leading/trailing whitespace
    
    Args:
        text: Raw text to clean
        strip_html: Remove HTML tags
        normalize_whitespace: Collapse multiple spaces
        unescape_html: Convert HTML entities
        max_length: Truncate to this length (None = no limit)
        
    Returns:
        Cleaned text string (never None, empty string if input is None/empty)
        
    Examples:
        >>> clean_text('<p>Hello   World!</p>')
        'Hello World!'
        >>> clean_text('Tom &amp; Jerry')
        'Tom & Jerry'
    """
    if not text:
        return ''
    
    result = str(text)
    
    # Remove control characters
    result = SPECIAL_CHARS_PATTERN.sub('', result)
    
    # Strip HTML tags
    if strip_html:
        result = HTML_TAG_PATTERN.sub(' ', result)
    
    # Unescape HTML entities
    if unescape_html:
        result = html.unescape(result)
    
    # Normalize whitespace
    if normalize_whitespace:
        result = MULTIPLE_SPACES_PATTERN.sub(' ', result)
    
    # Trim
    result = result.strip()
    
    # Truncate if needed
    if max_length and len(result) > max_length:
        result = result[:max_length - 3] + '...'
    
    return result


def clean_title(title: Optional[str], max_length: int = 500) -> str:
    """
    Cleans an event/venue title.
    
    Args:
        title: Raw title
        max_length: Maximum length
        
    Returns:
        Cleaned title
    """
    return clean_text(title, max_length=max_length)


def clean_description(description: Optional[str], max_length: int = 5000) -> str:
    """
    Cleans an event/venue description.
    
    Args:
        description: Raw description
        max_length: Maximum length
        
    Returns:
        Cleaned description
    """
    return clean_text(description, max_length=max_length)


# ==============================================================================
# RULE 4: URL Validation
# ==============================================================================

def validate_and_clean_url(url: Optional[str]) -> str:
    """
    Validates and cleans a URL.
    
    Operations:
    - Strips whitespace
    - Adds https:// if missing scheme
    - Validates URL structure
    - Returns empty string if invalid
    
    Args:
        url: Raw URL string
        
    Returns:
        Valid, cleaned URL or empty string
        
    Examples:
        >>> validate_and_clean_url('example.com/event')
        'https://example.com/event'
        >>> validate_and_clean_url('not a url')
        ''
    """
    if not url:
        return ''
    
    url = str(url).strip()
    
    if not url:
        return ''
    
    # Add scheme if missing
    if not url.startswith(('http://', 'https://', '//')):
        url = 'https://' + url
    elif url.startswith('//'):
        url = 'https:' + url
    
    # Parse and validate structure
    try:
        parsed = urlparse(url)
        
        # Must have scheme and netloc (domain)
        if not parsed.scheme or not parsed.netloc:
            logger.debug(f"Invalid URL structure: {url}")
            return ''
        
        # Validate scheme
        if parsed.scheme not in ('http', 'https'):
            logger.debug(f"Invalid URL scheme: {parsed.scheme}")
            return ''
        
        # Use validators library if available for stricter validation
        if HAS_VALIDATORS:
            if not validators.url(url):
                logger.debug(f"URL validation failed: {url}")
                return ''
        
        # Reconstruct clean URL
        return urlunparse(parsed)
        
    except Exception as e:
        logger.debug(f"URL parsing error for '{url}': {e}")
        return ''


def extract_google_maps_url(place_id: str) -> str:
    """
    Generates a Google Maps URL from a Place ID.
    
    Args:
        place_id: Google Place ID
        
    Returns:
        Google Maps URL
    """
    if not place_id:
        return ''
    return f"https://www.google.com/maps/place/?q=place_id:{place_id}"


# ==============================================================================
# Composite Sanitation Function
# ==============================================================================

def sanitize_event_data(data: dict) -> dict:
    """
    Applies all sanitation rules to raw event data.
    
    This is the main entry point for sanitizing event data from APIs.
    
    Args:
        data: Raw event data dictionary
        
    Returns:
        Sanitized event data dictionary
    """
    sanitized = data.copy()
    
    # Clean title
    if 'title' in sanitized:
        sanitized['title'] = clean_title(sanitized.get('title'))
    
    # Clean description
    if 'description' in sanitized:
        sanitized['description'] = clean_description(sanitized.get('description'))
    
    # Standardize city
    if 'city' in sanitized:
        sanitized['city'] = standardize_city_name(sanitized.get('city'))
    elif 'address' in sanitized:
        sanitized['city'] = extract_city_from_address(sanitized.get('address'))
    
    # Parse date
    if 'start_date' in sanitized:
        sanitized['start_date'] = parse_date(sanitized.get('start_date'))
    
    # Clean venue name
    if 'venue_name' in sanitized:
        sanitized['venue_name'] = clean_text(sanitized.get('venue_name'), max_length=500)
    
    # Validate URL
    if 'event_url' in sanitized:
        sanitized['event_url'] = validate_and_clean_url(sanitized.get('event_url'))
    
    # Clean category
    if 'category' in sanitized:
        sanitized['category'] = clean_text(sanitized.get('category'), max_length=200)
    
    # Clean address
    if 'address' in sanitized:
        sanitized['address'] = clean_text(sanitized.get('address'), max_length=500)
    
    return sanitized

