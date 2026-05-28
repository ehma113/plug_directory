from django.core.cache import cache
from django.http import JsonResponse
import time

def rate_limit_search(max_requests=10, timeout=60):
    """
    CEO FIX: The Search DDoS Shield.
    Limits a single IP to X search requests per Y seconds.
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            # Get the IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')

            cache_key = f"search_limit_{ip}"
            
            # Get current request data from cache
            request_data = cache.get(cache_key, {'count': 0, 'start_time': time.time()})
            
            # Calculate time elapsed
            elapsed = time.time() - request_data['start_time']
            
            if elapsed > timeout:
                # Reset the window if time has expired
                request_data = {'count': 1, 'start_time': time.time()}
            else:
                # Increment the count
                request_data['count'] += 1
                
            # Save back to cache
            cache.set(cache_key, request_data, timeout)

            # If they exceeded the limit, block them
            if request_data['count'] > max_requests:
                return JsonResponse({
                    'error': 'Rate limit exceeded. Slow down.',
                    'retry_after': int(timeout - elapsed)
                }, status=429) # HTTP 429 Too Many Requests

            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator