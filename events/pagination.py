"""
Enhanced Pagination for Events API.

Provides detailed pagination information including:
- Current page number
- Total pages
- Page numbers for navigation
- First/Last page links
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
import math


class EnhancedPageNumberPagination(PageNumberPagination):
    """
    Enhanced pagination with page numbers, total pages, and navigation.
    
    Response includes:
    - count: Total number of items
    - next: URL to next page (or null)
    - previous: URL to previous page (or null)
    - current_page: Current page number
    - total_pages: Total number of pages
    - page_numbers: List of page numbers to display
    - first_page: URL to first page
    - last_page: URL to last page
    - results: List of items for current page
    """
    
    page_size = 10  # Default page size
    page_size_query_param = 'page_size'
    max_page_size = 15  # Maximum allowed: 15 per user requirement
    
    def get_paginated_response(self, data):
        """
        Return a paginated style Response object with enhanced metadata.
        """
        page_size = self.get_page_size(self.request)
        total_pages = math.ceil(self.page.paginator.count / page_size) if page_size > 0 else 1
        current_page = self.page.number
        
        # Generate page numbers to display (show 5 pages around current)
        page_numbers = self._get_page_numbers(current_page, total_pages)
        
        # Build URLs for first and last page
        request = self.request
        base_url = request.build_absolute_uri().split('?')[0]
        query_params = request.GET.copy()
        
        # First page URL
        query_params['page'] = 1
        first_page = f"{base_url}?{query_params.urlencode()}" if query_params else base_url
        
        # Last page URL
        query_params['page'] = total_pages
        last_page = f"{base_url}?{query_params.urlencode()}" if query_params else base_url
        
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'current_page': current_page,
            'total_pages': total_pages,
            'page_size': page_size,
            'page_numbers': page_numbers,
            'first_page': first_page if current_page > 1 else None,
            'last_page': last_page if current_page < total_pages else None,
            'results': data,
        })
    
    def _get_page_numbers(self, current_page, total_pages, window=2):
        """
        Generate list of page numbers to display.
        
        Shows current page with 'window' pages on each side.
        Always includes first and last page if not in range.
        
        Example: current=5, total=10, window=2
        Returns: [1, None, 3, 4, 5, 6, 7, None, 10]
        (None represents ellipsis)
        """
        if total_pages <= 1:
            return [1]
        
        pages = []
        
        # Always show first page
        if current_page > window + 2:
            pages.append(1)
            pages.append(None)  # Ellipsis
        
        # Pages around current
        start = max(1, current_page - window)
        end = min(total_pages, current_page + window)
        
        for page in range(start, end + 1):
            pages.append(page)
        
        # Always show last page
        if current_page < total_pages - window - 1:
            pages.append(None)  # Ellipsis
            pages.append(total_pages)
        
        return pages

