from asgiref.sync import sync_to_async
from django.utils.decorators import sync_and_async_middleware


@sync_and_async_middleware
def force_sync_middleware(get_response):
    """
    Middleware to force synchronous execution of views in ASGI context.
    This prevents the 'coroutine' object has no attribute errors.
    """
    
    # Check if get_response is a coroutine function
    if hasattr(get_response, '_is_coroutine'):
        # Async path
        async def middleware(request):
            # Run the view in sync mode
            response = await sync_to_async(get_response)(request)
            return response
    else:
        # Sync path (normal Django behavior)
        def middleware(request):
            response = get_response(request)
            return response
    
    return middleware