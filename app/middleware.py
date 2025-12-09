"""
Custom middleware to disable caching in development
"""
from django.conf import settings
import time


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
            # Aggressively disable caching for ALL responses
            # Setting these headers will override any existing cache headers
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            
            # Add a unique timestamp header to verify middleware is working
            response['X-Cache-Disabled'] = str(time.time())
            
            # For HTML responses, inject a timestamp comment at the end
            if hasattr(response, 'content') and response.get('Content-Type', '').startswith('text/html'):
                try:
                    # Get current timestamp
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                    # Add comment before closing body tag if it exists
                    content = response.content.decode('utf-8')
                    if '</body>' in content:
                        comment = f'<!-- Template loaded at {timestamp} -->'
                        content = content.replace('</body>', f'{comment}\n</body>')
                        response.content = content.encode('utf-8')
                        # Update content length
                        response['Content-Length'] = str(len(response.content))
                except Exception as e:
                    # If we can't modify content, just continue
                    pass
        
        return response

