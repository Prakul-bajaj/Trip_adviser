from rest_framework import serializers
from destinations.models import Destination, Attraction, Restaurant, Accommodation
from .models import UserRecommendation, UserBookmark, TravelAdvisory


class AttractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attraction
        fields = ['id', 'name', 'type', 'description', 'rating']


class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ['id', 'name', 'cuisine', 'rating']


class AccommodationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Accommodation
        fields = ['id', 'name', 'type', 'rating']


class DestinationSerializer(serializers.ModelSerializer):
    attractions = AttractionSerializer(many=True, read_only=True, source='destination_attractions')
    restaurants = RestaurantSerializer(many=True, read_only=True, source='destination_restaurants')
    accommodations = AccommodationSerializer(many=True, read_only=True, source='destination_accommodations')
    
    class Meta:
        model = Destination
        fields = '__all__'


class DestinationListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views"""
    class Meta:
        model = Destination
        fields = [
            'id', 'name', 'state', 'country', 'description', 
            'geography_types', 'experience_types', 'landscape_types',
            'budget_range_min', 'budget_range_max', 'typical_duration',
            'best_time_to_visit', 'difficulty_level', 'safety_rating', 
            'popularity_score', 'latitude', 'longitude', 'altitude',
            'climate_type', 'nearest_airport', 'nearest_railway_station'
        ]
        read_only_fields = ['id', 'popularity_score', 'safety_rating']


class UserRecommendationSerializer(serializers.ModelSerializer):
    destination = DestinationListSerializer(read_only=True)
    
    class Meta:
        model = UserRecommendation
        fields = '__all__'


class UserBookmarkSerializer(serializers.ModelSerializer):
    destination = DestinationListSerializer(read_only=True)
    destination_id = serializers.PrimaryKeyRelatedField(
        queryset=Destination.objects.all(),
        source='destination',
        write_only=True
    )
    
    class Meta:
        model = UserBookmark
        fields = '__all__'
        read_only_fields = ['user', 'created_at']


class TravelAdvisorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelAdvisory
        fields = '__all__'


class DestinationSearchSerializer(serializers.Serializer):
    """Serializer for destination search filters"""
    query = serializers.CharField(required=False, allow_blank=True)
    state = serializers.CharField(required=False, allow_blank=True)
    geography_types = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    experience_types = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    landscape_types = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    budget_min = serializers.IntegerField(required=False, min_value=0)
    budget_max = serializers.IntegerField(required=False, min_value=0)
    difficulty_level = serializers.CharField(required=False)
    min_rating = serializers.FloatField(required=False, min_value=0, max_value=5)
    travel_month = serializers.CharField(required=False)
    sort_by = serializers.ChoiceField(
        choices=['popularity', 'name', 'budget', 'rating'],
        default='popularity',
        required=False
    )