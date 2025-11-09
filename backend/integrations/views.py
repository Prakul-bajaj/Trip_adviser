from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from destinations.models import Destination
from .weather_api import WeatherAPIClient, WeatherAnalyzer
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_weather(request, destination_id):
    """
    Get current weather for a destination
    GET /api/integrations/weather/<destination_id>/
    """
    try:
        destination = Destination.objects.get(id=destination_id, is_active=True)
    except Destination.DoesNotExist:
        return Response({
            'error': 'Destination not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    client = WeatherAPIClient()
    weather_data = client.get_current_weather(
        destination.latitude,
        destination.longitude
    )
    
    if not weather_data:
        return Response({
            'error': 'Unable to fetch weather data',
            'destination': {
                'name': destination.name,
                'climate_type': destination.climate_type,
                'average_temperature': destination.average_temperature_range
            }
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    is_good = client.is_good_travel_weather(weather_data)
    
    return Response({
        'destination': {
            'id': str(destination.id),
            'name': destination.name,
            'state': destination.state
        },
        'weather': weather_data,
        'is_good_for_travel': is_good,
        'travel_advice': get_travel_advice(weather_data, is_good)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_weather_forecast(request, destination_id):
    """
    Get weather forecast for a destination
    GET /api/integrations/weather/<destination_id>/forecast/
    Query params: days (default: 5)
    """
    try:
        destination = Destination.objects.get(id=destination_id, is_active=True)
    except Destination.DoesNotExist:
        return Response({
            'error': 'Destination not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    days = int(request.query_params.get('days', 5))
    if days > 5:
        days = 5  # API limit
    
    client = WeatherAPIClient()
    forecast_data = client.get_forecast(
        destination.latitude,
        destination.longitude,
        days=days
    )
    
    if not forecast_data:
        return Response({
            'error': 'Unable to fetch forecast data'
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    return Response({
        'destination': {
            'id': str(destination.id),
            'name': destination.name,
            'state': destination.state
        },
        'forecast': forecast_data,
        'days': days
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_weather_suitability(request):
    """
    Check if weather is suitable for multiple destinations
    POST /api/integrations/weather/check-suitability/
    Body: {
        "destination_ids": ["uuid1", "uuid2", ...],
        "travel_date": "2025-12-25"  # optional
    }
    """
    destination_ids = request.data.get('destination_ids', [])
    
    if not destination_ids:
        return Response({
            'error': 'destination_ids required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    destinations = Destination.objects.filter(
        id__in=destination_ids,
        is_active=True
    )
    
    client = WeatherAPIClient()
    results = []
    
    for destination in destinations:
        weather_data = client.get_current_weather(
            destination.latitude,
            destination.longitude
        )
        
        if weather_data:
            is_suitable = client.is_good_travel_weather(weather_data)
            results.append({
                'destination': {
                    'id': str(destination.id),
                    'name': destination.name,
                    'state': destination.state
                },
                'weather': weather_data,
                'is_suitable': is_suitable,
                'suitability_score': calculate_suitability_score(weather_data)
            })
    
    # Sort by suitability score
    results.sort(key=lambda x: x['suitability_score'], reverse=True)
    
    return Response({
        'results': results,
        'count': len(results)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_seasonal_recommendation(request, destination_id):
    """
    Get seasonal weather recommendation for a destination
    GET /api/integrations/weather/<destination_id>/seasonal/
    Query params: month (e.g., "january", "february")
    """
    try:
        destination = Destination.objects.get(id=destination_id, is_active=True)
    except Destination.DoesNotExist:
        return Response({
            'error': 'Destination not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    month = request.query_params.get('month', '').lower()
    
    if not month:
        return Response({
            'error': 'month parameter required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    analyzer = WeatherAnalyzer()
    analysis = analyzer.analyze_seasonal_weather(destination, month)
    
    return Response({
        'destination': {
            'id': str(destination.id),
            'name': destination.name,
            'state': destination.state
        },
        'month': month.title(),
        'analysis': analysis,
        'best_months': destination.best_time_to_visit,
        'avoid_months': destination.avoid_months
    })


def get_travel_advice(weather_data, is_good):
    """Generate travel advice based on weather"""
    if is_good:
        return "Perfect weather for traveling! Enjoy your trip! ☀️"
    
    description = weather_data.get('description', '').lower()
    temp = weather_data.get('temperature', 0)
    
    if 'rain' in description or 'drizzle' in description:
        return "Rain expected. Carry an umbrella and waterproof gear. 🌧️"
    elif 'thunderstorm' in description:
        return "Thunderstorms expected. Consider rescheduling outdoor activities. ⛈️"
    elif temp < 5:
        return "Very cold weather. Pack heavy winter clothing. 🥶"
    elif temp > 40:
        return "Extremely hot weather. Stay hydrated and avoid midday sun. 🥵"
    elif 'snow' in description:
        return "Snowy conditions. Roads may be difficult. Drive carefully. ❄️"
    else:
        return "Weather conditions may not be ideal. Plan accordingly. ⚠️"


def calculate_suitability_score(weather_data):
    """Calculate a suitability score (0-100) based on weather"""
    if not weather_data:
        return 0
    
    score = 50  # Base score
    
    temp = weather_data.get('temperature', 20)
    description = weather_data.get('description', '').lower()
    humidity = weather_data.get('humidity', 50)
    
    # Temperature scoring (ideal: 15-30°C)
    if 15 <= temp <= 30:
        score += 30
    elif 10 <= temp <= 35:
        score += 15
    elif temp < 5 or temp > 40:
        score -= 30
    
    # Weather condition scoring
    bad_conditions = ['thunderstorm', 'heavy rain', 'snow', 'extreme']
    if any(cond in description for cond in bad_conditions):
        score -= 40
    elif 'rain' in description or 'drizzle' in description:
        score -= 20
    elif 'clear' in description or 'sunny' in description:
        score += 20
    
    # Humidity scoring (ideal: 30-70%)
    if 30 <= humidity <= 70:
        score += 10
    elif humidity > 90:
        score -= 10
    
    return max(0, min(100, score))  # Clamp between 0-100