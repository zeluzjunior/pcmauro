"""
Custom middleware to disable caching in development
"""
from django.conf import settings


class DisableCacheMiddleware:
    """
    Middleware to disable caching for HTML responses in development mode
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Only disable caching in development
        if settings.DEBUG:
            # Disable caching for all responses (including HTML templates)
            # Check if it's an HTML response or if Content-Type is not set (Django templates)
            content_type = response.get('Content-Type', '')
            if not content_type or 'text/html' in content_type or 'text/plain' in content_type:
                response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
                response['Pragma'] = 'no-cache'
                response['Expires'] = '0'
                # Also add ETag removal to prevent conditional requests
                # Check if response supports pop method (HttpResponse does, but some others might not)
                if hasattr(response, 'pop'):
                    response.pop('ETag', None)
                elif 'ETag' in response:
                    del response['ETag']
        
        return response

