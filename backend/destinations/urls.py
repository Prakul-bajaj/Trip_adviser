from django.urls import path
from .views import (
    DestinationListView,
    DestinationDetailView,
    SpiritualDestinationsView,
    get_destinations_by_type,
    search_spiritual_places,
    save_destination,
    unsave_destination,
    get_saved_destinations,
    get_destinations_by_experience,
    get_destinations_by_geography,
    get_destinations_by_landscape,
    get_all_categories,
    search_all_destinations,
)

urlpatterns = [
    # List and detail views
    path('', DestinationListView.as_view(), name='destination-list'),
    path('<uuid:pk>/', DestinationDetailView.as_view(), name='destination-detail'),
    
    # Spiritual destinations
    path('spiritual/', SpiritualDestinationsView.as_view(), name='spiritual-destinations'),
    path('spiritual/search/', search_spiritual_places, name='search-spiritual-places'),
    
    # Category-based views
    path('experience/<str:experience_type>/', get_destinations_by_experience, name='destinations-by-experience'),
    path('geography/<str:geography_type>/', get_destinations_by_geography, name='destinations-by-geography'),
    path('landscape/<str:landscape_type>/', get_destinations_by_landscape, name='destinations-by-landscape'),
    
    # Get all available categories
    path('categories/', get_all_categories, name='all-categories'),
    
    # Advanced search
    path('search/', search_all_destinations, name='search-all-destinations'),
    
    # Type-based filtering (legacy)
    path('type/<str:destination_type>/', get_destinations_by_type, name='destinations-by-type'),
    
    # User interactions
    path('<uuid:destination_id>/save/', save_destination, name='save-destination'),
    path('<uuid:destination_id>/unsave/', unsave_destination, name='unsave-destination'),
    path('saved/', get_saved_destinations, name='saved-destinations'),
]