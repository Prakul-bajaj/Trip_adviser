import requests
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

class WeatherAPIClient:
    """
    OpenWeatherMap API client (Free tier: 60 calls/minute, 1M calls/month)
    """
    BASE_URL = "https://api.openweathermap.org/data/2.5"
    
    def __init__(self):
        self.api_key = settings.OPENWEATHER_API_KEY
    
    def get_current_weather(self, lat, lon):
        """
        Get current weather for coordinates
        """
        cache_key = f"weather_current_{lat}_{lon}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        try:
            url = f"{self.BASE_URL}/weather"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'units': 'metric'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            weather_info = {
                'temperature': data['main']['temp'],
                'feels_like': data['main']['feels_like'],
                'humidity': data['main']['humidity'],
                'description': data['weather'][0]['description'],
                'icon': data['weather'][0]['icon'],
                'wind_speed': data['wind']['speed'],
                'visibility': data.get('visibility', 0) / 1000,  # Convert to km
                'timestamp': data['dt']
            }
            
            # Cache for 30 minutes
            cache.set(cache_key, weather_info, 1800)
            
            return weather_info
            
        except requests.RequestException as e:
            logger.error(f"Weather API error: {str(e)}")
            return None
    
    def get_forecast(self, lat, lon, days=5):
        """
        Get weather forecast for next n days
        """
        cache_key = f"weather_forecast_{lat}_{lon}_{days}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        try:
            url = f"{self.BASE_URL}/forecast"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'units': 'metric',
                'cnt': days * 8  # 8 forecasts per day (3-hour intervals)
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            forecast_list = []
            for item in data['list']:
                forecast_list.append({
                    'datetime': item['dt'],
                    'temperature': item['main']['temp'],
                    'description': item['weather'][0]['description'],
                    'icon': item['weather'][0]['icon'],
                    'humidity': item['main']['humidity'],
                    'wind_speed': item['wind']['speed'],
                    'rain_probability': item.get('pop', 0) * 100
                })
            
            # Cache for 6 hours
            cache.set(cache_key, forecast_list, 21600)
            
            return forecast_list
            
        except requests.RequestException as e:
            logger.error(f"Weather forecast API error: {str(e)}")
            return None
    
    def is_good_travel_weather(self, weather_data):
        """
        Determine if weather is suitable for travel
        """
        if not weather_data:
            return None
        
        temp = weather_data.get('temperature', 0)
        description = weather_data.get('description', '').lower()
        
        # Bad weather conditions
        bad_conditions = ['thunderstorm', 'heavy rain', 'snow', 'extreme']
        
        if any(condition in description for condition in bad_conditions):
            return False
        
        # Temperature extremes
        if temp < 5 or temp > 40:
            return False
        
        return True


class WeatherAnalyzer:
    """
    Analyze weather patterns for destinations
    """
    
    @staticmethod
    def analyze_seasonal_weather(destination, month):
        """
        Analyze if destination is suitable for given month
        """
        # This would be enhanced with historical weather data
        best_months = destination.best_time_to_visit
        avoid_months = destination.avoid_months
        
        if month in avoid_months:
            return {
                'suitable': False,
                'reason': f"{month} is not recommended for visiting {destination.name}",
                'severity': 'high'
            }
        
        if month in best_months:
            return {
                'suitable': True,
                'reason': f"{month} is an ideal time to visit {destination.name}",
                'severity': 'none'
            }
        
        return {
            'suitable': True,
            'reason': f"{month} is acceptable for visiting {destination.name}",
            'severity': 'low'
        }
    
    @staticmethod
    def get_weather_based_recommendations(destinations, user_climate_preferences):
        """
        Filter destinations based on weather and user preferences
        """
        client = WeatherAPIClient()
        recommendations = []
        
        for destination in destinations:
            weather = client.get_current_weather(
                destination.latitude,
                destination.longitude
            )
            
            if weather and client.is_good_travel_weather(weather):
                # Check climate preference match
                if destination.climate_type in user_climate_preferences:
                    recommendations.append({
                        'destination': destination,
                        'weather': weather,
                        'match_score': 1.0
                    })
        
        return recommendations