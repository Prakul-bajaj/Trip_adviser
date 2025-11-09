from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/users/', include('users.urls')),
    path('api/destinations/', include('destinations.urls')),
    path('api/recommendations/', include('recommendations.urls')),
    path('api/chatbot/', include('chatbot.urls')),
    path('api/itinerary/', include('itinerary.urls')),
    path('api/integrations/', include('integrations.urls')),  # Added
    
    # JWT token endpoints
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)