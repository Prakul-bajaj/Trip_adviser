from django.urls import path
from . import views

urlpatterns = [
    # Weather endpoints
    path('weather/<uuid:destination_id>/', views.get_weather, name='weather-current'),
    path('weather/<uuid:destination_id>/forecast/', views.get_weather_forecast, name='weather-forecast'),
    path('weather/<uuid:destination_id>/seasonal/', views.get_seasonal_recommendation, name='weather-seasonal'),
    path('weather/check-suitability/', views.check_weather_suitability, name='weather-suitability'),
]