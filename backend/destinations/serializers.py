from rest_framework import serializers
from .models import Destination, Attraction, Restaurant, Accommodation, DestinationTag


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


class DestinationTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = DestinationTag
        fields = ['tag_name', 'tag_category']


class DestinationListSerializer(serializers.ModelSerializer):
    """Simplified serializer for list views"""
    budget_range = serializers.SerializerMethodField()
    
    class Meta:
        model = Destination
        fields = [
            'id', 'name', 'state', 'country', 'description',
            'geography_types', 'experience_types', 'landscape_types', 'spiritual_focus',
            'budget_range', 'budget_range_min', 'budget_range_max',
            'typical_duration', 'best_time_to_visit',
            'difficulty_level', 'popularity_score', 'safety_rating',
            'latitude', 'longitude', 'climate_type',
            'nearest_airport', 'nearest_railway_station'
        ]
    
    def get_budget_range(self, obj):
        return obj.get_budget_range()


class DestinationDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer with related data"""
    attractions = AttractionSerializer(source='destination_attractions', many=True, read_only=True)
    restaurants = RestaurantSerializer(source='destination_restaurants', many=True, read_only=True)
    accommodations = AccommodationSerializer(source='destination_accommodations', many=True, read_only=True)
    tags = DestinationTagSerializer(many=True, read_only=True)
    budget_range = serializers.SerializerMethodField()
    
    class Meta:
        model = Destination
        fields = '__all__'
    
    def get_budget_range(self, obj):
        return obj.get_budget_range()


class SpiritualDestinationSerializer(serializers.ModelSerializer):
    """Specialized serializer for spiritual destinations"""
    budget_range = serializers.SerializerMethodField()
    spiritual_attractions = serializers.SerializerMethodField()
    
    class Meta:
        model = Destination
        fields = [
            'id', 'name', 'state', 'country', 'description',
            'spiritual_focus', 'experience_types', 'landscape_types',
            'budget_range', 'typical_duration', 'best_time_to_visit',
            'difficulty_level', 'popularity_score', 'safety_rating',
            'latitude', 'longitude', 'altitude', 'climate_type',
            'average_temperature_range', 'nearest_airport', 'nearest_railway_station',
            'spiritual_attractions'
        ]
    
    def get_budget_range(self, obj):
        return obj.get_budget_range()
    
    def get_spiritual_attractions(self, obj):
        """Get only spiritual/religious attractions"""
        spiritual_types = ['Spiritual', 'Spiritual/Historical', 'Temple']
        attractions = obj.destination_attractions.filter(type__in=spiritual_types)
        return AttractionSerializer(attractions, many=True).data