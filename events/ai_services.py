"""
AI Services for Event Discovery and Enhancement.

This module provides AI-powered features including:
- Natural language search query parsing
- Event recommendations
- Event summarization
- Smart categorization
"""

import os
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from django.conf import settings
from django.db.models import Q, Count
from django.utils import timezone

logger = logging.getLogger(__name__)


class NaturalLanguageSearch:
    """
    Parses natural language queries into structured search parameters.
    
    Example:
        "Find jazz concerts this weekend in Johannesburg"
        -> {
            'category': 'Music',
            'city': 'Johannesburg',
            'date_range': ('2024-12-21', '2024-12-22'),
            'keywords': ['jazz', 'concert']
        }
    """
    
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.use_ai = bool(self.api_key)
    
    def parse_query(self, query: str) -> Dict[str, Any]:
        """
        Parse natural language query into search parameters.
        
        Args:
            query: Natural language search query
            
        Returns:
            Dictionary with search parameters:
            {
                'city': str or None,
                'category': str or None,
                'keywords': list,
                'date_range': tuple(start_date, end_date) or None,
                'time_preference': str or None  # 'morning', 'afternoon', 'evening', 'night'
            }
        """
        if not self.use_ai:
            # Fallback to simple keyword extraction
            return self._simple_parse(query)
        
        try:
            import openai
            
            client = openai.OpenAI(api_key=self.api_key)
            
            prompt = f"""Parse this event search query into structured parameters:
Query: "{query}"

Extract:
1. City (Johannesburg or Pretoria) - if mentioned
2. Category (Music, Sports, Arts, Food, etc.) - if mentioned
3. Keywords (important words to search for)
4. Date/time preferences (today, tomorrow, this weekend, next week, etc.)
5. Time of day preference (morning, afternoon, evening, night)

Respond in JSON format:
{{
    "city": "Johannesburg" or null,
    "category": "Music" or null,
    "keywords": ["jazz", "concert"],
    "date_range": {{"start": "2024-12-21", "end": "2024-12-22"}} or null,
    "time_preference": "evening" or null
}}"""

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that parses event search queries into structured data. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            return self._normalize_result(result)
            
        except Exception as e:
            logger.error(f"Error parsing query with AI: {e}")
            return self._simple_parse(query)
    
    def _simple_parse(self, query: str) -> Dict[str, Any]:
        """Fallback simple parsing without AI."""
        query_lower = query.lower()
        
        # Extract city
        city = None
        if 'johannesburg' in query_lower or 'joburg' in query_lower:
            city = 'Johannesburg'
        elif 'pretoria' in query_lower:
            city = 'Pretoria'
        
        # Extract category keywords
        category_keywords = {
            'music': 'Music',
            'concert': 'Music',
            'gig': 'Music',
            'sport': 'Sports',
            'game': 'Sports',
            'art': 'Arts',
            'theater': 'Arts',
            'food': 'Food',
            'restaurant': 'Food',
            'festival': 'Festival',
        }
        
        category = None
        for keyword, cat in category_keywords.items():
            if keyword in query_lower:
                category = cat
                break
        
        # Extract date keywords
        date_range = None
        if 'today' in query_lower:
            today = timezone.now().date()
            date_range = (today, today)
        elif 'tomorrow' in query_lower:
            tomorrow = (timezone.now() + timedelta(days=1)).date()
            date_range = (tomorrow, tomorrow)
        elif 'weekend' in query_lower:
            today = timezone.now().date()
            # Find next Saturday
            days_until_saturday = (5 - today.weekday()) % 7
            if days_until_saturday == 0:
                days_until_saturday = 7
            saturday = today + timedelta(days=days_until_saturday)
            sunday = saturday + timedelta(days=1)
            date_range = (saturday, sunday)
        
        # Extract time preference
        time_preference = None
        if 'morning' in query_lower:
            time_preference = 'morning'
        elif 'afternoon' in query_lower:
            time_preference = 'afternoon'
        elif 'evening' in query_lower or 'night' in query_lower:
            time_preference = 'evening'
        
        # Extract keywords (remove common words)
        stop_words = {'the', 'a', 'an', 'in', 'on', 'at', 'for', 'to', 'of', 'and', 'or', 'this', 'next', 'find', 'show', 'me'}
        words = query_lower.split()
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return {
            'city': city,
            'category': category,
            'keywords': keywords[:5],  # Limit to 5 keywords
            'date_range': date_range,
            'time_preference': time_preference
        }
    
    def _normalize_result(self, result: Dict) -> Dict[str, Any]:
        """Normalize AI result to ensure proper format."""
        # Convert date strings to date objects if present
        if result.get('date_range'):
            dr = result['date_range']
            if isinstance(dr, dict):
                start = datetime.strptime(dr.get('start', ''), '%Y-%m-%d').date() if dr.get('start') else None
                end = datetime.strptime(dr.get('end', ''), '%Y-%m-%d').date() if dr.get('end') else None
                result['date_range'] = (start, end) if start and end else None
        
        # Ensure city is valid
        if result.get('city') and result['city'] not in ['Johannesburg', 'Pretoria']:
            result['city'] = None
        
        return result


