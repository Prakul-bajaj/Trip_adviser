from django.urls import path
from . import views

urlpatterns = [
    # Recommendation endpoints
    path('', views.RecommendationListView.as_view(), name='recommendation-list'),
    
    # Destination endpoints - specific paths BEFORE uuid patterns
    path('destinations/', views.DestinationListView.as_view(), name='destination-list'),
    path('destinations/stats/', views.destination_stats, name='destination-stats'),
    path('destinations/search/', views.DestinationSearchView.as_view(), name='destination-search'),
    path('destinations/popular/', views.PopularDestinationsView.as_view(), name='popular-destinations'),
    
    # UUID patterns LAST to avoid conflicts
    path('destinations/<uuid:pk>/', views.DestinationDetailView.as_view(), name='destination-detail'),
    
    # Bookmark endpoints
    path('bookmarks/', views.UserBookmarkListView.as_view(), name='bookmark-list'),
    path('bookmarks/<uuid:destination_id>/', views.UserBookmarkToggleView.as_view(), name='bookmark-toggle'),
    
    # Search & Popular at root level for backwards compatibility
    path('search/', views.DestinationSearchView.as_view(), name='recommendation-search'),
    path('popular/', views.PopularDestinationsView.as_view(), name='recommendation-popular'),
]