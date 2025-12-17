"""
Custom middleware for Railway deployment.
Validates Railway domains dynamically since Django doesn't support wildcards in ALLOWED_HOSTS.
"""
import os


class RailwayHostMiddleware:
    """
    Middleware to allow Railway domains dynamically.
    This works around Django's limitation of not supporting wildcards in ALLOWED_HOSTS.
    We add Railway domains to ALLOWED_HOSTS before SecurityMiddleware validates them.
    This middleware must run BEFORE SecurityMiddleware.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if we're on Railway (Railway sets PORT environment variable)
        if os.getenv('PORT'):
            # Check if it's a Railway domain
            host = request.get_host().split(':')[0]  # Remove port if present
            railway_domains = ['.railway.app', '.up.railway.app']
            is_railway_domain = any(host.endswith(domain) for domain in railway_domains)
            
            if is_railway_domain:
                # Add to ALLOWED_HOSTS if not already there
                # This must happen before SecurityMiddleware checks it
                from django.conf import settings
                if host not in settings.ALLOWED_HOSTS:
                    settings.ALLOWED_HOSTS.append(host)
        
        response = self.get_response(request)
        return response