class EventRecommendationEngine:
    """
    Provides personalized event recommendations based on user behavior and event similarity.
    """
    
    def __init__(self):
        self.use_embeddings = os.getenv('USE_EMBEDDINGS', 'false').lower() == 'true'
    
    def get_recommendations(
        self,
        user_id: Optional[int] = None,
        viewed_event_ids: Optional[List[int]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recommended events for a user.
        
        Args:
            user_id: Optional user ID for personalized recommendations
            viewed_event_ids: List of event IDs user has viewed
            limit: Number of recommendations to return
            
        Returns:
            List of recommended event dictionaries
        """
        from .models import Event
        
        # If user has viewed events, recommend similar ones
        if viewed_event_ids:
            return self._get_similar_events(viewed_event_ids, limit)
        
        # Otherwise, recommend popular/trending events
        return self._get_popular_events(limit)
    
    def _get_similar_events(self, event_ids: List[int], limit: int) -> List[Dict]:
        """Get events similar to the ones user viewed."""
        from .models import Event
        
        # Get viewed events
        viewed_events = Event.objects.filter(id__in=event_ids)
        
        if not viewed_events.exists():
            return self._get_popular_events(limit)
        
        # Extract common characteristics
        categories = viewed_events.values_list('category', flat=True).distinct()
        cities = viewed_events.values_list('city', flat=True).distinct()
        
        # Find similar events (same category or city, not already viewed)
        similar = Event.objects.exclude(id__in=event_ids).filter(
            Q(category__in=categories) | Q(city__in=cities)
        ).order_by('-created_at')[:limit * 2]
        
        # Score and rank by similarity
        recommendations = []
        for event in similar:
            score = 0
            if event.category in categories:
                score += 2
            if event.city in cities:
                score += 1
            if event.start_date and event.start_date > timezone.now():
                score += 1
            
            recommendations.append({
                'event': event,
                'score': score
            })
        
        # Sort by score and return top N
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return [r['event'] for r in recommendations[:limit]]
    
    def _get_popular_events(self, limit: int) -> List[Dict]:
        """Get popular/trending events."""
        from .models import Event
        
        # Get upcoming events, ordered by creation date (newest first)
        # In a real app, you'd track views/clicks for popularity
        return list(Event.objects.filter(
            start_date__gte=timezone.now()
        ).order_by('-created_at')[:limit])


class EventSummarizer:
    """
    Generates concise summaries of event descriptions.
    """
    
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.use_ai = bool(self.api_key)
    
    def summarize(self, title: str, description: str, max_length: int = 150) -> str:
        """
        Generate a concise summary of an event.
        
        Args:
            title: Event title
            description: Event description
            max_length: Maximum summary length in characters
            
        Returns:
            Concise summary string
        """
        if not description:
            return title
        
        if not self.use_ai:
            # Simple truncation with ellipsis
            if len(description) <= max_length:
                return description
            return description[:max_length - 3] + '...'
        
        try:
            import openai
            
            client = openai.OpenAI(api_key=self.api_key)
            
            prompt = f"""Create a concise summary of this event in {max_length} characters or less:

Title: {title}
Description: {description}

Summary (include key details: date/time if mentioned, venue, highlights):"""

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that creates concise event summaries. Be informative but brief."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=100
            )
            
            summary = response.choices[0].message.content.strip()
            # Ensure it doesn't exceed max_length
            if len(summary) > max_length:
                summary = summary[:max_length - 3] + '...'
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary with AI: {e}")
            # Fallback to simple truncation
            if len(description) <= max_length:
                return description
            return description[:max_length - 3] + '...'


class SmartCategorizer:
    """
    Automatically categorizes events using AI.
    """
    
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.use_ai = bool(self.api_key)
    
    def categorize(self, title: str, description: str, venue_name: str = '') -> str:
        """
        Categorize an event based on its content.
        
        Args:
            title: Event title
            description: Event description
            venue_name: Venue name
            
        Returns:
            Category string (Music, Sports, Arts, Food, etc.)
        """
        if not self.use_ai:
            return self._simple_categorize(title, description, venue_name)
        
        try:
            import openai
            
            client = openai.OpenAI(api_key=self.api_key)
            
            prompt = f"""Categorize this event into one of these categories:
Music, Sports, Arts, Food, Festival, Conference, Workshop, Theater, Comedy, Family, Nightlife, Other

Title: {title}
Description: {description}
Venue: {venue_name}

Respond with only the category name:"""

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that categorizes events. Respond with only the category name."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=10
            )
            
            category = response.choices[0].message.content.strip()
            return category
            
        except Exception as e:
            logger.error(f"Error categorizing with AI: {e}")
            return self._simple_categorize(title, description, venue_name)
    
    def _simple_categorize(self, title: str, description: str, venue_name: str) -> str:
        """Simple keyword-based categorization."""
        text = f"{title} {description} {venue_name}".lower()
        
        categories = {
            'Music': ['music', 'concert', 'gig', 'band', 'dj', 'jazz', 'rock', 'pop', 'live music'],
            'Sports': ['sport', 'game', 'match', 'tournament', 'fitness', 'gym', 'running'],
            'Arts': ['art', 'gallery', 'exhibition', 'theater', 'drama', 'play'],
            'Food': ['food', 'restaurant', 'dining', 'wine', 'beer', 'culinary', 'chef'],
            'Festival': ['festival', 'celebration', 'carnival'],
            'Conference': ['conference', 'seminar', 'workshop', 'talk', 'lecture'],
        }
        
        for category, keywords in categories.items():
            if any(keyword in text for keyword in keywords):
                return category
        
        return 'Other'

