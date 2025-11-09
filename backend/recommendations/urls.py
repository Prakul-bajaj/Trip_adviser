from django.urls import path
from . import views

urlpatterns = [
    # Recommendation endpoints
    path('', views.RecommendationListView.as_view(), name='recommendation-list'),
    
    # Destination endpoints  
    path('destinations/', views.DestinationListView.as_view(), name='destination-list'),
    path('destinations/<uuid:pk>/', views.DestinationDetailView.as_view(), name='destination-detail'),
    path('destinations/stats/', views.destination_stats, name='destination-stats'),
    
    # Search & Popular (keep before <uuid:pk> to avoid conflicts)
    path('search/', views.DestinationSearchView.as_view(), name='destination-search'),
    path('popular/', views.PopularDestinationsView.as_view(), name='popular-destinations'),
    
    # Bookmark endpoints
    path('bookmarks/', views.UserBookmarkListView.as_view(), name='bookmark-list'),
    path('bookmarks/<uuid:destination_id>/', views.UserBookmarkToggleView.as_view(), name='bookmark-toggle'),
]