from django.utils.deprecation import MiddlewareMixin
from asgiref.sync import sync_to_async, iscoroutinefunction
import asyncio

class AsyncSafeMiddlewareWrapper(MiddlewareMixin):
    """
    Middleware to properly handle sync views in async context.
    Ensures Django can run sync views properly under ASGI/Channels.
    """
    sync_capable = True
    async_capable = True
    
    def __init__(self, get_response):
        self.get_response = get_response
        self._is_coroutine = iscoroutinefunction(get_response)
        
    async def __acall__(self, request):
        """Handle async requests"""
        # If get_response is async, await it
        if self._is_coroutine:
            response = await self.get_response(request)
        else:
            # If get_response is sync, run it in a thread pool
            response = await sync_to_async(self.get_response, thread_sensitive=True)(request)
        return response
    
    def __call__(self, request):
        """Handle sync requests"""
        # Check if we're in an async context
        try:
            asyncio.get_running_loop()
            # We're in async context, but this is a sync call - should not happen
            # but handle it gracefully
            if self._is_coroutine:
                return self.get_response(request)
            else:
                return self.get_response(request)
        except RuntimeError:
            # We're in sync context - normal sync flow
            return self.get_response(request)