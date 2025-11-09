from django.urls import path
from . import views

urlpatterns = [
    # Itinerary CRUD
    path('', views.ItineraryListCreateView.as_view(), name='itinerary-list-create'),
    path('<uuid:pk>/', views.ItineraryDetailView.as_view(), name='itinerary-detail'),
    
    # Day Plans
    path('day-plans/<uuid:pk>/', views.DayPlanDetailView.as_view(), name='dayplan-detail'),
    
    # Activities
    path('day-plans/<uuid:day_plan_id>/activities/', views.ActivityListCreateView.as_view(), name='activity-list-create'),
    path('activities/<uuid:pk>/', views.ActivityDetailView.as_view(), name='activity-detail'),
    
    # Transportation
    path('<uuid:itinerary_id>/transportation/', views.TransportationListCreateView.as_view(), name='transportation-list-create'),
    path('transportation/<uuid:pk>/', views.TransportationDetailView.as_view(), name='transportation-detail'),
    
    # Actions
    path('<uuid:pk>/optimize/', views.optimize_itinerary, name='itinerary-optimize'),
    path('<uuid:pk>/share/', views.share_itinerary, name='itinerary-share'),
    path('<uuid:pk>/duplicate/', views.duplicate_itinerary, name='itinerary-duplicate'),
    path('<uuid:pk>/export/pdf/', views.export_itinerary_pdf, name='itinerary-export-pdf'),
    path('<uuid:pk>/export/ics/', views.export_itinerary_ics, name='itinerary-export-ics'),
    
    # Shared itinerary view
    path('shared/<str:share_token>/', views.view_shared_itinerary, name='itinerary-shared-view'),
]